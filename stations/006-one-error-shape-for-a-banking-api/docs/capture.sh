#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/beneficiaries
J="Content-Type: application/json"
cap 01-add -X POST "$U" -u asha:asha-demo-pass -H "$J" -d '{"name":"Ravi Menon","accountNumber":"50100123457890","ifsc":"HDFC0001234"}'
cap 02-invalid -X POST "$U" -u asha:asha-demo-pass -H "$J" -d '{"name":"<script>alert(1)</script>","accountNumber":"12AB","ifsc":"HDFC1234"}'
cap 03-unknown-ifsc -X POST "$U" -u asha:asha-demo-pass -H "$J" -d '{"name":"Ravi Menon","accountNumber":"50100123457891","ifsc":"ABCD0123456"}'
cap 04-duplicate -X POST "$U" -u asha:asha-demo-pass -H "$J" -d '{"name":"Ravi Menon","accountNumber":"50100123457890","ifsc":"HDFC0001234"}'
LOC=$(grep -i '^Location:' 01-add.txt | cut -d' ' -f2)
cap 05-other-customer "http://localhost:8080$LOC" -u ravi:ravi-demo-pass
cap 06-no-credentials "http://localhost:8080$LOC"
cap 07-viewer-adds -X POST "$U" -u meera:meera-demo-pass -H "$J" -d '{"name":"Ravi Menon","accountNumber":"50100123457892","ifsc":"HDFC0001234"}'
cap 08-sql-in-path "$U/1'%20OR%20'1'='1" -u asha:asha-demo-pass
date '+%-d %b %Y' > date.txt
