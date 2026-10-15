#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/reports/doctor-load
cap 01-the-demo-week "$U?from=2026-10-05&to=2026-10-11"
cap 02-at-least-two-appointments "$U?from=2026-10-05&to=2026-10-11&minAppointments=2"
cap 03-one-sunday "$U?from=2026-10-11&to=2026-10-11"
cap 04-a-quiet-week "$U?from=2026-01-05&to=2026-01-11"
cap 05-to-before-from "$U?from=2026-10-11&to=2026-10-05"
# The old report's SQL on the same data, through psql: no Dr Khan, and Dr Mehta at 4.
docker compose -f ../../compose.yaml exec -T postgres psql -U mediqo -d mediqo -c \
  "SELECT d.name, count(*) AS appointments FROM doctors d JOIN appointments a ON a.doctor_id = d.id LEFT JOIN follow_ups f ON f.appointment_id = a.id WHERE d.active AND a.starts_at >= TIMESTAMPTZ '2026-10-05 00:00 Asia/Kolkata' AND a.starts_at < TIMESTAMPTZ '2026-10-12 00:00 Asia/Kolkata' AND a.status <> 'CANCELLED' GROUP BY d.name ORDER BY appointments DESC" > old-report.txt
date '+%-d %b %Y' > date.txt
