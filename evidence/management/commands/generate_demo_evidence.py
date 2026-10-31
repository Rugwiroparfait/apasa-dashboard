"""Export only the deterministic demonstration fixture; never touch published data."""
import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from evidence.demo_data import district_examples, GENERATED_ON, VERSION, LABEL


class Command(BaseCommand):
    help = "Export the repeatable synthetic district fixture under data/demo; no database writes."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="data/demo/district_statistics.json")

    def handle(self, *args, **options):
        root = (settings.BASE_DIR / "data/demo").resolve()
        output = (settings.BASE_DIR / Path(options["output"])).resolve()
        if not output.is_relative_to(root) or output.suffix != ".json" or output.name in {"manifest.json"}:
            raise CommandError("Output must be a demo JSON fixture within data/demo, not the manifest or published data.")
        if output.exists():
            try:
                old = json.loads(output.read_text())
                if old.get("dataset_id") != VERSION or old.get("classification") != LABEL or not all(r.get("is_mocked") is True for r in old["rows"]):
                    raise ValueError()
            except (ValueError, KeyError, AttributeError, TypeError):
                raise CommandError("Refusing to replace a file that is not this synthetic demo dataset.")
        payload = dict(dataset_id=VERSION, generation_date=GENERATED_ON, classification=LABEL, rows=district_examples())
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.stdout.write(f"108 synthetic aggregate records exported to {output}. No published data or database records changed.")
