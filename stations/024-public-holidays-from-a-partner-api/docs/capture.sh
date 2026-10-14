#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
cap 01-the-providers-raw-answer "$B/demo-provider/v1/holidays?year=2026&region=KA"
cap 02-our-answer "$B/holidays?year=2026&state=KA"
cap 03-no-list-for-the-state "$B/holidays?year=2026&state=tn"
cap 04-unknown-state "$B/holidays?year=2026&state=ZZ"
cap 05-provider-fails "$B/holidays?year=2099&state=KA"
cap 06-provider-too-slow "$B/holidays?year=2098&state=KA"
date '+%-d %b %Y' > date.txt
