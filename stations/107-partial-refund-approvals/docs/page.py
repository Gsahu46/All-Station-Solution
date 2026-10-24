"""Station 107 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 107,
    "stack": "Spring Boot 4.1.1 · Java 25 · JdbcClient · @Transactional domain service · Spring Security (HTTP Basic) · PostgreSQL 17 · Flyway · Testcontainers",
    "simulation": "No money moves: an approved refund is a record, and sending it to the payment provider is not part of this station. Orders, customers and staff are demo data.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/kartwala/refunds/"
T = "src/test/java/com/kartwala/refunds/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Partial refund", "Giving back part of what was paid for an order.", "Getting ₹500 back for a dented box.", "<code>POST /orders/{id}/refunds</code>"),
    ("Second approver", "A different person who must agree before a large refund goes ahead.", "A cheque that needs two signatures.", "above ₹5,000"),
    ("Invariant", "A rule that must be true at every moment, whatever happens.", "A bank balance never below zero.", "refunds ≤ the order's total"),
    ("Race", "Two requests at the same moment, each checking before the other has saved.", "Two people booking the last seat on two screens.", "the trap"),
    ("Conditional update", "An UPDATE that changes the row only if a condition still holds, checked and written in one step.", "\"Take one if any are left\" said to the shopkeeper, not two separate questions.", "<code>reserved + amount &lt;= total</code>"),
    ("Domain service", "One class that holds the business rules of an activity.", "The refunds desk's rulebook.", "<code>Refunds</code>"),
]
STORY = [
    ("Partial refunds", "Kartwala's agents give partial refunds: a dent, a missing part, a late delivery. Above ₹5,000, a second person must approve."),
    ("More back than paid", "An angry customer called again and again. Several agents refunded the same order at the same moment. Each one's screen checked \"what is left\" before the others had saved, and together they refunded more than the order cost."),
    ("The fix", "The amount is reserved on the order in one step that checks and writes together, so refunds at the same moment take turns. Pending refunds count. The database refuses any total above the order, from any program."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A rule checked in one step and acted on in another is not a rule when two people act at once. Check and write together, and let the database hold the line.</p>

<h2>What are we building?</h2>
<p>A refund workflow: agents ask, small refunds are approved at once, large ones wait for a different approver, and the total never passes the order.</p>

<h2>An everyday analogy</h2>
<p>A shared envelope of cash for one order. Each refund is taken out of the envelope, never counted from a list; when the envelope is empty, nobody can take more, however many people reach for it at once.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Reserve</strong>: take the amount from what is left on the order, only if it fits, in one step.</li>
<li><strong>Record</strong>: up to ₹5,000, approved at once; above, waiting for a second person.</li>
<li><strong>Decide</strong>: a different approver approves, or rejects and gives the amount back.</li>
<li><strong>Guard</strong>: the database itself refuses a total above the order.</li>
</ol>

<details class="qa check"><summary>Check yourself: why do pending refunds count against the order?</summary><p>Otherwise two large refunds could each wait for approval, each fitting on its own, and both be approved: more than the order again. Reserving at the request keeps the promise honest.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No payment provider.</strong> An approved refund is a record; sending it is another step (challenge 3).</li>
<li><strong>No order system.</strong> Three demo orders.</li>
<li><strong>No real sign-in.</strong> Four demo staff with HTTP Basic.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Kartwala</strong> (a fictional online store): partial refunds once added up to more than the order. Large refunds must have a second approver.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo rule: above ₹5,000 (500000 paise) needs a second person. Money in paise.</p>
<ol class="gwt">
<li><b>Given</b> an agent and an amount that fits, <b>then</b> <code>201</code>; up to ₹5,000 <code>APPROVED</code>, above <code>PENDING_APPROVAL</code>.</li>
<li><b>Given</b> more than is left (pending refunds included), <b>then</b> <code>409</code> with what is left.</li>
<li><b>Given</b> an approver who did not ask, <b>then</b> approve or reject; a rejection gives the amount back. The asker gets <code>403</code>; a second decision <code>409</code>.</li>
<li><b>Given</b> any number of refunds at the same moment, <b>then</b> the total never passes the order.</li>
<li><b>Given</b> bad input, unknown orders or refunds, or the wrong role, <b>then</b> <code>400</code>, <code>404</code>, <code>401</code>/<code>403</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>The total rule is a named database constraint, tested with plain SQL.</li>
<li>Four eyes is a named constraint too.</li>
<li>A refund that cannot be recorded reserves nothing.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Model a multi-step workflow with states and who may move between them.</li>
<li>Keep an invariant over partial amounts under concurrency.</li>
<li>Put the same rule in code and in the database.</li>
<li>Prove it with a real concurrency test.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Who", "Purpose"], [
    ["<code>POST</code>", "<code>/orders/{id}/refunds</code>", "agent", "Ask for a refund: <code>{amountPaise, reason}</code>."],
    ["<code>POST</code>", "<code>/refunds/{id}/approvals</code>", "approver", "<code>{decision: APPROVE | REJECT}</code>."],
    ["<code>GET</code>", "<code>/orders/{id}</code>", "both", "Total, reserved, remaining, and the order's refunds."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span> / <span class="pill ok">200</span>', "Refund recorded / decided"],
    ['<span class="pill warn">400</span>', "Amount not positive, no reason, unknown decision"],
    ['<span class="pill warn">401</span> / <span class="pill warn">403</span>', "Not signed in / wrong role, or deciding your own request"],
    ['<span class="pill warn">404</span>', "No such order or refund"],
    ['<span class="pill warn">409</span>', "More than is left (with <code>remainingPaise</code>); already decided"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-a-small-refund", "Case 1: ₹2,500 on the ₹12,500 washing machine", "<b>Why:</b> up to ₹5,000: approved at once."),
    ("02-a-large-refund", "Case 2: ₹9,000 on the same order", "<b>Why:</b> above ₹5,000: waits; the amount is already reserved."),
    ("03-the-asker-tries-to-approve", "Case 3: meena (agent and approver) asks for ₹6,000 on the phone", "<b>Why:</b> waits for a second person."),
    ("04-and-is-refused", "Case 4: meena approves her own request", "<b>Why:</b> <code>403</code>: four eyes."),
    ("05-another-approver-approves", "Case 5: raj approves case 2", "<b>Why:</b> <code>200</code>, approved by raj."),
    ("06-more-than-is-left", "Case 6: ₹2,000 more on the washing machine", "<b>Why:</b> ₹2,500 + ₹9,000 are taken: ₹1,000 left, so <code>409</code>."),
    ("07-the-order-afterwards", "Case 7: the washing machine order", "<b>Why:</b> reserved = the two refunds."),
    ("08-a-rejection", "Case 8: raj rejects meena's request", "<b>Why:</b> rejected; the ₹6,000 goes back to the phone order."),
    ("09-decided-already", "Case 9: raj tries to approve it after all", "<b>Why:</b> <code>409</code>: a decision is final."),
    ("10-no-such-order", "Case 10: no such order", "<b>Why:</b> <code>404</code>."),
    ("11-a-zero-refund", "Case 11: ₹0", "<b>Why:</b> <code>400</code>."),
    ("12-an-agent-tries-to-approve", "Case 12: an agent approves", "<b>Why:</b> <code>403</code>: not an approver."),
]) + """
<h2>Twenty at once</h2>
<p class="muted"><code>docs/capture.sh</code> sends twenty ₹1,000 refunds for the ₹4,999 mixer at the same moment. Status codes, counted:</p>
""" + code(read("docs/captures/burst-summary.txt").strip(), "text") + examples([
    ("13-the-mixer-afterwards", "Case 13: the mixer order afterwards", "<b>Why:</b> four refunds, ₹4,000 reserved, ₹999 left."),
]) + """
<p class="muted">And a hand-written UPDATE in <code>psql</code> that tries to reserve more than the order:</p>
""" + code(read("docs/captures/db-guard.txt").strip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["The old Java check, 20 at once", "More than 4 refunds of ₹1,000 on ₹4,999", "<code>theOldJavaCheckLetsConcurrentRefundsAddUpToMoreThanTheOrder</code>"],
    ["The API, 20 at once", "Exactly 4; 16 <code>409</code>s", "<code>theApiAcceptsOnlyWhatFitsUnderTwentyAtOnce</code>"],
    ["40 at once, mixed amounts", "Never past the total; reserved equals the refunds", "<code>manyAgentsWithDifferentAmountsNeverPassTheTotal</code>"],
    ["Two approvers at once", "One decides; the other gets <code>409</code>", "<code>twoApproversAtTheSameMomentDecideARefundOnce</code>"],
    ["An approval and a rejection at once, 10 rounds", "One wins; the order stays consistent", "<code>anApprovalAndARejectionAtOnceLeaveTheOrderConsistent</code>"],
    ["₹5,000 and ₹5,000.01", "Approved at once; waits", "<code>upToFiveThousandRupeesIsApprovedAtOnceAboveItWaitsForASecondPerson</code>"],
    ["The asker approves; a rejection; a second decision", "<code>403</code>; amount back; <code>409</code>", "<code>theAskerCannotApproveARejectionGivesTheAmountBackAndADecisionIsFinal</code>"],
    ["More than is left", "<code>409</code>, ₹ and paise left", "<code>moreThanIsLeftIs409WithWhatIsLeft</code>"],
    ["Bad input, unknown ids, wrong roles", "<code>400</code>, <code>404</code>, <code>401</code>, <code>403</code>", "<code>badInputIs400UnknownThingsAre404AndRolesAreChecked</code>"],
    ["Plain SQL against the rules", "Refused by named constraints", "<code>theRulesAreNamedConstraintsInTheDatabase</code>"],
    ["A refund that cannot be recorded", "Nothing reserved", "<code>aRefundThatCannotBeRecordedReservesNothing</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Checking the refund total only in Java, so concurrent refunds exceed the order.</p>
<ul>
<li><strong>The old way.</strong> Add up the order's refunds, compare with the total, insert. Between the check and the insert the old code asked the payment provider whether the card could take a refund (100 ms in the test). Twenty ₹1,000 refunds at once on a ₹4,999 order: more than four pass, because each check ran before the others were saved.</li>
<li><strong>The API.</strong> The same twenty: exactly four, because the check and the reservation are one UPDATE on the order's row, and requests queue on it.</li>
</ul>
<p>While building, each part was undone once: no condition in the UPDATE (the database's CHECK still refused the excess, but as a <code>500</code>) turned 3 tests red; no row lock on decisions 1; rejections that keep the amount 2; the asker allowed to approve 1; exactly ₹5,000 needing approval 1; no transaction around the request 1; decisions not final 3; agents allowed to approve 1.</p>
</div>
""" + code(read(T + "RefundOverlapTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "RefundController.java", dwn("The endpoints.", "Validates input; one status and a plain sentence per rule; amounts in rupees in messages, paise in fields.", "A 500 for a full order; a reason nobody can read.")),
    (J + "Refunds.java", dwn("The domain service.", "Reserve with one conditional UPDATE, then record; decide under a row lock; give the amount back on rejection.", "Two refunds that each fit, together more than the order; two approvers deciding one refund.",
        "<ul><li>The approval limit is copied onto each refund (<code>needs_second_approval</code>), so changing the limit later does not change what an old request needed.</li></ul>")),
    (J + "SecurityConfig.java", "<p>HTTP Basic, demo staff; agents ask, approvers decide.</p>"),
    (M + "V1__orders_and_refunds.sql", dwn("Orders and refunds.", "The total and four-eyes rules as named constraints.", "Any program, script or console writing past the rules.")),
    (M + "V2__demo_orders.sql", "<p>Three demo orders.</p>"),
    ("src/main/resources/application.yaml", "<p>The database and the approval limit.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
]
tree = """stations/107-partial-refund-approvals/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/refunds/
│   ├── RefundController.java   ├── Refunds.java   ├── SecurityConfig.java   ├── ProblemResponses.java   └── RefundsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__orders_and_refunds.sql, V2__demo_orders.sql
├── src/test/java/com/kartwala/refunds/   (see Tests)
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
""" + code("""docker compose up -d --wait   # PostgreSQL 17 on localhost:5432
./mvnw spring-boot:run        # the API on http://localhost:8080
./mvnw test                   # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d --wait
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Send twenty refunds at once and count the answers:</p>
""" + code("""for i in $(seq 1 20); do curl -s -o /dev/null -w '%{http_code}\\n' -u asha:asha-demo-pass -H 'Content-Type: application/json' \\
  -d '{"amountPaise":100000,"reason":"Customer called again"}' localhost:8080/orders/5002/refunds & done | sort | uniq -c""", "bash") + """
<p>Four <code>201</code>s, sixteen <code>409</code>s. Then copy the Review tab's <code>Refunds.java</code> over the real one, restart, run <code>docker compose down -v &amp;&amp; docker compose up -d --wait</code> for a fresh database, and try again.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>500</code> with <code>orders_refunds_within_total</code> in the log", "Something wrote past the total without the conditional UPDATE.", "Reserve with <code>... WHERE reserved_paise + :amount &lt;= total_paise</code> and map 0 rows to <code>409</code>."],
    ["<code>409 already APPROVED</code> for an approver who clicked once", "Two approvers at the same moment; the other one won.", "Expected: read the refund to see who decided."],
    ["Refunds wait a long time under load", "Requests queue on one hot order's row.", "Expected for one order; different orders do not wait for each other."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the database.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>RefundContractTest</code> ({cnt('RefundContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>RefundOverlapTrapTest</code> ({cnt('RefundOverlapTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>RefundDatabaseTest</code> ({cnt('RefundDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Concurrency", "A real concurrency test that proves the invariant holds", f"<code>RefundConcurrencyTest</code> ({cnt('RefundConcurrencyTest')}), and the trap test", '<span class="pill ok">pass</span>']]) + """
<p class="muted">Concurrency is real: virtual threads released together by a latch, against PostgreSQL 17 in Docker, and the totals are counted from the refunds themselves, not from the API's answers.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "RefundOverlapTrapTest.java", "<p>Written first: the Java check and the API, twenty at once.</p>"),
    (T + "RefundConcurrencyTest.java", "<p>Approvers at once; mixed amounts at once.</p>"),
    (T + "RefundContractTest.java", "<p>The workflow, its answers and its roles.</p>"),
    (T + "RefundDatabaseTest.java", "<p>Named constraints with plain SQL; a rollback.</p>"),
    (T + "ApiTest.java", "<p>Shared setup and the counts the tests trust.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/kartwala/refunds/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=RejectionNoteChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Say why", "Beginner-friendly", 25,
    "The customer is told why a refund was refused. A <code>REJECT</code> needs a <code>note</code> (1 to 200 characters), kept with the refund as <code>decisionNote</code>; an approval needs none.",
    "both tests in <code>RejectionNoteChallengeTest</code> pass.",
    ["A new migration, <code>V3__...sql</code>, adds the column: never edit V1 once it has run.",
     "Check \"note required for REJECT\" in the controller; the column may stay nullable."],
    "challenge/RejectionNoteChallengeTest.java", ["challenge/solution/V3__decision_note_and_first_approver.sql", "challenge/solution/RefundController.java", "challenge/solution/Refunds.java"]) + challenge(2, "Two approvers for the biggest", "Go deeper", 40,
    "Above ₹50,000, a refund needs two different approvers, neither of them the asker. The first approval is recorded as <code>firstApprovedBy</code> and the refund keeps waiting; the same person cannot give both; the database refuses it too (<code>refunds_two_different_approvers</code>).",
    "both tests in <code>TwoApproversChallengeTest</code> pass.",
    ["Copy the second limit onto the refund at request time, like <code>needs_second_approval</code>.",
     "The row lock in <code>decide</code> already keeps two approvals from overlapping.",
     "A CHECK can compare two columns of the same row."],
    "challenge/TwoApproversChallengeTest.java", ["challenge/solution/V3__decision_note_and_first_approver.sql", "challenge/solution/Refunds.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Refunds that really move money</h2>
<p>Approved refunds must now go to the payment provider. Design the step: when it is called (inside the approval's transaction or after it), what happens when the provider times out, how a retry avoids paying twice (its idempotency key), and what the order shows while a refund is \"approved but not yet paid\".</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the Java check, twenty at once.</li>
<li>Keep a running reserved amount on the order, guarded by a CHECK.</li>
<li>Reserve with a conditional UPDATE; 0 rows means <code>409</code>.</li>
<li>Decisions under a row lock; rejections release; four eyes in code and in the database.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Reserved amount on the order + conditional UPDATE + CHECK", "One column kept in step with the refunds.", '<span class="pill ok">Chosen</span>'],
    ["Sum in Java, then insert", "Correct alone; wrong at the same moment.", '<span class="pill bad">The trap</span>'],
    ["<code>SELECT ... FOR UPDATE</code> on the order, then sum", "Also correct; two statements and a lock to remember.", '<span class="pill warn">Fine too</span>'],
    ["SERIALIZABLE isolation", "Correct; callers must retry serialization failures.", '<span class="pill warn">Fine with retries</span>'],
    ["A trigger that sums refunds", "Rule in the database only; harder to read and test.", '<span class="pill warn">Possible</span>']]) + """
<h2>Database design</h2>
""" + table(["Constraint", "Rule", "Why"], [
    ["<code>orders_refunds_within_total</code>", "0 ≤ reserved ≤ total", "The invariant, for any writer."],
    ["<code>refunds_second_person</code>", "the decider is not the asker, when approval is needed", "Four eyes."],
    ["<code>refunds_decided_by_someone</code>", "a decided refund has a decider", "Nothing approved by nobody."],
    ["<code>refunds_small_not_pending</code>", "a refund that needs no approval is approved", "No refunds stuck waiting for nothing."],
    ["<code>refunds_amount_positive</code>, <code>refunds_status</code>", "amount &gt; 0; known states", "No zero or negative refunds; no invented states."]]) + """
<p><strong>Transaction boundaries:</strong> a request reserves and records in one transaction (a failed insert releases the reservation); a decision locks the refund, updates it and, on rejection, the order, in one transaction.</p>
""" + code(read(M + "V1__orders_and_refunds.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["14. Operations: metric, alert, rollback, runbook, failure drill", "15. Real-world considerations"],
               "What changes when this runs for real.") + """
<h2>Real-world considerations</h2>
<dl class="facts">
<dt>Audit</dt><dd>Who asked, who decided, when, and the reason: kept with each refund. For disputes, this is the record.</dd>
<dt>Hot orders</dt><dd>Requests for one order queue on its row: fine for refunds, which are rare per order. A design that makes thousands of writes to one row needs another shape.</dd>
<dt>The limit in rupees</dt><dd>Change it in configuration; old requests keep what they needed, because the need is copied onto each refund.</dd>
<dt>Pending for ever</dt><dd>A refund nobody decides blocks part of the order. Alert on pending refunds older than a day; expire them after a policy period.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why does a sum-then-insert check fail under concurrency?", "Each transaction checks before the others commit; at READ COMMITTED all see the old sum and all insert."),
    ("How do you make it safe?", "Check and write in one statement (a conditional UPDATE), or lock the parent row first, and back it with a database constraint."),
    ("Why keep the rule in the database too?", "Every writer obeys it: a script, a batch job, a second service, a future teammate."),
    ("How do you test it?", "Many threads released together against a real database, then count the stored rows, not the HTTP answers."),
    ("What is four eyes, and where do you enforce it?", "A different person must approve; in the service, and as a constraint so no path can skip it."),
    ("What is a domain service?", "A class that holds one activity's rules and transactions, so controllers stay thin and the rules live in one place."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Invariant", "Checked in code.", "Checked in one statement and held by a named constraint, proven by a concurrency test."],
    ["Workflow", "States work.", "Every move has a role, a rule and a test, including the races."],
    ["Money", "Paise.", "Paise in data, rupees in messages, no doubles anywhere."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("The total checked in Java",
     "\"One query fewer, the same rule\": the sum and the insert are two steps. Each request sees the total before the others are saved; at the same moment they all fit, and together they pass the order. And the reserved amount is no longer kept, so pending refunds stop counting too.",
     "<code>theApiAcceptsOnlyWhatFitsUnderTwentyAtOnce</code> and <code>manyAgentsWithDifferentAmountsNeverPassTheTotal</code> fail: more refunded than the order; <code>anApprovalAndARejectionAtOnceLeaveTheOrderConsistent</code> and <code>upToFiveThousandRupeesIsApprovedAtOnceAboveItWaitsForASecondPerson</code> fail: the order's reserved amount is no longer kept, so the database's guard has nothing to guard."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate \"simplifies\" the request: \"why keep a running total when the refunds are right there? Add them up and compare.\" Read the file and list every problem before opening the findings.</p>
<p class="path">review/Refunds.java</p>
""" + code(read("review/Refunds.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">One agent at a time, the flawed version is right. It fails on the day one customer calls five times.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
