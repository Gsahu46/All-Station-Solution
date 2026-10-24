"""Station 101 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 101,
    "stack": "Spring Boot 4.1.1 · Java 25 · RabbitMQ 4.1 · Spring AMQP 4.1 (@RabbitListener, publisher confirms, retry, dead-letter exchange) · Testcontainers · Awaitility",
    "simulation": "The lab is simulated: report LR-n has n pages, each taking a few milliseconds; LR-0013 always fails and LR-0042 fails once. The PDFs are real minimal files, kept on the local disk instead of object storage.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (RabbitMQ for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/mediqo/reports/"
T = "src/test/java/com/mediqo/reports/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Message broker", "A server that holds messages until a worker takes them.", "A post office.", "RabbitMQ"),
    ("Exchange and routing key", "Where a message is sent, and the label that decides which queue gets it.", "The sorting desk and the PIN code.", "<code>lab-reports</code>, <code>render</code>"),
    ("Queue", "Messages waiting, in order, for a worker.", "A pile of letters for one postman.", "<code>report-render</code>"),
    ("Acknowledgement", "The worker telling the broker \"done, you can delete it\".", "The signature on a delivery slip.", "after the listener returns"),
    ("Prefetch", "How many messages a worker may hold at once before acknowledging.", "Letters a postman carries per round.", "1"),
    ("Dead-letter queue", "Where messages go that no worker could handle, for a person.", "The returned-letters office.", "<code>report-render.dlq</code>"),
]
STORY = [
    ("Reports in the request", "At Mediqo, the doctor's \"get report\" click made the PDF in the request itself. At peak, requests waited; a server restart in the middle lost the reports being made."),
    ("A queue that forgets", "A queue fixed the waiting. But the workers used auto-ack: RabbitMQ treated a report as done the moment it handed it to a worker. A worker that restarted mid-report took that report with it."),
    ("The fix", "The broker confirms each message before the API says \"accepted\". A worker acknowledges only after the PDF is saved; if it dies, the broker gives the report to another worker. Reports that fail three times wait in a dead-letter queue with the reason."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A message is safe only until someone says it is done. Say it after the work, never before.</p>

<h2>What are we building?</h2>
<p>A render queue for lab reports: the API puts a request on a durable queue, workers turn it into a PDF, and nothing is lost when a worker dies.</p>

<h2>An everyday analogy</h2>
<p>A courier signs for a parcel only when it is in the customer's hands. If the courier's van breaks down, the depot still has the parcel on its books and sends another courier. Parcels that cannot be delivered after three tries go to the returns office with a note.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Send</strong>: the API publishes the request and waits for the broker's confirmation, then answers <code>202</code>.</li>
<li><strong>Take</strong>: a worker takes one message at a time (prefetch 1).</li>
<li><strong>Finish</strong>: the worker saves the PDF; only then is the message acknowledged and deleted.</li>
<li><strong>Give up well</strong>: after three failed tries, the message goes to the dead-letter queue and the report shows why.</li>
</ol>

<details class="qa check"><summary>Check yourself: the worker saves the PDF, then dies before acknowledging. What happens?</summary><p>The broker gives the message to another worker, marked as redelivered. That worker finds the PDF already there and skips it. Delivery is at least once, so workers must be safe to repeat.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real lab system.</strong> Rendering is simulated; the PDFs are minimal.</li>
<li><strong>One machine's disk.</strong> Reports would go to object storage with several servers.</li>
<li><strong>No sign-in.</strong> Access control is another station's topic.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Mediqo</strong> (a fictional diagnostics lab): lab report PDFs are generated in the request thread; at peak, reports are lost when a server restarts.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo rules: reports LR-0001 to LR-0500; 3 tries, 1 s then 2 s apart; one report per worker at a time; two workers.</p>
<ol class="gwt">
<li><b>Given</b> a known report, <b>then</b> <code>202</code> only after the broker has confirmed the message, and later <code>READY</code> with a PDF.</li>
<li><b>Given</b> the broker unreachable or refusing the message, <b>then</b> <code>503</code>, and asking again tries again.</li>
<li><b>Given</b> the same report asked for again, <b>then</b> <code>200</code> with its state and no second render.</li>
<li><b>Given</b> a worker that dies mid-report, <b>then</b> another worker renders it; nothing is lost.</li>
<li><b>Given</b> a passing failure, <b>then</b> a retry renders it; a lasting one ends <code>FAILED</code> with the reason, its message in the dead-letter queue.</li>
<li><b>Given</b> a slow report, <b>then</b> the reports after it go to the other worker.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Durable queues and persistent messages.</li>
<li>Acknowledge after the work, not before.</li>
<li>Every message ends rendered, or parked with a reason: never silently gone, never retried for ever.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Declare exchanges, queues, bindings and a dead-letter exchange.</li>
<li>Choose acknowledgement mode and prefetch, and explain Spring's \"auto\" against RabbitMQ's autoAck.</li>
<li>Use publisher confirms, listener retry and a message recoverer.</li>
<li>Make a consumer idempotent, and test crashes against a real broker.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its RabbitMQ, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/lab-reports/{id}/render</code>", "Queue a render; <code>202</code> once the broker has it."],
    ["<code>GET</code>", "<code>/lab-reports/{id}</code>", "QUEUED, READY (with the PDF's link) or FAILED (with the reason)."],
    ["<code>GET</code>", "<code>/lab-reports/{id}/pdf</code>", "The PDF."],
    ["worker", "queue <code>report-render</code>", "Renders; acknowledges after the PDF is saved."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">202</span>', "Render queued and confirmed by the broker"],
    ['<span class="pill ok">200</span>', "Asked again: its state, nothing new sent; a read"],
    ['<span class="pill warn">400</span>', "Not a report id (LR-0000 form)"],
    ['<span class="pill warn">404</span>', "No such report; never requested; no PDF yet"],
    ['<span class="pill warn">503</span>', "The broker is unreachable or refused the message"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, with the configured retry waits (1 s, 2 s). <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-render-a-report", "Case 1: render LR-0007", "<b>Why:</b> <code>202</code> after the broker's confirmation."),
    ("02-a-worker-rendered-it", "Case 2: a moment later", "<b>Why:</b> a worker rendered it."),
]) + """
<p class="muted">The PDF, read by poppler's <code>pdfinfo</code>, an independent reader:</p>
""" + code(read("docs/captures/pdf.txt").strip(), "text") + examples([
    ("03-asked-again", "Case 3: asked again", "<b>Why:</b> <code>200</code>, ready: no second message."),
    ("04-a-busy-lab-system", "Case 4: LR-0042, whose lab system is busy once", "<b>Why:</b> accepted like any other."),
    ("05-ready-after-a-retry", "Case 5: ready after a retry", "<b>Why:</b> the first try failed; the second, 1 s later, worked."),
    ("06-a-damaged-scan", "Case 6: LR-0013, a damaged scan", "<b>Why:</b> accepted; the worker will fail."),
    ("07-failed-after-three-tries", "Case 7: failed after three tries", "<b>Why:</b> the reason, recorded by the recoverer before it dead-lettered the message."),
]) + """
<p class="muted">The parked message, read through the management API without taking it off the dead-letter queue. <code>x-death</code> is written by the broker:</p>
""" + code(read("docs/captures/dead-letter.txt").strip(), "text") + examples([
    ("08-no-such-report", "Case 8: no such report", "<b>Why:</b> <code>404</code>, nothing sent."),
    ("09-not-a-report-id", "Case 9: not a report id", "<b>Why:</b> <code>400</code>."),
]) + """
<h2>The queues</h2>
<p class="muted">At the end, from <code>rabbitmqctl list_queues</code> (the management API's counts can be a few seconds old):</p>
""" + code(read("docs/captures/queues.txt").strip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Auto-ack, the worker dies before rendering", "The queue is empty: the report is gone", "<code>withAutoAckTheMessageIsGoneWithTheWorker</code>"],
    ["Acknowledge after the work, the same death", "The message is back, flagged redelivered", "<code>withAcknowledgementsAfterTheWorkTheBrokerGivesItToTheNextWorker</code>"],
    ["A report", "<code>202</code>, then READY and a 7-page PDF", "<code>aReportIsQueuedThenRenderedByAWorker</code>"],
    ["Unknown, bad ids, never requested", "<code>404</code>, <code>400</code>, nothing sent", "<code>unknownReportsAre404AndBadIds400</code>"],
    ["A slow report first, two quick ones after", "The quick ones are done while the slow one renders", "<code>aSlowReportDoesNotHoldUpTheOnesBehindIt</code>"],
    ["The broker refuses the message (exchange missing)", "<code>503</code>, then fine once it is back", "<code>aMessageTheBrokerDidNotTakeIs503</code>"],
    ["No broker at all", "<code>503</code>, twice: nothing marked as queued", "<code>withoutTheBrokerItIs503AndTheRequestCanBeTriedAgain</code>"],
    ["A failure that passes", "Retried, rendered once, nothing parked", "<code>aBusyLabSystemIsRetriedAndTheReportIsRendered</code>"],
    ["A failure that lasts", "FAILED with the reason; parked with <code>x-death</code>", "<code>aDamagedReportEndsInTheDeadLetterQueueWithItsReason</code>"],
    ["The worker's connection cut mid-render", "Redelivered; rendered once by the next worker", "<code>aWorkerCutOffMidRenderLosesNothing</code>"],
    ["The same request twice", "One message, one render", "<code>theSameRequestTwiceIsOneMessageAndOneRender</code>"],
    ["A repeated message for a rendered report", "Acknowledged and skipped", "<code>aRepeatedMessageForARenderedReportIsSkipped</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Auto-ack, so messages are lost when a worker crashes.</p>
<ul>
<li><strong>Auto-ack.</strong> With the plain RabbitMQ client: a worker consumes with <code>autoAck=true</code>, takes the message, and its channel closes before it renders. The queue is empty. The report will never be made, and nothing records that.</li>
<li><strong>Acknowledge after the work.</strong> The same death with <code>autoAck=false</code>: the message is back in the queue, and the next worker sees it marked redelivered.</li>
<li><strong>The app.</strong> Spring's <code>acknowledge-mode: auto</code> acknowledges after the listener returns. In <code>aWorkerCutOffMidRenderLosesNothing</code> the broker closes the app's connection in the middle of a 500-page report: the report is still rendered, once.</li>
</ul>
<p>While building, each part was undone once: <code>acknowledge-mode: none</code> turned 2 tests red; no retry 2; prefetch 250 1; no dead-letter exchange 1; no recoverer 1; no skip of rendered reports 1; no \"requested\" marker 1; no wait for the broker's confirmation 1; the marker kept after a refused publish 2. Two parts turned nothing red and stay, with their reasons: writing the PDF next to its name and moving it (so nobody reads half a PDF, which no test catches), and the worker stopping when its channel closes (see Tests).</p>
</div>
""" + code(read(T + "AutoAckTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "ReportController.java", dwn("The API.",
        "Checks the id, marks the report requested (once), publishes and waits for the broker's confirmation; reads state from the report files.",
        "A <code>202</code> for a message the broker never got; two messages for one report.",
        "<ul><li>A refused confirmation arrives as the RabbitMQ client's <code>ShutdownSignalException</code>, not Spring's <code>AmqpException</code>: both are caught. Found while building.</li><li>If publishing fails, the marker is removed so the next request tries again.</li></ul>")),
    (J + "ReportsApplication.java", dwn("The topology.", "A direct exchange, the durable work queue with its dead-letter exchange, and the dead-letter queue; JSON messages.", "Messages lost with a restart of the broker, or dropped when rejected.")),
    (J + "RenderWorker.java", dwn("The worker.",
        "Skips reports already rendered, renders page by page, saves the PDF; returns normally only when done.",
        "Lost or doubled reports when workers die or messages repeat.",
        "<ul><li>If its channel is closed mid-render, the broker has already given the message to another worker: it stops instead of racing it.</li><li>The two simulated failures: LR-0013 always, LR-0042 once.</li></ul>")),
    (J + "GiveUp.java", dwn("After the last retry.", "Writes the reason on the report, then rejects without requeue: the broker dead-letters it.", "A report that fails silently, or a message retried for ever.")),
    (J + "LabReports.java", dwn("Reports on disk.", "An atomic \"requested\" marker, the PDF written then moved, the failure note; ids checked before any file is touched.", "Half-written PDFs; paths built from user input.")),
    (J + "Pdf.java", "<p>A minimal valid PDF, one line per page.</p>"),
    ("src/main/resources/application.yaml", "<p>Publisher confirms, <code>acknowledge-mode: auto</code>, prefetch 1, two consumers, retry.</p>"),
    ("compose.yaml", "<p>RabbitMQ 4.1 with the management UI on port 15672 (guest / guest).</p>"),
]
tree = """stations/101-task-queue-with-rabbitmq/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/mediqo/reports/
│   ├── ReportController.java   ├── ReportsApplication.java   ├── RenderWorker.java
│   └── GiveUp.java   ├── LabReports.java   └── Pdf.java
├── src/main/resources/application.yaml
├── src/test/java/com/mediqo/reports/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Docker", "Docker Desktop (Windows, macOS) or Docker Engine (Linux), running", "<code>docker info</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""docker compose up -d        # RabbitMQ on localhost:5672, management UI on http://localhost:15672
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests; starts its own RabbitMQ container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Queue a long report and stop the app while it renders:</p>
""" + code("""curl -X POST http://localhost:8080/lab-reports/LR-0500/render
# within 10 s: stop the app (Ctrl+C), then start it again
curl http://localhost:8080/lab-reports/LR-0500""", "bash") + """
<p>The report is rendered after the restart: the broker kept the unacknowledged message. Open the management UI and watch <i>Unacked</i> go to 1 and back.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>PRECONDITION_FAILED - inequivalent arg</code>", "The queue exists with other arguments (for example without the dead-letter exchange).", "Delete it, or declare a new queue; arguments cannot change in place."],
    ["Messages pile up as Unacked", "A worker is stuck, or prefetch is high and one worker hoards them.", "Prefetch 1 for long tasks; look at the worker."],
    ["<code>Could not find a valid Docker environment</code>", "Docker is not running.", "Start Docker Desktop or the Docker service."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the worker and what happens when it gives up.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>RenderContractTest</code> ({cnt('RenderContractTest')}), <code>BrokerDownTest</code> ({cnt('BrokerDownTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>AutoAckTrapTest</code> ({cnt('AutoAckTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Messaging", "Duplicate delivery, retry and dead letter", f"<code>RetryAndDeadLetterMessagingTest</code> ({cnt('RetryAndDeadLetterMessagingTest')})", '<span class="pill ok">pass</span>'],
    ["Idempotency", "Replay: the same request twice gives one effect", f"<code>DuplicateRenderReplayTest</code> ({cnt('DuplicateRenderReplayTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">A real RabbitMQ in Docker. To kill a worker the way a crash does, a test closes the app's connection from the broker's side through the management API; the broker puts the unacknowledged message back.</p>
<p class="muted">Found while building, twice over: the first version of that test passed and proved nothing. The management API lists connections a few seconds late, so the test closed no connection at all; and once it did, a worker that had lost its connection kept rendering and saved the PDF anyway, so even <code>acknowledge-mode: none</code> passed. Now the test finds the app's connection before it starts, and the worker stops when its channel closes, as a crashed one would: with <code>none</code> the report is lost and the test fails.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, RabbitMQ 4.1 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "AutoAckTrapTest.java", "<p>Written first: auto-ack against acknowledging after the work, with the plain client.</p>"),
    (T + "RenderContractTest.java", "<p>A report from request to PDF; bad and unknown ids; prefetch; a refused publish.</p>"),
    (T + "BrokerDownTest.java", "<p>No broker: <code>503</code>, and the next request tries again.</p>"),
    (T + "RetryAndDeadLetterMessagingTest.java", "<p>A retry that works; the dead-letter queue; a worker cut off mid-render.</p>"),
    (T + "DuplicateRenderReplayTest.java", "<p>The same request twice; a repeated message.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: empty queues and no report files before each test.</p>"),
    (T + "RabbitTestConfig.java", "<p>RabbitMQ 4.1 with management, via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/mediqo/reports/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=ReplayDeadLettersChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Send the dead letters back", "Beginner-friendly", 30,
    "<code>POST /dead-letters/replay</code> moves every parked message back to the work queue (after someone fixed the cause) and answers how many it moved; each report goes back to QUEUED. One surprise, found while building: RabbitMQ 4 starts <code>x-death</code> afresh for a message a client publishes again, so the broker does not count the rounds for you.",
    "both tests in <code>ReplayDeadLettersChallengeTest</code> pass.",
    ["<code>basicGet</code> without auto-ack, publish it again, then acknowledge: a crash in between repeats it rather than losing it.",
     "Keep the message's properties when you publish it again; add your own header if you need to count replays."],
    "challenge/ReplayDeadLettersChallengeTest.java", ["challenge/solution/ReportController.java", "challenge/solution/LabReports.java"]) + challenge(2, "Urgent reports first", "Go deeper", 35,
    "<code>POST /lab-reports/{id}/render?urgent=true</code> sends the message with a higher priority on a queue that supports priorities, so it is the next message any worker takes.",
    "the test in <code>UrgentReportsChallengeTest</code> passes.",
    ["The queue needs <code>x-max-priority</code>; a queue's arguments cannot change in place, so in production this is a new queue or a migration.",
     "A message post-processor sets the priority when publishing.",
     "Priority only reorders what is waiting; prefetch 1 keeps little waiting inside the workers."],
    "challenge/UrgentReportsChallengeTest.java", ["challenge/solution/ReportsApplication.java", "challenge/solution/ReportController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>RabbitMQ or Kafka?</h2>
<p>Mediqo also wants every lab result as an event that billing, the patient app and analytics read on their own, and can read again from last month. Which part stays a RabbitMQ work queue and which becomes a Kafka topic? Compare: who removes a message, whether consumers compete or each read everything, replay, ordering, and Kafka's newer share groups (queue-like consumption on a topic). Where does each one's dead letter go?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test with the plain client: auto-ack against manual ack.</li>
<li>Declare the topology: exchange, durable queue, dead-letter exchange and queue.</li>
<li>Publish with confirms; consume with acknowledgement after the work, prefetch 1.</li>
<li>Add retry, the recoverer and idempotency; then cut a worker off in a test.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Acknowledge after the work, retry, dead-letter queue", "Repeats are possible: the worker must skip them.", '<span class="pill ok">Chosen</span>'],
    ["Auto-ack (<code>acknowledge-mode: none</code>)", "A worker that dies loses its messages.", '<span class="pill bad">The trap</span>'],
    ["Requeue on every failure", "A message that always fails loops for ever.", '<span class="pill bad">Avoid</span>'],
    ["@Async in the app (station 098's way)", "No broker; jobs die with the server.", '<span class="pill warn">For work you can lose</span>'],
    ["Kafka", "A log that consumers read at their own pace and can replay; work-queue semantics need share groups or care.", '<span class="pill warn">For events, see challenge 3</span>']]) + """
<h2>Database design</h2>
<p>No database: the broker holds the work, the disk holds the reports. With several servers, report state moves to a table and files to object storage; the queue stays the same.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Quorum queues</dt><dd>On a RabbitMQ cluster, use quorum queues for work that must survive a node: classic queues live on one node.</dd>
<dt>Watch</dt><dd>Queue depth, unacknowledged messages, consumer count and the dead-letter queue's size. A growing dead-letter queue is a bug report.</dd>
<dt>Timeouts</dt><dd>RabbitMQ closes a channel whose delivery is not acknowledged within <code>consumer_timeout</code> (30 minutes by default): long tasks must fit, or be split.</dd>
<dt>Poison messages</dt><dd>The retry limit is what keeps one bad message from blocking a worker for ever.</dd>
<dt>Outbox</dt><dd>If the request also writes a database row, publish through an outbox table, or a crash between the two loses one of them.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why do messages get lost with auto-ack?", "The broker deletes a message as soon as it is sent to a consumer. If the consumer dies before finishing, nobody has it."),
    ("What does Spring AMQP's acknowledge-mode auto mean?", "Spring acknowledges after the listener returns normally and rejects on an exception: the safe default. RabbitMQ's autoAck is Spring's NONE."),
    ("What is prefetch for?", "How many unacknowledged messages a consumer may hold. 1 spreads long tasks fairly; higher is faster for tiny ones."),
    ("How do you stop a poison message looping?", "Retry a few times, then reject without requeue so the broker dead-letters it."),
    ("How does the API know the broker has the message?", "Publisher confirms: wait for the broker's ack before answering 202."),
    ("Why must consumers be idempotent?", "Delivery is at least once: a crash after the work and before the ack means the message comes again."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Delivery", "Durable queue, acks after work.", "Publisher confirms, prefetch chosen on purpose, idempotent worker."],
    ["Failure", "Retries.", "A retry limit, a dead-letter queue, and the reason recorded."],
    ["Testing", "A listener test.", "A real broker, a worker cut off mid-task, and a test that fails without acknowledgements."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("AcknowledgeMode.NONE",
     "\"Auto-ack: faster\": the broker now deletes each message the moment a worker receives it. A worker that dies mid-report loses it, and a listener that throws loses it too: there is nothing left to retry or dead-letter.",
     "<code>aWorkerCutOffMidRenderLosesNothing</code> and <code>aDamagedReportEndsInTheDeadLetterQueueWithItsReason</code> fail."),
    ("A hand-made factory drops Spring Boot's settings",
     "Declaring <code>rabbitListenerContainerFactory</code> replaces the one Spring Boot builds from <code>application.yaml</code>: prefetch 1, the retry policy and the recoverer are all gone, with nothing in the code to say so.",
     "<code>aSlowReportDoesNotHoldUpTheOnesBehindIt</code> and <code>aBusyLabSystemIsRetriedAndTheReportIsRendered</code> fail: no prefetch 1, no retry."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate \"speeds up the workers\": a listener container factory with <code>AcknowledgeMode.NONE</code>, \"so the worker is simpler without acknowledgements\". Read the file and list every problem before opening the findings.</p>
<p class="path">review/ReportsApplication.java</p>
""" + code(read("review/ReportsApplication.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">On a calm day with healthy workers, every report is rendered. The flaw shows on the day a server restarts at peak: exactly the day in the story.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
