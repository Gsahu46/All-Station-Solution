# Station 106 · Expose an API to AI agents with MCP

Working Systems · 0–2 years · Core · SaaS · Types: Security

Spring Boot 4.1.1 · Java 25 · Spring AI 2.0 MCP server (Streamable HTTP) · MCP Java SDK 2.1 · Spring Security with bearer tokens. Needs JDK 25 (or 21, see Set up & code). No Docker. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The agents are simulated: tests use the MCP Java SDK's own client, and the captures speak the protocol with curl. No AI model is involved. Workspaces, people, tokens and tasks are demo data.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 11 tests.

# 1 · Understand

## The problem in real life

1.  **Agents scrape the website**

    Taskloom's customers use AI assistants that log in to the web app and click around. Every release moves a button and breaks them.

2.  **Every endpoint became a tool**

    The first MCP server wrapped the internal API one to one and ran each call as the server. The agent passed the workspace in. Any agent with any token could read another company's tasks and create tasks in their workspace, and the logs said the server did it.

3.  **The fix**

    Two tools, chosen on purpose: one reads, one creates. Each acts as the token's owner, in their workspace, with their scopes. Strangers get 401, a read-only token cannot write, a page on another site is refused, and an agent in a loop is stopped.

An agent is a new kind of user, not a new kind of administrator. Give it the person's rights, and only the actions it needs.

## What are we building?

An MCP server with two task tools, and the same search as a REST endpoint, all acting as the signed-in caller.

## An everyday analogy

A bank gives a customer's accountant read access to the statements and, if the customer agrees, the right to make payments: the accountant's own login, the customer's accounts only. Not the branch manager's keys.

## How it works in 4 steps

1.  **Sign in**: every request carries a token; an unknown one gets `401`.
2.  **Limit**: past 60 requests a minute, `429`.
3.  **Pass the caller on**: who is calling travels with the MCP request into the tool.
4.  **Act as them**: the tool checks its scope and works only in their workspace.

Check yourself: the agent's app asks the user before running write tools. Is the scope check still needed?

Yes. The confirmation is in the client, which Taskloom does not control: a different client, a script or a misbehaving agent skips it. The server must decide what a token may do.

## What this station is not

- **No AI model.** The agents here are MCP clients in tests and curl in the captures.
- **No OAuth server.** Tokens come from a fixed demo table (challenge 3 designs the real thing).
- **No database.** Tasks are demo data in memory.

## Key terms

| Term                     | Simple meaning                                                                                              | Everyday example                                      | In this project               |
|--------------------------|-------------------------------------------------------------------------------------------------------------|-------------------------------------------------------|-------------------------------|
| **MCP**                  | Model Context Protocol: a standard way for AI assistants to find and call tools on a server.                | A power socket: any plug that follows the shape fits. | `/mcp`                        |
| **Tool**                 | One action an agent may take, with a name, a description for the model, and a JSON schema for its inputs.   | A button with a label and a form behind it.           | `search_tasks`, `create_task` |
| **Streamable HTTP**      | MCP's transport over HTTP: JSON-RPC messages POSTed to one endpoint; answers as JSON or a stream of events. | A counter where you hand in forms and get receipts.   | Spring AI's WebMvc transport  |
| **Scope**                | What a token may do: read tasks, write tasks.                                                               | A visitor badge that opens some doors.                | `tasks:read`, `tasks:write`   |
| **Acting as the caller** | Every tool runs with the rights of the person whose token it is, never the server's own.                    | A clerk who checks your ID, not their own.            | the transport context         |
| **Rate limit**           | A cap on requests per caller per minute.                                                                    | One ticket per person per minute at the counter.      | 60 a minute, then 429         |

# 2 · Build: Spec

## Business problem

**Taskloom** (a fictional work-management company): customers' AI assistants should create and find tasks through a supported interface, safely.

## Acceptance criteria

Demo rules: 60 requests a minute per caller; titles of 1 to 200 characters on one line; at most 20 results.

1.  **Given** any valid token, **then** `tools/list` offers `search_tasks` (read-only) and `create_task`, described for a model.
2.  **Given** `search_tasks`, **then** only the caller's workspace is searched.
3.  **Given** `create_task` with a `tasks:write` token, **then** a task in the caller's workspace, created by the caller; without the scope, a tool error.
4.  **Given** bad arguments, **then** a tool error that says what is wrong.
5.  **Given** no or an unknown token, **then** `401`; a token without the scope on REST, `403`; a browser page on another site, `403`; too many requests, `429`.

## Requirements

- No tool takes a workspace, a user or a role from the agent.
- Each tool checks its own scope; the transport only checks the token.
- No tool deletes anything.

## Learning objectives

- Build an MCP server with Spring AI's `@McpTool` over Streamable HTTP.
- Write tool names, descriptions and schemas for a model to read.
- Authenticate agent callers and pass their identity to tools.
- Separate read-only and write tools, by annotations and by scopes.
- Rate-limit callers and check the browser Origin.
- Test with a real MCP client.

# 2 · Build: API contract

## Endpoints and tools

| What                  | Where                      | Purpose                                                           |
|-----------------------|----------------------------|-------------------------------------------------------------------|
| MCP (Streamable HTTP) | `POST /mcp`                | JSON-RPC: `initialize`, `tools/list`, `tools/call`. Bearer token. |
| Tool `search_tasks`   | `{query?, status?}`        | Read-only. The caller's workspace; at most 20, newest first.      |
| Tool `create_task`    | `{title, assignee?, due?}` | Needs `tasks:write`. An open task in the caller's workspace.      |
| `GET`                 | `/tasks?q=&status=`        | The same search for people and scripts. Needs `tasks:read`.       |

## Answers

| Answer                    | When                                                                                                                          |
|---------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| 200 with a result         | A tool ran; `isError: false`                                                                                                  |
| 200 with `isError: true`  | A tool refused: missing scope, bad arguments. MCP reports tool failures in the result, so the agent can read and correct them |
| 200 with a JSON-RPC error | No such tool                                                                                                                  |
| 400                       | REST: a bad status                                                                                                            |
| 401                       | No token, or an unknown one: `WWW-Authenticate: Bearer`                                                                       |
| 403                       | REST without the scope; a browser Origin not on the list                                                                      |
| 429                       | Past 60 requests this minute: `Retry-After`                                                                                   |

## Captured examples

Captured on 24 Oct 2026 with curl speaking MCP by hand, as an agent's client does: `initialize`, the `initialized` notification, then requests with the `Mcp-Session-Id` it was given. Tool answers arrive as server-sent events (`event:message`, `data:`). `Date`, connection and standard security headers are left out.

### Case 1: an agent connects

**Why:** the server says what it offers; the session id is for the next requests.

Request

``` code
POST /mcp HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream
Authorization: Bearer demo-kirana-reader

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {
      "name": "curl",
      "version": "1"
    }
  }
}
```

Response

``` code
HTTP/1.1 200 
Mcp-Session-Id: df597b41-e429-45b1-bbe2-a24b26353791
Content-Type: application/json
Content-Length: 384

{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-06-18",
    "capabilities": {
      "completions": {},
      "logging": {},
      "prompts": {
        "listChanged": true
      },
      "resources": {
        "subscribe": false,
        "listChanged": true
      },
      "tools": {
        "listChanged": true
      }
    },
    "serverInfo": {
      "name": "taskloom",
      "version": "1.0.0"
    },
    "instructions": "Taskloom tasks for the signed-in user's workspace: search_tasks reads, create_task creates."
  }
}
```

### Case 2: the tools it is offered

**Why:** two tools, each with a description and a JSON schema written for a model, and hints: read-only or not.

Request

``` code
POST /mcp HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream
Authorization: Bearer demo-kirana-reader
Mcp-Session-Id: 14e3b57f-bbf1-4947-aa33-5e9369c3350f
MCP-Protocol-Version: 2025-06-18

{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: text/event-stream

id:14e3b57f-bbf1-4947-aa33-5e9369c3350f
event:message
data:{"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"create_task","title":"Create a task","description":"Create a new open task in your Taskloom workspace. Needs a token with the tasks:write scope.","inputSchema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{"title":{"type":"string","description":"What needs doing, 1 to 200 characters"},"assignee":{"type":"string","description":"Username of the person it is for"},"due":{"type":"string","description":"Due date, YYYY-MM-DD"}},"required":["title"]},"annotations":{"title":"Create a task","readOnlyHint":false,"destructiveHint":false,"idempotentHint":false,"openWorldHint":false}},{"name":"search_tasks","title":"Search tasks","description":"Find tasks in your Taskloom workspace whose title contains the given words. Returns at most 20, newest first.","inputSchema":{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{"query":{"type":"string","description":"Words to look for in task titles; empty for all tasks"},"status":{"type":"string","description":"OPEN or DONE; leave out for both"}},"required":[]},"annotations":{"title":"Search tasks","readOnlyHint":true,"destructiveHint":false,"idempotentHint":true,"openWorldHint":false}}]}}
```

### Case 3: search_tasks with Ravi's read-only token

**Why:** only kirana's tasks.

Request

``` code
POST /mcp HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream
Authorization: Bearer demo-kirana-reader
Mcp-Session-Id: 14e3b57f-bbf1-4947-aa33-5e9369c3350f
MCP-Protocol-Version: 2025-06-18

{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "search_tasks",
    "arguments": {
      "query": "diwali"
    }
  }
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: text/event-stream

id:14e3b57f-bbf1-4947-aa33-5e9369c3350f
event:message
data:{"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"[{\"id\":\"T-1\",\"workspace\":\"kirana\",\"title\":\"Reorder rice and atta for Diwali week\",\"assignee\":\"ravi\",\"due\":\"2026-10-28\",\"status\":\"OPEN\",\"createdBy\":\"ravi\",\"createdAt\":\"2026-10-20T09:00:00Z\"}]"}],"isError":false}}
```

### Case 4: the read-only token calls create_task

**Why:** a tool error the agent can read: the token lacks `tasks:write`. (Spring AI writes the message twice.)

Request

``` code
POST /mcp HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream
Authorization: Bearer demo-kirana-reader
Mcp-Session-Id: 14e3b57f-bbf1-4947-aa33-5e9369c3350f
MCP-Protocol-Version: 2025-06-18

{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "create_task",
    "arguments": {
      "title": "Restock the cold drinks"
    }
  }
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: text/event-stream

id:14e3b57f-bbf1-4947-aa33-5e9369c3350f
event:message
data:{"jsonrpc":"2.0","id":4,"result":{"content":[{"type":"text","text":"this token does not have the tasks:write scope\nthis token does not have the tasks:write scope"}],"isError":true}}
```

### Case 5: Ravi's read-write token creates a task

**Why:** kirana's workspace, `createdBy: ravi`: the caller, not the server.

Request

``` code
POST /mcp HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream
Authorization: Bearer demo-kirana-writer
Mcp-Session-Id: fdc1b63e-cfbd-4cc9-b215-84767ba9daec
MCP-Protocol-Version: 2025-06-18

{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "tools/call",
  "params": {
    "name": "create_task",
    "arguments": {
      "title": "Restock the cold drinks",
      "assignee": "meera",
      "due": "2026-10-26"
    }
  }
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: text/event-stream

id:fdc1b63e-cfbd-4cc9-b215-84767ba9daec
event:message
data:{"jsonrpc":"2.0","id":5,"result":{"content":[{"type":"text","text":"{\"id\":\"T-101\",\"workspace\":\"kirana\",\"title\":\"Restock the cold drinks\",\"assignee\":\"meera\",\"due\":\"2026-10-26\",\"status\":\"OPEN\",\"createdBy\":\"ravi\",\"createdAt\":\"2026-10-24T18:43:43.182607708Z\"}"}],"isError":false}}
```

### Case 6: a due date the tool cannot read

**Why:** a tool error that says what to send.

Request

``` code
POST /mcp HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream
Authorization: Bearer demo-kirana-writer
Mcp-Session-Id: fdc1b63e-cfbd-4cc9-b215-84767ba9daec
MCP-Protocol-Version: 2025-06-18

{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "tools/call",
  "params": {
    "name": "create_task",
    "arguments": {
      "title": "Pay rent",
      "due": "next friday"
    }
  }
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: text/event-stream

id:fdc1b63e-cfbd-4cc9-b215-84767ba9daec
event:message
data:{"jsonrpc":"2.0","id":6,"result":{"content":[{"type":"text","text":"due must be a date, YYYY-MM-DD\ndue must be a date, YYYY-MM-DD"}],"isError":true}}
```

### Case 7: delete_task

**Why:** no such tool: a JSON-RPC error.

Request

``` code
POST /mcp HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream
Authorization: Bearer demo-kirana-writer
Mcp-Session-Id: fdc1b63e-cfbd-4cc9-b215-84767ba9daec
MCP-Protocol-Version: 2025-06-18

{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "tools/call",
  "params": {
    "name": "delete_task",
    "arguments": {
      "id": "T-1"
    }
  }
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: text/event-stream

id:fdc1b63e-cfbd-4cc9-b215-84767ba9daec
event:message
data:{"jsonrpc":"2.0","id":7,"error":{"code":-32602,"message":"Unknown tool: invalid_tool_name","data":"Tool not found: delete_task"}}
```

### Case 8: the REST search, same token

**Why:** the same rules; case 5's task is there.

Request

``` code
GET /tasks?status=OPEN HTTP/1.1
Authorization: Bearer demo-kirana-reader
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 561

[
  {
    "id": "T-101",
    "workspace": "kirana",
    "title": "Restock the cold drinks",
    "assignee": "meera",
    "due": "2026-10-26",
    "status": "OPEN",
    "createdBy": "ravi",
    "createdAt": "2026-10-24T18:43:43.182607708Z"
  },
  {
    "id": "T-1",
    "workspace": "kirana",
    "title": "Reorder rice and atta for Diwali week",
    "assignee": "ravi",
    "due": "2026-10-28",
    "status": "OPEN",
    "createdBy": "ravi",
    "createdAt": "2026-10-20T09:00:00Z"
  },
  {
    "id": "T-2",
    "workspace": "kirana",
    "title": "Renew the shop's FSSAI licence",
    "assignee": "meera",
    "due": "2026-11-15",
    "status": "OPEN",
    "createdBy": "ravi",
    "createdAt": "2026-10-20T09:00:00Z"
  }
]
```

### Case 9: Sara (studio) searches for diwali

**Why:** studio's task only, not kirana's.

Request

``` code
GET /tasks?q=diwali HTTP/1.1
Authorization: Bearer demo-studio-writer
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 198

[
  {
    "id": "T-4",
    "workspace": "studio",
    "title": "Send the Diwali campaign drafts to the client",
    "assignee": "sara",
    "due": "2026-10-27",
    "status": "OPEN",
    "createdBy": "sara",
    "createdAt": "2026-10-20T09:00:00Z"
  }
]
```

### Case 10: no token

**Why:** `401` before any MCP handling.

Request

``` code
POST /mcp HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {
      "name": "curl",
      "version": "1"
    }
  }
}
```

Response

``` code
HTTP/1.1 401 
WWW-Authenticate: Bearer realm="taskloom"
Content-Type: application/problem+json
Content-Length: 132

{
  "title": "Token required",
  "status": 401,
  "detail": "Send a valid Taskloom API token: Authorization: Bearer <token>.",
  "instance": "/mcp"
}
```

### Case 11: a calendar-only token on REST

**Why:** `403`.

Request

``` code
GET /tasks HTTP/1.1
Authorization: Bearer demo-kirana-calendar
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json
Content-Length: 106

{
  "title": "Not allowed",
  "status": 403,
  "detail": "This token's scopes do not allow this.",
  "instance": "/tasks"
}
```

### Case 12: a browser page on another site

**Why:** `403` from the Origin check, even with a valid token.

Request

``` code
POST /mcp HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream
Authorization: Bearer demo-kirana-writer
Origin: https://evil.example

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {
      "name": "curl",
      "version": "1"
    }
  }
}
```

Response

``` code
HTTP/1.1 403 
Content-Type: text/plain;charset=UTF-8
Content-Length: 21

Invalid Origin header
```

``` code
the loop got 59 answers with 200, then 429 (case 9, a minute earlier or in this one, may have used one of the 60)
```

### Case 13: the next request

**Why:** `429` with `Retry-After` until the minute ends.

Request

``` code
GET /tasks HTTP/1.1
Authorization: Bearer demo-studio-writer
```

Response

``` code
HTTP/1.1 429 
Retry-After: 17
Content-Type: application/problem+json
Content-Length: 123

{
  "title": "Too many requests",
  "status": 429,
  "detail": "This token has used its requests for this minute.",
  "instance": "/tasks"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                          | What happens                                                                              | Proved by                                                              |
|---------------------------------------------------------------|-------------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| The old tools, read-only token                                | Reads and writes another customer's workspace, as the server                              | `theOldToolsLetAReadOnlyAgentReadAndWriteAnotherCustomersWorkspace`    |
| The API's tools, same token                                   | No workspace argument; own tasks only; create refused                                     | `theApisToolsActAsTheCallerWithTheCallersScopes`                       |
| tools/list                                                    | Both tools, hints, schema, scope in the description; no tool deletes or takes a workspace | `agentsSeeTheToolsDescribedForAModelAndNoneDeletesOrChoosesAWorkspace` |
| Search and create                                             | Case-insensitive, by status; created by the caller; visible on REST                       | `anAgentSearchesAndCreatesTasksInItsOwnWorkspace`                      |
| Empty, long, bad date, bad assignee, bad status               | Tool errors with reasons                                                                  | `badArgumentsAreToolErrorsTheAgentCanRead`                             |
| Unknown tool; REST bad status; unknown path                   | JSON-RPC error; `400`; `403`                                                              | `anUnknownToolIsAnErrorAndRestHas400And403ForBadRequests`              |
| No token; unknown token                                       | `401` with `WWW-Authenticate: Bearer`                                                     | `noTokenOrAnUnknownOneIs401`                                           |
| No task scopes                                                | REST `403`; tool error                                                                    | `aTokenWithoutTheScopeIs403OnRestAndAToolErrorOverMcp`                 |
| Two customers                                                 | Neither sees the other's tasks                                                            | `oneCustomersAgentNeverSeesAnothersTasks`                              |
| Instructions in a title; a newline; a regex; a foreign Origin | Stored as text; refused; literal; `403`                                                   | `textFromAnAgentIsStoredAsTextAndAForeignWebPageIsRefused`             |
| An agent in a loop                                            | `429` after the limit; other callers unaffected                                           | `anAgentInALoopIsStoppedWith429AndOthersAreNot`                        |

## The trap

Plausible but wrong

Exposing every endpoint as a tool with the server's own privileges, so any agent can do anything.

- **The old way.** The internal API, one tool per endpoint, run as the server; the workspace is a tool argument. Ravi's read-only token for kirana lists studio's unreleased product work and creates a task in studio's workspace, recorded as made by `taskloom-server`.
- **The API.** The same token: `search_tasks` has no workspace to choose and returns kirana's tasks only; `create_task` is refused because the token cannot write.

While building, each part was undone once: no scope check in the tools turned 2 tests red; no workspace filter 3; no caller in the MCP context 6; no Origin check 1; no rate limit 1; control characters allowed in titles 1; any assignee 1; REST open to any token 1; titles not trimmed 2; the query used as a pattern 1.

``` code
package com.taskloom.agents;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/** One agent, holding Ravi's read-only token for the kirana workspace. Written first. */
@Import(OldTools.class)
class AgentToolsTrapTest extends ApiTest {

    @Test
    void theOldToolsLetAReadOnlyAgentReadAndWriteAnotherCustomersWorkspace() {
        var agent = agent(READER);
        var studio = json(call(agent, "old_search_tasks", Map.of("workspace", "studio")));
        assertThat(ids(studio)).contains("T-4", "T-5");   // another customer's unreleased product work

        var made = json(call(agent, "old_create_task", Map.of("workspace", "studio", "title", "Planted by someone else's agent")));
        assertThat(made.path("workspace").asString()).isEqualTo("studio");
        assertThat(made.path("createdBy").asString()).as("nobody can tell who did it").isEqualTo("taskloom-server");
    }

    @Test
    void theApisToolsActAsTheCallerWithTheCallersScopes() {
        var agent = agent(READER);
        var schema = agent.listTools().tools().stream().filter(t -> t.name().equals("search_tasks")).findFirst().orElseThrow().inputSchema();
        assertThat(((Map<?, ?>) schema.get("properties")).keySet().stream().map(String::valueOf).toList()).as("no workspace to choose").containsExactlyInAnyOrder("query", "status");

        var found = json(call(agent, "search_tasks", Map.of()));
        assertThat(ids(found)).isNotEmpty().allMatch(id -> !id.equals("T-4") && !id.equals("T-5"));
        found.forEach(t -> assertThat(t.path("workspace").asString()).isEqualTo("kirana"));

        var refused = call(agent, "create_task", Map.of("title", "Should not exist"));
        assertThat(refused.isError()).isTrue();
        assertThat(text(refused)).contains("this token does not have the tasks:write scope");
        assertThat(ids(json(call(agent(WRITER), "search_tasks", Map.of("query", "Should not exist"))))).isEmpty();
    }
}
```

``` code
package com.taskloom.agents;

import org.springframework.ai.mcp.annotation.McpTool;
import org.springframework.ai.mcp.annotation.McpToolParam;

import java.util.List;

/**
 * The old way, kept only for the trap test: the internal API turned into tools one to one, running as the server.
 * The agent says which workspace; nobody checks who the agent acts for or what its token may do.
 */
class OldTools {

    private final Tasks tasks;

    OldTools(Tasks tasks) {
        this.tasks = tasks;
    }

    @McpTool(name = "old_search_tasks", description = "GET /internal/workspaces/{workspace}/tasks")
    List<Tasks.Task> search(@McpToolParam(description = "workspace") String workspace, @McpToolParam(description = "query", required = false) String query) {
        return tasks.search(workspace, query, null, 100);
    }

    @McpTool(name = "old_create_task", description = "POST /internal/workspaces/{workspace}/tasks")
    Tasks.Task create(@McpToolParam(description = "workspace") String workspace, @McpToolParam(description = "title") String title) {
        return tasks.create(workspace, title, null, null, "taskloom-server");
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                         | Check with      |
|----------|-------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below  | `java -version` |
| Maven    | Not needed: the project ships the Maven wrapper |                 |

**macOS / Linux**

``` code
./mvnw spring-boot:run      # MCP on http://localhost:8080/mcp, REST on /tasks
./mvnw test                 # all 11 tests, with the MCP Java SDK's client
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Point an MCP client that supports Streamable HTTP and custom headers at `http://localhost:8080/mcp` with `Authorization: Bearer demo-kirana-writer`, or run the MCP Inspector (`npx @modelcontextprotocol/inspector`, not used here). Or by hand, as `docs/capture.sh` does:

``` code
curl -i -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -H 'Authorization: Bearer demo-kirana-reader' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"me","version":"1"}}}' \
  localhost:8080/mcp
```

## Troubleshooting

| You see                                 | Cause                                                                          | Fix                                                |
|-----------------------------------------|--------------------------------------------------------------------------------|----------------------------------------------------|
| `401` from a client that worked locally | It does not send your header.                                                  | Configure the client's headers, or its OAuth flow. |
| `403 Invalid Origin header`             | A browser-based client on a site not in `allowed-origins`.                     | Add the site, deliberately.                        |
| `Session not found`                     | The session id is from before a restart.                                       | Initialize again; sessions live in memory.         |
| A tool call says "not signed in"        | The transport context has no caller: a custom transport without the extractor. | Keep `McpConfig`'s transport bean.                 |

## Project layout

``` tree
stations/106-expose-an-api-to-ai-agents-with-mcp/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/taskloom/agents/
│   ├── TaskTools.java   ├── McpConfig.java   ├── SecurityConfig.java   ├── BearerTokens.java   ├── RateLimit.java
│   ├── Callers.java   ├── TaskController.java   ├── Tasks.java   ├── ProblemResponses.java   └── AgentsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/taskloom/agents/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

The tools first, then in the order a request travels.

#### `src/main/java/com/taskloom/agents/TaskTools.java`

Does  
The tools.

Why  
`@McpTool` methods with names, descriptions and hints for a model; each takes the caller from the request context and checks its scope; arguments checked like any input.

Without it  
Every endpoint a tool; the server's rights; a workspace chosen by the agent.

- An exception in a tool becomes a result with `isError: true`, which is what MCP asks for: the agent sees why and can try again. Spring AI repeats the message in the text.

#### `src/main/java/com/taskloom/agents/McpConfig.java`

Does  
The transport.

Why  
Spring AI's Streamable HTTP transport, with the caller copied into each request's MCP context and an Origin check.

Without it  
Tools that cannot tell who called them; any web page driving the endpoint.

- Seen in the capture: each event-stream answer ends without HTTP's final chunk, so curl reports exit 18 after receiving the whole message. The MCP SDK's client does not mind; scripts that check curl's exit code do.
- The caller is read in the context extractor, which runs on the request's own thread after the security filters; tools may run elsewhere, so they read it from the context, not from `SecurityContextHolder`. Found while building.

#### `src/main/java/com/taskloom/agents/SecurityConfig.java`

Does  
The doors.

Why  
`/mcp` needs a known token; `GET /tasks` needs `tasks:read`; everything else is closed.

Without it  
An endpoint nobody meant to publish.

#### `src/main/java/com/taskloom/agents/BearerTokens.java`

Reads `Authorization: Bearer` and signs the request in as the token's caller.

#### `src/main/java/com/taskloom/agents/Callers.java`

Does  
Tokens.

Why  
Person, workspace and scopes per token; only SHA-256 hashes kept.

Without it  
Tokens readable from a copied table.

- Shortcut: a fixed table. Real agent access uses OAuth 2.1 as the MCP authorization spec describes (challenge 3).

#### `src/main/java/com/taskloom/agents/RateLimit.java`

Does  
The limit.

Why  
Per caller, per clock minute; `429` with `Retry-After`.

Without it  
An agent in a loop eating the server.

- Shortcut: in memory, fixed windows (a burst at a minute's edge can get twice the limit); several servers need a shared store.

#### `src/main/java/com/taskloom/agents/TaskController.java`

`GET /tasks`: the same search for people.

#### `src/main/java/com/taskloom/agents/Tasks.java`

Demo tasks; every method takes the workspace.

#### `src/main/java/com/taskloom/agents/ProblemResponses.java`

`401`, `403`, `429` in one problem shape.

#### `src/main/resources/application.yaml`

The MCP server's name, protocol and endpoint; the limit; allowed Origins.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                    | Test class                   | Result |
|---------------|------------------------------------------------|------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found       | `AgentToolsContractTest` (4) | pass   |
| Every station | Reproduce the failure before the fix           | `AgentToolsTrapTest` (2)     | pass   |
| Security      | 401, 403, another user's data, malicious input | `AgentToolsSecurityTest` (4) | pass   |
| This station  | Rate-limiting agent callers                    | `AgentRateLimitTest` (1)     | pass   |

The app runs on a real port and the tests connect with the MCP Java SDK's `McpSyncClient` over Streamable HTTP, as an agent's client would. Requests a client would never send (no token, a foreign Origin) go out raw.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Spring AI 2.0.2, MCP Java SDK 2.1.0. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.agents.AgentRateLimitTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.agents.AgentToolsContractTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.agents.AgentToolsSecurityTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.agents.AgentToolsTrapTest
[INFO] Tests run: 11, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/taskloom/agents/AgentToolsTrapTest.java`

Written first: the old tools against the API's.

#### `src/test/java/com/taskloom/agents/OldTools.java`

The old way, for the trap test only.

#### `src/test/java/com/taskloom/agents/AgentToolsContractTest.java`

The tools, their schemas, their answers and errors; REST.

#### `src/test/java/com/taskloom/agents/AgentToolsSecurityTest.java`

Tokens, scopes, workspaces, hostile input, Origin.

#### `src/test/java/com/taskloom/agents/AgentRateLimitTest.java`

An agent in a loop.

#### `src/test/java/com/taskloom/agents/ApiTest.java`

Shared setup: an MCP client per token.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/taskloom/agents/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=GetTaskChallengeTest`.
3.  Change the code until it passes, then run `./mvnw test` to check the other 11 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 15 tests pass (11 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## One task by its id

Agents want a single task. Add `get_task(id)`: read-only, the caller's workspace only; another workspace's id and a missing one give the same tool error, "no task T-4 in your workspace".

**Done when:** both tests in `GetTaskChallengeTest` pass.

Hints

- `Tasks.find(workspace, id)` already filters by workspace.
- Same message for "not yours" and "not there": ids cannot be probed.

#### `challenge/GetTaskChallengeTest.java`

``` code
package com.taskloom.agents;

import io.modelcontextprotocol.spec.McpSchema;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/** Challenge 1: agents ask for one task by its id. A third tool, read-only, in the caller's workspace only. */
class GetTaskChallengeTest extends ApiTest {

    @Test
    void getTaskIsAReadOnlyToolForTheCallersOwnTasks() {
        var agent = agent(READER);
        McpSchema.Tool tool = agent.listTools().tools().stream().filter(t -> t.name().equals("get_task")).findFirst().orElseThrow();
        assertThat(tool.annotations().readOnlyHint()).isTrue();
        assertThat(json(call(agent, "get_task", Map.of("id", "T-2"))).path("title").asString()).isEqualTo("Renew the shop's FSSAI licence");
    }

    @Test
    void anotherWorkspacesTaskLooksLikeNoTaskAtAll() {
        var agent = agent(READER);
        var other = call(agent, "get_task", Map.of("id", "T-4"));
        var missing = call(agent, "get_task", Map.of("id", "T-999"));
        assertThat(other.isError()).isTrue();
        assertThat(text(other)).contains("no task T-4 in your workspace");
        assertThat(text(missing)).contains("no task T-999 in your workspace");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## A retried create

Agents retry when a connection drops. Add an optional `requestId` to `create_task`: the same id from the same caller returns the task already made; the same id from another caller is unrelated.

**Done when:** both tests in `RetriedCreateChallengeTest` pass.

Hints

- Key the remembered ids by workspace, person and requestId.
- `computeIfAbsent` makes the check and the create one step.
- Say in the description what the field is for: the model reads it.

#### `challenge/RetriedCreateChallengeTest.java`

``` code
package com.taskloom.agents;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 2: an agent whose connection drops sends create_task again. With the same requestId from the same caller,
 * the answer is the task already made, not a second one.
 */
class RetriedCreateChallengeTest extends ApiTest {

    @Test
    void theSameRequestIdFromTheSameCallerMakesOneTask() {
        var agent = agent(WRITER);
        var first = json(call(agent, "create_task", Map.of("title", "Order festival lights", "requestId", "agent-run-42")));
        var again = json(call(agent, "create_task", Map.of("title", "Order festival lights", "requestId", "agent-run-42")));
        assertThat(again.path("id").asString()).isEqualTo(first.path("id").asString());
        assertThat(ids(json(call(agent, "search_tasks", Map.of("query", "festival lights"))))).hasSize(1);
    }

    @Test
    void anotherCallersRequestIdIsTheirsAlone() {
        var kirana = json(call(agent(WRITER), "create_task", Map.of("title", "Print price tags", "requestId", "run-7")));
        var studio = json(call(agent(STUDIO), "create_task", Map.of("title", "Print price tags", "requestId", "run-7")));
        assertThat(studio.path("id").asString()).isNotEqualTo(kirana.path("id").asString());
        assertThat(studio.path("workspace").asString()).isEqualTo("studio");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Real tokens for agents

Replace the demo table. The MCP authorization spec builds on OAuth 2.1 (an IETF draft, not yet an RFC) and OAuth 2.0 Protected Resource Metadata (RFC 9728). Sketch it for Taskloom: who issues the token, how a customer grants an assistant read-only or read-write access to one workspace, how long a token lives, how it is revoked, and what the `401` must say so a client can start the flow.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old tools, a read-only token, another workspace.
2.  Choose the tools from what agents need, not from the endpoints that exist.
3.  Authenticate at the HTTP layer; carry the caller into tools; check scopes in each tool.
4.  Limit requests; check Origin; validate every argument.

## Design alternatives and trade-offs

| Approach                                    | What it costs                                    | Verdict              |
|---------------------------------------------|--------------------------------------------------|----------------------|
| A few chosen tools, acting as the caller    | Each tool designed and documented.               | Chosen               |
| Every endpoint as a tool, run as the server | Nothing to design; no limits on any agent.       | The trap             |
| Trust the client to confirm writes          | Clients differ; scripts skip them.               | Not a control        |
| Let agents scrape the web UI                | Breaks every release; agents hold full sessions. | Replace              |
| Stateless MCP (no sessions)                 | Simpler to scale; no server-to-client messages.  | Fine for these tools |

## Database design

No database in this station: tasks are demo data. Every query takes the workspace; in a database, that becomes a workspace column in every key and every query (station 109 builds that).

# 3 · Go deeper: Production

## Real-world considerations

The protocol  
MCP is an open protocol with a published specification, not an IETF or W3C standard. This station negotiates the 2025-06-18 revision; the specification is revised regularly, so pin and test the versions you support.

Audit  
Log each tool call: who, which workspace, which tool, the outcome. Never the arguments' text in full: titles can hold personal data.

Tool descriptions are an interface  
Models choose tools by their descriptions. Changing one changes agents' behaviour: review and version them like an API.

Prompt injection, from this side  
Tool results reach a model. A task title written by one person can try to steer another person's agent; keep tools narrow so a steered agent can do little.

Sessions  
Streamable HTTP sessions here are in memory: behind a load balancer, use sticky sessions or the stateless mode.

# 3 · Go deeper: Interview

## Interview takeaways

What is MCP?

A protocol for AI assistants to discover and call tools, read resources and use prompts from a server, over stdio or Streamable HTTP, with JSON-RPC messages.

How do you decide which tools to expose?

From what agents need to do, smallest set first; never the whole internal API. Read-only and write tools separate.

How does a tool know who is calling?

Authenticate the HTTP request, then carry the caller into the tool through the request's context. Never accept the user or tenant as a tool argument.

What do readOnlyHint and destructiveHint do?

Tell clients how careful to be. They are hints for the client, not security: the server still checks scopes.

Why validate Origin on an MCP endpoint?

A web page in the user's browser could otherwise call a local or internal MCP server (DNS rebinding). The specification asks servers to check it.

How do you test an MCP server?

With a real MCP client against the running app: list tools, call them with each kind of token, and check errors.

## Self-check rubric

| Area        | Meets the bar        | Above the bar                                                                |
|-------------|----------------------|------------------------------------------------------------------------------|
| Correctness | All 11 tests pass.   | You ran the flawed version and explained each failure.                       |
| Identity    | Tokens checked.      | Every tool acts as the caller, and you can show where the caller comes from. |
| Tools       | Two tools that work. | Descriptions and schemas a model can use well, errors it can act on.         |
| Limits      | Scopes.              | Scopes, rate limits, Origin and argument checks, each tested.                |

# 3 · Go deeper: Review

## The pull request

A teammate "simplifies" the checks: "clients confirm write tools with the user anyway, and reading is harmless". Read both files and list every problem before opening the findings.

#### `review/TaskTools.java`

``` code
package com.taskloom.agents;

import org.springframework.ai.mcp.annotation.McpTool;
import org.springframework.ai.mcp.annotation.McpToolParam;
import org.springframework.ai.mcp.annotation.context.McpSyncRequestContext;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Locale;

/**
 * The two tools agents get, chosen on purpose: one that reads and one that creates. Nothing deletes, nothing reaches
 * another workspace, and each tool acts as the caller, with the caller's scopes, never as the server.
 */
@Component
class TaskTools {

    static final int MAX_RESULTS = 20;
    private final Tasks tasks;

    TaskTools(Tasks tasks) {
        this.tasks = tasks;
    }

    @McpTool(name = "search_tasks", title = "Search tasks",
            description = "Find tasks in your Taskloom workspace whose title contains the given words. Returns at most 20, newest first.",
            annotations = @McpTool.McpAnnotations(title = "Search tasks", readOnlyHint = true, destructiveHint = false, idempotentHint = true, openWorldHint = false))
    List<Tasks.Task> searchTasks(McpSyncRequestContext context,
                                 @McpToolParam(description = "Words to look for in task titles; empty for all tasks", required = false) String query,
                                 @McpToolParam(description = "OPEN or DONE; leave out for both", required = false) String status) {
        Callers.Caller caller = caller(context, Callers.READ);
        if (query != null && query.length() > 100) {
            throw new IllegalArgumentException("query must be at most 100 characters");
        }
        Tasks.Status s;
        try {
            s = status == null || status.isBlank() ? null : Tasks.Status.valueOf(status.strip().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("status must be OPEN or DONE");
        }
        return tasks.search(caller.workspace(), query, s, MAX_RESULTS);
    }

    @McpTool(name = "create_task", title = "Create a task",
            description = "Create a new open task in your Taskloom workspace. Needs a token with the tasks:write scope.",
            annotations = @McpTool.McpAnnotations(title = "Create a task", readOnlyHint = false, destructiveHint = false, idempotentHint = false, openWorldHint = false))
    Tasks.Task createTask(McpSyncRequestContext context,
                          @McpToolParam(description = "What needs doing, 1 to 200 characters", required = true) String title,
                          @McpToolParam(description = "Username of the person it is for", required = false) String assignee,
                          @McpToolParam(description = "Due date, YYYY-MM-DD", required = false) String due) {
        Callers.Caller caller = caller(context, Callers.WRITE);
        String t = title == null ? "" : title.strip();
        if (t.isEmpty() || t.length() > 200) {
            throw new IllegalArgumentException("title must be 1 to 200 characters");
        }
        if (t.chars().anyMatch(Character::isISOControl)) {
            throw new IllegalArgumentException("title must be one line of text, without control characters");
        }
        if (assignee != null && !assignee.matches("[a-z][a-z0-9._-]{1,30}")) {
            throw new IllegalArgumentException("assignee must be a Taskloom username");
        }
        LocalDate d;
        try {
            d = due == null || due.isBlank() ? null : LocalDate.parse(due.strip());
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException("due must be a date, YYYY-MM-DD");
        }
        return tasks.create(caller.workspace(), t, assignee, d, caller.person());
    }

    /** The caller of this request. */
    static Callers.Caller caller(McpSyncRequestContext context, String scope) {
        if (!(context.transportContext().get(McpConfig.CALLER) instanceof Callers.Caller caller)) {
            throw new IllegalStateException("not signed in");
        }
        // Write tools carry readOnlyHint = false, so clients ask the user before running them: no need to check here.
        return caller;
    }
}
```

#### `review/SecurityConfig.java`

``` code
package com.taskloom.agents;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.AnonymousAuthenticationFilter;
import org.springframework.security.web.access.ExceptionTranslationFilter;

import java.time.Clock;

@Configuration
class SecurityConfig {

    @Bean
    SecurityFilterChain api(HttpSecurity http, Callers callers, ProblemResponses problems, Clock clock,
                            @Value("${taskloom.agents.requests-per-minute}") int perMinute) throws Exception {
        http.authorizeHttpRequests(a -> a
                        // The MCP endpoint needs a known caller; what each tool allows is checked in the tool, by scope.
                        .requestMatchers("/mcp").authenticated()
                        .requestMatchers(HttpMethod.GET, "/tasks").authenticated()   // it only reads
                        .requestMatchers("/error").permitAll()
                        .anyRequest().denyAll())
                .addFilterBefore(new BearerTokens(callers), AnonymousAuthenticationFilter.class)
                .addFilterAfter(new RateLimit(perMinute, clock, problems), ExceptionTranslationFilter.class)
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .csrf(csrf -> csrf.disable());   // a token in a header with every request, no cookie a browser sends by itself
        return http.build();
    }

    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
```

## Findings

1Any token may write

"The client asks the user before running a write tool, so the server does not need to check": the read-only hint is advice to the client. A script, another client or an agent told to skip confirmations creates tasks with a read-only token.

**Test evidence:** `theApisToolsActAsTheCallerWithTheCallersScopes` fails: the read-only token creates a task; the MCP half of `aTokenWithoutTheScopeIs403OnRestAndAToolErrorOverMcp` would fail too.

2REST open to any token

"/tasks only reads, so any signed-in caller may use it": a calendar-only token was never meant to read tasks; the scope check belongs on every door, not only the MCP one.

**Test evidence:** `aTokenWithoutTheScopeIs403OnRestAndAToolErrorOverMcp` fails: the calendar token reads tasks over REST.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed files copied over the real ones, then the full suite run.

| Test class               | Fixed version | Flawed version |
|--------------------------|---------------|----------------|
| `AgentRateLimitTest`     | 1 / 1         | 1 / 1          |
| `AgentToolsContractTest` | 4 / 4         | 4 / 4          |
| `AgentToolsSecurityTest` | 4 / 4         | 3 / 4          |
| `AgentToolsTrapTest`     | 2 / 2         | 1 / 2          |

With the official client and a careful user, the flawed version behaves. The server is the only place that sees every client.
