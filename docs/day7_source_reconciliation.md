# Day 7: official district source reconciliation

This dataset transcribes published NISR aggregate estimates for 2026 Season B (March–June 2026). No AHS input or private identifiers are read. No dashboard, target-progress, ranking or cross-period analysis is produced.

Validation passed: 1,800 rows, 30 districts × 15 individual source crop columns × four measures. The requested compound key is unique. Values and district/header references were checked against every source cell; units match each table title. Table 12 is never used.

## Source references

- [Official workbook](https://statistics.gov.rw/sites/default/files/documents/2026-09/Tables_2026%20Season%20B.xlsx)
- [Official report](https://statistics.gov.rw/sites/default/files/documents/2026-09/SAS%202026B_Main%20report.pdf)
- [Administrative layer](https://gis-server.statistics.gov.rw/server/rest/services/Hosted/District_Boundary_2022/FeatureServer/0)

Reference files are local and ignored under local_data/references/day7/. The extractor reads these fixed inputs without network access. The administrative query was `where=1=1`, `outFields=*`, `returnGeometry=false`, `f=json`; all 30 attributes were returned with no transfer-limit flag. Attribute IDs, rather than polygon geometry or object IDs, provide the district/province administrative codes.

## District coverage

| Table | Exact matches | Missing layer districts | Unmatched SAS districts |
|---|---:|---:|---:|
| Table 9 | 30 | 0 | 0 |
| Table 10 | 30 | 0 | 0 |
| Table 11 | 30 | 0 | 0 |
| Table 13 | 30 | 0 | 0 |

All district strings match exactly without spelling substitutions, case folding or manual parent assignment. Normalized district name equals the layer district field; the original SAS label is retained separately. There are no unresolved district matches in this extraction.

| Official province parent | Official province ID |
|---|---|
| City of Kigali | 1 |
| Eastern Province | 5 |
| Northern Province | 4 |
| Southern Province | 2 |
| Western Province | 3 |

City of Kigali is a province-level parent, not a child of another province. IDs are strings copied from the layer, not regenerated integers or inferred code patterns. The workbook does not establish that SAS estimates were computed on the exact geometry version of the 2022 layer; the exact-name parent attachment is verified, but boundary-vintage statistical equivalence remains unconfirmed.

## Crop selection and exclusions

The individually named columns are Maize, Sorghum, Paddy rice, Wheat, Cassava, Sweet potato, Irish potato, the cooking-banana variety, Dessert banana, Banana for beer, Bush bean, Climbing bean, Pea, Groundnuts and Soybean. Original source capitalization is retained: Table 13 uses Cooking Banana, while Tables 9–11 use Cooking banana. This yields 16 distinct literal labels for 15 source crop columns per measure. No canonical cross-table crop mapping is asserted or guessed.

- Table 9 excluded headers: Cereals ; Other cereals; Tubers and Roots; Yams & Taro; Banana; Legumes and Pulses; Bean; Vegetables and Fruits; vegetables; Fruits; Fodder crops; Other crops; Total Developed land.
- Table 10 excluded headers: Cereals ; Other cereals; Tubers and Roots; Yams & Taro; Banana; Legumes and Pulses; Bean; Vegetables and Fruits; vegetables; Fruits; Fodder crops; Other crops; Total Developed land.
- Table 11 excluded headers: Cereals ; Other cereals; Tubers and Roots; Yams & Taro; Banana; Legumes and Pulses; Bean; Vegetables and Fruits; vegetables; Fruits; Fodder crops; Other crops.
- Table 13 excluded headers: Cereals; Other Cereals; Tubers and Roots; Yams & Taro; Bananas; Legumes and Pulses; Bean; Vegetables and Fruits; Vegetables; Fruits; Fodder crops; Other crops.

Bean combines bush/climbing beans and is excluded alongside their individual columns. Other cereals, Yams & Taro, Other crops and Fodder crops also remain excluded because they are unspecified or combined groups. Broad Vegetables/Fruits do not establish individual horticulture observations. National, Total, S/Total, SSF/LSF, 2025B, Change and source rows are not districts.

## Source value states

| State observed | Cells |
|---|---:|
| blank | 44 |
| numeric | 1624 |
| numeric_zero | 132 |

The serializer separately supports blank, empty_text, NA, dash, numeric_zero, numeric, unresolved_text and unresolved_nonfinite. Only states actually present are counted above; absence of NA/dash in this extract does not change their treatment. Source raw values remain available alongside the numeric value. No missing value is imputed, no unit conversion is applied, and yield comes directly from Table 11.

## District sum diagnostics (areas and production only)

These compare fully numeric district cells to the same column’s published row-34 Total/S/Total within the same season. That reference is not asserted to be a separate national estimator. Yield is never summed or recomputed. If any district cell is nonnumeric, the diagnostic remains unavailable rather than treating it as zero. Decimal sums use the saved numeric representations, exposing even tiny workbook precision differences; no tolerance-based correction is applied. No district estimate is altered to match a reference. No separate reconciliation to national Table 6 is performed.

| Table | Source crop label | District sum or unavailable reason | Published row 34 | Difference (sum minus row 34) |
|---|---|---:|---:|---:|
| Table 9 | Maize | 94823.3951 | 94823.39510000001 | -0.00000000001 |
| Table 9 | Sorghum | not calculated: incomplete numeric district cells |  |  |
| Table 9 | Paddy rice | not calculated: incomplete numeric district cells |  |  |
| Table 9 | Wheat | not calculated: incomplete numeric district cells |  |  |
| Table 9 | Cassava | 192304.5590 | 192304.559 | 0.0000 |
| Table 9 | Sweet potato | 84774.5566 | 84774.55660000003 | -0.00000000003 |
| Table 9 | Irish potato | not calculated: incomplete numeric district cells |  |  |
| Table 9 | Cooking banana | 97498.4076 | 97498.4076 | 0.0000 |
| Table 9 | Dessert banana | 36413.6945 | 36413.6945 | 0.0000 |
| Table 9 | Banana for beer | 116859.4045 | 116859.40449999998 | 0.00000000002 |
| Table 9 | Bush bean | 210357.533203246613 | 210357.53320324662 | -0.000000000007 |
| Table 9 | Climbing bean | not calculated: incomplete numeric district cells |  |  |
| Table 9 | Pea | not calculated: incomplete numeric district cells |  |  |
| Table 9 | Groundnuts | not calculated: incomplete numeric district cells |  |  |
| Table 9 | Soybean | 38331.47980 | 38331.47979999999 | 0.00000000001 |
| Table 10 | Maize | 94705.5690797657622 | 94705.56907976576 | 0.0000000000022 |
| Table 10 | Sorghum | 103136.196965000789481 | 103136.1969650008 | -0.000000000010519 |
| Table 10 | Paddy rice | 17532.8183650271630593 | 17532.818365027164 | -0.0000000000009407 |
| Table 10 | Wheat | 9137.65598842521375 | 9137.655988425213 | 0.00000000000075 |
| Table 10 | Cassava | 60540.11640933029091 | 60540.11640933028 | 0.00000000001091 |
| Table 10 | Sweet potato | 78504.35253828907249 | 78504.35253828908 | -0.00000000000751 |
| Table 10 | Irish potato | 48424.209958859299662 | 48424.2099588593 | -0.000000000000338 |
| Table 10 | Cooking banana | 33848.85609465692745 | 33848.85609465693 | -0.00000000000255 |
| Table 10 | Dessert banana | 14240.25189825459188 | 14240.251898254592 | -0.00000000000012 |
| Table 10 | Banana for beer | 51449.68857665291253 | 51449.688576652916 | -0.00000000000347 |
| Table 10 | Bush bean | 210357.52991792440185 | 210357.5299179244 | 0.00000000000185 |
| Table 10 | Climbing bean | 123377.35734954690797 | 123377.3573495469 | 0.00000000000797 |
| Table 10 | Pea | 7981.064437676348523 | 7981.0644376763485 | 0.000000000000023 |
| Table 10 | Groundnuts | 17941.014006167725326 | 17941.014006167723 | 0.000000000002326 |
| Table 10 | Soybean | 38330.550873608364283 | 38330.550873608365 | -0.000000000000717 |
| Table 13 | Maize | 122370.32608850969399 | 122370.3260885097 | -0.00000000000601 |
| Table 13 | Sorghum | 122319.831298634086104 | 122319.83129863408 | 0.000000000006104 |
| Table 13 | Paddy rice | 80325.0226222946489524 | 80325.02262229467 | -0.0000000000210476 |
| Table 13 | Wheat | 10640.33586682293397 | 10640.335866822934 | -0.00000000000003 |
| Table 13 | Cassava | 846962.60257715644894 | 846962.6025771564 | 0.00000000004894 |
| Table 13 | Sweet potato | 641667.4175493284829 | 641667.4175493284 | 0.0000000000829 |
| Table 13 | Irish potato | 331963.062114170458096 | 331963.0621141704 | 0.000000000058096 |
| Table 13 | Cooking Banana | 571177.5540741419603 | 571177.5540741419 | 0.0000000000603 |
| Table 13 | Dessert banana | 156845.9983169392599 | 156845.99831693925 | 0.0000000000099 |
| Table 13 | Banana for beer | 503178.6155168897662 | 503178.6155168898 | -0.0000000000338 |
| Table 13 | Bush bean | 133427.85504624876442 | 133427.85504624876 | 0.00000000000442 |
| Table 13 | Climbing bean | 110346.83331470967758 | 110346.83331470966 | 0.00000000001758 |
| Table 13 | Pea | 4587.253441772989148 | 4587.253441772989 | 0.000000000000148 |
| Table 13 | Groundnuts | 7743.368178474774248 | 7743.368178474774 | 0.000000000000248 |
| Table 13 | Soybean | 15983.820397417248923 | 15983.82039741725 | -0.000000000001077 |

## Reference checksums

- `Tables_2026_Season_B.xlsx`: `5ca81c6b0a54c4a282ed718d134423920cc75279a5827bbe772fe6eb1a4e9d27`
- `district_attributes.json`: `1612eb18b4bb24556fb16d2caf1d3b5dbf296e0835f02b37b1af1ba807e53162`
- `district_layer_metadata.json`: `da8977c330264eac3f95e6f296a281fa1434664a45e1f31ca854a6d653248afb`

## Reproduce and limits

Install openpyxl in the Python environment (`python -m pip install openpyxl`). Run `python analysis/day7_extract_official_district_stats.py` after obtaining the three official reference files named above. Optional `--references`, `--output` and `--report` arguments select local paths. The script asserts source layout, coverage, key uniqueness, units and every exported value/reference, and regenerates this validation report.

Published official district yield is distinct from unweighted AHS crop-slot harvest quantity; this does not authorize deriving yield from AHS records. No district targets, policy-progress scores, recommendations or farmer-level follow-up lists are inferred. Small-cell zeros, blankness or estimates must not be interpreted as farmer absence or performance failure. Statistical uncertainty, source revisions and cross-period/boundary comparability still constrain later views. Existing Django and Day 2–6 artifacts are outside this extraction and remain unchanged.
