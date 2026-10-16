#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts both databases and the app on PostgreSQL, port 8080).
# This script starts a second copy of the same jar on MySQL, port 8081. Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
java -jar ../../target/*.jar --server.port=8081 --spring.profiles.active=mysql > /dev/null 2>&1 & MYSQL_APP=$!
trap 'kill $MYSQL_APP 2>/dev/null || true' EXIT
for _ in $(seq 1 90); do curl -s -o /dev/null http://localhost:8081/ && break; sleep 1; done
J="Content-Type: application/json"
PG=http://localhost:8080/signups
MY=http://localhost:8081/signups
cap 01-on-postgresql-asha-signs-up -X POST "$PG" -H "$J" -d '{"email":"Asha@x.com","name":"Asha Verma"}'
cap 02-on-postgresql-asha-again-in-lower-case -X POST "$PG" -H "$J" -d '{"email":"asha@x.com","name":"Asha Verma"}'
cap 03-on-mysql-asha-signs-up -X POST "$MY" -H "$J" -d '{"email":"Asha@x.com","name":"Asha Verma"}'
cap 04-on-mysql-asha-again-in-lower-case -X POST "$MY" -H "$J" -d '{"email":"asha@x.com","name":"Asha Verma"}'
cap 05-an-email-without-an-at -X POST "$PG" -H "$J" -d '{"email":"asha.x.com","name":"Asha Verma"}'
cap 06-no-such-signup "$PG/99"
# What "equal" means to each database, asked directly: no table, no index, just the default comparison.
{ echo "-- PostgreSQL 17"
  docker compose -f ../../compose.yaml exec -T postgres psql -U taskloom -d taskloom \
    -c "SELECT 'Asha@x.com' = 'asha@x.com' AS case_ignored, 'jose@x.com' = 'josé@x.com' AS accents_ignored"
  echo "-- MySQL 8.4, default collation $(docker compose -f ../../compose.yaml exec -T -e MYSQL_PWD=taskloom mysql mysql --default-character-set=utf8mb4 -N -utaskloom taskloom -e 'SELECT @@collation_connection')"
  docker compose -f ../../compose.yaml exec -T -e MYSQL_PWD=taskloom mysql mysql --default-character-set=utf8mb4 -t -utaskloom taskloom \
    -e "SELECT 'Asha@x.com' = 'asha@x.com' AS case_ignored, 'jose@x.com' = 'josé@x.com' AS accents_ignored"; } > equality.txt
date '+%-d %b %Y' > date.txt
