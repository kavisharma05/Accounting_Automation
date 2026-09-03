#!/usr/bin/env bash
# Bootstrap staging stack (Postgres, Redis, API, worker) and seed pilot org.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env.staging ]]; then
  echo "Missing .env.staging — copy from .env.staging.example and set SECRET_KEY."
  echo "  cp .env.staging.example .env.staging"
  exit 1
fi

if grep -q 'replace-with-openssl-rand-hex-32' .env.staging 2>/dev/null; then
  echo "Set a real SECRET_KEY in .env.staging before deploying."
  exit 1
fi

echo "Starting staging stack..."
docker compose -f docker-compose.yml -f docker-compose.staging.yml up --build -d

echo "Waiting for API readiness..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/api/v1/health/ready >/dev/null 2>&1; then
    echo "API ready."
    break
  fi
  if [[ "$i" -eq 30 ]]; then
    echo "API not ready after 30 attempts — check: docker compose logs api"
    exit 1
  fi
  sleep 2
done

echo "Seeding pilot organization..."
docker compose -f docker-compose.yml -f docker-compose.staging.yml --profile tools run --rm seed

echo ""
echo "Staging is up."
echo "  API + dashboard: http://localhost:8000"
echo "  API docs:        http://localhost:8000/docs"
echo "  Login:           admin@pilot.local / pilot-admin-change-me"
echo ""
echo "Run verification: ./scripts/staging_verify.sh"
