# Day 3: descriptive maize exploration

## Findings
Among 9,017 observed maize plot-crop records, 8,908 have reported harvest quantities and 109 are missing (1.21%). There are 215 reported zeros, whose meaning is unconfirmed, and 5 values above the 5,000 kg review threshold.
The median is 30.0 kg (Q1–Q3 10.0–70.0; IQR 60.0 kg); the mean is 92.12 kg. Excluding only the five review-flagged records in a sensitivity view gives 9,012 records, 8,903 observed harvests, median 30.0 kg and mean 86.91 kg. The main analysis retains all records.

### Main category comparisons (all reported values)
Each row counts observed maize records and distinct plot-seasons equally. Harvest statistics use only the observed-harvest denominator, including reported zeros. Missing category values remain a separate group. Q1/Q3 use pandas linear quantile interpolation.

| Category | Records / plots | Missing harvest | Observed harvest | Median kg | Q1–Q3 kg | Mean kg |
|---|---:|---:|---:|---:|---:|---:|
| Seed type (matching maize slot) — 1: Traditional seeds | 3,564 | 9 | 3,555 | 15.0 | 6.5–40.0 | 41.86 |
| Seed type (matching maize slot) — 2: Improved seeds | 5,311 | 11 | 5,300 | 40.0 | 15.0–100.0 | 125.18 |
| Seed type (matching maize slot) — 3: Both (traditional and improved seeds) | 55 | 2 | 53 | 80.0 | 25.0–170.0 | 156.89 |
| Seed type (matching maize slot) — Missing / not recorded | 87 | 87 | 0 | suppressed | suppressed | suppressed |
| Improved-seed source (matching maize slot) — 1: Government (MINAGRI/RAB/NAEB) | 56 | 0 | 56 | 50.0 | 18.6–146.2 | 92.88 |
| Improved-seed source (matching maize slot) — 2: Recognized seed multipliers | 63 | 0 | 63 | 30.0 | 13.0–85.0 | 79.03 |
| Improved-seed source (matching maize slot) — 3: Agro dealers | 2,147 | 2 | 2,145 | 40.0 | 15.0–100.0 | 114.81 |
| Improved-seed source (matching maize slot) — 4: NGOs | 2,464 | 8 | 2,456 | 47.1 | 20.0–110.0 | 145.31 |
| Improved-seed source (matching maize slot) — 5: Market | 432 | 3 | 429 | 30.0 | 12.0–60.0 | 64.54 |
| Improved-seed source (matching maize slot) — 6: Agriculture cooperative | 154 | 0 | 154 | 54.5 | 20.0–150.0 | 168.28 |
| Improved-seed source (matching maize slot) — 7: Other (specify) | 50 | 0 | 50 | 20.0 | 10.0–78.8 | 97.41 |
| Improved-seed source (matching maize slot) — Missing / not recorded | 3,651 | 96 | 3,555 | 15.0 | 6.5–40.0 | 41.86 |
| Organic fertilizer use — 1: Yes | 6,898 | 86 | 6,812 | 30.0 | 10.0–70.0 | 84.40 |
| Organic fertilizer use — 2: No | 2,119 | 23 | 2,096 | 24.0 | 10.0–70.0 | 117.22 |
| Inorganic fertilizer use — 1: Yes | 4,130 | 72 | 4,058 | 50.0 | 20.0–120.0 | 145.21 |
| Inorganic fertilizer use — 2: No | 4,887 | 37 | 4,850 | 20.0 | 7.5–45.0 | 47.69 |
| Pesticide/fungicide use — 1: Yes | 2,090 | 54 | 2,036 | 50.0 | 20.0–110.0 | 141.97 |
| Pesticide/fungicide use — 2: No | 6,927 | 55 | 6,872 | 25.0 | 10.0–60.0 | 77.35 |
| Mechanical equipment use — 1: Yes | 7 | 0 | 7 | suppressed | suppressed | suppressed |
| Mechanical equipment use — 2: No | 9,010 | 109 | 8,901 | suppressed | suppressed | suppressed |
| Anti-erosion activity present — 1: Yes | 6,916 | 93 | 6,823 | 30.0 | 10.0–70.0 | 75.84 |
| Anti-erosion activity present — 2: No | 2,101 | 16 | 2,085 | 30.0 | 10.0–94.0 | 145.40 |

### Interpretation
Median reported maize harvest is 40 kg for improved-seed records versus 15 kg for traditional-seed records. Inorganic fertilizer use categories have medians of 50 kg (Yes) and 20 kg (No); pesticide/fungicide categories have medians of 50 and 25 kg. These are associations among observed records, with different group compositions and potentially different plot sizes.
Organic fertilizer categories differ little in median (30 versus 24 kg), while both anti-erosion presence categories have a 30 kg median. Means tell a different story for these categories and are sensitive to the upper tail. The local-only support CSV gives the full median, quartile and mean comparison for every category with the flagged records excluded.
The Both-seed category has only 55 records (53 observed harvests); treat its higher median cautiously. Only seven records report mechanical equipment use, so no numerical harvest comparison or equipment chart is produced for that group. The report also withholds harvest statistics for equipment nonusers to prevent recovery of the small group total by subtraction from the overall mean. All 87 records with missing seed type also lack harvest quantity. Improved-seed source is missing in 3,651 records; source-group comparisons require attention to seed-question routing and cannot represent all maize growers.

## Methods and counting
Inputs: unchanged Day 2 prepared CSV and Section 3_4 raw file, plus local variable/value-label CSVs. The local questionnaire `audit_tmp/docs/AHS2024_questionnaire.pdf`, printed pages 3–6, supports plot number, crop-slot harvest units, seed categories and plot practices. Section 3.20 is total reported seasonal crop-slot harvest quantity in kg, with already-harvested and remaining-quantity questions preceding it; it is not a household total or necessarily a final measured harvest.
The prepared file deliberately excludes direct IDs. Source row index was used only in memory to recover identifiers from the same Section 3_4 file, not to merge survey sections. The available composite key is Season + Cluster_ID + hhid + s2q1 (plot number). All key components are present; zero duplicate composite keys occur in the 32,616 source rows or 9,017 maize records. There are zero repeated source rows among maize slots. Thus each maize slot corresponds to one distinct observed plot-season; no deduplication or summing is required. Multiple plots from one household may remain; independence is not assumed. The script stops if this uniqueness condition changes.
For all seven slots the script reconciles crop, harvest, seed type and improved-seed source against matching source suffixes, and checks plot-level values against the source row. Labels are resolved per slot rather than borrowed from another slot. No code meaning is guessed; unmapped codes are marked UNCONFIRMED.
The local-only grouped CSV (`local_data/day3/maize_support_summary.csv`) covers every listed Day 2 support field, including every observed category and missing category, for both the full and sensitivity samples. Each field partitions its scenario total; the different fields must not be added together. The sensitivity view excludes only values >5,000 kg and retains missing harvest records and zeros. This threshold is a review flag, not a validated error definition.
Inorganic fertilizer type is the first response position, not an exhaustive fertilizer-use category: the raw file has additional positions absent from the prepared data. Anti-erosion types are three separate response positions, not mutually exclusive overall activity types. Their counts must not be summed as unique activity users. Plot-level practices may apply to crops other than maize on mixed-crop plots.
Missing improved-seed sources, equipment/fertilizer types and anti-erosion follow-ups can reflect questionnaire routing or nonresponse. They are not interpreted as nonuse. The questionnaire routing has some inconsistent references; no structural-missing recoding is attempted. No plot area is used: the prepared data omit it, and no crop-specific area denominator is established.

## Outputs, safeguards and limitations
Public outputs `outputs/day3/maize_overall_summary.csv` and `category_dictionary.csv` contain overall aggregate descriptions and category metadata only. The detailed support CSV is local-only: singleton category counts and differencing of scenario means can disclose individual flagged harvest quantities, even when small-group statistics are suppressed. The legacy `outputs/day3/maize_support_summary.csv` is also retained locally and explicitly ignored. `outputs/day3/figures/` contains median and interquartile-range charts with group counts, missingness and zeros annotated. Categories with fewer than 30 observed harvests are omitted from charts with their omitted counts disclosed. Statistics for fewer than 20 observed harvests are suppressed in the local support CSV; its counts remain available locally. Chart footnotes referring to the CSV refer to this local-only support file. These are exploratory presentation safeguards, not an official disclosure clearance.
All statistics are descriptive and unweighted. Differences describe these observed records only; they do not measure practice effects, yield, productivity or national agricultural conditions. Plot size, crop mix, geography, selection into support categories, household clustering, missingness and reporting error may explain differences. No significance tests, confidence intervals, regressions or survey-design inference are produced. Small categories warrant particular caution; means can be sensitive to large quantities.
Raw inputs and Day 2 artifacts are read-only and hash-checked during execution. No household IDs, plot IDs, record UIDs, source row indices, individual observations or extreme-value lists are exported. Raw and processed microdata remain local and ignored. No NISR contact, other-section merge or dashboard work is performed.

## Reproduce
From the repository root, with the same local Day 2 inputs and Python 3.10+:

```bash
python3 -m pip install -r requirements.txt matplotlib
python3 analysis/day3_exploratory_analysis.py
```

The script asserts source/prepared shape, slot alignment, plot-key uniqueness, maize missing/zero/flag counts, and group-denominator reconciliation.
