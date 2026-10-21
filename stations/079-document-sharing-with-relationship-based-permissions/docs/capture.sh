#!/usr/bin/env bash
# Captures real request/response pairs and the stored tuples into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U taskloom -d taskloom -v ON_ERROR_STOP=1 -q "$@"; }
psql -c "SELECT object_type || ':' || object_id AS object, relation, subject_type || ':' || subject_id || CASE WHEN subject_relation = '' THEN '' ELSE '#' || subject_relation END AS subject FROM relation_tuples ORDER BY object_type DESC, object_id, relation" > tuples.txt
cap 01-asha-opens-a-doc-in-the-team-folder -u asha:asha-demo-pass "$B/docs/d-guidelines"
cap 02-neha-through-a-team-in-a-team -u neha:neha-demo-pass "$B/docs/d-logo-brief"
cap 03-shared-with-asha -u asha:asha-demo-pass "$B/me/shared-with-me"
cap 04-kabir-before-any-share -u kabir:kabir-demo-pass "$B/docs/d-roadmap"
cap 05-meera-shares-the-roadmap-with-kabir -u meera:meera-demo-pass -X POST "$B/docs/d-roadmap/shares" -H "$J" -d '{"subject": "user:kabir", "relation": "viewer"}'
cap 06-kabir-after-the-share -u kabir:kabir-demo-pass "$B/docs/d-roadmap"
cap 07-a-viewer-tries-to-share -u asha:asha-demo-pass -X POST "$B/docs/d-guidelines/shares" -H "$J" -d '{"subject": "user:kabir", "relation": "viewer"}'
# The team admin removes asha from design (not an endpoint of this station): one tuple out.
psql -c "DELETE FROM relation_tuples WHERE object_type = 'team' AND object_id = 'design' AND subject_id = 'asha'"
cap 08-asha-after-leaving-the-team -u asha:asha-demo-pass "$B/docs/d-guidelines"
psql -c "SELECT doc_id, shared_to, relation, shared_by FROM share_notices" > notices.txt
date '+%-d %b %Y' > date.txt
