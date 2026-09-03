#!/usr/bin/env bash
# Verify staging deployment: health probes + pilot smoke test.
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"

echo "=== Health checks ==="
curl -sf "$BASE_URL/api/v1/health/live" | python3 -m json.tool
curl -sf "$BASE_URL/api/v1/health/ready" | python3 -m json.tool

echo ""
echo "=== Pilot smoke test ==="
python3 "$(dirname "$0")/pilot_smoke_test.py" --base-url "$BASE_URL"

echo ""
echo "Staging verification PASSED"
