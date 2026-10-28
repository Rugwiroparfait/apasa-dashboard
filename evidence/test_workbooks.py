import hashlib
import json
from pathlib import Path
import tempfile
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, SimpleTestCase, override_settings
from .workbook_data import load_bundle


class WorkbookTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("workbook_reader"))

    def test_real_observations_filters_and_provenance(self):
        response = self.client.get(
            "/workbook-evidence/?crop=Maize&indicator=production&period=2026+Season+B"
        )
        self.assertContains(response, "122370.3260885097")
        self.assertContains(response, "Table 6!I6")
        self.assertEqual(len(response.context["rows"]), 1)
        self.assertFalse(response.context["rows"][0]["mocked"])
        self.assertEqual(
            self.client.get("/workbook-evidence/?period=2013").status_code, 404
        )
        exported = self.client.get(
            "/workbook-evidence/?crop=Maize&indicator=production&download=csv"
        )
        self.assertContains(exported, "source_sha256")
        self.assertContains(exported, "source_value")
        self.assertNotIn("MOCKED", exported["Content-Disposition"])

    def test_unavailable_mock_is_explicit_and_never_changes_source(self):
        bundle = load_bundle(str(settings.PUBLIC_EVIDENCE_ROOT))
        before = json.dumps(bundle, sort_keys=True)
        response = self.client.get("/workbook-evidence/?mock=1&download=csv")
        self.assertContains(response, "MOCKED — illustrative")
        self.assertIn("MOCKED", response["Content-Disposition"])
        self.assertEqual(json.dumps(bundle, sort_keys=True), before)
        self.assertContains(self.client.get("/workbook-evidence/"), "unavailable")


class BundleIntegrityTests(SimpleTestCase):
    def test_tampered_bundle_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "outputs/workbook_observations"
            path.mkdir(parents=True)
            (path / "evidence.json").write_text("{}")
            (path / "evidence.sha256").write_text("bad")
            with self.assertRaises(ValueError):
                load_bundle(directory)

    def test_six_seasons_and_known_farmer_denominators(self):
        bundle = load_bundle(str(settings.PUBLIC_EVIDENCE_ROOT))
        self.assertEqual(len({r["period"] for r in bundle["observations"]}), 6)
        rows = [
            r
            for r in bundle["observations"]
            if r["indicator"] == "improved_seeds" and r["period"] == "2024 Season B"
        ]
        self.assertEqual(
            {r["population"]: r["value"] for r in rows},
            {"SSF": "16.64", "LSF": "72.57"},
        )
        self.assertEqual(len(bundle["register"]), 30)
