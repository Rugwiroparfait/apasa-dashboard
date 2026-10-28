# Architecture

APASA is a server-rendered Django application. One runtime handles HTML, authentication, CSV and text downloads, and static assets. There is no JavaScript build chain, external analytics dependency, or Excel parsing during a web request.

| Directory | Responsibility |
| --- | --- |
| `apasa/` | Settings, top-level routes, WSGI and portable database-test configuration |
| `accounts/` | Public landing, role navigation, authentication gate, health check and account provisioning |
| `planning/` | Versioned input/target registration, validation/quarantine, comparisons, forecast/scenario review, briefs, publication snapshots and follow-up |
| `evidence/` | Evidence loading, curation, presentation, views, templates, static assets and tests |
| `evidence/management/commands/` | Deterministic workbook extraction and optional normalized CSV/database workflows |
| `outputs/workbook_observations/` | Small deployment bundle and integrity checksum |
| `outputs/workbook_review_2026_10_28/` | Preserved inspection/audit artifacts; not part of the container image |
| `data/` | Original reference workbooks; excluded from container images |
| `docs/` | Architecture, data contracts and operating instructions |

## Request flow

Django security, session, CSRF and authentication middleware run before the workspace gate. `/`, `/accounts/login/` and `/health/` are public; evidence and downloads redirect anonymous users to sign-in. Login uses Django's session framework, password hashing and safe-next validation. Logout requires POST with a CSRF token. Static assets are served by WhiteNoise.

After login, district-group members enter the district workflow; other accounts enter the national workflow. Both roles can read both evidence journeys and can register/review planning records. A record author cannot approve their own submission. This is navigation personalization, not district-level data isolation. There is no private farmer dataset in this app.

The application database holds users, groups and sessions. In default CSV mode, evidence comes from committed, allowlisted public files. The optional evidence database adapter uses versioned normalized records; it remains separate from the workbook bundle. PostgreSQL credentials are read from environment variables; `.env` files are not loaded automatically.

## Visualization layer

`evidence/charts.py` prepares chart geometry from the exact source rows. `bar_chart` rejects mixed units, excludes non-numeric/non-finite/negative values from plotting, preserves real zeros and mock status, and computes zero-baseline widths. `seasonal_charts` groups by crop, measure, population, unit and season; paired seasonal charts share the same numerical scale within a crop/measure/population/unit. Broad selections show a labelled four-series preview; the full selection remains downloadable.

`evidence/chart.html` is the shared rendering component. It produces SVGs with accessible labels and source tooltips on desktop, readable bar rows on mobile, and an expandable exact-value/source table for both. Forms progressively update server-rendered charts, so no chart CDN, JavaScript data service or browser-only computation is required. Static files remain served by WhiteNoise.

## Data boundaries

National policy references remain in the existing curated inventory. Workbook observations are a separate source layer. The extraction command checks workbook hashes, validates measure and season headers, and exports exact cached source values with coordinates and hashes. The request loader verifies the bundle checksum and caches the immutable result for the process lifetime. Restart web workers after rebuilding or deploying a bundle.

Mock previews work on copies of source rows. They cannot update source files, normalized records or register references. CSV outputs preserve a boolean mock flag and explicit status. Policy notes retain their existing mock warnings and also list associated workbook observations with coordinates.

The AHS research page, loader, tests, routes, templates, images and aggregate-only historical artifacts have been retired. They remain recoverable in Git history. The sidebar has four destinations: Overview, National policy, National statistics and District statistics. Crop observations and evidence notes are contextual actions on a selected policy record, rather than standalone global navigation entries.

Optional normalized evidence models/import commands stay because the supported PostgreSQL adapter and its provenance/rollback tests still use them. Uploaded reference workbooks and inspection reports are source material; they remain unchanged outside the production image.


## Reviewed planning domain

`planning/models.py` separates versioned source batches, NST2/PSTA5 target versions, mapped assessments, model validations, saved scenario runs, action briefs, follow-up tasks and review events. These are independent of the legacy optional normalized-evidence adapter; CSV evidence mode still needs a database for authentication and this workflow.

`validation.py` enforces the controlled aggregate CSV contract. `calculations.py` implements comparison-v1, source uncertainty, exploratory regression, held-out model validation and bounded conditional scenarios. `services.py` locks review records, enforces author/reviewer separation and freezes approved calculation snapshots. `briefs.py` drafts factual templates or optionally calls the configured AI provider; it cannot publish or change canonical calculations. Views handle orchestration and forms; templates show simple results first and expandable methods/review details.

Real records follow draft → submitted → approved, or submitted → changes requested. Invalid source batches enter quarantine. Mocked examples use a separate demo state and cannot transition into official publication. Corrected sources link to their predecessors; targets use explicit versions; saved scenarios and approved comparison results retain their reviewed outputs. There is no in-place published-data editing endpoint.

Forecasting and advice have separate gates: a quantitatively passing candidate still needs independent model approval; scenario assumptions/results then need their own review before inclusion in a brief; the brief needs approval before implementation tracking. Follow-up outcomes are reported evidence and are never silently substituted into an approved source observation. Optional AI is an opt-in wording service, with a transparent local-template fallback and human sign-off.


`planning/ai.py` is a bounded Responses API transport, separate from statistical calculations. It resolves existing local credential aliases, denies redirects, enforces an explicit model allowlist and rolling request/token budgets, sanitizes provider errors, and records safe usage metadata. `AIQuotaLedger` serializes reservations; `AIRequestLog` records attempts without raw secrets or prompts. `AIExplanation` stores the question, unapproved wording, canonical facts and drafting provenance under the existing review workflow. Optional local `.env` loading does not override injected credentials.
