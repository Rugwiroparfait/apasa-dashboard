"""Write one validated synthetic upload CSV, never load or publish database rows."""
import json
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from planning.demo_upload import CSV_NAME, generate_csv, metadata
from planning.validation import fingerprint


class Command(BaseCommand):
    help = "Generate the validated synthetic observation-upload CSV under data/demo; no database writes."

    def handle(self, *args, **options):
        target = settings.BASE_DIR / "data/demo" / CSV_NAME
        raw = generate_csv()
        if target.resolve().parent != (settings.BASE_DIR / "data/demo").resolve():
            raise CommandError("Refusing a CSV path outside the demo directory.")
        manifest = target.with_name("observation_upload_v1.manifest.json")
        payload = (json.dumps(metadata(raw), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        for path, content in [(target, raw), (manifest, payload)]:
            if path.resolve().parent != target.parent.resolve() or (path.exists() and path.read_bytes() != content):
                raise CommandError("Refusing to overwrite a different file. Preserve it before regenerating this named demo artifact.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        manifest.write_bytes(payload)
        self.stdout.write(f"{target}\n1,536 validated synthetic aggregates; SHA-256 {fingerprint(raw)}. No database records loaded or published.")
