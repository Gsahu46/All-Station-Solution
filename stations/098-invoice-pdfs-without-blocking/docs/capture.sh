#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/ (rendering at 130 ms a page, as configured).
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
job() { sed -n 's/^Location: //p' "$1.txt"; }
done_yet() { curl -s "$B$1" | grep -q '"done":true'; }
wait_done() { for _ in $(seq 1 100); do done_yet "$1" && return; sleep 0.2; done; return 1; }
cap 01-a-three-page-invoice -X POST "$B/invoices/INV-2026-0003/pdf-jobs"
J1=$(job 01-a-three-page-invoice); wait_done "$J1"
cap 02-done "$B$J1"
curl -s -D pdf-headers.txt -o invoice.pdf "$B$J1/pdf"
grep -iE "^(content-type|content-disposition|content-length):" pdf-headers.txt | tr -d '\r' > pdf-download.txt
pdfinfo invoice.pdf | grep -E "^(PDF version|Pages|Page size):" >> pdf-download.txt   # poppler's pdfinfo: an independent reader
rm -f invoice.pdf pdf-headers.txt
curl -s -o /dev/null -w 'answered %{http_code} in %{time_total} s\n' -X POST "$B/invoices/INV-2026-0300/pdf-jobs" > big-invoice-timing.txt
J2=$(curl -s -i -X POST "$B/invoices/INV-2026-0300/pdf-jobs" | tr -d '\r' | sed -n 's/^Location: //p')   # the same job, see case 4
sleep 2
cap 03-three-hundred-pages-two-seconds-later "$B$J2"
cap 04-the-same-invoice-again -X POST "$B/invoices/INV-2026-0300/pdf-jobs"
cap 05-its-pdf-before-it-is-ready "$B$J2/pdf"
cap 06-a-damaged-invoice -X POST "$B/invoices/INV-2026-0013/pdf-jobs"
J3=$(job 06-a-damaged-invoice); wait_done "$J3"
cap 07-the-failed-job "$B$J3"
cap 08-no-such-invoice -X POST "$B/invoices/INV-2026-0999/pdf-jobs"
cap 09-not-an-invoice-id -X POST "$B/invoices/hello/pdf-jobs"
cap 10-no-such-job "$B/pdf-jobs/00000000-0000-0000-0000-000000000000"
# Month end: 0300 is rendering; 21 more take the other worker and the 20 places in the queue. The next one is refused.
for n in $(seq 301 321); do curl -s -o /dev/null -X POST "$B/invoices/INV-2026-0$n/pdf-jobs"; done
cap 11-the-23rd-at-once -X POST "$B/invoices/INV-2026-0322/pdf-jobs"
date '+%-d %b %Y' > date.txt
