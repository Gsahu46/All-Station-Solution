# Station 106 plan: Expose an API to AI agents with MCP

**Problem.** Taskloom (fictional work-management SaaS): customers want their AI assistants to create and find tasks.
Today agents scrape the web UI and break on every release. The first MCP attempt turned the internal API into tools
one to one, running as the server: an agent named the workspace, and any token could read or write any customer's tasks.

**Endpoints.** MCP over Streamable HTTP at `/mcp` (Spring AI 2.0 MCP server, SDK 2.1): tools `search_tasks`
(read-only hint; query, status) and `create_task` (title 1..200 one line, assignee username, due date). `GET /tasks?q=&status=`
for people, same token, same rules. Bearer tokens (hashes kept) map to person, workspace and scopes tasks:read / tasks:write.
401 no or unknown token (WWW-Authenticate: Bearer); 403 REST without the scope; a tool error (isError) over MCP without
the scope or with bad arguments; JSON-RPC error for an unknown tool; 403 for a browser Origin not on the list; 429 with
Retry-After past 60 requests a minute per caller.

**Fix.** The caller is read on the request thread after the security filters and passed to tools through the MCP transport
context; tools take no workspace argument; each tool checks its scope; only two tools exist.

**Trap.** `AgentToolsTrapTest`: OldTools (test only: old_search_tasks / old_create_task with a workspace argument, run as the
server) let a read-only kirana token read studio's tasks and create one there as "taskloom-server". The API's tools: no
workspace parameter, only kirana's tasks, create refused for the read-only token.

**Review.** Scope check dropped ("the client asks the user before write tools") and REST open to any token.

**Practice.** 1: get_task, read-only, own workspace only. 2: requestId so a retried create_task makes one task.
3 (paper): OAuth for agents.
