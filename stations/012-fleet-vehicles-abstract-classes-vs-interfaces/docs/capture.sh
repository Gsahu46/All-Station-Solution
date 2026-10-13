#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/fleet/vehicles
cap 01-diesel-truck "$U/1/service-plan"
cap 02-ev-van "$U/3/service-plan"
cap 03-petrol-bike "$U/4/service-plan"
cap 04-unknown "$U/99/service-plan"
date '+%-d %b %Y' > date.txt
