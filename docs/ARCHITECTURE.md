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


`planning/ai.py` is a bounded NVIDIA Chat Completions transport, separate from statistical calculations. It resolves existing local credential aliases, denies redirects, enforces an explicit model allowlist and rolling request/token budgets, sanitizes provider errors, and records safe usage metadata. `AIQuotaLedger` serializes reservations; `AIRequestLog` records attempts without raw secrets or prompts. `AIExplanation` stores the question, unapproved wording, canonical facts and drafting provenance under the existing review workflow. Optional local `.env` loading does not override injected credentials.


Render uses native Python with `render.yaml` and three small deployment scripts. `DATABASE_URL` selects persistent PostgreSQL; Render startup refuses ephemeral SQLite. The platform hostname is added to allowed hosts and CSRF origins; custom domains use the existing explicit environment lists. Evidence remains versioned release files, validated during build/release. `/health/` is exempt from HTTPS redirection so Render’s internal probe can read database readiness. AI credentials resolve only NVIDIA aliases; the old OpenAI bindings are ignored.


`compose.vps.yaml` isolates the VPS web/database in project `apasa`. NPM shares only the external `apasa-proxy` network with the web alias `apasa-web`; PostgreSQL stays on an internal network and persistent named volume. No APASA ports are published. `deploy/configure_vps.py` generates non-overwriting private settings; `deploy/vps.sh` scopes lifecycle/backups to APASA. Shared `deploy/release.sh`/`start.sh` serve VPS, container and Render wrappers. `APASA_RUN_RELEASE=true` explicitly enables one-instance release-on-start outside Render.


Authenticated dashboards use `evidence/workspace_shell.html`. Public pages share `accounts/public_shell.html`; sign-in has a standalone compact form. `evidence/tokens.css` defines the shared forest-green/gold/neutral palette and system typography. A version-pinned Feather SVG subset and its MIT license are served locally; no icon or font CDN is used. Charts remain server-rendered SVG/HTML without a new library. Overview counts come from the workbook bundle and current district adapter. Seasonal bars use one zero-based scale and flat green series; gold is reserved for evidence cautions and explicitly mocked states. Exact values, statuses and citations remain available in tables; mobile uses labelled bars on the same scale.

The persistent assistant panel extends the existing `planning.views.question_create` endpoint: `/planning/ai/ask/` handles signed public dashboard context, while existing comparison `/ask/` URLs retain canonical calculation facts and saved `AIExplanation` review records. Both paths call `planning.briefs` and the same NVIDIA `planning.ai.generate` transport/ledger, model allowlist, timeout and rolling limits. Public-page threads use the existing server-side session (four turns, at most three context hashes); only two bounded prior turns accompany a follow-up. Context tokens are user-bound, signed, and expire after 30 minutes. The server whitelists published evidence chart values, source metadata and validated filters; browser-supplied facts are ignored, private planning drafts are not serialized, and mocked previews are rejected by the published-dashboard assistant. Opening a page does not call the provider. Errors return no fabricated AI answer. Reviewed comparison side-panel answers use the original generation/review path and remain unapproved.

### Public assets and assistant layout

The landing page contains audience, feature, workflow and evidence-limit sections.
The original full-width layered hero is restored with responsive local WebP
landscape, tractor and crops, plus a compressed dust layer and the existing flag.
Matching responsive preload, explicit dimensions and asynchronous decoding reduce
loading costs while preserving the artwork, wordmark and motion controls. Original
PNGs remain source assets. Below-the-fold sections use HTML and local SVG icons.
All evidence routes still require authentication; public workflow links preserve
the existing login redirects.

The assistant opens from a fixed bottom-left launcher in an actual shadcn New York
Popover, with Button and Card components. Tailwind CSS v4 compiles shared button,
card and input styles for both React and Django markup. The independently scrolling
message thread retains its fixed composer. Empty context labels are omitted only
from presentation; canonical signed evidence facts are unchanged. Missing credentials
disable panel generation controls. The existing provider, limits, signed contexts,
session history and reviewed-report explanations are reused. Sources remain visible
with replies and on reload; the complete-response endpoint does not support streaming.

The frontend build is `npm ci && npm run build`. Compiled `ui.css` and `ui.js` are
checked in and collected by the existing Python-only deployment pipeline; no Node
runtime, icon CDN or Tailwind browser compiler is required in production.

### Role-aware goal home

The default authenticated `/workspace/` entry redirects to `/planning/`. Safe explicit login `next` destinations still work. The home defaults to national goals for national policymakers and local (non-`RW`) goals for district officers; accounts with both roles or superuser access default to national scope. These are presentation defaults, not additional permission gates. No user district assignment exists: users explicitly select the reviewed goal geography, and shared evidence routes retain their existing access rules.

Goal cards use `report_result`, including approved immutable snapshots, and select the latest reviewed comparison per target version. Drafts, mocked inputs and demonstrations are excluded from official counts and progress. Incompatible comparisons show their validation reasons. Percentages describe baseline-to-target change, with only the visual bar bounded to 0–100; no aggregate progress score is calculated.

District selectors submit GET selections automatically, resetting district/crop when their parent changes. The single enhanced Apply control opens the existing shadcn chart dialog. Without JavaScript, Load selection submits the form and the chart/source disclosure remains available.

When no comparable official result exists for a selection, the progress home automatically displays explicitly labelled invented demonstrations. `planning.demo_examples` supplies the same national and district examples to the existing development seeder and to a stateless fallback using unsaved model instances and the existing comparison engine. GET requests do not seed or modify the database. Seeded demonstration reports retain links to their complete workflow; unseeded examples show progress, invented history charts and illustrative next steps directly on the dashboard. Official validation reasons remain visible and users can explicitly switch between official evidence and demonstration modes. Demonstrations never count as reviewed official goals or acquire the selected real geography.

### Explicit district demonstration journey

The published repository adapter is unchanged. `evidence.demo_data` generates a separate deterministic aggregate-only dataset solely for the explicit `data=demo` district mode. Period selectors use only the active dataset's periods. Synthetic numerical values have no source agency or report/workbook URL; geographic labels alone are reused from the public administrative extract. `generate_demo_evidence` exports only under `data/demo`, refuses unrelated files, and is never part of deployment. Manifest and README in that directory document the recipe and the existing development-only planning seeder.

The assistant signs demo origin, coverage and period alongside chart facts; only the explicit server-generated demonstration branch is allowed to explain synthetic dashboard data. The existing mixed-preview rejection, signature validation, actor permissions, session handling, provider transport and quota ledger remain in force. Provider calls still require an explicit question.
