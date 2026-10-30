# APASA

A Django workspace for two agricultural planning roles in Rwanda:

- **National policymaker:** policy references, source-linked seasonal observations, and downloadable evidence notes.
- **District agriculture officer:** province, district and crop filters for published SAS 2026 Season B statistics.

The public landing page is at `/`; sign-in is at `/accounts/login/`. All evidence pages and downloads require authentication. Roles choose the initial workspace; both roles can read both journeys. Both roles can register aggregate sources, define cited policy targets, create comparisons and peer-review the other user’s submissions. Published inputs and results are immutable through the interface; corrections create new versions. No individual farmer or household data are accepted by the upload schema.

## Host on your VPS

For **apasa.inzuyange.com**, use [VPS deployment](docs/VPS.md) and `compose.vps.yaml`. The stack uses your existing Nginx Proxy Manager, a private PostgreSQL database with persistent storage, and the existing reviewed evidence files. No new public ports are opened. On the VPS run `bash deploy/vps.sh prepare`, privately edit the generated `.env.vps`, then run `bash deploy/vps.sh up`. The guide gives exact DNS, proxy and certificate settings, first-login credentials, backups and update commands.

## Host on Render

The [Render Blueprint](render.yaml) provisions a Python web service and persistent PostgreSQL. It includes the existing reviewed evidence files; raw Excel workbooks and local SQLite are unnecessary. In Render choose **New → Blueprint**, connect this private GitHub repository, select `main`, and enter your NVIDIA key securely as `NVIDIA_API_KEY`. The configured Starter web service and PostgreSQL plan are paid; review Render’s pricing before creating resources. No Render deployment has been created by this repository change.

Render generates a secret and unique initial passwords for `policymaker` and `district_officer`. Retrieve these in the web service’s Environment settings. [Render instructions](docs/RENDER.md) cover first login, domains, backups and verification. Build validates evidence and collects static files; pre-deploy migrates and provisions accounts; startup binds Gunicorn to Render’s `$PORT`.

## Local development

Python 3.12 is tested. `requirements.txt` declares supported dependency ranges; `requirements.lock` pins the validated deployment versions. From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py provision_accounts --demo
.venv/bin/python manage.py seed_planning_demo
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Development defaults (created only by the explicit `--demo` command):

| Role | Username | Development password |
| --- | --- | --- |
| National policymaker | `policymaker` | `ApasaPolicyDemo!2026` |
| District agriculture officer | `district_officer` | `ApasaDistrictDemo!2026` |

These accounts are for local demonstrations. Do not deploy this development database or these passwords. Production refuses demo provisioning. Re-running account provisioning preserves existing passwords. Administrators can reset a password with `python manage.py changepassword USERNAME`; there is no public registration or email-reset service.

CSV evidence is the default. Authentication now requires a database even in CSV mode; local development uses ignored SQLite. PostgreSQL is supported for production and for the optional versioned evidence import.

## Data and mocked previews

`/national-policy-evidence/` retains the reviewed 126-record policy inventory. `/workbook-evidence/` adds 348 source-linked entries from six 2024–2026 seasonal workbooks and the 30 supplied register entries. Crop observations are also linked to the national workflow and included in evidence-note downloads.

Non-numeric source cells are unavailable, not zero. An explicit preview control substitutes illustrative values only for unavailable cells. Every replacement is labelled **MOCKED**, exported with its status and `mocked` flag, and placed in a `-MOCKED.csv` download. Existing policy previews similarly carry mock warnings. Mock values never enter the official bundle or target calculations.

Register targets have unresolved policy provenance; several reproduce observed NISR values. No target attainment, annual aggregation, causal result or district ranking is calculated. Earlier annual workbooks remain available for review rather than being silently interpreted as a comparable time series.

Rebuild the compact workbook bundle, verifying all input hashes first:

```bash
.venv/bin/python manage.py build_workbook_evidence
```

The deployed app reads the compact JSON bundle, not Excel or the 30 MB audit. Raw survey microdata are not needed. Original uploaded workbooks and review artifacts are preserved.

## Target comparisons, scenarios and follow-up

Open **Compare & plan** (`/planning/`) for current value, target, remaining need, and practical next steps. National and district mocked demonstrations show the complete workflow immediately. For official reports, register and independently review the source and authenticated NST2/PSTA5 target, then review the comparison before publication. Invalid CSV uploads are quarantined with row-level errors.

Calculations include direction-aware gaps, percentage-point differences, baseline progress, required yearly/compound change, source-standard-error intervals and historical regression diagnostics. Forecast candidates require at least six comparable observations, a two-observation holdout test, acceptable RMSE and independent model approval. Saved assumptions/scenarios receive separate review before an action brief uses them. Advice approval precedes implementation tracking; owners can record outcomes, feedback and due/overdue actions.

Mocked records cannot be approved as official evidence. Incompatible periods, units, populations, geography or methods produce explanations instead of unsupported calculations. AI wording and evidence Q&A are optional. The app uses NVIDIA hosted inference with `NVIDIA_API_KEY` from your environment or ignored local `.env`; the existing `NVDIA_API_KEY` spelling is also supported. The selected model is `openai/gpt-oss-20b`. OpenAI credentials are no longer used. The factual local template works without a provider. No AI output publishes itself or establishes intervention effects.

See [the workflow guide](docs/PLANNING.md) and [statistical methods](docs/STATISTICS.md).

### Run AI on your computer

Keep your existing key private. Add or update the model settings in your ignored local `.env` without overwriting its other values:

```text
APASA_DEBUG=true
APASA_ALLOWED_HOSTS=localhost,127.0.0.1,[::1]
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=openai/gpt-oss-20b
APASA_AI_ALLOWED_MODELS=openai/gpt-oss-20b
```

After updating the checkout:

```bash
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py check_ai
.venv/bin/python manage.py check_ai --check-access
# Optional: explicitly send one small generation request using your API project.
.venv/bin/python manage.py check_ai --generate
```

Restart the app after changing environment variables. **Compare & plan → AI availability** shows configuration and local limits; **Ask the evidence assistant** explains a selected report. Generated wording is unapproved until a different user reviews it. Explicitly mocked demonstrations remain mocked even when AI explains them.

The client uses NVIDIA’s Chat Completions API at `integrate.api.nvidia.com/v1`, never switches provider/model automatically, and applies local caps of 8 requests/minute, 45/rolling 24 hours, a conservative 80,000-token/minute budget, and 1,200 output tokens per generation. NVIDIA’s account limits and available credits remain authoritative; provider failures produce a labelled local fallback. Live validation requires your locally configured NVIDIA key.

## Visual dashboards

The overview opens with evidence coverage and maize production charts. National statistics defaults to maize production; crop, measure, population and reporting-period controls update the source-linked charts and CSV selection. Season A and B remain separate, sharing a zero-based scale within the same crop, measure, population and unit.

District statistics provides a crop-comparison chart after a district is selected. Choose production, cultivated area, harvested area or yield; each chart uses one unit, crops remain alphabetically ordered, and the selected crop is highlighted. Summary cards are rounded to two decimals; exact values stay in source details.

Desktop SVGs and mobile bar rows show the same data without an external chart library or CDN. Missing values are not plotted as zero; mocked values are labelled and styled distinctly. Expand the source details for exact values. Sidebar navigation now contains only Overview, National policy, National statistics and District statistics; crop details and note actions remain beside the relevant policy record.

## Checks

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py test evidence accounts planning apasa.test_render apasa.test_vps evidence.database_checks --settings=apasa.test_settings
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python -m pip check
```

`apasa.test_settings` explicitly uses temporary SQLite for portable import tests. Existing public-evidence unit tests bypass only the authentication gate to isolate loaders and rendering; `accounts/tests.py` exercises real session authentication, roles, logout, CSRF, protected routes, and provisioning.

## Project guide

- [Reviewed planning workflow](docs/PLANNING.md)
- [Statistical specification](docs/STATISTICS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Data provenance and coverage](docs/DATA.md)
- [VPS deployment](docs/VPS.md)
- [Render deployment](docs/RENDER.md)
- [Deployment and operations](docs/DEPLOYMENT.md)
- [Cleanup and implementation record](docs/CHANGELOG.md)
- [Optional versioned evidence database](docs/public_evidence_data_layer.md)

Django is the single supported web runtime. The retired AHS research interface, routes, loader, published charts and aggregate artifacts have been removed from this application, along with the duplicate Streamlit runtime and unused preparation scripts. Their history remains in Git. Uploaded NISR workbooks and their audit are preserved.
