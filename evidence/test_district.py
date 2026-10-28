from django.test import override_settings
from django.conf import settings as test_settings

import csv
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from django.conf import settings
from django.test import SimpleTestCase, override_settings
from .district_data import DATA_PATH, MEASURES


@override_settings(
    MIDDLEWARE=[
        m
        for m in test_settings.MIDDLEWARE
        if m != "accounts.middleware.WorkspaceAuthenticationMiddleware"
    ]
)
class DistrictStatisticsTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="apasa-district-public-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        target = self.root / DATA_PATH
        target.parent.mkdir(parents=True)
        shutil.copyfile(settings.BASE_DIR / DATA_PATH, target)
        with target.open() as f:
            self.source = list(csv.DictReader(f))
        override = override_settings(PUBLIC_EVIDENCE_ROOT=self.root)
        override.enable()
        self.addCleanup(override.disable)

    def get_page(self, **query):
        return self.client.get("/district-crop-statistics/", query)

    def test_page_and_parent_filters(self):
        r = self.get_page()
        self.assertContains(r, "District Crop Statistics")
        self.assertContains(r, "2026 Season B (March–June 2026)")
        self.assertEqual(len(r.context["provinces"]), 5)
        self.assertEqual(r.context["districts"], [])
        for parent in {x["province_id"] for x in self.source}:
            r = self.get_page(province=parent)
            expected = {
                (x["district_id"], x["district"])
                for x in self.source
                if x["province_id"] == parent
            }
            self.assertEqual(set(r.context["districts"]), expected)
        r = self.get_page(province="1")
        self.assertEqual(
            {x[1] for x in r.context["districts"]}, {"Nyarugenge", "Gasabo", "Kicukiro"}
        )
        for q in [
            {"province": "unknown"},
            {"province": "1", "district": "57"},
            {"district": "11"},
            {"province": "1", "district": "11", "crop": "Coffee"},
        ]:
            self.assertEqual(self.get_page(**q).status_code, 404)

    def test_crop_selection_and_source_units_values(self):
        r = self.get_page(province="1", district="11", crop="Maize")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["crops"]), 15)
        selected = r.context["selected"]
        self.assertEqual(len(selected), 4)
        for row in selected:
            original = next(
                x
                for x in self.source
                if x["district_id"] == "11"
                and x["crop_sas_label"] == "Maize"
                and x["measure"] == row["measure"]
            )
            for key in original:
                self.assertEqual(row[key], original[key])
            self.assertContains(r, row["value"])
            self.assertContains(r, MEASURES[row["measure"]][1])
            self.assertContains(r, row["worksheet"])
            self.assertContains(r, row["cell_reference"])
            self.assertContains(r, row["source_report"])
            self.assertContains(r, row["source_workbook_url"])
        self.assertEqual(
            {row["worksheet"] for row in selected},
            {"Table 9", "Table 10", "Table 11", "Table 13"},
        )

    def test_blank_and_zero_have_distinct_renderings(self):
        r = self.get_page(province="1", district="11", crop="Wheat")
        self.assertContains(r, "Unavailable — blank in source")
        self.assertContains(r, "0 — reported zero")
        cultivated = next(
            x for x in r.context["selected"] if x["measure"] == "cultivated_crop_area"
        )
        self.assertEqual(cultivated["value"], "")
        self.assertEqual(cultivated["source_value_status"], "blank")

    def test_only_explicit_case_mapping(self):
        r = self.get_page(province="1", district="11", crop="Cooking banana")
        self.assertEqual(len(r.context["selected"]), 4)
        self.assertEqual(
            {x["crop_sas_label"] for x in r.context["selected"]},
            {"Cooking Banana", "Cooking banana"},
        )
        self.assertEqual(len(set(r.context["crops"])), 15)
        self.assertContains(r, "Source details")
        self.assertContains(r, "No other crop mapping")

    def test_no_aggregate_results_or_write_actions(self):
        r = self.get_page(province="1", district="11", crop="Maize")
        self.assertEqual({x["district_id"] for x in r.context["selected"]}, {"11"})
        self.assertEqual({x["measure"] for x in r.context["selected"]}, set(MEASURES))
        for key in ["total", "ranking", "progress", "national_total", "province_total"]:
            self.assertNotIn(key, r.context[-1].flatten())
        self.assertNotContains(r, "<meter")
        self.assertContains(r, "No national or provincial aggregation")
        self.assertContains(r, "programme delivery")
        self.assertEqual(
            self.client.post("/district-crop-statistics/").status_code, 405
        )

    def test_fresh_process_with_only_day7_aggregate(self):
        for package in ["apasa", "evidence", "accounts", "planning"]:
            shutil.copytree(
                settings.BASE_DIR / package,
                self.root / package,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
        self.assertFalse((self.root / "local_data").exists())
        self.assertFalse((self.root / "data").exists())
        self.assertFalse((self.root / "outputs/day3").exists())
        code = "import os;os.environ['DJANGO_SETTINGS_MODULE']='apasa.settings';import django;django.setup();from django.conf import settings;settings.MIDDLEWARE=[m for m in settings.MIDDLEWARE if m != 'accounts.middleware.WorkspaceAuthenticationMiddleware'];from django.test import Client;r=Client(HTTP_HOST='localhost').get('/district-crop-statistics/?province=1&district=11&crop=Maize');assert r.status_code==200,r.status_code;assert b'574.4233' in r.content"
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unavailable_dataset_fails_closed(self):
        # Replace the fixture only; never alter the real Day 7 CSV.
        (self.root / DATA_PATH).write_text("invalid\n")
        self.assertEqual(self.get_page().status_code, 503)
