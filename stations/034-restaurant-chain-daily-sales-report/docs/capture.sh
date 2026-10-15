#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/reports/daily-sales
# The demo data covers the 7 days before today, in India's calendar.
YESTERDAY=$(TZ=Asia/Kolkata date -d yesterday +%F)
TODAY=$(TZ=Asia/Kolkata date +%F)
BEFORE_DATA=$(TZ=Asia/Kolkata date -d '8 days ago' +%F)
cap 01-yesterdays-report "$U?date=$YESTERDAY"
cap 02-a-day-with-no-sales "$U?date=$BEFORE_DATA"
cap 03-today-is-not-over "$U?date=$TODAY"
cap 04-a-date-in-another-format "$U?date=14-10-2026"
cap 05-no-date "$U"
date '+%-d %b %Y' > date.txt
