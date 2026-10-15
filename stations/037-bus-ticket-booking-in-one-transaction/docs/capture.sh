#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/bookings
J="Content-Type: application/json"
cap 01-a-family-of-two -X POST "$U" -H "$J" -d '{"tripId":101,"contactPhone":"9876543210","passengers":[{"name":"Asha Verma","age":34,"seatNo":12},{"name":"Kabir Verma","age":8,"seatNo":13}]}'
cap 02-one-seat-already-taken -X POST "$U" -H "$J" -d '{"tripId":101,"contactPhone":"9123456780","passengers":[{"name":"Ravi Iyer","age":41,"seatNo":11},{"name":"Meena Iyer","age":39,"seatNo":12}]}'
cap 03-the-free-seat-was-never-held -X POST "$U" -H "$J" -d '{"tripId":101,"contactPhone":"9123456780","passengers":[{"name":"Ravi Iyer","age":41,"seatNo":11}]}'
cap 04-a-seat-the-bus-does-not-have -X POST "$U" -H "$J" -d '{"tripId":101,"contactPhone":"9123456780","passengers":[{"name":"Ravi Iyer","age":41,"seatNo":41}]}'
cap 05-no-such-trip -X POST "$U" -H "$J" -d '{"tripId":999,"contactPhone":"9123456780","passengers":[{"name":"Ravi Iyer","age":41,"seatNo":1}]}'
cap 06-a-bad-phone-number -X POST "$U" -H "$J" -d '{"tripId":101,"contactPhone":"12345","passengers":[{"name":"Ravi Iyer","age":41,"seatNo":1}]}'
# What the database holds after those six requests: two bookings, three passengers, none half-saved.
docker compose -f ../../compose.yaml exec -T postgres psql -U safarbus -d safarbus -c \
  "SELECT b.id AS booking, b.total_paise, count(p.seat_no) AS passengers, string_agg(p.seat_no::text, ', ' ORDER BY p.seat_no) AS seats FROM bookings b LEFT JOIN booking_passengers p ON p.booking_id = b.id GROUP BY b.id ORDER BY b.id" > db-after.txt
date '+%-d %b %Y' > date.txt
