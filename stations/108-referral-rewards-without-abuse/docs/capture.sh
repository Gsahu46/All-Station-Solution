#!/usr/bin/env bash
# Captures real request/response pairs from the running app and its PostgreSQL into docs/captures/, against
# docs/test-wallet.py. Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first).
set -euo pipefail
cd docs/captures
rm -f wallet.txt
python3 ../test-wallet.py 9095 & WALLET=$!
trap 'kill $WALLET 2>/dev/null || true' EXIT
sleep 1
plan() { curl -s -o /dev/null -d "{\"plan\":$1}" http://127.0.0.1:9095/control; }
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary|www-authenticate):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J=(-H 'Content-Type: application/json')
SU=(-u signup:signup-demo-pass "${J[@]}")
OR=(-u orders:orders-demo-pass "${J[@]}")
until_delivery() { for _ in $(seq 1 60); do curl -s -u support:support-demo-pass "$B/rewards/$1" | grep -q "\"delivery\":\"$2\"" && return; sleep 0.5; done; echo "reward $1 never $2" >&2; return 1; }
cap 01-a-new-customer-signs-up "${SU[@]}" -d '{"referralCode":"RIYA100","name":"Neel Joshi","phone":"098765 43210","deviceId":"device-neel-7f3a"}' "$B/referrals"
NEEL=$(sed -n 's/.*"customerId":\([0-9]*\).*/\1/p' 01-a-new-customer-signs-up.txt)
cap 02-the-same-phone-with-a-new-sim "${SU[@]}" -d '{"referralCode":"RIYA100","name":"Neel J","phone":"9876500001","deviceId":"device-neel-7f3a"}' "$B/referrals"
cap 03-priyas-own-number "${SU[@]}" -d '{"referralCode":"RIYA100","name":"Priya N","phone":"+91 98123 45670","deviceId":"device-priya-02"}' "$B/referrals"
cap 04-a-number-that-has-an-account "${SU[@]}" -d '{"referralCode":"RIYA100","name":"Karan M","phone":"9898989898","deviceId":"device-karan-02"}' "$B/referrals"
cap 05-a-code-nobody-has "${SU[@]}" -d '{"referralCode":"FREE500","name":"Someone","phone":"9876500002","deviceId":"device-some-0001"}' "$B/referrals"
cap 06-the-first-order-is-placed "${OR[@]}" -d '{"customerId":'$NEEL',"totalPaise":65000,"status":"PLACED"}' "$B/orders/40001/referral-reward"
cap 07-a-delivered-order-below-500 "${OR[@]}" -d '{"customerId":'$NEEL',"totalPaise":45000,"status":"DELIVERED"}' "$B/orders/40002/referral-reward"
plan '[503]'
cap 08-a-delivered-order-of-650 "${OR[@]}" -d '{"customerId":'$NEEL',"totalPaise":65000,"status":"DELIVERED"}' "$B/orders/40003/referral-reward"
cap 09-the-same-event-again "${OR[@]}" -d '{"customerId":'$NEEL',"totalPaise":65000,"status":"DELIVERED"}' "$B/orders/40003/referral-reward"
until_delivery 1 SENT
cap 10-the-reward-after-a-retry -u support:support-demo-pass "$B/rewards/1"
# A second referral, and a wallet that refuses the credit.
# (Its id is read from the answer: refused sign-ups that reached the INSERT used up sequence numbers.)
MEHER=$(curl -s "${SU[@]}" -d '{"referralCode":"KARAN50","name":"Meher Ali","phone":"9876500003","deviceId":"device-meher-21c9"}' "$B/referrals" | sed -n 's/.*"customerId":\([0-9]*\).*/\1/p')
plan '[400]'
curl -s -o /dev/null "${OR[@]}" -d '{"customerId":'$MEHER',"totalPaise":120000,"status":"DELIVERED"}' "$B/orders/40004/referral-reward"
until_delivery 2 DEAD
cap 11-a-credit-the-wallet-refused -u support:support-demo-pass "$B/rewards/2"
docker compose -f ../../compose.yaml exec -T postgres psql -U basketo -d basketo \
  -c "INSERT INTO referrals (referrer_id, referee_id, device_id, status) VALUES (2, 1, 'device-neel-7f3a', 'PENDING')" > db-guard.txt 2>&1 || true
date '+%-d %b %Y' > date.txt
