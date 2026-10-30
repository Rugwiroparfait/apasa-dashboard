# VPS deployment: apasa.inzuyange.com

This is the deployment path for the supplied VPS running `nginx-proxy-manager-npm-app-1` alongside other applications. It does not use Render. Docker Compose v2 and Python 3 must be available. Nginx Proxy Manager (NPM) keeps ports 80/443 and manages the certificate; APASA publishes **no host ports**, so it does not conflict with the existing 3000/4000/5678/8000/8001/8080/18080 mappings.

The stack is named `apasa`: a single non-root web container, its own PostgreSQL 17 container, and persistent `apasa_postgres_data` volume. Only the web container joins `apasa-proxy`, shared with NPM. PostgreSQL is on a separate internal network and is not reachable from NPM or the public internet. The web alias is `apasa-web`, listening on container port 8000. The existing evidence files ship unchanged; raw workbooks, local databases and mock data are not seeded. The two roles, reviews, uploads and saved reports persist in PostgreSQL.

## First deployment

Run on the VPS with permission to use Docker. Clone the private repository using your existing GitHub credentials/deploy key; never put a token into these commands or chat.

```bash
mkdir -p /opt
cd /opt
git clone https://github.com/Rugwiroparfait/apasa-dashboard.git
cd apasa-dashboard
bash deploy/vps.sh prepare
nano .env.vps
bash deploy/vps.sh up
bash deploy/vps.sh status
```

If the checkout already exists, enter it and run `git pull --ff-only` instead of cloning again. Use the latest `main` commit. `prepare` checks the existing NPM container, creates an isolated proxy network if needed, and attaches NPM to it without restarting it or changing its other networks/hosts. If its name changes, use `APASA_NPM_CONTAINER=NEW_NAME bash deploy/vps.sh prepare`. Re-run `prepare` after NPM is recreated by its own upgrades to restore this network attachment.

`prepare` generates `.env.vps` **once**, with mode 600, unique database/app secrets and initial role passwords. Existing credentials are never overwritten. In the editor, add your NVIDIA key to `NVIDIA_API_KEY` (the local `NVDIA_API_KEY` spelling also works). Blank keys keep labelled local factual drafting available. Retrieve the generated `APASA_POLICYMAKER_PASSWORD` and `APASA_DISTRICT_PASSWORD` privately from this file. The usernames are `policymaker` and `district_officer`. Do not reuse demo passwords, publish this file, or regenerate it on updates. Docker Compose explicitly maps these secrets; it does not import unrelated Render/local environment settings.

`up` validates Compose without printing expanded secrets, builds the image, waits for PostgreSQL, applies migrations, provisions missing accounts, checks production configuration/data, and starts Gunicorn. Health checks must pass before the command succeeds. One web worker is the default for this shared VPS; adjust `WEB_CONCURRENCY` only if resources justify it. The initial build requires outbound access to Docker Hub and PyPI; NVIDIA requests need HTTPS to `integrate.api.nvidia.com`. No GPU is needed.

Do not copy the Render environment variables here. In particular, do not set `RENDER=true` or reuse an unrelated database URL. The VPS Compose file creates the correct private `DATABASE_URL` from `.env.vps` automatically.

## DNS and Nginx Proxy Manager

1. Create an **A record** for `apasa.inzuyange.com` pointing to the VPS public IP. The supplied screenshot uses `72.61.180.118`; use it if that is still this VPS's assigned address. Any AAAA record must also reach this server. Wait until public DNS resolves correctly before requesting the certificate.
2. In your existing NPM UI choose **Add Proxy Host**:

   | Field | Value |
   | --- | --- |
   | Domain Names | `apasa.inzuyange.com` |
   | Scheme | `http` |
   | Forward Hostname / IP | `apasa-web` |
   | Forward Port | `8000` |
   | Access List | Public (APASA still requires sign-in) |
   | Cache Assets | Off |

3. In **Advanced**, add `client_max_body_size 3m;` to allow bounded aggregate uploads. Keep NPM's normal forwarding of the original Host and `X-Forwarded-Proto`; do not replace the Host with `apasa-web`. The application trusts the proxy because it has no published public port.
4. In **SSL**, request a new Let's Encrypt certificate for this hostname, accept the terms, and enable **Force SSL**. Save the host. Ensure the existing firewall still permits NPM's 80/443; APASA requires no additional inbound port.
5. Open `https://apasa.inzuyange.com` and sign in using each role's generated credentials. Use two different people for independent review.

Do not forward this new host to `72.61.180.118:8000`: that is already another application's port. Use the shared-network name `apasa-web:8000`. Do not stop NPM or edit its existing proxy hosts.

## Verify and troubleshoot

```bash
bash deploy/vps.sh status
bash deploy/vps.sh logs
```

The expected services are healthy `web` and `db`. Database and Gunicorn logs must not contain credentials. Define this convenience function for additional commands in the current shell:

```bash
apasa() { docker compose --project-name apasa --env-file .env.vps -f compose.vps.yaml "$@"; }
apasa exec web python manage.py validate_deployment_data
apasa exec web python manage.py check --deploy --fail-level WARNING
apasa exec web python manage.py check_ai
# Optional explicit provider requests, using the key on this VPS:
apasa exec web python manage.py check_ai --check-access
apasa exec web python manage.py check_ai --generate
```

Verify the landing page, both role redirects, charts, district/crop filters, evidence exports, comparison review and sign-out. No missing target becomes an invented achievement; original evidence and explicitly mocked examples remain distinct.

A **502** from NPM usually means an unhealthy web container, incorrect forwarding name/port, or a missing shared-network attachment. Check `status`/`logs`, then re-run `prepare`. A **400** suggests the wrong Host/domain: `APASA_DOMAIN` must match the hostname. A login CSRF failure suggests an incorrect HTTPS origin/header: use the exact HTTPS domain and keep NPM's forwarded protocol. Certificate issuance requires correct public DNS and reachable ports 80/443. The `/health/` endpoint intentionally accepts HTTP within Docker for readiness; normal pages redirect to HTTPS.

## Updates, backups and recovery

Before every application update:

```bash
cd /opt/apasa-dashboard
bash deploy/vps.sh backup
git pull --ff-only
bash deploy/vps.sh prepare
bash deploy/vps.sh up
bash deploy/vps.sh status
```

`backup` uses `pg_dump` in custom format and writes a mode-600 archive under ignored `backups/`; failed dumps are removed. Keep copies off the VPS, along with a separate secure copy of `.env.vps`, and test restoration. Set up a backup schedule appropriate to your usage. Example daily root cron entry:

```cron
15 2 * * * cd /opt/apasa-dashboard && bash deploy/vps.sh backup >> /var/log/apasa-backup.log 2>&1
```

Cron uses the VPS timezone. Review backup retention and available disk space; the script does not delete old backups. Never run `docker compose down -v`, delete `apasa_postgres_data`, or replace the database password in `.env.vps` expecting an existing database to reset. Those operations can remove data or break authentication. Password rotation needs coordinated PostgreSQL changes; account password changes use `apasa exec web python manage.py changepassword USERNAME` and are preserved on subsequent releases.

To restore into the existing database, first take a fresh backup and stop APASA's web service (`apasa stop web`). Then, deliberately selecting a trusted archive, run `apasa exec -T db pg_restore -U apasa -d apasa --clean --if-exists --no-owner < backups/CHOSEN.pgdump`. This replaces matching database contents; run it only as a planned restore. Restart APASA with `bash deploy/vps.sh up` and verify both roles. Do not stop the other VPS applications or delete Docker resources globally.

The manual VPS stack is intentionally one web instance: release commands run before its workers at container startup. Do not scale it to multiple replicas without moving migrations/provisioning into a separate release job. Configure sign-in rate limits in your existing edge/proxy setup; Django authentication does not itself throttle brute-force attempts.

## Deployment boundary

Repository checks and disposable local container tests do not change your VPS, DNS, NPM settings or certificate. The first live HTTPS/provider checks must run on the VPS after you execute these steps. No VPS SSH credentials or production data were supplied to this cloud workspace.


## Recorded validation

All 112 Django tests passed. The Compose stack was tested with disposable PostgreSQL and a trusted-certificate HTTPS nginx proxy: both role logins, evidence charts/exports, private database networking, no published ports, repeatable proxy preparation and automatic release startup passed. A backup restored successfully into another test database, and complete container recreation retained credentials and a planning draft. This validates the repository configuration; your actual DNS/NPM certificate and live NVIDIA access must still be checked after VPS deployment.
