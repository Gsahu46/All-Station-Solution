#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
H=http://localhost:8080
J="Content-Type: application/json"
cap 01-classes "$H/classes?date=2026-10-19"
cap 02-book -X POST "$H/classes/1/bookings" -H "$J" -d '{"memberId":101}'
curl -s -o /dev/null -X POST "$H/classes/1/bookings" -H "$J" -d '{"memberId":102}'   # fills Morning Yoga (capacity 2)
cap 03-full -X POST "$H/classes/1/bookings" -H "$J" -d '{"memberId":103}'
cap 04-already-booked -X POST "$H/classes/1/bookings" -H "$J" -d '{"memberId":101}'
cap 05-unknown-class -X POST "$H/classes/999/bookings" -H "$J" -d '{"memberId":101}'
cap 06-member-bookings "$H/members/101/bookings"
LOC=$(grep -i '^Location:' 02-book.txt | cut -d' ' -f2)
cap 07-cancel -X DELETE "$H$LOC"
cap 08-cancel-again -X DELETE "$H$LOC"
date '+%-d %b %Y' > date.txt
