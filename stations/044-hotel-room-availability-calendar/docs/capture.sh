#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/rooms
J="Content-Type: application/json"
cap 01-the-calendar "$B/101/availability?from=2026-06-09&to=2026-06-17"
cap 02-the-old-bug-11-to-13-june -X POST "$B/101/blocks" -H "$J" -d '{"checkIn":"2026-06-11","checkOut":"2026-06-13","guestName":"Kabir Shah"}'
cap 03-exactly-the-gap -X POST "$B/101/blocks" -H "$J" -d '{"checkIn":"2026-06-12","checkOut":"2026-06-15","guestName":"Meena Rao"}'
cap 04-the-calendar-after "$B/101/availability?from=2026-06-09&to=2026-06-17"
cap 05-zero-nights -X POST "$B/101/blocks" -H "$J" -d '{"checkIn":"2026-07-02","checkOut":"2026-07-02","guestName":"Day Visitor"}'
cap 06-no-such-room "$B/999/availability?from=2026-06-09&to=2026-06-17"
# Twenty desks sell room 102 for the same three nights at once.
{ echo "20 requests at once for room 102, 1 to 4 August: HTTP status counts"
  seq 1 20 | xargs -P 20 -I{} curl -s -o /dev/null -w "%{http_code}\n" -X POST "$B/102/blocks" -H "$J" -d '{"checkIn":"2026-08-01","checkOut":"2026-08-04","guestName":"Desk {}"}' | sort | uniq -c
} > rush.txt
date '+%-d %b %Y' > date.txt
