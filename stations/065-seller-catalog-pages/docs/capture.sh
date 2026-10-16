#!/usr/bin/env bash
# Captures real request/response pairs and a paging experiment into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/seller/products
cap 01-meera-handlooms-first-page -H "X-Seller-Id: 8" "$B?size=3"
cap 02-dearest-first-page-two -H "X-Seller-Id: 7" "$B?sort=pricePaise,desc&size=3&page=1"
cap 03-a-size-of-5000 -H "X-Seller-Id: 8" "$B?size=5000"
cap 04-sort-by-a-column-not-on-the-list -H "X-Seller-Id: 7" "$B?sort=sellerId"
cap 05-no-such-seller -H "X-Seller-Id: 99" "$B"
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U kartwala -d kartwala -v ON_ERROR_STOP=1 -q "$@"; }
# Every page of seller 7's 2,000 products, 20 at a time: how many different products were shown? Ties are ordered
# by whatever plan PostgreSQL picks, so the experiment runs under both plans: a sort (index scans off) and the index.
EXPERIMENT="
DO \$\$ BEGIN FOR p IN 0..99 LOOP
  INSERT INTO seen SELECT current_setting('my.plan') || ': price only', id FROM (SELECT id FROM products WHERE seller_id = 7 ORDER BY price_paise LIMIT 20 OFFSET p * 20) x;
  INSERT INTO seen SELECT current_setting('my.plan') || ': price, then id', id FROM (SELECT id FROM products WHERE seller_id = 7 ORDER BY price_paise, id LIMIT 20 OFFSET p * 20) x;
END LOOP; END \$\$;"
PAGE="EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY OFF) SELECT id FROM products WHERE seller_id = 7 ORDER BY price_paise LIMIT 20 OFFSET 60"
psql -c "ANALYZE products" -c "CREATE TEMP TABLE seen (sort text, id bigint)" \
     -c "SET my.plan = 'sorted'" -c "SET enable_indexscan = off" -c "SET enable_indexonlyscan = off" -c "SET enable_bitmapscan = off" -c "$EXPERIMENT" -c "$PAGE" \
     -c "SET my.plan = 'from the index'" -c "RESET enable_indexscan" -c "RESET enable_indexonlyscan" -c "RESET enable_bitmapscan" -c "$EXPERIMENT" -c "$PAGE" \
     -c "SELECT sort AS \"plan: ORDER BY\", count(*) AS rows_shown, count(DISTINCT id) AS different_products, 2000 - count(DISTINCT id) AS never_shown FROM seen GROUP BY sort ORDER BY sort DESC" > paging-experiment.txt
date '+%-d %b %Y' > date.txt
