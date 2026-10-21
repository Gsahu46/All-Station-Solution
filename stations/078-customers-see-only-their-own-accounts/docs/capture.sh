#!/usr/bin/env bash
# Captures real request/response pairs into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U tijori -d tijori -v ON_ERROR_STOP=1 -q "$@"; }
cap 01-zoyas-own-account -u zoya@example.com:zoya-demo-pass "$B/accounts/1001"
cap 02-the-next-number -u zoya@example.com:zoya-demo-pass "$B/accounts/1002"
cap 03-a-number-that-does-not-exist -u zoya@example.com:zoya-demo-pass "$B/accounts/9999"
cap 04-zoyas-september-statement -u zoya@example.com:zoya-demo-pass "$B/accounts/1001/statements?month=2026-09"
cap 05-the-joint-account-as-dev -u dev@example.com:dev-demo-pass "$B/accounts/1003"
cap 06-the-shop-account-balance-only -u ravi@example.com:ravi-demo-pass "$B/accounts/1004"
cap 07-the-shop-statement-balance-only -u ravi@example.com:ravi-demo-pass "$B/accounts/1004/statements?month=2026-09"
cap 08-a-month-that-is-not-a-month -u zoya@example.com:zoya-demo-pass "$B/accounts/1001/statements?month=2026-13"
cap 09-no-credentials "$B/accounts/1001"
psql -c "SELECT h.account_id, c.email, h.access FROM account_holders h JOIN customers c ON c.id = h.customer_id ORDER BY h.account_id, c.email" > holders.txt
date '+%-d %b %Y' > date.txt
