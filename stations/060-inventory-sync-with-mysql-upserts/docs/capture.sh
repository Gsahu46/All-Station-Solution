#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts MySQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/warehouses
J="Content-Type: application/json"
cap 01-bhiwandi-first-snapshot -X PUT "$B/1/stock" -H "$J" -d '{"items":[{"sku":"RICE-5KG","quantity":40},{"sku":"ATTA-10KG","quantity":12},{"sku":"dal-1kg","quantity":25}]}'
cap 02-the-same-job-again-rice-recounted -X PUT "$B/1/stock" -H "$J" -d '{"items":[{"sku":"RICE-5KG","quantity":35}]}'
cap 03-one-sku-twice -X PUT "$B/1/stock" -H "$J" -d '{"items":[{"sku":"OIL-1L","quantity":5},{"sku":"oil-1l","quantity":8}]}'
cap 04-no-such-warehouse -X PUT "$B/99/stock" -H "$J" -d '{"items":[{"sku":"RICE-5KG","quantity":1}]}'
cap 05-half-a-bag -X PUT "$B/1/stock" -H "$J" -d '{"items":[{"sku":"RICE-5KG","quantity":2.5}]}'
mysql() { docker compose -f ../../compose.yaml exec -T -e MYSQL_PWD=basketo mysql mysql --default-character-set=utf8mb4 -t -ubasketo basketo -e "$1"; }
mysql "SELECT warehouse_id, sku, quantity FROM stock_levels ORDER BY warehouse_id, sku" > rows.txt
# Both warehouses' nightly jobs at once, five runs each, on the same 200 new SKUs.
SNAP=$(seq -f 'SKU-%05g' 1 200 | awk 'BEGIN{printf "{\"items\":["} {printf "%s{\"sku\":\"%s\",\"quantity\":7}", (NR>1?",":""), $0} END{print "]}"}')
{ echo "10 syncs at once (5 per warehouse), 200 new SKUs each: HTTP status counts"
  seq 1 10 | xargs -P 10 -I{} sh -c 'curl -s -o /dev/null -w "%{http_code}\n" -X PUT "'"$B"'/$(( {} % 2 + 1 ))/stock" -H "'"$J"'" -d "$0"' "$SNAP" | sort | uniq -c
  echo; echo "Rows per warehouse afterwards"
  mysql "SELECT warehouse_id, count(*) AS skus, count(DISTINCT sku) AS distinct_skus FROM stock_levels WHERE sku LIKE 'SKU-%' GROUP BY warehouse_id"
  echo; echo "Deadlocks the app retried (its own log lines)"
  grep -c "deadlocked (attempt" "$APP_LOG" || true
} > rush.txt
# The same upsert, asked of MySQL directly: affected rows 1 (inserted), 2 (updated), 0 (unchanged) in the mysql client.
mysql "INSERT INTO stock_levels (warehouse_id, sku, quantity) VALUES (2, 'TEA-250G', 10) AS incoming ON DUPLICATE KEY UPDATE quantity = incoming.quantity; SELECT ROW_COUNT() AS inserted;
       INSERT INTO stock_levels (warehouse_id, sku, quantity) VALUES (2, 'TEA-250G', 11) AS incoming ON DUPLICATE KEY UPDATE quantity = incoming.quantity; SELECT ROW_COUNT() AS updated;
       INSERT INTO stock_levels (warehouse_id, sku, quantity) VALUES (2, 'TEA-250G', 11) AS incoming ON DUPLICATE KEY UPDATE quantity = incoming.quantity; SELECT ROW_COUNT() AS unchanged" > row-count.txt
date '+%-d %b %Y' > date.txt
