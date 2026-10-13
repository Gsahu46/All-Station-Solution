#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
B='{"payerVpa":"asha@okpaysetu","payeeVpa":"ravi@oksbi","amountPaise":12550,"note":"Dinner split"}'
K=7f3c9a2e-5b1d-4e8a-9c6f-2d4b8e1a0c37
cap() { name=$1; shift; { echo "\$ curl $*"; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
cap 01-create -X POST http://localhost:8080/payments -H "Idempotency-Key: $K" -H "Content-Type: application/json" -d "$B"
cap 02-retry-same-key -X POST http://localhost:8080/payments -H "Idempotency-Key: $K" -H "Content-Type: application/json" -d "$B"
cap 03-same-key-different-amount -X POST http://localhost:8080/payments -H "Idempotency-Key: $K" -H "Content-Type: application/json" -d "${B/12550/99900}"
cap 04-missing-key -X POST http://localhost:8080/payments -H "Content-Type: application/json" -d "$B"
cap 05-invalid-fields -X POST http://localhost:8080/payments -H "Idempotency-Key: 0b8e4f6a-1c2d-4e3f-8a9b-7c6d5e4f3a2b" -H "Content-Type: application/json" -d '{"payerVpa":"asha","payeeVpa":"ravi@oksbi","amountPaise":0}'
ID=$(grep -o '"paymentId":"[^"]*"' 01-create.txt | cut -d'"' -f4)
cap 06-get "http://localhost:8080/payments/$ID"
cap 07-get-unknown http://localhost:8080/payments/00000000-0000-0000-0000-000000000000
date '+%-d %b %Y' > date.txt
