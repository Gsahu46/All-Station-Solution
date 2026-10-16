#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
cap 01-a-debit-alert-for-asha -X POST "$B/notifications" -H "$J" -d '{"customerId":1,"type":"DEBIT_ALERT","amountPaise":149900,"merchant":"BigBasket"}'
cap 02-a-debit-alert-for-rohan -X POST "$B/notifications" -H "$J" -d '{"customerId":2,"type":"DEBIT_ALERT","amountPaise":149900,"merchant":"BigBasket"}'
cap 03-asha-turns-off-email-and-push -X PUT "$B/customers/1/notification-preferences" -H "$J" -d '{"sms":true,"email":false,"push":false}'
cap 04-her-statement-notice -X POST "$B/notifications" -H "$J" -d '{"customerId":1,"type":"STATEMENT_READY"}'
cap 05-a-debit-in-crores -X POST "$B/notifications" -H "$J" -d '{"customerId":1,"type":"DEBIT_ALERT","amountPaise":1234567890,"merchant":"Sunrise Motors"}'
cap 06-a-debit-alert-without-amount -X POST "$B/notifications" -H "$J" -d '{"customerId":1,"type":"DEBIT_ALERT"}'
cap 07-an-unknown-type -X POST "$B/notifications" -H "$J" -d '{"customerId":1,"type":"LOAN_OFFER"}'
cap 08-preferences-of-customer-99 -X PUT "$B/customers/99/notification-preferences" -H "$J" -d '{"sms":true,"email":true,"push":true}'
date '+%-d %b %Y' > date.txt
