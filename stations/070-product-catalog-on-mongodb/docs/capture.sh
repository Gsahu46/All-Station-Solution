#!/usr/bin/env bash
# Captures real request/response pairs and MongoDB's own answers into docs/captures/.
# Run by tools/build_station.sh --capture (which starts MongoDB and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/catalog/products
J="Content-Type: application/json"
cap 01-a-saree-a-category-nobody-planned -X POST "$B" -H "$J" -d '{"sku": "sr-silk-red", "name": "Kanjeevaram Silk", "category": "sarees", "sellerId": 8, "pricePaise": 1250000, "attributes": {"fabric": "silk", "colour": "Red", "length_m": "6.3"}}'
cap 02-phones-with-8gb "$B?category=phones&attr.ram=8GB"
cap 03-the-same-sku-again -X POST "$B" -H "$J" -d '{"sku": "sr-silk-red", "name": "Kanjeevaram Silk", "category": "sarees", "sellerId": 8, "pricePaise": 1250000, "attributes": {"fabric": "silk"}}'
cap 04-an-operator-as-a-value -X POST "$B" -H "$J" -d '{"sku": "sr-x", "name": "X", "category": "sarees", "sellerId": 8, "pricePaise": 1250000, "attributes": {"fabric": {"$gt": ""}}}'
cap 05-an-operator-as-a-field -G "$B" --data-urlencode 'attr.$where=1'
mongosh() { docker compose -f ../../compose.yaml exec -T mongo mongosh --quiet kartwala --eval "$1"; }
mongosh 'const p = db.products.find({"attributes.ram": "8GB"}).explain().queryPlanner.winningPlan; const s = p.queryPlan ?? p; print(JSON.stringify({stage: s.stage, inputStage: {stage: s.inputStage.stage, indexName: s.inputStage.indexName, keyPattern: s.inputStage.keyPattern}}, null, 2))' > explain-attributes.txt
mongosh 'try { db.products.insertOne({sku: "SR-CHEAP", name: "X", category: "sarees", sellerId: NumberLong("8"), pricePaise: -100, attributes: {}}) } catch (e) { print(e.errInfo.failingDocumentId ? "Document failed validation: " + JSON.stringify(e.errInfo.details.schemaRulesNotSatisfied[0]) : e.message) }' > validator-refuses.txt
date '+%-d %b %Y' > date.txt
