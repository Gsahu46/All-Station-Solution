#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
cap 01-asha-sends-ravi-1500 -X POST "$B/transfers" -H "$J" -d '{"fromAccountId":1,"toAccountId":2,"amountPaise":150000}'
cap 02-ravi-tries-to-send-5000 -X POST "$B/transfers" -H "$J" -d '{"fromAccountId":2,"toAccountId":1,"amountPaise":500000}'
cap 03-asha-sends-to-account-99 -X POST "$B/transfers" -H "$J" -d '{"fromAccountId":1,"toAccountId":99,"amountPaise":1000}'
cap 04-ashas-audit-trail "$B/audit-events?accountId=1"
cap 05-ravis-audit-trail "$B/audit-events?accountId=2"
cap 06-account-99 "$B/audit-events?accountId=99"
cap 07-99-paise -X POST "$B/transfers" -H "$J" -d '{"fromAccountId":1,"toAccountId":2,"amountPaise":99}'
# The balances: Asha was debited once (case 1); case 3's debit was rolled back, its audit events were not.
docker compose -f ../../compose.yaml exec -T postgres psql -U tijori -d tijori -c "SELECT id, holder, balance_paise FROM accounts ORDER BY id" > balances.txt
date '+%-d %b %Y' > date.txt
