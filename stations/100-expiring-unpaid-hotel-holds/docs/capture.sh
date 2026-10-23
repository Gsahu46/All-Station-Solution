#!/usr/bin/env bash
# Captures real request/response pairs from the running app and its PostgreSQL into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J=(-H 'Content-Type: application/json')
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U ghoomo -d ghoomo -v ON_ERROR_STOP=1 -q "$@"; }
SUITE='{"roomTypeId":2,"date":"2026-12-31","guestEmail":"asha@example.com"}'
cap 01-asha-holds-the-suite-for-new-years-eve "${J[@]}" -H 'Idempotency-Key: asha-nye-0001' -d "$SUITE" "$B/holds"
cap 02-her-app-retries "${J[@]}" -H 'Idempotency-Key: asha-nye-0001' -d "$SUITE" "$B/holds"
cap 03-the-same-key-for-another-night "${J[@]}" -H 'Idempotency-Key: asha-nye-0001' -d '{"roomTypeId":2,"date":"2026-12-30","guestEmail":"asha@example.com"}' "$B/holds"
cap 04-ravi-wants-the-suite-too "${J[@]}" -H 'Idempotency-Key: ravi-nye-0001' -d '{"roomTypeId":2,"date":"2026-12-31","guestEmail":"ravi@example.com"}' "$B/holds"
cap 05-no-idempotency-key "${J[@]}" -d "$SUITE" "$B/holds"
cap 06-a-night-the-hotel-does-not-sell "${J[@]}" -H 'Idempotency-Key: asha-jan-0001' -d '{"roomTypeId":2,"date":"2027-01-15","guestEmail":"asha@example.com"}' "$B/holds"
cap 07-asha-has-not-paid-yet "$B/holds/1"
# Instead of waiting 15 minutes: move hold 1's times back 20 minutes in the database. The job (every 30 s) does the rest.
psql -c "UPDATE holds SET created_at = created_at - interval '20 minutes', expires_at = expires_at - interval '20 minutes' WHERE id = 1"
for _ in $(seq 1 45); do curl -s "$B/holds/1" | grep -q EXPIRED && break; sleep 1; done
cap 08-the-job-expired-it "$B/holds/1"
cap 09-ravi-tries-again "${J[@]}" -H 'Idempotency-Key: ravi-nye-0001' -d '{"roomTypeId":2,"date":"2026-12-31","guestEmail":"ravi@example.com"}' "$B/holds"
psql -c "SELECT id, room_type_id, stay_date, status, expired_at IS NOT NULL AS expired FROM holds ORDER BY id" > holds.txt
psql -c "SELECT room_type_id, stay_date, total, held FROM room_nights WHERE stay_date = '2026-12-31' ORDER BY room_type_id" > room-nights.txt
date '+%-d %b %Y' > date.txt
