#!/usr/bin/env bash
# Captures real request/response pairs from the running app and its PostgreSQL into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary|www-authenticate):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
I=(-u imran:imran-demo-pass)
PSQL=(docker compose -f ../../compose.yaml exec -T postgres psql -U chaupal -d chaupal -q)
# Where Imran's number appears: every text column of every table, searched.
scan() { "${PSQL[@]}" -t -A <<'SQL'
SELECT format('SELECT %L || '': '' || count(*) FROM %I WHERE %I::text ILIKE %L HAVING count(*) > 0', table_name || '.' || column_name, table_name, column_name, '%9811122233%')
FROM information_schema.columns WHERE table_schema = 'public' AND table_name <> 'flyway_schema_history'
  AND data_type IN ('text', 'character varying', 'jsonb') ORDER BY table_name, column_name \gexec
SQL
}
{ echo "Rows holding 9811122233, by table and column, before:"; scan; } > scan-before.txt
cap 01-imran-asks-for-his-data "${I[@]}" -X POST "$B/me/data-export"
for _ in $(seq 1 30); do curl -s "${I[@]}" "$B/me/data-exports/1" | grep -q READY && break; sleep 0.5; done
cap 02-the-export-is-ready "${I[@]}" "$B/me/data-exports/1"
cap 03-the-file "${I[@]}" "$B/me/data-exports/1/file"
cap 04-zoya-tries-imrans-export -u zoya:zoya-demo-pass "$B/me/data-exports/1"
cap 05-a-support-account-has-no-me -u support:support-demo-pass -X DELETE "$B/me"
cap 06-imran-deletes-his-account "${I[@]}" -X DELETE "$B/me"
cap 07-and-can-no-longer-sign-in "${I[@]}" "$B/me/data-exports/1"
for _ in $(seq 1 30); do "${PSQL[@]}" -t -A -c "SELECT completed_at IS NOT NULL FROM erasures WHERE user_id = 1" | grep -q t && break; sleep 0.5; done
{ echo "Rows holding 9811122233, by table and column, after:"; scan; } > scan-after.txt
"${PSQL[@]}" -c "SELECT id, login, name, phone, email, status FROM users WHERE id = 1" -c "SELECT user_id, requested_at::date, due_by::date, completed_at IS NOT NULL AS done FROM erasures" > after.txt
date '+%-d %b %Y' > date.txt
