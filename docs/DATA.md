# Data provenance and interpretation

## Supplied sources

The remote update at `4ddc4ae` supplied 15 Excel workbooks: one register and 14 NISR workbooks spanning 2016–2026. The original review covers 871 sheets. All uploaded files and the review are preserved. `input_manifest.json` records input SHA-256 hashes; rebuilding fails if an input changes.

The new production bundle contains 348 entries from the six seasonal workbooks for 2024 A/B, 2025 A/B and 2026 A/B. There are 323 numeric observations and 25 unavailable source entries; the total is not a count of numeric estimates. It also retains 30 register rows, six indicator definitions across five register seasons.

## Extraction contract

`build_workbook_evidence` uses the supplied sparse cell audit, after checking the corresponding workbook hashes. It does not run formulas, refresh external references or save Excel files. Its output records the audit checksum as well as every source workbook checksum. A modified audit must be independently reviewed; matching workbook hashes alone cannot authenticate changes to the audit.

Production/yield selections require the exact cultivated-area/harvested-area/production/yield table title and exact measure headers. The current season must match the selected column's year/season header. Only current-season columns are extracted; comparative columns are not duplicated across releases. Crop and group labels stay as published and must not be summed together.

Adoption selections require the seeds or inorganic-fertilizer farmer-type table, the first percentage-of-farmers block, SSF/LSF headers, and a unique national/total row. Plot percentages, land percentages and seed-source composition tables are excluded. Percentages retain their published denominator labels; no cross-year methodology equivalence is asserted.

The app displays exact source values; numeric estimates are marked `observed`. Non-numeric values retain the original text and are marked `unavailable`. Blank, `(NA)`, dashes and missing cached results are not converted to zero. Stored formulas are recorded separately from cached values.

The compact bundle is checked against its accompanying SHA-256 file before use. Both must be reviewed and deployed together. This detects accidental corruption; it is not a digital signature or an independent provenance attestation.

## Scope limits and mock policy

Older annual/legacy workbooks remain review-only: their units, populations, formula behavior and seasonal columns need explicit mapping before any historical-series claim. No 2013/2014 workbook was supplied. Register geography and official target authority remain unresolved. Register baseline/target text is displayed verbatim with these warnings, separately from the existing reviewed policy inventory.

The user authorized mock data where data are missing. The app therefore offers explicit previews rather than inserting fictional values into official records. Workbook missing-cell previews use 1,000 MT, 1 MT/ha or 50% solely for layout; these are not estimates. Rows, banners and filenames identify them as MOCKED, and downloads include `mocked=True` and the original `source_value`. Real values are unchanged. Existing national-policy mock previews remain optional and labelled in pages and evidence notes.

No mock policy target, missing historical year, or synthetic national/district observation is silently presented as official evidence. There are no progress calculations because target comparability is not established.

## Refresh procedure

1. Obtain and review a new official workbook and its release provenance.
2. Update the inspection audit and manifest through the documented review process, preserving originals.
3. Review exact measure, season, population, geography and source cells; extend the extraction command explicitly when schemas differ.
4. Run `python manage.py build_workbook_evidence`, inspect the diff and re-run the test suite.
5. Deploy the bundle and checksum together, then restart workers and smoke-test the filtered page and export.

The original detailed review remains at `outputs/workbook_review_2026_10_28/review_note.md`.
