"""Render configuration tests do not connect to a real service or database."""

import io
import os
from pathlib import Path
import runpy
from unittest.mock import patch
from django.core.management import call_command
from django.test import SimpleTestCase


class RenderSettingsTests(SimpleTestCase):
    def configured(self, **extra):
        env = {
            "APASA_DEBUG": "false",
            "APASA_SECRET_KEY": "test-production-placeholder-with-enough-length-123456789",
            "RENDER": "true",
            "RENDER_EXTERNAL_HOSTNAME": "apasa-test.onrender.com",
            "APASA_TRUST_PROXY": "true",
            "DATABASE_URL": "postgresql://user:p%40ss%2Fword@internal-db/apasa?sslmode=require",
        }
        env.update(extra)
        with patch.dict(os.environ, env, clear=True), patch("dotenv.load_dotenv"):
            return runpy.run_path(str(Path(__file__).with_name("settings.py")))

    def test_render_url_proxy_and_host_configuration(self):
        config = self.configured()
        database = config["DATABASES"]["default"]
        self.assertEqual(database["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(database["PASSWORD"], "p@ss/word")
        self.assertEqual(database["HOST"], "internal-db")
        self.assertEqual(database["OPTIONS"]["sslmode"], "require")
        self.assertTrue(database["CONN_HEALTH_CHECKS"])
        self.assertIn("apasa-test.onrender.com", config["ALLOWED_HOSTS"])
        self.assertIn("https://apasa-test.onrender.com", config["CSRF_TRUSTED_ORIGINS"])
        self.assertEqual(
            config["SECURE_PROXY_SSL_HEADER"], ("HTTP_X_FORWARDED_PROTO", "https")
        )
        self.assertTrue(config["SESSION_COOKIE_SECURE"])
        self.assertFalse(config["DEBUG"])

    def test_ephemeral_sqlite_is_rejected_on_render(self):
        with self.assertRaisesRegex(ValueError, "ephemeral SQLite"):
            self.configured(DATABASE_URL="")

    def test_non_postgresql_url_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "PostgreSQL"):
            self.configured(DATABASE_URL="sqlite:///temporary.sqlite3")

    def test_old_openai_model_does_not_override_nvidia_selection(self):
        config = self.configured(APASA_AI_MODEL="obsolete-openai-model")
        self.assertEqual(config["APASA_AI_MODEL"], "openai/gpt-oss-20b")

    def test_nvidia_model_environment_is_used(self):
        config = self.configured(NVIDIA_MODEL="openai/gpt-oss-20b")
        self.assertEqual(config["APASA_AI_MODEL"], "openai/gpt-oss-20b")

    def test_packaged_evidence_validates_without_database(self):
        output = io.StringIO()
        call_command("validate_deployment_data", stdout=output)
        self.assertIn(
            "126 policy records; 1800 district records; 348", output.getvalue()
        )
