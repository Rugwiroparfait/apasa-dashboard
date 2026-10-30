"""Validate shipped evidence without raw Excel inputs or database writes."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from evidence.policy_data import load_policy_evidence
from evidence.district_data import load_district_statistics
from evidence.workbook_data import load_bundle


class Command(BaseCommand):
    help = "Verify policy/district evidence and the national workbook bundle before release."

    def handle(self, *args, **options):
        try:
            root = settings.PUBLIC_EVIDENCE_ROOT
            policy = load_policy_evidence(root)
            district = load_district_statistics(root)
            load_bundle.cache_clear()
            bundle = load_bundle(str(root))
            observations = bundle["observations"]
            if not observations:
                raise ValueError("Empty national observation bundle")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise CommandError(
                "Packaged evidence validation failed; restore the reviewed release files."
            ) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Packaged evidence verified: {len(policy)} policy records; "
                f"{len(district)} district records; {len(observations)} national workbook entries. "
                "No raw workbooks or mocked replacements required."
            )
        )
