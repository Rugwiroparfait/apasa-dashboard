"""Create a deterministic, source-linked seasonal bundle from the uploaded audit.

Only exact national production/yield tables and farmer-adoption blocks are
selected. Comparative columns and older annual workbooks remain in the audit.
"""

import csv
import hashlib
import json
import re
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Command(BaseCommand):
    help = "Verify uploaded workbook hashes and export seasonal observations without editing sources."

    def handle(self, *args, **options):
        root = Path(settings.BASE_DIR)
        review = root / "outputs/workbook_review_2026_10_28"
        manifest = json.loads((review / "input_manifest.json").read_text())["after"]
        for path, expected in manifest.items():
            if sha(root / path) != expected:
                raise CommandError(f"Source checksum mismatch: {path}")
        sheets = json.loads((review / "source_cells.json").read_text())
        observations = []
        for sheet in sheets:
            workbook = sheet["source_workbook"]
            if not workbook.startswith("Tables_"):
                continue
            cells = {c["cell"]: c for c in sheet["cells"]}
            title = " ".join(
                str(c["cached_value"]) for c in sheet["cells"] if c["row"] <= 3
            )
            period_match = re.search(r"(202[456]) Season ([AB])", title)
            if not period_match:
                continue
            year, season = period_match.groups()
            period = f"{year} Season {season}"
            current_header = f"{year} {season}"

            def emit(cell, indicator, crop, unit, population):
                item = cells.get(cell)
                value = item["cached_value"] if item else None
                state = (
                    "observed"
                    if isinstance(value, (int, float)) and not isinstance(value, bool)
                    else "unavailable"
                )
                observations.append(
                    dict(
                        period=period,
                        indicator=indicator,
                        crop=crop,
                        unit=unit,
                        population=population,
                        geography="Rwanda",
                        value=str(value) if value is not None else "",
                        status=state,
                        source_workbook=workbook,
                        source_sheet=sheet["sheet"],
                        source_cell=cell,
                        source_sha256=manifest["data/" + workbook],
                        source_title=title,
                        formula=item["value"] if item and item["type"] == "f" else "",
                        mocked=False,
                    )
                )

            if (
                "cultivated area, harvested area, production and yield by crop"
                in title.lower()
            ):
                for label, indicator, unit in [
                    ("Production (MT)", "production", "MT"),
                    ("Yield (MT/ha)", "yield", "MT/ha"),
                ]:
                    headers = [
                        c
                        for c in sheet["cells"]
                        if c["row"] == 3 and str(c["cached_value"]).strip() == label
                    ]
                    if len(headers) != 1:
                        raise CommandError(
                            f"Unexpected measure header: {workbook} {label}"
                        )
                    header = headers[0]
                    column = header["cell"][:-1]
                    if (
                        str(cells.get(column + "4", {}).get("cached_value", "")).strip()
                        != current_header
                    ):
                        raise CommandError(f"Unexpected season column: {workbook}")
                    for c in sheet["cells"]:
                        crop = str(c["cached_value"]).strip()
                        if (
                            c["col"] == 2
                            and 5 <= c["row"] <= 31
                            and crop
                            and crop.lower() != "total"
                        ):
                            emit(
                                f'{column}{c["row"]}',
                                indicator,
                                crop,
                                unit,
                                "All farmer types; crop/group as published",
                            )
            # Farmer percentages, never plot/land percentages or seed-source shares.
            adoption = None
            if "use of seeds by farmer type per district" in title.lower():
                adoption = "improved_seeds"
            elif (
                "use of inorganic fertilizer by farmer type per district"
                in title.lower()
            ):
                adoption = "inorganic_fertilizer"
            if adoption:
                totals = [
                    c
                    for c in sheet["cells"]
                    if c["col"] == 2
                    and str(c["cached_value"]).strip().lower() in {"national", "total"}
                ]
                if len(totals) != 1:
                    raise CommandError(
                        f'National total not unique: {workbook} {sheet["sheet"]}'
                    )
                # Assert the population headers belong to the first (farmer) block.
                for column, population in [("D", "SSF"), ("E", "LSF")]:
                    if not any(
                        c["col"] in {3, 4, 5}
                        and "percentage of farmers" in str(c["cached_value"]).lower()
                        for c in sheet["cells"]
                        if c["row"] <= 5
                    ):
                        raise CommandError("Farmer denominator not verified")
                    if not any(
                        c["cell"].startswith(column)
                        and c["row"] <= 5
                        and str(c["cached_value"]).strip() == population
                        for c in sheet["cells"]
                    ):
                        raise CommandError("Population header not verified")
                    emit(
                        f'{column}{totals[0]["row"]}',
                        adoption,
                        "All crops",
                        "% of farmers",
                        population,
                    )
        with (review / "register_fields_for_review.csv").open(
            encoding="utf-8-sig", newline=""
        ) as stream:
            register = list(csv.DictReader(stream))
        if len(register) != 30 or not observations:
            raise CommandError("Incomplete workbook coverage")
        bundle = {
            "schema_version": 1,
            "source_hashes": manifest,
            "audit_sha256": sha(review / "source_cells.json"),
            "limitations": "Register targets are unverified policy references. Seasons are separate; no annual aggregation, target attainment, or inferred historical trend. Older annual workbooks remain review-only.",
            "register": register,
            "observations": observations,
        }
        output = root / "outputs/workbook_observations"
        output.mkdir(exist_ok=True)
        encoded = (
            json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode()
        (output / "evidence.json").write_bytes(encoded)
        (output / "evidence.sha256").write_text(
            hashlib.sha256(encoded).hexdigest() + "\n"
        )
        self.stdout.write(
            f"{len(observations)} source observations; {len(register)} register entries; checksum verified inputs unchanged."
        )
