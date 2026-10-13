#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/loan-quotes
J="Content-Type: application/json"
cap 01-personal-quote -X POST "$U" -H "$J" -d '{"product":"PERSONAL","principalPaise":50000000,"tenureMonths":24}'
cap 02-schedule "http://localhost:8080$(grep -i '^location:' 01-personal-quote.txt | cut -d' ' -f2)"
cap 03-home-quote -X POST "$U" -H "$J" -d '{"product":"HOME","principalPaise":500000000,"tenureMonths":240}'
cap 04-small-long-loan -X POST "$U" -H "$J" -d '{"product":"PERSONAL","principalPaise":1000000,"tenureMonths":360}'
cap 05-gold-no-rate-yet -X POST "$U" -H "$J" -d '{"product":"GOLD","principalPaise":10000000,"tenureMonths":12}'
cap 06-tenure-too-short -X POST "$U" -H "$J" -d '{"product":"PERSONAL","principalPaise":50000000,"tenureMonths":3}'
date '+%-d %b %Y' > date.txt
