"""Provider integration is fully mocked here: test suites never spend API credits."""

import io
import json
import os
from datetime import timedelta
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from django.test import TestCase, SimpleTestCase, override_settings
from django.utils import timezone
from django.urls import reverse
from .ai import (
    key_binding,
    generate,
    check_access,
    local_status,
    AIUnavailable,
    reserve,
)
from .models import AIRequestLog, AIExplanation, State
from .tests import PlanningFixture


def response(body):
    item = MagicMock()
    item.__enter__.return_value.read.return_value = json.dumps(body).encode()
    return item


def answer_payload(text="The gap is based on the supplied current value and target."):
    return {
        "choices": [
            {"finish_reason": "stop", "message": {"role": "assistant", "content": text}}
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130},
    }


class KeyBindingTests(SimpleTestCase):
    def test_local_NVIDIA_API_KEY_is_reused_without_renaming(self):
        with patch.dict(
            os.environ,
            {
                "NVIDIA_API_KEY": "local-test-placeholder",
                "NVDIA_API_KEY": "",
            },
        ):
            self.assertEqual(
                key_binding(), ("NVIDIA_API_KEY", "local-test-placeholder")
            )
            self.assertTrue(local_status()["configured"])

    def test_local_misspelled_nvdia_alias_is_supported(self):
        with patch.dict(
            os.environ, {"NVIDIA_API_KEY": "", "NVDIA_API_KEY": "alias-placeholder"}
        ):
            self.assertEqual(key_binding(), ("NVDIA_API_KEY", "alias-placeholder"))

    def test_openai_credential_is_not_used_for_nvidia(self):
        with patch.dict(
            os.environ,
            {
                "NVIDIA_API_KEY": "",
                "NVDIA_API_KEY": "",
                "chat_openai_key": "old-placeholder",
                "APASA_AI_API_KEY": "old-placeholder",
            },
        ):
            self.assertEqual(key_binding(), ("", None))

    def test_dotenv_does_not_replace_an_injected_binding(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from dotenv import load_dotenv

        with TemporaryDirectory() as directory, patch.dict(
            os.environ, {"NVIDIA_API_KEY": "injected-placeholder"}
        ):
            path = Path(directory) / ".env"
            path.write_text("NVIDIA_API_KEY=local-placeholder\n")
            load_dotenv(path, override=False)
            self.assertEqual(os.environ["NVIDIA_API_KEY"], "injected-placeholder")


class AITransportTests(TestCase):
    def setUp(self):
        self.key = patch(
            "planning.ai.key_binding",
            return_value=("NVIDIA_API_KEY", "test-placeholder-not-a-secret"),
        )
        self.key.start()
        self.addCleanup(self.key.stop)

    def test_selected_model_uses_nvidia_chat_and_bounded_output(self):
        with patch(
            "planning.ai.urlopen", return_value=response(answer_payload())
        ) as network:
            text, metadata = generate(
                "Use source facts only.", "Current 170; target 200."
            )
        request = network.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(
            request.full_url, "https://integrate.api.nvidia.com/v1/chat/completions"
        )
        self.assertEqual(payload["model"], "openai/gpt-oss-20b")
        self.assertLessEqual(payload["max_tokens"], 1200)
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertFalse(payload["stream"])
        self.assertNotIn("reasoning", payload)
        self.assertIn("gap", text)
        self.assertEqual(metadata["usage"]["total_tokens"], 130)
        self.assertEqual(AIRequestLog.objects.get().status, "completed")

    def test_model_check_is_read_only_and_does_not_claim_free_credit(self):
        with patch(
            "planning.ai.urlopen",
            return_value=response({"data": [{"id": "openai/gpt-oss-20b"}]}),
        ) as network:
            output = check_access()
        self.assertIsNone(network.call_args.args[0].data)
        self.assertTrue(output["model_available"])
        self.assertIn("not generation quota", output["note"])

    def test_quota_error_is_sanitized_and_never_retried(self):
        body = json.dumps(
            {
                "error": {
                    "code": "insufficient_quota",
                    "message": "do-not-display-key-placeholder",
                }
            }
        ).encode()
        error = HTTPError(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            429,
            "quota",
            {},
            io.BytesIO(body),
        )
        with patch("planning.ai.urlopen", side_effect=error) as network:
            with self.assertRaises(AIUnavailable) as caught:
                generate("Facts only.", "A source-backed fact.")
        self.assertIn("credits", str(caught.exception))
        self.assertNotIn("do-not-display", str(caught.exception))
        self.assertTrue(caught.exception.metadata["provider_call"])
        network.assert_called_once()
        self.assertEqual(AIRequestLog.objects.get().status, "insufficient_quota")

    @override_settings(APASA_AI_RPM=1)
    def test_per_minute_limit_blocks_provider_calls_before_sending(self):
        reserve("test-placeholder-not-a-secret", "openai/gpt-oss-20b", 10)
        with patch("planning.ai.urlopen") as network:
            with self.assertRaisesRegex(AIUnavailable, "per-minute"):
                generate("Facts only.", "A fact.")
            network.assert_not_called()
        self.assertEqual(AIRequestLog.objects.count(), 1)

    @override_settings(APASA_AI_RPD=1)
    def test_daily_limit_is_a_rolling_24_hour_limit(self):
        record = reserve("test-placeholder-not-a-secret", "openai/gpt-oss-20b", 10)
        AIRequestLog.objects.filter(pk=record.pk).update(
            created_at=timezone.now() - timedelta(minutes=5)
        )
        with self.assertRaisesRegex(AIUnavailable, "24-hour"):
            generate("Facts only.", "A fact.")

    @override_settings(APASA_AI_TPM=100)
    def test_conservative_token_budget_rejects_before_network(self):
        with patch("planning.ai.urlopen") as network:
            with self.assertRaisesRegex(AIUnavailable, "token budget"):
                generate("Facts only.", "A fact.")
            network.assert_not_called()

    @override_settings(APASA_AI_MODEL="not-an-authorized-model")
    def test_no_alternative_or_unlisted_model_is_tried(self):
        with patch("planning.ai.urlopen") as network:
            with self.assertRaisesRegex(AIUnavailable, "permitted model"):
                generate("Facts only.", "A fact.")
            network.assert_not_called()
        self.assertFalse(AIRequestLog.objects.exists())

    def test_incomplete_response_preserves_an_explicit_failure(self):
        with patch(
            "planning.ai.urlopen",
            return_value=response(
                {
                    "choices": [
                        {"finish_reason": "length", "message": {"content": "Partial"}}
                    ],
                    "usage": {"total_tokens": 1200},
                }
            ),
        ):
            with self.assertRaisesRegex(AIUnavailable, "output limit"):
                generate("Facts only.", "A fact.")
        self.assertEqual(AIRequestLog.objects.get().status, "incomplete")

    @override_settings(NVIDIA_BASE_URL="https://another-service.example/v1")
    def test_key_cannot_be_sent_to_a_different_host(self):
        with patch("planning.ai.urlopen") as network:
            with self.assertRaisesRegex(AIUnavailable, "NVIDIA_BASE_URL"):
                generate("Facts only.", "A fact.")
            network.assert_not_called()
        self.assertFalse(AIRequestLog.objects.exists())

    def test_private_reasoning_is_not_used_as_an_answer(self):
        body = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": None,
                        "reasoning_content": "private intermediate reasoning",
                    },
                }
            ]
        }
        with patch("planning.ai.urlopen", return_value=response(body)):
            with self.assertRaisesRegex(AIUnavailable, "no usable explanation"):
                generate("Facts only.", "A fact.")
        self.assertEqual(AIRequestLog.objects.get().status, "invalid_output")


class AIUserWorkflowTests(PlanningFixture):
    def test_question_saves_unapproved_explanation_with_canonical_facts(self):
        with patch(
            "planning.briefs.generate",
            return_value=(
                "Explain the documented gap; causes are not established.",
                {"model": "openai/gpt-oss-20b", "usage": {"total_tokens": 130}},
            ),
        ):
            result = self.client.post(
                reverse("planning:question", args=[self.report.pk]),
                {"question": "What does the current target gap mean?"},
            )
        self.assertEqual(result.status_code, 302)
        answer = AIExplanation.objects.get()
        self.assertEqual(answer.status, State.DRAFT)
        self.assertEqual(answer.method, "ai")
        self.assertIn("CANONICAL INPUT FACTS", answer.answer)
        self.assertIn("170.00", answer.answer)
        self.assertContains(self.client.get(result["Location"]), "Evidence explanation")
        self.assertEqual(answer.ai_metadata["model"], "openai/gpt-oss-20b")

    def test_unavailable_provider_returns_local_facts_not_fake_ai(self):
        with patch("planning.ai.key_binding", return_value=("", None)):
            result = self.client.post(
                reverse("planning:question", args=[self.report.pk]),
                {"question": "What information is needed before an intervention?"},
            )
        answer = AIExplanation.objects.get()
        self.assertEqual(answer.method, "template")
        self.assertIn("NOT AN AI RESPONSE", answer.answer)
        self.assertFalse(AIRequestLog.objects.exists())
        self.assertContains(self.client.get(result["Location"]), "No API key")

    def test_mocked_ai_output_remains_mocked_and_cannot_publish(self):
        self.report.is_mocked = True
        self.report.status = State.DEMO
        self.report.save()
        self.indicator.is_mocked = True
        self.indicator.status = State.DEMO
        self.indicator.save()
        self.batch.is_mocked = True
        self.batch.status = State.DEMO
        self.batch.save()
        with patch(
            "planning.briefs.generate",
            return_value=(
                "This is a fictional example.",
                {"model": "openai/gpt-oss-20b"},
            ),
        ):
            self.client.post(
                reverse("planning:question", args=[self.report.pk]),
                {"question": "Explain this mocked target gap example."},
            )
        answer = AIExplanation.objects.get()
        self.assertTrue(answer.is_mocked)
        self.assertIn("MOCKED AI", answer.answer)
        from .services import transition

        with self.assertRaisesRegex(ValueError, "Mocked"):
            transition(
                "answer",
                answer.pk,
                self.reviewer,
                "approve",
                "Attempting to publish a mocked example.",
                True,
            )

    def test_status_is_local_until_an_explicit_connection_check(self):
        with patch("planning.ai.check_access") as network:
            self.assertContains(
                self.client.get(reverse("planning:ai-status")), "Evidence assistant"
            )
            network.assert_not_called()
