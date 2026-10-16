#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/loyalty
J="Content-Type: application/json"
cap 01-asha-earns-on-a-1499-order -X POST "$B/1/earn" -H "$J" -d '{"orderRef":"BK-1002","amountPaise":149900}'
cap 02-rohans-first-points -X POST "$B/2/earn" -H "$J" -d '{"orderRef":"BK-1003","amountPaise":25000}'
cap 03-the-same-order-again -X POST "$B/2/earn" -H "$J" -d '{"orderRef":"bk-1003","amountPaise":25000}'
cap 04-asha-redeems-100 -X POST "$B/1/redeem" -H "$J" -d '{"points":100}'
cap 05-asha-redeems-500 -X POST "$B/1/redeem" -H "$J" -d '{"points":500}'
cap 06-customer-99 -X POST "$B/99/earn" -H "$J" -d '{"orderRef":"BK-1004","amountPaise":10000}'
cap 07-an-amount-of-zero -X POST "$B/1/earn" -H "$J" -d '{"orderRef":"BK-1005","amountPaise":0}'
# The old code's upsert, sent to the same PostgreSQL the app runs on.
docker compose -f ../../compose.yaml exec -T postgres psql -U basketo -d basketo \
  -c "MERGE INTO point_balances (customer_id, points) KEY (customer_id) VALUES (2, 5)" > old-upsert.txt 2>&1 || true
date '+%-d %b %Y' > date.txt
