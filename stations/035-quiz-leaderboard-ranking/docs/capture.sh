#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/quizzes
cap 01-the-top-ten "$B/3/leaderboard"
cap 02-the-top-three "$B/3/leaderboard?top=3"
cap 03-my-place "$B/3/leaderboard/me" -H "X-Student-Id: S-1011"
cap 04-the-top-five-of-two-thousand "$B/7/leaderboard?top=5"
cap 05-a-student-who-did-not-attempt "$B/3/leaderboard/me" -H "X-Student-Id: S-9999"
cap 06-top-zero "$B/3/leaderboard?top=0"
cap 07-no-such-quiz "$B/99/leaderboard"
date '+%-d %b %Y' > date.txt
