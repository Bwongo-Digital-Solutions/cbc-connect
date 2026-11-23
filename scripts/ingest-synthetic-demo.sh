#!/usr/bin/env sh
set -eu
API_URL="${CBC_API_URL:-http://localhost:8000}"
: "${CBC_ANALYZER_API_KEY:?Set CBC_ANALYZER_API_KEY to the same value configured in the API environment}"
curl --fail-with-body --silent --show-error \
  -X POST "${API_URL}/api/v1/analyzer/ingest" \
  -H "Content-Type: application/json" \
  -H "X-Analyzer-Key: ${CBC_ANALYZER_API_KEY}" \
  -H "X-Device-Id: demo-humacount-30ts" \
  --data-binary @backend/demo/synthetic_cbc_export.json
printf '\n'
