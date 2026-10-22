# Day 4 dashboard prototype review

The root `app.py` is a local Streamlit prototype for the observed maize records
in AHS 2024 Section 3_4. No deployment was performed.

## Approved public inputs

All analytical inputs were already published in Day 3 commit
`cbdd42ab3051a75e46f85fe1cfae1f2034c8e418`:

- `outputs/day3/maize_overall_summary.csv`: the all-record and overall sensitivity scenarios.
- `docs/day3_findings.md`: the traditional/improved seed medians and their published record, observed-harvest and missing-harvest denominators.
- Eleven explicitly named images in `outputs/day3/figures/`: optional published practice comparisons, displayed without recalculation.

`outputs/day3/category_dictionary.csv` is approved public category metadata but
is not loaded by the app. No new aggregate dataset was created. No ignored
support CSV, unpublished small-group summary, row-level file or raw survey file
was read or used for this task. The app does not import the analysis scripts.

## Verified behavior

- Overall figures match the committed report: 9,017 distinct maize plot-seasons;
  8,908 observed harvests; 109 missing; 215 reported zeros; five review flags.
- Overall median is 30 kg and mean is 92.12 kg. The approved sensitivity view
  has 9,012 records and 8,903 observed harvests, with median 30 kg and mean
  86.91 kg. Missing reports and zeros remain distinct in both views.
- The seed chart shows published medians of 15 kg (traditional) and 40 kg
  (improved). Median denominators are 3,555 and 5,300 observed reports,
  respectively, from 3,564 and 5,311 records. The comparison remains fixed to
  the all-record sample when the separate sensitivity panel changes.
- Quantities are kg per maize crop-slot/plot-season record. The app identifies
  observational associations and explicitly disclaims causal effects, national
  estimates and crop-specific yield calculations. Sensitive groups remain
  suppressed or omitted. No geographic filters or group-level sensitivity
  summaries are offered.

## Checks

`python -m unittest discover -s tests -v` passed four tests, including all eleven
chart selections, both sensitivity settings, invalid-summary handling, and
startup from a temporary copy containing only approved public files. The test
copy contains no raw data, local data, local metadata or analysis scripts.

Local Chrome verification passed at 1440px desktop and 390px mobile widths:
HTTP health returned 200; the interactive seed chart rendered; the sensitivity
switch updated to 86.91 kg; published-image selection rendered successfully;
there was no document-wide horizontal overflow and no browser page error.
Desktop and mobile screenshots were visually reviewed. Captions use a dark
text color, and the national-estimate caveat is visible in the main page even
when the sidebar is closed. Browser tooling and screenshots stay in `/tmp`.

The tested environment used Python 3.12, Streamlit 1.66.1, Altair 6.3.0,
pandas 2.1.4, NumPy 1.26.4 and PyArrow 24.0.0. An initial PyArrow 26 / NumPy 1.26
runtime incompatibility was resolved by constraining the table-serialization
dependency to PyArrow <25. Matplotlib is retained for the existing Day 3 script;
Playwright was used temporarily for verification and is not an app dependency.

Existing analysis scripts, Day 2/3 reports and tracked aggregate outputs were
checked against their initial hashes and remain unchanged. Existing README and
requirements edits were preserved and extended for Day 4. Git checks confirmed that raw survey files, processed
row-level data and both detailed support-CSV paths remain ignored and are not
tracked or staged. The prototype binds to loopback with usage telemetry and
file watching disabled. Deployment and final submission remain later tasks.
