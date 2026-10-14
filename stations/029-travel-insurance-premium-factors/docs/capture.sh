#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/premium-quotes
J="Content-Type: application/json"
cap 01-senior-to-europe-with-adventure -X POST "$U" -H "$J" -d '{"age":67,"destination":"EUROPE","days":10,"adventureSports":true}'
cap 02-a-short-trip-pays-the-minimum -X POST "$U" -H "$J" -d '{"age":25,"destination":"ASIA","days":3}'
cap 03-rounded-up-not-to-nearest -X POST "$U" -H "$J" -d '{"age":45,"destination":"EUROPE","days":5}'
cap 04-over-80 -X POST "$U" -H "$J" -d '{"age":81,"destination":"ASIA","days":3}'
cap 05-a-destination-we-do-not-cover -X POST "$U" -H "$J" -d '{"age":30,"destination":"MARS","days":3}'
# The app's own startup line naming the factors in the order it will apply them (APP_LOG is set by tools/build_station.sh).
grep -o "Premium factors, in order: .*" "$APP_LOG" > startup-log.txt
date '+%-d %b %Y' > date.txt
