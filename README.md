# APASA

APASA is a project for the 2026 NISR Big Data Hackathon. Day 2 preparation
of AHS 2024 Section 3_4 is complete. This baseline organizes that workflow;
Day 3 analysis has not started.

## Scope and status

The preparation uses only the combined Section 3_4 file (crop grown, seeds,
production, and agricultural inputs and practices). It reshapes seven crop
slots into valid plot-crop slot records and checks crop, seed, harvest quantity
and support-indicator completeness. The existing run produced 74,549 valid
slots from 32,616 source rows and identified 15 candidate crops.

There are no merges with other survey sections, yield or productivity
calculations, survey-design inference, or national estimates. No contact with
NISR is part of this workflow. Zero and unusual harvest quantities remain
unchanged; their interpretation is unresolved.

## Repository structure

```text
README.md
requirements.txt
.gitignore
analysis/prepare_section3_4.py
outputs/aggregates/day2_section3_4_crop_candidates.csv
```

Local-only files are organized as follows:

```text
data/                     # original survey inputs
local_data/section3_4/     # generated row-level CSV (optional Parquet)
audit_tmp/                # metadata inputs and script-generated QA working files
docs/day2_section3_4_qa_report.md
docs/day2_section3_4_structure_and_qa.json
```

The unchanged QA report and JSON were moved to `docs/` but are excluded from
Git because they include the ten largest individual observed harvest values;
their public-release status is unresolved. The tracked candidate CSV contains
only crop-level counts and completeness rates, with at least 400 records per
candidate and no household IDs, plot IDs, or individual records.

## Install and run

Use Python 3.10 or newer:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python analysis/prepare_section3_4.py
```

Before running, place the authorized original input at this exact local path:

```text
data/AHS2024_Section3_4_CROP GROWN, SEEDS AND PRODUCTION & AGRICULTURAL INPUTS AND PRACTICES.dta
```

Also supply the existing local metadata inputs:

- `audit_tmp/s3_4_variables.csv`, with columns `var,label,value_label_set`.
- `audit_tmp/s3_4_value_labels.csv`, with columns `value_label_set,code,label`.

These inputs are not distributed in Git. Obtain them through the project's
authorized local data workflow; this script does not generate the metadata.

The preparation script is preserved byte-for-byte. Its root-relative paths
still work from `analysis/`. It writes row-level data to `local_data/section3_4/`
and regenerates QA report, JSON and candidate CSV in ignored `audit_tmp/`.
The files in `docs/` and `outputs/aggregates/` are the preserved Day 2 snapshots.
Parquet export is optional and skipped if no Parquet engine is installed;
NumPy and pandas are the only required third-party dependencies.

## Data boundary

Raw survey files and all row-level processed data remain local and are excluded
from Git, including records without direct identifiers. Never force-add ignored
data. Only reviewed source code, documentation and aggregate-only outputs may
be committed. Other survey metadata, reference PDFs, editor settings and scratch
files remain local. No dashboard or Day 3 work is included in this baseline.
