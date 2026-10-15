#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
cap 01-a-new-member -X POST "$B/members" -H "$J" -d '{"name":"Asha Verma","phone":"+91 98765-43210"}'
cap 02-the-same-phone-written-differently -X POST "$B/members" -H "$J" -d '{"name":"Asha V","phone":"098765 43210"}'
cap 03-not-a-mobile-number -X POST "$B/members" -H "$J" -d '{"name":"Ravi Iyer","phone":"12345"}'
cap 04-a-quarterly-membership -X POST "$B/members/1/memberships" -H "$J" -d '{"planCode":"quarterly","startsOn":"2026-11-15"}'
cap 05-an-overlapping-membership -X POST "$B/members/1/memberships" -H "$J" -d '{"planCode":"MONTHLY","startsOn":"2027-01-31"}'
cap 06-the-next-one-back-to-back -X POST "$B/members/1/memberships" -H "$J" -d '{"planCode":"MONTHLY","startsOn":"2027-02-15"}'
cap 07-a-plan-we-do-not-sell -X POST "$B/members/1/memberships" -H "$J" -d '{"planCode":"WEEKLY","startsOn":"2026-11-01"}'
cap 08-no-such-member -X POST "$B/members/99/memberships" -H "$J" -d '{"planCode":"MONTHLY","startsOn":"2026-11-01"}'
# The database the app migrated on startup: Flyway's history and every named constraint.
PSQL="docker compose -f ../../compose.yaml exec -T postgres psql -U fitnest -d fitnest -c"
$PSQL "SELECT version, description, success FROM flyway_schema_history ORDER BY installed_rank" > flyway-history.txt
$PSQL "SELECT conrelid::regclass AS on_table, conname AS constraint_name, CASE contype WHEN 'p' THEN 'primary key' WHEN 'f' THEN 'foreign key' WHEN 'u' THEN 'unique' WHEN 'c' THEN 'check' WHEN 'x' THEN 'exclude' END AS kind FROM pg_constraint WHERE conrelid IN ('members'::regclass, 'memberships'::regclass, 'plans'::regclass) ORDER BY 1::text, 2" > constraints.txt
date '+%-d %b %Y' > date.txt
