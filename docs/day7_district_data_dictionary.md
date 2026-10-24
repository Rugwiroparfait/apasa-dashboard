# Day 7: published district crop-statistics dictionary

## Dataset and observation grain

`outputs/day7/official_sas_2026_b_district.csv` contains published NISR SAS 2026
Season B estimates: one district × literal source crop label × measure per row.
There are 1,800 rows: 30 districts × 15 individual crop columns × four measures.
This is an aggregate official-statistics dataset, not AHS microdata or a new
estimate computed from survey records. It supplies no policy targets or progress.

Reference period is March–June 2026. The source report is
[NISR SAS 2026 Season B](https://statistics.gov.rw/sites/default/files/documents/2026-09/SAS%202026B_Main%20report.pdf);
the cell-level authority is the [published workbook](https://statistics.gov.rw/sites/default/files/documents/2026-09/Tables_2026%20Season%20B.xlsx).
Administrative names and parent IDs are from the
[NISR District Boundary 2022 layer](https://gis-server.statistics.gov.rw/server/rest/services/Hosted/District_Boundary_2022/FeatureServer/0).

## Measures

| `measure` | Source | Unit as printed | Meaning and limitation |
|---|---|---|---|
| cultivated_crop_area | Table 9 | Ha | Published cultivated crop area by district; not interchangeable with harvested area or physical nonoverlapping land |
| harvested_crop_area | Table 10 | Ha | Published harvested crop area by district; no use as an AHS crop-slot denominator |
| average_crop_yield | Table 11 | Kg/Ha | Published general average crop yield. Transcribed directly, never derived from the other two measures. Table 12's large-scale-farmer yield is excluded |
| crop_production | Table 13 | MT | Published crop production by district in metric tonnes, not an AHS slot mean or a household quantity |

No unit conversions, annualization, seasonal sums, district rankings, inferred
targets or target-progress calculations are performed. Measures remain separate
rows. Broad groups and component crops must not be summed together. Crop-specific
cultivated/harvested areas are not necessarily disjoint physical land areas.

## Columns

| Column | Definition |
|---|---|
| reference_period | `March-June 2026`, following the official release period |
| season | `2026 B` |
| geography_level | `district` |
| country | `Rwanda` |
| province, province_id | Exact official parent name/code from administrative attributes; City of Kigali is a province-level parent |
| district, district_id | Exact matched official name/code; IDs are text, with no inferred or synthesized codes |
| sas_district_label | Original district label in the SAS worksheet; retained even if a future lookup cannot resolve it |
| crop_sas_label | Original crop header string, without renaming, pooling or guessed equivalence |
| measure | One of the four named measures above |
| value | Numeric source value serialized without rounding; empty for nonnumeric/missing source states |
| unit | Exact table unit (`Ha`, `Kg/Ha`, `MT`) |
| source_agency | `NISR` |
| source_report | Official report URL |
| source_workbook_url | Official workbook URL |
| table_name | Full worksheet title as read from the source's title row |
| worksheet | Table 9, Table 10, Table 11 or Table 13 |
| cell_reference | Value cell in that worksheet, e.g. D4; not an identifier for a farmer |
| source_value_status | Explicit state defined below |
| source_value_raw | Raw saved cell value as text; numeric Excel values use Python's saved-value representation, not the Excel display format |
| source_district_cell | District-label cell reference in the same worksheet |
| source_crop_header_cell | Crop-header cell reference in the same worksheet |
| administrative_source | Official feature-layer URL |
| administrative_objectid | Administrative feature OBJECTID for traceability; not the district administrative code and not a person identifier |
| district_mapping_status | `exact` or `unresolved`; unresolved fields remain empty, never guessed |
| workbook_sha256 | SHA-256 of the exact local source workbook used |
| administrative_attributes_sha256 | SHA-256 of the saved administrative query response used |
| notes | Extraction limitations and any source-label or value-state caveat |

## Missingness and source states

| State | Value field | Meaning |
|---|---|---|
| numeric | Original numeric value | Finite nonzero source number; no alteration or capping |
| numeric_zero | `0` | Actual numeric zero in the source; never generated from a missing value |
| blank | Empty | Cell is empty (`None`) |
| empty_text | Empty | Saved text contains no non-whitespace characters; separate from an empty cell |
| NA | Empty | Explicit NA/N/A/(NA) source token; exact token retained in source_value_raw |
| dash | Empty | Explicit hyphen/en-dash/em-dash source token, preserved in source_value_raw |
| unresolved_text | Empty | Other text requiring interpretation; original string retained |
| unresolved_nonfinite | Empty | Non-finite numeric state requiring interpretation |

Only observed states appear in the reconciliation report; supported states are
not fabricated as records. The numeric value alone cannot distinguish missing
states: consumers must read source_value_status and source_value_raw. Zero yield
must not automatically be interpreted as crop failure, and a blank must not be
interpreted as zero or absence of a crop in Rwanda.

## Exact labels and exclusions

The fifteen crop columns are maize, sorghum, paddy rice, wheat, cassava, sweet
potato, Irish potato, three named banana varieties, bush bean, climbing bean,
pea, groundnuts and soybean, retained using the workbook's literal spelling.
Table 13 prints `Cooking Banana`; the other three tables print `Cooking banana`.
No canonical cross-table mapping is asserted for those differing literal strings.
The dataset therefore has sixteen distinct literal crop labels across measures,
not sixteen individual crop columns within each measure. No AHS or PSTA5 label
mapping is introduced.

Excluded groups include Cereals, Other cereals, Tubers and Roots, Yams & Taro,
Banana/Bananas, Legumes and Pulses, Bean, Vegetables and Fruits,
Vegetables/vegetables, Fruits, Fodder crops, Other crops and totals. `Bean` is
excluded because Bush bean and Climbing bean are retained separately. National,
S/Total, SSF/LSF, previous-year and Change rows are excluded from district data.
No individual horticulture crop is inferred from a broad group.

## Reference inputs and reproducibility

The extractor reads only these local published reference files:

- `local_data/references/day7/Tables_2026_Season_B.xlsx`
- `local_data/references/day7/district_layer_metadata.json`
- `local_data/references/day7/district_attributes.json`

This folder is already covered by `/local_data/` in `.gitignore`; no ignore rule
was weakened and no source workbook is copied into a public output directory.
The layer metadata endpoint is the layer URL plus `?f=pjson`. The query endpoint
is the layer URL plus `/query`, with `where=1=1`, `outFields=*`,
`returnGeometry=false`, `f=json`. The saved query contains administrative
attributes only; polygon geometry is not required. These are public geographic
records, not household, plot or farmer records. Source files must be downloaded
from the URLs above before running the extractor; it performs no network calls.

Run `python analysis/day7_extract_official_district_stats.py` with openpyxl
installed. The script validates every value, unit, district/header reference and
compound key and regenerates `docs/day7_source_reconciliation.md`. It rejects
unexpected source formulas instead of interpreting an unverified cached result.
See that report for coverage, file hashes, exclusions and within-season subtotal
diagnostics. No AHS files, Django code or prior outputs are used or modified.
