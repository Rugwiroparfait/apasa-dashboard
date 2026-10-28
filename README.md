# APASA

A Django workspace for two agricultural planning roles in Rwanda:

- **National policymaker:** policy references, source-linked seasonal observations, and downloadable evidence notes.
- **District agriculture officer:** province, district and crop filters for published SAS 2026 Season B statistics.

The public landing page is at `/`; sign-in is at `/accounts/login/`. All evidence pages and downloads require authentication. Roles choose the initial workspace; both roles can read both journeys. Neither role can upload or edit evidence through the app.

## Local development

Python 3.12 is tested. `requirements.txt` declares supported dependency ranges; `requirements.lock` pins the validated deployment versions. From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py provision_accounts --demo
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

## Checks

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py test evidence accounts evidence.database_checks --settings=apasa.test_settings
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python -m pip check
```

`apasa.test_settings` explicitly uses temporary SQLite for portable import tests. Existing public-evidence unit tests bypass only the authentication gate to isolate loaders and rendering; `accounts/tests.py` exercises real session authentication, roles, logout, CSRF, protected routes, and provisioning.

## Project guide

- [Architecture](docs/ARCHITECTURE.md)
- [Data provenance and coverage](docs/DATA.md)
- [Deployment and operations](docs/DEPLOYMENT.md)
- [Cleanup and implementation record](docs/CHANGELOG.md)
- [Optional versioned evidence database](docs/public_evidence_data_layer.md)

Django is the single supported web runtime. The duplicate Streamlit app and unused private-survey preparation scripts were removed; their history remains in Git. Published AHS summary assets and the Django read-only research page remain separate from official policy and district evidence.
