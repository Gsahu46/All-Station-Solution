#!/usr/bin/env bash
# Captures real MCP and REST exchanges from the running app into docs/captures/, with curl speaking MCP's
# Streamable HTTP by hand (what an agent's MCP client does). Run by tools/build_station.sh --capture. Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
# curl's exit code is ignored: the server ends each event stream without the final chunk (curl exit 18).
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; { curl -s -i "$@" || true; } | grep -viE "^(date|keep-alive|connection|transfer-encoding|x-content-type-options|x-xss-protection|cache-control|pragma|expires|x-frame-options|vary):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
MCP=(-H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream')
INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"1"}}}'
# A session for a token: initialize, then the "initialized" notification. Prints the session id.
session() { local sid; sid=$(curl -s -D - -o /dev/null "${MCP[@]}" -H "Authorization: Bearer $1" -d "$INIT" $B/mcp | tr -d '\r' | awk -F': ' 'tolower($1)=="mcp-session-id"{print $2}')
  curl -s -o /dev/null "${MCP[@]}" -H "Authorization: Bearer $1" -H "Mcp-Session-Id: $sid" -H 'MCP-Protocol-Version: 2025-06-18' -d '{"jsonrpc":"2.0","method":"notifications/initialized"}' $B/mcp
  echo "$sid"; }
cap 01-an-agent-connects "${MCP[@]}" -H 'Authorization: Bearer demo-kirana-reader' -d "$INIT" "$B/mcp"
R=$(session demo-kirana-reader)
W=$(session demo-kirana-writer)
RH=(-H 'Authorization: Bearer demo-kirana-reader' -H "Mcp-Session-Id: $R" -H 'MCP-Protocol-Version: 2025-06-18')
WH=(-H 'Authorization: Bearer demo-kirana-writer' -H "Mcp-Session-Id: $W" -H 'MCP-Protocol-Version: 2025-06-18')
cap 02-the-tools-it-is-offered "${MCP[@]}" "${RH[@]}" -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' "$B/mcp"
cap 03-search-tasks "${MCP[@]}" "${RH[@]}" -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_tasks","arguments":{"query":"diwali"}}}' "$B/mcp"
cap 04-a-read-only-token-tries-to-create "${MCP[@]}" "${RH[@]}" -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"create_task","arguments":{"title":"Restock the cold drinks"}}}' "$B/mcp"
cap 05-a-writer-creates-a-task "${MCP[@]}" "${WH[@]}" -d '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"create_task","arguments":{"title":"Restock the cold drinks","assignee":"meera","due":"2026-10-26"}}}' "$B/mcp"
cap 06-a-bad-due-date "${MCP[@]}" "${WH[@]}" -d '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"create_task","arguments":{"title":"Pay rent","due":"next friday"}}}' "$B/mcp"
cap 07-a-tool-that-does-not-exist "${MCP[@]}" "${WH[@]}" -d '{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"delete_task","arguments":{"id":"T-1"}}}' "$B/mcp"
cap 08-people-use-the-rest-api -H 'Authorization: Bearer demo-kirana-reader' "$B/tasks?status=OPEN"
cap 09-another-customer-searches -H 'Authorization: Bearer demo-studio-writer' "$B/tasks?q=diwali"
cap 10-no-token "${MCP[@]}" -d "$INIT" "$B/mcp"
cap 11-a-token-without-task-scopes -H 'Authorization: Bearer demo-kirana-calendar' "$B/tasks"
cap 12-a-page-on-another-site "${MCP[@]}" -H 'Authorization: Bearer demo-kirana-writer' -H 'Origin: https://evil.example' -d "$INIT" "$B/mcp"
# An agent in a loop: requests until the first 429, counted, then one more captured.
S=$(date +%S); [ "${S#0}" -gt 45 ] && sleep $((61 - ${S#0}))
n=0; while [ "$(curl -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer demo-studio-writer' "$B/tasks")" = 200 ]; do n=$((n + 1)); done
echo "the loop got $n answers with 200, then 429 (case 9, a minute earlier or in this one, may have used one of the 60)" > rate-limit.txt
cap 13-an-agent-in-a-loop -H 'Authorization: Bearer demo-studio-writer' "$B/tasks"
date '+%-d %b %Y' > date.txt
