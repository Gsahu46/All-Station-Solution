#!/usr/bin/env bash
# Captures real request/response pairs into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first, on the real clock). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/products
J="Content-Type: application/json"
cap 01-one-second-before-diwali -G "$B/2/price" --data-urlencode "at=2026-11-07T23:59:59+05:30"
cap 02-midnight-in-india -G "$B/2/price" --data-urlencode "at=2026-11-08T00:00:00+05:30"
cap 03-the-same-instant-in-utc -G "$B/2/price" --data-urlencode "at=2026-11-07T18:30:00Z"
cap 04-a-sale-for-the-lamps -X POST "$B/1/prices" -H "$J" -d '{"pricePaise": 39900, "from": "2026-11-08T00:00", "to": "2026-11-11T00:00"}'
cap 05-changing-a-price-in-the-past -X POST "$B/3/prices" -H "$J" -d '{"pricePaise": 59900, "from": "2026-03-01T00:00"}'
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U kartwala -d kartwala -v ON_ERROR_STOP=1 -q "$@"; }
# What "midnight on 8 November" means to a server whose session runs in UTC, with and without a time zone.
psql -c "SET TimeZone = 'UTC'" -c "SELECT TIMESTAMP '2026-11-08 00:00' AS without_zone, TIMESTAMPTZ '2026-11-08 00:00+05:30' AS with_zone_shown_in_utc" > midnight.txt
date '+%-d %b %Y' > date.txt
