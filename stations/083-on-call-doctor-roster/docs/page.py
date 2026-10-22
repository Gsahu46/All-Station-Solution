"""Station 083 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 83,
    "stack": "Spring Boot 4.1.1 · Java 25 · SERIALIZABLE transactions and retries · TransactionTemplate · JdbcClient · constraint triggers · PostgreSQL 17 · Testcontainers",
    "simulation": "The wards, doctors and roster are demo data, not Mediqo's. Nobody is paged: going off call changes a row and records the change.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/mediqo/roster/"
T = "src/test/java/com/mediqo/roster/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Transaction", "Several reads and writes that count as one: all happen, or none.", "Paying and getting the receipt together.", "<code>TransactionTemplate</code>"),
    ("Isolation level", "How much a transaction can see of others that run at the same time.", "Whether you see a colleague's half-filled form.", "READ COMMITTED (default), SERIALIZABLE"),
    ("Write skew", "Two transactions each read the same facts, then change different rows; together they break a rule neither broke alone.", "Two doctors each checking the other is staying.", "<code>WriteSkewTrapTest</code>"),
    ("Serialization failure", "PostgreSQL stops a SERIALIZABLE transaction that cannot fit with another one. SQLState 40001.", "\"Someone changed this while you were deciding: start again.\"", "<code>Roster.offCall</code>"),
    ("Retry", "Running the whole transaction again from the start after a serialization failure.", "Re-reading the board before deciding again.", "up to 5 attempts in all"),
    ("Constraint trigger", "A database check that runs at commit and can look at many rows.", "A ward sister checking the board before signing it.", "<code>wards_keep_min_on_call</code>"),
]
STORY = [
    ("Nobody on call", "At 02:00 two cardiology doctors pressed \"go off call\" at the same second. Each request counted two doctors on call, decided the other one was staying, and took its own doctor off. Cardiology had nobody on call for 40 minutes."),
    ("Why the check did not help", "The check was right, the database was right, and the transactions were right one at a time. Together they were wrong: each saw the world before the other's change. The default isolation level, READ COMMITTED, allows that."),
    ("The fix", "Run the check and the change in a SERIALIZABLE transaction. When two of them cannot both be right, PostgreSQL stops one; it runs again, sees one doctor left, and is refused. A rule in the database checks every writer at commit."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A rule about several rows ("at least one doctor on call") is not protected by the default isolation level. Use SERIALIZABLE and retry, or lock what the rule depends on.</p>

<h2>What are we building?</h2>
<p>One endpoint: a doctor goes off call, unless the ward would then have fewer doctors on call than it needs.</p>

<h2>An everyday analogy</h2>
<p>Two people share a car to the office and each wants to take the day off. Each looks at the calendar, sees the other is coming in, and books leave. Nobody drives. The fix: whoever books second must look at the calendar again, after the first booking.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Read</strong>: the ward's minimum, the doctor, how many are on call. In a SERIALIZABLE transaction.</li>
<li><strong>Decide</strong>: refuse if the ward would drop below its minimum; if the doctor is already off, answer the same as before.</li>
<li><strong>Write</strong>: take the doctor off and record the change.</li>
<li><strong>Commit, or start again</strong>: if PostgreSQL says another transaction got in the way (40001), run all of it again.</li>
</ol>

<details class="qa check"><summary>Check yourself: Orthopaedics has three doctors on call and needs one. All three ask to go at once. What happens?</summary><p>Two go off, one is refused, in whatever order PostgreSQL lets them commit: <code>threeDoctorsLeavingAtOnceFromAWardThatNeedsOne</code>. The captures show one real run.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No shifts or times.</strong> \"On call\" is a yes or no for tonight; challenge 3 adds time ranges.</li>
<li><strong>No sign-in.</strong> Any caller can name any doctor; station 077 shows how to check who may.</li>
<li><strong>No paging.</strong> Nobody is notified: a row changes and the change is recorded.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Mediqo</strong> (a fictional hospital group): two doctors went off call at the same moment and a ward was left with nobody on call.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo roster: Cardiology needs 1 on call and has dr.sharma and dr.iyer (dr.menon is off); Orthopaedics needs 1 and has dr.bose, dr.khan and dr.rao. Demo rule: a lost race is tried up to 5 times in all.</p>
<ol class="gwt">
<li><b>Given</b> two doctors on call and a minimum of one, <b>when</b> one goes off, <b>then</b> <code>200</code> and one on call.</li>
<li><b>Given</b> the last doctor needed, <b>then</b> <code>409</code> and nothing changes.</li>
<li><b>Given</b> two doctors going off at the same moment, <b>then</b> one goes, one is refused; the ward keeps its minimum.</li>
<li><b>Given</b> the same request twice, <b>then</b> the same answer and one recorded change, even if the ward is now at its minimum.</li>
<li><b>Given</b> a race lost on every attempt, <b>then</b> <code>503</code>: try again, nothing changed.</li>
<li><b>Given</b> an unknown ward or doctor, <b>then</b> <code>404</code>; a name not shaped <code>dr.name</code>, <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>The check and the change run in one SERIALIZABLE transaction, retried on SQLState 40001.</li>
<li>The database refuses, at commit, any change that leaves a ward below its minimum, whoever writes it.</li>
<li>Every real change is recorded in <code>roster_changes</code> in the same transaction.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Explain write skew and why READ COMMITTED allows it.</li>
<li>Run a transaction at SERIALIZABLE and retry it correctly, the whole transaction from the start.</li>
<li>Tell a lost race (try again) from a business refusal (409).</li>
<li>Reproduce a race deterministically with two database connections.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/rosters/{ward}/off-call</code>", "<code>{doctor}</code>: take the doctor off call. Safe to repeat."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "Off call now, or already off (the same answer, nothing changes)"],
    ['<span class="pill warn">400</span>', "No doctor, or a name not shaped <code>dr.name</code>"],
    ['<span class="pill warn">404</span>', "No such ward, or no such doctor on this ward"],
    ['<span class="pill warn">409</span>', "The ward would drop below its minimum"],
    ['<span class="pill warn">503</span>', "The roster kept changing during every attempt: try again"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. JSON bodies are indented for reading; <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-dr-sharma-goes-off-call", "Case 1: dr.sharma goes off call", "<b>Why:</b> dr.iyer stays: one on call, the minimum."),
    ("02-dr-iyer-asks-to-go-too", "Case 2: dr.iyer asks to go too", "<b>Why:</b> Cardiology would have nobody: <code>409</code>."),
    ("03-dr-sharma-sends-it-again", "Case 3: dr.sharma's app sends it again", "<b>Why:</b> already off: the same answer, no second change, and no <code>409</code> although the ward is at its minimum."),
    ("04-unknown-ward", "Case 4: a ward that does not exist", "<b>Why:</b> <code>404</code>."),
    ("05-a-name-that-is-not-a-doctor", "Case 5: a name not shaped dr.name", "<b>Why:</b> <code>400</code>."),
    ("06-at-once-dr-bose", "Case 6a: dr.bose, at the same moment as 6b and 6c", "<b>Why:</b> the three Orthopaedics requests were sent together. Which two go depends on timing; two of three always do."),
    ("06-at-once-dr-khan", "Case 6b: dr.khan", "<b>Why:</b> see 6a."),
    ("06-at-once-dr-rao", "Case 6c: dr.rao", "<b>Why:</b> see 6a."),
]) + """
<h2>The roster and the recorded changes afterwards</h2>
""" + code(read("docs/captures/roster.txt").rstrip(), "text") + code(read("docs/captures/changes.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["One of two goes off", "<code>200</code>, one on call", "<code>aDoctorGoesOffCallWhileAnotherStaysOn</code>"],
    ["The last one needed", "<code>409</code>, nothing changes", "<code>theLastDoctorOnCallCannotGo</code>"],
    ["Unknown ward or doctor; a bad name", "<code>404</code>; <code>400</code>", "<code>unknownWardsAndDoctorsAre404AndBadNamesAre400</code>"],
    ["The same request twice", "The same answer, one recorded change", "<code>theSameOffCallTwiceChangesTheRosterOnce</code>"],
    ["A retry once the ward is at its minimum", "<code>200</code>, not <code>409</code>: the change already happened", "<code>aRetryIsNotRefusedEvenWhenTheWardIsNowAtItsMinimum</code>"],
    ["Two doctors at once", "One goes, one <code>409</code>, after a retry", "<code>twoDoctorsLeavingAtOnceLeaveOneOnCall</code>"],
    ["Three doctors at once, minimum one", "Two go, one <code>409</code>", "<code>threeDoctorsLeavingAtOnceFromAWardThatNeedsOne</code>"],
    ["A race lost on every attempt", "<code>503</code>, nothing changed", "<code>aLostRaceWithNoRetriesLeftIs503AndChangesNothing</code>"],
    ["Plain SQL leaving a ward with nobody", "Refused at commit by <code>wards_keep_min_on_call</code>", "<code>aWardIsNeverLeftWithoutItsMinimumByAnyWriter</code>"],
    ["Other rules written by plain SQL", "Refused by named constraints", "<code>otherRulesHoldWithoutJava</code>"],
    ["The change record cannot be written", "The doctor stays on call", "<code>anOffCallWhoseRecordFailsChangesNothing</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Assuming READ COMMITTED prevents write skew.</p>
<ul>
<li><strong>The old code, READ COMMITTED.</strong> The test opens two real database connections and runs them step by step: both count two doctors on call, both take their own doctor off. They change different rows, so nothing waits and nothing conflicts. Both commit: Cardiology has nobody.</li>
<li><strong>The same steps, SERIALIZABLE.</strong> The first commit succeeds; the second fails with SQLState 40001, and one doctor stays on call. The app then runs the second request again from the start, and it is refused with <code>409</code>.</li>
</ul>
<p>The ward rule in the database is switched off in this test, because the old schema had none and because only isolation is tested here.</p>
<p>While building, each part was undone once: READ COMMITTED instead of SERIALIZABLE turned 1 test red; no retry 2; no minimum check 1; no database rule 3; no \"already off\" answer 2; the lost race not turned into a <code>503</code> 1; no change record 3; a minimum of 0 allowed 1. With READ COMMITTED, the parallel tests still ended with one doctor on call: the database rule refused the second commit. Only the check that a retry happened failed. See Tests.</p>
</div>
""" + code(read(T + "WriteSkewTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "RosterController.java", dwn("The endpoint.", "Checks the doctor's name shape and hands over to <code>Roster</code>.", "Any string reaching the database.")),
    (J + "Roster.java", dwn("Going off call, safely when two ask at once.",
        "One SERIALIZABLE transaction for the check and the change; SQLState 40001 runs it again, up to 5 attempts in all, with a short random wait; then <code>503</code>. A doctor already off gets the same answer before any rule is checked.",
        "A ward left with nobody when two doctors press at the same second.",
        "<ul><li>The retry repeats the whole transaction, reads included: retrying only the update would act on what was read before the other change.</li><li>Spring reports 40001 as a <code>DataAccessException</code> subclass; the code matches the SQLState, as station 082 does for lock timeouts.</li><li>The \"already off\" answer comes before the minimum check. The other order refuses a retry with <code>409</code> once the ward is at its minimum, although the change was made.</li><li>The <code>retries</code> counter is there for tests and dashboards.</li></ul>")),
    (M + "V1__wards_and_roster.sql", dwn("Wards, the roster, recorded changes, and the ward rule.",
        "A constraint trigger, deferred to commit, refuses any change that leaves a ward below its minimum.",
        "A plain SQL fix at night that leaves a ward with nobody.",
        "<p>Its limit, written in the file: two READ COMMITTED transactions committing at the same instant can each miss the other's change, and deleting a roster row is not covered. The application therefore also runs SERIALIZABLE.</p>")),
    (M + "V2__demo_roster.sql", "<p>Two wards, six doctors.</p>"),
    ("src/main/resources/application.yaml", "<p>The demo rule: 5 attempts in all for a lost race.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "RosterApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/083-on-call-doctor-roster/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/mediqo/roster/
│   ├── RosterController.java   ├── Roster.java   └── RosterApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__wards_and_roster.sql, V2__demo_roster.sql
├── src/test/java/com/mediqo/roster/   (see Tests)
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
""" + code("""docker compose up -d        # PostgreSQL 17 on localhost:5432
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>See write skew with your own eyes in two <code>psql</code> sessions. Open two terminals and run in each:</p>
""" + code("""docker compose exec postgres psql -U mediqo -d mediqo""", "bash") + """
<p>Then type, alternating between them (A, then B, then A...):</p>
""" + code("""-- A and B:
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT count(*) FROM roster WHERE ward = 'cardiology' AND on_call;   -- both see 2
-- A:
UPDATE roster SET on_call = false WHERE ward = 'cardiology' AND doctor = 'dr.sharma';
-- B:
UPDATE roster SET on_call = false WHERE ward = 'cardiology' AND doctor = 'dr.iyer';
-- A:
COMMIT;
-- B:
COMMIT;""", "sql") + """
<p>A's <code>COMMIT</code> succeeds. B's fails with <code>could not serialize access due to read/write dependencies among transactions</code>: that is the 40001 the app retries. Put dr.sharma back on call (in A: <code>UPDATE roster SET on_call = true WHERE ward = 'cardiology' AND doctor = 'dr.sharma';</code>), then repeat the steps with <code>BEGIN ISOLATION LEVEL READ COMMITTED</code>: this time both updates and A's commit pass, and B's <code>COMMIT</code> is refused by <code>wards_keep_min_on_call</code>, the database rule, not by isolation.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>could not serialize access</code> (SQLState 40001) as a 500", "A SERIALIZABLE transaction lost a race and nothing retried it.", "Retry the whole transaction, as <code>Roster.offCall</code> does."],
    ["Parallel tests pass with READ COMMITTED", "The database rule refused the second commit; the answer was right for the wrong reason.", "Check that the retry happened (<code>roster.retries</code>), and test isolation alone with two connections."],
    ["<code>Could not find a valid Docker environment</code>", "Docker is not running.", "Start Docker Desktop or the Docker service."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the database behind it.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>RosterContractTest</code> ({cnt('RosterContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>WriteSkewTrapTest</code> ({cnt('WriteSkewTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>RosterDatabaseTest</code> ({cnt('RosterDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Concurrency", "A real concurrency test that proves the invariant holds", f"<code>RosterConcurrencyTest</code> ({cnt('RosterConcurrencyTest')}), <code>RosterBusyTest</code> ({cnt('RosterBusyTest')})", '<span class="pill ok">pass</span>'],
    ["Idempotency", "A replay test: the same request twice gives one effect", f"<code>OffCallReplayTest</code> ({cnt('OffCallReplayTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">The parallel tests run on virtual threads released by one latch. A trigger makes each recorded change take 200 ms to write, so the transactions overlap every time. With READ COMMITTED instead of SERIALIZABLE they still ended with one doctor on call, because the database rule refused the second commit; only the check that a retry happened (<code>roster.retries</code>) turned red. That is why the trap test checks isolation alone, with the rule switched off. Removing the <code>503</code> changed no test at first; <code>RosterBusyTest</code> (1 attempt in all) was added. Found while building.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "WriteSkewTrapTest.java", "<p>Written first: two real transactions, step by step, at READ COMMITTED and at SERIALIZABLE.</p>"),
    (T + "RosterConcurrencyTest.java", "<p>Two and three doctors leaving at once through the API.</p>"),
    (T + "RosterBusyTest.java", "<p>No retries left: <code>503</code>, nothing changed.</p>"),
    (T + "OffCallReplayTest.java", "<p>The same request twice; a retry once the ward is at its minimum.</p>"),
    (T + "RosterDatabaseTest.java", "<p>The ward rule and named constraints with plain SQL; a change whose record fails changes nothing.</p>"),
    (T + "RosterContractTest.java", "<p>The endpoint through HTTP.</p>"),
    (T + "ParallelApiTest.java", "<p>Shared by the parallel tests: the slow-write trigger and the start latch.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the demo roster before each test, request helpers.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/mediqo/roster/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=HandoverChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Hand over", "Beginner-friendly", 25,
    "<code>POST /rosters/{ward}/handover {from, to}</code>: the doctor taking over goes on call and the other goes off, in one transaction, so it works even when the ward is at its minimum. A handover already done answers the same.",
    "both tests in <code>HandoverChallengeTest</code> pass.",
    ["Use the same SERIALIZABLE retry as <code>offCall</code>: move it into a method that takes the work.",
     "The ward rule is checked at commit, so the order of the two updates inside the transaction does not matter to it."],
    "challenge/HandoverChallengeTest.java", ["challenge/solution/Roster.java", "challenge/solution/RosterController.java"]) + challenge(2, "Raise the minimum", "Go deeper", 35,
    "<code>PUT /rosters/{ward}/minimum {minOnCall}</code>, 1 to 50. A minimum above the doctors on call right now is refused (<code>409</code>), by the API and by the database.",
    "the three tests in <code>MinimumChallengeTest</code> pass.",
    ["Raising the minimum while a doctor goes off is the same write skew from the other side: run it SERIALIZABLE too.",
     "The V1 rule watches <code>roster</code> only. A V3 migration adds a deferred constraint trigger on <code>wards</code> named <code>wards_minimum_is_met</code>."],
    "challenge/MinimumChallengeTest.java", ["challenge/solution/Roster.java", "challenge/solution/RosterController.java", "challenge/solution/V3__minimum_rule_on_wards.sql"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>A roster with times</h2>
<p>Real rosters are time ranges: dr.iyer is on call from 20:00 to 08:00. Design the table so that a ward never has a moment below its minimum. Which rule can an exclusion constraint (<code>EXCLUDE USING gist</code> with <code>tstzrange</code>) hold, and which one (\"at least one at every moment\") still needs SERIALIZABLE or a lock on the ward row? Compare the two ways out of write skew: SERIALIZABLE and retries, or <code>SELECT ... FOR UPDATE</code> on the ward row so every change to one ward waits its turn.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: two connections, step by step, at READ COMMITTED.</li>
<li>Run the check and the change in one SERIALIZABLE transaction.</li>
<li>Retry the whole transaction on 40001, a few times, with a short random wait; then <code>503</code>.</li>
<li>Add the ward rule to the database, checked at commit, for every other writer.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["SERIALIZABLE and retry", "Retries under heavy contention; every transaction must be safe to run again.", '<span class="pill ok">Chosen</span>'],
    ["READ COMMITTED and a Java check", "Write skew: the ward can be left with nobody.", '<span class="pill bad">The trap</span>'],
    ["Lock the ward row (<code>SELECT ... FOR UPDATE</code>)", "No retries; every change to one ward waits in line, and every writer must remember to lock.", '<span class="pill warn">Good, if all writers lock</span>'],
    ["A counter column on wards, with a CHECK", "One row holds the rule; the counter must be kept in step with the roster.", '<span class="pill warn">Works, more to keep right</span>'],
    ["Only the database trigger", "Catches most races at commit, but two commits at the same instant can both pass.", '<span class="pill warn">A safety net, not the fix</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>wards_keep_min_on_call</code>", "Constraint trigger, deferred to commit", "The rule spans rows, so a CHECK cannot hold it; checked once, after all changes in the transaction."],
    ["<code>wards_min_on_call_positive</code>", "CHECK", "A ward needs at least one doctor on call."],
    ["<code>roster_pk</code>, <code>roster_doctor_shape</code>", "Primary key, CHECK", "One row per doctor per ward; names shaped <code>dr.name</code>."],
    ["<code>roster_changes_went</code>", "CHECK", "A change is off or on."]]) + """
<p><strong>Transaction boundary:</strong> one SERIALIZABLE transaction reads the ward, the doctor and the count, updates the roster and records the change. A retry starts a new one.</p>
""" + code(read(M + "V1__wards_and_roster.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Retries are part of SERIALIZABLE</dt><dd>PostgreSQL's documentation says applications using it must be ready to retry. Retry the whole transaction, never with side effects (emails, calls) inside it.</dd>
<dt>Count the retries</dt><dd>A rising retry or <code>503</code> count means contention: many writers on the same rows. Lock the ward row instead, or split the work.</dd>
<dt>Read-only transactions</dt><dd>Screens that only show the roster can run READ COMMITTED; only the decide-then-write paths need SERIALIZABLE.</dd>
<dt>Every writer</dt><dd>Night fixes in <code>psql</code> skip the API. The database rule covers them, within its limit.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is write skew?", "Two transactions read the same facts, each changes a different row based on them, and together they break a rule neither broke alone. No row is written twice, so row locks do not see it."),
    ("Does READ COMMITTED prevent it? REPEATABLE READ?", "No to both in PostgreSQL. REPEATABLE READ gives each transaction a fixed snapshot, but both snapshots still show the other doctor on call. SERIALIZABLE detects it."),
    ("What must you do when you use SERIALIZABLE?", "Retry on SQLState 40001: run the whole transaction again from the start, a limited number of times, with a short random wait."),
    ("How else can you prevent write skew?", "Lock a row that every writer touches (the ward), or turn the rule into one row with a CHECK (a counter). Both make the writers meet on one row."),
    ("How do you test it?", "Drive two connections step by step so the bad order happens every time; then a parallel test through the API, checked to fail without the fix."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Isolation", "SERIALIZABLE for the decision.", "You can show write skew with two connections and explain why REPEATABLE READ is not enough."],
    ["Retries", "40001 retried.", "The whole transaction, bounded, with a random wait, and a 503 at the end."],
    ["Proof", "A parallel test.", "One that fails without the fix, and a database rule for other writers."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("A lost race answered as a refusal",
     "\"If PostgreSQL stopped us, the other doctor won\": not always. Two Orthopaedics doctors may both go (three on call, one needed), but SERIALIZABLE can still stop one of them. Without a retry, that doctor is told the ward needs them, which is false. A 40001 means \"run again\", not \"no\".",
     "<code>twoDoctorsLeavingAtOnceLeaveOneOnCall</code>, <code>threeDoctorsLeavingAtOnceFromAWardThatNeedsOne</code> and <code>aLostRaceWithNoRetriesLeftIs503AndChangesNothing</code> fail."),
    ("The safety rule before the \"already off\" answer",
     "\"Safety first\" sounds right, but a phone that retries after a timeout now gets <code>409</code> once the ward is at its minimum, although its doctor did go off. The app shows an error for a change that happened.",
     "<code>aRetryIsNotRefusedEvenWhenTheWardIsNowAtItsMinimum</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate simplifies <code>Roster</code>: \"the retry loop is complicated; if PostgreSQL stops us, someone else changed the ward, so refuse\". They also move the minimum check to the top, \"safety first\". Read the file and list every problem before opening the findings.</p>
<p class="path">review/Roster.java</p>
""" + code(read("review/Roster.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">The ward is never left with nobody in the flawed version: SERIALIZABLE and the database rule still hold. What breaks is the answer: doctors refused who were allowed to go, and retries told \"no\" for a change already made.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
