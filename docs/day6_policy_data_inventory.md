# Day 6: policy and official-statistics inventory

Checked 23 October 2026. Documentation only: the Django app, existing local work,
policy catalogue and Day 2–5 outputs are unchanged. No microdata was opened.

## Sources checked

| Primary source | Verified coverage and use | Boundary |
|---|---|---|
| [MINAGRI PSTA5 full text, Annex 1](https://www.minagri.gov.rw/fileadmin/user_upload/Minagri/Publications/Policies_and_strategies/PSTA_5_Fulltext__Final.pdf), printed pp. 102–117 | Rechecked the official PDF supporting the existing 126-row crop-indicator catalogue; baseline heading 2023, targets 2024/25–2028/29, source institutions and units. Explicit older baseline years override the heading. | National strategy context is not evidence of district targets. Many rows lack an operational definition or annual/seasonal aggregation rule. |
| [NISR SAS 2024 annual release](https://statistics.gov.rw/statistical-publications/agriculture-environment/seasonal-agricultural-survey-2024-annual-report-2024) and [published workbook](https://statistics.gov.rw/sites/default/files/documents/2025-02/SAS%202024_Annual%20Tables.xlsx) | Agricultural year September 2023–September 2024; season-specific published tables. Workbook inspected, including district production Tables 21–23 and yield Tables 16–18. | Historical reference; not the latest annual release. No new district change statistic calculated. |
| [NISR SAS 2025 annual release](https://statistics.gov.rw/data-sources/surveys/Seasonal-Agricultural-Survey/Seasonal-Agricultural-Survey/seasonal-agricultural-survey-2025-) and [published workbook](https://statistics.gov.rw/sites/default/files/documents/2025-12/SAS%202025_Annual%20Tables.xlsx) | Latest annual SAS release verified in this search. Table 0 contains seasonal national production, area and yield values. District crop production Tables 24–26; cultivated area 13–15; harvested area 16–18; yield 19–21. | The release page says January–December 2025, but the report defines agricultural year 2024/2025. Season A is September 2024–February 2025; B March–June 2025; C July–September 2025. These are separate seasonal results, not an assumed fiscal-year total. |
| [NISR SAS 2025 full report](https://statistics.gov.rw/sites/default/files/documents/2025-12/SAS%202025%20Final%20report.pdf) | Survey definition, season coverage, table inventory and methodology inspected alongside the workbook. | A report called annual does not make every table cell an annual total or annual weighted yield. |
| [NISR SAS 2026 Season B release](https://statistics.gov.rw/statistical-publications/agriculture-environment/seasonal-agricultural-survey-season-b-2026), [report](https://statistics.gov.rw/sites/default/files/documents/2026-09/SAS%202026B_Main%20report.pdf) and [workbook](https://statistics.gov.rw/sites/default/files/documents/2026-09/Tables_2026%20Season%20B.xlsx) | Later seasonal release verified; reference period March–June 2026. Page lists documents updated 22 September 2026. Workbook Table 6 supplies national cultivated/harvested area, production and yield, with separate 2026 B/2025 B/2024 B columns. Tables 9–11 and 13 supply district measures. | No 2026 annual or Season C release was verified by this check. This is the latest seasonal table verified here, not a guarantee that no other release exists. |

Downloads were read in `/tmp`, not bundled into the repository. NISR website file
update stamps and search crawl dates are not treated as measurement dates or as
proof of first publication. The actual period in the table/report takes precedence.
No institution was contacted.

## Candidate pairings and comparison status

[day6_indicator_comparability.csv](day6_indicator_comparability.csv) inventories all
126 existing candidate crop/group × policy-indicator rows. It includes the final
2028/29 policy target and a separate 2025/26 target reference where verified.
Blank, dash or TBD references are not converted to zero or carried forward.
Policy sources and exact printed pages remain distinct from actual-data sources.
The CSV transcribes official actuals only; it does not estimate production or yield.

Eighteen rows have national seasonal actuals verified at exact workbook cells:
ten production pairings and eight productivity pairings. For those rows the CSV
also records available 2025 A/B/C values from annual-workbook Table 0, with cell
references. Empty season cells stay blank; no seasonal values are summed or yields
averaged. The latest actual column uses 2026 B; the annual-source columns remain
explicitly 2025 seasonal observations. Crop mappings involving Rice/Paddy rice or
Beans/Bean remain flagged for scope confirmation even where contextual values are
transcribed. Horticultural aggregates are not substituted for individual crops or
export-only production measures.

- **Directly comparable:** none established. This status requires the same
  operational definition, unit, time coverage and geography, not merely a matching
  crop name and unit.
- **Context only:** 18 verified seasonal national production/productivity actuals.
  PSTA5 fiscal-year targets lack a verified matching temporal aggregation in the
  checked rows. A 2026 B harvest estimate does not establish a complete 2025/26
  fiscal-year observation, nor progress toward the later 2028/29 target.
- **Not currently comparable:** 108 rows without a verified matching actual or
  sufficiently specified target/definition in the checked sources. This is not
  zero performance or proof that an official source does not exist elsewhere.

All progress values and formulas are blank. No ratio is justified for these
pairings. Were a pairing verified, a target-attainment percentage would require
its approved definition and direction; baseline-gap closure and target attainment
are different concepts. Neither is calculated in this task.

The existing catalogue's malformed Pyrethrum 2027/28 export target remains a source
quality issue; it was not corrected or used in a calculation. National-level scope
is inferred from the national strategy context where the indicator row has no
explicit geography: this limitation is recorded instead of inventing a district
allocation. Source institution labels such as “NIST” remain as printed in policy
metadata and need clarification. No district targets were manufactured.

## Verified district statistics

The latest checked workbook has these exact district measure tables, also named
in the 2026 B report's table list:

| Workbook sheet | Period | Measure/unit | Report table-list page reference |
|---|---|---|---|
| Table 9 | 2026 B | Cultivated crop area, Ha | printed p. 37 |
| Table 10 | 2026 B | Harvested crop area, Ha | printed p. 38 |
| Table 11 | 2026 B | Average crop yield, Kg/Ha | printed p. 39 |
| Table 13 | 2026 B | Crop production, MT | printed p. 41 |

Table 12 is specifically large-scale-farmer yield and must not be substituted for
Table 11's population. National Table 6 uses MT/ha for yield, whereas district
Table 11 uses Kg/Ha. No silent unit conversion or AHS-derived yield is performed.
Table numbers/printed page references are recorded as printed; workbook sheet
and cell references are the primary extraction locator.

The 30 district labels are explicitly verified from Table 13, rows 4–33, column B:
Nyarugenge, Gasabo, Kicukiro, Nyanza, Gisagara, Nyaruguru, Huye, Nyamagabe,
Ruhango, Muhanga, Kamonyi, Karongi, Rutsiro, Rubavu, Nyabihu, Ngororero,
Rusizi, Nyamasheke, Rulindo, Gakenke, Musanze, Burera, Gicumbi, Rwamagana,
Nyagatare, Gatsibo, Kayonza, Kirehe, Ngoma and Bugesera. Subsequent S/Total,
2025B, Change and source rows are not districts.

Crop columns explicitly include Maize, Sorghum, Paddy rice, Wheat, Cassava,
Sweet potato, Irish potato, Cooking Banana, Dessert banana, Banana for beer,
Bean, Bush bean, Climbing bean, Pea, Groundnuts and Soybean, alongside broader
groups such as Cereals, Tubers and Roots, Yams & Taro, Bananas, Legumes and Pulses,
Vegetables and Fruits, Vegetables, Fruits, Fodder crops and Other crops. Group
headers and component columns overlap: do not sum them together. Individual
onion, avocado or other horticulture statistics are not established by these
broad group columns. Blank and numeric zero cells are distinct in the workbook;
neither is a new estimate supplied by APASA.

District coverage is verified, but a district time-comparison series is not yet
cleared: 2025 annual Table 25 and 2026 B Table 13 provide corresponding seasonal
production tables, yet comparability still requires validation of definitions,
frames, revisions, boundaries and uncertainty. A historical national row in the
2026 workbook is not a historical district observation. No district percentage
changes, rankings or policy scores are calculated. Province/City of Kigali mapping
and boundary version must be verified separately before hierarchical navigation.

## The two APASA journeys supported by these sources

**National policymaker:** select an indicator and crop, inspect its policy source,
reference target and period, then view a verified official actual with its own
source, crop wording, period, measure and geography. The present inventory supports
an evidence review with an explicit comparison-status label. It does not yet
support target-progress scores. Exports, insured area, input delivery and extension
services require their own official actuals; SAS harvest statistics do not stand in
for them.

**District officer:** select a verified district, crop and season and inspect the
published official production/area/yield table. The inventory establishes where
these district statistics exist. It does not establish district targets, live
programme delivery, individual farmer eligibility or follow-up lists. A second
period can support a comparison only after the comparability checks above; no
cross-period district result is generated here.

**Separate AHS evidence:** Day 5 covers 75 documented crop groups, with harvest
statistics released for 35 under its exploratory safeguards. It describes crop-slot
records and reported practices, missingness and zeros; source-row surrogates are
not independently verified plot IDs. It complements official statistics by showing
what the analyzed survey records report. It cannot replace representative SAS
production estimates, official yields, national totals or programme delivery data.
No AHS-to-SAS linkage, causal interpretation or PSTA5 progress calculation is made.

## Remaining verification and audit boundary

See [day6_data_gaps.md](day6_data_gaps.md). The sources checked here establish
specific tables and values, not completeness of every MINAGRI/NAEB administrative
series. No new dashboard screen, forecast, model, recommendation, regression or
significance test is produced. Existing app and analysis files are preserved.
