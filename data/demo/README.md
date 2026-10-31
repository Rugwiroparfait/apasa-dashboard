# APASA interface demonstrations

**Synthetic / illustrative — not official statistics.** Generation date: **2026-10-31**. Version: `apasa-interface-demo-v1`.

These aggregate examples were generated for APASA interface demonstration. They are **not official NISR or MINAGRI statistics**, authenticated PSTA5 goals, forecasts or evidence of programme effects. Do not use them for analysis or policy decisions. No household/person records, real sampled population, sample size, verification or source organisation is invented.

`manifest.json` records the exact variables, units, formula assumptions, periods and source inputs. Geography labels/IDs alone come from the existing district CSV. All numerical values and targets are invented. The annual planning and seasonal district examples are separate; do not join them or substitute one for published statistics.

## Use in the app

- `/planning/`: automatic, clearly labelled annual demonstrations when comparable reviewed evidence is unavailable. Select Demonstration to explore them explicitly. Reviewed real comparisons remain the default when available.
- `/district-crop-statistics/`: defaults to the **published** 2026 B dataset. Select **Demonstration data** (`?data=demo`) for three districts, three crops, four measures and three illustrative periods. Published and synthetic statistics never share a series in this mode.
- Published national policy and seasonal workbooks retain their actual sources, units, dates and comparison warnings. Synthetic planning targets are never substituted for policy references.

## Repeatable commands

Use the project's Python environment (`venv/bin/python` in this checkout):

```bash
venv/bin/python manage.py seed_planning_demo
venv/bin/python manage.py generate_demo_evidence
```

`seed_planning_demo` is the existing **development-only** loader (requires `DEBUG=True`). It creates/reuses two MOCKED source batches, two target versions, two comparisons and two demonstration forecast models. It refuses collisions with non-demo records and never changes published records, permissions or passwords. Re-running does not duplicate records. Full comparison, scenario and assistant workflows remain available for these saved examples.

`generate_demo_evidence` writes the deterministic district JSON fixture to `data/demo/district_statistics.json`. It can only write within `data/demo` and refuses to replace unrelated data. It does not write to the database. The read-only district demonstration uses the same deterministic generator, so it also works without running a loader. The exported fixture is for inspecting/reproducing these records; it is not imported into the published adapter.

Neither command runs on GET requests or automatically during deployment. No schema changes are needed. Existing real records and CSVs are not overwritten, deleted, relabelled or used as synthetic statistical values.

## Observation-upload CSV (version 1.0)

Use **`data/demo/synthetic_rwanda_crop_observations_v1.csv`** to demonstrate **Add an observation dataset** at `/planning/sources/upload/`. This is a separate, upload-compatible dataset, not the district-page fixture or the earlier two planning examples.

It contains **1,536 observations**, all `is_mocked=true`: 2019–2026, Seasons A/B/C plus annual observations, three crops (Maize, Bush bean, Cassava), Rwanda national scope (`RW`) and three districts (`11` Nyarugenge, `12` Gasabo, `24` Huye). Four measures use the parser's codes and units: `cultivated_area`/`harvested_area` in Ha, `yield` in Kg/Ha and `production` in MT. No persons, households, farmer identifiers or provincial estimates are included. The national series represents a separate illustrative whole-country series, not a total of these three districts.

The exact CSV headers match the app's downloadable template:

```text
measure,crop,value,unit,period,geography_code,geography,population,source_reference,standard_error,is_mocked
```

Annual areas and production sum the three synthetic seasons. Annual yield is the harvested-area-weighted yield, rounded to eight decimals. Never add annual rows to seasonal rows. Seasonal production = harvested Ha × yield Kg/Ha ÷ 1,000. No standard errors or sampling claims are invented. All required values are present: the parser requires unavailable observations to be omitted, rather than uploaded with blanks or substituted zeros. Each row contains an explicit synthetic source reference. The exact formulas, coverage, size and SHA-256 are recorded in `observation_upload_v1.manifest.json`.

### Form metadata and loading steps

1. Sign in as a national policymaker or district officer. Open **Manage evidence & review → Add an observation dataset** (`/planning/sources/upload/`).
2. Enter these values:

| Form field | Value |
| --- | --- |
| Dataset name | DEMO — Synthetic Rwanda crop observations (not official) |
| Synthetic demonstration dataset | **Checked** |
| Publication or source URL | **Leave empty**; no publication URL exists |
| Data origin | Synthetic illustrative data generated for APASA demonstration; not official NISR or MINAGRI statistics. |
| Publication, table and release/version | APASA interface demonstration dataset, version 1.0; generated 31 October 2026 |
| Methodology identifier | APASA-SYNTH-DEMO-2026-V1 |
| File | synthetic_rwanda_crop_observations_v1.csv |
| Aggregate-only declaration | **Checked**: this file contains only aggregate observations; this does not claim official approval |

3. Click **Save for validation**. The actual CSV parser validates every row. Expect a **MOCKED demonstration** source record with **Synthetic / illustrative — not official statistics** labels, origin/release details and a source table. No independent official approval is appropriate or possible for this file.
4. Re-uploading the identical demo with identical metadata as the same user reopens the existing demo source. Published sources and other users' records are never overwritten. Changes to file content or metadata create a separate demo version.
5. To illustrate a comparison, create a **MOCKED demonstration target** with the same methodology, crop, measure, unit, population (`Synthetic aggregate crop coverage; no sampled farmer population`) and exact geography. Use the same period type for baseline, observation and target (e.g. 2019 / 2026 / 2028 annual, or 2019 Season B / 2026 Season B / 2028 Season B). Select this demo dataset and one matching row in **Compare a goal**. For the invented target, leave the publication URL blank and describe the synthetic origin in its source reference. All targets and resulting comparisons must remain synthetic; never pair this dataset with an official target or approve it as official evidence. Existing seeded examples have a different methodology/population and are not compatible targets for this new CSV.
6. Existing national/district published charts remain unchanged. Comparison charts created from this source carry their own synthetic labels; they are not added to official series.

Regenerate the CSV and its manifest safely:

```bash
venv/bin/python manage.py generate_observation_demo
```

The generator uses the real `validate_csv` function before writing. It is deterministic, has no database writes, and refuses to overwrite different files. It is not part of deployment. The file is already generated; no command is required before uploading it.
