#!/usr/bin/env bash
# Captures real request/response pairs from the running app and its PostgreSQL into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J=(-H 'Content-Type: application/json')
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U paysetu -d paysetu -v ON_ERROR_STOP=1 -q "$@"; }
cap 01-ravi-registers-his-server -u ravi:ravi-demo-pass "${J[@]}" -d '{"url":"http://127.0.0.1:9095/hooks/paysetu"}' "$B/merchants/1/webhook-endpoints"
SECRET=$(sed -n 's/.*"secret":"\([^"]*\)".*/\1/p' 01-ravi-registers-his-server.txt)
python3 ../test-merchant.py 9095 "$SECRET" > merchant-server.txt 2>&1 & MERCHANT=$!
trap 'kill $MERCHANT 2>/dev/null || true' EXIT
cap 02-a-second-server-that-is-off -u ravi:ravi-demo-pass "${J[@]}" -d '{"url":"http://127.0.0.1:9096/hooks"}' "$B/merchants/1/webhook-endpoints"
cap 03-the-same-url-again -u ravi:ravi-demo-pass "${J[@]}" -d '{"url":"http://127.0.0.1:9095/hooks/paysetu"}' "$B/merchants/1/webhook-endpoints"
cap 04-not-a-web-address -u ravi:ravi-demo-pass "${J[@]}" -d '{"url":"file:///etc/passwd"}' "$B/merchants/1/webhook-endpoints"
cap 05-a-payment-is-captured -u ravi:ravi-demo-pass "${J[@]}" -d '{"paymentRef":"PAY-1001","amountPaise":49900}' "$B/merchants/1/test-events"
cap 06-reported-again -u ravi:ravi-demo-pass "${J[@]}" -d '{"paymentRef":"PAY-1001","amountPaise":49900}' "$B/merchants/1/test-events"
cap 07-again-with-another-amount -u ravi:ravi-demo-pass "${J[@]}" -d '{"paymentRef":"PAY-1001","amountPaise":4990000}' "$B/merchants/1/test-events"
cap 08-meena-on-ravis-merchant -u meena:meena-demo-pass "${J[@]}" -d '{"url":"http://127.0.0.1:9097/steal"}' "$B/merchants/1/webhook-endpoints"
cap 09-no-sign-in "$B/webhook-deliveries"
sleep 3   # one dispatcher round: both first tries recorded
cap 10-right-after -u ravi:ravi-demo-pass "$B/webhook-deliveries"
# The merchant answers 503 once; the retry comes 30 s later. Wait for its 200 (at most 60 s).
for _ in $(seq 1 60); do grep -q "answered 200" merchant-server.txt && break; sleep 1; done
grep -q "answered 200" merchant-server.txt
cap 11-delivered-after-the-retry -u ravi:ravi-demo-pass "$B/webhook-deliveries?status=DELIVERED"
cap 12-the-delivery-log -u ravi:ravi-demo-pass "$B/webhook-deliveries/1"
cap 13-the-server-that-is-off -u ravi:ravi-demo-pass "$B/webhook-deliveries?status=PENDING"
cap 14-meena-reads-ravis-delivery -u meena:meena-demo-pass "$B/webhook-deliveries/1"
cap 15-not-a-status -u ravi:ravi-demo-pass "$B/webhook-deliveries?status=LOST"
psql -c "SELECT delivery_id, to_char(attempted_at, 'HH24:MI:SS') AS at_utc, status_code, error, duration_ms FROM delivery_attempts ORDER BY id" > attempts.txt
date '+%-d %b %Y' > date.txt
