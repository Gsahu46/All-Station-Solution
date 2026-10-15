#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
cap 01-shorten-a-campaign-link -X POST "$B/links" -H "$J" -d '{"targetUrl":"https://shop.example/diwali-sale?utm_source=sms&utm_medium=bulk&utm_campaign=diwali2026&utm_content=variant-b"}'
C=$(grep -o '"code":"[^"]*"' 01-shorten-a-campaign-link.txt | cut -d'"' -f4)
cap 02-someone-taps-it "$B/$C"
cap 03-someone-else-taps-it "$B/$C"
cap 04-the-click-count "$B/links/$C/stats"
cap 05-a-code-that-does-not-exist "$B/zzzzzzz"
cap 06-a-javascript-link -X POST "$B/links" -H "$J" -d '{"targetUrl":"javascript:alert(document.cookie)"}'
date '+%-d %b %Y' > date.txt
