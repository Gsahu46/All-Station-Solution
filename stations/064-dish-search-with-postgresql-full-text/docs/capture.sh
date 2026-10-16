#!/usr/bin/env bash
# Captures real request/response pairs and real query plans into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/dishes/search
cap 01-paneer-tikka -G "$B" --data-urlencode "q=paneer tikka" -d city=pune
cap 02-dosas-in-capitals -G "$B" --data-urlencode "q=DOSAS" -d city=Pune
cap 03-exact-phrase-without-mysore -G "$B" --data-urlencode 'q="masala dosa" -mysore' -d city=pune
cap 04-a-typo -G "$B" --data-urlencode "q=panner" -d city=pune
cap 05-one-letter -G "$B" --data-urlencode "q=p" -d city=pune
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U tiffino -d tiffino -v ON_ERROR_STOP=1 -q "$@"; }
explain() { psql -c "SET max_parallel_workers_per_gather = 0" -c "EXPLAIN (ANALYZE, BUFFERS, COSTS OFF, TIMING OFF, SUMMARY OFF) $1"; }
explain "SELECT name FROM dishes WHERE city = 'pune' AND name LIKE '%Paneer%' ORDER BY id LIMIT 20" > explain-like.txt
explain "SELECT id, name FROM dishes, websearch_to_tsquery('english', 'paneer') AS query WHERE city = 'pune' AND search @@ query ORDER BY ts_rank(search, query) DESC, id LIMIT 20" > explain-full-text.txt
# What the English configuration does to words, asked directly.
psql -c "SELECT to_tsvector('english', 'Paneer Tikka Masala, two dosas') AS stored, websearch_to_tsquery('english', 'TIKKAS paneer') AS searched, websearch_to_tsquery('english', '\"masala dosa\" -mysore') AS syntax" > words.txt
date '+%-d %b %Y' > date.txt
