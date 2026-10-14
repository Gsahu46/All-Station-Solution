#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
cap 01-with-the-apps-request-id -H "X-Request-Id: app-7f3a9c21" "$B/shipments/DKR100000001IN"
cap 02-without-an-id "$B/shipments/DKR100000002IN"
cap 03-unknown-shipment -H "X-Request-Id: support-case-41" "$B/shipments/DKR999999999IN"
cap 04-an-unsafe-id-is-replaced -H "X-Request-Id: x ERROR forged" "$B/shipments/DKR100000001IN"
cap 05-a-path-no-controller-handles -H "X-Request-Id: typo-path-0001" "$B/shipment/DKR100000001IN"
cap 06-the-metric-the-alert-reads "$B/actuator/metrics/tracking.lookups?tag=outcome:found"
# The app's own log lines for the ids sent above (APP_LOG is set by tools/build_station.sh), without timestamps and pids.
grep -E "rid:(app-7f3a9c21|support-case-41)\]" "$APP_LOG" | sed -E 's/^[0-9T:.Z+-]+ +//; s/ [0-9]+ --- / --- /' > app-log.txt
date '+%-d %b %Y' > date.txt
