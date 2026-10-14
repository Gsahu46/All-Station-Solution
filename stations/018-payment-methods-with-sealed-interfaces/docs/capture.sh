#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/payment-intents
J="Content-Type: application/json"
cap 01-upi -X POST "$U" -H "$J" -d '{"orderId":"ORD-1042","amountPaise":49900,"method":{"type":"UPI","vpa":"Asha.R@OKAXIS"}}'
cap 02-card -X POST "$U" -H "$J" -d '{"orderId":"ORD-1043","amountPaise":129900,"method":{"type":"CARD","network":"RUPAY","last4":"4242","token":"tok_9f8e7d6c5b4a"}}'
cap 03-net-banking -X POST "$U" -H "$J" -d '{"orderId":"ORD-1044","amountPaise":250000,"method":{"type":"NET_BANKING","bankCode":"hdfc"}}'
cap 04-wallet -X POST "$U" -H "$J" -d '{"orderId":"ORD-1045","amountPaise":9900,"method":{"type":"WALLET","mobile":"9876543210"}}'
cap 05-two-methods-at-once -X POST "$U" -H "$J" -d '{"orderId":"ORD-1046","amountPaise":49900,"method":{"type":"UPI","vpa":"asha@okaxis","last4":"4242"}}'
cap 06-unknown-type -X POST "$U" -H "$J" -d '{"orderId":"ORD-1047","amountPaise":49900,"method":{"type":"CHEQUE","number":"000123"}}'
cap 07-bank-not-offered -X POST "$U" -H "$J" -d '{"orderId":"ORD-1048","amountPaise":49900,"method":{"type":"NET_BANKING","bankCode":"ABCD"}}'
date '+%-d %b %Y' > date.txt
