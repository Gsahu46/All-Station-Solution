#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/groups/1
J="Content-Type: application/json"
cap 01-equal -X POST "$U/expenses" -H "$J" -d '{"description":"Dinner","paidBy":"asha","amountPaise":100000,"splitType":"EQUAL","participants":["asha","ravi","meera"]}'
cap 02-shares -X POST "$U/expenses" -H "$J" -d '{"description":"Fuel","paidBy":"kabir","amountPaise":100000,"splitType":"SHARES","shares":{"kabir":2,"asha":1,"ravi":1}}'
cap 03-exact -X POST "$U/expenses" -H "$J" -d '{"description":"Hotel","paidBy":"ravi","amountPaise":1200000,"splitType":"EXACT","exactPaise":{"asha":500000,"ravi":400000,"meera":300000}}'
cap 04-exact-wrong-total -X POST "$U/expenses" -H "$J" -d '{"description":"Hotel","paidBy":"ravi","amountPaise":1200000,"splitType":"EXACT","exactPaise":{"asha":500000,"ravi":400000}}'
cap 05-settle-up "$U/settle-up"
date '+%-d %b %Y' > date.txt
