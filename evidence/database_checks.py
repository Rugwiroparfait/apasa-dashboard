"""Explicit DB integration suite: run with PostgreSQL or apasa.test_settings."""
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, IntegrityError, transaction
from django.test import TestCase, override_settings
from .models import Crop, PolicyNode, DatasetVersion, SourceRecord, Observation


class DatabaseImportTests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.output=Path(self.temp.name)

    def import_data(self):
        out=io.StringIO()
        call_command('import_public_evidence',output=self.output,stdout=out)
        return out.getvalue()

    def test_atomic_idempotent_import_and_provenance(self):
        self.import_data()
        self.assertEqual(DatasetVersion.objects.count(),2)
        self.assertEqual(SourceRecord.objects.count(),1926)
        self.assertEqual(Observation.objects.count(),2358)
        self.assertIn('already imported',self.import_data())
        self.assertEqual(SourceRecord.objects.count(),1926)
        record=SourceRecord.objects.filter(dataset__slug='sas_2026_b_district').first()
        obs=record.observations.get()
        self.assertEqual(obs.value_text,record.original['value'])
        self.assertEqual(obs.source_reference,record.original['worksheet']+'!'+record.original['cell_reference'])
        self.assertTrue(record.dataset.source_urls)
        self.assertTrue(record.dataset.imported_at)
        self.assertEqual(record.dataset.source_sha256,record.dataset.manifest['datasets'][1]['source_sha256'])
        self.assertTrue(Observation.objects.filter(value_state='blank',value_text='').exists())
        self.assertTrue(Observation.objects.filter(value_state='numeric_zero',value_text='0').exists())

    def test_curated_relations_and_uncertain_mappings(self):
        self.import_data()
        variants=SourceRecord.objects.filter(policy_label_raw__in=['Outcome 1.1','Outcome 1.1: MODERNIZED CROP PRODUCTION AND PRODUCTIVITY'])
        self.assertEqual(variants.values('policy_node_id').distinct().count(),1)
        self.assertEqual(PolicyNode.objects.count(),21)
        self.assertEqual(Crop.objects.get(pk='maize').kind,'individual')
        self.assertEqual(Crop.objects.get(pk='cereals').kind,'group')
        self.assertFalse(SourceRecord.objects.filter(crop_label_raw='Rice',crop__isnull=False).exists())
        self.assertTrue(SourceRecord.objects.filter(crop_label_raw='Rice',crop_mapping_status='review').exists())
        with self.assertRaises(IntegrityError),transaction.atomic():
            Crop.objects.create(code='invalid',name='invalid',kind='household')

    def test_database_pages_do_not_open_source_csvs(self):
        self.import_data()
        with override_settings(PUBLIC_EVIDENCE_MODE='database'):
            with patch('evidence.policy_data.load_policy_evidence',side_effect=AssertionError('CSV read')),patch('evidence.district_data.load_district_statistics',side_effect=AssertionError('CSV read')):
                for url in ['/national-policy-evidence/?record=1','/district-crop-statistics/?province=1&district=11&crop=maize',
                            '/national-policy-evidence/crop/?record=1','/national-policy-evidence/note/?record=11&mock=1']:
                    r=self.client.get(url);self.assertEqual(r.status_code,200)
                self.assertContains(self.client.get('/national-policy-evidence/?record=1'),'122370.3260885097')

    def test_failure_rolls_back_entire_import(self):
        with patch.object(Observation.objects,'bulk_create',side_effect=DatabaseError('simulated failure')):
            with self.assertRaises(CommandError):self.import_data()
        self.assertEqual(DatasetVersion.objects.count(),0)
        self.assertEqual(SourceRecord.objects.count(),0)
        self.assertEqual(Observation.objects.count(),0)
        self.assertEqual(Crop.objects.count(),0)

    def test_database_constraints_preserve_unique_records(self):
        self.import_data()
        record=SourceRecord.objects.first()
        with self.assertRaises(IntegrityError),transaction.atomic():
            SourceRecord.objects.create(dataset=record.dataset,key=record.key,original={},crop_label_raw='')
        version=record.dataset
        with self.assertRaises(IntegrityError),transaction.atomic():
            DatasetVersion.objects.create(fingerprint='f'*64,slug=version.slug,active=True)

    def test_new_transform_retains_history_and_only_one_active_version(self):
        self.import_data()
        original_ids=set(DatasetVersion.objects.values_list('pk',flat=True))
        with patch('evidence.normalization.TRANSFORM_VERSION','test-next-transform'):
            self.import_data()
        self.assertEqual(DatasetVersion.objects.count(),4)
        self.assertEqual(DatasetVersion.objects.filter(active=True).count(),2)
        self.assertEqual(DatasetVersion.objects.filter(pk__in=original_ids,active=False).count(),2)
        self.assertEqual(SourceRecord.objects.count(),3852)
        self.import_data()
        self.assertEqual(set(DatasetVersion.objects.filter(active=True).values_list('pk',flat=True)),original_ids)
        self.assertEqual(SourceRecord.objects.count(),3852)
