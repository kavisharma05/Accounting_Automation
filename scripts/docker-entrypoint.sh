#!/bin/bash
set -euo pipefail

echo "Waiting for PostgreSQL..."
until python -c "
import os, psycopg2
psycopg2.connect(os.environ['DATABASE_URL'].replace('+psycopg2', ''))
" 2>/dev/null; do
  sleep 2
done

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Running Alembic migrations..."
  alembic upgrade head
else
  echo "Skipping migrations (RUN_MIGRATIONS=false)"
fi

exec "$@"
