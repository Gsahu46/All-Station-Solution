#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/orders
J="Content-Type: application/json"
cap 01-a-new-order "$U/1001"
cap 02-delivered-before-accepted -X POST "$U/1001/status-changes" -H "$J" -d '{"to":"DELIVERED"}'
cap 03-accepted -X POST "$U/1001/status-changes" -H "$J" -d '{"to":"ACCEPTED"}'
cap 04-the-tablet-taps-twice -X POST "$U/1001/status-changes" -H "$J" -d '{"to":"ACCEPTED"}'
cap 05-picking-up-a-cancelled-order -X POST "$U/1002/status-changes" -H "$J" -d '{"to":"PICKED_UP"}'
cap 06-a-status-that-does-not-exist -X POST "$U/1001/status-changes" -H "$J" -d '{"to":"TELEPORTED"}'
cap 07-an-unknown-order "$U/9999"
date '+%-d %b %Y' > date.txt
