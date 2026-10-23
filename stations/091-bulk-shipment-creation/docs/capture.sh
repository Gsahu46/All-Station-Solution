#!/usr/bin/env bash
# Captures real request/response pairs and the shipment rows into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U dakroute -d dakroute -v ON_ERROR_STOP=1 -q "$@"; }
A='"to":{"name":"Meera Iyer","line1":"14 Lodhi Road","city":"New Delhi","pincode":"110003","phone":"9810000001"}'
cap 01-three-shipments-one-bad-pin-code -X POST "$B/shipments/bulk" -H "$J" -d "{\"shipments\":[{\"ref\":\"ORD-1001\",\"fromPincode\":\"560001\",\"weightGrams\":1200,$A},{\"ref\":\"ORD-1002\",\"fromPincode\":\"560001\",\"weightGrams\":800,\"to\":{\"name\":\"Arjun Rao\",\"line1\":\"2 MG Road\",\"city\":\"Pune\",\"pincode\":\"41100\",\"phone\":\"9820000002\"}},{\"ref\":\"ORD-1003\",\"fromPincode\":\"560001\",\"weightGrams\":2500,$A}]}"
cap 02-an-item-with-three-problems -X POST "$B/shipments/bulk" -H "$J" -d '{"shipments":[{"ref":"ORD-1004","fromPincode":"560001","weightGrams":0,"to":{"name":" ","line1":"14 Lodhi Road","city":"New Delhi","pincode":"110003","phone":"12345"}}]}'
cap 03-a-ref-already-used -X POST "$B/shipments/bulk" -H "$J" -d "{\"shipments\":[{\"ref\":\"ORD-1001\",\"fromPincode\":\"560001\",\"weightGrams\":900,$A}]}"
cap 04-an-empty-batch -X POST "$B/shipments/bulk" -H "$J" -d '{"shipments":[]}'
cap 05-a-weight-that-is-not-a-number -X POST "$B/shipments/bulk" -H "$J" -d "{\"shipments\":[{\"ref\":\"ORD-1005\",\"fromPincode\":\"560001\",\"weightGrams\":\"heavy\",$A}]}"
items=$(for i in $(seq 1 501); do printf '{"ref":"BIG-%d","fromPincode":"560001","weightGrams":500,%s},' "$i" "$A"; done)
cap 06-five-hundred-and-one -X POST "$B/shipments/bulk" -H "$J" -d "{\"shipments\":[${items%,}]}"
# The request line is shortened for the page; the request sent had all 501 items.
sed -i "1s/'-d' '.*/'-d' '{\"shipments\":[ 501 items: {\"ref\":\"BIG-1\", ...} to {\"ref\":\"BIG-501\", ...} ]}'/" 06-five-hundred-and-one.txt
psql -c "SELECT id, ref, from_pincode, to_city, to_pincode, weight_grams FROM shipments ORDER BY id" > shipments.txt
date '+%-d %b %Y' > date.txt
