#!/usr/bin/env bash
# Captures real request/response pairs and the stored hashes into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/candidates
J="Content-Type: application/json"
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U hireloop -d hireloop -v ON_ERROR_STOP=1 -q "$@"; }
psql -c "SELECT email, password_hash FROM candidates ORDER BY id" > hashes-before.txt
cap 01-sign-up -X POST "$B/signup" -H "$J" -d '{"email": "Nisha@Example.com", "fullName": "Nisha Rao", "password": "correct-horse-battery"}'
cap 02-my-profile -u 'nisha@example.com:correct-horse-battery' "$B/me"
cap 03-a-wrong-password -u 'nisha@example.com:wrong-password-here' "$B/me"
cap 04-an-email-with-no-account -u 'nobody@example.com:wrong-password-here' "$B/me"
cap 05-the-same-email-again -X POST "$B/signup" -H "$J" -d '{"email": "nisha@example.com", "fullName": "Someone Else", "password": "another-long-password"}'
cap 06-a-legacy-account-signs-in -u 'priya@example.com:summer2024!' "$B/me"
cap 07-a-browser-on-another-site -X OPTIONS "$B/signup" -H "Origin: https://evil.example" -H "Access-Control-Request-Method: POST"
psql -c "SELECT email, password_hash FROM candidates ORDER BY id" > hashes-after.txt
date '+%-d %b %Y' > date.txt
