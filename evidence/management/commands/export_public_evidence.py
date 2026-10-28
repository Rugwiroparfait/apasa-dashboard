from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from evidence.normalization import export_bundle


class Command(BaseCommand):
    help = "Export only checksum-approved public policy and district aggregate CSVs."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--output", type=Path, default=None)

    def handle(self, *args, **options):
        try:
            target, manifest = export_bundle(
                settings.PUBLIC_EVIDENCE_ROOT,
                options["output"] or settings.BASE_DIR / "outputs/public_evidence",
            )
        except (OSError, ValueError, KeyError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(str(target))
        self.stdout.write(
            "Records: " + str(sum(d["record_count"] for d in manifest["datasets"]))
        )
