#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/seller/products
cap 01-chaiwala-lists-its-products "$B" -H "X-Seller-Id: 1"
cap 02-it-deletes-assam-tea -X DELETE "$B/1" -H "X-Seller-Id: 1"
cap 03-the-list-now "$B" -H "X-Seller-Id: 1"
cap 04-with-archived-products "$B?includeArchived=true" -H "X-Seller-Id: 1"
cap 05-another-sellers-product -X DELETE "$B/3" -H "X-Seller-Id: 1"
cap 06-no-seller-header -X DELETE "$B/2"
# The order history after the archive, and what a real DELETE meets, through psql.
P="docker compose -f ../../compose.yaml exec -T postgres psql -U kartwala -d kartwala"
{ $P -c "SELECT l.order_ref, p.name, l.quantity, l.unit_price_paise, p.archived_at IS NOT NULL AS archived FROM order_lines l JOIN products p ON p.id = l.product_id ORDER BY l.id"
  $P -c "DELETE FROM products WHERE id = 1" 2>&1 || true; } > order-history.txt
date '+%-d %b %Y' > date.txt
