#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
U=$B/refunds
J="Content-Type: application/json"
# The ticket's stack trace: the ticket's request replayed on the old code (kept in the tests), this app's frames only.
java -cp ../../target/classes:../../target/test-classes com.kartwala.refunds.TicketReplay > ticket-stack-trace.txt
cap 01-the-tickets-request -X POST "$U" -H "$J" -H "X-Request-Id: req-5b1e9d42" -d '{"orderId":"KW-1042","lineIds":["L2"]}'
cap 02-the-same-line-again -X POST "$U" -H "$J" -H "X-Request-Id: req-5b1e9d43" -d '{"orderId":"KW-1042","lineIds":["L2"]}'
cap 03-the-rest-of-the-order -X POST "$U" -H "$J" -d '{"orderId":"KW-1042"}'
cap 04-one-line-of-a-coupon-order -X POST "$U" -H "$J" -d '{"orderId":"KW-1041","lineIds":["L2"]}'
cap 05-the-last-line-takes-what-is-left -X POST "$U" -H "$J" -d '{"orderId":"KW-1041"}'
cap 06-a-line-the-order-does-not-have -X POST "$U" -H "$J" -d '{"orderId":"KW-1041","lineIds":["L9"]}'
cap 07-no-such-order -X POST "$U" -H "$J" -d '{"orderId":"KW-9999"}'
cap 08-the-metric-the-alert-reads "$B/actuator/metrics/refunds.requests?tag=outcome:recorded"
# The app's own log lines for the ticket's request ids (APP_LOG is set by tools/build_station.sh), without timestamps and pids.
grep -E "rid:req-5b1e9d4[23]\]" "$APP_LOG" | sed -E 's/^[0-9T:.Z+-]+ +//; s/ [0-9]+ --- / --- /' > app-log.txt
date '+%-d %b %Y' > date.txt
