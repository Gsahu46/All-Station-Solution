#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/partner/delivery-updates
J="Content-Type: application/json"
cap 01-partner-update-with-new-fields -X POST "$U" -H "$J" -d '{"awb_number":"DKR100000001IN","status_code":"OFD","event_time":"2026-10-14 09:15:00","location":{"city_name":"Pune","pin_code":"411001","hub_id":"PNQ-07"},"promised_by":"2026-10-14T18:00:00+05:30","rider_phone":"98XXXXXX21","temperature_c":31.5}'
cap 02-late-night-in-india -X POST "$U" -H "$J" -d '{"awb_number":"dkr100000002in","status_code":"DLV","event_time":"2026-10-15 02:00:00"}'
cap 03-new-status-code -X POST "$U" -H "$J" -d '{"awb_number":"DKR100000001IN","status_code":"HLD","event_time":"2026-10-14 10:00:00"}'
cap 04-unknown-awb -X POST "$U" -H "$J" -d '{"awb_number":"DKR999999999IN","status_code":"OFD","event_time":"2026-10-14 09:15:00"}'
cap 05-time-without-the-agreed-format -X POST "$U" -H "$J" -d '{"awb_number":"DKR100000001IN","status_code":"OFD","event_time":"14/10/2026 09:15"}'
cap 06-our-names-not-theirs -X POST "$U" -H "$J" -d '{"awbNumber":"DKR100000001IN","statusCode":"OFD","eventTime":"2026-10-14 09:15:00"}'
date '+%-d %b %Y' > date.txt
