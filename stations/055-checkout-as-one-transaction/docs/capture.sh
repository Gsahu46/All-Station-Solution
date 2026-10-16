#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/checkouts
J="Content-Type: application/json"
cap 01-a-checkout -X POST "$B" -H "$J" -d '{"customerId":7,"lines":[{"productId":1,"quantity":2},{"productId":2,"quantity":5}]}'
cap 02-read-it-back "$B/1"
cap 03-the-chilli-is-sold-out-now -X POST "$B" -H "$J" -d '{"customerId":8,"lines":[{"productId":2,"quantity":1}]}'
cap 04-tea-and-a-sold-out-box -X POST "$B" -H "$J" -d '{"customerId":8,"lines":[{"productId":1,"quantity":2},{"productId":3,"quantity":1}]}'
cap 05-an-unknown-product -X POST "$B" -H "$J" -d '{"customerId":8,"lines":[{"productId":99,"quantity":1}]}'
cap 06-quantity-zero -X POST "$B" -H "$J" -d '{"customerId":8,"lines":[{"productId":1,"quantity":0}]}'
cap 07-no-such-checkout "$B/99"
# What the database holds after all of that: one order, and the tea from case 4 was given back.
docker compose -f ../../compose.yaml exec -T postgres psql -U kartwala -d kartwala -c "
  SELECT (SELECT count(*) FROM orders) AS orders, (SELECT count(*) FROM reservations) AS reservations,
         (SELECT count(*) FROM payments) AS payments, (SELECT stock FROM products WHERE id = 1) AS tea_stock,
         (SELECT stock FROM products WHERE id = 2) AS chilli_stock" > state.txt
date '+%-d %b %Y' > date.txt
