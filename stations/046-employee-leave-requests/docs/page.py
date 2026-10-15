"""Station 046 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 46,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Data JPA (Hibernate 7) · @Transactional · @Version · @DataJpaTest · PostgreSQL 17 · Flyway · Testcontainers",
    "simulation": "Employees, balances and requests are demo data, not Teamdesk's. Approving creates a record and changes a number; no payroll, calendar or email is involved. Weekends are free; public holidays are not modelled (a demo rule).",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/teamdesk/leave/"
T = "src/test/java/com/teamdesk/leave/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Entity", "A Java object that stands for one row of a table.", "A file card for one employee.", "<code>Employee</code>, <code>LeaveRequest</code>"),
    ("Persistence context", "The set of entities Hibernate is watching during one transaction.", "The cards on the clerk's desk right now.", "One per <code>@Transactional</code> call"),
    ("Managed", "An entity inside the persistence context: its changes are saved by themselves.", "A card on the desk: any edit goes into the file at closing time.", "Inside <code>LeaveDesk.approve</code>"),
    ("Detached", "An entity whose transaction has ended: changes stay in memory.", "A photocopy taken home: editing it changes nothing in the file.", "What the old desk worked on"),
    ("Dirty checking", "At commit, Hibernate compares each managed entity with what it loaded and writes the differences.", "The clerk checking every card on the desk before filing.", "No <code>save()</code> in <code>approve</code>"),
    ("<code>@Transactional</code>", "Runs a method in one transaction: one persistence context, one commit or one rollback.", "One sitting at the desk.", "<code>LeaveDesk</code>"),
]
STORY = [
    ("The balance that did not move", "Teamdesk's HR found employees with approved leave and an untouched balance. The manager's screen had shown the right number at approval: 12 days, 3 approved, 9 left."),
    ("It depended on the method", "Approvals from the mobile app were fine; approvals from the web inbox were not. Both called the same lines of code, but only one of them ran inside a transaction."),
    ("The fix", "One transactional service method that loads the request and the employee, changes both, and lets Hibernate write both at commit."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A change to an object is saved only while Hibernate is watching it, and Hibernate watches only inside a transaction.</p>

<h2>What are we building?</h2>
<p>An employee asks for leave (<code>POST /leave-requests</code>); a manager approves it (<code>POST /leave-requests/{id}/approval</code>), which marks the request approved and takes the days off the balance; anyone can read the balance (<code>GET /employees/{id}/leave-balance</code>). The request and the balance always change together.</p>

<h2>An everyday analogy</h2>
<p>A clerk with a desk. While the cards are on the desk, any correction goes into the file when the clerk closes for the day. A photocopy taken home can be corrected all evening; the file never hears of it. The old code corrected the photocopy of the employee's card, and refiled only the leave form.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>The approval starts</strong> a transaction, with a fresh persistence context.</li>
<li><strong>It loads</strong> the request and its employee: both are now managed.</li>
<li><strong>It checks and changes</strong> them in memory: status APPROVED, balance minus the days.</li>
<li><strong>At commit</strong>, Hibernate finds both changes and writes both rows, or neither.</li>
</ol>

<details class="qa check"><summary>Check yourself: the fixed <code>approve</code> never calls <code>save()</code>. How do the changes reach the database?</summary><p>Both entities were loaded inside the transaction, so they are managed. At commit, Hibernate compares them with what it loaded (dirty checking) and writes an UPDATE for each one that changed.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No login.</strong> Anyone may approve; a real desk checks the manager.</li>
<li><strong>No holidays or half days.</strong> Monday to Friday count; nothing else is modelled.</li>
<li><strong>No overlap check.</strong> Two requests for the same days are both accepted.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Teamdesk</strong> (a fictional HR SaaS) approves leave and keeps each employee's balance. Approvals saved the request but sometimes not the balance, depending on which code path ran.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> Asha asks for Friday 6 to Tuesday 10 November 2026, <b>then</b> <code>201</code>, 3 working days, PENDING, and her balance is still 12.</li>
<li><b>Given</b> the manager approves it, <b>then</b> <code>200</code>, and both the response and <code>GET</code> show 9.</li>
<li><b>Given</b> it is approved again, <b>then</b> <code>409</code> and the balance stays 9.</li>
<li><b>Given</b> Rohan has 2 days and asks for 3, <b>then</b> approval is <code>422</code> and nothing changes.</li>
<li><b>Given</b> 8 managers approve the same request at the same moment, <b>then</b> one <code>200</code>, seven <code>409</code>, and 3 days are taken once.</li>
<li><b>Given</b> a malformed body, <code>400</code>; impossible dates or an unknown employee, <code>422</code>; an unknown request or employee in the path, <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Approval changes the request and the balance in one transaction.</li>
<li>A balance never goes below zero, and a request is approved at most once, also in the database.</li>
<li>Days are counted on the server: Monday to Friday, at most 42 calendar days per request (demo rules).</li>
<li>Two approvals at once never lose a deduction.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Explain the persistence context: managed and detached entities, dirty checking.</li>
<li>Put <code>@Transactional</code> on the service method that owns a business change.</li>
<li>Know what <code>save()</code> does on a managed entity (nothing) and on a detached one (merge, returning a copy).</li>
<li>Write a <code>@DataJpaTest</code>, and know what its automatic transaction can hide.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/leave-requests</code>", "Ask for leave: <code>employeeId</code>, <code>startDate</code>, <code>endDate</code> (inclusive, ISO dates), <code>reason</code> (1 to 200 characters)."],
    ["<code>POST</code>", "<code>/leave-requests/{id}/approval</code>", "Approve a pending request: the days come off the balance."],
    ["<code>GET</code>", "<code>/employees/{id}/leave-balance</code>", "The employee's balance in working days."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Request created, PENDING"],
    ['<span class="pill ok">200</span>', "Approved; or the balance"],
    ['<span class="pill warn">400</span>', "A field missing or malformed"],
    ['<span class="pill warn">404</span>', "No such request or employee in the path"],
    ['<span class="pill warn">409</span>', "Already decided, or another approval changed it at the same moment (reload and retry)"],
    ['<span class="pill warn">422</span>', "End before start, weekends only, more than 42 days, unknown employee, or not enough leave"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against one fresh database (Asha 12 days, Rohan 2). JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-asha-asks-for-three-days", "Case 1: Asha asks for Friday to Tuesday", "<b>Why:</b> 5 dates, 3 working days; PENDING."),
    ("02-the-manager-approves", "Case 2: the manager approves", "<b>Why:</b> 12 − 3 = 9, in the response..."),
    ("03-ashas-balance", "Case 3: Asha's balance", "<b>Why:</b> ...and in the database. This is the number the old code lost."),
    ("04-approved-twice", "Case 4: the same approval again", "<b>Why:</b> already decided: <code>409</code>."),
    ("05-rohan-asks-for-three-days", "Case 5: Rohan asks for the same dates", "<b>Why:</b> a request may exceed the balance; approval decides."),
    ("06-not-enough-leave", "Case 6: approving Rohan's request", "<b>Why:</b> 2 days left, 3 needed: <code>422</code>."),
    ("07-a-weekend-only", "Case 7: Saturday 7 to Sunday 8", "<b>Why:</b> no working day to take: <code>422</code>."),
    ("08-no-such-request", "Case 8: request 99", "<b>Why:</b> <code>404</code>."),
]) + """
<h2>What the database kept</h2>
<p class="muted">Read with psql after the requests above (<code>docs/captures/rows.txt</code>). Each approval raised the <code>version</code> of both rows it changed.</p>
""" + code(read("docs/captures/rows.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Friday to Tuesday", "3 working days", "<code>aRequestCountsWorkingDaysAndWaits</code>"],
    ["Approve, then read the balance", "Both say 9", "<code>approvalTakesTheDaysAndTheBalanceShowsIt</code>"],
    ["Approve twice", "<code>409</code>, deducted once", "<code>aDecidedRequestCannotBeApprovedAgain</code>"],
    ["Not enough leave", "<code>422</code>, nothing changes", "<code>moreDaysThanTheBalanceIs422AndChangesNothing</code>"],
    ["Reversed dates, weekend only, 43 days, unknown employee", "<code>422</code>; exactly 42 days is 30 working days and allowed", "<code>impossibleRequestsAre422</code>"],
    ["Negative balance, bad status, dates or days, written directly", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"],
    ["The balance write fails", "The request stays PENDING too", "<code>whenTheBalanceWriteFailsTheApprovalRollsBackToo</code>"],
    ["8 approvals of one request at once", "One <code>200</code>, seven <code>409</code>, 3 days taken", "<code>eightManagersApprovingTheSameRequestDeductOnce</code>"],
    ["6 different requests approved at once", "Each <code>200</code> took its days; the rest are <code>409</code> or <code>422</code>", "<code>approvingDifferentRequestsAtOnceNeverLosesADeduction</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Changing a managed entity outside a transaction and expecting it to be saved.</p>
<p>The old desk, kept in the tests, has no <code>@Transactional</code>. Each repository call runs in its own short transaction, so the request and employee it loads are detached when the call returns. It sets the status and the balance, then calls <code>requests.save(request)</code>: a merge, which copies the request's own columns and nothing from the employee, because the association is not cascaded. The manager sees 9; the database keeps 12.</p>
<p>The second test runs the very same lines inside a transaction: both rows are saved, with no extra code. That is the "depends on which method ran" in the bug report.</p>
<p>While building, each part was undone once. Removing <code>@Transactional</code> from <code>approve</code> turned 5 tests red; removing <code>@Version</code> from <code>Employee</code> 1 (the parallel test with different requests); removing the PENDING check 2; removing the balance check 1. Removing <code>@Version</code> from <code>LeaveRequest</code> turned none red: every approval also changes the employee, whose version already catches the race. It is kept because rejecting (challenge 1) changes only the request.</p>
</div>
""" + code(read(T + "DetachedEntityTrapTest.java"), "java") + code(read(T + "OldLeaveDesk.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "LeaveController.java", dwn("Validates the body and calls the desk; turns a failed version check into <code>409</code>.", "HTTP only.", "Transactions started in the controller.")),
    (J + "LeaveDesk.java", dwn("Counts working days, creates requests, approves them, reads balances.",
        "<code>approve</code> is one transaction and calls no <code>save()</code>.",
        "Half-saved approvals.",
        "<ul><li>The checks (PENDING, enough days) run on the loaded entities, then <code>request.approve()</code> changes both.</li><li>The response is built inside the transaction, from the same objects that are about to be written.</li><li>Errors are <code>ErrorResponseException</code> with a <code>ProblemDetail</code>; the transaction rolls back on them.</li></ul>")),
    (J + "LeaveRequest.java", dwn("The leave_requests table, with a lazy link to the employee.",
        "<code>approve()</code> changes two objects; <code>@Version</code> guards the row.",
        "Two decisions on the same request at once.")),
    (J + "Employee.java", dwn("The employees table: name and balance.",
        "<code>@Version</code>: two approvals for one person cannot overwrite each other's deduction.",
        "A lost update: 12 − 3 − 3 saved as 9.")),
    (J + "LeaveRequestRepository.java", "<p><code>findWithEmployeeById</code> loads the request and its employee in one query (<code>@EntityGraph</code>).</p>"),
    (J + "EmployeeRepository.java", "<p>Spring Data repository.</p>"),
    (M + "V1__employees_and_leave_requests.sql", "<p>Both tables, version columns, and the named constraints.</p>"),
    (M + "V2__demo_team.sql", "<p>Asha (12 days) and Rohan (2 days).</p>"),
    ("src/main/resources/application.yaml", "<p>open-in-view off, so nothing is managed outside a service transaction; schema validation.</p>"),
    ("pom.xml", "<p>Data JPA, Flyway, PostgreSQL; <code>spring-boot-starter-data-jpa-test</code> for <code>@DataJpaTest</code>.</p>"),
    (J + "LeaveApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/046-employee-leave-requests/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/teamdesk/leave/
│   ├── LeaveController.java   ├── LeaveDesk.java   ├── LeaveRequest.java   ├── Employee.java
│   ├── LeaveRequestRepository.java   ├── EmployeeRepository.java   └── LeaveApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__employees_and_leave_requests.sql, V2__demo_team.sql
├── src/test/java/com/teamdesk/leave/   (see Tests)
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
./mvnw test                 # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL containers""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Delete the <code>@Transactional</code> line above <code>approve</code> in <code>LeaveDesk</code> and run the contract tests.</p>
""" + code("""./mvnw test -Dtest=LeaveContractTest""", "bash") + """
<p>The approval still answers 9, but the balance read back is 12: without a transaction, the loaded entities are detached and nothing calls <code>save()</code>. Put the line back.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["A change in the response but not in the database", "The entity was detached: no transaction around the change.", "Make the change inside a <code>@Transactional</code> service method."],
    ["<code>@Transactional</code> on a method, and still nothing saved", "It was called from the same class (<code>this.approve()</code>), which skips Spring's proxy; or the method is private.", "Call it from another bean; keep it non-private."],
    ["<code>LazyInitializationException ... no session</code>", "A lazy association read after the transaction ended.", "Load what you need inside it (<code>@EntityGraph</code>), and map to a response there."],
    ["<code>409 Changed meanwhile</code>", "A <code>@Version</code> check failed: another approval committed first.", "Reload and retry; that is the intended answer."],
    ["A <code>@DataJpaTest</code> passes but the app does not save", "The test's own transaction kept the entities managed.", "Also test through the real entry point, with no test transaction (<code>DetachedEntityTrapTest</code>)."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the entities and the database.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>LeaveContractTest</code> ({cnt('LeaveContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>DetachedEntityTrapTest</code> ({cnt('DetachedEntityTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>LeaveDatabaseTest</code> ({cnt('LeaveDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["This station's concepts", "<code>@DataJpaTest</code>: dirty checking, save vs merge", f"<code>LeaveJpaTest</code> ({cnt('LeaveJpaTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Two kinds of test, on purpose</h2>
<p><code>LeaveJpaTest</code> is a <code>@DataJpaTest</code>: it starts only JPA and wraps every test in a transaction that is rolled back. That is fast and keeps tests independent, and it is also why the old approval passes there (its last test shows it). The other classes start the whole app with no test transaction, exactly as production runs, and that is where the bug shows.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "DetachedEntityTrapTest.java", "<p>Written first: the old desk without and with a transaction, and the fixed desk.</p>"),
    (T + "LeaveContractTest.java", "<p>Requests, approvals and balances; every refusal.</p>"),
    (T + "LeaveDatabaseTest.java", "<p>Named constraints, a rollback across both rows, and approvals in parallel (virtual threads and a start latch).</p>"),
    (T + "LeaveJpaTest.java", "<p><code>@DataJpaTest</code>: dirty checking, <code>save()</code> on managed and detached entities.</p>"),
    (T + "OldLeaveDesk.java", "<p>The old approval, kept only in tests.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: resets the demo team before each test.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/teamdesk/leave/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=RejectChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in (Java files and one migration), all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Reject a request", "Beginner-friendly", 20,
    "Add <code>POST /leave-requests/{id}/rejection</code> with a required note: PENDING becomes REJECTED and the balance is untouched. A decided request is <code>409</code>.",
    "both tests in <code>RejectChallengeTest</code> pass.",
    ["Same shape as <code>approve</code>: load, check PENDING, change, no <code>save()</code>.",
     "Only the request changes here, so its own <code>@Version</code> is what stops a rejection racing an approval."],
    "challenge/RejectChallengeTest.java", ["challenge/solution/LeaveRequest.java", "challenge/solution/LeaveDesk.java", "challenge/solution/LeaveController.java"]) + challenge(2, "Cancel approved leave", "Go deeper", 30,
    "Add <code>POST /leave-requests/{id}/cancellation</code>: APPROVED becomes CANCELLED and the days go back to the balance, together. Anything else is <code>409</code>.",
    "both tests in <code>CancelChallengeTest</code> pass.",
    ["The database refuses the new status until a migration changes <code>leave_requests_status_known</code>.",
     "A refund is the mirror of a deduction: two managed objects, one transaction."],
    "challenge/CancelChallengeTest.java", ["challenge/solution/V3__cancelled_status.sql", "challenge/solution/LeaveRequest.java", "challenge/solution/Employee.java", "challenge/solution/LeaveDesk.java", "challenge/solution/LeaveController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>When the balance lives elsewhere</h2>
<p>Teamdesk moves balances to a payroll service with its own database. An approval must now change a row here and a number there, and no single transaction covers both. Sketch what happens when the payroll call fails after the request is APPROVED, and how a manager or a job would notice and repair it.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, mapping"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: run the old approval with no transaction and read both rows back with SQL.</li>
<li>Put the business change in one <code>@Transactional</code> service method; load what it changes with one query.</li>
<li>Delete the <code>save()</code> calls that only hid the problem.</li>
<li>Add <code>@Version</code> and a parallel test, because approvals are clicked twice.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["<code>@Transactional</code> service method, dirty checking", "Knowing which objects are managed.", '<span class="pill ok">Chosen</span>'],
    ["No transaction, <code>save()</code> each entity", "Two commits: a crash between them leaves half an approval.", '<span class="pill bad">Fragile</span>'],
    ["<code>cascade = MERGE</code> from request to employee", "Saves the employee by accident from any request merge.", '<span class="pill warn">Surprising</span>'],
    ["One SQL <code>UPDATE ... WHERE balance_days >= ?</code>", "Fast and race-free for one row, but the status change is a second statement anyway.", '<span class="pill warn">Station 042 style</span>'],
    ["<code>@Transactional</code> on the controller", "Transactions that include HTTP work; easy to leak.", '<span class="pill bad">No</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Constraints", "Mapped as"], [
    ["<code>employees</code>", "<code>employees_balance_not_negative</code>", "<code>Employee</code>, with <code>@Version</code>"],
    ["<code>leave_requests</code>", "<code>leave_requests_employee_fk</code>, <code>leave_requests_dates_ordered</code>, <code>leave_requests_days_range</code>, <code>leave_requests_days_fit_dates</code>, <code>leave_requests_status_known</code>", "<code>LeaveRequest</code>, <code>@ManyToOne(fetch = LAZY)</code> to the employee, with <code>@Version</code>"]]) + """
""" + code(read(M + "V1__employees_and_leave_requests.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Where transactions belong</dt><dd>On the service method that owns one business change. Not on repositories one by one, and not around HTTP work.</dd>
<dt>Self-invocation</dt><dd><code>@Transactional</code> works through a Spring proxy: a call from inside the same class skips it. A classic way to get exactly this station's bug.</dd>
<dt>open-in-view</dt><dd>Off here. On (Spring's default), it keeps entities loadable during the response, which hides where the transaction really ends.</dd>
<dt>Retries</dt><dd>A <code>409 Changed meanwhile</code> is safe to retry after reloading; approval checks PENDING again, so a retry never deducts twice.</dd>
<dt>Audit</dt><dd>HR needs who approved what and when; this station keeps only the status. A real system records the decision as its own row.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is the persistence context?", "The set of entities Hibernate tracks in one session, usually one transaction. It returns the same object for the same row, and at flush writes every change it finds by dirty checking."),
    ("Why did save() not save the balance?", "The request was detached, so save() merged it: Hibernate copied its columns onto a managed copy. The employee association is not cascaded, so the employee's changes were not copied, and the employee itself was never managed."),
    ("Is there an update() in Spring Data JPA?", "No. save() on a managed entity does nothing; on a new one it persists; on a detached one it merges and returns a different, managed object. Keep using the returned one."),
    ("What can @DataJpaTest hide?", "Each test runs in a transaction, so code that forgets its own transaction still works in the test. Test the real entry point without a test transaction as well."),
    ("How do you stop two approvals deducting twice?", "Check the status inside the transaction and add @Version: the second commit finds a changed version and fails, which you answer with 409. A pessimistic lock is the alternative."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You removed <code>@Transactional</code> and explained the red tests."],
    ["Transactions", "One service method per business change.", "You can explain self-invocation and open-in-view."],
    ["Persistence context", "Managed vs detached; no needless <code>save()</code>.", "What merge returns, and why that matters."],
    ["Testing", "A <code>@DataJpaTest</code>.", "You know when its transaction hides a bug."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any JPA change:</p>
<ul class="rules">
<li>Which method starts the transaction, and does every change happen inside it?</li>
<li>Is a <code>@Transactional</code> method called from its own class, or private?</li>
<li>Does code keep using the object it passed to <code>save()</code> instead of the one returned?</li>
<li>Could two people change the same row at once, and what stops the second?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
