"""VPS setup must preserve existing secrets and avoid exposing credentials."""

from pathlib import Path
from tempfile import TemporaryDirectory
from django.test import SimpleTestCase
from deploy.configure_vps import create_config


class VPSConfigurationTests(SimpleTestCase):
    def test_generated_configuration_has_private_permissions_and_distinct_secrets(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env.vps"
            create_config(path, "apasa.inzuyange.com")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            values = dict(
                line.split("=", 1)
                for line in path.read_text().splitlines()
                if line and not line.startswith("#")
            )
            self.assertEqual(values["APASA_DOMAIN"], "apasa.inzuyange.com")
            secret_names = [
                "APASA_SECRET_KEY",
                "APASA_DB_PASSWORD",
                "APASA_POLICYMAKER_PASSWORD",
                "APASA_DISTRICT_PASSWORD",
            ]
            secrets = [values[key] for key in secret_names]
            self.assertEqual(len(set(secrets)), 4)
            self.assertTrue(all(len(secret) >= 32 for secret in secrets))
            self.assertTrue(
                all(not any(c in secret for c in "/:@$#\n") for secret in secrets)
            )
            self.assertEqual(values["NVIDIA_API_KEY"], "")

    def test_existing_configuration_cannot_be_overwritten(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env.vps"
            create_config(path, "apasa.inzuyange.com")
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                create_config(path, "apasa.inzuyange.com")
            self.assertEqual(path.read_bytes(), original)

    def test_invalid_domain_does_not_write_a_file(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env.vps"
            for domain in [
                "https://apasa.inzuyange.com",
                "apasa.inzuyange.com:8000",
                "a.example\nDEBUG=true",
            ]:
                with self.assertRaises(ValueError):
                    create_config(path, domain)
                self.assertFalse(path.exists())
