#!/usr/bin/env bash
# Captures real request/response pairs and the generated OpenAPI description from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
cap 01-a-parcel-bengaluru-to-delhi -X POST "$B/rate-quotes" -H "$J" -d '{"fromPincode": "560001", "toPincode": "110001", "weightGrams": 1200, "lengthCm": 30, "widthCm": 20, "heightCm": 10, "service": "STANDARD"}'
cap 02-light-but-bulky-express-in-bengaluru -X POST "$B/rate-quotes" -H "$J" -d '{"fromPincode": "560001", "toPincode": "560034", "weightGrams": 800, "lengthCm": 60, "widthCm": 40, "heightCm": 40, "service": "EXPRESS"}'
cap 03-too-heavy -X POST "$B/rate-quotes" -H "$J" -d '{"fromPincode": "560001", "toPincode": "110001", "weightGrams": 62000, "lengthCm": 80, "widthCm": 60, "heightCm": 60, "service": "STANDARD"}'
cap 04-a-pin-code-not-served -X POST "$B/rate-quotes" -H "$J" -d '{"fromPincode": "560001", "toPincode": "744101", "weightGrams": 500, "lengthCm": 10, "widthCm": 10, "heightCm": 10, "service": "STANDARD"}'
cap 05-a-five-digit-pin-code -X POST "$B/rate-quotes" -H "$J" -d '{"fromPincode": "56001", "toPincode": "110001", "weightGrams": 1200, "lengthCm": 30, "widthCm": 20, "heightCm": 10, "service": "STANDARD"}'
cap 06-the-old-pdfs-example -X POST "$B/rate-quotes" -H "$J" -d '{"origin": "560001", "destination": "110001", "weight_kg": 1.2, "dimensions": "30x20x10", "type": "surface"}'
curl -s "$B/v3/api-docs" > api-docs.json
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' "$B/v3/api-docs" > api-docs-status.txt
date '+%-d %b %Y' > date.txt
