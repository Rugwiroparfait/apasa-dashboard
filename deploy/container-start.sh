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
  # The manual Docker deployment is a single instance. Complete setup before workers.
  # Multi-instance deployments use the Blueprint and its one-off pre-deploy command.
  bash deploy/render-release.sh
fi

exec bash deploy/render-start.sh
