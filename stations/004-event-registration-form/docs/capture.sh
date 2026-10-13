#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/events/pune-tech-summit-2026/registrations
J="Content-Type: application/json"
cap 01-register -X POST "$U" -H "$J" -d '{"name":"Asha Kulkarni","email":"asha.k@example.com","phone":"9876543210","tickets":2}'
cap 02-garbage -X POST "$U" -H "$J" -d '{"name":"   ","email":"asha","tickets":0}'
cap 03-fraction -X POST "$U" -H "$J" -d '{"name":"Ravi","email":"ravi@example.com","tickets":2.5}'
LOC=$(grep -i '^Location:' 01-register.txt | cut -d' ' -f2)
cap 04-read-back "http://localhost:8080$LOC"
cap 05-unknown-event -X POST http://localhost:8080/events/mumbai-marathon-2026/registrations -H "$J" -d '{"name":"Ravi","email":"ravi@example.com","tickets":1}'
date '+%-d %b %Y' > date.txt
