#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/webinars
J="Content-Type: application/json"
w() { printf '{"title":"Planning your first sprint","startsAt":"%s","zone":"%s","durationMinutes":60%s}' "$1" "$2" "${3:-}"; }
cap 01-a-webinar-in-india -X POST "$B" -H "$J" -d "$(w 2026-11-05T10:00 Asia/Kolkata)"
cap 02-seen-from-london "$B/1?viewerZone=Europe/London"
cap 03-seen-from-los-angeles "$B/1?viewerZone=America/Los_Angeles"
cap 04-a-new-york-series-across-daylight-saving -X POST "$B" -H "$J" -d "$(w 2026-10-20T10:00 America/New_York ',"repeat":"MONTHLY","sessions":2')"
cap 05-the-series-seen-from-india "$B/2?viewerZone=Asia/Kolkata"
cap 06-monthly-from-january-31 -X POST "$B" -H "$J" -d "$(w 2027-01-31T10:00 Asia/Kolkata ',"repeat":"MONTHLY","sessions":4')"
cap 07-a-time-the-clocks-skip -X POST "$B" -H "$J" -d "$(w 2027-03-14T02:30 America/New_York)"
cap 08-a-time-that-happens-twice -X POST "$B" -H "$J" -d "$(w 2026-11-01T01:30 America/New_York)"
cap 09-ist-is-not-a-zone -X POST "$B" -H "$J" -d "$(w 2026-11-05T10:00 IST)"
cap 10-no-such-webinar "$B/99"
date '+%-d %b %Y' > date.txt
