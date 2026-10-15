#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
cap 01-the-patients-own-language "$B/appointments/501/reminder"
cap 02-lang-asks-for-english "$B/appointments/501/reminder?lang=en"
cap 03-the-phone-asks-for-hindi "$B/appointments/502/reminder" -H "Accept-Language: hi-IN,hi;q=0.9,en;q=0.8"
cap 04-a-language-we-do-not-have "$B/appointments/501/reminder?lang=ta"
cap 05-no-such-appointment "$B/appointments/999/reminder"
cap 06-a-lang-that-is-not-a-language "$B/appointments/501/reminder?lang=hindi-language"
date '+%-d %b %Y' > date.txt
