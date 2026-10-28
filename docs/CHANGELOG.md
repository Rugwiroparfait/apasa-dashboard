# Implementation record — 28 October 2026

## Starting point

Updated the existing checkout by a clean fast-forward from `fa42d10` to remote `4ddc4ae`, which added the source workbooks and workbook review. Original uploaded workbooks and review artifacts were not modified. No public deployment was performed. The implementation is being committed and pushed to GitHub at the user’s request.

## Delivered changes

- Public landing page and Django session authentication with CSRF-protected login/logout.
- Explicit account provisioning for national policymaker and district agriculture officer groups. Their initial workspace differs; both can read both evidence journeys. No self-registration, evidence editing or farmer-level access is provided.
- Development-only default accounts; production requires secure credentials, rejects demo provisioning and known demo passwords, and preserves existing passwords on repeat runs.
- Authentication gate covering evidence pages, figures, CSVs and evidence-note downloads.
- Deterministic workbook extraction with input hash checks, validated season/measure/population headers, source cells, original cached values and formula metadata.
- Compact 348-entry seasonal bundle: 323 numeric observations and 25 unavailable entries, comprising 162 production entries, 162 yield entries, 12 improved-seed adoption entries and 12 inorganic-fertilizer adoption entries. Thirty supplied register rows are displayed separately with provenance warnings.
- Workbook filters, CSV downloads, optional mocked missing-cell previews, links from national policy evidence, crop observation tables and source-linked evidence notes.
- Production settings, pinned runtime dependencies, Gunicorn, WhiteNoise, HTTPS/cookie/host settings, database health endpoint, non-root Docker image, proxy configuration example and operations documentation.
- Consistent Python formatting across the Django codebase with Black 26.10.1.

## Removed and retained material

Removed `app.py`, `.streamlit/config.toml`, `tests/test_dashboard.py`, `analysis/prepare_section3_4.py` and `analysis/day3_exploratory_analysis.py`. These duplicate or unused runtimes remain recoverable in Git history. Removed NumPy, pandas, Matplotlib, Streamlit, Altair and PyArrow from production dependencies.

Retained Django AHS research code, its published aggregates/images and loader tests because this feature remains linked and used. Retained optional normalized evidence models/import commands and integration tests because they provide the supported PostgreSQL adapter and provenance validation. Retained uploaded workbooks, review artifacts and source documentation; they are not dead application code and were not deleted. The production image excludes raw workbooks and the large review audit.

## Validation

- 52 Django tests passed across `evidence`, `accounts`, and `evidence.database_checks` using portable SQLite test settings.
- Django system checks, migration consistency, dependency consistency and whitespace checks passed.
- Rebuilding workbook evidence verified every source workbook hash; original data and review files have no diff.
- Both default development accounts passed live HTTP login and role redirects through Gunicorn, plus workbook filters, district selection, evidence-note download, mocked CSV, static assets, health and anonymous redirect checks.
- The Docker image built using locked dependencies with TLS verification enabled. A build CA was mounted for the managed environment; no session CA or credential was embedded in the image.
- Production container smoke test passed as the image's non-root user with fresh temporary generated credentials and a fresh container-local database: migrations, account provisioning, `check --deploy --fail-level WARNING`, Gunicorn, secure cookies, CSRF login, both role redirects, national/district/workbook evidence, mocked download, health, and hashed static assets.
- The container test identified and resolved restrictive copied-file permissions; production static collection uses manifest storage.

## Boundaries still requiring deployment configuration

This work prepares and validates the application; it does not publish it. A real hosting destination, domain, TLS termination, secure production secrets, persistent database/storage, login rate limiting and backups must be configured by the deployment operator. The Nginx fragment is a template, not an installed TLS service. Live PostgreSQL, a real domain/TLS certificate and backup restoration were not tested; portable SQLite integration and the production container workflow were tested.

The older annual/legacy workbooks remain review-only. No missing historical records or policy target provenance were fabricated. Register targets must not be treated as authenticated policy goals. Mocked values are demonstration placeholders, labelled in pages and exports, never official evidence.


## Follow-up: visual dashboards and removal of the research interface

The user identified remaining clutter in the overview and requested graphs. Removed the separate AHS research feature, including its routes, loader, five feature tests, templates, published charts, aggregate summaries and historical research-only reports. Removed the global crop-detail and note navigation entries; their contextual policy actions remain. Uploaded NISR workbooks and the workbook review were not changed.

Replaced the long overview with a compact coverage summary, paired maize-production charts and two short workflow entry cards. Added seasonal charts to national statistics, selected policy records and crop-detail pages. Added district crop-comparison charts with a measure selector and selected-crop highlight. Long observation tables and interpretation details are collapsed by default. District cards display two-decimal summaries while exact source values remain available.

Charts preserve zero baselines, exact source provenance, missingness and mock labels. Season and population series stay separate; paired charts use shared scales within a crop/measure/population/unit. Mock values use a gold outlined/striped style plus text labels. Mobile layouts use readable bar rows with visible values rather than requiring horizontal chart scrolling. No external chart dependency was added.

Validation: 53 Django tests passed, including new checks for mixed-unit rejection, zero versus missing values, non-finite values, season/population separation, source-linked charts, filters/download agreement, mocked chart labels, district measures/highlighting and retirement of old routes. Chromium checks covered desktop and 390px mobile layouts, national filter changes, district measure changes, four-link navigation, SVG rendering, page overflow and JavaScript errors. Screenshots were inspected; mobile chart readability and low-contrast labels were corrected during review. The updated production image built successfully and its non-root smoke test passed, including authenticated overview and national-chart assertions, deployment checks, secure sessions, both role journeys, static assets and health.
