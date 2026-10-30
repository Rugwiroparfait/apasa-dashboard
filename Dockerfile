# syntax=docker/dockerfile:1
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APASA_DEBUG=false
WORKDIR /app
COPY requirements.lock ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir -r requirements.lock; else pip install --no-cache-dir -r requirements.lock; fi
COPY apasa ./apasa
COPY accounts ./accounts
COPY planning ./planning
COPY evidence ./evidence
COPY manage.py ./
COPY deploy/container-start.sh deploy/start.sh deploy/release.sh deploy/render-start.sh deploy/render-release.sh ./deploy/
COPY docs ./docs
COPY outputs/day7 ./outputs/day7
COPY outputs/public_evidence ./outputs/public_evidence
COPY outputs/workbook_observations ./outputs/workbook_observations
RUN APASA_DEBUG=false APASA_SECRET_KEY=build-time-static-collection-only-not-a-runtime-secret-key python manage.py collectstatic --noinput && chmod -R a+rX /app && useradd --create-home app && mkdir -p /app/runtime && chown app:app /app/runtime
USER app
ENV APASA_SQLITE_PATH=/app/runtime/db.sqlite3
EXPOSE 8000
CMD ["bash", "deploy/container-start.sh"]
