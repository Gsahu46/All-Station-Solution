#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/invoices
J="Content-Type: application/json"
INVOICE='{"customerName":"Kaveri Textiles Pvt Ltd","lines":[{"description":"Cloud hosting, March 2026","quantity":1,"unitPricePaise":499900},{"description":"Support hours","quantity":6,"unitPricePaise":150000}]}'
CORRECTED='{"lines":[{"description":"Cloud hosting, March 2026","quantity":1,"unitPricePaise":499900},{"description":"Support hours","quantity":4,"unitPricePaise":150000}]}'
cap 01-create-an-invoice -X POST "$B" -H "$J" -d "$INVOICE"
cap 02-correct-the-lines -X PUT "$B/1/lines" -H "$J" -d "$CORRECTED"
cap 03-read-it-back "$B/1"
cap 04-no-lines -X PUT "$B/1/lines" -H "$J" -d '{"lines":[]}'
cap 05-a-price-with-decimals -X PUT "$B/1/lines" -H "$J" -d "${CORRECTED/150000/1500.50}"
cap 06-no-such-invoice "$B/99"
# The table itself after the requests above: rows 1 and 2 (the original lines) are gone, not orphaned.
docker compose -f ../../compose.yaml exec -T postgres psql -U billora -d billora \
  -c "SELECT id, invoice_id, description, quantity, unit_price_paise FROM invoice_lines ORDER BY id" > rows.txt
date '+%-d %b %Y' > date.txt
