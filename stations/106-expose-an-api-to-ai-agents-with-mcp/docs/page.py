"""Station 106 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 106,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring AI 2.0 MCP server (Streamable HTTP) · MCP Java SDK 2.1 · Spring Security with bearer tokens",
    "simulation": "The agents are simulated: tests use the MCP Java SDK's own client, and the captures speak the protocol with curl. No AI model is involved. Workspaces, people, tokens and tasks are demo data.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/taskloom/agents/"
T = "src/test/java/com/taskloom/agents/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("MCP", "Model Context Protocol: a standard way for AI assistants to find and call tools on a server.", "A power socket: any plug that follows the shape fits.", "<code>/mcp</code>"),
    ("Tool", "One action an agent may take, with a name, a description for the model, and a JSON schema for its inputs.", "A button with a label and a form behind it.", "<code>search_tasks</code>, <code>create_task</code>"),
    ("Streamable HTTP", "MCP's transport over HTTP: JSON-RPC messages POSTed to one endpoint; answers as JSON or a stream of events.", "A counter where you hand in forms and get receipts.", "Spring AI's WebMvc transport"),
    ("Scope", "What a token may do: read tasks, write tasks.", "A visitor badge that opens some doors.", "<code>tasks:read</code>, <code>tasks:write</code>"),
    ("Acting as the caller", "Every tool runs with the rights of the person whose token it is, never the server's own.", "A clerk who checks your ID, not their own.", "the transport context"),
    ("Rate limit", "A cap on requests per caller per minute.", "One ticket per person per minute at the counter.", "60 a minute, then 429"),
]
STORY = [
    ("Agents scrape the website", "Taskloom's customers use AI assistants that log in to the web app and click around. Every release moves a button and breaks them."),
    ("Every endpoint became a tool", "The first MCP server wrapped the internal API one to one and ran each call as the server. The agent passed the workspace in. Any agent with any token could read another company's tasks and create tasks in their workspace, and the logs said the server did it."),
    ("The fix", "Two tools, chosen on purpose: one reads, one creates. Each acts as the token's owner, in their workspace, with their scopes. Strangers get 401, a read-only token cannot write, a page on another site is refused, and an agent in a loop is stopped."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">An agent is a new kind of user, not a new kind of administrator. Give it the person's rights, and only the actions it needs.</p>

<h2>What are we building?</h2>
<p>An MCP server with two task tools, and the same search as a REST endpoint, all acting as the signed-in caller.</p>

<h2>An everyday analogy</h2>
<p>A bank gives a customer's accountant read access to the statements and, if the customer agrees, the right to make payments: the accountant's own login, the customer's accounts only. Not the branch manager's keys.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Sign in</strong>: every request carries a token; an unknown one gets <code>401</code>.</li>
<li><strong>Limit</strong>: past 60 requests a minute, <code>429</code>.</li>
<li><strong>Pass the caller on</strong>: who is calling travels with the MCP request into the tool.</li>
<li><strong>Act as them</strong>: the tool checks its scope and works only in their workspace.</li>
</ol>

<details class="qa check"><summary>Check yourself: the agent's app asks the user before running write tools. Is the scope check still needed?</summary><p>Yes. The confirmation is in the client, which Taskloom does not control: a different client, a script or a misbehaving agent skips it. The server must decide what a token may do.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No AI model.</strong> The agents here are MCP clients in tests and curl in the captures.</li>
<li><strong>No OAuth server.</strong> Tokens come from a fixed demo table (challenge 3 designs the real thing).</li>
<li><strong>No database.</strong> Tasks are demo data in memory.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Taskloom</strong> (a fictional work-management company): customers' AI assistants should create and find tasks through a supported interface, safely.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo rules: 60 requests a minute per caller; titles of 1 to 200 characters on one line; at most 20 results.</p>
<ol class="gwt">
<li><b>Given</b> any valid token, <b>then</b> <code>tools/list</code> offers <code>search_tasks</code> (read-only) and <code>create_task</code>, described for a model.</li>
<li><b>Given</b> <code>search_tasks</code>, <b>then</b> only the caller's workspace is searched.</li>
<li><b>Given</b> <code>create_task</code> with a <code>tasks:write</code> token, <b>then</b> a task in the caller's workspace, created by the caller; without the scope, a tool error.</li>
<li><b>Given</b> bad arguments, <b>then</b> a tool error that says what is wrong.</li>
<li><b>Given</b> no or an unknown token, <b>then</b> <code>401</code>; a token without the scope on REST, <code>403</code>; a browser page on another site, <code>403</code>; too many requests, <code>429</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>No tool takes a workspace, a user or a role from the agent.</li>
<li>Each tool checks its own scope; the transport only checks the token.</li>
<li>No tool deletes anything.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Build an MCP server with Spring AI's <code>@McpTool</code> over Streamable HTTP.</li>
<li>Write tool names, descriptions and schemas for a model to read.</li>
<li>Authenticate agent callers and pass their identity to tools.</li>
<li>Separate read-only and write tools, by annotations and by scopes.</li>
<li>Rate-limit callers and check the browser Origin.</li>
<li>Test with a real MCP client.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints and tools</h2>
""" + table(["What", "Where", "Purpose"], [
    ["MCP (Streamable HTTP)", "<code>POST /mcp</code>", "JSON-RPC: <code>initialize</code>, <code>tools/list</code>, <code>tools/call</code>. Bearer token."],
    ["Tool <code>search_tasks</code>", "<code>{query?, status?}</code>", "Read-only. The caller's workspace; at most 20, newest first."],
    ["Tool <code>create_task</code>", "<code>{title, assignee?, due?}</code>", "Needs <code>tasks:write</code>. An open task in the caller's workspace."],
    ["<code>GET</code>", "<code>/tasks?q=&amp;status=</code>", "The same search for people and scripts. Needs <code>tasks:read</code>."]]) + """
<h2>Answers</h2>
""" + table(["Answer", "When"], [
    ['<span class="pill ok">200</span> with a result', "A tool ran; <code>isError: false</code>"],
    ['<span class="pill warn">200</span> with <code>isError: true</code>', "A tool refused: missing scope, bad arguments. MCP reports tool failures in the result, so the agent can read and correct them"],
    ['<span class="pill warn">200</span> with a JSON-RPC error', "No such tool"],
    ['<span class="pill warn">400</span>', "REST: a bad status"],
    ['<span class="pill warn">401</span>', "No token, or an unknown one: <code>WWW-Authenticate: Bearer</code>"],
    ['<span class="pill warn">403</span>', "REST without the scope; a browser Origin not on the list"],
    ['<span class="pill warn">429</span>', "Past 60 requests this minute: <code>Retry-After</code>"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured on """ + read("docs/captures/date.txt").strip() + """ with curl speaking MCP by hand, as an agent's client does: <code>initialize</code>, the <code>initialized</code> notification, then requests with the <code>Mcp-Session-Id</code> it was given. Tool answers arrive as server-sent events (<code>event:message</code>, <code>data:</code>). <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-an-agent-connects", "Case 1: an agent connects", "<b>Why:</b> the server says what it offers; the session id is for the next requests."),
    ("02-the-tools-it-is-offered", "Case 2: the tools it is offered", "<b>Why:</b> two tools, each with a description and a JSON schema written for a model, and hints: read-only or not."),
    ("03-search-tasks", "Case 3: search_tasks with Ravi's read-only token", "<b>Why:</b> only kirana's tasks."),
    ("04-a-read-only-token-tries-to-create", "Case 4: the read-only token calls create_task", "<b>Why:</b> a tool error the agent can read: the token lacks <code>tasks:write</code>. (Spring AI writes the message twice.)"),
    ("05-a-writer-creates-a-task", "Case 5: Ravi's read-write token creates a task", "<b>Why:</b> kirana's workspace, <code>createdBy: ravi</code>: the caller, not the server."),
    ("06-a-bad-due-date", "Case 6: a due date the tool cannot read", "<b>Why:</b> a tool error that says what to send."),
    ("07-a-tool-that-does-not-exist", "Case 7: delete_task", "<b>Why:</b> no such tool: a JSON-RPC error."),
    ("08-people-use-the-rest-api", "Case 8: the REST search, same token", "<b>Why:</b> the same rules; case 5's task is there."),
    ("09-another-customer-searches", "Case 9: Sara (studio) searches for diwali", "<b>Why:</b> studio's task only, not kirana's."),
    ("10-no-token", "Case 10: no token", "<b>Why:</b> <code>401</code> before any MCP handling."),
    ("11-a-token-without-task-scopes", "Case 11: a calendar-only token on REST", "<b>Why:</b> <code>403</code>."),
    ("12-a-page-on-another-site", "Case 12: a browser page on another site", "<b>Why:</b> <code>403</code> from the Origin check, even with a valid token."),
]) + code(read("docs/captures/rate-limit.txt").strip(), "text") + examples([
    ("13-an-agent-in-a-loop", "Case 13: the next request", "<b>Why:</b> <code>429</code> with <code>Retry-After</code> until the minute ends."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["The old tools, read-only token", "Reads and writes another customer's workspace, as the server", "<code>theOldToolsLetAReadOnlyAgentReadAndWriteAnotherCustomersWorkspace</code>"],
    ["The API's tools, same token", "No workspace argument; own tasks only; create refused", "<code>theApisToolsActAsTheCallerWithTheCallersScopes</code>"],
    ["tools/list", "Both tools, hints, schema, scope in the description; no tool deletes or takes a workspace", "<code>agentsSeeTheToolsDescribedForAModelAndNoneDeletesOrChoosesAWorkspace</code>"],
    ["Search and create", "Case-insensitive, by status; created by the caller; visible on REST", "<code>anAgentSearchesAndCreatesTasksInItsOwnWorkspace</code>"],
    ["Empty, long, bad date, bad assignee, bad status", "Tool errors with reasons", "<code>badArgumentsAreToolErrorsTheAgentCanRead</code>"],
    ["Unknown tool; REST bad status; unknown path", "JSON-RPC error; <code>400</code>; <code>403</code>", "<code>anUnknownToolIsAnErrorAndRestHas400And403ForBadRequests</code>"],
    ["No token; unknown token", "<code>401</code> with <code>WWW-Authenticate: Bearer</code>", "<code>noTokenOrAnUnknownOneIs401</code>"],
    ["No task scopes", "REST <code>403</code>; tool error", "<code>aTokenWithoutTheScopeIs403OnRestAndAToolErrorOverMcp</code>"],
    ["Two customers", "Neither sees the other's tasks", "<code>oneCustomersAgentNeverSeesAnothersTasks</code>"],
    ["Instructions in a title; a newline; a regex; a foreign Origin", "Stored as text; refused; literal; <code>403</code>", "<code>textFromAnAgentIsStoredAsTextAndAForeignWebPageIsRefused</code>"],
    ["An agent in a loop", "<code>429</code> after the limit; other callers unaffected", "<code>anAgentInALoopIsStoppedWith429AndOthersAreNot</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Exposing every endpoint as a tool with the server's own privileges, so any agent can do anything.</p>
<ul>
<li><strong>The old way.</strong> The internal API, one tool per endpoint, run as the server; the workspace is a tool argument. Ravi's read-only token for kirana lists studio's unreleased product work and creates a task in studio's workspace, recorded as made by <code>taskloom-server</code>.</li>
<li><strong>The API.</strong> The same token: <code>search_tasks</code> has no workspace to choose and returns kirana's tasks only; <code>create_task</code> is refused because the token cannot write.</li>
</ul>
<p>While building, each part was undone once: no scope check in the tools turned 2 tests red; no workspace filter 3; no caller in the MCP context 6; no Origin check 1; no rate limit 1; control characters allowed in titles 1; any assignee 1; REST open to any token 1; titles not trimmed 2; the query used as a pattern 1.</p>
</div>
""" + code(read(T + "AgentToolsTrapTest.java"), "java") + code(read(T + "OldTools.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "TaskTools.java", dwn("The tools.", "<code>@McpTool</code> methods with names, descriptions and hints for a model; each takes the caller from the request context and checks its scope; arguments checked like any input.", "Every endpoint a tool; the server's rights; a workspace chosen by the agent.",
        "<ul><li>An exception in a tool becomes a result with <code>isError: true</code>, which is what MCP asks for: the agent sees why and can try again. Spring AI repeats the message in the text.</li></ul>")),
    (J + "McpConfig.java", dwn("The transport.", "Spring AI's Streamable HTTP transport, with the caller copied into each request's MCP context and an Origin check.", "Tools that cannot tell who called them; any web page driving the endpoint.",
        "<ul><li>Seen in the capture: each event-stream answer ends without HTTP's final chunk, so curl reports exit 18 after receiving the whole message. The MCP SDK's client does not mind; scripts that check curl's exit code do.</li><li>The caller is read in the context extractor, which runs on the request's own thread after the security filters; tools may run elsewhere, so they read it from the context, not from <code>SecurityContextHolder</code>. Found while building.</li></ul>")),
    (J + "SecurityConfig.java", dwn("The doors.", "<code>/mcp</code> needs a known token; <code>GET /tasks</code> needs <code>tasks:read</code>; everything else is closed.", "An endpoint nobody meant to publish.")),
    (J + "BearerTokens.java", "<p>Reads <code>Authorization: Bearer</code> and signs the request in as the token's caller.</p>"),
    (J + "Callers.java", dwn("Tokens.", "Person, workspace and scopes per token; only SHA-256 hashes kept.", "Tokens readable from a copied table.",
        "<ul><li>Shortcut: a fixed table. Real agent access uses OAuth 2.1 as the MCP authorization spec describes (challenge 3).</li></ul>")),
    (J + "RateLimit.java", dwn("The limit.", "Per caller, per clock minute; <code>429</code> with <code>Retry-After</code>.", "An agent in a loop eating the server.",
        "<ul><li>Shortcut: in memory, fixed windows (a burst at a minute's edge can get twice the limit); several servers need a shared store.</li></ul>")),
    (J + "TaskController.java", "<p><code>GET /tasks</code>: the same search for people.</p>"),
    (J + "Tasks.java", "<p>Demo tasks; every method takes the workspace.</p>"),
    (J + "ProblemResponses.java", "<p><code>401</code>, <code>403</code>, <code>429</code> in one problem shape.</p>"),
    ("src/main/resources/application.yaml", "<p>The MCP server's name, protocol and endpoint; the limit; allowed Origins.</p>"),
]
tree = """stations/106-expose-an-api-to-ai-agents-with-mcp/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/taskloom/agents/
│   ├── TaskTools.java   ├── McpConfig.java   ├── SecurityConfig.java   ├── BearerTokens.java   ├── RateLimit.java
│   ├── Callers.java   ├── TaskController.java   ├── Tasks.java   ├── ProblemResponses.java   └── AgentsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/taskloom/agents/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""./mvnw spring-boot:run      # MCP on http://localhost:8080/mcp, REST on /tasks
./mvnw test                 # all """ + str(N_TESTS) + """ tests, with the MCP Java SDK's client""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Point an MCP client that supports Streamable HTTP and custom headers at <code>http://localhost:8080/mcp</code> with <code>Authorization: Bearer demo-kirana-writer</code>, or run the MCP Inspector (<code>npx @modelcontextprotocol/inspector</code>, not used here). Or by hand, as <code>docs/capture.sh</code> does:</p>
""" + code("""curl -i -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \\
  -H 'Authorization: Bearer demo-kirana-reader' \\
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"me","version":"1"}}}' \\
  localhost:8080/mcp""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>401</code> from a client that worked locally", "It does not send your header.", "Configure the client's headers, or its OAuth flow."],
    ["<code>403 Invalid Origin header</code>", "A browser-based client on a site not in <code>allowed-origins</code>.", "Add the site, deliberately."],
    ["<code>Session not found</code>", "The session id is from before a restart.", "Initialize again; sessions live in memory."],
    ["A tool call says \"not signed in\"", "The transport context has no caller: a custom transport without the extractor.", "Keep <code>McpConfig</code>'s transport bean."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">The tools first, then in the order a request travels.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>AgentToolsContractTest</code> ({cnt('AgentToolsContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>AgentToolsTrapTest</code> ({cnt('AgentToolsTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, another user's data, malicious input", f"<code>AgentToolsSecurityTest</code> ({cnt('AgentToolsSecurityTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Rate-limiting agent callers", f"<code>AgentRateLimitTest</code> ({cnt('AgentRateLimitTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">The app runs on a real port and the tests connect with the MCP Java SDK's <code>McpSyncClient</code> over Streamable HTTP, as an agent's client would. Requests a client would never send (no token, a foreign Origin) go out raw.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Spring AI 2.0.2, MCP Java SDK 2.1.0. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "AgentToolsTrapTest.java", "<p>Written first: the old tools against the API's.</p>"),
    (T + "OldTools.java", "<p>The old way, for the trap test only.</p>"),
    (T + "AgentToolsContractTest.java", "<p>The tools, their schemas, their answers and errors; REST.</p>"),
    (T + "AgentToolsSecurityTest.java", "<p>Tokens, scopes, workspaces, hostile input, Origin.</p>"),
    (T + "AgentRateLimitTest.java", "<p>An agent in a loop.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: an MCP client per token.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/taskloom/agents/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=GetTaskChallengeTest</code>.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "One task by its id", "Beginner-friendly", 20,
    "Agents want a single task. Add <code>get_task(id)</code>: read-only, the caller's workspace only; another workspace's id and a missing one give the same tool error, \"no task T-4 in your workspace\".",
    "both tests in <code>GetTaskChallengeTest</code> pass.",
    ["<code>Tasks.find(workspace, id)</code> already filters by workspace.",
     "Same message for \"not yours\" and \"not there\": ids cannot be probed."],
    "challenge/GetTaskChallengeTest.java", ["challenge/solution/TaskTools.java"]) + challenge(2, "A retried create", "Go deeper", 30,
    "Agents retry when a connection drops. Add an optional <code>requestId</code> to <code>create_task</code>: the same id from the same caller returns the task already made; the same id from another caller is unrelated.",
    "both tests in <code>RetriedCreateChallengeTest</code> pass.",
    ["Key the remembered ids by workspace, person and requestId.",
     "<code>computeIfAbsent</code> makes the check and the create one step.",
     "Say in the description what the field is for: the model reads it."],
    "challenge/RetriedCreateChallengeTest.java", ["challenge/solution/TaskTools.java", "challenge/solution/Tasks.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Real tokens for agents</h2>
<p>Replace the demo table. The MCP authorization spec builds on OAuth 2.1 (an IETF draft, not yet an RFC) and OAuth 2.0 Protected Resource Metadata (RFC 9728). Sketch it for Taskloom: who issues the token, how a customer grants an assistant read-only or read-write access to one workspace, how long a token lives, how it is revoked, and what the <code>401</code> must say so a client can start the flow.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old tools, a read-only token, another workspace.</li>
<li>Choose the tools from what agents need, not from the endpoints that exist.</li>
<li>Authenticate at the HTTP layer; carry the caller into tools; check scopes in each tool.</li>
<li>Limit requests; check Origin; validate every argument.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["A few chosen tools, acting as the caller", "Each tool designed and documented.", '<span class="pill ok">Chosen</span>'],
    ["Every endpoint as a tool, run as the server", "Nothing to design; no limits on any agent.", '<span class="pill bad">The trap</span>'],
    ["Trust the client to confirm writes", "Clients differ; scripts skip them.", '<span class="pill bad">Not a control</span>'],
    ["Let agents scrape the web UI", "Breaks every release; agents hold full sessions.", '<span class="pill bad">Replace</span>'],
    ["Stateless MCP (no sessions)", "Simpler to scale; no server-to-client messages.", '<span class="pill warn">Fine for these tools</span>']]) + """
<h2>Database design</h2>
<p>No database in this station: tasks are demo data. Every query takes the workspace; in a database, that becomes a workspace column in every key and every query (station 109 builds that).</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["14. Operations: metric, alert, rollback, runbook, failure drill", "15. Real-world considerations"],
               "What changes when this runs for real.") + """
<h2>Real-world considerations</h2>
<dl class="facts">
<dt>The protocol</dt><dd>MCP is an open protocol with a published specification, not an IETF or W3C standard. This station negotiates the 2025-06-18 revision; the specification is revised regularly, so pin and test the versions you support.</dd>
<dt>Audit</dt><dd>Log each tool call: who, which workspace, which tool, the outcome. Never the arguments' text in full: titles can hold personal data.</dd>
<dt>Tool descriptions are an interface</dt><dd>Models choose tools by their descriptions. Changing one changes agents' behaviour: review and version them like an API.</dd>
<dt>Prompt injection, from this side</dt><dd>Tool results reach a model. A task title written by one person can try to steer another person's agent; keep tools narrow so a steered agent can do little.</dd>
<dt>Sessions</dt><dd>Streamable HTTP sessions here are in memory: behind a load balancer, use sticky sessions or the stateless mode.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is MCP?", "A protocol for AI assistants to discover and call tools, read resources and use prompts from a server, over stdio or Streamable HTTP, with JSON-RPC messages."),
    ("How do you decide which tools to expose?", "From what agents need to do, smallest set first; never the whole internal API. Read-only and write tools separate."),
    ("How does a tool know who is calling?", "Authenticate the HTTP request, then carry the caller into the tool through the request's context. Never accept the user or tenant as a tool argument."),
    ("What do readOnlyHint and destructiveHint do?", "Tell clients how careful to be. They are hints for the client, not security: the server still checks scopes."),
    ("Why validate Origin on an MCP endpoint?", "A web page in the user's browser could otherwise call a local or internal MCP server (DNS rebinding). The specification asks servers to check it."),
    ("How do you test an MCP server?", "With a real MCP client against the running app: list tools, call them with each kind of token, and check errors."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Identity", "Tokens checked.", "Every tool acts as the caller, and you can show where the caller comes from."],
    ["Tools", "Two tools that work.", "Descriptions and schemas a model can use well, errors it can act on."],
    ["Limits", "Scopes.", "Scopes, rate limits, Origin and argument checks, each tested."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("Any token may write",
     "\"The client asks the user before running a write tool, so the server does not need to check\": the read-only hint is advice to the client. A script, another client or an agent told to skip confirmations creates tasks with a read-only token.",
     "<code>theApisToolsActAsTheCallerWithTheCallersScopes</code> fails: the read-only token creates a task; the MCP half of <code>aTokenWithoutTheScopeIs403OnRestAndAToolErrorOverMcp</code> would fail too."),
    ("REST open to any token",
     "\"/tasks only reads, so any signed-in caller may use it\": a calendar-only token was never meant to read tasks; the scope check belongs on every door, not only the MCP one.",
     "<code>aTokenWithoutTheScopeIs403OnRestAndAToolErrorOverMcp</code> fails: the calendar token reads tasks over REST."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate \"simplifies\" the checks: \"clients confirm write tools with the user anyway, and reading is harmless\". Read both files and list every problem before opening the findings.</p>
<p class="path">review/TaskTools.java</p>
""" + code(read("review/TaskTools.java"), "java") + """
<p class="path">review/SecurityConfig.java</p>
""" + code(read("review/SecurityConfig.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">With the official client and a careful user, the flawed version behaves. The server is the only place that sees every client.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
