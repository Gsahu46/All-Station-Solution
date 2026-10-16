#!/usr/bin/env bash
# Captures real request/response pairs and real query plans into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/feed
cap 01-the-newest-three "$B?limit=3"
NEXT=$(curl -s "$B?limit=3" | python3 -c 'import json,sys; print(json.load(sys.stdin)["nextCursor"])')
cap 02-the-next-three "$B?limit=3&cursor=$NEXT"
python3 -c 'import base64,sys; s=sys.argv[1]; print(base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)).decode())' "$NEXT" > cursor-decoded.txt
cap 03-a-cursor-that-is-not-ours "$B?cursor=bm90LW91cnM"
cap 04-a-limit-of-500 "$B?limit=500"
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U chaupal -d chaupal -v ON_ERROR_STOP=1 -q "$@"; }
explain() { psql -c "SET max_parallel_workers_per_gather = 0" -c "EXPLAIN (ANALYZE, BUFFERS, COSTS OFF, TIMING OFF, SUMMARY OFF) $1"; }
# Page 2,001 of 20 both ways: by OFFSET, and by seeking past post 60,001 (the last post of page 2,000).
explain "SELECT id FROM posts ORDER BY created_at DESC, id DESC LIMIT 20 OFFSET 40000" > explain-offset.txt
explain "SELECT id FROM posts WHERE (created_at, id) < ((SELECT created_at FROM posts WHERE id = 60001), 60001) ORDER BY created_at DESC, id DESC LIMIT 20" > explain-keyset.txt
date '+%-d %b %Y' > date.txt
