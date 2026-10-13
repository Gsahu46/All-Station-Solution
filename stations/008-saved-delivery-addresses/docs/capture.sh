#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/customers/42/addresses
J="Content-Type: application/json"
B='{"line1":"Flat 402, Lotus Residency","line2":"14th Cross, Indiranagar","landmark":"Opposite Cafe Coffee Day","city":"Bengaluru","pincode":"560038"}'
cap 01-put-new -X PUT "$U/home" -H "$J" -d "$B"
cap 02-put-again -X PUT "$U/home" -H "$J" -d "$B"
cap 03-patch -X PATCH "$U/home" -H "Content-Type: application/merge-patch+json" -d '{"landmark":"Next to Indiranagar metro","line2":null}'
cap 04-list "$U"
cap 05-post -X POST "$U/home" -H "$J" -d "$B"
cap 06-bad-pincode -X PUT "$U/work" -H "$J" -d '{"line1":"Floor 3, Prestige Tech Park","city":"Bengaluru","pincode":"06003"}'
cap 07-delete -X DELETE "$U/home"
cap 08-delete-again -X DELETE "$U/home"
date '+%-d %b %Y' > date.txt
