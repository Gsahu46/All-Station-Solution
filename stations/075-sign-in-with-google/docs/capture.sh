#!/usr/bin/env bash
# Captures real request/response pairs into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). The app is configured for the real Google,
# but these captures need no network: they stop at the redirect, or are refused before Google would be asked.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
cap 01-start-sign-in "$B/oauth2/authorization/google"
cap 02-me-without-signing-in "$B/me"
cap 03-an-unknown-provider "$B/oauth2/authorization/github"
cap 04-a-callback-this-browser-never-started "$B/login/oauth2/code/google?code=4/0Afake&state=made-up"
cap 05-sign-out-without-the-csrf-token -X POST "$B/logout"
# The session cookie of capture 1 is a sign-in in progress: shown by its shape only.
sed -i -E 's/JSESSIONID=[0-9A-F]+/JSESSIONID=<session id>/' 0*.txt
date '+%-d %b %Y' > date.txt
