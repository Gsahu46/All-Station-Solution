#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/restaurants
cap 01-mumbai "$B?city=mumbai"
cap 02-pune-first-five "$B?city=pune&size=5"
cap 03-nagpur-no-restaurants-yet "$B?city=Nagpur"
cap 04-a-city-tiffino-does-not-serve "$B?city=jaipur"
cap 05-too-big-a-page "$B?city=pune&size=500"
# The SQL behind one page of 50: a second copy of the jar with Hibernate's SQL log on, port 8081, one request.
java -jar ../../target/*.jar --server.port=8081 --logging.level.org.hibernate.SQL=debug > sql-app.log 2>&1 & SQL_APP=$!
trap 'kill $SQL_APP 2>/dev/null || true; rm -f sql-app.log' EXIT
for _ in $(seq 1 90); do curl -s -o /dev/null http://localhost:8081/ && break; sleep 1; done
BEFORE=$(wc -l < sql-app.log)
curl -s -o /dev/null "http://localhost:8081/restaurants?city=pune&size=50"
sleep 1
{ echo "SQL statements for GET /restaurants?city=pune&size=50 (Hibernate's own log, one per line):"
  tail -n +$((BEFORE + 1)) sql-app.log | grep -a "org.hibernate.SQL" | sed -E 's/^.*org\.hibernate\.SQL[^:]*: *//'
} > sql.txt
date '+%-d %b %Y' > date.txt
