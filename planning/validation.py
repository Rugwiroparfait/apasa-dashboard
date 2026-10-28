"""Strict aggregate CSV contract; malformed data never enters the comparison engine."""

import csv
import hashlib
import io
import re
from decimal import Decimal, InvalidOperation

REQUIRED = {
    "measure",
    "crop",
    "value",
    "unit",
    "period",
    "geography_code",
    "geography",
    "population",
    "source_reference",
}
OPTIONAL = {"standard_error", "is_mocked"}
UNITS = {"MT", "Ha", "Kg/Ha", "MT/ha", "%", "count", "RWF"}
MEASURE_UNITS = {
    "production": {"MT"},
    "yield": {"Kg/Ha", "MT/ha"},
    "improved_seeds": {"%"},
    "inorganic_fertilizer": {"%"},
    "cultivated_area": {"Ha"},
    "harvested_area": {"Ha"},
}


def period_key(value):
    if re.fullmatch(r"20\d{2}", value):
        return ("annual", int(value))
    match = re.fullmatch(r"(20\d{2}) Season ([ABC])", value)
    if match:
        return ("Season " + match[2], int(match[1]))
    match = re.fullmatch(r"(20\d{2})/(\d{2})", value)
    if match and int(match[2]) == (int(match[1]) + 1) % 100:
        return ("fiscal", int(match[1]))
    raise ValueError(
        "Use a year (2026), a season (2026 Season B), or a fiscal year (2026/27)."
    )


def number(value, label, optional=False):
    if optional and str(value).strip() == "":
        return None
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(
            f"{label} must be a number; missing data must not be entered as zero."
        )
    if not result.is_finite() or result < 0 or result > Decimal("1e15"):
        raise ValueError(
            f"{label} must be finite, non-negative and no larger than 10^15."
        )
    return result


def validate_csv(raw):
    if len(raw) > 2 * 1024 * 1024:
        return [], ["The file exceeds the 2 MB aggregate-data limit."]
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        headers = reader.fieldnames or []
        if (
            len(headers) != len(set(headers))
            or not REQUIRED.issubset(headers)
            or set(headers) - REQUIRED - OPTIONAL
        ):
            return [], [
                "CSV columns must be: "
                + ", ".join(sorted(REQUIRED))
                + "; optional: standard_error, is_mocked. Do not upload farmer or household records."
            ]
        rows, errors, seen = [], [], set()
        for index, row in enumerate(reader, 2):
            if index > 5001:
                errors.append(
                    "A batch may contain at most 5,000 aggregate observations."
                )
                break
            try:
                if None in row or any(v is None for v in row.values()):
                    raise ValueError("The number of columns does not match the header.")
                row = {k: v.strip() for k, v in row.items()}
                if any(not row[k] for k in REQUIRED):
                    raise ValueError(
                        "Every required field must be filled; omit unavailable observations rather than inventing them."
                    )
                if any(len(v) > 1000 for v in row.values()):
                    raise ValueError("A field exceeds 1,000 characters.")
                if not re.fullmatch(r"[a-z][a-z0-9_]{0,79}", row["measure"]):
                    raise ValueError(
                        "Measure must be a stable lowercase code such as production or improved_seeds."
                    )
                if row["unit"] not in UNITS:
                    raise ValueError(
                        "Unsupported unit; use " + ", ".join(sorted(UNITS)) + "."
                    )
                if (
                    row["measure"] in MEASURE_UNITS
                    and row["unit"] not in MEASURE_UNITS[row["measure"]]
                ):
                    raise ValueError("The unit does not describe the declared measure.")
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", row["geography_code"]):
                    raise ValueError(
                        "Geography code must contain only letters, numbers, underscores or hyphens."
                    )
                period_key(row["period"])
                value = number(row["value"], "Value")
                if row["unit"] == "%" and value > 100:
                    raise ValueError("Percentages must be between 0 and 100.")
                number(row.get("standard_error", ""), "Standard error", optional=True)
                flag = row.get("is_mocked", "false").lower()
                if flag not in {"true", "false", "1", "0", ""}:
                    raise ValueError("is_mocked must be true or false.")
                row["is_mocked"] = flag in {"true", "1"}
                row.setdefault("standard_error", "")
                key = tuple(
                    (
                        ("MT/ha" if row[k] == "Kg/Ha" else row[k])
                        if k == "unit"
                        else row[k]
                    )
                    for k in [
                        "measure",
                        "crop",
                        "unit",
                        "period",
                        "geography_code",
                        "population",
                    ]
                )
                if key in seen:
                    raise ValueError(
                        "Duplicate observation dimensions and period; select one reviewed source version."
                    )
                seen.add(key)
                rows.append(row)
            except ValueError as exc:
                errors.append(f"Row {index}: {exc}")
                if len(errors) >= 30:
                    errors.append(
                        "Showing the first 30 errors; correct the file and upload a new version."
                    )
                    break
        if not rows and not errors:
            errors.append("The file contains no observations.")
        # Quarantine the whole batch, rather than silently accepting a partial file.
        return ([], errors) if errors else (rows, [])
    except (UnicodeDecodeError, csv.Error) as exc:
        return [], ["Upload a well-formed UTF-8 CSV file."]


def fingerprint(value):
    return hashlib.sha256(value).hexdigest()
