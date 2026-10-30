#!/usr/bin/env bash
set -euo pipefail

if [[ "${RENDER:-false}" == "true" ]]; then
  if [[ -z "${DATABASE_URL:-}" ]]; then
    echo 'Render setup required: set DATABASE_URL to your Render PostgreSQL Internal Database URL in the web service Environment settings.' >&2
    echo 'The Docker web service does not automatically apply render.yaml. See docs/RENDER.md: Existing Docker service.' >&2
    exit 1
  fi
  if [[ -z "${APASA_SECRET_KEY:-}" ]]; then
    echo 'Render setup required: generate APASA_SECRET_KEY in the web service Environment settings.' >&2
    exit 1
  fi
  export APASA_TRUST_PROXY="${APASA_TRUST_PROXY:-true}"
fi

# Single-instance VPS/Render containers finish release setup before workers start.
if [[ "${RENDER:-false}" == "true" || "${APASA_RUN_RELEASE:-false}" == "true" ]]; then
  if [[ -z "${DATABASE_URL:-}" || -z "${APASA_SECRET_KEY:-}" ]]; then
    echo 'Deployment setup required: set DATABASE_URL and APASA_SECRET_KEY securely before startup.' >&2
    exit 1
  fi
  bash deploy/release.sh
fi

exec bash deploy/start.sh
