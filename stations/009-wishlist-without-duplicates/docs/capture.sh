#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/wishlists/7
J="Content-Type: application/json"
cap 01-add -X POST "$U/items" -H "$J" -d '{"sku":"ph-12"}'
cap 02-add-upper -X POST "$U/items" -H "$J" -d '{"sku":"PH-12"}'
cap 03-add-spaces -X POST "$U/items" -H "$J" -d '{"sku":" PH-12 "}'
cap 04-add-tv -X POST "$U/items" -H "$J" -d '{"sku":"tv-55"}'
cap 05-unknown-product -X POST "$U/items" -H "$J" -d '{"sku":"XX-99"}'
cap 06-bad-sku -X POST "$U/items" -H "$J" -d '{"sku":"PH 12!"}'
cap 07-remove -X DELETE "$U/items/ph-12"
cap 08-get "$U"
date '+%-d %b %Y' > date.txt
