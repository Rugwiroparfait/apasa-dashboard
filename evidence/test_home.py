"""The overview remains usable when a source bundle is temporarily unavailable."""

from unittest.mock import patch
from django.conf import settings
from django.test import SimpleTestCase, override_settings


@override_settings(
    MIDDLEWARE=[
        m
        for m in settings.MIDDLEWARE
        if m != "accounts.middleware.WorkspaceAuthenticationMiddleware"
    ]
)
class HomeJourneyTests(SimpleTestCase):
    def test_overview_contains_only_supported_workflows_and_real_charts(self):
        response = self.client.get("/workspace/overview/")
        self.assertContains(response, "Your planning overview")
        self.assertContains(response, "National evidence")
        self.assertContains(response, "District crop statistics")
        self.assertNotContains(response, "AHS")
        self.assertNotContains(response, "Separate survey research")
        self.assertEqual(len(response.context["charts"]), 2)
        self.assertEqual(response.context["coverage"]["observations"], 323)
        self.assertEqual(self.client.post("/workspace/overview/").status_code, 405)

    def test_missing_bundle_preserves_workflow_entry_points(self):
        with patch("evidence.views.load_bundle", side_effect=OSError("missing")):
            response = self.client.get("/workspace/overview/")
        self.assertContains(response, "National charts are temporarily unavailable")
        self.assertContains(response, "/national-policy-evidence/")
        self.assertContains(response, "/district-crop-statistics/")
