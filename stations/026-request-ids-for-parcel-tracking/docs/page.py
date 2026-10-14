"""Station 026 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 26,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · OncePerRequestFilter · SLF4J MDC · Micrometer · Actuator · MockMvc",
    "simulation": "Shipments are demo records in memory; no parcel moves. The store outage is simulated by a switch that is off unless a drill turns it on.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/dakroute/tracking/"
T = "src/test/java/com/dakroute/tracking/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# Real log lines from the running app during the captures (docs/captures/app-log.txt), for the ids the captures sent.
LOG_LINES = read("docs/captures/app-log.txt").strip().splitlines()
assert LOG_LINES, "docs/captures/app-log.txt is empty"

# ---------- Level 1: Understand ----------
TERMS = [
    ("Request id", "A label for one request, the same in every log line it writes.", "A token number at a hospital: every desk writes it on your file.", "<code>X-Request-Id</code>"),
    ("MDC", "Mapped Diagnostic Context: values the logger adds to every line on this thread.", "A name badge the logger reads before writing anything.", "<code>MDC.put(\"requestId\", id)</code>"),
    ("Filter", "Code that runs around every request, before Spring decides which controller handles it.", "Security at the building door, not at one office.", "<code>RequestIdFilter</code>"),
    ("Interceptor", "Code that runs around a controller call, after Spring picked the controller.", "A check at one office door.", "Not used: it misses requests no controller handles"),
    ("Log level", "How important a line is: DEBUG, INFO, WARN, ERROR.", "A note, a message, a warning, an alarm.", "INFO per lookup, ERROR when the store fails"),
    ("Metric", "A number that changes over time, counted by the app.", "The counter at a toll booth.", "<code>tracking.lookups{outcome}</code>"),
]
STORY = [
    ("A customer's tracking page fails", "She sends support a screenshot. Support opens the logs: 40,000 lines a minute, from hundreds of customers, all mixed together."),
    ("The first fix makes it worse", "Someone adds a request id to the logs, but never clears it. Server threads serve one request after another, so the next customer's lines carry the first customer's id. Support now finds the wrong person's logs."),
    ("The fix", "One filter gives every request its own id, puts it on every log line, returns it in a header and in error bodies, and removes it when the request ends, whatever happened."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Whatever you put on a shared thread, take it off in a <code>finally</code>.</p>

<h2>What are we building?</h2>
<p><code>GET /shipments/{awb}</code> returns a parcel's tracking. Around it: a request id on every response and every log line, a metric of lookups by outcome, and a drill that proves support can find a failure from a screenshot.</p>

<h2>An everyday analogy</h2>
<p>A hospital gives each patient a token at the door. Every desk writes the token on its notes, and the token is taken back when the patient leaves, so the next patient does not walk around with it.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>At the door</strong>: take the caller's <code>X-Request-Id</code> if it is safe, or make one.</li>
<li><strong>On the badge</strong>: put it in the MDC; every log line of the request carries it.</li>
<li><strong>On the way out</strong>: return it in the header, and in any error body.</li>
<li><strong>At the end, always</strong>: remove it from the MDC, even when the request failed.</li>
</ol>

<details class="qa check"><summary>Check yourself: why must the id be removed if the next request sets its own anyway?</summary><p>Not every request sets one: the old code only did when the caller sent an id. And work outside a request on that thread (a scheduled task, a log line after an error) would carry a stranger's id too.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>Not distributed tracing.</strong> One service; tracing across services is discussed in Design.</li>
<li><strong>No log storage.</strong> Logs go to the console; searching them is the log platform's job.</li>
<li><strong>No real tracking store.</strong> Demo records, with a simulated outage for drills.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Dakroute</strong> (a fictional logistics platform) logs 40,000 lines a minute. When a customer's tracking request fails, support cannot find its lines. A first attempt at request ids filed some customers' lines under other customers' ids, which is worse than no id.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a request with <code>X-Request-Id: app-7f3a9c21</code>, <b>then</b> the response carries the same header, and every log line of the request shows <code>[rid:app-7f3a9c21]</code>.</li>
<li><b>Given</b> no id, or an unsafe one (spaces, too short or long, control characters), <b>then</b> the server makes a UUID and returns it.</li>
<li><b>Given</b> two requests on one thread, <b>then</b> each logs only its own id, and nothing is left in the MDC afterwards, even after a failure.</li>
<li><b>Given</b> an unknown shipment or a bad AWB, <b>then</b> <code>404</code> or <code>400</code> with <code>requestId</code> in the body.</li>
<li><b>Given</b> a path no controller handles, <b>then</b> the <code>404</code> still carries <code>X-Request-Id</code>.</li>
<li><b>Given</b> the store is down, <b>then</b> <code>503</code> with <code>Retry-After: 60</code>, one ERROR line with the id, and the error metric goes up.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Accepted ids: 8 to 64 letters, digits or <code>-</code>. Anything else is replaced and never logged.</li>
<li>The filter runs first, for every request; the MDC entry is removed in <code>finally</code>.</li>
<li>Log levels: DEBUG detail, INFO per lookup, ERROR when the store fails.</li>
<li><code>tracking.lookups</code> counts lookups by outcome: found, not_found, invalid, error.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Write a <code>OncePerRequestFilter</code>, and explain filter versus <code>HandlerInterceptor</code>.</li>
<li>Use the MDC safely on pooled threads.</li>
<li>Choose log levels, and treat request headers as untrusted input to logs.</li>
<li>Publish a metric and run a controlled failure drill.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/shipments/{awb}</code>", "A parcel's status and events."],
    ["<code>GET</code>", "<code>/actuator/metrics/tracking.lookups</code>", "The lookup counter, by <code>outcome</code> tag (for monitoring)."]]) + """
<h2>Headers</h2>
""" + table(["Header", "Rule"], [
    ["<code>X-Request-Id</code> (request)", "Optional. 8 to 64 letters, digits or <code>-</code>; anything else is replaced."],
    ["<code>X-Request-Id</code> (response)", "Always present: the caller's id, or the one the server made."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "The shipment"],
    ['<span class="pill warn">400</span>', "Not an AWB (10 to 20 letters and digits)"],
    ['<span class="pill warn">404</span>', "No such shipment, or no such path"],
    ['<span class="pill bad">503</span>', "The tracking store is down; <code>Retry-After: 60</code>"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-with-the-apps-request-id", "Case 1: the app sends its id", "<b>Why:</b> the same id comes back in <code>X-Request-Id</code>; the app shows it on its error screens."),
    ("02-without-an-id", "Case 2: no id", "<b>Why:</b> the server makes a UUID and returns it."),
    ("03-unknown-shipment", "Case 3: an unknown shipment", "<b>Why:</b> <code>404</code>, and the body names the request id, so a screenshot is enough for support."),
    ("04-an-unsafe-id-is-replaced", "Case 4: an id with spaces and fake log text", "<b>Why:</b> replaced by a UUID; the caller's text never reaches a log line."),
    ("05-a-path-no-controller-handles", "Case 5: a typo in the path", "<b>Why:</b> no controller ran, but the filter did: the <code>404</code> carries the id."),
    ("06-the-metric-the-alert-reads", "Case 6: the metric", "<b>Why:</b> lookups counted by outcome; the alert in the Production tab reads this counter."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Caller's id, lower-case AWB", "200, same id back", "<code>aShipmentComesBackWithTheCallersRequestId</code>"],
    ["No id", "A UUID", "<code>withoutAnIdTheServerMakesOne</code>"],
    ["Unknown shipment", "<code>404</code> with requestId", "<code>anUnknownShipmentIs404AndTheBodyNamesTheRequestId</code>"],
    ["Bad AWB", "<code>400</code> with requestId", "<code>aBadAwbIs400WithItsRequestId</code>"],
    ["A path no controller handles", "<code>404</code> with the header", "<code>evenAPathNoControllerHandlesGetsAnId</code>"],
    ["Short, spaced, 65 characters, a tab and fake log text", "Replaced", "<code>anUnsafeIdIsReplacedNotEchoed</code>"],
    ["A lookup", "INFO line with <code>[rid:…]</code>", "<code>theLookupsLogLineCarriesTheRequestId</code>"],
    ["Forged log text in the header", "Never in the log", "<code>forgedLogTextInTheHeaderNeverReachesTheLog</code>"],
    ["Two requests on one thread; a failing handler", "Own ids; MDC empty after", "<code>LeakedRequestIdTrapTest</code>"],
    ["Store outage; recovery; the metric endpoint", "503 with trail; 200; counter readable", "<code>OperationsDrillTest</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Setting the MDC without clearing it, so the next request on the thread logs the wrong id.</p>
<p>The MDC is per thread, and a server reuses threads. The first test runs the old filter for two requests on one thread: the second, sent without an id, logs under the first one's. The second test runs the real filter the same way: each request has its own id, and nothing is left behind. The third makes the handler throw: the id is still removed. While building, removing the <code>MDC.remove</code> turned 2 tests red, accepting any incoming id turned 2 red, and dropping <code>requestId</code> from error bodies turned 3 red.</p>
</div>
""" + code(read(T + "LeakedRequestIdTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "RequestIdFilter.java", dwn("Takes or makes the id, puts it in the MDC and the response header, and removes it at the end.",
        "A filter at the highest precedence: it wraps everything, including requests no controller handles.",
        "The trap: <code>MDC.put</code> with no <code>finally</code>.",
        "<ul><li>Only <code>[A-Za-z0-9-]{8,64}</code> is accepted: a header is attacker input, and the log is not a place for it.</li><li><code>MDC.remove</code> in <code>finally</code> runs even when the handler throws.</li></ul>")),
    (J + "ShipmentController.java", dwn("The lookup, its log lines at the right levels, the metric, and problems that carry the request id.",
        "One <code>count(outcome)</code> per path through the method, so the metric adds up to all lookups.",
        "A 500 with a stack trace when the store fails.")),
    (J + "Shipments.java", "<p>Demo shipments in memory, and the outage switch used by the failure drill.</p>"),
    ("src/main/resources/application.yaml", "<p>The log pattern with <code>[rid:…]</code>, the actuator endpoints, and the drill switch (off).</p>"),
    (J + "TrackingApplication.java", "<p>Standard Spring Boot entry point.</p>"),
]
tree = """stations/026-request-ids-for-parcel-tracking/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/dakroute/tracking/
│   ├── RequestIdFilter.java   ├── ShipmentController.java
│   ├── Shipments.java         └── TrackingApplication.java
├── src/main/resources/application.yaml   log pattern, actuator, drill switch
├── src/test/java/com/dakroute/tracking/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""],
    ["Docker", "Not needed for this station", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Send a request with your own id, then look for it in the app's console.</p>
""" + code("""curl -i -H "X-Request-Id: my-first-request" http://localhost:8080/shipments/DKR100000001IN
# in the app's console:  INFO [rid:my-first-request] ... Tracking lookup for DKR100000001IN: OUT_FOR_DELIVERY""", "bash") + """
<h2>What the log lines look like</h2>
<p class="muted">The running app's own console lines while the examples above were captured (<code>docs/captures/app-log.txt</code>; timestamps and process id removed). Case 1 and case 3, each under its request id.</p>
<pre class="console">""" + e("\n".join(LOG_LINES)) + """</pre>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>[rid:-]</code> on a line", "Logged outside a request, or on another thread.", "Expected at startup; for worker threads, see challenge 2."],
    ["A different id than you sent", "Yours was not 8 to 64 letters, digits or dashes.", "Send a UUID or similar."],
    ["<code>503</code> on every lookup", "The drill switch is on.", "Restart without <code>--dakroute.tracking.simulate-outage=true</code>."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>ShipmentContractTest</code> ({cnt('ShipmentContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>LeakedRequestIdTrapTest</code> ({cnt('LeakedRequestIdTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Operations", "A controlled failure drill", f"<code>OperationsDrillTest</code> ({cnt('OperationsDrillTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Log lines carry the id; forged text never does", f"<code>RequestIdLoggingTest</code> ({cnt('RequestIdLoggingTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "LeakedRequestIdTrapTest.java", "<p>Written first: the old filter on one thread, the real filter, and a failing handler.</p>"),
    (T + "ShipmentContractTest.java", "<p>The id on every response and error body, and unsafe ids replaced.</p>"),
    (T + "RequestIdLoggingTest.java", "<p>The real console output, captured: the id on the line, forged text absent.</p>"),
    (T + "OperationsDrillTest.java", "<p>The drill: outage, the trail it leaves (503, ERROR line, metric), and recovery.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app through MockMvc, filters included.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/dakroute/tracking/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=AccessLogChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "An access line per request", "Beginner-friendly", 20,
    "Log one INFO line when each request ends: method, path, status and duration, under the request's id. Requests that log nothing else, and paths no controller handles, get one too.",
    "the test in <code>AccessLogChallengeTest</code> passes.",
    ["The filter already wraps every request: time it there.",
     "Log in the <code>finally</code>, before the MDC entry is removed."],
    "challenge/AccessLogChallengeTest.java", ["challenge/solution/RequestIdFilter.java"]) + challenge(2, "Keep the id on another thread", "Go deeper", 35,
    "Add <code>GET /shipments/{awb}/eta</code>, which works out the estimate on a worker thread and logs it. The MDC belongs to one thread, so the worker's line has no id. Make the executor carry it across.",
    "the test in <code>AsyncRequestIdChallengeTest</code> passes. Without the fix the line shows <code>[rid:-]</code>.",
    ["A <code>TaskDecorator</code> on a <code>ThreadPoolTaskExecutor</code> runs around every task.",
     "Copy with <code>MDC.getCopyOfContextMap()</code> on the caller's thread; <code>setContextMap</code> and <code>clear</code> on the worker."],
    "challenge/AsyncRequestIdChallengeTest.java", ["challenge/solution/AsyncConfig.java", "challenge/solution/ShipmentController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>One id across five services</h2>
<p>Tracking calls the courier partner, the address service and the notification service. How would one customer's request be followed through all of them? Compare passing <code>X-Request-Id</code> along with the W3C Trace Context <code>traceparent</code> header and a tracing system. What does each service need to do, and what happens at a service that does not?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: two requests on one thread through the old filter.</li>
<li>Write the filter with <code>finally</code>; test it the same way, and with a failing handler.</li>
<li>Add the id to the log pattern and to error bodies; capture real log output in a test.</li>
<li>Add the metric and the outage switch; write the drill as a test.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["<code>OncePerRequestFilter</code> at the highest precedence", "A filter class.", '<span class="pill ok">Chosen</span>'],
    ["<code>HandlerInterceptor</code>", "Runs only when a controller is chosen: unknown paths and early errors have no id.", '<span class="pill warn">Misses requests</span>'],
    ["Set the MDC, never clear it", "The next request on the thread logs the wrong id.", '<span class="pill bad">The trap</span>'],
    ["Trust any incoming id", "Callers write into your logs: fake lines, huge values.", '<span class="pill bad">Unsafe</span>'],
    ["Micrometer Tracing (trace and span ids)", "A dependency and a tracing backend; ids across services.", '<span class="pill warn">For many services</span>']]) + """
<h2>Database design</h2>
<p>None in this station. Logs and metrics are not stored in the application's database: they go to a log platform and a metrics system, which keep them for a set time.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["14. Operations: metric, alert, rollback, runbook, failure drill", "15. Real-world considerations"],
               "An Operations station: everything someone on call needs, and a drill to prove it works.") + """
<h2>Operations</h2>
<dl class="facts">
<dt>Metric</dt><dd><code>tracking.lookups</code>, tagged <code>outcome</code> = found, not_found, invalid, error. Error rate = error ÷ all lookups.</dd>
<dt>Alert</dt><dd>Page the on-call engineer when the error rate is above 5% for 5 minutes (thresholds are a starting point; tune them on real traffic). A rise in not_found alone is not an outage: it often follows a partner's bad data.</dd>
<dt>Rollback</dt><dd>The filter and metric hold no data, so rolling back is redeploying the previous version. If a release breaks request ids (missing headers, wrong ids in logs), roll back first and investigate after.</dd>
</dl>
<h2>Runbook: "a customer's tracking failed"</h2>
<ol class="steps">
<li>Ask for the screenshot or the error body: it shows <code>requestId</code>.</li>
<li>Search the logs for <code>[rid:&lt;that id&gt;]</code>. Every line of that request appears, in order.</li>
<li>An ERROR line names the failure (for example, the store did not answer). Check <code>tracking.lookups{outcome=error}</code>: one customer, or everyone?</li>
<li>Everyone: follow the store's own runbook; tell customers to retry (the response already says <code>Retry-After: 60</code>). One customer: check the AWB and the shipment's data.</li>
</ol>
<h2>Failure drill</h2>
<p>A controlled failure drill, run before you need the runbook for real:</p>
<ol class="steps">
<li>Start a test instance with <code>--dakroute.tracking.simulate-outage=true</code>.</li>
<li>Send a lookup with <code>X-Request-Id: drill-001</code>: expect <code>503</code>, <code>Retry-After: 60</code> and <code>requestId: drill-001</code> in the body.</li>
<li>Follow the runbook from that id alone: find the ERROR line, and see <code>outcome=error</code> rise in <code>/actuator/metrics/tracking.lookups</code>.</li>
<li>Restart without the switch; check lookups answer <code>200</code> again.</li>
</ol>
<p class="muted">The same drill runs on every build as <code>OperationsDrillTest</code> (""" + str(cnt("OperationsDrillTest")) + """ tests, passing in <code>docs/test-run.txt</code>).</p>
<h2>Real-world considerations</h2>
<dl class="facts">
<dt>Privacy</dt><dd>Request ids are opaque labels. Never use a phone number or an email as one: it would sit in every log line.</dd>
<dt>Threads</dt><dd>Virtual threads, async executors and reactive code do not carry the MDC on their own (challenge 2).</dd>
<dt>Volume</dt><dd>DEBUG lines are off in production. INFO per lookup at 40,000 lines a minute costs storage: keep only what support uses.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is the MDC?", "A per-thread map of values that the logging pattern can print on every line, such as a request id. It belongs to the thread, not the request."),
    ("Why clear the MDC in finally?", "Servers reuse threads. Anything left in the MDC is printed on the next request's lines, and finally runs even when the request fails."),
    ("Filter or HandlerInterceptor?", "A filter wraps the whole request, before Spring chooses a controller. An interceptor runs around controller calls only, so unknown paths and some errors never reach it."),
    ("Should you trust the incoming X-Request-Id?", "Only if it matches a strict pattern. It is caller input going into your logs: it can forge lines or be huge."),
    ("Which log level for what?", "DEBUG: details for debugging. INFO: normal events. WARN: something a person should look at soon. ERROR: a failure that needs action now."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can explain why the trap only shows on a reused thread."],
    ["Logging", "Every line of a request carries its id.", "You can keep it on worker threads too."],
    ["Operations", "A metric, an alert and a runbook.", "You ran the failure drill end to end."],
    ["Explanation", "Filter versus interceptor.", "Request ids versus distributed tracing."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any logging change:</p>
<ul class="rules">
<li>Is everything put in the MDC removed in a <code>finally</code>?</li>
<li>Does every request get an id, including errors and unknown paths?</li>
<li>Can a caller write arbitrary text into the logs?</li>
<li>Does every error body carry something support can search for?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
