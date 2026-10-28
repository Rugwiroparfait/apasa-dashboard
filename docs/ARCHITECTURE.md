# Architecture

APASA is a server-rendered Django application. One runtime handles HTML, authentication, CSV and text downloads, and static assets. There is no JavaScript build chain, external analytics dependency, or Excel parsing during a web request.

| Directory | Responsibility |
| --- | --- |
| `apasa/` | Settings, top-level routes, WSGI and portable database-test configuration |
| `accounts/` | Public landing, role navigation, authentication gate, health check and account provisioning |
| `evidence/` | Evidence loading, curation, presentation, views, templates, static assets and tests |
| `evidence/management/commands/` | Deterministic workbook extraction and optional normalized CSV/database workflows |
| `outputs/workbook_observations/` | Small deployment bundle and integrity checksum |
| `outputs/workbook_review_2026_10_28/` | Preserved inspection/audit artifacts; not part of the container image |
| `data/` | Original reference workbooks; excluded from container images |
| `docs/` | Architecture, data contracts and operating instructions |

## Request flow

Django security, session, CSRF and authentication middleware run before the workspace gate. `/`, `/accounts/login/` and `/health/` are public; evidence and downloads redirect anonymous users to sign-in. Login uses Django's session framework, password hashing and safe-next validation. Logout requires POST with a CSRF token. Static assets are served by WhiteNoise.

After login, district-group members enter the district workflow; other accounts enter the national workflow. Both roles have read-only access to both journeys. This is navigation personalization, not district-level data isolation. There is no private farmer dataset in this app.

The application database holds users, groups and sessions. In default CSV mode, evidence comes from committed, allowlisted public files. The optional evidence database adapter uses versioned normalized records; it remains separate from the workbook bundle. PostgreSQL credentials are read from environment variables; `.env` files are not loaded automatically.

## Data boundaries

National policy references remain in the existing curated inventory. Workbook observations are a separate source layer. The extraction command checks workbook hashes, validates measure and season headers, and exports exact cached source values with coordinates and hashes. The request loader verifies the bundle checksum and caches the immutable result for the process lifetime. Restart web workers after rebuilding or deploying a bundle.

Mock previews work on copies of source rows. They cannot update source files, normalized records or register references. CSV outputs preserve a boolean mock flag and explicit status. Policy notes retain their existing mock warnings and also list associated workbook observations with coordinates.

The old Streamlit runtime and analysis scripts were removed. Django's AHS research page stays because it is still linked and tested; its aggregate inputs and image allowlist are required. Database models/import commands stay because the optional adapter and its provenance/rollback tests use them. Uploaded reference workbooks, inspection reports, and published research assets are retained as source material rather than discarded as dead code.
