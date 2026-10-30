# Deploy APASA on Render

## What gets hosted

The committed `render.yaml` creates one Python 3.12 web service (Starter) and a persistent PostgreSQL database (`basic-256mb`) in Frankfurt. These plans are paid: review Render pricing before confirming resource creation. The service uses the repository's `main` branch; select that branch when creating the Blueprint. No hosting resources are created by a GitHub push alone.

The checked-in evidence is already ready to serve:

- `docs/day6_indicator_comparability.csv`: 126 reviewed policy inventory records.
- `outputs/day7/official_sas_2026_b_district.csv`: 1,800 published district/crop/measure records.
- `outputs/workbook_observations/evidence.json` and checksum: 348 national workbook entries, with original provenance and unavailable-value states.

The build does not regenerate evidence or require the raw `data/` directory. Missing observations stay missing; no mocked replacements or fictional targets are installed. The optional demonstrations remain development-only. New uploads, target versions, accounts, review history and saved results persist in PostgreSQL. A redeploy changes code/static evidence but preserves these database records. Existing local planning drafts are not automatically copied to Render.

## Create the service

1. Push the repository changes to `main`.
2. In Render, choose **New → Blueprint**. Grant Render access to the private `Rugwiroparfait/apasa-dashboard` repository and select `main` and the root `render.yaml`.
3. Enter `NVIDIA_API_KEY` through Render's secure environment UI. Use the real key from your computer; no key is stored in the Blueprint. The local alias `NVDIA_API_KEY` also works, but the Blueprint uses the correctly spelled name. If AI is not required, leave the credential unset/blank: the app retains explicitly labelled local factual drafting.
4. Review resource pricing, then create the Blueprint. Render generates `APASA_SECRET_KEY` and two distinct initial account passwords. Keep them private and keep the secret stable across releases.
5. Watch the build and pre-deploy logs. Build installs `requirements.lock`, validates evidence, and collects WhiteNoise assets. Pre-deploy runs migrations once, provisions the two accounts transactionally, checks production settings, and validates evidence again. Gunicorn binds to Render's `PORT`; `/health/` checks PostgreSQL.
6. Open the assigned HTTPS URL. Retrieve the generated `APASA_POLICYMAKER_PASSWORD` and `APASA_DISTRICT_PASSWORD` from the web service's Environment settings and sign in as `policymaker` and `district_officer`. The passwords are not printed in application logs. Both users retain independent-review responsibilities.

Do not run `provision_accounts --demo` or `seed_planning_demo` in production. Existing accounts and passwords are preserved during later releases. To change one, use the Render shell with `python manage.py changepassword policymaker` (or `district_officer`), then remove obsolete initial-password variables. Avoid changing the variables expecting a password reset; provisioning intentionally does not reset accounts.

## Environment and domains

The Blueprint wires `DATABASE_URL` from PostgreSQL's private connection string, generates secrets, enables production settings and trusted TLS proxy handling, and pins NVIDIA's hosted endpoint/model. PostgreSQL public access is disabled by `ipAllowList: []`. Keep both services in the same Render region/workspace. Do not expose the database publicly or use Render's ephemeral service filesystem for SQLite.

The app automatically adds `RENDER_EXTERNAL_HOSTNAME` to allowed hosts and `https://HOSTNAME` to CSRF trusted origins. If you add a custom domain in Render, also set:

```text
APASA_ALLOWED_HOSTS=your-domain.example
APASA_CSRF_TRUSTED_ORIGINS=https://your-domain.example
```

The assigned Render hostname still works. Keep `APASA_DEBUG=false`, `APASA_TRUST_PROXY=true`, secure cookies and HTTPS enabled. Health alone is exempt from redirection for Render's internal probe; it returns no evidence, credentials or database details.

NVIDIA configuration:

```text
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=openai/gpt-oss-20b
APASA_AI_ALLOWED_MODELS=openai/gpt-oss-20b
```

`NVIDIA_API_KEY` takes precedence over `NVDIA_API_KEY`. Old `chat_openai_key`, `OPENAI_API_KEY`, `APASA_AI_API_KEY` and `APASA_AI_MODEL` settings are ignored; remove them from the Render service to avoid confusion. The `openai/` prefix in the model ID names the model publisher; requests go to NVIDIA, never OpenAI. No additional provider package or GPU is required on Render.

## Verify the first deployment

In the Render shell:

```bash
python manage.py check --deploy --fail-level WARNING
python manage.py validate_deployment_data
python manage.py check_ai
python manage.py check_ai --check-access
# Optional explicit live generation; subject to your NVIDIA quota:
python manage.py check_ai --generate
```

Verify the landing page and sign-in, both role redirects, national policy, national statistics, district/crop filters, charts, CSV/brief downloads and sign-out. Create a small aggregate draft and confirm it survives redeploy. One user's submission must require the other user's approval. Confirm missing/unsupported target comparisons display their evidence gaps rather than invented attainment.

A key on your local computer is not automatically available on Render. API failures produce a labelled local fallback. Live NVIDIA generation must be verified with the configured operator key; automated tests mock network calls and never spend API credits.

## Operations and recovery

Enable PostgreSQL backups appropriate to the selected Render plan and test restoration before important use. Back up before migrations and retain previous code releases. Do not delete/recreate the database to redeploy the app. Set up Render health/error monitoring; periodically run `python manage.py clearsessions`. For a rollback, verify schema compatibility first; keep the database backup alongside the previous code/data release.

Use Render or an upstream edge service to limit sign-in attempts; Django authentication does not itself implement brute-force throttling. Application aggregate uploads are limited to 2 MB/5,000 rows. No raw rejected upload, local `.env`, raw workbooks or keys belong in build logs or source control.

Do not change this Blueprint to a free ephemeral SQLite service: it would lose accounts and saved work. An alternate free-tier deployment needs a separately persistent database and migration/provisioning before startup; this Blueprint deliberately supplies the supported durable configuration.

## Validation recorded for this release

The 106-test suite and disposable production image passed. Render’s release/start scripts were additionally exercised against PostgreSQL 17, including both role logins, evidence pages/exports, direct HTTP health probes, HTTPS redirects/cookies, repeatable provisioning, and preserved passwords/planning drafts after restart. The native Render service itself and live NVIDIA generation still require the first-deployment checks above.
