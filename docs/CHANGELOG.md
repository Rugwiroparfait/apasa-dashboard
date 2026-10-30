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

## Follow-up: reviewed engineering workflow, target comparisons and AI

Implemented the supplied workflow diagrams as the `planning` Django app, linked from both planning journeys. It includes controlled aggregate CSV registration, row-level validation/quarantine, cited NST2/PSTA5 target versions, explicit mapping checks, independent peer review, publication, immutable calculation/scenario snapshots, source-linked reports, and action/outcome tracking with due/overdue queues. Invalid batches retain hashes/errors rather than partially accepted rows. Published records have no in-place editing endpoint; corrections create new versions.

Added comparison-v1 calculations: direction-aware remaining gaps, percentage-point differences, baseline progress, required linear/compound yearly pace, source-standard-error intervals, exploratory historical OLS diagnostics, Student-t intervals, held-out forecast evaluation against a carry-forward baseline, bounded prediction intervals and assumption sensitivity. Forecasting requires at least six comparable observations, two held out, an acceptable RMSE and independent model approval. Saved scenario assumptions need their own review before advice uses them. No causal intervention effect, missing variance or authenticated policy target is fabricated.

Added two development-only, explicitly MOCKED national/district walkthroughs. Mocked sources, targets, models, scenarios and AI text cannot be promoted to official publication. Existing uploaded NISR workbooks and review artifacts remain unchanged. Original source dashboards remain release-based; new source versions appear in reviewed planning reports rather than silently replacing those CSVs.

AI features now include evidence questions, plain-language explanations and action-brief drafting, with unchanged canonical calculation facts and provenance attached. The app supports the user's local `chat_openai_key` and ignored `.env` file without requiring it in this cloud machine. It selects `gpt-5.4-mini` from the user's supplied API Free tier listing and uses the Responses API with low reasoning effort. An allowlist prevents automatic model fallback. Serialized rolling request/token budgets enforce caps below the shown model limits; there are no automatic retries, billing changes or background generation. Raw keys and provider error bodies are not logged. AI output remains unapproved until another trusted user reviews it.

Local factual drafting remains usable when no key is available or the provider rejects a request. The UI never labels that fallback as a real AI response. Safe model-status, explicit read-only model access checks and `manage.py check_ai` diagnostics were added. Rate-limit listings do not establish credits or free billing; the provider's project settings remain authoritative. Live API generation could not be tested here because the user explicitly keeps the key on their own computer.

Validation completed: **96 tests passed** across existing evidence, authentication, planning, AI transport/workflow and portable database imports. Tests cover numerical boundary cases, incompatible dimensions, zero/missing data, conversions, held-out accuracy, publication snapshots, cross-user approval, scenario review, quarantine/correction, follow-up ownership, model allowlists, request/token limits, sanitized quota errors, incomplete responses, mocked provider success and transparent fallback. No test suite spends real API credits.

Desktop and 390px mobile Chromium checks passed for comparisons, source/target forms, observation selection, saved scenarios, evidence questions, local fallback, action drafting, AI availability/connection checks, chart rendering and page overflow. The production Docker image built and ran as its non-root user; disposable smoke checks passed for migrations, deployment settings, both secure user sessions, source/target peer review, frozen comparison, model/scenario approval, approved brief, follow-up, local AI fallback, report download, static assets and health. No public hosting deployment or live PostgreSQL/AI entitlement verification was performed.

Documentation now includes `docs/PLANNING.md`, `docs/STATISTICS.md`, updated architecture/deployment guidance, local AI commands and an empty-valued `.env.example`. Four planning migrations and the pinned SciPy/NumPy/python-dotenv dependencies are included. Apply migrations before starting the updated app; production does not seed demonstration data or approvals.


## 2026-10-30 — NVIDIA provider and Render readiness

Replaced the OpenAI Responses integration with NVIDIA hosted Chat Completions, using `openai/gpt-oss-20b`, `NVIDIA_BASE_URL` and `NVIDIA_API_KEY`/`NVDIA_API_KEY`. Old OpenAI credentials/settings no longer select a provider. Retained bounded requests, safe error handling, canonical statistical facts, explicit local fallback and independent review. Completed assistant content is used; truncated/private-reasoning output is rejected.

Added `render.yaml`, Python runtime pin, build/release/start scripts and persistent PostgreSQL `DATABASE_URL` configuration. Render hostname/CSRF setup is automatic, health probes avoid redirect loops, and Render rejects ephemeral SQLite. Production accounts use generated secure credentials and are preserved across releases. Existing policy/district CSV and checksummed national workbook bundle ship unchanged; build/release validate all three. No raw inputs, local database, demo accounts or mocked data are seeded in production. Render services must be created separately; this change does not publish cloud environment settings or provision hosting resources.

Validation: all 106 Django tests passed, including NVIDIA transport/alias/error tests, PostgreSQL URL/Render settings tests and existing evidence/workflow suites. Migration consistency, dependency checks, shell syntax and YAML parsing passed. The non-root production image passed authentication, static assets, evidence, review/model/scenario/brief/follow-up and local-AI-fallback smoke checks. Render release/start scripts were exercised against disposable PostgreSQL 17: HTTP health probe, secure HTTPS sessions, both role journeys and downloads passed; repeated release and container restart preserved a changed password and saved planning draft. All three packaged datasets validated; original data/bundles were unchanged. No live NVIDIA generation or Render resource creation was performed.


## 2026-10-30 — Manual Render Docker startup recovery

The supplied Render log confirms a manually created Docker service, not the native Python Blueprint. Its runtime had no `DATABASE_URL`, so the intentional persistence guard prevented worker boot. Added an explicit container startup: actionable missing-setting errors, Render-only release commands before workers, and platform-selected port/concurrency. Included release/start scripts in the image and documented how to connect the existing service to PostgreSQL and configure initial accounts. Native Blueprint behavior is unchanged; the persistence guard remains enabled. Manual Docker startup is supported for one instance; multiple replicas use a separate release phase.

Validation: all 108 Django tests passed. The rebuilt non-root image was started with its actual default command against disposable PostgreSQL 17; automatic migrations/provisioning, Render-selected port, HTTP health, secure role logins, evidence pages/downloads and persistence across restart passed. Missing database/secret errors were tested without exposing credential values.


## 2026-10-30 — VPS deployment for apasa.inzuyange.com

Added a project-scoped Docker Compose stack for the supplied VPS/Nginx Proxy Manager layout: persistent PostgreSQL 17, a non-root web service, internal database network, and external proxy network with alias `apasa-web`. No application/database host ports are published, so existing services keep their ports. Added one-time mode-600 secret generation without overwrites, idempotent proxy attachment, Compose lifecycle commands, private custom-format backups and a domain-specific DNS/NPM/SSL/update/recovery guide. Shared release/start scripts now serve VPS and backwards-compatible Render wrappers. Container release-on-start outside Render is explicitly enabled with `APASA_RUN_RELEASE=true` for one web instance. Raw inputs, private environment files and backups are excluded from builds; reviewed release evidence is unchanged.

Validation: all 112 Django tests passed; migration consistency, dependency checks, shell syntax and Compose validation passed. The actual Compose stack passed PostgreSQL startup and network/port checks. Repeating preparation left the test proxy running without restart. A disposable nginx HTTPS proxy with a trusted test certificate passed secure sessions for both roles, role redirects, evidence pages/charts/downloads, and local AI fallback. A mode-600 custom-format backup restored into a separate test database; full web/database container recreation preserved passwords and a saved planning draft. Tests used generated disposable credentials and data. No commands were run on the real VPS; public DNS, the existing NPM installation, Let's Encrypt issuance and live NVIDIA generation still require the documented live checks.
