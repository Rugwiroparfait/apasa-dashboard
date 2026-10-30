# Deployment and operations

For the supported Render Blueprint, follow [Render deployment](RENDER.md).

## Production requirements

Use Python 3.12, PostgreSQL for multiple web instances, and an HTTPS reverse proxy. A single instance can use SQLite on a persistent writable volume. Never ship the development database or demonstration credentials. Back up the application database: it contains authentication sessions and accounts even when evidence uses CSV.

Required environment configuration:

| Variable | Purpose |
| --- | --- |
| `APASA_DEBUG=false` | Production mode; secure cookies, HTTPS redirect, HSTS and manifest static assets |
| `APASA_SECRET_KEY` | Unique securely generated secret; startup refuses the development default |
| `APASA_ALLOWED_HOSTS` | Comma-separated application hostnames |
| `APASA_CSRF_TRUSTED_ORIGINS` | Comma-separated HTTPS origins |
| `APASA_TRUST_PROXY=true` | Trust `X-Forwarded-Proto` only behind a proxy that replaces incoming forwarding headers |
| `APASA_POLICYMAKER_PASSWORD` | Initial production password for the `policymaker` account |
| `APASA_DISTRICT_PASSWORD` | Initial production password for the `district_officer` account |

`DATABASE_URL` takes precedence and supports PostgreSQL URLs (including URL-encoded credentials and an optional `sslmode`). On Render it is required. Optional separate database variables: `APASA_DB_NAME`, `APASA_DB_USER`, `APASA_DB_PASSWORD`, `APASA_DB_HOST`, `APASA_DB_PORT`. Setting `APASA_DB_NAME` selects PostgreSQL; otherwise set `APASA_SQLITE_PATH` to a persistent writable file. `APASA_EVIDENCE_MODE=csv` remains the default and works with either authentication database backend. For imported evidence mode, follow the separate data-layer guide.

Set secrets through the hosting platform's secure environment settings, never source control. `.env.example` contains names and non-secret examples only. The ignored local `.env` is loaded without replacing injected process variables; production should use platform-injected secrets. The image excludes `.env` files. Remove initial-account password variables after provisioning. Rotate the secret key and passwords if exposed; rotating the key invalidates sessions.

## Release commands

From the repository root, with production environment variables available:

```bash
python -m pip install -r requirements.lock
python manage.py migrate --noinput
python manage.py provision_accounts
python manage.py collectstatic --noinput
python manage.py check --deploy --fail-level WARNING
python manage.py check
python -m gunicorn apasa.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 60 --access-logfile - --error-logfile -
```

Run migrations once per release, not independently in each worker. This release adds the planning app and four schema migrations; back up the database before applying them. It stores source versions, policy targets, approvals, immutable comparison/scenario outputs, briefs and follow-up history in addition to accounts/sessions. `provision_accounts` is repeatable and preserves existing passwords. Use `python manage.py changepassword USERNAME` to rotate an existing account. Provisioning is transactional; production rejects known demo passwords. There is no public signup or email provider to configure.

Before exposure, configure the trusted proxy to terminate TLS, replace forwarded headers, limit request sizes, and rate-limit `/accounts/login/`. Django login does not provide brute-force throttling by itself. An Nginx example is in `deploy/nginx.conf`; replace the hostname and supply your platform's TLS certificate configuration. The application port should only be reachable through that proxy. Set the correct real-client-IP handling for your hosting platform before using IP rate limits.

## Container

`Dockerfile` installs only the Django runtime and runs Gunicorn as an unprivileged user. It includes approved CSVs and the compact workbook bundle; it excludes raw workbooks, the large review, local credentials and analysis runtimes. Build with the normal Docker TLS/proxy trust for your platform:

```bash
docker build -t apasa-dashboard .
```

Verify a disposable built image without real credentials or a production database:

```bash
docker run --rm -i apasa-dashboard python - < deploy/validate_container.py
```

This script creates a temporary SQLite test database and generated account credentials inside the disposable container, starts Gunicorn, and checks production sign-in, both journeys and static assets. Do not attach production storage or database variables to this validation command.

Supply production settings securely through your platform. Run release commands in a one-off container with the same database and environment before starting the web service. Mount persistent storage at `/app/runtime` when using SQLite; ensure the container user can write to it. Outside Render, the image does not start a database or create users automatically. On Render, its default startup checks database/secret configuration and runs release commands before Gunicorn for the supported single-instance manual Docker deployment; see the existing Docker service section in RENDER.md. The image was built and smoke-tested as its non-root user with production settings and temporary credentials; consult CHANGELOG for exact validation and remaining hosting requirements. In a managed proxy environment, build with `--secret id=proxy_ca,src=/etc/ssl/certs/ca-certificates.crt` to mount its trusted CA for pip without embedding it in the image.

## Readiness and monitoring

`GET /health/` returns `200 {"status":"ok"}` after a database `SELECT 1`, or a generic 503 without leaking details. It is a database liveness check, not a comprehensive evidence test. Over HTTPS, verify the landing page, successful and failed sign-in, each role's redirect, a national record, a district selection, workbook filters, CSV export, an evidence note, logout, and anonymous redirects. Verify `/static/evidence/dashboard.css` is served. Send the correct Host and forwarded-protocol headers when checking behind the proxy.

Log output goes to stdout/stderr for platform collection. Do not log passwords or full environment values. Use platform access logs/alerts for repeated sign-in failures and server errors. Back up PostgreSQL or the SQLite file consistently, test restoration, and keep enough disk for sessions. Run `python manage.py clearsessions` regularly. Apply security updates and run tests before releasing dependency changes.

## Recovery

Keep the prior application image and database backup. Inspect migrations before downgrading; roll back code only when compatible with the current schema. Evidence bundles are immutable release artifacts: deploy the prior bundle and checksum together if needed and restart workers. Default account provisioning never resets a user's password.


## Planning workflow operations

Run `python manage.py seed_planning_demo` only with development settings if mocked walkthroughs are wanted. Production deliberately rejects this command and demo-account provisioning; no official target or model is automatically approved during installation. Configure trusted role accounts for at least two different people so authors can obtain independent review. Both provisioned planning roles can review each other's submissions.

Use persistent SQLite for one instance or PostgreSQL for shared production instances. The database is now the system of record for uploaded aggregate observations, target versions, decisions, published calculation snapshots, scenario assumptions and action tracking. Backups and restoration tests must include all planning tables. Raw rejected CSV uploads are not retained; their hashes and bounded validation errors are stored.

Uploads are limited to 2 MB/5,000 rows at the application layer; set the reverse proxy's request-body limit to 3 MB (or greater) to allow multipart overhead while retaining the application limit. This release's Nginx fragment uses 3 MB. Keep CSRF, HTTPS, cookie and forwarding-header protections in place.

AI drafting is optional. Set `NVIDIA_API_KEY` (or the compatibility spelling `NVDIA_API_KEY`) securely and set `NVIDIA_MODEL=openai/gpt-oss-20b`; permit outbound HTTPS to `integrate.api.nvidia.com` through the configured proxy. No API key is stored in source code or database records. With no key or a provider failure, factual template drafting remains available and is labelled as such. Live provider authorization is not validated without operator-supplied credentials. AI requests use a 30-second timeout; the supplied Gunicorn timeout is 60 seconds. Do not enable raw request-body logging for login, uploads or AI credentials.

Smoke-test `/planning/`, source/target registration, quarantine errors, both users' review boundary, comparison publication, model backtesting, saved scenario review, brief approval, and follow-up updates. No email service, external source polling or automatic publication daemon is required. Due/overdue follow-ups are evaluated when the planning page is opened.


AI request accounting requires the planning migrations as well as the normal authentication schema. Configure persistent shared storage for quotas; multiple production replicas should share PostgreSQL. The default allowed-model list contains only `openai/gpt-oss-20b`. No automatic fallback or provider billing change is implemented. Local rolling caps are 8 requests/minute, 45 requests/24 hours and a conservative 80,000-token/minute reservation budget; the provider's own limits and available credits remain authoritative. Requests use NVIDIA’s Chat Completions API with at most 1,200 output tokens. These are application safeguards, not a promise of NVIDIA’s free quota. Changing model access/rate settings requires explicit operator review.

Do not pass real AI credentials into `deploy/validate_container.py`: its disposable workflow checks local fallback and must make no provider generation requests. Run `manage.py check_ai --check-access` and optionally `--generate` separately on the configured deployment or local computer to verify live access. Keys are never printed by these commands.
