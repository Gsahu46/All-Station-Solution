#!/usr/bin/env bash
# Captures real request/response pairs from the running app and its RabbitMQ into docs/captures/.
# Run by tools/build_station.sh --capture (which starts RabbitMQ and the app first). Run from the station folder.
set -euo pipefail
rm -f data/reports/*   # report files from an earlier capture (the app made the folder when it started)
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
M=(-s -u guest:guest)
until_status() { for _ in $(seq 1 60); do curl -s "$B/lab-reports/$1" | grep -q "\"$2\"" && return; sleep 0.5; done; return 1; }
cap 01-render-a-report -X POST "$B/lab-reports/LR-0007/render"
until_status LR-0007 READY
cap 02-a-worker-rendered-it "$B/lab-reports/LR-0007"
curl -s -o report.pdf "$B/lab-reports/LR-0007/pdf"
pdfinfo report.pdf | grep -E "^(Pages|Page size|PDF version):" > pdf.txt   # poppler's pdfinfo: an independent reader
rm -f report.pdf
cap 03-asked-again -X POST "$B/lab-reports/LR-0007/render"
cap 04-a-busy-lab-system -X POST "$B/lab-reports/LR-0042/render"
until_status LR-0042 READY
cap 05-ready-after-a-retry "$B/lab-reports/LR-0042"
cap 06-a-damaged-scan -X POST "$B/lab-reports/LR-0013/render"
until_status LR-0013 FAILED
cap 07-failed-after-three-tries "$B/lab-reports/LR-0013"
# The parked message, read through the management API without taking it off the queue.
curl "${M[@]}" -H 'Content-Type: application/json' -d '{"count":1,"ackmode":"ack_requeue_true","encoding":"auto"}' \
  http://localhost:15672/api/queues/%2F/report-render.dlq/get | python3 -c '
import json, sys
m = json.load(sys.stdin)[0]
d = m["properties"]["headers"]["x-death"][0]
print("payload:", m["payload"])
print("x-death:", {k: d[k] for k in ("reason", "queue", "exchange", "count")})'  > dead-letter.txt
cap 08-no-such-report -X POST "$B/lab-reports/LR-0999/render"
cap 09-not-a-report-id -X POST "$B/lab-reports/report-7/render"
docker compose -f ../../compose.yaml exec -T rabbitmq rabbitmqctl -q list_queues name messages_ready messages_unacknowledged consumers > queues.txt
date '+%-d %b %Y' > date.txt
rm -rf ../../data   # the app's report files are not part of the station
