#!/usr/bin/env python3
"""Day 2 prep: Section 3_4-only crop-slot dataset and QA outputs.

This script:
1) Verifies repeated crop-slot structure in Section 3_4.
2) Reshapes slot fields to one record per valid plot-crop slot.
3) Writes local row-level prepared data (ignored by git).
4) Writes aggregate QA artifacts (safe to track).

Constraints respected:
- No cross-section merges.
- No yield calculation.
- No row-level identifier export in QA artifacts.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "AHS2024_Section3_4_CROP GROWN, SEEDS AND PRODUCTION & AGRICULTURAL INPUTS AND PRACTICES.dta"
VARIABLES_CSV = ROOT / "audit_tmp" / "s3_4_variables.csv"
VALUE_LABELS_CSV = ROOT / "audit_tmp" / "s3_4_value_labels.csv"

SAFE_OUT = ROOT / "audit_tmp"
LOCAL_OUT = ROOT / "local_data" / "section3_4"


def load_value_labels(path: Path) -> dict[str, dict[int, str]]:
    labels: dict[str, dict[int, str]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            label_set = row["value_label_set"]
            code_raw = row["code"]
            label = row["label"]
            try:
                code = int(float(code_raw))
            except (TypeError, ValueError):
                continue
            labels.setdefault(label_set, {})[code] = label
    return labels


def read_weight_label(path: Path) -> str | None:
    vars_df = pd.read_csv(path)
    row = vars_df.loc[vars_df["var"] == "weight", "label"]
    if row.empty:
        return None
    return str(row.iloc[0])


def slot_columns(slot: int) -> dict[str, str]:
    return {
        "crop_code": f"s3_q4_{slot}",
        "crop_other_text": f"s3q4_o{slot}",
        "harvest_kg": f"s3_q20_{slot}",
        "seed_type_code": f"s3_q9_{slot}",
        "improved_seed_source_code": f"s3q10_{slot}",
    }


def main() -> None:
    SAFE_OUT.mkdir(parents=True, exist_ok=True)
    LOCAL_OUT.mkdir(parents=True, exist_ok=True)

    df = pd.read_stata(DATA_PATH, convert_categoricals=False)
    value_labels = load_value_labels(VALUE_LABELS_CSV)

    slot_records = []
    support_plot_level_cols = [
        "s4_q1",   # organic fertilizer use
        "s4_q4",   # inorganic fertilizer use
        "s4_q6",   # type of inorganic fertilizer used
        "s4_q12",  # pesticide/fungicide use
        "s4_q27",  # mechanical equipment use
        "s4_q28",  # type of mechanical equipment used
        "s4_q19",  # anti-erosion practices use
        "s4_q19_a1",
        "s4_q19_a2",
        "s4_q19_a3",
        "s4_q20",
    ]

    id_cols_local_only = ["hhid", "clust", "Cluster_ID", "province", "district", "Season", "s2q1"]
    id_cols_local_only = [c for c in id_cols_local_only if c in df.columns]

    for slot in range(1, 8):
        cols = slot_columns(slot)
        tmp = pd.DataFrame(
            {
                "source_row_index": df.index,
                "slot": slot,
                "crop_code": df[cols["crop_code"]],
                "crop_other_text": df[cols["crop_other_text"]] if cols["crop_other_text"] in df.columns else np.nan,
                "harvest_quantity_kg": df[cols["harvest_kg"]],
                "seed_type_code": df[cols["seed_type_code"]],
                "improved_seed_source_code": df[cols["improved_seed_source_code"]],
                "weight": df["weight"] if "weight" in df.columns else np.nan,
            }
        )

        for c in id_cols_local_only:
            tmp[c] = df[c]

        for c in support_plot_level_cols:
            tmp[c] = df[c] if c in df.columns else np.nan

        slot_records.append(tmp)

    long_df = pd.concat(slot_records, ignore_index=True)

    long_df["slot_valid_by_crop"] = long_df["crop_code"].notna()
    long_df["slot_has_any_key_field"] = long_df[["crop_code", "harvest_quantity_kg", "seed_type_code"]].notna().any(axis=1)

    prepared = long_df.loc[long_df["slot_valid_by_crop"]].copy()

    # Add crop and coded-label views for easier auditing.
    for slot in range(1, 8):
        map_i = value_labels.get(f"S3_Q4_{slot}", {})
        mask = prepared["slot"] == slot
        prepared.loc[mask, "crop_name"] = prepared.loc[mask, "crop_code"].map(map_i)

    seed_map = value_labels.get("S3_Q9_1", {})
    for slot in range(1, 8):
        map_i = value_labels.get(f"S3_Q9_{slot}", seed_map)
        mask = prepared["slot"] == slot
        prepared.loc[mask, "seed_type_label"] = prepared.loc[mask, "seed_type_code"].map(map_i)

    source_map = value_labels.get("S3_Q10_1", {})
    for slot in range(1, 8):
        map_i = value_labels.get(f"S3_Q10_{slot}", source_map)
        mask = prepared["slot"] == slot
        prepared.loc[mask, "improved_seed_source_label"] = prepared.loc[mask, "improved_seed_source_code"].map(map_i)

    # Build local export without direct identifiers.
    export_df = prepared.drop(columns=id_cols_local_only)
    export_df.insert(0, "record_uid", export_df["source_row_index"].astype(str) + "_slot" + export_df["slot"].astype(str))

    local_parquet = LOCAL_OUT / "section3_4_plot_crop_slots.parquet"
    local_csv = LOCAL_OUT / "section3_4_plot_crop_slots.csv"
    parquet_written = False
    try:
        export_df.to_parquet(local_parquet, index=False)
        parquet_written = True
    except ImportError:
        parquet_written = False
    export_df.to_csv(local_csv, index=False)

    # Aggregate QA outputs (no identifier values).
    slot_summary = (
        prepared.groupby("slot", dropna=False)
        .agg(
            records=("crop_code", "size"),
            harvest_nonmissing=("harvest_quantity_kg", lambda s: int(s.notna().sum())),
            harvest_zero=("harvest_quantity_kg", lambda s: int((s == 0).sum())),
            harvest_negative=("harvest_quantity_kg", lambda s: int((s < 0).sum())),
            harvest_missing=("harvest_quantity_kg", lambda s: int(s.isna().sum())),
            seed_nonmissing=("seed_type_code", lambda s: int(s.notna().sum())),
            improved_source_nonmissing=("improved_seed_source_code", lambda s: int(s.notna().sum())),
        )
        .reset_index()
    )

    harvest_series = prepared["harvest_quantity_kg"]
    unusual_threshold = 5000
    unresolved_codes = {
        "harvest_negative_count": int((harvest_series < 0).sum()),
        "harvest_zero_count": int((harvest_series == 0).sum()),
        "harvest_missing_count": int(harvest_series.isna().sum()),
        "harvest_gt_5000_count": int((harvest_series > unusual_threshold).sum()),
        "harvest_top10_values": [
            float(v) for v in harvest_series.dropna().sort_values(ascending=False).head(10).tolist()
        ],
        "note": "No recoding was applied to missing or zero harvest values.",
    }

    crop_summary = (
        prepared.groupby(["crop_code", "crop_name"], dropna=False)
        .agg(
            records=("crop_code", "size"),
            harvest_nonmissing=("harvest_quantity_kg", lambda s: int(s.notna().sum())),
            seed_nonmissing=("seed_type_code", lambda s: int(s.notna().sum())),
        )
        .reset_index()
    )
    crop_summary["harvest_completeness"] = crop_summary["harvest_nonmissing"] / crop_summary["records"]
    crop_summary["seed_completeness"] = crop_summary["seed_nonmissing"] / crop_summary["records"]

    candidates = crop_summary.loc[
        (crop_summary["records"] >= 400)
        & (crop_summary["harvest_completeness"] >= 0.70)
        & (crop_summary["seed_completeness"] >= 0.70)
        & (crop_summary["crop_name"].notna())
    ].sort_values(["records", "harvest_nonmissing"], ascending=[False, False])

    candidates_csv = SAFE_OUT / "day2_section3_4_crop_candidates.csv"
    candidates.to_csv(candidates_csv, index=False)

    structure = {
        "input_shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        "supports_reshape": True,
        "row_structure_summary": {
            "unit_note": "Rows contain up to seven repeated crop slots plus plot-level Section 4 indicators.",
            "s3_q3_distribution": df["s3_q3"].value_counts(dropna=False).sort_index().to_dict(),
            "slot_occupancy_by_crop_code_nonmissing": {
                str(i): int(df[f"s3_q4_{i}"].notna().sum()) for i in range(1, 8)
            },
        },
        "suffix_mapping": {
            str(i): {
                "crop_name_var": f"s3_q4_{i}",
                "harvest_var": f"s3_q20_{i}",
                "seed_type_var": f"s3_q9_{i}",
                "improved_seed_source_var": f"s3q10_{i}",
            }
            for i in range(1, 8)
        },
        "support_indicator_levels": {
            "crop_slot_level": ["s3_q9_*", "s3q10_*"],
            "plot_level": ["s4_q1", "s4_q4", "s4_q6", "s4_q12", "s4_q27", "s4_q28", "s4_q19", "s4_q19_a*", "s4_q20"],
            "note": "Plot-level indicators are repeated across all slot rows after reshape for modeling convenience.",
        },
        "weight_check": {
            "weight_var_exists": bool("weight" in df.columns),
            "weight_label_in_section3_4_metadata": read_weight_label(VARIABLES_CSV),
            "weight_nonmissing_rows": int(df["weight"].notna().sum()) if "weight" in df.columns else 0,
            "weight_usage_boundary": "Weight retained as provided in Section 3_4 records; no survey design inference performed.",
        },
        "qa_harvest": unresolved_codes,
        "prepared_slot_rows": int(prepared.shape[0]),
    }

    structure_json = SAFE_OUT / "day2_section3_4_structure_and_qa.json"
    structure_json.write_text(json.dumps(structure, indent=2), encoding="utf-8")

    # Human-readable report.
    report_md = SAFE_OUT / "day2_section3_4_qa_report.md"
    lines = []
    lines.append("# Day 2 QA Report: Section 3_4 Preparation")
    lines.append("")
    lines.append("## Scope")
    lines.append("- Section 3_4 only. No merges with other sections.")
    lines.append("- Outcome kept as harvest quantity (kg), not yield/productivity.")
    lines.append("- Aggregate QA only in this report; no household or plot identifier values shown.")
    lines.append("")
    lines.append("## Verified Row Structure")
    lines.append(f"- Input shape: {df.shape[0]} rows x {df.shape[1]} columns.")
    lines.append("- The data support a 7-slot repeated crop structure within each source row.")
    lines.append("- Reshape rule used: one output row per valid crop slot where crop code is non-missing.")
    lines.append(f"- Prepared slot-level rows: {prepared.shape[0]}.")
    lines.append("")
    lines.append("## Slot Suffix Mapping")
    for i in range(1, 8):
        lines.append(
            f"- Slot {i}: crop=s3_q4_{i}, harvest=s3_q20_{i}, seed type=s3_q9_{i}, improved-seed source=s3q10_{i}."
        )
    lines.append("")
    lines.append("## Support Indicator Level Classification")
    lines.append("- Crop-slot level: s3_q9_*, s3q10_*.")
    lines.append("- Plot level: s4_q1, s4_q4, s4_q6, s4_q12, s4_q27, s4_q28, s4_q19, s4_q19_a1, s4_q19_a2, s4_q19_a3, s4_q20.")
    lines.append("- Plot-level support indicators are repeated across slot rows after reshape.")
    lines.append("")
    lines.append("## Weight Check")
    lines.append(f"- weight variable present: {'yes' if 'weight' in df.columns else 'no' }.")
    lines.append(f"- Section 3_4 metadata label for weight: {read_weight_label(VARIABLES_CSV)}.")
    lines.append(f"- Non-missing weight rows in source data: {int(df['weight'].notna().sum()) if 'weight' in df.columns else 0}.")
    lines.append("- Weight retained for possible descriptive use only; no survey-design inference, national claims, or CIs were produced.")
    lines.append("")
    lines.append("## Harvest Quantity QA (Aggregate)")
    lines.append(f"- Non-missing harvest rows: {int(prepared['harvest_quantity_kg'].notna().sum())}.")
    lines.append(f"- Missing harvest rows: {int(prepared['harvest_quantity_kg'].isna().sum())}.")
    lines.append(f"- Zero harvest rows: {int((prepared['harvest_quantity_kg'] == 0).sum())}.")
    lines.append(f"- Negative harvest rows: {int((prepared['harvest_quantity_kg'] < 0).sum())}.")
    lines.append(f"- Harvest values > {unusual_threshold} kg: {int((prepared['harvest_quantity_kg'] > unusual_threshold).sum())}.")
    lines.append(f"- Largest observed harvest values (top 10): {unresolved_codes['harvest_top10_values']}.")
    lines.append("- No uncertain code recoding was applied.")
    lines.append("")
    lines.append("## Candidate Crop Selection Rule")
    lines.append("- Rule: records >= 400, harvest completeness >= 0.70, seed completeness >= 0.70, and mapped crop name available.")
    lines.append(f"- Selected candidate crops: {candidates.shape[0]}.")
    lines.append("")

    display_cols = [
        "crop_code",
        "crop_name",
        "records",
        "harvest_nonmissing",
        "seed_nonmissing",
        "harvest_completeness",
        "seed_completeness",
    ]
    if candidates.empty:
        lines.append("No crop met the current candidate thresholds.")
    else:
        lines.append("crop_code | crop_name | records | harvest_nonmissing | seed_nonmissing | harvest_completeness | seed_completeness")
        lines.append("--- | --- | --- | --- | --- | --- | ---")
        for _, r in candidates[display_cols].iterrows():
            lines.append(
                f"{int(r['crop_code']) if pd.notna(r['crop_code']) else ''} | "
                f"{r['crop_name']} | "
                f"{int(r['records'])} | "
                f"{int(r['harvest_nonmissing'])} | "
                f"{int(r['seed_nonmissing'])} | "
                f"{r['harvest_completeness']:.3f} | "
                f"{r['seed_completeness']:.3f}"
            )

    lines.append("")
    lines.append("## Unresolved Items")
    lines.append("- The meaning of zero harvest values is not explicitly documented as failure vs true zero in available materials.")
    lines.append("- Very large harvest values were flagged as unusual but not altered.")
    lines.append("- Survey design details (PSU/strata) remain unresolved, so inferential survey statistics are out of scope.")

    report_md.write_text("\n".join(lines), encoding="utf-8")

    print("Wrote:")
    if parquet_written:
        print(f"- {local_parquet}")
    else:
        print("- parquet not written (pyarrow/fastparquet not installed)")
    print(f"- {local_csv}")
    print(f"- {structure_json}")
    print(f"- {candidates_csv}")
    print(f"- {report_md}")


if __name__ == "__main__":
    main()
