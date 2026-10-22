#!/usr/bin/env bash
# Captures real request/response pairs and the roster rows into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U mediqo -d mediqo -v ON_ERROR_STOP=1 -q "$@"; }
cap 01-dr-sharma-goes-off-call -X POST "$B/rosters/cardiology/off-call" -H "$J" -d '{"doctor": "dr.sharma"}'
cap 02-dr-iyer-asks-to-go-too -X POST "$B/rosters/cardiology/off-call" -H "$J" -d '{"doctor": "dr.iyer"}'
cap 03-dr-sharma-sends-it-again -X POST "$B/rosters/cardiology/off-call" -H "$J" -d '{"doctor": "dr.sharma"}'
cap 04-unknown-ward -X POST "$B/rosters/neurology/off-call" -H "$J" -d '{"doctor": "dr.sharma"}'
cap 05-a-name-that-is-not-a-doctor -X POST "$B/rosters/cardiology/off-call" -H "$J" -d '{"doctor": "Sharma"}'
# All three orthopaedics doctors ask at the same moment; the ward needs one.
for d in bose khan rao; do cap "06-at-once-dr-$d" -X POST "$B/rosters/orthopaedics/off-call" -H "$J" -d "{\"doctor\": \"dr.$d\"}" & done
wait
psql -c "SELECT ward, doctor, on_call FROM roster ORDER BY ward, doctor" > roster.txt
psql -c "SELECT ward, doctor, went FROM roster_changes ORDER BY id" > changes.txt
date '+%-d %b %Y' > date.txt
