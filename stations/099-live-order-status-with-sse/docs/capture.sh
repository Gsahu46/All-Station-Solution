#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
filter() { grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; }
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | filter; echo; } > "$name.txt"; }
# A stream, read as it arrives (-N), for at most SECS seconds: these streams only end by themselves at delivery or after 5 minutes.
stream() { name=$1; secs=$2; shift 2; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; timeout "$secs" curl -s -i -N "$@" | filter || true; echo; } > "$name.txt"; }
B=http://localhost:8080
RIYA=(-u riya:riya-demo-pass -H 'Accept: text/event-stream')
KITCHEN=(-u kitchen:kitchen-demo-pass -H 'Content-Type: application/json')
stream 01-riya-watches-order-1001 4 "${RIYA[@]}" "$B/orders/1001/events" &
sleep 1
cap 02-the-kitchen-accepts "${KITCHEN[@]}" -d '{"status":"ACCEPTED"}' "$B/orders/1001/status"
cap 03-and-starts-cooking "${KITCHEN[@]}" -d '{"status":"COOKING"}' "$B/orders/1001/status"
wait
cap 04-out-for-delivery-while-riya-is-in-a-tunnel "${KITCHEN[@]}" -d '{"status":"OUT_FOR_DELIVERY"}' "$B/orders/1001/status"
stream 05-riya-reconnects-with-last-event-id 10 "${RIYA[@]}" -H 'Last-Event-ID: 3' "$B/orders/1001/events" &
sleep 1
cap 06-delivered "${KITCHEN[@]}" -d '{"status":"DELIVERED"}' "$B/orders/1001/status"
wait   # the server ends the stream after the delivered event: curl stops by itself
cap 07-reconnecting-after-the-end "${RIYA[@]}" -H 'Last-Event-ID: 5' "$B/orders/1001/events"
cap 08-kabir-watches-riyas-order -u kabir:kabir-demo-pass -H 'Accept: text/event-stream' "$B/orders/1001/events"
cap 09-skipping-a-step "${KITCHEN[@]}" -d '{"status":"DELIVERED"}' "$B/orders/1003/status"
cap 10-no-sign-in -H 'Accept: text/event-stream' "$B/orders/1003/events"
date '+%-d %b %Y' > date.txt
