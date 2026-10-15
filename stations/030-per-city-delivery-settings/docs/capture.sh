#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
cap 01-pune-terms "$B/cities/pune/delivery-terms"
cap 02-an-address-in-range -X POST "$B/delivery-checks" -H "$J" -d '{"city":"pune","lat":18.5362,"lon":73.8940,"orderPaise":25000}'
cap 03-too-far-and-too-small -X POST "$B/delivery-checks" -H "$J" -d '{"city":"pune","lat":18.5913,"lon":73.7389,"orderPaise":9900}'
cap 04-the-client-sends-its-own-distance -X POST "$B/delivery-checks" -H "$J" -d '{"city":"pune","lat":18.5913,"lon":73.7389,"orderPaise":25000,"distanceKm":0}'
cap 05-a-city-we-do-not-serve "$B/cities/jaipur/delivery-terms"
date '+%-d %b %Y' > date.txt
