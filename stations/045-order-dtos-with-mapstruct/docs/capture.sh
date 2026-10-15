#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which builds the jar, starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/orders
J="Content-Type: application/json"
ORDER='{"customerName":"Asha Verma","phone":"9876543210","address":{"line":"Flat 4B, Lotus Residency, Baner Road","city":"Pune","pincode":"411045"},"deliveryInstructions":"Ring twice, baby sleeping","lines":[{"item":"Paneer thali","quantity":2,"unitPricePaise":24900},{"item":"Masala chaas","quantity":1,"unitPricePaise":4900}]}'
cap 01-place-an-order -X POST "$B" -H "$J" -d "$ORDER"
cap 02-read-it-back "$B/1"
cap 03-no-such-order "$B/99"
cap 04-a-five-digit-pin -X POST "$B" -H "$J" -d "${ORDER/411045/41104}"
cap 05-the-client-sets-the-total -X POST "$B" -H "$J" -d "${ORDER/\"customerName\"/\"totalPaise\":1,\"customerName\"}"
# The mapper MapStruct generated for this build, as compiled into the jar the captures ran against.
cp ../../target/generated-sources/annotations/com/tiffino/ordering/OrderMapperImpl.java generated-OrderMapperImpl.java.txt
date '+%-d %b %Y' > date.txt
