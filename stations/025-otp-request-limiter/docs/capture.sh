#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/otp-requests
J="Content-Type: application/json"
cap 01-first-request -X POST "$U" -H "$J" -H "Idempotency-Key: tap-7f3a-0001" -d '{"mobile":"9876543210"}'
cap 02-the-app-retries-the-same-tap -X POST "$U" -H "$J" -H "Idempotency-Key: tap-7f3a-0001" -d '{"mobile":"+91 98765 43210"}'
cap 03-second-tap -X POST "$U" -H "$J" -H "Idempotency-Key: tap-7f3a-0002" -d '{"mobile":"098765-43210"}'
cap 04-third-tap -X POST "$U" -H "$J" -H "Idempotency-Key: tap-7f3a-0003" -d '{"mobile":"9876543210"}'
cap 05-fourth-tap -X POST "$U" -H "$J" -H "Idempotency-Key: tap-7f3a-0004" -d '{"mobile":"9876543210"}'
cap 06-key-reused-for-another-number -X POST "$U" -H "$J" -H "Idempotency-Key: tap-7f3a-0001" -d '{"mobile":"9123456780"}'
cap 07-not-a-mobile-number -X POST "$U" -H "$J" -H "Idempotency-Key: tap-7f3a-0005" -d '{"mobile":"12345"}'
date '+%-d %b %Y' > date.txt
