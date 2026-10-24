import csv
import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction, DatabaseError
from evidence.models import Crop, PolicyNode, DatasetVersion, SourceRecord, Observation
from evidence.normalization import export_bundle


class Command(BaseCommand):
    help = 'Atomically import checksum-approved public evidence; repeated imports are idempotent.'
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument('--output', type=Path, default=None)

    def handle(self, *args, **options):
        if connection.vendor not in ['postgresql', 'sqlite']:
            raise CommandError('Configure PostgreSQL first. CSV export/startup does not need a database.')
        if connection.vendor == 'sqlite' and not getattr(settings, 'PUBLIC_EVIDENCE_TEST_DATABASE', False):
            raise CommandError('SQLite import is reserved for the explicit test settings.')
        try:
            target, manifest = export_bundle(settings.PUBLIC_EVIDENCE_ROOT,
                options['output'] or settings.BASE_DIR/'outputs/public_evidence')
            def read(name):
                with (target/name).open(newline='', encoding='utf-8') as f: return list(csv.DictReader(f))
            records, observations = read('source_records.csv'), read('observations.csv')
            counts = []
            with transaction.atomic():
                for row in read('curated_crops.csv'):
                    Crop.objects.update_or_create(code=row['code'], defaults={k:v for k,v in row.items() if k!='code'})
                for row in read('curated_policy_nodes.csv'):
                    PolicyNode.objects.update_or_create(code=row['code'],defaults={k:v for k,v in row.items() if k!='code'})
                for d in manifest['datasets']:
                    existing = DatasetVersion.objects.filter(pk=d['fingerprint']).first()
                    if existing:
                        DatasetVersion.objects.filter(slug=d['slug'],active=True).exclude(pk=existing.pk).update(active=False)
                        if not existing.active: existing.active=True;existing.save(update_fields=['active'])
                        counts.append((d['slug'],'already imported'));continue
                    version = DatasetVersion.objects.create(fingerprint=d['fingerprint'],slug=d['slug'],
                        source_path=d['path'],source_sha256=d['source_sha256'],
                        registry_sha256=d['registry_sha256'],transform_version=d['transform_version'],
                        source_label=d['label'],source_urls=d['source_urls'],manifest=manifest,active=False)
                    objects = [SourceRecord(dataset=version,key=r['key'],crop_id=r['crop_code'] or None,
                        crop_label_raw=r['crop_label_raw'],crop_mapping_status=r['crop_mapping_status'],
                        policy_node_id=r['policy_code'] or None,policy_label_raw=r['policy_label_raw'],
                        original=json.loads(r['original_json'])) for r in records if r['dataset']==d['fingerprint']]
                    SourceRecord.objects.bulk_create(objects)
                    lookup={r.key:r.pk for r in version.records.all()}
                    obs=[]
                    for r in observations:
                        if r['dataset']!=d['fingerprint']:continue
                        obs.append(Observation(record_id=lookup[r['record_key']],
                            **{k:r[k] for k in ['key','kind','measure','value_text','value_state','period','unit',
                                'geography','geography_code','source_label','source_url','source_reference','source_crop_label']}))
                    Observation.objects.bulk_create(obs)
                    DatasetVersion.objects.filter(slug=d['slug'],active=True).update(active=False)
                    version.active=True;version.save(update_fields=['active'])
                    counts.append((d['slug'],str(len(objects))+' records / '+str(len(obs))+' observations'))
        except (OSError,ValueError,KeyError,DatabaseError) as exc:
            # No connection credentials or raw database error strings in console output.
            raise CommandError('Public import failed; transaction rolled back. Check source checksums, migrations and database configuration.') from exc
        for slug,status in counts:self.stdout.write(slug+': '+status)
