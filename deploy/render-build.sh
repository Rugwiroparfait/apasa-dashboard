#!/usr/bin/env bash
set -euo pipefail
python -m pip install --no-cache-dir -r requirements.lock
python manage.py validate_deployment_data
python manage.py collectstatic --noinput
