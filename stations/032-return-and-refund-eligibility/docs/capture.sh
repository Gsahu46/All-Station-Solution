#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/refund-eligibility-checks
J="Content-Type: application/json"
cap 01-a-kurta-that-did-not-fit -X POST "$U" -H "$J" -d '{"orderId":"KW-1001","reason":"SIZE_ISSUE","tagsAttached":true}'
cap 02-innerwear-changed-mind -X POST "$U" -H "$J" -d '{"orderId":"KW-1002","reason":"CHANGED_MIND","tagsAttached":true}'
cap 03-earbuds-every-reason -X POST "$U" -H "$J" -d '{"orderId":"KW-1003","reason":"CHANGED_MIND","sealIntact":false}'
cap 04-a-damaged-phone -X POST "$U" -H "$J" -d '{"orderId":"KW-1004","reason":"DAMAGED","sealIntact":false}'
cap 05-groceries-changed-mind -X POST "$U" -H "$J" -d '{"orderId":"KW-1005","reason":"CHANGED_MIND"}'
cap 06-not-delivered-yet -X POST "$U" -H "$J" -d '{"orderId":"KW-1006","reason":"CHANGED_MIND"}'
cap 07-no-such-order -X POST "$U" -H "$J" -d '{"orderId":"KW-9999","reason":"DAMAGED"}'
cap 08-clothing-without-the-tags-answer -X POST "$U" -H "$J" -d '{"orderId":"KW-1001","reason":"SIZE_ISSUE"}'
date '+%-d %b %Y' > date.txt
