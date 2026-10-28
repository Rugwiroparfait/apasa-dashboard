from django.test import override_settings
from django.conf import settings as test_settings

import csv
import io
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.conf import settings
from django.test import SimpleTestCase, override_settings
from .curation import registry, annotate, crop_options
from .normalization import build_tables, export_bundle


@override_settings(
    MIDDLEWARE=[
        m
        for m in test_settings.MIDDLEWARE
        if m != "accounts.middleware.WorkspaceAuthenticationMiddleware"
    ]
)
class PublicWorkflowTests(SimpleTestCase):
    def test_policy_aliases_use_one_curated_code(self):
        data, _, nodes, _, aliases = registry()
        self.assertEqual(
            aliases["Outcome 1.1"],
            aliases["Outcome 1.1: MODERNIZED CROP PRODUCTION AND PRODUCTIVITY"],
        )
        self.assertEqual(
            aliases["Output 2.3.1"],
            aliases["Output 2.3.1: Food security and nutrition improved"],
        )
        response = self.client.get("/national-policy-evidence/")
        node_filter = next(
            f for f in response.context["filters"] if f["name"] == "outcome_output"
        )
        self.assertEqual(len(node_filter["options"]), 21)
        self.assertEqual(len({code for code, name in node_filter["options"]}), 21)
        self.assertTrue(
            all(code.startswith("PSTA5:") for code, name in node_filter["options"])
        )
        crop_filter = next(
            f for f in response.context["filters"] if f["name"] == "crop"
        )
        self.assertNotIn("AgriHubs", dict(crop_filter["options"]))
        self.assertNotIn("Rice", dict(crop_filter["options"]))
        r = self.client.get(
            "/national-policy-evidence/", {"outcome_output": aliases["Outcome 1.1"]}
        )
        self.assertTrue(
            all(x["policy_code"] == aliases["Outcome 1.1"] for x in r.context["rows"])
        )

    def test_individuals_groups_and_uncertain_matches(self):
        rows = annotate(
            [
                dict(crop=x, outcome_output="Outcome 1.1")
                for x in [
                    "Maize",
                    "Cereals",
                    "Beans",
                    "Beans (Bush and Climbing)",
                    "Rice",
                    "Paddy rice",
                ]
            ],
            "policy",
        )
        self.assertEqual(
            [r["crop_kind"] for r in rows[:4]],
            ["individual", "group", "group", "group"],
        )
        self.assertNotEqual(rows[2]["crop_code"], rows[3]["crop_code"])
        self.assertEqual(rows[4]["crop_code"], "")
        self.assertEqual(rows[4]["crop_mapping_status"], "review")
        self.assertNotEqual(rows[4]["crop_code"], rows[5]["crop_code"])
        self.assertEqual(len(crop_options(rows)), 5)
        r = self.client.get(
            "/district-crop-statistics/",
            {"province": "1", "district": "11", "crop": "maize"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(all(x["crop_code"] == "maize" for x in r.context["selected"]))
        self.assertNotIn("cereals", dict(r.context["crops"]))

    def test_deterministic_exports_keep_provenance_and_values(self):
        one = build_tables(settings.BASE_DIR)
        self.assertEqual(one, build_tables(settings.BASE_DIR))
        bundle_id, manifest, files = one
        records = list(
            csv.DictReader(io.StringIO(files["source_records.csv"].decode()))
        )
        observations = list(
            csv.DictReader(io.StringIO(files["observations.csv"].decode()))
        )
        self.assertEqual(len(records), 1926)
        self.assertEqual(len(observations), 2358)
        self.assertTrue(all(o["measure"] for o in observations))
        self.assertTrue(manifest["curation"]["policy_nodes"])
        source = next(
            r
            for r in records
            if json.loads(r["original_json"]).get("district_id") == "11"
        )
        raw = json.loads(source["original_json"])
        obs = next(
            o
            for o in observations
            if (o["dataset"], o["record_key"]) == (source["dataset"], source["key"])
        )
        self.assertEqual(obs["value_text"], raw["value"])
        self.assertEqual(
            obs["source_reference"], raw["worksheet"] + "!" + raw["cell_reference"]
        )
        self.assertEqual(obs["unit"], raw["unit"])
        self.assertIn("March-June 2026", obs["period"])
        self.assertIn("Nyarugenge", obs["geography"])
        self.assertTrue(
            all(x["source_sha256"] and x["source_urls"] for x in manifest["datasets"])
        )
        self.assertTrue(
            any(
                o["value_state"] == "blank" and o["value_text"] == ""
                for o in observations
            )
        )
        self.assertTrue(
            any(
                o["value_state"] == "numeric_zero" and o["value_text"] == "0"
                for o in observations
            )
        )
        self.assertEqual(
            {o["key"] for o in observations if o["kind"] == "seasonal_actual"},
            {
                "annual_2025_season_a_actual",
                "annual_2025_season_b_actual",
                "annual_2025_season_c_actual",
            },
        )

    def test_only_allowlisted_inputs_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for relative in [
                "docs/day6_indicator_comparability.csv",
                "outputs/day7/official_sas_2026_b_district.csv",
            ]:
                dest = root / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(settings.BASE_DIR / relative, dest)
            target, _ = export_bundle(root, root / "export")
            self.assertEqual(export_bundle(root, root / "export")[0], target)
            (target / "observations.csv").write_text("unexpected changes")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                export_bundle(root, root / "export")
            source = root / "docs/day6_indicator_comparability.csv"
            source.write_text(source.read_text() + "\n")
            with self.assertRaisesRegex(ValueError, "checksum changed"):
                build_tables(root)
            self.assertFalse((root / "local_data").exists())

    def test_database_free_mode_does_not_query_offline_postgres(self):
        with override_settings(PUBLIC_EVIDENCE_MODE="csv"):
            with patch(
                "evidence.repository.database_records",
                side_effect=AssertionError("Database queried in CSV mode"),
            ):
                for url in [
                    "/",
                    "/national-policy-evidence/?record=1",
                    "/district-crop-statistics/?province=1&district=11&crop=maize",
                ]:
                    self.assertEqual(self.client.get(url).status_code, 200)
        from django.db import OperationalError

        with override_settings(PUBLIC_EVIDENCE_MODE="database"):
            with patch(
                "evidence.repository.database_records",
                side_effect=OperationalError("offline"),
            ):
                self.assertEqual(self.client.get("/").status_code, 200)
                self.assertEqual(
                    self.client.get("/national-policy-evidence/").status_code, 503
                )
                self.assertEqual(
                    self.client.get("/district-crop-statistics/").status_code, 503
                )

    def test_fresh_public_only_startup_without_database_or_microdata(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for package in ["apasa", "evidence", "accounts", "planning"]:
                shutil.copytree(
                    settings.BASE_DIR / package,
                    root / package,
                    ignore=shutil.ignore_patterns("__pycache__"),
                )
            for relative in [
                "docs/day6_indicator_comparability.csv",
                "outputs/day7/official_sas_2026_b_district.csv",
            ]:
                dest = root / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(settings.BASE_DIR / relative, dest)
            code = """import os
os.environ['DJANGO_SETTINGS_MODULE']='apasa.settings'
os.environ['APASA_EVIDENCE_MODE']='csv'
os.environ.pop('APASA_DB_NAME',None)
import django;django.setup()
from django.conf import settings;settings.MIDDLEWARE=[m for m in settings.MIDDLEWARE if m != 'accounts.middleware.WorkspaceAuthenticationMiddleware']
from django.test import Client
c=Client(HTTP_HOST='localhost')
for url in ['/', '/national-policy-evidence/?record=1', '/district-crop-statistics/?province=1&district=11&crop=maize']:
 r=c.get(url);assert r.status_code==200,(url,r.status_code)
"""
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((root / "data").exists())
            self.assertFalse((root / "local_data").exists())
