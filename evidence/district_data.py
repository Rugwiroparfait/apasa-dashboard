"""Read only the published Day 7 aggregate CSV. No AHS or reference inputs."""

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

DATA_PATH = Path("outputs/day7/official_sas_2026_b_district.csv")
MEASURES = {
    "cultivated_crop_area": ("Cultivated crop area", "hectares", "Ha", "Table 9"),
    "harvested_crop_area": ("Harvested crop area", "hectares", "Ha", "Table 10"),
    "average_crop_yield": (
        "Average crop yield",
        "kilograms per hectare",
        "Kg/Ha",
        "Table 11",
    ),
    "crop_production": ("Crop production", "metric tonnes", "MT", "Table 13"),
}
# Display-only equivalence, explicitly documented. Never modify the source CSV.
DISPLAY_CROP = {"Cooking Banana": "Cooking banana"}
STATES = {
    "numeric",
    "numeric_zero",
    "blank",
    "empty_text",
    "NA",
    "dash",
    "unresolved_text",
    "unresolved_nonfinite",
}


def load_district_statistics(root):
    with (Path(root) / DATA_PATH).open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 1800:
        raise ValueError("Unexpected Day 7 coverage")
    keys = set()
    parents = {}
    provinces = {}
    for r in rows:
        if r["measure"] not in MEASURES:
            raise ValueError("Unknown measure")
        title, unit, source_unit, table = MEASURES[r["measure"]]
        if (
            r["unit"] != source_unit
            or r["worksheet"] != table
            or r["season"] != "2026 B"
            or r["reference_period"] != "March-June 2026"
            or r["geography_level"] != "district"
            or r["source_agency"] != "NISR"
            or r["district_mapping_status"] != "exact"
        ):
            raise ValueError("Unsupported source metadata")
        if not all(
            r[k] for k in ["province", "province_id", "district", "district_id"]
        ):
            raise ValueError("Unresolved geography")
        district = (r["district"], r["province_id"], r["province"])
        if parents.setdefault(r["district_id"], district) != district:
            raise ValueError("Conflicting district parent")
        if provinces.setdefault(r["province_id"], r["province"]) != r["province"]:
            raise ValueError("Conflicting province name")
        crop = DISPLAY_CROP.get(r["crop_sas_label"], r["crop_sas_label"])
        key = (r["district_id"], crop, r["measure"])
        if key in keys:
            raise ValueError("Duplicate display crop/measure")
        keys.add(key)
        state = r["source_value_status"]
        if state not in STATES:
            raise ValueError("Unknown source state")
        if state in ["numeric", "numeric_zero"]:
            try:
                number = Decimal(r["value"])
            except InvalidOperation as exc:
                raise ValueError("Invalid numeric source") from exc
            if not number.is_finite() or ((number == 0) != (state == "numeric_zero")):
                raise ValueError("Inconsistent numeric state")
            display = r["value"] + (
                " — reported zero" if state == "numeric_zero" else ""
            )
        else:
            if r["value"] != "":
                raise ValueError("Missing state contains numeric value")
            display = "Unavailable — " + (
                "blank in source" if state == "blank" else state + " in source"
            )
        r.update(
            display_crop=crop, title=title, display_unit=unit, value_display=display
        )
    if len(parents) != 30 or len(provinces) != 5:
        raise ValueError("Unexpected geography coverage")
    for district_id in parents:
        selected = [r for r in rows if r["district_id"] == district_id]
        if len({r["display_crop"] for r in selected}) != 15 or len(selected) != 60:
            raise ValueError("Incomplete district crop coverage")
    return rows
