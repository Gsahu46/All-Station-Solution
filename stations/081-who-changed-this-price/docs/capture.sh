#!/usr/bin/env bash
# Captures real request/response pairs and the history rows into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U kartwala -d kartwala -v ON_ERROR_STOP=1 -q "$@"; }
cap 01-neha-drops-the-tv-price -u neha.store:neha-demo-pass -X PUT "$B/products/1/price" -H "$J" -d '{"pricePaise": 549900}'
cap 02-neha-puts-it-back -u neha.store:neha-demo-pass -X PUT "$B/products/1/price" -H "$J" -d '{"pricePaise": 5499900}'
cap 03-support-reads-the-history -u sam.help:sam-demo-pass "$B/products/1/history"
cap 04-a-body-that-names-someone-else -u neha.store:neha-demo-pass -X PUT "$B/products/2/price" -H "$J" -d '{"pricePaise": 1199900, "changedBy": "priya.ops"}'
cap 05-another-seller-asks -u arun.mart:arun-demo-pass "$B/products/1/history"
cap 06-support-tries-to-change-a-price -u sam.help:sam-demo-pass -X PUT "$B/products/1/price" -H "$J" -d '{"pricePaise": 100}'
cap 07-a-price-with-paise-after-the-point -u neha.store:neha-demo-pass -X PUT "$B/products/1/price" -H "$J" -d '{"pricePaise": 5499.99}'
psql -c "SELECT a.id AS product, a.rev, a.revtype, a.price_paise, r.changed_by, to_timestamp(r.changed_at_ms / 1000.0) AT TIME ZONE 'UTC' AS changed_at_utc FROM products_aud a JOIN revisions r ON r.id = a.rev ORDER BY a.rev, a.id" > history-rows.txt
psql -c "UPDATE products_aud SET price_paise = 5499900 WHERE rev = 2" > tidy-up.txt 2>&1 || true
date '+%-d %b %Y' > date.txt
