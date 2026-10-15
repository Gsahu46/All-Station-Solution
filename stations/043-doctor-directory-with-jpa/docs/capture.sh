#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
cap 01-cardiologists-in-pune "$B/doctors?speciality=cardiology&city=pune"
cap 02-every-cardiologist "$B/doctors?speciality=Cardiology"
cap 03-one-doctor "$B/doctors/1"
cap 04-no-such-doctor "$B/doctors/99"
cap 05-a-filter-with-a-digit "$B/doctors?speciality=Cardio1ogy"
date '+%-d %b %Y' > date.txt
