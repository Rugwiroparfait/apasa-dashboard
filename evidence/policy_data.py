"""National evidence is transcribed from Day 6 only; never aggregate districts."""

import csv
import re
from pathlib import Path

DATA_PATH = Path("docs/day6_indicator_comparability.csv")
STATUSES = ("Context only", "Not currently comparable")
SEASONS = (
    ("annual_2025_season_a_actual", "2025 Season A (September 2024–February 2025)"),
    ("annual_2025_season_b_actual", "2025 Season B (March–June 2025)"),
    ("annual_2025_season_c_actual", "2025 Season C (July–September 2025)"),
)


def source_value(text):
    """Keep source strings verbatim, including ambiguous or missing references."""
    review = bool(text and not re.fullmatch(r"-?\d+(?:\.\d+)?", text))
    return {"value": text, "review": review}


def load_policy_evidence(root):
    with (Path(root) / DATA_PATH).open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return prepare_policy_rows(rows)


def prepare_policy_rows(rows):
    from .curation import annotate

    if len(rows) != 126 or any(r["comparability_status"] not in STATUSES for r in rows):
        raise ValueError("Unexpected Day 6 coverage or status")
    if sum(r["comparability_status"] == "Context only" for r in rows) != 18:
        raise ValueError("Unexpected Day 6 classifications")
    for index, r in enumerate(rows, 1):
        r["key"] = str(index)
        r["references"] = [
            dict(
                label="Baseline",
                period=r["baseline_year"],
                **source_value(r["baseline_value"])
            ),
            dict(
                label="Separate target reference",
                period="2025/26",
                **source_value(r["target_2025_26_reference"])
            ),
            dict(
                label="Final target",
                period=r["target_year"],
                **source_value(r["target_value"])
            ),
        ]
        r["actual"] = source_value(r["official_actual_value"])
        r["seasons"] = [
            dict(period=period, **source_value(r[field])) for field, period in SEASONS
        ]
    return annotate(rows, "policy")
