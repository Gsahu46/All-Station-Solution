#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/wallets/w-asha
J="Content-Type: application/json"
cap 01-credit-10.5-inr -X POST "$U/credits" -H "$J" -d '{"amount":"10.5","currency":"INR","reference":"cashback-1"}'
cap 02-credit-10.50-inr -X POST "$U/credits" -H "$J" -d '{"amount":"10.50","currency":"INR","reference":"cashback-2"}'
cap 03-credit-usd -X POST "$U/credits" -H "$J" -d '{"amount":"5","currency":"USD","reference":"refund-us-store"}'
cap 04-credit-jpy -X POST "$U/credits" -H "$J" -d '{"amount":"1500","currency":"JPY","reference":"trip-leftover"}'
cap 05-balance "$U/balance"
cap 06-too-many-decimals -X POST "$U/credits" -H "$J" -d '{"amount":"1500.5","currency":"JPY","reference":"oops"}'
cap 07-unsupported-currency -X POST "$U/credits" -H "$J" -d '{"amount":"5","currency":"BTC","reference":"oops"}'
cap 08-unknown-wallet http://localhost:8080/wallets/w-nobody/balance
date '+%-d %b %Y' > date.txt
