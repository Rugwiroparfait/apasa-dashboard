# APASA interpretation review — awaiting review before cleaned exports

The directory contains **15 Excel workbooks: one register and 14 NISR workbooks**, covering 871 sheets in total. There is no single assembled 2013-onward workbook in `data/`. NISR filenames span 2016–2026; some headers include 2015 comparison data. No 2013 or 2014 source workbook was found. A header year is evidence of a label, not proof of a complete observation series. `local_data/references/day7/Tables_2026_Season_B.xlsx` is an additional reference copy outside the requested data directory and was not substituted for the supplied input.

The register is `PSTA5_Indicator_Register (1).xlsx`: five seasonal sheets, each 7 rows × 7 columns, containing six recurring indicator definitions (30 seasonal records). There are no official indicator codes, no explicit geography field, no detailed estimator specifications, no authenticated policy-framework citation, and no fiscal-year targets in this supplied register. Local REG-01–REG-06 IDs identify the six definitions; every candidate links to all five original seasonal register records. Baselines refer to the corresponding prior-year season; targets refer to the sheet's season. These seasonal records have not been collapsed into annual targets.

## Most important unresolved issue: what are the register's targets?

The register cites NISR SAS as its stated source. Its 2024 B target values reproduce NISR observations in `Tables_2024 Season B.xlsx`:

| Register field | NISR source cell | NISR stored result |
|---|---|---|
| Maize production: 119,101.23 MT | Table 5!G6 | 119101.22948988932 MT |
| Maize productivity: 1.284 MT/ha | Table 5!I6 | 1.2841270272071035 MT/ha |
| SSF improved seeds: 16.64% | Table 17!D36 | 16.64 |
| LSF improved seeds: 72.57% | Table 17!E36 | 72.57 |
| SSF inorganic fertilizer: 51.20% | Table 22!D35 | 51.2 |
| LSF inorganic fertilizer: 82.89% | Table 22!E35 | 82.89 |

The first two coincide after rounding; the other four coincide numerically. This does not establish how the register was compiled, nor authenticate a policy target. Preserve the register field labels but request the official PSTA5 results framework, indicator IDs, baseline methodology, target approval/source and target periods before using these as policy targets. No target-achievement inference is justified.

## Comparability checks still needed

- Crop production: distinguish volume (MT) from shares of production use, uncertainty estimates and category aggregates. The register names broad crop categories but gives only maize baseline/target examples. Do not extend maize values to other crops or sum crop totals and their component crops.
- Productivity: match exact crop and farmer population, and verify harvested area rather than cultivated area. Table 5 explicitly distinguishes both area columns. A source yield in kg/ha could be converted to MT/ha by dividing by 1000, but no conversion was performed. Survey estimators and treatment of mixed cropping still require methodology review.
- Improved seeds and inorganic fertilizer: select the percentage-of-farmers block and the correct SSF or LSF column. Farmer, plot and land percentages coexist in the same sheets. Seed/fertilizer composition or source shares do not measure adoption prevalence. Group definitions, thresholds, weights and survey coverage may change across years.
- Periods: seasonal A/B/C observations remain separate. Comparative years inside one table do not mean all measures cover all years. Header-year relationships are provisional until the exact columns are checked; filename-only years are UNRESOLVED. Do not assume a year associated with constant prices is the observation year. No annual totals or fiscal-year alignment was calculated.
- Geography: national, province and district rows must be selected explicitly; do not add national totals to component districts. Register geography is unstated. Local file names do not authenticate publication provenance.
- Missing values: literal strings including `N/A`, `(NA)`, dashes and blanks have different possible meanings. No codebook meanings have been assumed. Formula results may also be empty strings, zero or missing cached values; these are distinct.
- Five sheets contain formulas without cached results: 2018 Table 10.1 (4), 2018 Appendix 9 (86), SAS 2021 Table 40 (1), USAS 2020 Table 35 (1), and USAS 2020 Table 38 (1). There are external formulas in 23 sheets. Formula expressions and cached results are preserved separately; external references were not refreshed. The legacy XLS reader exposes stored results but cannot provide the same formula audit.

## How to review these outputs

Open `review.html` for the full searchable inventory, register fields and candidate crosswalk. `sheet_inventory.csv` describes every sheet and previews its structure. `source_cells.json` retains every nonempty source cell, coordinates, formulas, cached results, comments and merged ranges; absent coordinates remain blank. `noncandidate_sheets.csv` documents sheets outside the initial topic screen. The candidate screen is based on the first eight rows and is intentionally provisional; tables with unexpected header placement can require scope extension. Full-cell data is preserved so those exclusions are reviewable.

The crosswalk has one status per distinct register indicator × candidate workbook/sheet × header year (or unresolved filename year). It is a broad table-level candidate map, not a verified observation-level crosswalk. Exact crop rows, season/year columns, denominator blocks and survey methodology must be checked before extraction. Different register seasonal occurrences are linked through `register_records`; candidate historical seasons are not assumed aligned to every register period. Source labels are preserved alongside analytical IDs and interpretations.

All input SHA-256 hashes are verified unchanged in `input_manifest.json`. No workbook was saved, no cleaned observations were exported, and baseline/target fields remain in `register_fields_for_review.csv`. Review the target provenance, crop scope, farmer denominators and year/season mapping before authorizing the next extraction stage.
