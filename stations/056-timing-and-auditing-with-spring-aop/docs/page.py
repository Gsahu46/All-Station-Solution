"""Station 056 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 56,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring AOP (spring-boot-starter-aspectj) · custom annotation · @Around advice · @Transactional · JdbcClient · PostgreSQL 17 · Flyway · Testcontainers",
    "simulation": "Merchants, balances and payouts are demo data, not Paysetu's. A payout is a record in the payouts table: no bank is called and no money moves.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/paysetu/payouts/"
T = "src/test/java/com/paysetu/payouts/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Cross-cutting concern", "Something many methods need, unrelated to what each one does.", "Every shop till printing a receipt.", "Timing, audit"),
    ("Aspect", "A class that holds code to run around many methods.", "The receipt printer attached to every till.", "<code>AuditAspect</code>"),
    ("Pointcut", "Which methods the aspect applies to.", "\"Every till marked with a sticker\".", "<code>@annotation(audited)</code>"),
    ("Advice", "The code that runs: before, after, or around the method.", "Print the receipt after the sale.", "<code>@Around</code>"),
    ("Custom annotation", "A label you invent and put on methods.", "The sticker on the till.", "<code>@Audited</code>"),
    ("Proxy", "The object Spring puts in front of a bean to run the advice.", "A cashier who stands between you and the till.", "CGLIB subclass of the service"),
]
STORY = [
    ("120 copies", "Paysetu's services each started a timer, ran, then wrote an audit row, by hand. The copies drifted: some forgot failures, some forgot the audit."),
    ("Half missing", "A compliance review found that half the money-moving methods left no audit trail at all."),
    ("The fix, and its limits", "One @Audited annotation and one aspect replace every copy. Then the team learned where Spring's aspects cannot reach: calls inside the same class, final methods, private methods."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Write the shared behaviour once, and know exactly which calls it can see.</p>

<h2>What are we building?</h2>
<p><code>POST /payouts</code> pays a merchant's balance out to a bank account (a record). Every call, accepted or refused, leaves one audit event with its outcome and duration, readable at <code>GET /audit-events</code>. The payout code has no timing or audit lines: one annotation does it.</p>

<h2>An everyday analogy</h2>
<p>A bank branch where every counter must log each transaction. Instead of every clerk keeping their own notebook (and some forgetting), a supervisor stands at the entrance to each counter and logs everyone who goes up to it. A clerk who walks to the next counter through the back door is not logged: the supervisor only sees the front.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Spring sees</strong> <code>@Audited</code> on a bean's method and wraps the bean in a proxy.</li>
<li><strong>A call from another bean</strong> reaches the proxy; the aspect starts a timer.</li>
<li><strong>The real method runs</strong>, inside its transaction.</li>
<li><strong>The aspect writes</strong> one event, SUCCESS or FAILURE, and passes the result or the exception on unchanged.</li>
</ol>

<details class="qa check"><summary>Check yourself: why is a method called with <code>this.monthly()</code> not audited?</summary><p>The aspect lives in the proxy. <code>this</code> is the real object behind it, so the call never passes the proxy. The same is true for <code>@Transactional</code> (station 055).</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real payouts.</strong> Records only.</li>
<li><strong>No metrics system.</strong> Durations go to the audit table and the log.</li>
<li><strong>No login.</strong> Who did it is challenge 2.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Paysetu</strong> (a fictional payments company) must be able to show who asked for every payout, when, and with what result. The hand-written audit code was missing from half the methods that move money.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a ₹10,000 payout from Chaiwala Traders (₹50,000), <b>then</b> <code>201</code>, balance ₹40,000, and one SUCCESS event with subject 1 and a duration.</li>
<li><b>Given</b> a ₹500 payout from Desi Spices (₹200), <b>then</b> <code>422</code>, balance unchanged, and one FAILURE event: "Not enough balance".</li>
<li><b>Given</b> a payout the database refuses after the debit, <b>then</b> the debit is rolled back and the FAILURE event is still there.</li>
<li><b>Given</b> any event, <b>then</b> it never contains the account number.</li>
<li><b>Given</b> a malformed body, <b>then</b> <code>400</code> and no event (the audited method was never called); an unknown payout, <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Timing and audit live in one aspect; business methods carry only the annotation.</li>
<li>The aspect never changes a result or an exception.</li>
<li>It records only the parameter named for it, never all arguments.</li>
<li>Failure events survive the business transaction's rollback.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Write an aspect with a pointcut on a custom annotation and around advice.</li>
<li>Explain how Spring's proxies apply aspects, and order them against transactions.</li>
<li>Know the limits: self-invocation, final and private methods.</li>
<li>Keep an audit log useful and free of personal data.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/payouts</code>", "A payout: <code>merchantId</code>, <code>amountPaise</code> (₹1 to ₹10 lakh), <code>ifsc</code>, <code>accountNumber</code>. Audited as <code>PAYOUT_REQUESTED</code>."],
    ["<code>GET</code>", "<code>/payouts/{id}</code>", "The payout record."],
    ["<code>GET</code>", "<code>/audit-events?action=&amp;limit=20</code>", "Audit events, newest first, optionally of one action; 1 to 100."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Payout recorded; <code>Location</code> points at it"],
    ['<span class="pill ok">200</span>', "A payout; the audit events"],
    ['<span class="pill warn">400</span>', "Malformed payout, or a limit outside 1 to 100"],
    ['<span class="pill warn">404</span>', "No such payout"],
    ['<span class="pill warn">422</span>', "Unknown merchant, or not enough balance"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against one fresh database. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-a-payout", "Case 1: ₹10,000 from Chaiwala Traders", "<b>Why:</b> recorded: <code>201</code>, and audited."),
    ("02-read-it-back", "Case 2: read it back", "<b>Why:</b> not audited: only <code>@Audited</code> methods are."),
    ("03-not-enough-balance", "Case 3: ₹500 from Desi Spices (₹200)", "<b>Why:</b> <code>422</code>, and a FAILURE event."),
    ("04-an-unknown-merchant", "Case 4: merchant 99", "<b>Why:</b> <code>422</code>, and a FAILURE event."),
    ("05-a-bad-ifsc", "Case 5: an IFSC without its 0", "<b>Why:</b> <code>400</code> before the service: no event."),
    ("06-the-audit-log", "Case 6: the audit log", "<b>Why:</b> three events, newest first, with durations; no account numbers."),
    ("07-no-such-payout", "Case 7: payout 99", "<b>Why:</b> <code>404</code>."),
]) + """
<h2>The aspect's log lines</h2>
<p class="muted">From the running app's log during the captures (<code>docs/captures/app-log.txt</code>): the timing, written by the same advice.</p>
""" + code(read("docs/captures/app-log.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A payout", "Recorded, debited, one SUCCESS event", "<code>aPayoutIsRecordedAndAudited</code>"],
    ["Not enough balance", "<code>422</code>, one FAILURE event", "<code>aRefusedPayoutIsAuditedAsAFailure</code>"],
    ["The account number", "Never in the audit table", "<code>theAuditLogNeverHoldsTheAccountNumber</code>"],
    ["Several events; a filter", "Newest first; filtered by action", "<code>eventsComeNewestFirstAndCanBeFiltered</code>"],
    ["Malformed bodies; a bad limit", "<code>400</code>, no events", "<code>malformedPayoutsAre400AndNeverReachTheAuditedMethod</code>"],
    ["Unknown merchant; unknown payout", "<code>422</code>; <code>404</code>", "<code>unknownMerchantsAre422AndUnknownPayouts404</code>"],
    ["Bad rows written directly", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"],
    ["Refused after the debit", "Debit rolled back; FAILURE event kept", "<code>aPayoutTheDatabaseRefusesAfterTheDebitIsRolledBackButStillAudited</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Expecting aspects to run on private, final or self-invoked methods.</p>
<p>The trap test registers a small test-only bean, <code>MonthEndReports</code>, whose methods all carry <code>@Audited</code>, and checks that Spring proxied it. Called from outside, <code>monthly()</code> leaves one event. Called through <code>dailyThenMonthly()</code>, which calls <code>this.monthly()</code>, it leaves none. A <code>final</code> method leaves none, and worse: it runs on the proxy object itself, whose injected field was never set, so it sees <code>null</code>. A <code>private</code> method leaves none.</p>
<p>While building, each part was undone once. Without the annotation on <code>request</code>, 4 tests turned red. Ordering the aspect inside the transaction, 3: the FAILURE events were rolled back with the payouts they described. Recording every argument, 5 (the account number reached the audit table). Swallowing the exception instead of rethrowing it, 4. One real bug was found: <code>@Order(HIGHEST_PRECEDENCE)</code> made every audited call fail with "JoinPointMatch was NOT bound", because the aspect then runs before Spring's <code>ExposeInvocationInterceptor</code>. <code>@Order(0)</code> still wraps the transaction.</p>
</div>
""" + code(read(T + "ProxyLimitsTrapTest.java"), "java") + code(read(T + "MonthEndReports.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "PayoutController.java", dwn("Validates the payout; reads payouts and audit events.", "HTTP only; calls the service through its proxy.", "Validation inside the audited method (so a bad body would be audited).")),
    (J + "PayoutService.java", dwn("Debits the balance if it can, then records the payout, in one transaction.",
        "One annotation instead of timing and audit code.", "The 121st copy-paste.")),
    (J + "Audited.java", dwn("The annotation: an action name and the parameter that names the subject.", "Explicit about what is recorded.", "Logging every argument.")),
    (J + "AuditAspect.java", dwn("Around every <code>@Audited</code> call: time, run, record, rethrow.",
        "One place for the cross-cutting code; its order puts it outside the transaction.", "Lost failure events; changed exceptions.",
        "<ul><li><code>@annotation(audited)</code> binds the annotation itself, so the advice reads <code>action()</code>.</li><li><code>@Order(0)</code>: ahead of the transaction advisor, behind Spring's own <code>ExposeInvocationInterceptor</code>.</li><li>The subject comes from the one named parameter, found by name.</li></ul>")),
    (J + "AuditLog.java", "<p>Writes and reads <code>audit_events</code>.</p>"),
    (M + "V1__merchants_payouts_audit.sql", "<p>Merchants, payouts and audit events, with named constraints.</p>"),
    (M + "V2__demo_merchants.sql", "<p>Two merchants and their balances.</p>"),
    ("pom.xml", "<p><code>spring-boot-starter-aspectj</code> (Boot 4's name for the AOP starter).</p>"),
    (J + "PayoutsApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/056-timing-and-auditing-with-spring-aop/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/paysetu/payouts/
│   ├── PayoutController.java   ├── PayoutService.java   ├── Audited.java   ├── AuditAspect.java
│   ├── AuditLog.java   └── PayoutsApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__merchants_payouts_audit.sql, V2__demo_merchants.sql
├── src/test/java/com/paysetu/payouts/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
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
""" + code("""docker compose up -d        # PostgreSQL 17 on localhost:5432
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Make <code>request</code> in <code>PayoutService</code> <code>final</code> and run the contract tests:</p>
""" + code("""./mvnw test -Dtest=PayoutContractTest""", "bash") + """
<p>Nothing is audited any more, and the method runs on the proxy, where <code>jdbc</code> is <code>null</code>. Remove <code>final</code>.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["An annotated method is never advised", "Self-invocation, or the method is private or final.", "Call it from another bean; make it public and not final."],
    ["<code>NullPointerException</code> on an injected field in a final method", "The final method ran on the proxy, whose fields are empty.", "Do not make proxied methods final."],
    ["<code>Required to bind 2 arguments, but only bound 1 (JoinPointMatch was NOT bound)</code>", "The aspect is ordered at <code>HIGHEST_PRECEDENCE</code>, before Spring's own interceptor.", "Any order after it, such as <code>@Order(0)</code>."],
    ["Failure events disappear", "The aspect runs inside the transaction and is rolled back with it.", "Order it ahead of the transaction advisor."],
    ["Which starter brings AOP?", "In Boot 4 it is <code>spring-boot-starter-aspectj</code> (the one this project uses).", "Add it; Boot then turns on <code>@Aspect</code> beans."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the aspect and the database.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>PayoutContractTest</code> ({cnt('PayoutContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>ProxyLimitsTrapTest</code> ({cnt('ProxyLimitsTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>PayoutDatabaseTest</code> ({cnt('PayoutDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "ProxyLimitsTrapTest.java", "<p>Written first: which calls the aspect can see.</p>"),
    (T + "PayoutContractTest.java", "<p>Payouts and their events, and every refusal.</p>"),
    (T + "PayoutDatabaseTest.java", "<p>Named constraints; a rollback with its FAILURE event kept.</p>"),
    (T + "MonthEndReports.java", "<p>Test-only bean: one audited method reached four ways.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: no payouts or events, balances reset.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/paysetu/payouts/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=CancelPayoutChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in (Java files and one migration), all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Cancel a payout", "Beginner-friendly", 25,
    "Add <code>POST /payouts/{id}/cancellation</code>: REQUESTED becomes CANCELLED and the money returns to the balance. Audit it as <code>PAYOUT_CANCELLED</code>, subject the payout id, without writing any audit code.",
    "the test in <code>CancelPayoutChallengeTest</code> passes.",
    ["<code>@Audited(action = \"PAYOUT_CANCELLED\", subjectParam = \"payoutId\")</code> on a public method of the service.",
     "Lock the payout row so two cancellations cannot both refund."],
    "challenge/CancelPayoutChallengeTest.java", ["challenge/solution/PayoutService.java", "challenge/solution/PayoutController.java"]) + challenge(2, "Who did it", "Go deeper", 30,
    "Record the actor on every event: the <code>X-Operator</code> header of the HTTP request, or \"system\" outside one. A migration adds the column with a check.",
    "the test in <code>OperatorChallengeTest</code> passes.",
    ["<code>RequestContextHolder.getRequestAttributes()</code> is the current request, or <code>null</code> outside one.",
     "The aspect changes; no service does."],
    "challenge/OperatorChallengeTest.java", ["challenge/solution/V3__audit_actor.sql", "challenge/solution/AuditAspect.java", "challenge/solution/AuditLog.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Aspect, filter, or a plain call?</h2>
<p>Timing every HTTP request, auditing payouts, and retrying a flaky bank call: for each, choose a servlet filter, an aspect, or an explicit call in the code. What does each choice hide from the next reader, and what does it stop people forgetting?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, mapping"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: one audited method, reached four ways.</li>
<li>Design the annotation: what is recorded, and what never is.</li>
<li>Write the around advice; rethrow everything; order it against the transaction.</li>
<li>Delete the copy-pasted code; test that refusals and rollbacks are still audited.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Custom annotation + around aspect", "Behaviour not visible in the method body; proxy limits.", '<span class="pill ok">Chosen</span>'],
    ["Copy-pasted timing and audit code", "Drifts and goes missing.", '<span class="pill bad">The problem</span>'],
    ["A pointcut on a package (<code>execution(* com.paysetu..*Service.*(..))</code>)", "No annotation to forget; audits methods nobody meant to.", '<span class="pill warn">Too wide here</span>'],
    ["Servlet filter", "Sees HTTP requests only, not service calls from jobs.", '<span class="pill warn">For request timing</span>'],
    ["Micrometer <code>@Timed</code> / <code>@Observed</code>", "Metrics and traces, not an audit trail.", '<span class="pill warn">For timing</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Constraints"], [
    ["<code>merchants</code>", "<code>merchants_balance_not_negative</code>"],
    ["<code>payouts</code>", "<code>payouts_merchant_fk</code>, <code>payouts_amount_range</code>, <code>payouts_ifsc_shape</code>, <code>payouts_status_known</code>"],
    ["<code>audit_events</code>", "<code>audit_events_outcome_known</code>, <code>audit_events_error_on_failure</code>, <code>audit_events_duration_not_negative</code>"]]) + """
""" + code(read(M + "V1__merchants_payouts_audit.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Audit is evidence</dt><dd>An audit table is useful only if it is complete and nobody edits it. Restrict UPDATE and DELETE on it to nobody, and keep it longer than the business data.</dd>
<dt>No personal data by default</dt><dd>Record identifiers and outcomes, not arguments. Account numbers, names and addresses copied into logs spread everywhere logs go.</dd>
<dt>Cost</dt><dd>Every audited call writes a row. For hot paths, write asynchronously or batch, and accept the small window that opens.</dd>
<dt>Failure of the audit itself</dt><dd>If the audit insert fails, this aspect's exception replaces the business result. Decide which matters more: for money, failing loudly is usually right.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What are a pointcut and an advice?", "The pointcut selects join points (here: methods annotated with @Audited); the advice is the code run at them (here: around, so it can time the call and see its outcome)."),
    ("How does Spring apply aspects?", "It creates a proxy for each bean with advised methods, a JDK interface proxy or a CGLIB subclass, and runs the advice when calls go through the proxy."),
    ("Why are final and private methods not advised?", "A CGLIB proxy works by overriding methods. Final methods cannot be overridden; private ones are not visible. A final method even runs on the proxy instance, whose fields are empty."),
    ("How do you order an aspect against @Transactional?", "With @Order: a lower value runs outside. The transaction advisor has the lowest precedence by default, so @Order(0) wraps it."),
    ("When is an aspect the wrong tool?", "When the behaviour is the point of the method (put it in the code), or when readers must see it to understand the method. Aspects suit concerns that are the same everywhere."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You made a method final and explained what broke."],
    ["AOP", "Annotation, pointcut, around advice.", "You can order it against transactions."],
    ["Proxies", "You know the three limits.", "You can explain the null field in a final method."],
    ["Audit", "Every outcome recorded.", "No personal data, and a plan for the audit insert failing."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any aspect:</p>
<ul class="rules">
<li>Are the advised methods public, not final, and called from other beans?</li>
<li>Does the advice ever change the result or swallow an exception?</li>
<li>Where does it sit relative to transactions, and is that on purpose?</li>
<li>What data does it copy, and where does that data end up?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
