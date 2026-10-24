#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/, against docs/test-model.py.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
rm -f sent-*.json
python3 ../test-model.py 9077 & MODEL=$!
trap 'kill $MODEL 2>/dev/null || true' EXIT
sleep 1
control() { curl -s -o /dev/null -d "$1" http://127.0.0.1:9077/control; }
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary|www-authenticate):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
cap 01-a-billing-agent-asks-for-a-summary -X POST -u priya:priya-demo-pass "$B/tickets/T-1001/summary"
cap 02-another-agent-asks-again -X POST -u arjun:arjun-demo-pass "$B/tickets/T-1001/summary"
cap 03-a-ticket-with-instructions-in-it -X POST -u priya:priya-demo-pass "$B/tickets/T-1003/summary"
cap 04-a-400-message-thread -X POST -u priya:priya-demo-pass "$B/tickets/T-1004/summary"
cap 05-another-teams-ticket -X POST -u meena:meena-demo-pass "$B/tickets/T-1001/summary"
cap 06-a-customer-asks -X POST -u rahul:rahul-demo-pass "$B/tickets/T-1001/summary"
cap 07-no-sign-in -X POST "$B/tickets/T-1001/summary"
cap 08-no-such-ticket -X POST -u priya:priya-demo-pass "$B/tickets/T-9999/summary"
cap 09-not-a-ticket-id -X POST -u priya:priya-demo-pass "$B/tickets/1001/summary"
control '{"status":529}'
cap 10-the-provider-is-overloaded -X POST -u meena:meena-demo-pass "$B/tickets/T-1002/summary"
control '{"status":200,"delay":30}'
cap 11-the-provider-hangs -X POST -u meena:meena-demo-pass "$B/tickets/T-1002/summary"
curl -s -o /dev/null -w 'the app answered %{http_code} after %{time_total} s (its limit: 20 s; the model would have taken 30 s)\n' \
  -X POST -u meena:meena-demo-pass "$B/tickets/T-1002/summary" > hang-timing.txt
control '{"delay":0}'
# What left Taskloom for T-1001 and T-1003, as the provider received it.
for t in T-1001 T-1003; do python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
b = d["body"]
print("headers:", json.dumps(d["headers"]))
print("model:", b["model"], " max_tokens:", b["max_tokens"])
print("\n--- system ---\n" + b["system"])
print("\n--- messages[0].content (role user) ---\n" + b["messages"][0]["content"])' sent-$t.json > sent-$t.txt; done
python3 -c '
import json
c = json.load(open("sent-T-1004.json"))["body"]["messages"][0]["content"]
print(len(c), "characters sent for T-1004 (the thread has 400 messages)")
print(c[:400] + "\n...\n" + c[-300:])' > sent-T-1004.txt
rm -f sent-*.json
date '+%-d %b %Y' > date.txt
