"""Station 033 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 33,
    "stack": "Spring Boot 4.1.1 · Java 25 · stack traces · MDC request ids · @RestControllerAdvice · ProblemDetail · Micrometer · Actuator · MockMvc",
    "simulation": "Orders and amounts are demo data, not Kartwala's. A refund creates a record in memory; no payment provider is called and no money moves. The ledger failure in the drill is switched on by a setting.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/kartwala/refunds/"
T = "src/test/java/com/kartwala/refunds/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]
TRACE = read("docs/captures/ticket-stack-trace.txt").strip()
assert TRACE.startswith("java.lang.NullPointerException"), "docs/captures/ticket-stack-trace.txt is not the replayed NPE"
LOG_LINES = read("docs/captures/app-log.txt").strip()
assert LOG_LINES, "docs/captures/app-log.txt is empty"

# ---------- Level 1: Understand ----------
TERMS = [
    ("Stack trace", "The list of method calls that were running when an error happened, newest first.", "Footprints back from where someone fell.", "<code>at …couponShare(…)</code>"),
    ("Request id", "A label on one request, shown to the customer and written on every log line of that request.", "A token number at a bank counter.", "<code>X-Request-Id</code>"),
    ("Symptom", "What the customer sees.", "A fever.", "\"The button does nothing\""),
    ("Root cause", "The mistake that produces the symptom.", "The infection behind the fever.", "a null coupon"),
    ("Failing test first", "A test that reproduces the bug before you change any code.", "Showing the leak with water before fixing the pipe.", "<code>NullCouponTrapTest</code>"),
    ("Null object", "A real object that means \"nothing\", used instead of <code>null</code>.", "A blank form instead of no form.", "<code>Coupon.NONE</code>"),
]
STORY = [
    ("A ticket arrives", "\"I press refund and nothing happens.\" Support attaches a screenshot from the app's error log: a request id and a stack trace."),
    ("Last time, a quick patch", "A similar ticket last month was closed with a null check where that request came in. The ticket closed; the bug moved to the cancel-whole-order path."),
    ("This time, the cause", "Reproduce the request in a failing test, read the trace to the line that failed, ask why the value was null, and fix it where it is created, so every path is safe."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Fix the reason, not the place it showed up, and keep the test that proved it.</p>

<h2>What are we building?</h2>
<p><code>POST /refunds</code> records a refund for some lines of an order, or for every line not yet refunded. When something unexpected fails, the customer gets a message with a request id, and that id leads support straight to the stack trace.</p>

<h2>An everyday analogy</h2>
<p>A doctor with a patient who has a fever. Paracetamol makes the fever go away today (the patch). A blood test finds the infection, and the right medicine stops it coming back (the cause).</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Read the ticket</strong>: the request id and the error.</li>
<li><strong>Find the logs</strong> for that id, and the stack trace.</li>
<li><strong>Reproduce</strong> the request in a test that fails.</li>
<li><strong>Fix the cause</strong> until the test passes, and keep the test.</li>
</ol>

<details class="qa check"><summary>Check yourself: the patch made the ticket's request work. Why was that not enough?</summary><p>It guarded one entrance to the code. The calculator underneath still assumed every order had a coupon, so the next caller (the whole-order path) failed the same way.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No money moves.</strong> A refund record is created in memory.</li>
<li><strong>No log platform.</strong> Logs go to the console; searching them by id works the same in any tool.</li>
<li><strong>No front-end.</strong> The app's "does nothing" was it ignoring a 500; the API now explains itself.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Kartwala</strong> (a fictional shopping app) gets a ticket: the refund button does nothing for order KW-1042. The only clue is a stack trace with a request id.</p>

<h2>The ticket's stack trace</h2>
<p class="muted">Real output: the ticket's request replayed on the old code (kept in the tests as <code>OldRefundCalculator</code>), this app's frames only. Produced by <code>docs/capture.sh</code>, saved in <code>docs/captures/ticket-stack-trace.txt</code>.</p>
""" + code(TRACE, "text") + """
<h2>Reading it</h2>
<ol class="steps">
<li><strong>The first line</strong> is the exception and its message. Since Java 15 (by default), a <code>NullPointerException</code> says what was null: the return value of <code>coupon()</code>.</li>
<li><strong>The first <code>at</code> line</strong> is where it failed: <code>couponShare</code>. The lines below are who called it.</li>
<li>In a full log, frames from Spring and Tomcat sit around these. Look for the first frame in your own package.</li>
<li>Ask <em>why</em> it was null: an order without a coupon had <code>null</code> for its coupon. That is the cause.</li>
</ol>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> the ticket's request (KW-1042, line L2, no coupon), <b>then</b> <code>201</code>, ₹599.00 recorded.</li>
<li><b>Given</b> a whole-order refund of KW-1042, <b>then</b> <code>201</code>, ₹2,598.00: the other path works too.</li>
<li><b>Given</b> KW-1041 (₹200 coupon) refunded line by line, <b>then</b> the amounts add up to exactly what was paid, ₹1,598.00.</li>
<li><b>Given</b> a line already refunded, <code>409</code>; a line the order does not have, <code>422</code>; an unknown order, <code>404</code>.</li>
<li><b>Given</b> an unexpected failure, <b>then</b> <code>500</code> with the request id in the body and header, and one ERROR log line with that id and the stack trace.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>A failing test that reproduces the ticket comes before the fix, and stays.</li>
<li>Fix where the bad value is created, so every caller is safe.</li>
<li>Coupon share is proportional to price; the refund that empties the order gets what is left.</li>
<li>Money in integer paise; ids normalised with <code>Locale.ROOT</code>.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Read a stack trace: message, first frame, your own frames, the cause.</li>
<li>Find every log line of one request by its id.</li>
<li>Reproduce a bug with a failing test before fixing it.</li>
<li>Tell a fix of the cause from a patch of the symptom.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Body"], [
    ["<code>POST</code>", "<code>/refunds</code>", "<code>{\"orderId\", \"lineIds\"?}</code>. Without <code>lineIds</code>, every line not yet refunded."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "A refund record was created"],
    ['<span class="pill warn">400</span>', "Not JSON, a bad order or line id, or an unknown field"],
    ['<span class="pill warn">404</span>', "No such order"],
    ['<span class="pill warn">409</span>', "The line, or the whole order, is already refunded"],
    ['<span class="pill warn">422</span>', "A line the order does not have"],
    ['<span class="pill bad">500</span>', "Something unexpected; the body has the request id to quote"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against one app. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-the-tickets-request", "Case 1: the ticket's request", "<b>Why:</b> no coupon is now <code>Coupon.NONE</code>: the belt's full ₹599.00."),
    ("02-the-same-line-again", "Case 2: the same line again", "<b>Why:</b> a line is refunded once: <code>409</code>."),
    ("03-the-rest-of-the-order", "Case 3: the rest of KW-1042", "<b>Why:</b> the whole-order path, which last month's patch missed."),
    ("04-one-line-of-a-coupon-order", "Case 4: the dupatta from KW-1041", "<b>Why:</b> ₹499 minus its share of the ₹200 coupon (₹55.50, rounded down to whole paise)."),
    ("05-the-last-line-takes-what-is-left", "Case 5: the rest of KW-1041", "<b>Why:</b> the last refund gets what is left, so the two add up to the ₹1,598.00 paid."),
    ("06-a-line-the-order-does-not-have", "Case 6: line L9", "<b>Why:</b> <code>422</code>."),
    ("07-no-such-order", "Case 7: KW-9999", "<b>Why:</b> <code>404</code>."),
    ("08-the-metric-the-alert-reads", "Case 8: the metric", "<b>Why:</b> the count the dashboard and alert read."),
]) + """
<h2>The same requests in the app's log</h2>
<p class="muted">The running app's own console lines searched for the ids of cases 1 and 2 (<code>docs/captures/app-log.txt</code>; timestamps and process id removed). Only case 1 has a line: case 2's <code>409</code> is a client's mistake, not a failure, so it writes none.</p>
""" + code(LOG_LINES, "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["The ticket's exact request", "<code>201</code>, ₹599.00", "<code>theTicketsExactRequestIsRecorded</code>"],
    ["Whole order, no coupon", "<code>201</code>, ₹2,598.00", "<code>theWholeOrderPathWorksWithoutACouponToo</code>"],
    ["The same line twice in one request; part then rest", "Counted once; totals equal what was paid", "<code>partRefundsOfACouponOrderAddUpToWhatWasPaid</code>"],
    ["A line twice; the whole order twice", "<code>409</code>", "<code>aLineIsRefundedOnce</code>"],
    ["Unknown order; unknown line", "<code>404</code>; <code>422</code>", "<code>unknownOrdersAndLinesAreRefused</code>"],
    ["No order id; bad ids; an extra field; not JSON", "<code>400</code>", "<code>badBodiesAre400</code>"],
    ["The ledger fails", "<code>500</code> with the id, an ERROR line, the metric", "<code>anUnexpectedErrorLeavesATrailFromTheCustomerToTheStackTrace</code>"],
    ["The failure ends", "Refunds work; nothing half-recorded", "<code>afterTheFailureRefundsRecover</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Fixing the symptom without a failing test first, so the bug returns.</p>
<p>The first test reproduces the ticket on the old code: the same <code>NullPointerException</code>, failing in <code>couponShare</code>. The second shows last month's patch: the ticket's path now works, and the whole-order path still throws. The third shows the fix at the cause: every path is safe. While building, each fix was undone once. Keeping the null coupon turned 7 tests red; not logging the error turned 1 red, dropping the last-refund rule 2, and leaving the request id out of the 500 body 1.</p>
</div>
""" + code(read(T + "NullCouponTrapTest.java"), "java") + code(read(T + "OldRefundCalculator.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "RequestIdFilter.java", dwn("Gives each request an id, puts it in the MDC and the response header.",
        "A filter, so it wraps everything, including errors.",
        "An id only on some log lines, or one a caller can fill with fake log text.")),
    (J + "RefundController.java", dwn("Validates the body and returns the refund record.",
        "Ids normalised once, at the edge.",
        "A null check here for the coupon: that was the patch.")),
    (J + "RefundService.java", dwn("Checks the lines, computes the amount, records the refund.",
        "No line ids means the rest of the order; a line twice in one request counts once.",
        "Refunding a line twice, or over-refunding with rounding.")),
    (J + "Order.java", dwn("An order and what was paid.",
        "The fix lives here: the constructor turns a null coupon into <code>Coupon.NONE</code>, so no caller ever sees null.",
        "The trap: a null that every caller has to remember.")),
    (J + "RefundCalculator.java", dwn("How much comes back for some lines.",
        "Proportional coupon share, rounded down; the last refund gets what is left.",
        "<code>order.coupon().discountPaise()</code> with a coupon that might be null.")),
    (J + "UnexpectedErrorHandler.java", dwn("Turns an unexpected exception into a 500 the customer can quote, and a log line support can find.",
        "Logs while the request id is still in the MDC, once, at ERROR, with the stack trace.",
        "Letting it escape: the servlet container logs it after the filter has cleared the id.")),
    (J + "RefundLedger.java", "<p>Refund records in memory, and the switch the failure drill uses.</p>"),
    (J + "Coupon.java", "<p>A coupon, and <code>Coupon.NONE</code>.</p>"),
    (J + "Line.java", "<p>One line of an order.</p>"),
    (J + "Orders.java", "<p>Two demo orders: one with a coupon, and the ticket's, without.</p>"),
    (J + "RefundsApplication.java", "<p>Entry point.</p>"),
    ("src/main/resources/application.yaml", "<p>The request id in the log pattern, the metrics endpoint, strict JSON, and the drill switch (off).</p>"),
]
tree = """stations/033-bug-triage-from-a-customer-ticket/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/kartwala/refunds/
│   ├── RequestIdFilter.java   ├── RefundController.java   ├── RefundService.java
│   ├── Order.java   ├── Coupon.java   ├── Line.java   ├── Orders.java
│   ├── RefundCalculator.java   ├── RefundLedger.java
│   ├── UnexpectedErrorHandler.java   └── RefundsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/kartwala/refunds/   (see Tests; TicketReplay prints the ticket's trace)
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
""" + code("""./mvnw spring-boot:run                                    # the API on http://localhost:8080
./mvnw spring-boot:run -Dspring-boot.run.arguments=--kartwala.refunds.simulate-ledger-failure=true   # the failure drill
./mvnw test                                               # all """ + str(N_TESTS) + """ tests""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
.\\mvnw.cmd spring-boot:run "-Dspring-boot.run.arguments=--kartwala.refunds.simulate-ledger-failure=true"
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Bring the bug back: in <code>Order.java</code>, delete the line <code>coupon = coupon == null ? Coupon.NONE : coupon;</code> and run the tests. Read the first failure's stack trace the way the Spec tab does. Then put it back.</p>
""" + code("""curl -i -X POST http://localhost:8080/refunds -H "Content-Type: application/json" \\
     -H "X-Request-Id: my-ticket-0001" -d '{"orderId":"KW-1042","lineIds":["L2"]}'""", "bash") + """
<p>Then search the app's console for <code>rid:my-ticket-0001</code>.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["A stack trace with no line of your own code", "The error came from a library, called by your code further down.", "Read down to the first frame in <code>com.kartwala</code>, and look for <code>Caused by:</code>."],
    ["An ERROR log line with <code>[rid:-]</code>", "It was logged after the request finished (outside the filter).", "Handle the exception inside the request, as <code>UnexpectedErrorHandler</code> does."],
    ["The NPE message says only <code>null</code>", "Helpful NullPointerException messages switched off, or Java older than 15.", "Java 15 and later have them on by default; check for <code>-XX:-ShowCodeDetailsInExceptionMessages</code>."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the pieces it uses.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>RefundContractTest</code> ({cnt('RefundContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>NullCouponTrapTest</code> ({cnt('NullCouponTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Operations", "Metric, alert, rollback, runbook; a controlled failure drill", f"<code>OperationsDrillTest</code> ({cnt('OperationsDrillTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Amounts without Spring", f"<code>RefundCalculatorTest</code> ({cnt('RefundCalculatorTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "NullCouponTrapTest.java", "<p>Written first: the ticket on the old code, the patch that missed a path, and the fix.</p>"),
    (T + "RefundContractTest.java", "<p>The ticket's request, both paths, the money, and every refusal.</p>"),
    (T + "OperationsDrillTest.java", "<p>The failure drill: a 500 with the id, the ERROR line with the trace, the metric, recovery.</p>"),
    (T + "RefundCalculatorTest.java", "<p>Coupon share, the last refund's remainder, and no coupon.</p>"),
    (T + "OldRefundCalculator.java", "<p>The old code, with last month's patch.</p>"),
    (T + "TicketReplay.java", "<p>Prints the ticket's real stack trace for this page.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: a fresh app per test, since refunds change the ledger.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/kartwala/refunds/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=FreeOrderTicketChallengeTest</code>. Read the stack trace first.</li>
<li>Fix the cause until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "A second ticket: free samples", "Beginner-friendly", 20,
    "\"Refund for my free samples fails.\" The log shows <code>java.lang.ArithmeticException: / by zero</code> in <code>RefundCalculator.amount</code>, for an order where every line cost ₹0. The failing test is written for you; fix the cause.",
    "both tests in <code>FreeOrderTicketChallengeTest</code> pass, and nothing else turns red.",
    ["Which number is zero, and why can it be?",
     "Nothing was paid, so nothing comes back: answer 0 before dividing."],
    "challenge/FreeOrderTicketChallengeTest.java", ["challenge/solution/RefundCalculator.java"]) + challenge(2, "The request id on every refusal", "Go deeper", 30,
    "Support wants the request id on every problem response (<code>400</code>, <code>404</code>, <code>409</code>, <code>422</code>), not only on <code>500</code>, so a customer who sees \"already refunded\" can be traced too.",
    "both tests in <code>RequestIdOnEveryProblemChallengeTest</code> pass.",
    ["<code>ResponseEntityExceptionHandler</code> builds every Spring problem response through one protected method.",
     "Override <code>createResponseEntity</code> and add the property when the body is a <code>ProblemDetail</code>."],
    "challenge/RequestIdOnEveryProblemChallengeTest.java", ["challenge/solution/UnexpectedErrorHandler.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>A triage template for support</h2>
<p>Write the one-page template support fills before a ticket reaches engineering: what the customer did, when, the request id, the order, the exact message shown. For each field, say which step of the runbook it saves. What would you add so that a ticket like this one is linked to the failing test that closed it?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Find the request id's log lines and the stack trace.</li>
<li>Write the failing test: the ticket's request on the code as it is.</li>
<li>Ask why the value was null until the answer is a design choice (null meant \"no coupon\").</li>
<li>Fix it there, run every test, and keep the new one.</li>
<li>Make the next ticket easier: the 500 carries the id, and the log line has it.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Fix", "What it costs", "Verdict"], [
    ["<code>Coupon.NONE</code> set in the record's constructor", "One line; every caller is safe.", '<span class="pill ok">Chosen</span>'],
    ["<code>Optional&lt;Coupon&gt;</code> accessor", "Every caller must unwrap; also safe.", '<span class="pill warn">Also fine</span>'],
    ["A null check in the calculator", "Fixes this calculator; the next reader of the coupon can forget again.", '<span class="pill warn">Partial</span>'],
    ["A null check where the request comes in", "The ticket closes; other paths still fail.", '<span class="pill bad">The trap</span>'],
    ["<code>catch (Exception e)</code> returning 0", "A silent wrong refund instead of an error.", '<span class="pill bad">Worse</span>']]) + """
<h2>Database design</h2>
<p>None in this station. With a database, the cause is often a nullable column: <code>coupon_id</code> nullable is fine if the code models it, and a <code>unique (order_id, line_id)</code> on the refund lines table makes "refunded once" hold across app instances.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["14. Operations: metric, alert, rollback, runbook, failure drill", "15. Real-world considerations"],
               "An Operations station: everything someone on call needs, and a drill to prove it works.") + """
<h2>Operations</h2>
<dl class="facts">
<dt>Metric</dt><dd><code>refunds.requests</code>, tagged <code>outcome</code> = recorded or failed. Client mistakes (4xx) are not failures and are not counted as them.</dd>
<dt>Alert</dt><dd>Page the on-call engineer when <code>failed</code> is more than 2% of all refund requests for 10 minutes, or more than 0 for an hour at low traffic (thresholds are a starting point; tune them on real traffic).</dd>
<dt>Rollback</dt><dd>The fix changes no stored data, so rolling back is redeploying the previous version. Refunds recorded meanwhile stay valid. If a release raises <code>failed</code>, roll back first and investigate from the request ids after.</dd>
</dl>
<h2>Runbook: "the refund button does nothing"</h2>
<ol class="steps">
<li>Get the request id: from the customer's screenshot (the 500 body now shows it), or the app's error report.</li>
<li>Search the logs for <code>[rid:&lt;that id&gt;]</code>. Read the ERROR line's exception, message and first frame in <code>com.kartwala</code>.</li>
<li>Check <code>refunds.requests{outcome=failed}</code>: one customer, or everyone? Everyone after a release: roll back.</li>
<li>One kind of order: write a failing test with that order's shape before touching code. Fix the cause; link the test to the ticket.</li>
</ol>
<h2>Failure drill</h2>
<p>A controlled failure drill, run before you need the runbook for real:</p>
<ol class="steps">
<li>Start a test instance with <code>--kartwala.refunds.simulate-ledger-failure=true</code>.</li>
<li>Send a refund with <code>X-Request-Id: drill-req-0001</code>: expect <code>500</code>, and <code>requestId: drill-req-0001</code> in the body.</li>
<li>Follow the runbook from that id alone: find the ERROR line and its stack trace, and see <code>outcome=failed</code> in <code>/actuator/metrics/refunds.requests</code>.</li>
<li>Restart without the switch; the same refund now gives <code>201</code>, because nothing was recorded by the failed try.</li>
</ol>
<p class="muted">The same drill runs on every build as <code>OperationsDrillTest</code> (""" + str(cnt("OperationsDrillTest")) + """ tests, passing in <code>docs/test-run.txt</code>).</p>
<h2>Real-world considerations</h2>
<dl class="facts">
<dt>Privacy</dt><dd>Stack traces and log lines must not carry card numbers, addresses or phone numbers; log ids, not people.</dd>
<dt>Error trackers</dt><dd>Tools such as Sentry group identical stack traces and count them; the request id links each event to its logs.</dd>
<dt>Regression tests</dt><dd>A bug's test is named after what it proves, not the ticket number, and stays in the suite for good.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("How do you read a Java stack trace?", "Read the exception type and message first, then the first frame (where it was thrown), then down to the first frame in your own code. With a chain, the last 'Caused by:' is usually the origin."),
    ("A customer reports an error. What do you do first?", "Get the request id or time, find the logs for it, read the error, and reproduce it with a failing test before changing anything."),
    ("Symptom fix vs root-cause fix?", "A symptom fix makes the visible failure go away where it was seen. A root-cause fix removes the reason, so every path that could hit it is safe. The failing test proves which one you did."),
    ("Why log unexpected errors in a @RestControllerAdvice?", "It runs inside the request, while the MDC still has the request id, and it can return a useful body. An exception that escapes is logged by the container after the filter cleared the id."),
    ("What is the null object pattern?", "A real object standing for 'nothing' (Coupon.NONE, discount 0), so callers never need a null check."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You brought the bug back and read the trace."],
    ["Triage", "From request id to the failing line.", "From the failing line to why the value was wrong."],
    ["Testing", "A failing test before the fix.", "A test for the other paths the same cause could reach."],
    ["Operations", "The 500 shows the id; the log has it.", "You ran the failure drill and followed the runbook."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any bug fix:</p>
<ul class="rules">
<li>Is there a test that fails without the fix? Did someone see it fail?</li>
<li>Is the fix where the bad value is created, or where it was noticed?</li>
<li>Which other paths read the same value?</li>
<li>Would the next error of this kind reach a log line with a request id?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
