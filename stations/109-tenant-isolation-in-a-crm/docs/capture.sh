#!/usr/bin/env bash
# Captures real request/response pairs from the running app and its PostgreSQL into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary|www-authenticate):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J=(-H 'Content-Type: application/json')
A=(-u ananya:ananya-demo-pass)
F=(-u farhan:farhan-demo-pass)
cap 01-zestfuls-leads "${A[@]}" "$B/leads"
cap 02-brightpaths-leads "${F[@]}" "$B/leads"
cap 03-a-new-lead "${A[@]}" "${J[@]}" -d '{"name":"Divya Kapoor","email":"Divya@MasalaBox.example","company":"Masala Box"}' "$B/leads"
cap 04-the-same-email-again "${A[@]}" "${J[@]}" -d '{"name":"Divya K","email":"divya@masalabox.example"}' "$B/leads"
cap 05-the-same-email-at-another-company "${F[@]}" "${J[@]}" -d '{"name":"Divya Kapoor","email":"divya@masalabox.example"}' "$B/leads"
cap 06-a-tenant-in-the-body "${A[@]}" "${J[@]}" -d '{"tenantId":"brightpath","name":"Planted Lead","email":"planted@example.com"}' "$B/leads"
cap 07-a-tenant-in-the-query "${A[@]}" "$B/leads?q=rahul&tenant=brightpath"
cap 08-another-companys-lead-by-id "${A[@]}" "$B/leads/3"
cap 09-a-viewer-tries-to-create -u kabir:kabir-demo-pass "${J[@]}" -d '{"name":"X","email":"x@example.com"}' "$B/leads"
cap 10-no-sign-in "$B/leads"
cap 11-a-percent-sign-is-text "${A[@]}" "$B/leads?q=%25"
cap 12-a-bad-email "${A[@]}" "${J[@]}" -d '{"name":"X","email":"not-an-email"}' "$B/leads"
# The policy itself, in psql, as the application's role: no WHERE in these queries.
docker compose -f ../../compose.yaml exec -T postgres psql -U crm -d crm -q <<'SQL' > policy.txt 2>&1 || true
\echo '-- as crm_app, no tenant set:'
BEGIN; SET LOCAL ROLE crm_app; SELECT count(*) AS leads_visible FROM leads; COMMIT;
\echo '-- as crm_app, tenant zestful:'
BEGIN; SET LOCAL ROLE crm_app; SELECT set_config('app.tenant', 'zestful', true) AS tenant; SELECT name, email FROM leads ORDER BY id; COMMIT;
\echo '-- as crm_app, tenant zestful, writing a row for brightpath:'
BEGIN; SET LOCAL ROLE crm_app; SELECT set_config('app.tenant', 'zestful', true) AS tenant;
INSERT INTO leads (tenant_id, name, email, owner) VALUES ('brightpath', 'X', 'x@example.com', 'ananya');
ROLLBACK;
SQL
date '+%-d %b %Y' > date.txt
