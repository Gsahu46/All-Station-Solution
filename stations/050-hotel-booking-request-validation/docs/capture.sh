#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/hotel-bookings
J="Content-Type: application/json"
day() { TZ=Asia/Kolkata date -d "+$1 days" +%F; }   # dates relative to today in India, as the app sees them
IN=$(day 30); OUT=$(day 33)
OK='{"hotelId":1,"roomType":"STANDARD","checkIn":"'$IN'","checkOut":"'$OUT'","adults":2,"children":0,"guestName":"Asha Verma","phone":"98765 43210"}'
cap 01-a-valid-request -X POST "$B" -H "$J" -d "$OK"
cap 02-read-it-back "$B/1"
SWAPPED=${OK/\"checkIn\":\"$IN\"/\"checkIn\":\"$OUT\"}
cap 03-check-out-before-check-in -X POST "$B" -H "$J" -d "${SWAPPED/\"checkOut\":\"$OUT\"/\"checkOut\":\"$IN\"}"
cap 04-six-guests-in-a-standard-room -X POST "$B" -H "$J" -d "${OK/\"adults\":2,\"children\":0/\"adults\":4,\"children\":2}"
NOPHONE=${OK/98765 43210/12345}
cap 05-a-bad-phone-and-no-adults -X POST "$B" -H "$J" -d "${NOPHONE/\"adults\":2/\"adults\":0}"
NOIN=${OK/\"checkIn\":\"$IN\",/}
cap 06-a-missing-date-and-six-guests -X POST "$B" -H "$J" -d "${NOIN/\"adults\":2/\"adults\":6}"
cap 07-no-such-booking "$B/999"
date '+%-d %b %Y' > date.txt
