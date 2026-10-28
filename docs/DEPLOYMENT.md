# Deployment and operations

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

Optional database variables: `APASA_DB_NAME`, `APASA_DB_USER`, `APASA_DB_PASSWORD`, `APASA_DB_HOST`, `APASA_DB_PORT`. Setting `APASA_DB_NAME` selects PostgreSQL; otherwise set `APASA_SQLITE_PATH` to a persistent writable file. `APASA_EVIDENCE_MODE=csv` remains the default and works with either authentication database backend. For imported evidence mode, follow the separate data-layer guide.

Set secrets through the hosting platform's secure environment settings, never source control. `.env.example` contains names and non-secret examples only. Django does not read `.env` automatically. Remove initial-account password variables after provisioning. Rotate the secret key and passwords if exposed; rotating the key invalidates sessions.

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

Run migrations once per release, not independently in each worker. `provision_accounts` is repeatable and preserves existing passwords. Use `python manage.py changepassword USERNAME` to rotate an existing account. Provisioning is transactional; production rejects known demo passwords. There is no public signup or email provider to configure.

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

Supply production settings securely through your platform. Run release commands in a one-off container with the same database and environment before starting the web service. Mount persistent storage at `/app/runtime` when using SQLite; ensure the container user can write to it. The image does not start a database or create users automatically. The image was built and smoke-tested as its non-root user with production settings and temporary credentials; consult CHANGELOG for exact validation and remaining hosting requirements. In a managed proxy environment, build with `--secret id=proxy_ca,src=/etc/ssl/certs/ca-certificates.crt` to mount its trusted CA for pip without embedding it in the image.

## Readiness and monitoring

`GET /health/` returns `200 {"status":"ok"}` after a database `SELECT 1`, or a generic 503 without leaking details. It is a database liveness check, not a comprehensive evidence test. Over HTTPS, verify the landing page, successful and failed sign-in, each role's redirect, a national record, a district selection, workbook filters, CSV export, an evidence note, logout, and anonymous redirects. Verify `/static/evidence/dashboard.css` is served. Send the correct Host and forwarded-protocol headers when checking behind the proxy.

Log output goes to stdout/stderr for platform collection. Do not log passwords or full environment values. Use platform access logs/alerts for repeated sign-in failures and server errors. Back up PostgreSQL or the SQLite file consistently, test restoration, and keep enough disk for sessions. Run `python manage.py clearsessions` regularly. Apply security updates and run tests before releasing dependency changes.

## Recovery

Keep the prior application image and database backup. Inspect migrations before downgrading; roll back code only when compatible with the current schema. Evidence bundles are immutable release artifacts: deploy the prior bundle and checksum together if needed and restart workers. Default account provisioning never resets a user's password.
