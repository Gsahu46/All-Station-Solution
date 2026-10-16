"""Station 057 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 57,
    "stack": "Spring Boot 4.1.1 · Java 25 · @Transactional propagation (REQUIRED, REQUIRES_NEW) · TransactionSynchronization afterCompletion · JdbcClient · PostgreSQL 17 · Flyway · Testcontainers",
    "simulation": "Accounts and transfers are demo data, not Tijori's. A transfer changes two balances and writes a record: no bank network (IMPS, NEFT, UPI) is involved.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tijori/transfers/"
T = "src/test/java/com/tijori/transfers/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Rollback", "Undoing every change a transaction made.", "Tearing up a bill that was never paid.", "A failed transfer"),
    ("Propagation", "What a transactional method does when a transaction is already open.", "Joining the same bill, or opening your own.", "<code>REQUIRED</code>, <code>REQUIRES_NEW</code>"),
    ("REQUIRED", "Join the caller's transaction; start one only if there is none.", "Adding a line to the same bill.", "<code>TransferService.transfer</code>"),
    ("REQUIRES_NEW", "Pause the caller's transaction and run in a new one that commits on its own.", "A separate receipt, signed at once.", "<code>AuditTrail.record</code>"),
    ("Transaction synchronization", "Code Spring calls when the transaction ends.", "A note to phone the customer once the bill is settled, or torn up.", "<code>afterCompletion</code>"),
    ("Attempt id", "One id shared by every event of one transfer attempt.", "A token number at a counter.", "<code>attempt_id</code>"),
]
STORY = [
    ("Audit every attempt", "Regulators and fraud teams want every transfer attempt recorded, especially the failed ones: those are where fraud shows."),
    ("The failures vanished", "Tijori's code caught the failure and wrote an audit row, then rethrew. The transaction rolled back, as it should, and took the audit row with it. The trail showed only successes."),
    ("The fix", "Write audit rows in a transaction of their own (REQUIRES_NEW), and write the outcome only when the transfer's transaction has really ended."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A record that must outlive a failure cannot live inside the failing transaction.</p>

<h2>What are we building?</h2>
<p><code>POST /transfers</code> records a transfer between two accounts: two balances change and a transfer record is written. Every attempt leaves events in the audit trail: one when it starts, and one outcome, COMPLETED or FAILED with a reason. <code>GET /audit-events?accountId=…</code> shows an account's trail, failures included.</p>

<h2>An everyday analogy</h2>
<p>A bank's visitor register at the door. You sign it when you walk in, whatever happens at the counter. If your request is refused, the counter tears up your form, but nobody tears a page out of the visitor register. The old code kept the register on the counter, inside the form.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>The transfer starts</strong> its transaction, and records TRANSFER_ATTEMPTED in a separate one, committed at once.</li>
<li><strong>It debits, credits, records</strong> the transfer; any refusal throws and rolls back.</li>
<li><strong>When the transaction ends</strong>, committed or rolled back, Spring calls the transfer's callback.</li>
<li><strong>The callback records</strong> COMPLETED or FAILED (with the reason), again in a transaction of its own.</li>
</ol>

<details class="qa check"><summary>Check yourself: why not write COMPLETED just before the method returns?</summary><p>Because the transaction is not over: the commit can still fail, or a caller can roll back the transaction this method joined. The trail would then say COMPLETED for a transfer that never happened. Only after completion is the outcome known.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No bank network.</strong> Balances in one database.</li>
<li><strong>No fraud rules.</strong> A lockout is challenge 2.</li>
<li><strong>No login.</strong> Anyone can call the API.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tijori</strong> (a fictional digital bank) must keep an audit trail of every transfer attempt. Failed attempts disappeared from it, because their audit rows rolled back with the transfer.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> Asha (₹25,000) sends Ravi ₹1,500, <b>then</b> <code>201</code>, both balances change, and the trail has ATTEMPTED then COMPLETED with one attempt id.</li>
<li><b>Given</b> Ravi (₹100) tries to send ₹5,000, <b>then</b> <code>422</code>, his balance is unchanged, and the trail has ATTEMPTED then FAILED "Insufficient funds".</li>
<li><b>Given</b> a transfer to account 99, <b>then</b> <code>422</code>, Asha's debit is rolled back, and the attempt is still in the trail.</li>
<li><b>Given</b> a caller rolls back a transfer that returned normally, <b>then</b> the trail says FAILED, never COMPLETED.</li>
<li><b>Given</b> a malformed body, <b>then</b> <code>400</code> and no attempt; an unknown account's trail, <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Audit rows commit on their own; no business rollback can remove them.</li>
<li>Each attempt has exactly one outcome, enforced by the database.</li>
<li>The outcome is written only after the transaction's real end.</li>
<li>Money in integer paise; balances never below zero.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Choose between <code>REQUIRED</code> and <code>REQUIRES_NEW</code>, and know what each costs.</li>
<li>Run code after commit or rollback with a transaction synchronization.</li>
<li>Know that data access in those callbacks needs its own transaction.</li>
<li>Prove propagation behaviour against a real database.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/transfers</code>", "Transfer: <code>fromAccountId</code>, <code>toAccountId</code>, <code>amountPaise</code> (₹1 to ₹5 lakh)."],
    ["<code>GET</code>", "<code>/audit-events?accountId=1</code>", "Every event where the account sent or would have received, oldest first."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Transferred; audited ATTEMPTED and COMPLETED"],
    ['<span class="pill ok">200</span>', "The trail"],
    ['<span class="pill warn">400</span>', "Malformed body (not an attempt, not audited); no <code>accountId</code>"],
    ['<span class="pill warn">404</span>', "No such account (trail)"],
    ['<span class="pill warn">422</span>', "Insufficient funds, same account, unknown account: audited ATTEMPTED and FAILED"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against one fresh database. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-asha-sends-ravi-1500", "Case 1: Asha sends Ravi ₹1,500", "<b>Why:</b> <code>201</code>."),
    ("02-ravi-tries-to-send-5000", "Case 2: Ravi (₹100) tries ₹5,000", "<b>Why:</b> <code>422</code>, and still audited."),
    ("03-asha-sends-to-account-99", "Case 3: Asha sends ₹10 to account 99", "<b>Why:</b> her debit ran, then the credit found no account: rolled back, <code>422</code>."),
    ("04-ashas-audit-trail", "Case 4: Asha's trail", "<b>Why:</b> two attempts, one COMPLETED, one FAILED, each pair sharing its attempt id."),
    ("05-ravis-audit-trail", "Case 5: Ravi's trail", "<b>Why:</b> the transfer he received and the one he failed to send."),
    ("06-account-99", "Case 6: account 99's trail", "<b>Why:</b> no such account: <code>404</code>."),
    ("07-99-paise", "Case 7: 99 paise", "<b>Why:</b> <code>400</code>: a malformed request is not an attempt."),
]) + """
<h2>The balances afterwards</h2>
<p class="muted">Read with psql after the requests above (<code>docs/captures/balances.txt</code>): Asha was debited once, ₹1,500. Case 3's debit was rolled back; its audit events were not.</p>
""" + code(read("docs/captures/balances.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A transfer", "Both balances change; ATTEMPTED and COMPLETED, one attempt id", "<code>aTransferChangesBothBalancesAndIsAuditedTwice</code>"],
    ["Insufficient funds, same account, unknown account", "<code>422</code> each; debit rolled back; each audited with its reason", "<code>everyRefusalIsAuditedWithItsReason</code>"],
    ["Malformed bodies", "<code>400</code>; no events", "<code>malformedTransfersAre400AndNotAttempts</code>"],
    ["Unknown account's trail; no account given", "<code>404</code>; <code>400</code>", "<code>unknownAccountsHaveNoTrail</code>"],
    ["Bad rows written directly; two outcomes for one attempt", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"],
    ["REQUIRES_NEW and REQUIRED inside a rolled-back transaction", "The first survives, the second does not", "<code>requiresNewSurvivesTheCallersRollbackAndRequiredDoesNot</code>"],
    ["A caller rolls back a transfer that returned normally", "FAILED, not COMPLETED; balances unchanged", "<code>aTransferRolledBackByItsCallerIsAuditedAsFailedNotCompleted</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Writing the audit row in the same transaction, so it rolls back too.</p>
<p>The old service is kept in the tests as <code>OldTransferService</code>, a real proxied bean. Its catch block writes a TRANSFER_FAILED row with the same <code>JdbcClient</code>, then rethrows. Ravi's ₹5,000 attempt fails as it should, and the trail is empty: the rollback took the audit row too. The same attempt through the fixed API leaves ATTEMPTED and FAILED "Insufficient funds", and Ravi's balance unchanged.</p>
<p>While building, each part was undone once. <code>REQUIRED</code> instead of <code>REQUIRES_NEW</code> on the audit write turned 4 tests red. Writing COMPLETED inside the method, before the commit, turned 1 red: the test whose caller rolls back, where the trail then claimed a completed transfer. Not capturing the reason turned 2 red.</p>
</div>
""" + code(read(T + "AuditRollbackTrapTest.java"), "java") + code(read(T + "OldTransferService.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "TransferController.java", dwn("Validates the transfer; reads an account's trail.", "HTTP only; a malformed body never becomes an attempt.", "Validation errors audited as attempts.")),
    (J + "TransferService.java", dwn("Records the attempt, moves the money, and leaves the outcome to the end of the transaction.",
        "REQUIRED for the business work; a synchronization for the outcome.", "COMPLETED for a transfer that rolled back.",
        "<ul><li><code>registerSynchronization</code> hooks into the transaction this call runs in, even if it is the caller's.</li><li>The reason is kept in an <code>AtomicReference</code> set in the catch block and read in <code>afterCompletion</code>.</li><li>The debit is conditional: zero rows means insufficient funds (or no account).</li></ul>")),
    (J + "AuditTrail.java", dwn("Writes and reads audit events.",
        "<code>REQUIRES_NEW</code>: each write commits on its own, also when called from <code>afterCompletion</code>.", "Audit rows that roll back.")),
    (M + "V1__accounts_transfers_audit.sql", "<p>Accounts, transfers and the audit table, with named constraints and one outcome per attempt.</p>"),
    (M + "V2__demo_accounts.sql", "<p>Asha (₹25,000) and Ravi (₹100).</p>"),
    ("src/main/resources/application.yaml", "<p>Problem details on; decimals refused for whole-number fields.</p>"),
    (J + "TransfersApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/057-audit-trail-that-survives-a-rollback/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/tijori/transfers/
│   ├── TransferController.java   ├── TransferService.java   ├── AuditTrail.java   └── TransfersApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__accounts_transfers_audit.sql, V2__demo_accounts.sql
├── src/test/java/com/tijori/transfers/   (see Tests)
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
<p>Change <code>REQUIRES_NEW</code> to the default in <code>AuditTrail</code> (remove <code>propagation = …</code>) and run:</p>
""" + code("""./mvnw test -Dtest=AuditRollbackTrapTest""", "bash") + """
<p>The new trail now loses its failures exactly like the old one. Put it back.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Audit rows of failed operations are missing", "Written in the failing transaction.", "<code>REQUIRES_NEW</code>, or write outside the transaction."],
    ["A write in <code>afterCommit</code>/<code>afterCompletion</code> does nothing or errors", "It tried to join a transaction that is already finished.", "Call a <code>REQUIRES_NEW</code> method from the callback."],
    ["Requests hang under load", "Each <code>REQUIRES_NEW</code> holds a second connection while the first waits: the pool runs dry.", "Pool size above the concurrency; keep nested transactions short."],
    ["COMPLETED in the trail for a transfer that rolled back", "Outcome written before the commit.", "Write it in <code>afterCompletion</code>, from the real status."],
    ["<code>Transaction synchronization is not active</code>", "<code>registerSynchronization</code> called outside a transaction.", "Call it inside a <code>@Transactional</code> method."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>TransferContractTest</code> ({cnt('TransferContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>AuditRollbackTrapTest</code> ({cnt('AuditRollbackTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>AuditDatabaseTest</code> ({cnt('AuditDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "AuditRollbackTrapTest.java", "<p>Written first: the old catch-block audit, and the new trail, for the same failed attempt.</p>"),
    (T + "TransferContractTest.java", "<p>Transfers, refusals with reasons, and the trail.</p>"),
    (T + "AuditDatabaseTest.java", "<p>Named constraints; REQUIRES_NEW vs REQUIRED; a caller's rollback after a normal return.</p>"),
    (T + "OldTransferService.java", "<p>The old service, kept only in tests.</p>"),
    (T + "RequiredPropagation.java", "<p>Test-only bean: the same insert with REQUIRED, for comparison.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: no transfers or events, balances reset.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tijori/transfers/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=AttemptIdChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solution copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "The attempt id in the refusal", "Beginner-friendly", 15,
    "Add <code>attemptId</code> to every refused transfer's problem response: the same id its audit events carry.",
    "the test in <code>AttemptIdChallengeTest</code> passes.",
    ["<code>ProblemDetail.setProperty</code> adds a field to the response.",
     "The catch block already has the problem and the attempt id."],
    "challenge/AttemptIdChallengeTest.java", ["challenge/solution/TransferService.java"]) + challenge(2, "Lock out repeated failures", "Go deeper", 25,
    "After 3 failed transfers from an account within 10 minutes, refuse its next ones with <code>429</code> \"Too many failed attempts\", until the failures age. Count from the audit trail.",
    "the test in <code>LockoutChallengeTest</code> passes.",
    ["The count only works because failures survive their rollbacks: that is the point.",
     "The blocked attempt is itself an attempt: it is audited like the others."],
    "challenge/LockoutChallengeTest.java", ["challenge/solution/TransferService.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Where should the audit trail live?</h2>
<p>Compare three homes for it: a table in the same database written with REQUIRES_NEW (this station), an outbox table written in the same transaction and shipped elsewhere, and a log line sent to a log pipeline. For each: can an event be lost, can it describe something that never happened, and who can change it later?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, mapping"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test with the old catch-block audit as a real bean.</li>
<li>Move audit writes to a bean whose method is <code>REQUIRES_NEW</code>.</li>
<li>Record the attempt first; record the outcome from <code>afterCompletion</code>.</li>
<li>Prove both against a rollback by a caller, not only by an exception.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["<code>REQUIRES_NEW</code> audit writes + <code>afterCompletion</code> outcome", "A second connection per audit write.", '<span class="pill ok">Chosen</span>'],
    ["Audit in the same transaction", "Failures vanish.", '<span class="pill bad">The trap</span>'],
    ["<code>@TransactionalEventListener(phase = AFTER_COMPLETION)</code>", "The same idea through events; the listener still needs <code>REQUIRES_NEW</code>.", '<span class="pill warn">Equivalent</span>'],
    ["Audit written by the controller after the service returns", "Misses calls from jobs and other services; a caller's rollback is invisible.", '<span class="pill bad">Incomplete</span>'],
    ["<code>NESTED</code> (savepoints)", "Rolls back with the outer transaction: the opposite of what an audit needs.", '<span class="pill bad">Wrong tool</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Constraints"], [
    ["<code>accounts</code>", "<code>accounts_balance_not_negative</code>"],
    ["<code>transfers</code>", "<code>transfers_from_fk</code>, <code>transfers_to_fk</code>, <code>transfers_not_to_self</code>, <code>transfers_amount_range</code>, <code>transfers_attempt_unique</code>"],
    ["<code>audit_events</code>", "<code>audit_events_event_known</code>, <code>audit_events_reason_on_failure</code>, <code>audit_events_one_per_attempt</code>, partial unique <code>audit_events_one_outcome</code>; no foreign keys, on purpose"]]) + """
""" + code(read(M + "V1__accounts_transfers_audit.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Connections</dt><dd>Each <code>REQUIRES_NEW</code> borrows a second connection while the first is held. Under load, a pool smaller than twice the concurrent requests can deadlock on itself.</dd>
<dt>A crash between the two</dt><dd>If the app dies after ATTEMPTED and before the outcome, the attempt has no outcome. A nightly check lists attempts older than a few minutes with no outcome, for a person to resolve.</dd>
<dt>Keep it append-only</dt><dd>Grant the application INSERT and SELECT on <code>audit_events</code>, never UPDATE or DELETE.</dd>
<dt>Retention</dt><dd>Audit trails often must be kept for years; plan partitions or archiving from the start.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("REQUIRED vs REQUIRES_NEW?", "REQUIRED joins the current transaction (or starts one): it commits or rolls back with the caller. REQUIRES_NEW suspends the caller's transaction and runs in a new one that commits independently."),
    ("Why does a failure audit need REQUIRES_NEW?", "The failure makes the business transaction roll back. Anything written in it, including the audit row, rolls back too. A separate transaction is the only way the row survives."),
    ("How do you run code after a transaction commits?", "Register a TransactionSynchronization (afterCommit or afterCompletion), or use @TransactionalEventListener with a phase. Data access there must use REQUIRES_NEW."),
    ("What does REQUIRES_NEW cost?", "A second database connection and transaction per call, held while the outer one waits. It can exhaust the pool, and it can deadlock if the inner transaction needs rows the outer one locked."),
    ("Is NESTED the same as REQUIRES_NEW?", "No. NESTED uses a savepoint inside the outer transaction: it can roll back on its own, but if the outer transaction rolls back, it goes too."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You switched REQUIRES_NEW off and saw the trail lose its failures."],
    ["Propagation", "REQUIRED vs REQUIRES_NEW.", "You can explain NESTED and the connection cost."],
    ["Outcome", "Written after completion.", "You covered a caller's rollback, not only an exception."],
    ["Audit design", "One outcome per attempt, in the schema.", "A plan for attempts with no outcome."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any record that must survive a failure:</p>
<ul class="rules">
<li>Which transaction is this row written in, and what happens to it if that transaction rolls back?</li>
<li>Is "it worked" recorded before or after the commit?</li>
<li>Does a nested transaction lock rows the outer one also needs?</li>
<li>Could the pool run out of connections when every request opens two?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
