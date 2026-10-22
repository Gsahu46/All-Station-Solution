#!/usr/bin/env bash
# Captures real request/response pairs and the seat rows into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U seatsure -d seatsure -v ON_ERROR_STOP=1 -q "$@"; }
cap 01-meera-holds-f12-and-f13 -X POST "$B/shows/1/holds" -H "$J" -d '{"customer": "meera", "seats": ["F12", "F13"]}'
HOLD=$(sed -n 's/.*"id":"\([0-9a-f-]*\)".*/\1/p' 01-meera-holds-f12-and-f13.txt)
cap 02-arjun-asks-for-f12 -X POST "$B/shows/1/holds" -H "$J" -d '{"customer": "arjun", "seats": ["F11", "F12"]}'
cap 03-arjun-asks-for-any-two -X POST "$B/shows/1/holds" -H "$J" -d '{"customer": "arjun", "count": 2}'
cap 04-meera-confirms -X POST "$B/holds/$HOLD/confirm"
cap 05-meera-confirms-again -X POST "$B/holds/$HOLD/confirm"
# Someone else's transaction keeps G12 locked for 4 seconds (as the old code did while waiting for the payment provider).
(psql -c "BEGIN; SELECT seat_no FROM seats WHERE show_id = 1 AND seat_no = 'G12' FOR UPDATE; SELECT pg_sleep(4); COMMIT;" > /dev/null &)
sleep 1
start=$(date +%s%N)
cap 06-a-seat-locked-by-someone-else -X POST "$B/shows/1/holds" -H "$J" -d '{"customer": "kabir", "seats": ["G12"]}'
echo "answered after $(( ($(date +%s%N) - start) / 1000000 / 100 * 100 )) ms (to the nearest 100 ms)" > lock-wait.txt
cap 07-both-seats-and-count -X POST "$B/shows/1/holds" -H "$J" -d '{"customer": "kabir", "seats": ["G12"], "count": 1}'
sleep 4
psql -c "SELECT seat_no, price_paise, hold_id IS NOT NULL AS held, booked_by FROM seats WHERE show_id = 1 AND (hold_id IS NOT NULL OR booked_by IS NOT NULL) ORDER BY seat_no" > seats.txt
psql -c "SELECT customer, seat_nos, total_paise, status, payment_ref FROM holds ORDER BY customer" > holds.txt
date '+%-d %b %Y' > date.txt
