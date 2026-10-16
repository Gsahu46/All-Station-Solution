#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first, logging to $APP_LOG).
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
cap 01-a-payout -X POST "$B/payouts" -H "$J" -d '{"merchantId":1,"amountPaise":1000000,"ifsc":"HDFC0001234","accountNumber":"50100123457890"}'
cap 02-read-it-back "$B/payouts/1"
cap 03-not-enough-balance -X POST "$B/payouts" -H "$J" -d '{"merchantId":2,"amountPaise":50000,"ifsc":"SBIN0004567","accountNumber":"30012345678"}'
cap 04-an-unknown-merchant -X POST "$B/payouts" -H "$J" -d '{"merchantId":99,"amountPaise":1000,"ifsc":"HDFC0001234","accountNumber":"50100123457890"}'
cap 05-a-bad-ifsc -X POST "$B/payouts" -H "$J" -d '{"merchantId":1,"amountPaise":1000,"ifsc":"HDFC1001234","accountNumber":"50100123457890"}'
cap 06-the-audit-log "$B/audit-events"
cap 07-no-such-payout "$B/payouts/99"
# The aspect's own log lines from the running app: one per audited call, with its time.
grep -o "PAYOUT_REQUESTED .*" "$APP_LOG" > app-log.txt
date '+%-d %b %Y' > date.txt
