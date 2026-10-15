#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
ASK='{"employeeId":1,"startDate":"2026-11-06","endDate":"2026-11-10","reason":"Sister'"'"'s wedding in Jaipur"}'
cap 01-asha-asks-for-three-days -X POST "$B/leave-requests" -H "$J" -d "$ASK"
cap 02-the-manager-approves -X POST "$B/leave-requests/1/approval"
cap 03-ashas-balance "$B/employees/1/leave-balance"
cap 04-approved-twice -X POST "$B/leave-requests/1/approval"
cap 05-rohan-asks-for-three-days -X POST "$B/leave-requests" -H "$J" -d "${ASK/\"employeeId\":1/\"employeeId\":2}"
cap 06-not-enough-leave -X POST "$B/leave-requests/2/approval"
WEEKEND=${ASK/2026-11-06/2026-11-07}
cap 07-a-weekend-only -X POST "$B/leave-requests" -H "$J" -d "${WEEKEND/2026-11-10/2026-11-08}"
cap 08-no-such-request -X POST "$B/leave-requests/99/approval"
# The rows themselves, read with psql after the requests above: what the database kept.
docker compose -f ../../compose.yaml exec -T postgres psql -U teamdesk -d teamdesk \
  -c "SELECT id, name, balance_days, version FROM employees ORDER BY id" \
  -c "SELECT id, employee_id, start_date, end_date, days, status, version FROM leave_requests ORDER BY id" > rows.txt
date '+%-d %b %Y' > date.txt
