#!/usr/bin/env bash
# Captures real request/response pairs and the SQL behind one search into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/hotels
cap 01-goa-wifi-and-pool-under-rs-5000 "$B?city=goa&amenities=wifi,pool&maxPrice=5000"
cap 02-jaipur-4-and-5-stars-dearest-first "$B?city=jaipur&stars=4,5&sort=-price"
cap 03-a-sort-that-is-not-on-the-list -G "$B" --data-urlencode "sort=name; DELETE FROM hotel_amenities"
cap 04-an-amenity-ghoomo-does-not-list "$B?amenities=wifi,sauna"
cap 05-no-hotel-in-shimla "$B?city=shimla"
# The SQL behind case 1: a second copy of the jar with Hibernate's SQL log on, port 8081, one request.
java -jar ../../target/*.jar --server.port=8081 --logging.level.org.hibernate.SQL=debug > sql-app.log 2>&1 & SQL_APP=$!
trap 'kill $SQL_APP 2>/dev/null || true; rm -f sql-app.log' EXIT
for _ in $(seq 1 90); do curl -s -o /dev/null http://localhost:8081/ && break; sleep 1; done
BEFORE=$(wc -l < sql-app.log)
curl -s -o /dev/null "http://localhost:8081/hotels?city=goa&amenities=wifi,pool&maxPrice=5000"
sleep 1
{ echo "SQL statements for GET /hotels?city=goa&amenities=wifi,pool&maxPrice=5000 (Hibernate's own log, one per line):"
  tail -n +$((BEFORE + 1)) sql-app.log | grep -a "org.hibernate.SQL" | sed -E 's/^.*org\.hibernate\.SQL[^:]*: *//'
} > sql.txt
date '+%-d %b %Y' > date.txt
