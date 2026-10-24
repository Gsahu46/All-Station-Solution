#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/, against docs/test-insurer.py.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
python3 ../test-insurer.py 9088 & INSURER=$!
trap 'kill $INSURER 2>/dev/null || true' EXIT
sleep 1
control() { curl -s -o /dev/null -d "$1" http://127.0.0.1:9088/control; }
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J=(-H 'Content-Type: application/json')
control '{"save":"wire-issue"}'
cap 01-a-term-policy "${J[@]}" -d '{"customerName":"Meera Iyer","dateOfBirth":"1988-04-12","productCode":"TERM10","sumInsuredPaise":1000000000}' "$B/policies"
control '{"save":"wire-fault"}'
cap 02-a-product-the-insurer-does-not-sell "${J[@]}" -d '{"customerName":"Meera Iyer","dateOfBirth":"1988-04-12","productCode":"CAR1","sumInsuredPaise":1000000000}' "$B/policies"
control '{"save":null}'
cap 03-a-sum-above-the-limit "${J[@]}" -d '{"customerName":"Ravi Kumar","dateOfBirth":"1975-11-02","productCode":"HEALTH5","sumInsuredPaise":60000000000}' "$B/policies"
cap 04-a-date-of-birth-in-the-future "${J[@]}" -d '{"customerName":"Ravi Kumar","dateOfBirth":"2999-01-01","productCode":"HEALTH5","sumInsuredPaise":50000000}' "$B/policies"
control '{"broken":true}'
cap 05-the-insurers-system-fails "${J[@]}" -d '{"customerName":"Asha Rao","dateOfBirth":"1990-06-30","productCode":"HEALTH5","sumInsuredPaise":50000000}' "$B/policies"
control '{"broken":false,"delay":20}'
cap 06-the-insurer-hangs "${J[@]}" -d '{"customerName":"Asha Rao","dateOfBirth":"1990-06-30","productCode":"HEALTH5","sumInsuredPaise":50000000}' "$B/policies"
curl -s -o /dev/null -w 'the app answered %{http_code} after %{time_total} s (its limit: 8 s; the insurer would have taken 20 s)\n' "${J[@]}" \
  -d '{"customerName":"Asha Rao","dateOfBirth":"1990-06-30","productCode":"HEALTH5","sumInsuredPaise":50000000}' "$B/policies" > hang-timing.txt
control '{"delay":0}'
date '+%-d %b %Y' > date.txt
