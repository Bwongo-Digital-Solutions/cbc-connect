#!/usr/bin/env sh
# Loads fictional records into the pending-review queue. Safe to rerun.
set -eu
API_URL="${CBC_API_URL:-http://localhost:8900}"
: "${CBC_ANALYZER_API_KEY:?Set CBC_ANALYZER_API_KEY to the same value configured in the API environment}"
DEVICE_ID="demo-humacount-30ts"
count=0
for fixture in backend/demo/synthetic_cbc_export*.json; do
  [ -f "$fixture" ] || continue
  code=$(curl --silent --show-error -o /tmp/cbc-connect-demo-response.json -w '%{http_code}' \
    -X POST "${API_URL}/api/v1/analyzer/ingest" \
    -H "Content-Type: application/json" \
    -H "X-Analyzer-Key: ${CBC_ANALYZER_API_KEY}" \
    -H "X-Device-Id: ${DEVICE_ID}" \
    --data-binary "@${fixture}")
  case "$code" in
    201) printf 'Loaded %s\n' "$fixture"; count=$((count + 1)) ;;
    200) printf 'Enriched missing biodata or already complete: %s\n' "$fixture" ;;
    409) printf 'Already loaded (duplicate): %s\n' "$fixture" ;;
    *) cat /tmp/cbc-connect-demo-response.json; printf 'Failed loading %s (HTTP %s)\n' "$fixture" "$code" >&2; exit 1 ;;
  esac
done
printf 'Demo seed complete. New records: %s. All demo records remain PENDING_REVIEW.\n' "$count"
rm -f /tmp/cbc-connect-demo-response.json
