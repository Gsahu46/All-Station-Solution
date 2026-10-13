#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
cap 01-open http://localhost:8080/stores/BLR-KOR-01/status
cap 02-closed http://localhost:8080/stores/BLR-IND-01/status
cap 03-unknown http://localhost:8080/stores/BLR-XYZ-99/status
cap 04-malformed http://localhost:8080/stores/koramangala/status
date '+%-d %b %Y' > date.txt
