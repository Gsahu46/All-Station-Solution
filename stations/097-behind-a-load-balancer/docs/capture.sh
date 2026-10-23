#!/usr/bin/env bash
# Captures real request/response pairs into docs/captures/. Run by tools/build_station.sh --capture, which starts the
# app on 8080 with its own configuration: there, the load balancer is 10.0.0.0/24, so localhost is just a client.
# For the balancer's side this script starts a second copy of the app on 8082 that trusts 127.0.0.1, and
# docs/test-balancer.py on 8081 in front of it. Run from the station folder.
set -euo pipefail
JAR=$(ls target/*.jar)
java -jar "$JAR" --server.port=8082 --server.tomcat.remoteip.internal-proxies=127.0.0.1/32 > /dev/null 2>&1 & APP2=$!
python3 docs/test-balancer.py 8081 8082 & LB=$!
trap 'kill $APP2 $LB 2>/dev/null || true' EXIT
for _ in $(seq 1 60); do curl -s -o /dev/null localhost:8082/whoami && break; sleep 1; done
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
# Requests to the balancer come from 127.0.0.2, a client; the balancer itself talks to the app from 127.0.0.1.
C=(--interface 127.0.0.2)
cap 01-straight-to-the-app "${C[@]}" http://127.0.0.1:8080/whoami
cap 02-straight-with-a-made-up-header "${C[@]}" -H 'X-Forwarded-For: 203.0.113.9' http://127.0.0.1:8080/whoami
cap 03-ops-pretends-to-be-in-the-office "${C[@]}" -u ops:ops-demo-pass -H 'X-Forwarded-For: 203.0.113.9' http://127.0.0.1:8080/admin/uploads
cap 04-through-the-balancer "${C[@]}" http://127.0.0.1:8081/whoami
cap 05-through-the-balancer-with-a-made-up-header "${C[@]}" -H 'X-Forwarded-For: 203.0.113.9' http://127.0.0.1:8081/whoami
cap 06-asha-uploads "${C[@]}" -u asha:asha-demo-pass -H 'Content-Type: application/octet-stream' --data-binary 'quarterly-report-v3' http://127.0.0.1:8081/uploads
cap 07-ops-from-outside-the-office "${C[@]}" -u ops:ops-demo-pass http://127.0.0.1:8081/admin/uploads
cap 08-no-sign-in "${C[@]}" -H 'Content-Type: application/octet-stream' --data-binary 'x' http://127.0.0.1:8081/uploads
cap 09-vikram-reads-ashas-upload "${C[@]}" -u vikram:vikram-demo-pass http://127.0.0.1:8081/uploads/1
# A stalled upload against the app's own configuration (20 s read timeout): 1,000 bytes announced, 10 sent.
python3 - > stalled-upload.txt <<'PY'
import base64, socket, time
s = socket.create_connection(("127.0.0.1", 8080))
auth = base64.b64encode(b"asha:asha-demo-pass").decode()
s.sendall(f"POST /uploads HTTP/1.1\r\nHost: localhost\r\nAuthorization: Basic {auth}\r\nContent-Type: application/octet-stream\r\nContent-Length: 1000\r\n\r\n0123456789".encode())
start = time.monotonic()
s.settimeout(60)
first = s.recv(4096).decode(errors="replace").split("\r\n")[0]
print(f"sent 10 of 1,000 bytes, then nothing; after {int(time.monotonic() - start)} s (rounded down) the app answered: {first}")
PY
date '+%-d %b %Y' > date.txt
