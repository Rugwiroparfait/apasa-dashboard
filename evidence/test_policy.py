from django.test import override_settings
from django.conf import settings as test_settings

import csv
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch
from django.conf import settings
from django.test import SimpleTestCase, override_settings
from .policy_data import DATA_PATH, load_policy_evidence, source_value


@override_settings(
    MIDDLEWARE=[
        m
        for m in test_settings.MIDDLEWARE
        if m != "accounts.middleware.WorkspaceAuthenticationMiddleware"
    ]
)
class PolicyEvidenceTests(SimpleTestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="apasa-policy-public-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        path = self.root / DATA_PATH
        path.parent.mkdir(parents=True)
        shutil.copyfile(settings.BASE_DIR / DATA_PATH, path)
        self.override = override_settings(PUBLIC_EVIDENCE_ROOT=self.root)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.rows = load_policy_evidence(self.root)

    def page(self, **query):
        return self.client.get("/national-policy-evidence/", query)

    def test_statuses_and_filters(self):
        response = self.page()
        self.assertContains(response, "National Policy Evidence")
        for status, count in [("Context only", 18), ("Not currently comparable", 108)]:
            r = self.page(comparability_status=status)
            self.assertEqual(len(r.context["rows"]), count)
            self.assertTrue(
                all(x["comparability_status"] == status for x in r.context["rows"])
            )
        row = self.rows[0]
        query = {
            field: row[field]
            for field in [
                "outcome_output",
                "crop",
                "indicator_name",
                "comparability_status",
            ]
        }
        r = self.page(**query, record=row["key"])
        self.assertEqual(len(r.context["rows"]), 1)
        self.assertContains(r, row["reason"])
        self.assertContains(
            r, '<h3 id="comparison-heading">Context only</h3>', html=True
        )
        self.assertEqual(self.page(crop="unknown").status_code, 404)
        self.assertEqual(self.page(crop="Maize", record="126").status_code, 404)
        self.assertEqual(
            self.client.post("/national-policy-evidence/").status_code, 405
        )

    def test_reference_values_and_actual_metadata_links(self):
        for row in self.rows:
            r = self.page(record=row["key"])
            for ref in row["references"]:
                if ref["value"]:
                    self.assertContains(r, ref["value"])
                if ref["period"]:
                    self.assertContains(r, ref["period"])
            for field in [
                "target_unit",
                "target_geography",
                "policy_page",
                "policy_source_url",
                "policy_source_agency",
            ]:
                if row[field]:
                    self.assertContains(r, row[field])
            if row["actual"]["value"]:
                for field in [
                    "official_actual_value",
                    "actual_year_or_period",
                    "actual_unit",
                    "actual_geography",
                    "actual_crop_label",
                    "source_url",
                    "page_or_table",
                ]:
                    self.assertContains(r, row[field])

    def test_blank_actual_is_not_zero_and_seasons_stay_separate(self):
        row = next(x for x in self.rows if not x["official_actual_value"])
        r = self.page(record=row["key"])
        self.assertContains(r, "No matching actual verified in the sources reviewed.")
        self.assertEqual(r.context["selected"]["actual"]["value"], "")
        self.assertNotContains(r, '<p class="district-value">0</p>', html=True)
        maize = self.rows[0]
        r = self.page(record=maize["key"])
        seasons = r.context["selected"]["seasons"]
        self.assertEqual(len(seasons), 3)
        self.assertEqual(
            [s["value"] for s in seasons],
            [
                maize["annual_2025_season_a_actual"],
                maize["annual_2025_season_b_actual"],
                maize["annual_2025_season_c_actual"],
            ],
        )
        for season in seasons:
            self.assertContains(r, season["period"])
        self.assertContains(r, "No seasonal value recorded in the reviewed inventory")
        self.assertContains(r, maize["annual_table_reference"])
        self.assertContains(r, maize["latest_annual_source_url"])

    def test_ambiguous_values_preserved_and_reviewed(self):
        with (self.root / DATA_PATH).open(newline="") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames
            rows = list(reader)
        rows[0]["target_value"] = "10,1801,897"
        with (self.root / DATA_PATH).open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        r = self.page(record="1")
        self.assertContains(r, "10,1801,897")
        self.assertContains(r, "Review note: source text is non-numeric or ambiguous")
        self.assertEqual(source_value("0"), {"value": "0", "review": False})

    def test_no_progress_or_district_aggregation(self):
        with patch(
            "evidence.district_data.load_district_statistics",
            side_effect=AssertionError("District data forbidden"),
        ):
            r = self.page(record="1")
        self.assertEqual(r.status_code, 200)
        for markup in [
            "<meter",
            "<progress",
            'role="progressbar"',
            "progress_value",
            "progress_formula",
        ]:
            self.assertNotContains(r, markup)
        self.assertContains(r, "district values are never summed")
        # Only the CSV can be opened by the loader, even when district files are absent.
        self.assertFalse((self.root / "outputs/day7").exists())
        original = Path.open
        opened = []

        def audited(path, *args, **kwargs):
            opened.append(path)
            return original(path, *args, **kwargs)

        with patch.object(Path, "open", audited):
            load_policy_evidence(self.root)
        from .curation import REGISTRY_PATH

        self.assertEqual(opened, [self.root / DATA_PATH, REGISTRY_PATH])

    def test_fresh_process_without_ahs_or_day7(self):
        for package in ["apasa", "evidence", "accounts"]:
            shutil.copytree(
                settings.BASE_DIR / package,
                self.root / package,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
        self.assertFalse((self.root / "local_data").exists())
        self.assertFalse((self.root / "outputs").exists())
        code = "import os;os.environ['DJANGO_SETTINGS_MODULE']='apasa.settings';import django;django.setup();from django.conf import settings;settings.MIDDLEWARE=[m for m in settings.MIDDLEWARE if m != 'accounts.middleware.WorkspaceAuthenticationMiddleware'];from django.test import Client;r=Client(HTTP_HOST='localhost').get('/national-policy-evidence/?record=1');assert r.status_code==200,r.status_code;assert b'122370.3260885097' in r.content"
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_navigation_and_missing_source(self):
        r = self.page()
        for url in ["/", "/workbook-evidence/", "/district-crop-statistics/"]:
            self.assertContains(
                r, 'href="' + url + '"' if url != "/" else "National Policy Evidence"
            )
        self.assertContains(r, 'name="viewport"')
        self.assertContains(r, 'for="outcome_output"')
        (self.root / DATA_PATH).unlink()
        self.assertEqual(self.page().status_code, 503)

    def test_default_and_valid_analyst_selection(self):
        response = self.page()
        self.assertEqual(len(response.context["rows"]), 126)
        self.assertEqual(response.context["selected"]["key"], "1")
        self.assertContains(response, "Showing the first matching evidence record")
        row = self.rows[0]
        response = self.page(
            outcome_output=row["outcome_output"],
            crop="maize",
            indicator_name=row["indicator_name"],
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected"]["key"], row["key"])
        for field in [
            "official_actual_value",
            "actual_year_or_period",
            "actual_unit",
            "actual_geography",
            "source_url",
            "page_or_table",
            "reason",
        ]:
            self.assertContains(response, row[field])
        self.assertContains(
            response, "It cannot establish progress against the policy target."
        )

    def test_dependent_options_only_offer_matching_records(self):
        for outcome in {r["policy_code"] for r in self.rows}:
            outcome_rows = [r for r in self.rows if r["policy_code"] == outcome]
            response = self.page(outcome_output=outcome)
            filters = {f["name"]: f for f in response.context["filters"]}
            self.assertEqual(
                {code for code, name in filters["crop"]["options"]},
                {r["crop_code"] for r in outcome_rows if r["crop_code"]},
            )
            for crop, name in filters["crop"]["options"]:
                response = self.page(outcome_output=outcome, crop=crop)
                matching = [r for r in outcome_rows if r["crop_code"] == crop]
                filters = {f["name"]: f for f in response.context["filters"]}
                from .curation import registry

                indicators = registry()[0]["indicators"]
                expected = {
                    x["code"]
                    for x in indicators
                    if any(r["indicator_name"] in x["aliases"] for r in matching)
                }
                self.assertEqual(
                    set(dict(filters["indicator_name"]["options"])), expected
                )
                self.assertEqual(
                    {r["key"] for r in response.context["rows"]},
                    {r["key"] for r in matching},
                )

    def test_stale_combination_explains_cleared_choice(self):
        # Maize exists, but is not an export-output crop. A bookmarked or stale
        # dependent choice must not trap the analyst in an impossible menu.
        response = self.page(outcome_output="PSTA5:Output-2.1.1", crop="maize")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Crop or crop group", response.context["cleared_filters"])
        self.assertTrue(response.context["rows"])
        self.assertContains(
            response,
            "has no matching records under the choices above it and was cleared",
        )
        filters = {f["name"]: f for f in response.context["filters"]}
        self.assertNotIn("maize", dict(filters["crop"]["options"]))
        self.assertEqual(filters["crop"]["value"], "")

    def test_unavailable_comparison_and_empty_inventory_explain_limits(self):
        row = next(
            r
            for r in self.rows
            if r["crop"] == "Onions" and not r["official_actual_value"]
        )
        response = self.page(
            outcome_output=row["outcome_output"],
            crop=row["crop_code"],
            indicator_name=row["indicator_name"],
        )
        self.assertEqual(response.context["selected"]["key"], row["key"])
        for text in [
            "No matching actual verified in the sources reviewed.",
            row["reason"],
            row["target_year"],
            row["target_unit"],
            row["policy_source_url"],
            "Not verified",
        ]:
            self.assertContains(response, text)
        self.assertNotContains(response, "<progress")
        self.assertNotContains(response, "<meter")
        with patch("evidence.policy_views.policy_rows", return_value=[]):
            response = self.page()
        self.assertContains(
            response, "No evidence records available for this selection"
        )
        self.assertContains(response, "does not mean the crop has no data elsewhere")
        self.assertNotContains(response, 'id="record"')

    def test_user_pages_do_not_show_development_day_references(self):
        import re

        # Home and policy work with only the public policy source in this fixture.
        for url in ["/", "/national-policy-evidence/?record=1"]:
            response = self.client.get(url)
            self.assertIsNone(
                re.search(r"\bDay\s+\d+\b", response.content.decode(), re.I)
            )
        # Cover unavailable templates as well as normal pages at source level.
        for template in (settings.BASE_DIR / "evidence/templates/evidence").glob(
            "*.html"
        ):
            self.assertIsNone(
                re.search(r"\bDay\s+\d+\b", template.read_text(), re.I), str(template)
            )
        self.assertNotContains(self.page(), "AHS Research Evidence")
