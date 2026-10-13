#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
M=http://localhost:8080/restaurants
cap 01-veg-under-200 "$M/101/menu?veg=true&maxPrice=200&sort=price_asc&limit=5"
cap 02-defaults "$M/101/menu?limit=3"
cap 03-nothing-matches "$M/102/menu?veg=true"
cap 04-invalid-filters "$M/101/menu?limit=0&sort=cheapest"
cap 05-unknown-restaurant "$M/999/menu"
date '+%-d %b %Y' > date.txt
