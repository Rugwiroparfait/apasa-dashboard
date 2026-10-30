#!/usr/bin/env bash
# Run only this project's stack; do not stop or reconfigure other VPS services.
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
compose=(docker compose --project-name apasa --env-file .env.vps -f compose.vps.yaml)

case "${1:-help}" in
  prepare)
    docker compose version >/dev/null
    [[ -f .env.vps ]] || python3 deploy/configure_vps.py
    chmod 600 .env.vps
    proxy="${APASA_NPM_CONTAINER:-nginx-proxy-manager-npm-app-1}"
    docker inspect "$proxy" >/dev/null
    docker network inspect apasa-proxy >/dev/null 2>&1 || docker network create apasa-proxy >/dev/null
    if [[ "$(docker inspect -f '{{if index .NetworkSettings.Networks "apasa-proxy"}}connected{{end}}' "$proxy")" != connected ]]; then
      docker network connect apasa-proxy "$proxy"
    fi
    echo 'APASA proxy network is ready; existing proxy hosts and services were not restarted.'
    ;;
  up)
    "${compose[@]}" config --quiet
    "${compose[@]}" up -d --build --wait --wait-timeout 180
    ;;
  status)
    "${compose[@]}" ps
    ;;
  logs)
    "${compose[@]}" logs --tail 100 web
    ;;
  backup)
    mkdir -p backups
    chmod 700 backups
    snapshot="backups/apasa-$(date -u +%Y%m%dT%H%M%SZ).pgdump"
    temporary="$(mktemp backups/.apasa-backup.XXXXXX)"
    if "${compose[@]}" exec -T db pg_dump -U apasa -d apasa -Fc > "$temporary"; then
      mv "$temporary" "$snapshot"
      echo "Database backup saved: $snapshot"
    else
      rm -f "$temporary"
      exit 1
    fi
    ;;
  *)
    echo 'Usage: bash deploy/vps.sh {prepare|up|status|logs|backup}'
    ;;
esac
