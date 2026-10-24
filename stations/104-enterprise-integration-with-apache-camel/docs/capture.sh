#!/usr/bin/env bash
# Captures real responses from the running app, its RabbitMQ and the simulated bank's SFTP server into docs/captures/.
# Run by tools/build_station.sh --capture (which starts compose.yaml and the app first). Run from the station folder.
# The app polls the bank's folder every 30 s, so this takes about two minutes.
set -euo pipefail
[ -z "$(ls data/runs 2>/dev/null)" ] || { echo "data/runs is not empty: stop the app, delete data/, start again" >&2; exit 1; }
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
DC=(docker compose -f ../../compose.yaml)
# As the bank does it: write NAME.part, then rename.
upload() { "${DC[@]}" exec -T sftp sh -c "cat > /home/koshbank/upload/$1.part && mv /home/koshbank/upload/$1.part /home/koshbank/upload/$1"; }
until_done() { for _ in $(seq 1 120); do curl -s "$B/integration/runs/$1" | grep -qE '"status":"(DONE|DUPLICATE|FAILED|DEAD_LETTERED)"' && return; sleep 0.5; done; echo "run $1 did not finish" >&2; return 1; }
H=reference,customer_name,date_of_birth,product_code,sum_insured_paise

printf '%s\n' $H "KB-1001,Meera Iyer,1988-04-12,TERM10,1000000000" "KB-1002,Ravi Kumar,1975-11-02,HEALTH5,50000000" \
  "KB-1003,Asha Rao,1990-06-30,HEALTH5,50000000" > KOSHBANK-20261022.csv
printf '%s\n' $H "KB-1101,Vikram Shah,1982-01-15,TERM10,2500000000" "KB-1102,Lata Menon,2999-01-01,HEALTH5,50000000" \
  "KB-1103,Kiran Das,1979-07-21,HEALTH5" "kb-1101,Vikram Shah,1982-01-15,TERM10,2500000000" > KOSHBANK-20261023.csv
printf '%s\n' "ref;name;dob;product;sum" "KB-1201;Neha Gupta;1991-03-03;TERM10;1000000000" > KOSHBANK-20261024.csv
for f in KOSHBANK-2026102{2,3,4}.csv; do upload $f < $f; done   # one poll picks up all three, in name order
until_done 3
cap 01-a-good-file "$B/integration/runs/1"
cap 02-a-file-with-bad-lines "$B/integration/runs/2"
cap 03-a-file-that-cannot-be-read "$B/integration/runs/3"
cmp -s KOSHBANK-20261024.csv ../../data/dead-letter/KOSHBANK-20261024.csv && echo "data/dead-letter/KOSHBANK-20261024.csv: the file as it arrived (identical bytes)" > dead-letter.txt

# The messages on the queue, read through the management API without taking them off.
curl -s -u guest:guest -H 'Content-Type: application/json' -d '{"count":10,"ackmode":"ack_requeue_true","encoding":"auto"}' \
  http://localhost:15672/api/queues/%2F/policy.requests/get | python3 -c '
import json, sys
ms = json.load(sys.stdin)
print(len(ms), "messages on policy.requests")
for m in ms:
    print(m["properties"]["message_id"], m["properties"]["delivery_mode"], m["payload"])' > queue.txt

# The bank's job runs twice: the same file again, same name.
sleep 1.1; upload KOSHBANK-20261022.csv < KOSHBANK-20261022.csv
until_done 4
cap 04-the-same-file-again "$B/integration/runs/4"

# The broker refuses messages for the queue (as when it is out of disk), then recovers.
"${DC[@]}" exec -T rabbitmq rabbitmqctl -q set_policy --apply-to queues refuse '^policy\.requests$' '{"max-length":0,"overflow":"reject-publish"}' > /dev/null
printf '%s\n' $H "KB-1301,Arjun Nair,1985-09-09,TERM10,1500000000" > KOSHBANK-20261025.csv
upload KOSHBANK-20261025.csv < KOSHBANK-20261025.csv
until_done 5
"${DC[@]}" exec -T rabbitmq rabbitmqctl -q clear_policy refuse > /dev/null
cap 05-the-broker-refuses "$B/integration/runs/5"
until_done 6
cap 06-the-next-poll-tries-again "$B/integration/runs/6"

cap 07-no-such-run "$B/integration/runs/99"
cap 08-not-a-run-number "$B/integration/runs/latest"

# What the app keeps on disk to remember what it already did.
{ echo "data/processed-files.dat (SHA-256 of each processed file's content):"; cat ../../data/processed-files.dat
  echo; echo "data/seen-files.dat (name-size-time of each downloaded file):"; cat ../../data/seen-files.dat; } > records.txt
rm -f KOSHBANK-*.csv
rm -rf ../../data
date '+%-d %b %Y' > date.txt
