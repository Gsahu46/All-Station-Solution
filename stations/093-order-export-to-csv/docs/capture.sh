#!/usr/bin/env bash
# Captures real request/response pairs from the running app and its PostgreSQL into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r' | sed 's/^\xEF\xBB\xBF//'; echo; } > "$name.txt"; }
B=http://localhost:8080
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U kartwala -d kartwala -v ON_ERROR_STOP=1 -q "$@"; }
cap 01-neha-exports-2026 -u neha.store:neha-demo-pass "$B/seller/orders/export?from=2026-01-01&to=2026-12-31"
cap 02-arun-exports-2026 -u arun.mart:arun-demo-pass "$B/seller/orders/export?from=2026-01-01&to=2026-12-31"
cap 03-one-indian-day -u neha.store:neha-demo-pass "$B/seller/orders/export?from=2026-06-30&to=2026-06-30"
cap 04-more-than-a-year -u neha.store:neha-demo-pass "$B/seller/orders/export?from=2025-01-01&to=2026-01-02"
cap 05-not-a-date -u neha.store:neha-demo-pass "$B/seller/orders/export?from=2026-01-01&to=2026-13-01"
cap 06-support-may-not-export -u sam.help:sam-demo-pass "$B/seller/orders/export?from=2026-01-01&to=2026-12-31"
cap 07-no-sign-in "$B/seller/orders/export?from=2026-01-01&to=2026-12-31"
curl -s -u neha.store:neha-demo-pass "$B/seller/orders/export?from=2026-01-01&to=2026-12-31" | head -c 3 | od -An -tx1 | tr -s ' ' > bom.txt
psql -c "SELECT seller_id, from_date, to_date FROM export_log ORDER BY id" > export-log.txt
date '+%-d %b %Y' > date.txt
