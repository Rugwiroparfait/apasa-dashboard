"""Allowlisted public CSVs -> immutable, aggregate-only import tables."""

import csv
import hashlib
import io
import json
from pathlib import Path
from decimal import Decimal, InvalidOperation
import tempfile

from .curation import REGISTRY_PATH, registry
from .policy_data import load_policy_evidence, SEASONS
from .district_data import load_district_statistics

TRANSFORM_VERSION = "public-evidence-v2"
APPROVALS_PATH = Path(__file__).with_name("public_sources.json")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode_csv(rows, fields):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")


def value_state(value):
    if value == "":
        return "blank"
    try:
        number = Decimal(value)
        if number.is_finite():
            return "numeric_zero" if number == 0 else "numeric"
    except InvalidOperation:
        pass
    return "source_text_review"


def build_tables(root):
    root = Path(root).resolve()
    approvals = json.loads(APPROVALS_PATH.read_text())
    curated, crops, nodes, aliases, policy_aliases = registry()
    registry_hash = digest(REGISTRY_PATH.read_bytes())
    records, observations, versions = [], [], []
    for entry in approvals:
        path = (root / entry["path"]).resolve()
        if not path.is_relative_to(root) or path.suffix != ".csv":
            raise ValueError(
                "Only fixed public CSV paths inside the source root are permitted"
            )
        raw = path.read_bytes()
        sha = digest(raw)
        if sha != entry["approved_sha256"]:
            raise ValueError(
                "Public source checksum changed; review and update public_sources.json before importing: "
                + entry["path"]
            )
        originals = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
        annotated = (
            load_policy_evidence(root)
            if entry["slug"] == "psta5_day6"
            else load_district_statistics(root)
        )
        if entry["slug"] == "sas_2026_b_district":
            from .curation import annotate

            annotate(annotated, "district")
        fingerprint = digest(
            (entry["slug"] + sha + registry_hash + TRANSFORM_VERSION).encode()
        )
        version = dict(
            entry,
            source_sha256=sha,
            registry_sha256=registry_hash,
            transform_version=TRANSFORM_VERSION,
            fingerprint=fingerprint,
            record_count=len(originals),
        )
        versions.append(version)
        for i, (rawrow, row) in enumerate(zip(originals, annotated), 1):
            key = f"{i:06}"
            records.append(
                dict(
                    dataset=fingerprint,
                    key=key,
                    crop_code=row["crop_code"],
                    crop_label_raw=rawrow.get("crop", rawrow.get("crop_sas_label", "")),
                    crop_mapping_status=row["crop_mapping_status"],
                    policy_code=row.get("policy_code", ""),
                    policy_label_raw=rawrow.get("outcome_output", ""),
                    original_json=json.dumps(
                        rawrow, sort_keys=True, ensure_ascii=False
                    ),
                )
            )

            def observation(
                obs_key,
                kind,
                value,
                period,
                unit,
                geography,
                source_label,
                source_url,
                reference,
                source_crop="",
                state=None,
                geography_code="",
            ):
                observations.append(
                    dict(
                        dataset=fingerprint,
                        record_key=key,
                        key=obs_key,
                        kind=kind,
                        measure=rawrow.get("measure", rawrow.get("indicator_name", "")),
                        value_text=value,
                        value_state=state or value_state(value),
                        period=period,
                        unit=unit,
                        geography=geography,
                        geography_code=geography_code,
                        source_label=source_label,
                        source_url=source_url,
                        source_reference=reference,
                        source_crop_label=source_crop,
                        crop_code=row["crop_code"],
                        crop_label_raw=records[-1]["crop_label_raw"],
                        crop_display=row["crop_display"],
                        crop_kind=row["crop_kind"],
                        crop_mapping_status=row["crop_mapping_status"],
                        policy_code=row.get("policy_code", ""),
                    )
                )

            if entry["slug"] == "psta5_day6":
                for obs_key, kind, field, period in [
                    ("baseline", "baseline", "baseline_value", rawrow["baseline_year"]),
                    ("target_2025_26", "target", "target_2025_26_reference", "2025/26"),
                    ("target_final", "target", "target_value", rawrow["target_year"]),
                ]:
                    observation(
                        obs_key,
                        kind,
                        rawrow[field],
                        period,
                        rawrow["target_unit"],
                        rawrow["target_geography"],
                        rawrow["policy_name"],
                        rawrow["policy_source_url"],
                        "Printed page " + rawrow["policy_page"],
                        rawrow["crop"],
                    )
                observation(
                    "latest_actual",
                    "official_actual",
                    rawrow["official_actual_value"],
                    rawrow["actual_year_or_period"],
                    rawrow["actual_unit"],
                    rawrow["actual_geography"],
                    rawrow["source_title"],
                    rawrow["source_url"],
                    rawrow["page_or_table"],
                    rawrow["actual_crop_label"],
                )
                # A source URL establishes these as separately recorded seasonal references.
                if rawrow["latest_annual_source_url"]:
                    for field, period in SEASONS:
                        observation(
                            field,
                            "seasonal_actual",
                            rawrow[field],
                            period,
                            rawrow["annual_actual_unit"],
                            rawrow["actual_geography"],
                            "NISR SAS 2025 annual workbook",
                            rawrow["latest_annual_source_url"],
                            rawrow["annual_table_reference"],
                            rawrow["actual_crop_label"],
                        )
            else:
                observation(
                    "published_value",
                    "district_estimate",
                    rawrow["value"],
                    rawrow["season"] + " (" + rawrow["reference_period"] + ")",
                    rawrow["unit"],
                    rawrow["country"]
                    + " / "
                    + rawrow["province"]
                    + " / "
                    + rawrow["district"],
                    rawrow["source_agency"] + " SAS 2026 Season B",
                    rawrow["source_workbook_url"],
                    rawrow["worksheet"] + "!" + rawrow["cell_reference"],
                    rawrow["crop_sas_label"],
                    state=rawrow["source_value_status"],
                    geography_code=rawrow["district_id"],
                )
    crop_rows = [
        dict(code=r["code"], name=r["name"], kind=r["kind"]) for r in curated["crops"]
    ]
    node_rows = [
        dict(
            code=r["code"],
            name=r["name"],
            framework_code=r["framework_code"],
            framework_name=r["framework_name"],
            name_status=r["name_status"],
        )
        for r in curated["policy_nodes"]
    ]
    files = {}
    for name, data in [
        ("source_records.csv", records),
        ("observations.csv", observations),
        ("curated_crops.csv", crop_rows),
        ("curated_policy_nodes.csv", node_rows),
    ]:
        files[name] = encode_csv(data, list(data[0]))
    manifest = dict(
        transform_version=TRANSFORM_VERSION,
        registry_sha256=registry_hash,
        curation=curated,
        datasets=versions,
        files={
            name: dict(
                sha256=digest(data),
                rows=len(list(csv.DictReader(io.StringIO(data.decode())))),
            )
            for name, data in files.items()
        },
    )
    bundle_id = digest(json.dumps(manifest, sort_keys=True).encode())[:20]
    return bundle_id, manifest, files


def export_bundle(root, output):
    bundle_id, manifest, files = build_tables(root)
    output = Path(output)
    target = output / bundle_id
    manifest_bytes = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    expected = dict(files, **{"manifest.json": manifest_bytes})
    if target.exists():
        if any(
            not (target / name).is_file() or (target / name).read_bytes() != data
            for name, data in expected.items()
        ):
            raise ValueError("Existing bundle differs; refusing to overwrite it")
        return target, manifest
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".public-evidence-", dir=output) as temp:
        staging = Path(temp) / "bundle"
        staging.mkdir()
        for name, data in expected.items():
            (staging / name).write_bytes(data)
        staging.rename(target)
    return target, manifest
