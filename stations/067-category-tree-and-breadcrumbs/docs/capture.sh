#!/usr/bin/env bash
# Captures real request/response pairs into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/categories
cap 01-android-breadcrumb "$B/4/breadcrumb"
cap 02-everything-under-fashion "$B/8/descendants"
cap 03-a-leaf "$B/5/descendants"
cap 04-no-such-category "$B/999/breadcrumb"
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U kartwala -d kartwala -v ON_ERROR_STOP=1 -q "$@"; }
# The move that made the old loop, tried on the real table.
psql -c "UPDATE categories SET parent_id = 3 WHERE id = 2" > loop-refused.txt 2>&1 || true
date '+%-d %b %Y' > date.txt
