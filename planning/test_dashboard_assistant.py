"""Dashboard questions use server-signed public facts and the existing AI transport."""

import json
import re
from html import unescape
from unittest.mock import patch
from django.test import Client
from django.urls import reverse
from planning.ai import AIUnavailable
from planning.models import AIExplanation
from planning.tests import PlanningFixture


class DashboardAssistantTests(PlanningFixture):
    def token(self, path="/workspace/overview/"):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return unescape(
            re.search(
                r'name="context_token" value="([^"]+)"', response.content.decode()
            ).group(1)
        )

    def ask(self, token, **extra):
        return self.client.post(
            reverse("planning:dashboard-question"),
            dict(
                context_token=token,
                question="Explain the published chart and its limitations.",
                **extra
            ),
            HTTP_ACCEPT="application/json",
        )

    def test_dashboard_facts_are_server_signed_and_browser_facts_are_ignored(self):
        token = self.token()
        with patch(
            "planning.briefs.generate",
            return_value=(
                "Published observations are descriptive.",
                {"provider": "NVIDIA"},
            ),
        ) as call:
            response = self.ask(token, facts="PRIVATE BROWSER INVENTION")
        self.assertEqual(response.status_code, 200)
        sent = call.call_args.args[1]
        self.assertIn("507984.9194559117", sent)
        self.assertIn("2024 Season A", sent)
        self.assertIn("source", sent)
        self.assertNotIn("PRIVATE BROWSER INVENTION", sent)
        self.assertEqual(response.json()["method"], "ai")
        self.assertTrue(response.json()["sources"])

    def test_modified_or_other_user_token_cannot_call_provider(self):
        token = self.token()
        with patch("planning.briefs.generate") as call:
            self.assertEqual(self.ask(token + "tampered").status_code, 400)
            self.client.force_login(self.reviewer)
            self.assertEqual(self.ask(token).status_code, 400)
            call.assert_not_called()

    def test_unavailable_service_returns_error_without_fake_answer(self):
        token = self.token()
        with patch(
            "planning.briefs.generate",
            side_effect=AIUnavailable("NVIDIA quota unavailable."),
        ):
            response = self.ask(token)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"], "NVIDIA quota unavailable.")
        self.assertNotIn("answer", response.json())

    def test_thread_survives_reload_and_changes_with_filters(self):
        token = self.token()
        with patch(
            "planning.briefs.generate",
            return_value=("Only the cited observations are available.", {}),
        ):
            self.ask(token)
        reloaded = self.client.get("/workspace/overview/")
        self.assertContains(reloaded, "Only the cited observations are available.")
        self.assertContains(reloaded, "Source references")
        self.assertContains(reloaded, "Table 6!I6")
        self.assertNotContains(
            self.client.get("/workspace/overview/?crop=Maize&period=2026+Season+B"),
            "Only the cited observations are available.",
        )

    def test_page_load_does_not_generate_and_no_private_draft_chart_is_shared(self):
        with patch("planning.ai.urlopen") as network:
            self.token()
            token = self.token(reverse("planning:manage"))
            self.assertEqual(self.ask(token).status_code, 422)
            network.assert_not_called()

    def test_mocked_preview_cannot_be_presented_as_published_context(self):
        token = self.token(
            "/workbook-evidence/?crop=Maize&indicator=improved_seeds&mock=1"
        )
        with patch("planning.briefs.generate") as call:
            self.assertEqual(self.ask(token).status_code, 422)
            call.assert_not_called()

    def test_unconfigured_panel_disables_generation_controls(self):
        with patch("evidence.templatetags.workspace_ui.local_status", return_value={"configured": False}):
            response = self.client.get("/workspace/overview/")
        self.assertContains(response, 'data-enabled="false"')
        self.assertContains(response, "Assistant unavailable")
        self.assertContains(response, 'type="submit" disabled')
        self.assertNotContains(response, 'data-assistant-question=')

    def test_display_context_omits_blank_fields(self):
        from evidence.templatetags.workspace_ui import workspace_assistant
        response = self.client.get("/workspace/overview/")
        context = {"request": response.wsgi_request}
        with patch("evidence.templatetags.workspace_ui.snapshot", return_value=(
            {"page": "", "filters": {"crop": "  ", "period": None, "district_name": "Gasabo"}, "charts": []},
            "test-context", "signed-token",
        )):
            panel = workspace_assistant(context)
        self.assertEqual(panel["assistant_context_page"], "General APASA question")
        self.assertEqual(panel["assistant_context_fields"], [("District", "Gasabo")])

    def test_csrf_and_existing_role_boundary_are_preserved(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.author)
        response = client.post(
            reverse("planning:dashboard-question"), {"question": "Explain this chart."}
        )
        self.assertEqual(response.status_code, 403)

    def test_report_panel_still_saves_existing_reviewable_explanation(self):
        with patch(
            "planning.briefs.generate",
            return_value=("The canonical report has a documented gap.", {}),
        ):
            response = self.client.post(
                reverse("planning:question", args=[self.report.pk]),
                {"question": "Explain the current target gap."},
                HTTP_ACCEPT="application/json",
            )
        self.assertEqual(response.status_code, 200)
        answer = AIExplanation.objects.get()
        self.assertEqual(answer.created_by, self.author)
        self.assertEqual(answer.assessment, self.report)
        self.assertEqual(answer.method, "ai")
        self.assertIn("planning/records/answer", response.json()["url"])

    def test_district_demo_context_preserves_selection_origin_and_limits(self):
        token = self.token('/district-crop-statistics/?data=demo&province=2&district=24&crop=Maize&period=2026+A&chart_measure=crop_production')
        with patch('planning.briefs.generate', return_value=('This is a synthetic example, not official evidence.', {})) as provider:
            response = self.ask(token)
        self.assertEqual(response.status_code, 200)
        sent = provider.call_args.args[1]
        for phrase in ['Huye', 'Maize', '2026 A', 'Synthetic / illustrative', 'not official statistics', 'no sample or farmer population']:
            self.assertIn(phrase.lower(), sent.lower())
        self.assertNotIn('NISR SAS 2026 Season B', sent)
        self.assertTrue(response.json()['sources'])
