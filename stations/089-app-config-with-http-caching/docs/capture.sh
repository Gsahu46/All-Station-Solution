#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
U="$B/app-config?platform=android&version=6.1.0"
cap 01-an-app-launch "$U"
ETAG=$(sed -n 's/^ETag: //p' 01-an-app-launch.txt)
cap 02-the-next-launch-sends-the-etag "$U" -H "If-None-Match: $ETAG"
cap 03-an-app-older-than-the-minimum "$B/app-config?platform=android&version=5.8.9"
cap 04-version-5-10-is-newer-than-5-9 "$B/app-config?platform=android&version=5.10.0"
cap 05-if-none-match-star "$U" -H "If-None-Match: *"
cap 06-an-unknown-platform "$B/app-config?platform=windows&version=6.1.0"
cap 07-a-version-without-patch "$B/app-config?platform=android&version=6.1"
full=$(curl -s -o /dev/null -w '%{size_download}' "$U")
again=$(curl -s -o /dev/null -w '%{size_download}' "$U" -H "If-None-Match: $ETAG")
echo "Body bytes: $full for a 200, $again for a 304. For 20 launches: $((20 * full)) without the ETag, $((full + 19 * again)) with it." > bytes.txt
date '+%-d %b %Y' > date.txt
