"""Station 098 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 98,
    "stack": "Spring Boot 4.1.1 · Java 25 · @Async with its own ThreadPoolTaskExecutor · CompletableFuture · 202 Accepted and an operation resource (Google AIP-151) · Awaitility",
    "simulation": "Rendering is simulated: demo invoice INV-2026-n has n pages and each page takes 130 ms of waiting; INV-2026-0013 always fails. The PDF itself is real: a minimal valid file with one line per page.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No database, no Docker. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/billora/invoices/"
T = "src/test/java/com/billora/invoices/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Request thread", "The server thread that answers one request; there are only so many.", "A counter clerk.", "Tomcat's pool"),
    ("@Async", "Spring runs the method on another thread and returns at once.", "The clerk hands the order to the kitchen.", "<code>Renderer.render</code>"),
    ("Executor", "A pool of worker threads with a queue in front.", "The kitchen: cooks, and a rail of waiting orders.", "<code>pdfExecutor</code>"),
    ("Bounded queue", "A queue with a size limit: when full, new work is refused.", "\"Kitchen full, come back in half an hour\".", "20"),
    ("202 Accepted", "\"Got it, not done yet\", with where to check.", "An order number.", "<code>Location: /pdf-jobs/...</code>"),
    ("Operation", "A resource that describes long-running work until it is done.", "The order's status board.", "AIP-151"),
]
STORY = [
    ("A 40-second click", "An accountant clicks \"Download PDF\" on a 300-page invoice. The server makes the PDF inside the request: 40 seconds of a request thread doing nothing else."),
    ("Month end", "Two hundred accountants do the same. Request threads run out, and the whole app stops answering. A quick fix moves the work to @Async: now every request is accepted and queued without limit, and when one render throws, its job says \"running\" for ever."),
    ("The fix", "The request answers 202 with a job's address in milliseconds. A pool of two workers with a queue of twenty does the work; when both are full the API says \"busy, try later\". A failure ends the job as failed, with the reason."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Slow work leaves the request, but it still needs limits and a place to report failure.</p>

<h2>What are we building?</h2>
<p>PDF jobs: start one, get its address, check it until it is done, then download the PDF, or read why it failed.</p>

<h2>An everyday analogy</h2>
<p>A tailor's shop: you leave your cloth and get a slip with a number. Two tailors work; twenty orders can wait on the rail. When the rail is full, the shop says \"come back tomorrow\" instead of taking cloth it cannot sew. If the cloth tears, the slip says so.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Start</strong>: <code>POST</code> answers <code>202</code> with the job's address, at once.</li>
<li><strong>Queue</strong>: a worker takes the job, or it waits on a bounded queue; full means <code>503</code>.</li>
<li><strong>Follow</strong>: <code>GET</code> the job: pages done so far, then done with a PDF link or an error.</li>
<li><strong>Download</strong> the PDF from the link.</li>
</ol>

<details class="qa check"><summary>Check yourself: why refuse a job when the queue is full, instead of keeping it?</summary><p>A job that would start in an hour helps nobody: the accountant gave up long ago, and the waiting jobs use memory. A clear \"busy, try in 30 s\" lets the client decide; the queue's limit is how long anyone would wait.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real PDF library.</strong> A minimal PDF written by hand; rendering time is simulated.</li>
<li><strong>One server.</strong> Jobs live in memory (Production).</li>
<li><strong>No sign-in.</strong> Job ids are random UUIDs; access control is another station's topic.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Billora</strong> (a fictional invoicing company): generating a 300-page invoice PDF holds a request thread for 40 seconds.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo rules: 2 workers, 20 waiting; INV-2026-n has n pages (1 to 500), 130 ms a page.</p>
<ol class="gwt">
<li><b>Given</b> an invoice, <b>then</b> <code>202</code> with <code>Location: /pdf-jobs/{uuid}</code> in milliseconds, whatever its size.</li>
<li><b>Given</b> a running job, <b>then</b> <code>GET</code> shows <code>done: false</code> and the pages done so far.</li>
<li><b>Given</b> a finished job, <b>then</b> <code>done: true</code> and either a response with the PDF's link or an error with the reason.</li>
<li><b>Given</b> both workers busy and 20 waiting, <b>then</b> a new job is <code>503</code> with <code>Retry-After</code>.</li>
<li><b>Given</b> the same invoice while its job is queued or running, <b>then</b> <code>200</code> with that job, not a second render.</li>
<li><b>Given</b> an unknown invoice or job, <b>then</b> <code>404</code>; a malformed id <code>400</code>; the PDF before it exists <code>409</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>No PDF work on a request thread.</li>
<li>A bounded pool and queue, owned by this feature.</li>
<li>Every failure ends its job as failed; none is only logged.</li>
<li>Tests never sleep for a fixed time.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Configure <code>@Async</code> with a named, bounded executor and handle rejection.</li>
<li>Return <code>CompletableFuture</code> from <code>@Async</code> and handle its failure.</li>
<li>Design a <code>202</code> + operation resource API for long-running work.</li>
<li>Test asynchronous code with Awaitility.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/invoices/{id}/pdf-jobs</code>", "Start a PDF job; <code>202</code> and its Location."],
    ["<code>GET</code>", "<code>/pdf-jobs/{jobId}</code>", "The job as an operation: done, metadata, then response or error."],
    ["<code>GET</code>", "<code>/pdf-jobs/{jobId}/pdf</code>", "The finished PDF."]]) + """
<p class="muted">The operation's shape follows <a href=\"https://google.aip.dev/151\">AIP-151</a>, Google's API design guideline for long-running operations (a guideline, not a formal standard): <code>name</code>, <code>done</code>, <code>metadata</code>, and when done exactly one of <code>response</code> or <code>error</code>.</p>
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">202</span>', "Job started"],
    ['<span class="pill ok">200</span>', "The same invoice's job is still queued or running (that job); a job; the PDF"],
    ['<span class="pill warn">400</span>', "An invoice id that is not <code>INV-YYYY-NNNN</code>; a job id that is not a UUID"],
    ['<span class="pill warn">404</span>', "No such invoice or job"],
    ['<span class="pill warn">409</span>', "The PDF of a job that is not done, or failed"],
    ['<span class="pill warn">503</span>', "Both workers busy and the queue full, with <code>Retry-After: 30</code>"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, at the configured 130 ms a page. <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-a-three-page-invoice", "Case 1: a three-page invoice", "<b>Why:</b> <code>202</code> and the job's address; not done yet."),
    ("02-done", "Case 2: the same job, done", "<b>Why:</b> a response with the PDF's link, size and pages."),
]) + """
<p class="muted">Downloading that PDF: its headers, then what poppler's <code>pdfinfo</code>, an independent PDF reader, says about the file.</p>
""" + code(read("docs/captures/pdf-download.txt").strip(), "text") + """
<p class="muted">Starting the 300-page invoice (about 40 s of work), timed by curl:</p>
""" + code(read("docs/captures/big-invoice-timing.txt").strip(), "text") + examples([
    ("03-three-hundred-pages-two-seconds-later", "Case 3: the 300-page job, two seconds later", "<b>Why:</b> running, with its progress."),
    ("04-the-same-invoice-again", "Case 4: the same invoice again", "<b>Why:</b> <code>200</code> with the same job: a double click does not start a second render."),
    ("05-its-pdf-before-it-is-ready", "Case 5: its PDF before it is ready", "<b>Why:</b> <code>409</code>."),
    ("06-a-damaged-invoice", "Case 6: the damaged invoice", "<b>Why:</b> accepted like any other."),
    ("07-the-failed-job", "Case 7: the failed job", "<b>Why:</b> done, with an error that says why: no job stays \"running\" for ever."),
    ("08-no-such-invoice", "Case 8: no such invoice", "<b>Why:</b> <code>404</code>."),
    ("09-not-an-invoice-id", "Case 9: not an invoice id", "<b>Why:</b> <code>400</code>."),
    ("10-no-such-job", "Case 10: no such job", "<b>Why:</b> <code>404</code>."),
    ("11-the-23rd-at-once", "Case 11: month end, the 23rd big invoice at once", "<b>Why:</b> two rendering, twenty waiting: <code>503</code> with <code>Retry-After</code>, instead of a place in a queue no one would wait in."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Boot's default pool, 1,000 jobs", "All accepted: 8 running, 992 waiting", "<code>theDefaultPoolAcceptsEveryJobAndQueuesItWithoutLimit</code>"],
    ["An @Async void method that throws; the API's failing render", "Stays RUNNING; FAILED with the reason", "<code>theOldWaySwallowsTheErrorAndTheApiReportsIt</code>"],
    ["A small invoice", "<code>202</code>, then a valid 3-page PDF", "<code>aJobIsAcceptedAndEndsWithAPdf</code>"],
    ["A 300-page invoice", "<code>202</code> in under 0.5 s; progress; <code>409</code> for the PDF until done", "<code>theRequestReturnsAtOnceAndProgressCanBeFollowed</code>"],
    ["Unknown invoices, malformed ids, unknown jobs", "<code>404</code>, <code>400</code>", "<code>unknownInvoicesAndJobsAre404AndBadIds400</code>"],
    ["A render that fails", "FAILED, the reason; no PDF; a new job next time", "<code>aFailedRenderIsAFailedJobWithItsReason</code>"],
    ["Workers and queue full", "<code>503</code> and <code>Retry-After</code>; accepted again later", "<code>whenBothWorkersAndTheQueueAreFullANewJobIs503</code>"],
    ["The same invoice twice", "The same job", "<code>theSameInvoiceWhileItsJobRunsIsTheSameJob</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">@Async on the default executor with unbounded queues and swallowed errors.</p>
<ul>
<li><strong>The default pool.</strong> The test reads Spring Boot's own defaults for its task executor (8 threads, a queue of <code>Integer.MAX_VALUE</code>) and builds a pool like it. 1,000 jobs: all accepted, 8 running, 992 waiting in memory, none refused. At 40 s a render the last starts after about 83 minutes.</li>
<li><strong>Swallowed errors.</strong> An <code>@Async void</code> method sets \"RUNNING\", throws, and the line that would set \"DONE\" never runs. Spring logs the exception; the status says running for ever. The API's own failing render ends <code>FAILED</code> with the reason.</li>
</ul>
<p>While building, each part was undone once: an unbounded queue turned 1 test red; no <code>@Async</code> 6; failures ignored 2; the failure not unwrapped 2; no check for a running job of the same invoice 1; a refused job left registered 1; a finished job left registered 1; no id pattern 1.</p>
</div>
""" + code(read(T + "AsyncTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "PdfJobController.java", dwn("The three endpoints.",
        "<code>202</code> and Location; <code>200</code> for a job already running; <code>503</code> with <code>Retry-After</code> when the pool refuses; <code>409</code> for a PDF that does not exist yet.",
        "A request thread held for 40 s; a client told nothing when the server is full.")),
    (J + "PdfJobs.java", dwn("Jobs as operations.",
        "Registers a job, hands it to the renderer, and on completion records the PDF or the error.",
        "Jobs that say \"running\" after their render died; two renders of one invoice.",
        "<ul><li><code>whenComplete</code>, not <code>thenAccept</code>: the second runs only on success.</li><li>The failure arrives wrapped in a <code>CompletionException</code>; the job keeps the render's own message. Found while building.</li><li>If the pool refuses, the job is unregistered so the invoice can be tried again.</li></ul>")),
    (J + "Renderer.java", dwn("The slow part, on the pdf pool.",
        "<code>@Async(\"pdfExecutor\")</code>, a <code>CompletableFuture</code>, progress per page, and a minimal PDF.",
        "Rendering on the caller's thread; failures that reach only a log.",
        "<ul><li>A separate bean: <code>@Async</code> works through a proxy, so calling it from the same class would run it on the caller's thread.</li></ul>")),
    (J + "InvoicesApplication.java", dwn("The pdf pool.", "2 workers, a queue of 20, refuse when full, let running renders finish on shutdown.", "Boot's default: a queue without limit.")),
    (J + "Invoices.java", "<p>Simulated invoices: INV-2026-n has n pages.</p>"),
    ("src/main/resources/application.yaml", "<p>Workers, queue and the simulated speed.</p>"),
]
tree = """stations/098-invoice-pdfs-without-blocking/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/billora/invoices/
│   ├── PdfJobController.java   ├── PdfJobs.java   ├── Renderer.java
│   └── InvoicesApplication.java   └── Invoices.java
├── src/main/resources/application.yaml
├── src/test/java/com/billora/invoices/   (see Tests)
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
""" + code("""curl -i -X POST http://localhost:8080/invoices/INV-2026-0120/pdf-jobs
curl http://localhost:8080/pdf-jobs/<the id from Location>      # again every few seconds
curl -o invoice.pdf http://localhost:8080/pdf-jobs/<id>/pdf      # once done""", "bash") + """
<p>120 pages take about 16 s. Start 23 big ones in a loop and watch the 23rd get <code>503</code>.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["The POST still takes 40 s", "The @Async method is called from its own class, so no proxy is in between.", "Put it in another bean."],
    ["Jobs stay RUNNING after an error", "<code>@Async void</code>, or <code>thenAccept</code> without failure handling.", "Return a future; use <code>whenComplete</code>."],
    ["<code>No qualifying bean of type TaskExecutor</code>", "<code>@Async(\"pdfExecutor\")</code> names a pool that does not exist.", "Define the executor bean with that name."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>PdfJobContractTest</code> ({cnt('PdfJobContractTest')}), <code>FailureAndBackpressureTest</code> ({cnt('FailureAndBackpressureTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>AsyncTrapTest</code> ({cnt('AsyncTrapTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">Pages take 5 ms in the tests (300 pages in 1.5 s), with 2 workers and a queue of 3. Every wait is Awaitility: it checks every 20 ms and fails after a limit, so a test is as fast as the code and never flaky because a sleep was too short. To prove the old way's job stays \"RUNNING\", Awaitility's <code>during</code> checks it stays so for half a second.</p>
<p class="muted">Found while building: the test's <code>@Async</code> bean is a proxy, and reading its field through the proxy gave <code>null</code>; it is read through a method now.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "AsyncTrapTest.java", "<p>Written first: Boot's default pool, and an @Async void method that throws.</p>"),
    (T + "PdfJobContractTest.java", "<p>A job from start to PDF; a big one followed while it runs; bad and unknown ids.</p>"),
    (T + "FailureAndBackpressureTest.java", "<p>A failed render; a full pool; the same invoice twice.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: fast pages, a small pool, Awaitility helpers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/billora/invoices/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=RetryAfterChallengeTest</code>.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "When to look again", "Beginner-friendly", 20,
    "While a job is not done, the <code>202</code> and every <code>GET</code> of it carry <code>Retry-After</code>: the seconds its remaining pages should take, rounded up, at least 1. A done job has none. Clients stop polling every 100 ms.",
    "both tests in <code>RetryAfterChallengeTest</code> pass.",
    ["Pages left times ms per page, from the operation's metadata and the configuration.",
     "One helper used by both endpoints."],
    "challenge/RetryAfterChallengeTest.java", ["challenge/solution/PdfJobController.java"]) + challenge(2, "Cancel a job", "Go deeper", 40,
    "<code>POST /pdf-jobs/{jobId}:cancel</code>, AIP-151's custom method. A queued job is cancelled at once and never renders; a running one stops after its current page. Both end done, with the error code <code>CANCELLED</code>. A done job is <code>409</code>.",
    "both tests in <code>CancelChallengeTest</code> pass.",
    ["Threads cannot be stopped safely from outside: set a flag the renderer checks before each page.",
     "Spring's path patterns accept <code>{jobId}:cancel</code>: a variable followed by literal text.",
     "A queued job's render still runs once: it sees the flag and returns at once."],
    "challenge/CancelChallengeTest.java", ["challenge/solution/PdfJobs.java", "challenge/solution/Renderer.java", "challenge/solution/PdfJobController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Jobs that survive a restart</h2>
<p>Billora runs four servers and deploys twice a day. A job started on server 2 must be readable from server 3, and a render cut off by a deploy must not be lost. Design it: a jobs table, a queue (a table with SKIP LOCKED, or a broker), PDFs in object storage with a time-limited link, and what happens to a render that was half done when its server stopped.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: Boot's default pool, and an @Async void method that throws.</li>
<li>Define a named, bounded executor, and a renderer bean that returns a future.</li>
<li>Wrap the work in an operation resource: register, follow, finish.</li>
<li>Map a refused job to <code>503</code>, and test it all with Awaitility.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["A bounded executor, 202 and an operation", "Clients poll; jobs need a home.", '<span class="pill ok">Chosen</span>'],
    ["Make the PDF inside the request", "A request thread per render; time limits on the way.", '<span class="pill bad">The problem</span>'],
    ["@Async on Boot's default pool, void", "Unbounded queue; errors only logged.", '<span class="pill bad">The trap</span>'],
    ["Virtual threads for renders", "No thread shortage, but no limit either: CPU and memory become the limit.", '<span class="pill warn">Still needs a limit</span>'],
    ["A message queue and worker service", "More parts; survives restarts and scales on its own.", '<span class="pill warn">At larger scale</span>']]) + """
<h2>Database design</h2>
<p>No database: jobs are in memory, which loses them on restart and hides them from other servers (challenge 3).</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Sizing</dt><dd>Workers are limited by CPU and memory per render; the queue by how long a user will wait (20 jobs × 40 s / 2 workers ≈ 7 minutes here).</dd>
<dt>Shutdown</dt><dd>The pool waits up to 60 s for running renders on shutdown; longer jobs need to be resumable (challenge 3).</dd>
<dt>Clean-up</dt><dd>Finished jobs and their PDFs are never removed here. Expire them (an hour, a day) and say so in the API.</dd>
<dt>Monitoring</dt><dd>Watch queue length, active workers, rejections and failures: <code>ThreadPoolTaskExecutor</code> exposes them, and Micrometer can publish them.</dd>
<dt>Push instead of poll</dt><dd>Email or a webhook when done saves clients from polling; <code>Retry-After</code> (challenge 1) makes polling cheaper.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("How do you keep a slow task off the request thread?", "Run it on a separate, bounded executor; answer 202 with a status URL."),
    ("What is wrong with Spring Boot's default @Async pool for this?", "Its queue has no limit: it accepts everything, runs out of memory or makes users wait for hours, and nobody is told \"busy\"."),
    ("What happens to an exception in an @Async void method?", "It goes to the AsyncUncaughtExceptionHandler, which logs it. The caller never knows. Return a CompletableFuture instead."),
    ("Why does @Async sometimes not work?", "It is applied by a proxy: calling the method from the same class bypasses it."),
    ("How do you test async code?", "Wait for the condition with Awaitility (poll until true, with a limit), never a fixed sleep."),
    ("What does a client get when the server is full?", "503 with Retry-After: an honest answer it can act on."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Async", "@Async with a named pool.", "Bounded, rejection mapped to 503, failures recorded."],
    ["API", "202 and a status URL.", "An operation shape with progress, response or error."],
    ["Testing", "Awaitility instead of sleep.", "A test that proves the request returns before the work."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("Boot's default executor queues without limit",
     "\"Spring Boot already configures a task executor\": 8 threads and a queue of <code>Integer.MAX_VALUE</code>. At month end every job is accepted, the queue grows in memory, and users wait for hours with no \"busy\". <code>@Async</code> without a name also shares that pool with every other async task in the app.",
     "<code>whenBothWorkersAndTheQueueAreFullANewJobIs503</code> fails: the 6th job is accepted."),
    ("thenAccept only runs on success",
     "\"Simpler: we only need the PDF\": when the render throws, <code>thenAccept</code> is skipped, the failure goes nowhere, and the job says RUNNING for ever. The trap's swallowed error, moved one line.",
     "<code>aFailedRenderIsAFailedJobWithItsReason</code> and <code>theOldWaySwallowsTheErrorAndTheApiReportsIt</code> fail: the job never finishes."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate tidies up: the custom executor goes (\"Boot already has one\"), <code>@Async</code> loses its name, and <code>whenComplete</code> becomes <code>thenAccept</code> (\"we only need the PDF\"). Read the three files and list every problem before opening the findings.</p>
<p class="path">review/InvoicesApplication.java</p>
""" + code(read("review/InvoicesApplication.java"), "java") + """
<p class="path">review/Renderer.java (only the annotation differs)</p>
""" + code("\n".join(l for l in read("review/Renderer.java").splitlines() if "@Async" in l or "CompletableFuture<byte[]> render" in l), "java") + """
<p class="path">review/PdfJobs.java</p>
""" + code(read("review/PdfJobs.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">On a quiet day with good invoices, the flawed version works and the PDFs arrive. It fails on the days that matter: month end, and the invoice with a broken logo.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
