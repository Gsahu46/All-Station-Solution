#!/usr/bin/env bash
# Captures real request/response pairs and the wallet rows into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U tijori -d tijori -v ON_ERROR_STOP=1 -q "$@"; }
cap 01-ananya-tops-up-6000 -X POST "$B/wallets/1001/top-ups" -H "$J" -d '{"amountPaise": 600000}'
cap 02-ananya-tries-5000-more -X POST "$B/wallets/1001/top-ups" -H "$J" -d '{"amountPaise": 500000}'
cap 03-ananya-tops-up-exactly-4000 -X POST "$B/wallets/1001/top-ups" -H "$J" -d '{"amountPaise": 400000}'
cap 04-vikram-full-kyc-tops-up-50000 -X POST "$B/wallets/1002/top-ups" -H "$J" -d '{"amountPaise": 5000000}'
cap 05-unknown-wallet -X POST "$B/wallets/9999/top-ups" -H "$J" -d '{"amountPaise": 100000}'
cap 06-rupees-sent-as-a-fraction -X POST "$B/wallets/1001/top-ups" -H "$J" -d '{"amountPaise": 4000.5}'
# Five top-ups of ₹20,000 for Vikram at the same moment; ₹50,000 is left today.
for i in 1 2 3 4 5; do cap "07-at-once-$i" -X POST "$B/wallets/1002/top-ups" -H "$J" -d '{"amountPaise": 2000000}' & done
wait
psql -c "SELECT id, owner, tier, balance_paise FROM wallets ORDER BY id" > wallets.txt
psql -c "SELECT wallet_id, amount_paise, to_char(created_at AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI') AS created_ist FROM top_ups ORDER BY id" > top-ups.txt
date '+%-d %b %Y' > date.txt
