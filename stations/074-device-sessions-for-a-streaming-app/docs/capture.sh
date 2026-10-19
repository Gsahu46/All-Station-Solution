#!/usr/bin/env bash
# Captures real request/response pairs and the stored rows into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
psql() { docker compose -f ../../compose.yaml exec -T postgres psql -U streamo -d streamo -v ON_ERROR_STOP=1 -q "$@"; }
field() { sed -n "s/.*\"$2\":\"\([^\"]*\)\".*/\1/p" "$1"; }
cap 01-login-on-a-phone -X POST "$B/auth/login" -H "$J" -d '{"email": "anika@example.com", "password": "anika-demo-pass", "deviceName": "Anika phone", "deviceType": "phone"}'
A1=$(field 01-login-on-a-phone.txt accessToken); R1=$(field 01-login-on-a-phone.txt refreshToken); PHONE=$(field 01-login-on-a-phone.txt deviceId)
cap 02-login-on-a-tv -X POST "$B/auth/login" -H "$J" -d '{"email": "anika@example.com", "password": "anika-demo-pass", "deviceName": "Living room TV", "deviceType": "tv"}'
ATV=$(field 02-login-on-a-tv.txt accessToken); RTV=$(field 02-login-on-a-tv.txt refreshToken); TV=$(field 02-login-on-a-tv.txt deviceId)
cap 03-refresh -X POST "$B/auth/refresh" -H "$J" -d "{\"refreshToken\": \"$R1\"}"
A2=$(field 03-refresh.txt accessToken); R2=$(field 03-refresh.txt refreshToken)
cap 04-the-device-list "$B/me/devices" -H "Authorization: Bearer $A2"
cap 05-the-tv-asks-for-the-list "$B/me/devices" -H "Authorization: Bearer $ATV"
cap 06-remove-the-tv -X DELETE "$B/me/devices/$TV" -H "Authorization: Bearer $A2"
cap 07-the-tv-right-after "$B/me/devices" -H "Authorization: Bearer $ATV"
AR=$(curl -s -X POST "$B/auth/login" -H "$J" -d '{"email": "rohan@example.com", "password": "rohan-demo-pass", "deviceName": "Rohan phone", "deviceType": "phone"}' | sed -n 's/.*"accessToken":"\([^"]*\)".*/\1/p')
cap 08-another-members-device -X DELETE "$B/me/devices/$PHONE" -H "Authorization: Bearer $AR"
cap 09-the-used-refresh-token-again -X POST "$B/auth/refresh" -H "$J" -d "{\"refreshToken\": \"$R1\"}"
cap 10-the-phone-after-reuse -X POST "$B/auth/refresh" -H "$J" -d "{\"refreshToken\": \"$R2\"}"
psql -c "SELECT m.email, d.device_name, d.device_type, d.revoked_reason FROM device_sessions d JOIN members m ON m.id = d.member_id ORDER BY d.created_at" > sessions.txt
psql -c "SELECT left(t.token_hash, 16) || '...' AS token_hash, d.device_name, t.expires_at - t.created_at AS valid_for, t.used_at IS NOT NULL AS used FROM refresh_tokens t JOIN device_sessions d ON d.id = t.session_id ORDER BY t.created_at, d.device_name" > tokens.txt
# Real tokens open an account: the page shows which token was sent, not the token itself.
for f in 0*.txt 10*.txt; do sed -i "s/$A1/<access token 1>/g; s/$R1/<refresh token 1>/g; s/$A2/<access token 2>/g; s/$R2/<refresh token 2>/g; s/$ATV/<TV access token>/g; s/$RTV/<TV refresh token>/g; s/$AR/<access token of rohan>/g" "$f"; done
date '+%-d %b %Y' > date.txt
