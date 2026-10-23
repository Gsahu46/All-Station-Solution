#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r' | sed '/^HTTP\/1.1 100 $/,/^$/d'; echo; } > "$name.txt"; }
B=http://localhost:8080
ASHA=asha:asha-demo-pass
F=$(mktemp -d)
printf '%%PDF-1.7\n%%demo PAN card\n' > "$F/pan-card.pdf"
printf 'MZ\x90\x00this program cannot be run in DOS mode' > "$F/pan.pdf"
{ printf '%%PDF-1.7\n'; head -c 6291456 /dev/zero; } > "$F/big.pdf"
: > "$F/empty.pdf"
cd "$F"   # so the file names in the commands are short; answers are written back to docs/captures
OUT=$OLDPWD
cap "$OUT/01-asha-uploads-her-pan-card" -u "$ASHA" -F type=PAN -F 'file=@pan-card.pdf;type=application/pdf' "$B/kyc/1/documents"
cap "$OUT/02-a-program-sent-as-a-pdf" -u "$ASHA" -F type=PAN -F 'file=@pan.pdf;type=application/pdf' "$B/kyc/1/documents"
cap "$OUT/03-a-name-that-climbs-out-of-the-folder" -u "$ASHA" -F type=PAN -F 'file=@pan-card.pdf;filename=../../etc/passwd;type=application/pdf' "$B/kyc/1/documents"
cap "$OUT/04-six-megabytes" -u "$ASHA" -F type=PAN -F 'file=@big.pdf;type=application/pdf' "$B/kyc/1/documents"
cap "$OUT/05-an-empty-file" -u "$ASHA" -F type=PAN -F 'file=@empty.pdf;type=application/pdf' "$B/kyc/1/documents"
cap "$OUT/06-asha-lists-her-documents" -u "$ASHA" "$B/kyc/1/documents"
cap "$OUT/07-rohan-lists-ashas-documents" -u rohan:rohan-demo-pass "$B/kyc/1/documents"
cap "$OUT/08-no-sign-in" "$B/kyc/1/documents"
cd "$OUT"
rm -r "$F"
date '+%-d %b %Y' > date.txt
