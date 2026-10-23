"""Station 099 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 99,
    "stack": "Spring Boot 4.1.1 · Java 25 · Server-Sent Events with SseEmitter · Last-Event-ID and retry · timeouts and heartbeats · Spring Security 7 · Awaitility",
    "simulation": "The orders, the kitchen and the rider are simulated: demo orders 1001 to 1099 move on when the kitchen sign-in posts the next status.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No database, no Docker. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tiffino/orders/"
T = "src/test/java/com/tiffino/orders/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Polling", "Asking again and again: \"any news?\"", "A child asking \"are we there yet?\" every minute.", "every 2 s, before"),
    ("Server-Sent Events", "One long HTTP response the server keeps writing to, one event at a time.", "A radio station: you tune in once and listen.", "<code>text/event-stream</code>"),
    ("Event id", "A number on each event; the browser remembers the last one.", "Page numbers in a book.", "<code>id:3</code>"),
    ("Last-Event-ID", "The header a reconnecting browser sends: \"I had up to here\".", "A bookmark.", "<code>Last-Event-ID: 3</code>"),
    ("Timeout", "The server ends a stream after a while; the browser reconnects by itself.", "A phone call that hangs up every five minutes and redials.", "5 minutes"),
    ("Heartbeat", "A comment line sent now and then; writing to a phone that has gone fails.", "\"Are you still there?\" on a quiet call.", "every 15 s"),
]
STORY = [
    ("Are we there yet?", "Tiffino's app asked for the order's status every 2 seconds. At dinner time that was 30,000 requests a second, almost all answered \"same as before\"."),
    ("Streams that never end", "A first move to Server-Sent Events made each stream never time out and kept it in a list. People locked their phones; the streams stayed, one for every phone that had ever opened the screen, until the server ran out."),
    ("The fix", "Each stream has a timeout and leaves the list however it ends. A heartbeat finds phones that have gone. A reconnecting phone says which event it saw last and gets exactly what it missed."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">An open connection is a resource. Every one needs an end: a timeout, a heartbeat, and a place it is removed from.</p>

<h2>What are we building?</h2>
<p>A live stream of one order's status for the customer's app: the current status at once, then every change as it happens.</p>

<h2>An everyday analogy</h2>
<p>A cricket commentary on the radio instead of phoning the ground every two minutes. If the signal drops, you tune back in and the commentator says what you missed since the last over you heard.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Open</strong>: the app opens <code>/orders/{id}/events</code>; the server sends the current status.</li>
<li><strong>Listen</strong>: each change arrives as an event with a number.</li>
<li><strong>Reconnect</strong>: when the stream ends (timeout, tunnel), the browser reconnects with the last number and gets only what it missed.</li>
<li><strong>End</strong>: at delivery the server ends the stream; a reconnect after that gets <code>204</code>: \"stop\".</li>
</ol>

<details class="qa check"><summary>Check yourself: the phone goes through a tunnel while the order goes from COOKING to OUT_FOR_DELIVERY. What does it get when it reconnects?</summary><p>The browser sends <code>Last-Event-ID: 3</code> (COOKING). The server replays event 4, OUT_FOR_DELIVERY, and nothing twice. If event 4 were already too old to keep, it would get a snapshot of the current status instead.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No WebSockets.</strong> The app only listens; SSE is enough (Design).</li>
<li><strong>One server.</strong> Changes are told to this server's streams only (Production).</li>
<li><strong>No real kitchen.</strong> A kitchen sign-in moves the demo orders on.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tiffino</strong> (a fictional food delivery company): the app polls order status every 2 seconds: 30,000 requests a second at dinner time, mostly unchanged.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo rules: streams end after 5 minutes; a heartbeat every 15 s; the last 50 events of each order are kept. Riya owns the odd orders 1001 to 1099, Kabir the even ones; password: the name plus <code>-demo-pass</code>.</p>
<ol class="gwt">
<li><b>Given</b> a customer opening their order's stream, <b>then</b> <code>200</code>, <code>text/event-stream</code>, a <code>retry</code> hint and a snapshot of the current status at once.</li>
<li><b>Given</b> a status change, <b>then</b> every open stream of that order gets it once, in order, with the next id.</li>
<li><b>Given</b> a reconnect with <code>Last-Event-ID</code>, <b>then</b> exactly the missed events; if they are no longer kept, a snapshot; if none were missed, an open stream that waits.</li>
<li><b>Given</b> delivery, <b>then</b> the server ends every stream; a reconnect that saw the last event gets <code>204</code>.</li>
<li><b>Given</b> a client that has gone, <b>then</b> its stream is dropped at the next heartbeat or timeout.</li>
<li><b>Given</b> someone else's or an unknown order, <b>then</b> <code>404</code>; no sign-in <code>401</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Every stream has a timeout and is removed from the list however it ends.</li>
<li>No change can fall between a stream's replay and its joining the list.</li>
<li>Statuses move one step at a time.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Stream events with <code>SseEmitter</code>: ids, names, retry, completion.</li>
<li>Resume with <code>Last-Event-ID</code> without gaps or repeats.</li>
<li>Release streams with timeouts, callbacks and heartbeats.</li>
<li>Test streams on a real port, as a browser reads them.</li>
<li>Choose between polling, SSE and WebSockets.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/orders/{id}/events</code> (<code>Accept: text/event-stream</code>)", "The order's live status. Optional <code>Last-Event-ID</code>."],
    ["<code>POST</code>", "<code>/orders/{id}/status</code>", "Simulated kitchen and rider: move the order to its next status."]]) + """
<h2>The stream</h2>
""" + table(["Line", "Meaning"], [
    ["<code>retry:3000</code>", "Wait 3 s before reconnecting. Sent first: it also gets the headers to the client at once."],
    ["<code>id:3</code>", "This event's number; the browser sends the last one back as <code>Last-Event-ID</code>."],
    ["<code>event:snapshot</code> / <code>event:status</code>", "The current status (first visit, or after a gap), or a change."],
    ["<code>data:{...}</code>", "The event as JSON."],
    ["<code>:keep-alive</code>", "A heartbeat comment, every 15 s; the browser ignores it."]]) + """
<p class="muted">The format is the HTML Living Standard's <a href=\"https://html.spec.whatwg.org/multipage/server-sent-events.html\">server-sent events</a>, which also says that a <code>204</code> tells the browser to stop reconnecting.</p>
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "A stream; a status change"],
    ['<span class="pill ok">204</span>', "Reconnecting to a delivered order whose last event was seen"],
    ['<span class="pill warn">400</span>', "<code>Last-Event-ID</code> not a number; an unknown status"],
    ['<span class="pill warn">401</span>', "No sign-in"],
    ['<span class="pill warn">403</span>', "The kitchen watching, or a customer changing a status"],
    ['<span class="pill warn">404</span>', "No such order, or someone else's"],
    ['<span class="pill warn">409</span>', "Not the next status"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. A stream is read as it arrives (<code>curl -N</code>) and cut off by <code>docs/capture.sh</code> after a few seconds unless the server ends it. <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-riya-watches-order-1001", "Case 1: Riya watches order 1001 while the kitchen works", "<b>Why:</b> the retry hint and a snapshot (event 1), then events 2 and 3 as cases 2 and 3 happen."),
    ("02-the-kitchen-accepts", "Case 2: the kitchen accepts", "<b>Why:</b> event 2, sent to every open stream."),
    ("03-and-starts-cooking", "Case 3: and starts cooking", "<b>Why:</b> event 3."),
    ("04-out-for-delivery-while-riya-is-in-a-tunnel", "Case 4: out for delivery, while nobody watches", "<b>Why:</b> event 4 is kept for whoever reconnects."),
    ("05-riya-reconnects-with-last-event-id", "Case 5: Riya reconnects with Last-Event-ID: 3", "<b>Why:</b> event 4 replayed, nothing twice; then 5 (case 6) and the server ends the stream: curl stopped by itself."),
    ("06-delivered", "Case 6: delivered", "<b>Why:</b> event 5, the last."),
    ("07-reconnecting-after-the-end", "Case 7: reconnecting after the end", "<b>Why:</b> <code>204</code>: the browser stops."),
    ("08-kabir-watches-riyas-order", "Case 8: Kabir watches Riya's order", "<b>Why:</b> <code>404</code>."),
    ("09-skipping-a-step", "Case 9: skipping a step", "<b>Why:</b> <code>409</code>."),
    ("10-no-sign-in", "Case 10: no sign-in", "<b>Why:</b> <code>401</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["The old way, 20 phones that went away", "20 streams kept for ever", "<code>theOldWayKeepsEveryStreamOfEveryClientThatLeft</code>"],
    ["The API, the same 20", "Dropped at the next heartbeats", "<code>theApiLetsGoOfClientsThatLeft</code>"],
    ["A new watcher, then two changes", "Retry hint, snapshot 1, then 2 and 3", "<code>aWatcherGetsTheCurrentStatusThenEachChange</code>"],
    ["Delivery; reconnects after it", "Stream ended; <code>204</code>; or the missed 4 and 5, then the end", "<code>theStreamEndsAtDeliveryAndA204TellsTheBrowserToStop</code>"],
    ["Someone else's order, unknown, no sign-in, the kitchen, a bad id; bad changes", "<code>404</code>, <code>401</code>, <code>403</code>, <code>400</code>; <code>409</code>, <code>400</code>", "<code>unknownOrdersSomeoneElsesAndBadRequests</code>"],
    ["A reconnect after a missed change; one that missed nothing", "Only the missed event; an open stream at once", "<code>reconnectingWithLastEventIdGetsOnlyWhatWasMissed</code>"],
    ["A Last-Event-ID older than the kept events", "A snapshot instead of a gap", "<code>aLastEventIdOlderThanTheKeptEventsGetsASnapshotInstead</code>"],
    ["30 watchers, four changes", "Each gets 1 to 5 once, in order, then the end", "<code>everyWatcherGetsEveryChangeOnceAndInOrder</code>"],
    ["A stream that times out", "Ended by the server; the reconnect misses nothing", "<code>aStreamTimesOutAndTheClientResumesWithoutMissingAnything</code>"],
    ["After the timeout", "Not held any more", "<code>aStreamThatTimedOutIsNoLongerHeld</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Never timing out emitters, leaking connections and threads.</p>
<ul>
<li><strong>The old way.</strong> <code>new SseEmitter(0L)</code> (no timeout) kept in a list. Twenty phones open the stream and go away; four seconds later the list still holds all twenty, and nothing will ever end them. With a sending thread per stream, as many first versions have, those threads stay too.</li>
<li><strong>The API.</strong> The same twenty: the next heartbeats write to them, the writes fail, and each stream ends and leaves the list.</li>
</ul>
<p>While building, each part was undone once: no timeout turned 2 tests red; no completion callback 2; no replay 2; no gap check 1; no <code>204</code> 1; streams not ended at delivery 2; any customer's order 1; no retry hint 1; skipping a status 1; the retry hint not sent first 1 (a reconnect that had missed nothing got no answer at all). Two things turned nothing red and were simplified: removing a stream in the timeout handler and in the heartbeat's failure path (the completion callback already does it). Removing the order's lock turned nothing red either: no test reaches the instant between a replay and joining the list. The lock stays; that case is not proven by a test.</p>
</div>
""" + code(read(T + "LeakingStreamsTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "OrderController.java", dwn("The two endpoints.", "The customer's own order or <code>404</code>; <code>204</code> when there is nothing left to stream; one step at a time for the kitchen.", "Watching someone else's order; statuses out of order.")),
    (J + "OrderStreams.java", dwn("Orders, their events and their streams.",
        "Replay or snapshot on subscribe, then the stream joins the order's list; every change goes to every stream; heartbeats; the end at delivery.",
        "Streams that outlive their clients; events lost or repeated on reconnect.",
        "<ul><li>Subscribe and advance lock the order, so no change falls between a stream's replay and its joining the list.</li><li><code>onCompletion</code> removes a stream however it ended: delivered, timed out, or a failed write (<code>completeWithError</code>).</li><li><code>onTimeout</code> only completes the stream: without it Spring logs an <code>AsyncRequestTimeoutException</code> for every stream that times out.</li><li><code>retry</code> is sent first because it also flushes the headers: a reconnect that missed nothing would otherwise wait with no answer at all until the next event. Found while building.</li><li>Shortcut: sends run on the kitchen's request thread; a slow reader slows it down.</li></ul>")),
    (J + "SecurityConfig.java", "<p>HTTP Basic: customers watch, the kitchen changes statuses.</p>"),
    (J + "ProblemResponses.java", "<p><code>401</code> and <code>403</code> in the problem shape.</p>"),
    ("src/main/resources/application.yaml", "<p>Timeout, retry, heartbeat and history: the demo rules.</p>"),
    (J + "OrdersApplication.java", "<p>Entry point; scheduling on, for the heartbeat.</p>"),
]
tree = """stations/099-live-order-status-with-sse/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tiffino/orders/
│   ├── OrderController.java   ├── OrderStreams.java   ├── SecurityConfig.java
│   └── ProblemResponses.java   └── OrdersApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/tiffino/orders/   (see Tests)
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
""" + code("""./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Watch in one terminal, cook in another:</p>
""" + code("""curl -N -u riya:riya-demo-pass http://localhost:8080/orders/1021/events
curl -u kitchen:kitchen-demo-pass -H 'Content-Type: application/json' -d '{"status":"ACCEPTED"}' http://localhost:8080/orders/1021/status""", "bash") + """
<p>Stop the first command, move the order on, and reconnect with <code>-H 'Last-Event-ID: 2'</code>: only what you missed arrives.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Events arrive in bursts, late", "A proxy buffers the response.", "Turn buffering off for the path (nginx: <code>X-Accel-Buffering: no</code>)."],
    ["The stream ends every 60 s", "A proxy's idle timeout.", "Heartbeats more often than it; the browser reconnects anyway."],
    ["The browser reconnects for ever after delivery", "The server answers 200 with an empty stream.", "Answer <code>204</code>."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>OrderEventsContractTest</code> ({cnt('OrderEventsContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>LeakingStreamsTrapTest</code> ({cnt('LeakingStreamsTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Messaging", "Duplicate delivery, retry and dead letter", f"<code>ReconnectMessagingTest</code> ({cnt('ReconnectMessagingTest')}), <code>StreamTimeoutTest</code> ({cnt('StreamTimeoutTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">For a stream, \"duplicate delivery\" is a reconnect that gets events twice (it does not: only what is after <code>Last-Event-ID</code>); \"retry\" is the browser reconnecting after a timeout without missing anything; the \"dead letter\" cases are events no longer kept, replaced by a snapshot, and clients that have gone, dropped rather than written to again and again.</p>
<p class="muted">The tests use a real port and read each stream line by line, as a browser's EventSource does. Streams end after 10 s here (1 s in <code>StreamTimeoutTest</code>), two events are kept per order, and the tests call the heartbeat themselves.</p>
<p class="muted">Found while building: 30 watchers opened one after another took longer than a short stream timeout, because each sign-in checks a BCrypt password; they are opened at once now. And a test that opened an old-way stream waited for ever: an emitter that has sent nothing has not sent its headers either.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "LeakingStreamsTrapTest.java", "<p>Written first: streams that never end, against the API's.</p>"),
    (T + "OrderEventsContractTest.java", "<p>Snapshot and changes; the end and the 204; bad and foreign requests.</p>"),
    (T + "ReconnectMessagingTest.java", "<p>Reconnects with Last-Event-ID; a gap; 30 watchers.</p>"),
    (T + "StreamTimeoutTest.java", "<p>Streams that time out after 1 s.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: a stream reader, the kitchen helper, the test settings.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tiffino/orders/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=RiderLocationChallengeTest</code>.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Where is the rider?", "Beginner-friendly", 30,
    "While an order is out for delivery, <code>POST /orders/{id}/location {\"lat\": ..., \"lng\": ...}</code> sends the rider's position. Watchers get an event named <code>location</code>, numbered in the same sequence, so a reconnect replays it. Before or after the ride: <code>409</code>; a latitude over 90: <code>400</code>.",
    "both tests in <code>RiderLocationChallengeTest</code> pass.",
    ["Give the event an optional position; name it by whether it has one.",
     "<code>@DecimalMin</code> and <code>@DecimalMax</code> on the request's numbers."],
    "challenge/RiderLocationChallengeTest.java", ["challenge/solution/OrderStreams.java", "challenge/solution/OrderController.java", "challenge/solution/SecurityConfig.java"]) + challenge(2, "A limit on open streams", "Go deeper", 35,
    "A customer may hold a limited number of open streams (<code>tiffino.sse.max-streams-per-customer</code>, 50 by default, 3 in the test). An app stuck in a reconnect loop gets <code>429</code> with <code>Retry-After</code>; when one of its streams ends, it may open another.",
    "the test in <code>StreamLimitChallengeTest</code> passes.",
    ["Count when a stream joins a list, and uncount in the same completion callback that removes it.",
     "Check and count under one lock, or two requests could both take the last place."],
    "challenge/StreamLimitChallengeTest.java", ["challenge/solution/OrderStreams.java", "challenge/solution/OrderController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Ten servers, one kitchen</h2>
<p>Tiffino runs ten servers; a phone's stream is on one of them, and the kitchen's update reaches another. Design how every server learns about the change (Valkey pub/sub, Kafka, or a database's LISTEN/NOTIFY), where the event history lives so any server can replay it, and how many streams one server can hold. Then argue: would WebSockets or plain polling with <code>ETag</code>s be better for this screen?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: streams that never end, and clients that leave.</li>
<li>Number every event per order and keep the last few.</li>
<li>Subscribe: retry hint, replay or snapshot, then join the list, all under the order's lock.</li>
<li>End streams: timeout, completion callback, heartbeat, delivery and <code>204</code>.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["SSE with ids, timeouts and heartbeats", "An open connection per watcher; one-way only.", '<span class="pill ok">Chosen</span>'],
    ["Polling every 2 s", "30,000 requests a second, nearly all \"no change\".", '<span class="pill bad">The problem</span>'],
    ["SSE that never times out", "Connections and memory held for every client that ever left.", '<span class="pill bad">The trap</span>'],
    ["Polling with <code>ETag</code> and a longer interval", "Cheaper per request, still late and still many.", '<span class="pill warn">Fine for slow-changing data</span>'],
    ["WebSockets", "Two-way; more to run (upgrades, proxies, own reconnect logic).", '<span class="pill warn">When the client also talks</span>']]) + """
<h2>Database design</h2>
<p>No database: orders and their last events are in memory. With several servers, the history moves to a shared store and changes go through a broker (challenge 3).</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Connections</dt><dd>Each watcher holds a connection (not a thread: servlet async releases it). Size the server's connection limit and file descriptors for the busiest hour.</dd>
<dt>Proxies</dt><dd>Turn response buffering off for the stream's path and keep heartbeats shorter than every idle timeout on the way.</dd>
<dt>HTTP/1.1</dt><dd>Browsers allow about six connections per host over HTTP/1.1; streams count. HTTP/2 removes that limit.</dd>
<dt>Several servers</dt><dd>Publish changes through a broker so every server can tell its own watchers; keep the history somewhere shared.</dd>
<dt>Slow readers</dt><dd>Sends here run on the caller's thread; with many watchers, hand them to an executor with a bounded queue and drop readers that fall behind.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("When do you choose SSE over polling and WebSockets?", "SSE when the server pushes and the client only listens: one HTTP response, automatic reconnects, event ids. Polling for rare changes; WebSockets when the client talks back too."),
    ("How does a client resume after a dropped connection?", "The browser reconnects after the retry delay and sends Last-Event-ID; the server replays what came after it."),
    ("How do you stop leaking SSE connections?", "A timeout on every emitter, removal in a completion callback, and heartbeats that make writes to gone clients fail."),
    ("How does the server tell the browser to stop reconnecting?", "Answer 204 No Content."),
    ("What if the client's last event is no longer kept?", "Send a snapshot of the current state instead of pretending nothing was missed."),
    ("How do you test SSE?", "On a real port, reading the stream line by line, with Awaitility for each expected event."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Streams", "Events reach the app.", "Ids, retry, snapshot, 204 at the end."],
    ["Resources", "A timeout.", "Removal however a stream ends, and heartbeats; you can say what a stream costs."],
    ["Testing", "One stream test.", "Reconnects, gaps, timeouts and many watchers on a real port."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("No timeout",
     "\"So phones never have to reconnect\": and a phone that leaves without a word is never noticed unless something writes to it. Reconnects are cheap and built into the browser; a stream with no end is a connection held for ever.",
     "<code>aStreamTimesOutAndTheClientResumesWithoutMissingAnything</code> and <code>aStreamThatTimedOutIsNoLongerHeld</code> fail."),
    ("Streams leave the list only on a failed write",
     "\"Streams leave the list when a write to them fails\": but in this version nothing removes them, even then. A failed heartbeat ends the stream, and the ended stream stays in the list for ever; delivered orders' streams too.",
     "<code>theApiLetsGoOfClientsThatLeft</code> fails: the twenty streams stay."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate \"simplifies the streams\": no timeout, \"so phones never have to reconnect\", and no completion callback, \"since streams leave the list when a write to them fails\". Read the file and list every problem before opening the findings.</p>
<p class="path">review/OrderStreams.java</p>
""" + code(read("review/OrderStreams.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">Every event still reaches every phone that is watching. The flaw is in the phones that stopped watching: invisible in a demo, a slow leak at dinner time.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
