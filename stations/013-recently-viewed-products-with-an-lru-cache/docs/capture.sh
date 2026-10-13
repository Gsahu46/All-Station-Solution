#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/users/7/recently-viewed
J="Content-Type: application/json"
for p in 101 102 103; do curl -s -o /dev/null -X POST "$U" -H "$J" -d "{\"productId\":$p}"; done
cap 01-view-again -X POST "$U" -H "$J" -d '{"productId":101}'
for p in 104 105 106 107 108 109 110 111; do curl -s -o /dev/null -X POST "$U" -H "$J" -d "{\"productId\":$p}"; done
cap 02-after-eleven-products "$U"
cap 03-new-user http://localhost:8080/users/8/recently-viewed
cap 04-bad-user -X POST http://localhost:8080/users/0/recently-viewed -H "$J" -d '{"productId":101}'
date '+%-d %b %Y' > date.txt
