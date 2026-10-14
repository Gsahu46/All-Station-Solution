#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
cap 01-borrow-on-the-web -X POST "$B/loans" -H "$J" -d '{"memberId":"m-1","bookId":"b-1"}'
cap 02-borrow-at-the-kiosk -X POST "$B/kiosk/checkouts" -H "$J" -d '{"cardNumber":"CL-0001","barcode":"LIB100002"}'
cap 03-a-members-loans "$B/members/m-1/loans"
cap 04-a-fourth-book-at-the-kiosk -X POST "$B/kiosk/checkouts" -H "$J" -d '{"cardNumber":"CL-0003","barcode":"LIB100003"}'
cap 05-a-loan-with-a-fine-unpaid -X POST "$B/loans" -H "$J" -d '{"memberId":"m-2","bookId":"b-3"}'
cap 06-a-book-already-out -X POST "$B/loans" -H "$J" -d '{"memberId":"m-1","bookId":"b-6"}'
cap 07-a-return -X POST "$B/loans/l-6/return"
cap 08-an-unknown-member "$B/members/m-9/loans"
date '+%-d %b %Y' > date.txt
