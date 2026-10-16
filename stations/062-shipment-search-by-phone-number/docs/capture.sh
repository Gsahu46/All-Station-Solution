#!/usr/bin/env bash
# Captures real request/response pairs and real query plans into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/shipments/search
cap 01-march-for-one-customer -G "$B" --data-urlencode "phone=9876543210" -d from=2026-03-01 -d to=2026-03-31
cap 02-the-phone-as-the-customer-says-it -G "$B" --data-urlencode "phone=+91 98765 43210" -d from=2026-01-01 -d to=2026-12-31
cap 03-nothing-in-april -G "$B" --data-urlencode "phone=9876543210" -d from=2026-04-01 -d to=2026-04-30
cap 04-not-a-mobile-number -G "$B" --data-urlencode "phone=12345" -d from=2026-03-01 -d to=2026-03-31
cap 05-dates-backwards -G "$B" --data-urlencode "phone=9876543210" -d from=2026-03-31 -d to=2026-03-01
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U dakroute -d dakroute -v ON_ERROR_STOP=1 -q "$@"; }
# EXPLAIN (ANALYZE, BUFFERS): the plan PostgreSQL chose and the 8 kB pages it touched ("Buffers: shared hit/read").
explain() { psql -c "SET max_parallel_workers_per_gather = 0" -c "EXPLAIN (ANALYZE, BUFFERS, COSTS OFF, TIMING OFF, SUMMARY OFF) $1"; }
explain "SELECT awb, booked_on, status FROM shipments WHERE phone = '9876543210' AND booked_on BETWEEN '2026-03-01' AND '2026-03-31' ORDER BY booked_on DESC, id DESC LIMIT 50" > explain-the-search.txt
# The old table and search: phones as typed, cleaned in SQL, with an index on phone that cannot be used.
psql -c "DROP TABLE IF EXISTS old_shipments" -c "CREATE TABLE old_shipments AS SELECT id, awb, CASE id % 3 WHEN 0 THEN '+91 ' || substr(phone, 1, 5) || ' ' || substr(phone, 6) WHEN 1 THEN '0' || phone ELSE phone END AS phone, booked_on, status FROM shipments" \
     -c "CREATE INDEX old_shipments_phone ON old_shipments (phone)" -c "ANALYZE old_shipments"
explain "SELECT awb, booked_on, status FROM old_shipments WHERE right(regexp_replace(phone, '[^0-9]', '', 'g'), 10) = '9876543210' AND booked_on BETWEEN '2026-03-01' AND '2026-03-31' ORDER BY booked_on DESC, id DESC LIMIT 50" > explain-the-old-search.txt
# The same search on a copy indexed the other way round: range column first.
psql -c "DROP TABLE IF EXISTS shipments_copy" -c "CREATE TABLE shipments_copy AS SELECT * FROM shipments" -c "CREATE INDEX copy_date_phone ON shipments_copy (booked_on, phone)" -c "ANALYZE shipments_copy"
explain "SELECT awb, booked_on, status FROM shipments_copy WHERE phone = '9876543210' AND booked_on BETWEEN '2026-01-01' AND '2026-09-30' ORDER BY booked_on DESC, id DESC LIMIT 50" > explain-date-first-index.txt
psql -c "DROP TABLE old_shipments, shipments_copy"
# What the indexes cost in space; every insert writes to each of them too.
psql -c "SELECT c.relname AS name, CASE c.relkind WHEN 'r' THEN 'table' ELSE 'index' END AS kind, pg_size_pretty(pg_relation_size(c.oid)) AS size FROM pg_class c WHERE c.relname IN ('shipments', 'shipments_pkey', 'shipments_awb_unique', 'shipments_phone_booked_on') ORDER BY pg_relation_size(c.oid) DESC" > sizes.txt
date '+%-d %b %Y' > date.txt
