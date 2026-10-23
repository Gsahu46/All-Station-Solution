#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
# The app uses real DNS here, and every address it could reach in this build is private: these are refusals.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080/link-previews
J="Content-Type: application/json"
M=meera:meera-demo-pass
cap 01-the-cloud-metadata-address -u "$M" -H "$J" -d '{"url": "http://169.254.169.254/latest/meta-data/iam/security-credentials/"}' "$B"
cap 02-the-app-itself-on-localhost -u "$M" -H "$J" -d '{"url": "http://localhost:8080/actuator"}' "$B"
cap 03-ipv6-loopback -u "$M" -H "$J" -d '{"url": "http://[::1]:8080/"}' "$B"
cap 04-a-private-network-address -u "$M" -H "$J" -d '{"url": "http://10.0.0.5/admin"}' "$B"
cap 05-a-file-link -u "$M" -H "$J" -d '{"url": "file:///etc/passwd"}' "$B"
cap 06-a-name-that-does-not-exist -u "$M" -H "$J" -d '{"url": "http://nosuch.invalid/"}' "$B"
cap 07-a-guest -u guest:guest-demo-pass -H "$J" -d '{"url": "http://169.254.169.254/"}' "$B"
cap 08-no-sign-in -H "$J" -d '{"url": "http://169.254.169.254/"}' "$B"
start=$(date +%s%N)
curl -s -o /dev/null -u "$M" -H "$J" -d '{"url": "http://169.254.169.254/latest/meta-data/"}' "$B"
echo "The metadata address was refused after $(( ($(date +%s%N) - start) / 1000000 / 100 * 100 )) ms (rounded down to 100 ms); the connect timeout is 2,000 ms." > refusal-time.txt
date '+%-d %b %Y' > date.txt
