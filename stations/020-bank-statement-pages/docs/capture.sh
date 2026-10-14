#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/accounts
cap 01-first-page "$U/acc-1001/transactions?size=3"
cap 02-next-page "$U/acc-1001/transactions?page=1&size=3"
cap 03-past-the-end "$U/acc-1001/transactions?page=40&size=100"
cap 04-size-too-large "$U/acc-1001/transactions?size=1000000"
cap 05-page-too-deep "$U/acc-1001/transactions?page=200000000&size=20"
cap 06-empty-account "$U/acc-1002/transactions"
cap 07-unknown-account "$U/acc-9999/transactions"
date '+%-d %b %Y' > date.txt
