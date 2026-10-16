#!/usr/bin/env bash
# Captures real request/response pairs and query plans into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/products
J="Content-Type: application/json"
cap 01-a-new-phone -X POST "$B" -H "$J" -d '{"sku": "ph-pixel-12-256", "name": "Pixel Pro", "category": "phones", "sellerId": 7, "pricePaise": 5999900, "attributes": {"ram": "12GB", "storage": "256GB", "colour": "Obsidian"}}'
cap 02-a-shoe-that-breaks-the-rules -X POST "$B" -H "$J" -d '{"sku": "sh-odd-13", "name": "Odd Shoe", "category": "shoes", "sellerId": 8, "pricePaise": 99900, "attributes": {"size": "13", "ram": "8GB"}}'
cap 03-phones-with-8gb-and-256gb "$B?category=phones&attr.ram=8GB&attr.storage=256GB"
cap 04-size-9-leather "$B?attr.size=9&attr.material=leather"
cap 05-ram-on-a-shoe "$B?category=shoes&attr.ram=8GB"
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U kartwala -d kartwala -v ON_ERROR_STOP=1 -q "$@"; }
explain() { psql -c "EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY OFF) $1"; }
explain "SELECT id FROM products WHERE attributes @> '{\"ram\": \"12GB\"}'" > explain-containment.txt
explain "SELECT id FROM products WHERE attributes->>'ram' = '12GB'" > explain-arrow.txt
date '+%-d %b %Y' > date.txt
