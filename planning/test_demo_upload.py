"""The supplied demonstration exercises the real form/parser/review path."""
import io
import json
import tempfile
from pathlib import Path
from decimal import Decimal
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from .demo_upload import *
from .validation import validate_csv
from .models import SourceBatch, State
from .services import transition
from .tests import PlanningFixture
from .forms import SourceForm, IndicatorForm


class ObservationCSVTests(SimpleTestCase):
    def test_shipped_file_uses_exact_parser_contract_and_consistent_values(self):
        raw = (settings.BASE_DIR / 'data/demo' / CSV_NAME).read_bytes()
        self.assertEqual(raw, generate_csv())
        rows, errors = validate_csv(raw)
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 1536)
        self.assertTrue(all(row['is_mocked'] and not row['standard_error'] for row in rows))
        self.assertEqual(set(rows[0]), set(HEADERS))
        groups = {}
        for row in rows:
            groups.setdefault((row['geography_code'], row['crop'], row['period']), {})[row['measure']] = Decimal(row['value'])
        for (geo, crop, period), values in groups.items():
            self.assertLessEqual(values['harvested_area'], values['cultivated_area'])
            self.assertLess(abs(values['production'] - values['harvested_area'] * values['yield'] / 1000), Decimal('.0001'))
            if 'Season' not in period:
                seasonal = [groups[(geo, crop, f'{period} Season {s}')] for s in 'ABC']
                for measure in ['cultivated_area', 'harvested_area', 'production']:
                    self.assertEqual(values[measure], sum(s[measure] for s in seasonal))
        manifest = json.loads((settings.BASE_DIR / 'data/demo/observation_upload_v1.manifest.json').read_text())
        self.assertEqual(manifest, metadata(raw))

    def test_generator_is_repeatable_and_refuses_unrelated_artifacts(self):
        with tempfile.TemporaryDirectory() as folder, override_settings(BASE_DIR=Path(folder)):
            call_command('generate_observation_demo', stdout=io.StringIO())
            target = Path(folder) / 'data/demo' / CSV_NAME
            original = target.read_bytes()
            call_command('generate_observation_demo', stdout=io.StringIO())
            self.assertEqual(target.read_bytes(), original)
            target.write_text('Unrelated real data')
            with self.assertRaises(CommandError):
                call_command('generate_observation_demo', stdout=io.StringIO())
            self.assertEqual(target.read_text(), 'Unrelated real data')


class DemoUploadWorkflowTests(PlanningFixture):
    def payload(self, **changes):
        values = dict(title=TITLE, synthetic_demo='on', source_url='', origin=ORIGIN,
            source_reference=RELEASE, methodology=METHODOLOGY, aggregate_only='on',
            file=SimpleUploadedFile(CSV_NAME, generate_csv(), content_type='text/csv'))
        values.update(changes)
        return values

    def test_upload_is_demo_without_fake_url_and_cannot_be_approved(self):
        response = self.client.post(reverse('planning:upload'), self.payload())
        self.assertEqual(response.status_code, 302)
        batch = SourceBatch.objects.get(title=TITLE)
        self.assertEqual(batch.status, State.DEMO)
        self.assertTrue(batch.is_mocked)
        self.assertEqual(batch.source_url, '')
        self.assertIn(ORIGIN, batch.source_reference)
        self.assertEqual(len(batch.rows), 1536)
        page = self.client.get(response.url)
        self.assertContains(page, LABEL)
        self.assertContains(page, METHODOLOGY)
        self.assertContains(page, 'Data origin')
        with self.assertRaises(ValueError):
            transition('source', batch.pk, self.reviewer, 'approve', 'Attempt to approve demonstration data', True)
        again = self.client.post(reverse('planning:upload'), self.payload())
        self.assertEqual(again.url, response.url)
        self.assertEqual(SourceBatch.objects.filter(title=TITLE).count(), 1)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, State.APPROVED)
        self.assertFalse(self.batch.is_mocked)

    def test_real_source_requires_url_and_synthetic_requires_origin(self):
        response = self.client.post(reverse('planning:upload'), self.payload(synthetic_demo=''))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'URL is required for real evidence')
        response = self.client.post(reverse('planning:upload'), self.payload(origin=''))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Describe the synthetic data origin')
        self.assertFalse(SourceBatch.objects.filter(title=TITLE).exists())

    def test_aggregate_declaration_and_row_flags_are_enforced(self):
        response = self.client.post(reverse('planning:upload'), self.payload(aggregate_only=''))
        self.assertEqual(response.status_code, 200)
        raw = generate_csv().replace(b',true\n', b',false\n', 1)
        response = self.client.post(reverse('planning:upload'), self.payload(file=SimpleUploadedFile('mixed.csv', raw)))
        self.assertEqual(response.status_code, 302)
        batch = SourceBatch.objects.get(title=TITLE)
        self.assertEqual(batch.status, State.QUARANTINED)
        self.assertTrue(batch.is_mocked)
        self.assertEqual(batch.rows, [])
        self.assertTrue(batch.errors)

    def test_target_url_exemption_applies_only_to_synthetic_targets(self):
        data = {field: getattr(self.indicator, field) for field in IndicatorForm._meta.fields}
        data['code'] = 'DEMO-UPLOAD-URL-TEST'
        data['source_url'] = ''
        data['is_mocked'] = True
        self.assertTrue(IndicatorForm(data=data).is_valid())
        data['is_mocked'] = False
        self.assertFalse(IndicatorForm(data=data).is_valid())
