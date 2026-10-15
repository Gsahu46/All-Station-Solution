#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/products
J="Content-Type: application/json"
cap 01-asha-reviews-the-headphones -X POST "$B/1/reviews" -H "$J" -d '{"customerId":1,"stars":5,"text":"Good bass, and the battery really lasts a week."}'
cap 02-vikram-reviews-them -X POST "$B/1/reviews" -H "$J" -d '{"customerId":2,"stars":3,"text":"Comfortable, but the case feels cheap."}'
cap 03-the-rating "$B/1/rating"
cap 04-asha-again -X POST "$B/1/reviews" -H "$J" -d '{"customerId":1,"stars":5,"text":"Still love them!"}'
cap 05-neha-before-delivery -X POST "$B/1/reviews" -H "$J" -d '{"customerId":3,"stars":1,"text":"Not here yet."}'
cap 06-the-reviews "$B/1/reviews?page=0"
cap 07-no-such-product "$B/99/rating"
# 200,000 reviews of the water bottle written straight to the tables, the stored totals backfilled from them once,
# then both ways of getting the rating, with PostgreSQL's own measurements.
P="docker compose -f ../../compose.yaml exec -T postgres psql -U kartwala -d kartwala"
$P -q <<'SQL'
INSERT INTO customers (id, name) SELECT 1000 + g, 'Buyer ' || g FROM generate_series(1, 200000) g;
INSERT INTO purchases (id, customer_id, product_id, delivered_on) SELECT 1000 + g, 1000 + g, 2, DATE '2026-01-01' FROM generate_series(1, 200000) g;
INSERT INTO reviews (product_id, customer_id, purchase_id, stars, text, created_at)
SELECT 2, 1000 + g, 1000 + g, CASE WHEN g % 10 < 5 THEN 5 WHEN g % 10 < 8 THEN 4 ELSE 2 END, 'Keeps water cold', now() FROM generate_series(1, 200000) g;
UPDATE product_ratings SET (review_count, star_total) = (SELECT count(*), sum(stars) FROM reviews WHERE product_id = 2) WHERE product_id = 2;
VACUUM ANALYZE reviews;
SQL
{ echo "-- The old rating: recomputed from every review, on every product page view"
  $P -c "EXPLAIN (ANALYZE, COSTS OFF) SELECT avg(stars), count(*) FROM reviews WHERE product_id = 2"
  echo "-- The stored rating: one row by primary key"
  $P -c "EXPLAIN (ANALYZE, COSTS OFF) SELECT review_count, star_total FROM product_ratings WHERE product_id = 2"; } > plans.txt
cap 08-the-bottle-rating "$B/2/rating"
date '+%-d %b %Y' > date.txt
