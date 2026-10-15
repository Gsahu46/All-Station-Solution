#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
cap 01-an-order -X POST "$B/orders" -H "$J" -d '{"outletId":"TF-07","totalPaise":45000}'
N=$(grep -o '"orderNumber":"[^"]*"' 01-an-order.txt | cut -d'"' -f4)
cap 02-the-next-order -X POST "$B/orders" -H "$J" -d '{"outletId":"TF-02","totalPaise":18900}'
cap 03-looked-up-as-written "$B/orders/by-number/$N"
# As a customer reads it out: lower case, spaces instead of dashes (URL-encoded as %20).
SPOKEN=$(echo "$N" | tr 'A-Z-' 'a-z ' | sed 's/ /%20/g')
cap 04-looked-up-as-spoken "$B/orders/by-number/$SPOKEN"
# One digit misheard: the 6th character, changed by one.
D=${N:5:1}; W=$(( (D + 1) % 10 ))
cap 05-one-digit-misheard "$B/orders/by-number/${N:0:5}$W${N:6}"
cap 06-a-valid-number-nobody-has "$B/orders/by-number/TF-9999999-7"
cap 07-not-an-order-number "$B/orders/by-number/12345"
date '+%-d %b %Y' > date.txt
