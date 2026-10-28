from django.test import override_settings
from django.conf import settings as test_settings

from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from django.conf import settings
from django.test import SimpleTestCase, override_settings
from django.urls import reverse


class EntryParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.article = None
        self.entries = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article":
            self.article = attrs.get("aria-labelledby")
            self.entries[self.article] = {"links": [], "text": ""}
        if tag == "a" and self.article:
            self.entries[self.article]["links"].append(attrs.get("href"))

    def handle_data(self, data):
        if self.article:
            self.entries[self.article]["text"] += data + " "

    def handle_endtag(self, tag):
        if tag == "article":
            self.article = None


@override_settings(
    MIDDLEWARE=[
        m
        for m in test_settings.MIDDLEWARE
        if m != "accounts.middleware.WorkspaceAuthenticationMiddleware"
    ]
)
class HomeJourneyTests(SimpleTestCase):
    def test_home_entries_and_source_boundaries(self):
        response = self.client.get(reverse("evidence:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "evidence/home.html")
        parser = EntryParser()
        parser.feed(response.content.decode())
        expected = {
            "national-heading": (
                "policy",
                [
                    "PSTA5",
                    "National policymaker",
                    "no reviewed target/actual pairing is directly comparable",
                ],
            ),
            "district-heading": (
                "district-statistics",
                [
                    "NISR SAS",
                    "District agriculture officer",
                    "programme delivery, farmer eligibility or district target attainment",
                ],
            ),
            "ahs-heading": (
                "pilot",
                [
                    "AHS 2024 Section 3_4",
                    "survey records",
                    "not official district estimates or national production",
                ],
            ),
        }
        self.assertEqual(set(parser.entries), set(expected))
        for heading, (route, texts) in expected.items():
            entry = parser.entries[heading]
            self.assertEqual(entry["links"], [reverse("evidence:" + route)])
            for text in texts + ["For ", "Your task:", "What it tells you:", "Limit:"]:
                self.assertIn(text, entry["text"])
        self.assertContains(response, "Separate survey research")
        self.assertContains(response, 'name="viewport"')
        self.assertContains(response, 'href="#main"')
        self.assertEqual(self.client.post(reverse("evidence:home")).status_code, 405)

    def test_home_runs_in_fresh_process_without_any_datasets(self):
        with tempfile.TemporaryDirectory(prefix="apasa-home-only-") as temp:
            root = Path(temp)
            for package in ["apasa", "evidence", "accounts"]:
                shutil.copytree(
                    settings.BASE_DIR / package,
                    root / package,
                    ignore=shutil.ignore_patterns("__pycache__"),
                )
            for folder in ["data", "local_data", "outputs", "docs"]:
                self.assertFalse((root / folder).exists())
            code = "import os;os.environ['DJANGO_SETTINGS_MODULE']='apasa.settings';import django;django.setup();from django.conf import settings;settings.MIDDLEWARE=[m for m in settings.MIDDLEWARE if m != 'accounts.middleware.WorkspaceAuthenticationMiddleware'];from django.test import Client;r=Client(HTTP_HOST='localhost').get('/workspace/overview/');assert r.status_code==200,r.status_code;assert b'Choose the evidence' in r.content"
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_navigation_returns_home_from_existing_pages(self):
        for route in ["policy", "district-statistics", "pilot"]:
            response = self.client.get(reverse("evidence:" + route))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'href="/"')
            self.assertContains(response, "Home</a>")
