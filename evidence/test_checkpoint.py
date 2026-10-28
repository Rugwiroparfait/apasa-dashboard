"""The visual checkpoint never promotes mock data to official evidence."""

from django.test import override_settings
from django.conf import settings as test_settings

from unittest.mock import patch
from django.conf import settings
from django.test import SimpleTestCase
from .policy_data import load_policy_evidence
from .policy_presentation import presentation
from .normalization import build_tables


@override_settings(
    MIDDLEWARE=[
        m
        for m in test_settings.MIDDLEWARE
        if m != "accounts.middleware.WorkspaceAuthenticationMiddleware"
    ]
)
class PolicyCheckpointTests(SimpleTestCase):
    def setUp(self):
        self.rows = load_policy_evidence(settings.BASE_DIR)
        self.maize = self.rows[0]
        self.missing = next(
            r for r in self.rows if r["crop"] == "Onions" and not r["actual"]["value"]
        )

    def test_four_steps_and_real_source_values(self):
        for url in [
            "/national-policy-evidence/?record=1",
            "/national-policy-evidence/crop/?record=1",
            "/national-policy-evidence/note/?record=1",
        ]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            for text in ["122370.3260885097", self.maize["source_url"]]:
                self.assertContains(response, text)
            for forbidden in [
                "<progress",
                'role="progressbar"',
                "MOCK DATA · NOT OFFICIAL",
            ]:
                self.assertNotContains(response, forbidden)
        response = self.client.get("/national-policy-evidence/crop/?record=1")
        self.assertContains(response, "Separate observations, not a verified trend.")
        for period in [
            "2025 Season A",
            "2025 Season B",
            "2025 Season C",
            "2026 Season B",
        ]:
            self.assertContains(response, period)

    def test_mock_is_opt_in_only_for_a_missing_actual(self):
        original = dict(self.missing)
        self.assertIsNone(presentation(self.missing)["mock"])
        self.assertIsNone(presentation(self.maize, True)["mock"])
        self.assertIsNotNone(presentation(self.missing, True)["mock"])
        self.assertEqual(self.missing, original)
        for page in ["", "crop/", "note/"]:
            url = "/national-policy-evidence/" + page
            response = self.client.get(url, {"record": self.missing["key"]})
            self.assertNotContains(response, "MOCK DATA · NOT OFFICIAL")
            self.assertContains(
                response, "No matching actual verified in the sources reviewed."
            )
            response = self.client.get(
                url, {"record": self.missing["key"], "mock": "1"}
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "MOCK DATA")
            self.assertContains(response, "no official source")
            self.assertContains(response, "How to replace this missing actual")
            self.assertEqual(response.context["selected"]["actual"]["value"], "")
            self.assertEqual(
                response.context["selected"]["comparability_status"],
                "Not currently comparable",
            )

    def test_note_download_preserves_units_periods_sources_and_mock_warning(self):
        response = self.client.get(
            "/national-policy-evidence/note/", {"record": "1", "download": "text"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/plain"))
        for value in [
            "122370.3260885097",
            self.maize["actual_year_or_period"],
            self.maize["actual_unit"],
            self.maize["actual_geography"],
            self.maize["reason"],
            self.maize["policy_source_url"],
        ]:
            self.assertIn(value, response.content.decode())
        self.assertNotIn("MOCK DATA", response.content.decode())
        response = self.client.get(
            "/national-policy-evidence/note/",
            {"record": self.missing["key"], "download": "text", "mock": "1"},
        )
        self.assertIn("MOCK", response["Content-Disposition"])
        self.assertIn(
            "MOCK DATA — DESIGN PREVIEW ONLY; NOT OFFICIAL EVIDENCE",
            response.content.decode(),
        )
        self.assertIn("official actual remains unverified", response.content.decode())

    def test_previews_never_change_export_or_read_districts(self):
        before = build_tables(settings.BASE_DIR)
        with patch(
            "evidence.district_data.load_district_statistics",
            side_effect=AssertionError("District data forbidden"),
        ):
            for url in [
                "/national-policy-evidence/crop/",
                "/national-policy-evidence/note/",
            ]:
                response = self.client.get(
                    url, {"record": self.missing["key"], "mock": "1"}
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    self.client.get(url, {"record": "9999"}).status_code, 404
                )
                self.assertEqual(self.client.post(url).status_code, 405)
        self.assertEqual(build_tables(settings.BASE_DIR), before)
