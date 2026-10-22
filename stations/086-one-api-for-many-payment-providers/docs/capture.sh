#!/usr/bin/env bash
# Captures real request/response pairs and the payment rows into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U paysetu -d paysetu -v ON_ERROR_STOP=1 -q "$@"; }
cap 01-a-payment -X POST "$B/payments" -H "$J" -d '{"orderId": "ORD-1001", "amountPaise": 249900}'
cap 02-the-same-order-again -X POST "$B/payments" -H "$J" -d '{"orderId": "ord-1001", "amountPaise": 249900}'
cap 03-the-same-order-another-amount -X POST "$B/payments" -H "$J" -d '{"orderId": "ORD-1001", "amountPaise": 100000}'
cap 04-a-decline -X POST "$B/payments" -H "$J" -d '{"orderId": "ORD-1002", "amountPaise": 249951}'
cap 05-sim-alpha-charges-then-times-out -X POST "$B/payments" -H "$J" -d '{"orderId": "ORD-1003", "amountPaise": 249997}'
cap 06-sim-alpha-refuses-the-connection -X POST "$B/payments" -H "$J" -d '{"orderId": "ORD-1004", "amountPaise": 249998}'
cap 07-refund-part-of-the-first -X POST "$B/payments/1/refunds" -H "$J" -d '{"amountPaise": 100000}'
cap 08-refund-the-sim-beta-payment -X POST "$B/payments/4/refunds" -H "$J" -d '{"amountPaise": 249998}'
cap 09-refund-more-than-is-left -X POST "$B/payments/1/refunds" -H "$J" -d '{"amountPaise": 200000}'
cap 10-refund-a-declined-payment -X POST "$B/payments/2/refunds" -H "$J" -d '{"amountPaise": 100}'
cap 11-an-order-id-with-a-space -X POST "$B/payments" -H "$J" -d '{"orderId": "ORD 1005", "amountPaise": 249900}'
psql -c "SELECT id, order_id, amount_paise, status, provider, provider_ref, decline_reason, refunded_paise FROM payments ORDER BY id" > payments.txt
psql -c "SELECT id, payment_id, amount_paise, status, provider_ref FROM refunds ORDER BY id" > refunds.txt
date '+%-d %b %Y' > date.txt
