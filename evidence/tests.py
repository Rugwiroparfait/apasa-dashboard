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
from .public_data import FIGURES


@override_settings(
    MIDDLEWARE=[
        m
        for m in test_settings.MIDDLEWARE
        if m != "accounts.middleware.WorkspaceAuthenticationMiddleware"
    ]
)
class PublicEvidenceTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="apasa-django-public-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        paths = ["docs/day3_findings.md", "outputs/day3/maize_overall_summary.csv"]
        paths += ["outputs/day3/figures/" + name for name in FIGURES.values()]
        for name in paths:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(settings.BASE_DIR / name, target)
        self.override = override_settings(PUBLIC_EVIDENCE_ROOT=self.root)
        self.override.enable()
        self.addCleanup(self.override.disable)

    def test_page_matches_public_aggregates(self):
        response = self.client.get("/evidence/maize/")
        self.assertEqual(response.status_code, 200)
        with (self.root / "outputs/day3/maize_overall_summary.csv").open() as f:
            raw = next(csv.DictReader(f))
        for key in [
            "records",
            "harvest_nonmissing",
            "harvest_missing",
            "reported_zero",
            "flagged_gt_5000",
            "median_kg",
            "mean_kg",
        ]:
            self.assertEqual(float(response.context["full"][key]), float(raw[key]))
        for text in [
            "9,017",
            "8,908",
            "92.12 kg",
            "30 kg",
            "215",
            "109",
            "not national estimates",
            "do not establish cause and effect",
            "PSU",
            "No crop-specific yield",
        ]:
            self.assertContains(response, text)
        self.assertEqual(
            [
                (g["records"], g["observed"], g["missing"], g["median"])
                for g in response.context["seed"]
            ],
            [(3564, 3555, 9, 15), (5311, 5300, 11, 40)],
        )

    def test_sensitivity_changes_only_selected_summary(self):
        r = self.client.get("/evidence/maize/?scenario=review_sensitivity_le_5000")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["selected"]["records"], 9012)
        self.assertEqual(r.context["selected"]["harvest_nonmissing"], 8903)
        self.assertEqual(format(r.context["selected"]["mean_kg"], ".2f"), "86.91")
        self.assertEqual(r.context["full"]["records"], 9017)
        self.assertEqual([g["median"] for g in r.context["seed"]], [15, 40])

    def test_only_approved_assets_and_download_are_served(self):
        for filename in FIGURES.values():
            r = self.client.get("/evidence/figures/" + filename + "/")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(
                b"".join(r.streaming_content),
                (self.root / "outputs/day3/figures" / filename).read_bytes(),
            )
        r = self.client.get("/evidence/maize/summary.csv")
        self.assertEqual(
            b"".join(r.streaming_content),
            (self.root / "outputs/day3/maize_overall_summary.csv").read_bytes(),
        )
        for url in [
            "/evidence/figures/maize_support_summary.csv/",
            "/data/private.dta",
            "/local_data/section3_4/section3_4_plot_crop_slots.csv",
            "/evidence/maize/?scenario=unknown",
            "/evidence/maize/?chart=secret.png",
        ]:
            self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post("/evidence/maize/").status_code, 405)

    def test_invalid_public_input_fails_closed(self):
        p = self.root / "outputs/day3/maize_overall_summary.csv"
        p.write_text(p.read_text().replace("9017,9017,8908", "9018,9017,8908"))
        self.assertEqual(self.client.get("/evidence/maize/").status_code, 503)

    def test_fresh_process_starts_from_public_files_only(self):
        for package in ["apasa", "evidence", "accounts"]:
            shutil.copytree(
                settings.BASE_DIR / package,
                self.root / package,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
        shutil.copyfile(settings.BASE_DIR / "manage.py", self.root / "manage.py")
        self.assertFalse((self.root / "data").exists())
        self.assertFalse((self.root / "local_data").exists())
        self.assertFalse((self.root / "app.py").exists())
        code = "import os; os.environ['DJANGO_SETTINGS_MODULE']='apasa.settings'; import django; django.setup(); from django.conf import settings;settings.MIDDLEWARE=[m for m in settings.MIDDLEWARE if m != 'accounts.middleware.WorkspaceAuthenticationMiddleware'];from django.test import Client; r=Client(HTTP_HOST='localhost').get('/evidence/maize/'); assert r.status_code==200,r.status_code; assert b'9,017' in r.content; print('public-only startup passed')"
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
