#!/usr/bin/env bash
# Captures real request/response pairs into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first; no database here). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
cap 01-login -X POST "$B/auth/login" -H "$J" -d '{"username": "asha", "password": "asha-demo-pass"}'
TOKEN=$(sed -n 's/.*"accessToken":"\([^"]*\)".*/\1/p' 01-login.txt)
cap 02-my-workouts "$B/workouts/me" -H "Authorization: Bearer $TOKEN"
cap 03-no-token "$B/workouts/me"
# The payload with "asha" swapped for "ravi", signature kept: what the old base64-only check would have accepted.
H=${TOKEN%%.*}; SIG=${TOKEN##*.}
P=$(printf '%s' "$TOKEN" | cut -d. -f2 | tr '_-' '/+'); while [ $(( ${#P} % 4 )) -ne 0 ]; do P="$P="; done
P2=$(printf '%s' "$P" | base64 -d | sed 's/"sub":"asha"/"sub":"ravi"/' | base64 -w0 | tr '/+' '_-' | tr -d '=')
cap 04-payload-changed-to-ravi "$B/workouts/me" -H "Authorization: Bearer $H.$P2.$SIG"
printf '%s' "$P" | base64 -d > payload.txt; echo >> payload.txt
cap 05-wrong-password -X POST "$B/auth/login" -H "$J" -d '{"username": "asha", "password": "guess"}'
NEWBIE=$(curl -s -X POST "$B/auth/login" -H "$J" -d '{"username": "newbie", "password": "newbie-demo-pass"}' | sed -n 's/.*"accessToken":"\([^"]*\)".*/\1/p')
cap 06-signed-in-without-the-scope "$B/workouts/me" -H "Authorization: Bearer $NEWBIE"
# A real token is a key to an account for 15 minutes: the page shows its shape, not the token.
for f in 0*.txt; do sed -i "s/$TOKEN/<header>.<payload>.<signature>/g; s/$H\.$P2\.$SIG/<header>.<payload with sub=ravi>.<signature of asha>/g; s/$NEWBIE/<token of newbie>/g" "$f"; done
date '+%-d %b %Y' > date.txt
