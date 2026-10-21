#!/usr/bin/env bash
# Captures real request/response pairs and the stored rows into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
# curl has no authenticator, so the passkey ceremonies themselves run in the tests (webauthn4j's emulator); here:
# the code sign-in, both option documents, and what is refused.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U tijori -d tijori -v ON_ERROR_STOP=1 -q "$@"; }
# The current code for the demo secret (RFC 6238's test secret), as an authenticator app would show it.
CODE=$(python3 -c 'import hmac,hashlib,struct,time; h=hmac.new(b"12345678901234567890",struct.pack(">Q",int(time.time())//30),hashlib.sha1).digest(); o=h[-1]&15; print("%06d"%((int.from_bytes(h[o:o+4],"big")&0x7fffffff)%1000000))')
cap 01-password-and-code -X POST "$B/2fa/totp" -H "$J" -d "{\"email\": \"zoya@example.com\", \"password\": \"zoya-demo-pass\", \"code\": \"$CODE\"}"
TOKEN=$(sed -n 's/.*"accessToken":"\([^"]*\)".*/\1/p' 01-password-and-code.txt)
cap 02-the-same-code-again -X POST "$B/2fa/totp" -H "$J" -d "{\"email\": \"zoya@example.com\", \"password\": \"zoya-demo-pass\", \"code\": \"$CODE\"}"
cap 03-the-account "$B/accounts/me" -H "Authorization: Bearer $TOKEN"
cap 04-registration-options -X POST "$B/webauthn/registration/options" -H "Authorization: Bearer $TOKEN"
cap 05-sign-in-options -X POST "$B/webauthn/authentication/options"
CH=$(sed -n 's/.*"challenge":"\([^"]*\)".*/\1/p' 05-sign-in-options.txt)
CD=$(printf '{"type":"webauthn.get","challenge":"%s","origin":"https://tijori-login.example"}' "$CH" | base64 -w0 | tr '/+' '_-' | tr -d '=')
cap 06-a-made-up-passkey-answer -X POST "$B/webauthn/authentication" -H "$J" -d "{\"id\": \"AAAAAAAAAAAAAAAAAAAAAA\", \"rawId\": \"AAAAAAAAAAAAAAAAAAAAAA\", \"type\": \"public-key\", \"response\": {\"clientDataJSON\": \"$CD\", \"authenticatorData\": \"AA\", \"signature\": \"AA\", \"userHandle\": \"AA\"}}"
cap 07-registration-without-a-token -X POST "$B/webauthn/registration/options"
psql -c "SELECT purpose, customer_id IS NOT NULL AS for_a_customer, expires_at - created_at AS valid_for, used_at IS NOT NULL AS used FROM webauthn_challenges ORDER BY created_at" > challenges.txt
psql -c "SELECT email, octet_length(user_handle) AS user_handle_bytes, totp_last_step IS NOT NULL AS a_code_was_used, balance_paise FROM customers ORDER BY id" > customers.txt
# A real token is a key to the account for 10 minutes: the page shows which one was sent, not the token.
for f in 0*.txt; do sed -i "s/$TOKEN/<access token>/g; s/$CODE/<current code>/g; s/$CD/<clientDataJSON naming tijori-login.example>/g" "$f"; done
date '+%-d %b %Y' > date.txt
