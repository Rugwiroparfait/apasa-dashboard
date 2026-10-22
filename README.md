# APASA

APASA is a project for the 2026 NISR Big Data Hackathon. Day 2 preparation
of AHS 2024 Section 3_4 is complete. This baseline organizes that workflow;
Day 3 descriptive maize exploration is published. Day 4 adds a local Streamlit
dashboard prototype; deployment is a later stage.

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
app.py
.streamlit/config.toml
analysis/prepare_section3_4.py
analysis/day3_exploratory_analysis.py
docs/day3_findings.md
outputs/aggregates/day2_section3_4_crop_candidates.csv
outputs/day3/maize_overall_summary.csv
outputs/day3/category_dictionary.csv
outputs/day3/figures/
tests/test_dashboard.py
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
files remain local. The published Day 2 baseline contains no dashboard or Day 3 analysis.

## Day 3 descriptive exploration

Run `python3 analysis/day3_exploratory_analysis.py` using the same local inputs
and the dependencies in `requirements.txt` (now including matplotlib for charts).
Read `docs/day3_findings.md`; the public overall-summary CSV, category dictionary
and eleven charts are in `outputs/day3/`. The detailed support CSV is written to
ignored `local_data/day3/`; its legacy copy under `outputs/day3/` is also ignored
because small categories and sensitivity differences can disclose individual values.
This stage describes observed maize plot-crop harvest quantities in kilograms,
without weighting, causal inference, area normalization, or other-section merges.
Raw inputs and all Day 2 artifacts remain unchanged. The Day 3 workflow does not build the dashboard.

## Day 4: local dashboard prototype

The dashboard starts from the public repository alone; no survey inputs, local
metadata, preparation run, or ignored files are needed. Use Python 3.10+:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open `http://localhost:8501`. Stop with Ctrl+C. The server binds to loopback;
this is a local prototype and has not been deployed. Run the verification with
`python -m unittest discover -s tests -v`. The tests use
[Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)
on a temporary copy containing only the public app inputs.

The app reads an explicit set of approved public files: the two scenarios in
`outputs/day3/maize_overall_summary.csv`, the traditional/improved seed rows
already published in `docs/day3_findings.md`, and the eleven committed chart
images. The category dictionary is public metadata but is not needed at startup.
It does not import the preparation or analysis scripts, traverse data folders,
load the detailed support CSV, or compute new group statistics.

The only sample control switches the overall-summary panel between all records
and the published sensitivity excluding values above 5,000 kg. Seed medians
and practice charts always show the all-record view. No geographic filters are
available. Harvest quantity is kg per maize crop-slot/plot-season record;
statistics exclude missing reports and retain reported zeros. Zero meaning is
unconfirmed, and the 5,000 kg threshold is a review flag, not an error rule.

These are unweighted descriptions of observed records, not national estimates.
Seed comparisons are observational associations, not causal effects. The app
does not calculate crop-specific yield or productivity. Small or sensitive
groups and complementary harvest statistics remain suppressed or omitted.
Neither raw `.dta` files nor row-level data may ever be bundled or pushed.

Stage history: Day 2 preparation → Day 3 descriptive maize exploration →
Day 4 local prototype. Deployment and final submission remain future tasks.
