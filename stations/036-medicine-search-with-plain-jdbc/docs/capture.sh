#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/medicines
cap 01-part-of-a-name "$U?name=para"
cap 02-an-apostrophe "$U?name=john%27s"
cap 03-an-injection-attempt "$U?name=x%27%20OR%201%3D1%20--"
cap 04-wildcards-are-just-characters "$U?name=%25%25"
cap 05-no-match "$U?name=aspirin"
cap 06-too-short "$U?name=p"
cap 07-no-name "$U"
date '+%-d %b %Y' > date.txt
