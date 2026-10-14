#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/invoices/tax-preview
J="Content-Type: application/json"
OFFICE='[{"description":"Team T-shirt","hsn":"6109","quantity":3,"unitPricePaise":79900},{"description":"Keyboard","hsn":"8471","quantity":1,"unitPricePaise":124950},{"description":"Mouse","hsn":"8471","quantity":1,"unitPricePaise":54950},{"description":"USB cable","hsn":"8544","quantity":3,"unitPricePaise":19950}]'
SHIRT='[{"description":"Polo T-shirt","hsn":"6109","quantity":1,"unitPricePaise":149900}]'
cap 01-same-state -X POST "$U" -H "$J" -d '{"invoiceDate":"2026-10-13","placeOfSupply":"29","lines":'"$OFFICE"'}'
cap 02-other-state -X POST "$U" -H "$J" -d '{"invoiceDate":"2026-10-13","placeOfSupply":"27","lines":'"$OFFICE"'}'
cap 03-tshirt-before-22-sep-2025 -X POST "$U" -H "$J" -d '{"invoiceDate":"2025-09-21","placeOfSupply":"29","lines":'"$SHIRT"'}'
cap 04-tshirt-from-22-sep-2025 -X POST "$U" -H "$J" -d '{"invoiceDate":"2025-09-22","placeOfSupply":"29","lines":'"$SHIRT"'}'
cap 05-unknown-hsn -X POST "$U" -H "$J" -d '{"invoiceDate":"2026-10-13","placeOfSupply":"29","lines":[{"description":"Mystery box","hsn":"1234","quantity":1,"unitPricePaise":10000}]}'
cap 06-unknown-state -X POST "$U" -H "$J" -d '{"invoiceDate":"2026-10-13","placeOfSupply":"99","lines":'"$SHIRT"'}'
date '+%-d %b %Y' > date.txt
