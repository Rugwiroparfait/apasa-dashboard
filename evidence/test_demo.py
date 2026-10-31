"""Demonstrations remain deterministic, separate and honestly labelled."""
import io
import json
import tempfile
from decimal import Decimal
from pathlib import Path
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings
from .demo_data import district_examples, LABEL


@override_settings(MIDDLEWARE=[m for m in settings.MIDDLEWARE if m != "accounts.middleware.WorkspaceAuthenticationMiddleware"])
class DistrictDemoTests(SimpleTestCase):
    def test_deterministic_aggregate_arithmetic_and_provenance(self):
        rows = district_examples()
        self.assertEqual(rows, district_examples())
        self.assertEqual(len(rows), 108)
        for row in rows:
            self.assertTrue(row["is_mocked"])
            self.assertEqual(row["source_report"], "")
            self.assertEqual(row["source_workbook_url"], "")
            self.assertEqual(row["source_agency"], "")
            if row["measure"] == "crop_production" and row["value"] != "":
                group = {r["measure"]: r for r in rows if (r["district_id"], r["crop_code"], r["season"]) == (row["district_id"], row["crop_code"], row["season"])}
                expected = Decimal(group["harvested_crop_area"]["value"]) * Decimal(group["average_crop_yield"]["value"]) / 1000
                self.assertEqual(Decimal(row["value"]), expected)
        self.assertEqual(sum(r["source_value_status"] == "blank" for r in rows), 2)
        self.assertEqual(sum(r["source_value_status"] == "numeric_zero" for r in rows), 2)

    def test_synthetic_journey_filters_periods_and_sources(self):
        response = self.client.get('/district-crop-statistics/', dict(data="demo", province="1", district="11", crop="Maize", period="2025 B", chart_measure="average_crop_yield"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, LABEL)
        self.assertContains(response, "Data origin")
        self.assertContains(response, "not official NISR or MINAGRI statistics")
        self.assertNotContains(response, '>NISR report</a>')
        self.assertNotContains(response, 'Source: NISR')
        self.assertEqual(len(response.context["selected"]), 4)
        self.assertEqual(len(response.context["periods"]), 3)
        self.assertEqual(len(response.context["history_chart"]["bars"]), 3)
        self.assertTrue(response.context["chart"]["has_mock"])
        self.assertEqual(response.context["period"], "2025 B")

    def test_missing_and_zero_remain_distinct_in_period_charts(self):
        response = self.client.get('/district-crop-statistics/', dict(data="demo", province="1", district="11", crop="Cassava", period="2025 B", chart_measure="crop_production"))
        bar = response.context["history_chart"]["bars"][0]
        self.assertTrue(bar["available"])
        self.assertTrue(bar["zero"])
        response = self.client.get('/district-crop-statistics/', dict(data="demo", province="2", district="24", crop="Bush bean", period="2026 A", chart_measure="crop_production"))
        bar = response.context["history_chart"]["bars"][1]
        self.assertFalse(bar["available"])
        self.assertFalse(bar["zero"])

    def test_published_mode_never_supplies_synthetic_periods(self):
        response = self.client.get('/district-crop-statistics/', dict(province="1", district="11", crop="Maize"))
        self.assertFalse(response.context["demo_active"])
        self.assertIsNone(response.context["history_chart"])
        self.assertEqual([p[0] for p in response.context["periods"]], ["2026 B"])
        self.assertContains(response, '574.4233')
        self.assertContains(response, 'year or season comparison is not supported')
        self.assertEqual(self.client.get('/district-crop-statistics/', dict(period="2025 B")).status_code, 404)
        self.assertEqual(self.client.get('/district-crop-statistics/', dict(data="demo", province="1", district="24")).status_code, 404)

    def test_export_is_repeatable_and_refuses_published_or_unrelated_paths(self):
        with tempfile.TemporaryDirectory() as folder, override_settings(BASE_DIR=Path(folder)):
            call_command('generate_demo_evidence', stdout=io.StringIO())
            fixture = Path(folder) / 'data/demo/district_statistics.json'
            first = fixture.read_bytes()
            call_command('generate_demo_evidence', stdout=io.StringIO())
            self.assertEqual(first, fixture.read_bytes())
            self.assertEqual(len(json.loads(first)["rows"]), 108)
            with self.assertRaises(CommandError):
                call_command('generate_demo_evidence', output='outputs/published.json', stdout=io.StringIO())
            with self.assertRaises(CommandError):
                call_command('generate_demo_evidence', output='data/demo/manifest.json', stdout=io.StringIO())
            fixture.write_text('{"published":true}')
            with self.assertRaises(CommandError):
                call_command('generate_demo_evidence', stdout=io.StringIO())
            self.assertEqual(fixture.read_text(), '{"published":true}')

    def test_mode_switch_preserves_compatible_place_and_clears_unavailable_crop(self):
        from urllib.parse import parse_qs
        response = self.client.get('/district-crop-statistics/', dict(province='2', district='24', crop='Maize'))
        parameters = parse_qs(response.context['demo_url'].lstrip('?'))
        self.assertEqual(parameters['district'], ['24'])
        self.assertEqual(parameters['period'], ['2026 B'])
        self.assertEqual(parameters['data'], ['demo'])
        demo = self.client.get('/district-crop-statistics/' + response.context['demo_url'])
        self.assertEqual(demo.status_code, 200)
        real = self.client.get('/district-crop-statistics/' + demo.context['published_url'])
        self.assertEqual(real.status_code, 200)
        self.assertEqual(real.context['district_id'], '24')

    def test_demo_uses_one_compact_label_and_keeps_origin_expandable(self):
        response = self.client.get('/district-crop-statistics/', dict(data='demo', province='1', district='11', crop='Maize'))
        self.assertContains(response, 'class="data-label"', count=1)
        self.assertNotContains(response, 'demo-mode-notice')
        self.assertContains(response, 'Data origin &amp; details')
