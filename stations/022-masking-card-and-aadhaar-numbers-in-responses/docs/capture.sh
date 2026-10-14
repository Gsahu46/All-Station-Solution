#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/customers
cap 01-own-profile -u asha:asha-demo-pass "$U/c-1001/profile"
cap 02-support-view -u neha:neha-demo-pass "$U/c-1002/profile"
cap 03-support-asks-for-full -u neha:neha-demo-pass "$U/c-1001/profile?full=true"
cap 04-someone-elses-profile -u asha:asha-demo-pass "$U/c-1002/profile"
cap 05-no-credentials "$U/c-1001/profile"
cap 06-marketing -u kiran:kiran-demo-pass "$U/c-1001/profile"
date '+%-d %b %Y' > date.txt
