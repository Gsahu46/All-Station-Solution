#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/suggestions
cap 01-sam "$U?prefix=sam"
cap 02-second-word "$U?prefix=GALAXY&limit=3"
cap 03-no-match "$U?prefix=msung"
cap 04-too-short "$U?prefix=s"
cap 05-bad-limit "$U?prefix=sam&limit=50"
date '+%-d %b %Y' > date.txt
