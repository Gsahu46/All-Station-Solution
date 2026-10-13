#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/parking
J="Content-Type: application/json"
cap 01-bike -X POST "$U/entries" -H "$J" -d '{"vehicleNumber":"KA05XY4321","vehicleType":"BIKE"}'
cap 02-car -X POST "$U/entries" -H "$J" -d '{"vehicleNumber":"mh 12 ab-1234","vehicleType":"CAR"}'
cap 03-same-car-again -X POST "$U/entries" -H "$J" -d '{"vehicleNumber":"MH12AB1234","vehicleType":"CAR"}'
cap 04-bad-plate -X POST "$U/entries" -H "$J" -d '{"vehicleNumber":"12345","vehicleType":"CAR"}'
T=$(grep -o '"ticketId":"[^"]*"' 02-car.txt | head -1 | cut -d'"' -f4)
cap 05-exit -X POST "$U/exits/$T"
cap 06-exit-again -X POST "$U/exits/$T"
cap 07-unknown-ticket -X POST "$U/exits/00000000-0000-0000-0000-000000000000"
date '+%-d %b %Y' > date.txt
