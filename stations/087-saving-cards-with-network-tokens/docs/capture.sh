#!/usr/bin/env bash
# Captures real request/response pairs and the stored rows into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
ASHA=asha:asha-demo-pass
ROHAN=rohan:rohan-demo-pass
pg() { docker compose -f ../../compose.yaml exec -T postgres "$@"; }
cap 01-asha-saves-a-card -X POST "$B/customers/1/saved-cards" -u "$ASHA" -H "$J" -d '{"cardNumber": "4111 1111 1111 1111", "expiryMonth": 12, "expiryYear": 2028, "consent": true}'
cap 02-asha-lists-her-cards "$B/customers/1/saved-cards" -u "$ASHA"
cap 03-rohan-lists-ashas-cards "$B/customers/1/saved-cards" -u "$ROHAN"
cap 04-no-sign-in "$B/customers/1/saved-cards"
cap 05-a-wrong-check-digit -X POST "$B/customers/1/saved-cards" -u "$ASHA" -H "$J" -d '{"cardNumber": "4111111111111112", "expiryMonth": 12, "expiryYear": 2028, "consent": true}'
cap 06-no-consent -X POST "$B/customers/1/saved-cards" -u "$ASHA" -H "$J" -d '{"cardNumber": "5555555555554444", "expiryMonth": 1, "expiryYear": 2027, "consent": false}'
cap 07-asha-pays-with-her-saved-card -X POST "$B/payments" -u "$ASHA" -H "$J" -d '{"orderId": "ORD-1001", "savedCardId": 1, "amountPaise": 129900}'
cap 08-the-same-order-again -X POST "$B/payments" -u "$ASHA" -H "$J" -d '{"orderId": "ORD-1001", "savedCardId": 1, "amountPaise": 129900}'
cap 09-rohan-pays-with-ashas-card -X POST "$B/payments" -u "$ROHAN" -H "$J" -d '{"orderId": "ORD-2001", "savedCardId": 1, "amountPaise": 129900}'
cap 10-a-decline -X POST "$B/payments" -u "$ASHA" -H "$J" -d '{"orderId": "ORD-1002", "savedCardId": 1, "amountPaise": 129951}'
pg psql -U paysetu -d paysetu -v ON_ERROR_STOP=1 -q -c "SELECT id, customer_id, token_ref, network, last4, expiry_month, expiry_year, status FROM saved_cards" > saved-cards.txt
pg psql -U paysetu -d paysetu -v ON_ERROR_STOP=1 -q -c "SELECT id, order_id, saved_card_id, amount_paise, status, network_ref FROM payments ORDER BY id" > payments.txt
n=$(pg pg_dump -U paysetu -d paysetu --data-only | grep -c 4111111111111111 || true)
echo "Lines in a full data dump of the database containing 4111111111111111: $n" > dump-search.txt
date '+%-d %b %Y' > date.txt
