#!/usr/bin/env bash
# Captures real request/response pairs from the running app and its PostgreSQL into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary|www-authenticate):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J=(-H 'Content-Type: application/json')
cap 01-a-small-refund -u asha:asha-demo-pass "${J[@]}" -d '{"amountPaise":250000,"reason":"Dent on the side panel"}' "$B/orders/5001/refunds"
cap 02-a-large-refund -u asha:asha-demo-pass "${J[@]}" -d '{"amountPaise":900000,"reason":"Drum does not spin"}' "$B/orders/5001/refunds"
cap 03-the-asker-tries-to-approve -u meena:meena-demo-pass "${J[@]}" -d '{"amountPaise":600000,"reason":"Wrong colour delivered"}' "$B/orders/5003/refunds"
cap 04-and-is-refused -u meena:meena-demo-pass "${J[@]}" -d '{"decision":"APPROVE"}' "$B/refunds/3/approvals"
cap 05-another-approver-approves -u raj:raj-demo-pass "${J[@]}" -d '{"decision":"APPROVE"}' "$B/refunds/2/approvals"
cap 06-more-than-is-left -u vikram:vikram-demo-pass "${J[@]}" -d '{"amountPaise":200000,"reason":"Late delivery"}' "$B/orders/5001/refunds"
cap 07-the-order-afterwards -u raj:raj-demo-pass "$B/orders/5001"
cap 08-a-rejection -u raj:raj-demo-pass "${J[@]}" -d '{"decision":"REJECT"}' "$B/refunds/3/approvals"
cap 09-decided-already -u raj:raj-demo-pass "${J[@]}" -d '{"decision":"APPROVE"}' "$B/refunds/3/approvals"
cap 10-no-such-order -u asha:asha-demo-pass "${J[@]}" -d '{"amountPaise":1000,"reason":"Test"}' "$B/orders/9999/refunds"
cap 11-a-zero-refund -u asha:asha-demo-pass "${J[@]}" -d '{"amountPaise":0,"reason":"Test"}' "$B/orders/5002/refunds"
cap 12-an-agent-tries-to-approve -u asha:asha-demo-pass "${J[@]}" -d '{"decision":"APPROVE"}' "$B/refunds/1/approvals"
# Twenty refunds of ₹1,000 at once on the ₹4,999 mixer.
for i in $(seq 1 20); do curl -s -o /dev/null -w '%{http_code}\n' -u asha:asha-demo-pass "${J[@]}" -d '{"amountPaise":100000,"reason":"Customer called again"}' "$B/orders/5002/refunds" & done > burst.txt
wait
sort burst.txt | uniq -c | awk '{print $2": "$1}' > burst-summary.txt && rm burst.txt
cap 13-the-mixer-afterwards -u raj:raj-demo-pass "$B/orders/5002"
# Writing past the rule by hand, as a script or a console might.
docker compose -f ../../compose.yaml exec -T postgres psql -U kartwala -d kartwala -c "UPDATE orders SET reserved_paise = 600000 WHERE id = 5002" > db-guard.txt 2>&1 || true
date '+%-d %b %Y' > date.txt
