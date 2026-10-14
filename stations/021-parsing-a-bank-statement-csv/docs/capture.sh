#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/statements/parse
C="Content-Type: text/csv"
cap 01-clean -X POST "$U" -H "$C" --data-binary @../samples/clean.csv
cap 02-three-bad-lines -X POST "$U" -H "$C" --data-binary @../samples/three-bad-lines.csv
cap 03-no-header -X POST "$U" -H "$C" --data-binary @../samples/no-header.csv
cap 04-json-instead-of-csv -X POST "$U" -H "Content-Type: application/json" -d '{"rows":[]}'
date '+%-d %b %Y' > date.txt
