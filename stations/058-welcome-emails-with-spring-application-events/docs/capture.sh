#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first, logging to $APP_LOG).
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/signups
J="Content-Type: application/json"
cap 01-asha-signs-up -X POST "$B" -H "$J" -d '{"email":"asha@x.com","name":"Asha Verma"}'
sleep 1   # the welcome email is sent after the commit, on another thread
cap 02-a-moment-later "$B/1"
cap 03-ravi-with-a-full-invite -X POST "$B" -H "$J" -d '{"email":"ravi@x.com","name":"Ravi Menon","inviteCode":"OPS-FULL"}'
cap 04-meera-with-a-design-team-invite -X POST "$B" -H "$J" -d '{"email":"meera@x.com","name":"Meera Nair","inviteCode":"DESIGN-26"}'
cap 05-asha-again -X POST "$B" -H "$J" -d '{"email":"Asha@x.com","name":"Asha Verma"}'
cap 06-not-an-email -X POST "$B" -H "$J" -d '{"email":"asha.x.com","name":"Asha Verma"}'
cap 07-no-such-signup "$B/99"
sleep 1
# What the app did after each commit, from its own log: two welcome emails, none for Ravi's rolled-back sign-up.
grep -o "Welcome email for sign-up .*" "$APP_LOG" > app-log.txt
docker compose -f ../../compose.yaml exec -T postgres psql -U taskloom -d taskloom \
  -c "SELECT s.id, s.email, e.status, e.attempts FROM signups s LEFT JOIN sent_emails e ON e.signup_id = s.id ORDER BY s.id" > emails.txt
date '+%-d %b %Y' > date.txt
