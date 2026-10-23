#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
ZOOMKART=(-H 'X-Api-Key: mw_demo_zoomkart_7Qp2Lx9V')
CHALO=(-H 'X-Api-Key: mw_demo_chalo_K3vN8sT1')
cap 01-zoomkart-geocodes "${ZOOMKART[@]}" "$B/geocode?address=MG%20Road,%20Bengaluru"
cap 02-any-case-and-spacing "${ZOOMKART[@]}" "$B/geocode?address=%20%20marine%20%20DRIVE,%20mumbai"
cap 03-not-a-known-place "${ZOOMKART[@]}" "$B/geocode?address=Nowhere%20Lane,%20Atlantis"
cap 04-too-short "${ZOOMKART[@]}" "$B/geocode?address=MG"
cap 05-no-key "$B/geocode?address=MG%20Road,%20Bengaluru"
cap 06-key-in-the-url "$B/geocode?address=MG%20Road,%20Bengaluru&api_key=mw_demo_zoomkart_7Qp2Lx9V"
cap 07-a-suspended-key -H 'X-Api-Key: mw_demo_oldmaps_P0dW5yZr' "$B/geocode?address=MG%20Road,%20Bengaluru"
cap 08-chalo-reads-zoomkarts-usage "${CHALO[@]}" "$B/partners/1/usage"
sleep 1   # Chalo's bucket full again after case 8
# Zoomkart's bug: 50 requests as fast as curl can send them, one after another.
for _ in $(seq 1 50); do curl -s -o /dev/null -w '%{http_code}\n' "${ZOOMKART[@]}" "$B/geocode?address=MG%20Road,%20Bengaluru"; done | sort | uniq -c | awk '{print $2 " x " $1}' > zoomkart-50-requests.txt
cap 09-zoomkarts-50th-request "${ZOOMKART[@]}" "$B/geocode?address=MG%20Road,%20Bengaluru"
cap 10-chalo-right-after "${CHALO[@]}" "$B/geocode?address=Park%20Street,%20Kolkata"
curl -s -o /dev/null "${CHALO[@]}" "$B/geocode?address=Park%20Street,%20Kolkata"
curl -s -o /dev/null "${CHALO[@]}" "$B/geocode?address=Park%20Street,%20Kolkata"
cap 11-chalos-fourth-in-a-second "${CHALO[@]}" "$B/geocode?address=Park%20Street,%20Kolkata"
sleep 1   # one token back: the usage call needs one too
cap 12-chalos-usage "${CHALO[@]}" "$B/partners/2/usage"
date '+%-d %b %Y' > date.txt
