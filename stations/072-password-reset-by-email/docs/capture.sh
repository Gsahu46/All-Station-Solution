#!/usr/bin/env bash
# Captures real request/response pairs and the stored rows into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U hireloop -d hireloop -v ON_ERROR_STOP=1 -q "$@"; }
cap 01-reset-for-a-known-email -X POST "$B/password-resets" -H "$J" -d '{"email": "priya@example.com"}'
cap 02-reset-for-an-unknown-email -X POST "$B/password-resets" -H "$J" -d '{"email": "nobody@example.com"}'
TOKEN=$(psql -At -c "SELECT substring(body from 'token=([A-Za-z0-9_-]+)') FROM outbox_emails WHERE to_email = 'priya@example.com' ORDER BY id DESC LIMIT 1")
psql -c "SELECT to_email, subject, regexp_replace(body, 'token=[A-Za-z0-9_-]+', 'token=<43 random characters>') AS body FROM outbox_emails ORDER BY id" > outbox.txt
psql -c "SELECT token_hash, expires_at - created_at AS valid_for, used_at IS NOT NULL AS used FROM password_resets" > resets-before.txt
cap 03-choose-a-new-password -X POST "$B/password-resets/$TOKEN/complete" -H "$J" -d '{"newPassword": "priya-new-long-password"}'
cap 04-the-same-link-again -X POST "$B/password-resets/$TOKEN/complete" -H "$J" -d '{"newPassword": "someone-elses-password"}'
cap 05-signed-in-with-the-new-password -u 'priya@example.com:priya-new-long-password' "$B/candidates/me"
cap 06-a-suspended-account -u 'kiran@example.com:kiran-old-password' "$B/candidates/me"
psql -c "SELECT token_hash, used_at IS NOT NULL AS used FROM password_resets" > resets-after.txt
# Every capture shows the token only as "<43 random characters>": a real link is a key to an account.
sed -i "s/$TOKEN/<token from the email>/g" 03-choose-a-new-password.txt 04-the-same-link-again.txt
date '+%-d %b %Y' > date.txt
