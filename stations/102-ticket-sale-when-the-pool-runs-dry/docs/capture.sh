#!/usr/bin/env bash
# Captures real request/response pairs from the running app and its PostgreSQL into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
rm -f drill-orders.txt
python3 ../test-gateway.py 9099 & GW=$!
trap 'kill $GW 2>/dev/null || true' EXIT
sleep 1
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J=(-H 'Content-Type: application/json')
cap 01-two-seats-for-the-big-match "${J[@]}" -d '{"buyer":"Priya Nair","seats":2}' "$B/sales/1/orders"
cap 02-the-sale-afterwards "$B/sales/1"
cap 03-four-seats-at-the-small-match "${J[@]}" -d '{"buyer":"Ravi Kumar","seats":4}' "$B/sales/2/orders"
cap 04-one-more-at-the-small-match "${J[@]}" -d '{"buyer":"Asha Rao","seats":1}' "$B/sales/2/orders"
cap 05-seven-seats "${J[@]}" -d '{"buyer":"Asha Rao","seats":7}' "$B/sales/1/orders"
cap 06-no-such-sale "${J[@]}" -d '{"buyer":"Asha Rao","seats":1}' "$B/sales/9/orders"
# The drill: the gateway hangs for 10 s. Twenty orders at once; meanwhile, how fast does the rest of the app answer?
curl -s -o /dev/null -d '{"seconds":10}' http://127.0.0.1:9099/delay
pids=()
for i in $(seq 1 20); do curl -s -o /dev/null -w '%{http_code} %{time_total}\n' "${J[@]}" -d '{"buyer":"fan","seats":1}' "$B/sales/1/orders" >> drill-orders.txt & pids+=($!); done
sleep 1
curl -s -o /dev/null -w 'GET /sales/1 during the hang: %{http_code} in %{time_total} s\n' "$B/sales/1" > drill-read.txt
wait "${pids[@]}"   # the orders only: the gateway runs in the background too
curl -s -o /dev/null -d '{"seconds":0}' http://127.0.0.1:9099/delay
awk '{n[$1]++; if ($2 > max) max = $2} END {for (c in n) printf "%s x %d\n", c, n[c]; printf "slowest: %.1f s\n", max}' drill-orders.txt > drill.txt
rm drill-orders.txt
cap 07-the-sale-after-the-drill "$B/sales/1"
curl -s "$B/actuator/metrics/hikaricp.connections.timeout" | python3 -c 'import json,sys; m=json.load(sys.stdin); print("hikaricp.connections.timeout =", m["measurements"][0]["value"])' > pool-metrics.txt
curl -s "$B/actuator/metrics/hikaricp.connections.usage" | python3 -c 'import json,sys; m={x["statistic"]: x["value"] for x in json.load(sys.stdin)["measurements"]}; print("hikaricp.connections.usage: count =", int(m["COUNT"]), ", max =", round(m["MAX"] * 1000, 1), "ms")' >> pool-metrics.txt
date '+%-d %b %Y' > date.txt
