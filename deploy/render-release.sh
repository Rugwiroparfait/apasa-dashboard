#!/usr/bin/env bash
set -euo pipefail
python manage.py migrate --noinput
python manage.py provision_accounts
python manage.py check --deploy --fail-level WARNING
python manage.py validate_deployment_data
