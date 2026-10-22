#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
cap 01-v1-the-shape-old-apps-read "$B/v1/orders/1001"
cap 02-v2-the-new-shape "$B/v2/orders/1001"
cap 03-v2-an-order-not-shipped-yet "$B/v2/orders/1002"
cap 04-a-version-that-does-not-exist "$B/v3/orders/1001"
cap 05-v1-an-unknown-order "$B/v1/orders/9"
cap 06-v2-an-id-that-is-not-a-number "$B/v2/orders/abc"
cap 07-v1-0-is-version-1-too "$B/v1.0/orders/1001"
{ echo "v1 says: $(curl -s "$B/v1/orders/1002")"; echo "v2 says: $(curl -s "$B/v2/orders/1002")"; } > try-1002.txt
date '+%-d %b %Y' > date.txt
