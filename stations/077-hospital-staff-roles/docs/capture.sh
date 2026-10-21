#!/usr/bin/env bash
# Captures real request/response pairs into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first; no database here). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
cap 01-a-doctor-reads-her-patients-notes -u dr.sharma:sharma-demo-pass "$B/patients/P-1001/notes"
cap 02-reception-tries-the-same -u reception.anu:anu-demo-pass "$B/patients/P-1001/notes"
cap 03-reception-sees-todays-list -u reception.anu:anu-demo-pass "$B/appointments/today"
cap 04-a-nurse-sees-the-reasons-too -u nurse.ritu:ritu-demo-pass "$B/appointments/today"
cap 05-a-nurse-on-another-ward -u nurse.joseph:joseph-demo-pass "$B/patients/P-1001/notes"
cap 06-a-doctor-prescribes -u dr.bose:bose-demo-pass -X POST "$B/patients/P-2001/prescriptions" -H "$J" -d '{"drug": "Paracetamol", "doseMg": 500, "timesPerDay": 3, "days": 5}'
cap 07-a-nurse-tries-to-prescribe -u nurse.joseph:joseph-demo-pass -X POST "$B/patients/P-2001/prescriptions" -H "$J" -d '{"drug": "Paracetamol", "doseMg": 500, "timesPerDay": 3, "days": 5}'
cap 08-another-doctors-patient -u dr.bose:bose-demo-pass "$B/patients/P-1001/notes"
cap 09-no-credentials "$B/patients/P-1001/notes"
date '+%-d %b %Y' > date.txt
