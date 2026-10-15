#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/flash-sales
J="Content-Type: application/json"
cap 01-a-buyer-gets-a-phone -X POST "$B/1/purchases" -H "$J" -d '{"customerId":"C-000123"}'
cap 02-the-same-buyer-again -X POST "$B/1/purchases" -H "$J" -d '{"customerId":"C-000123"}'
cap 03-a-sold-out-sale -X POST "$B/2/purchases" -H "$J" -d '{"customerId":"C-000123"}'
cap 04-a-sale-that-ended -X POST "$B/3/purchases" -H "$J" -d '{"customerId":"C-000123"}'
cap 05-a-sale-not-started -X POST "$B/4/purchases" -H "$J" -d '{"customerId":"C-000123"}'
cap 06-no-such-sale -X POST "$B/99/purchases" -H "$J" -d '{"customerId":"C-000123"}'
# A real rush: sale 5 with 50 phones, 300 different buyers, 50 requests in flight at a time.
PSQL="docker compose -f ../../compose.yaml exec -T postgres psql -U kartwala -d kartwala"
$PSQL -q -c "INSERT INTO flash_sales VALUES (5, 'Rush test phone', 50, 50, 999900, now() - interval '1 minute', now() + interval '1 hour')"
{ echo "300 buyers, 50 phones, 50 requests at a time: HTTP status counts"
  seq 1 300 | xargs -P 50 -I{} sh -c 'curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8080/flash-sales/5/purchases -H "Content-Type: application/json" -d "{\"customerId\":\"C-$(printf %06d {})\"}"' | sort | uniq -c
  echo
  $PSQL -c "SELECT s.stock_total, s.stock_left, count(p.id) AS purchases FROM flash_sales s LEFT JOIN purchases p ON p.sale_id = s.id WHERE s.id = 5 GROUP BY s.id"
} > rush.txt
date '+%-d %b %Y' > date.txt
