#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
U=http://localhost:8080/posts
cap 01-tree "$U/1/comment-tree"
cap 02-depth-2 "$U/1/comment-tree?maxDepth=2"
cap 03-deep-thread "$U/2/comment-tree?maxDepth=3"
cap 04-too-deep "$U/1/comment-tree?maxDepth=1000"
cap 05-unknown-post "$U/99/comment-tree"
date '+%-d %b %Y' > date.txt
