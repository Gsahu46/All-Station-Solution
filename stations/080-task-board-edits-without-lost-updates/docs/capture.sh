#!/usr/bin/env bash
# Captures real request/response pairs and the stored rows into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U taskloom -d taskloom -v ON_ERROR_STOP=1 -q "$@"; }
cap 01-both-managers-read-the-card "$B/tasks/1"
cap 02-meera-saves-first -X PUT "$B/tasks/1" -H "$J" -H 'If-Match: "0"' -d '{"title": "Write the press release", "description": "One page, two quotes.", "status": "doing", "assignee": "asha"}'
cap 03-kabir-saves-his-old-copy -X PUT "$B/tasks/1" -H "$J" -H 'If-Match: "0"' -d '{"title": "Write the press release", "description": "One page, two quotes.", "status": "open", "assignee": "ravi"}'
cap 04-kabir-reads-again "$B/tasks/1"
cap 05-kabir-saves-on-top -X PUT "$B/tasks/1" -H "$J" -H 'If-Match: "1"' -d '{"title": "Write the press release", "description": "One page, two quotes.", "status": "doing", "assignee": "ravi"}'
cap 06-no-if-match -X PUT "$B/tasks/1" -H "$J" -d '{"title": "Write the press release", "description": "One page, two quotes.", "status": "done", "assignee": "ravi"}'
cap 07-a-title-already-on-the-board -X PUT "$B/tasks/1" -H "$J" -H 'If-Match: "2"' -d '{"title": "Book the venue", "description": "One page, two quotes.", "status": "doing", "assignee": "ravi"}'
cap 08-the-board-polls-unchanged "$B/tasks/1" -H 'If-None-Match: "2"'
cap 09-no-such-task "$B/tasks/99"
psql -c "SELECT task_id, version, title, status FROM task_changes ORDER BY id" > changes.txt
date '+%-d %b %Y' > date.txt
