#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/posts
J="Content-Type: application/json"
cap 01-comment -X POST "$U/1/comments" -u ravi:ravi-demo-pass -H "$J" -d '{"text":"Amruttulya near FC Road, every time."}'
cap 02-attack -X POST "$U/1/comments" -u kabir:kabir-demo-pass -H "$J" -d '{"text":"<img src=x onerror=alert(document.cookie)>"}'
cap 03-html "$U/1/comments" -H "Accept: text/html"
cap 04-json "$U/1/comments"
cap 05-disguised-insult -X POST "$U/1/comments" -u ravi:ravi-demo-pass -H "$J" -d '{"text":"what an 1d10t"}'
cap 06-scampi -X POST "$U/1/comments" -u asha:asha-demo-pass -H "$J" -d '{"text":"Try the scampi at Mahesh Lunch Home"}'
cap 07-muted -X POST "$U/1/comments" -u tara:tara-demo-pass -H "$J" -d '{"text":"Let me in"}'
cap 08-private-post "$U/2/comments" -u asha:asha-demo-pass
date '+%-d %b %Y' > date.txt
