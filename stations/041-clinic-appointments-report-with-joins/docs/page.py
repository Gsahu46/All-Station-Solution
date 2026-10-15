"""Station 041 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 41,
    "stack": "Spring Boot 4.1.1 · Java 25 · PostgreSQL 17: INNER and LEFT JOIN, GROUP BY, HAVING, FILTER, COALESCE · JdbcClient · Flyway · Testcontainers",
    "simulation": "Doctors, patients, fees and appointments are demo data for one week, not Mediqo's. The report reads records only.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/mediqo/reports/"
T = "src/test/java/com/mediqo/reports/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("JOIN", "Combine rows from two tables that match on a condition.", "Matching a class list with an exam results list by roll number.", "<code>doctors</code> with <code>appointments</code>"),
    ("INNER JOIN", "Keep only rows that have a match on both sides.", "Only students who sat the exam appear.", "the trap"),
    ("LEFT JOIN", "Keep every row on the left, matched or not; missing values are NULL.", "Every student appears; absentees get a blank.", "<code>DoctorLoadReport</code>"),
    ("GROUP BY", "Collapse rows into one per group, with totals.", "One line per doctor.", "<code>GROUP BY d.id</code>"),
    ("HAVING", "A condition on the groups, after counting.", "\"Only doctors with at least 2 appointments\".", "<code>minAppointments</code>"),
    ("NULL", "\"No value\": not zero, and any comparison with it is not true.", "A blank cell, not a 0.", "<code>coalesce(sum(…), 0)</code>"),
]
STORY = [
    ("A weekly report", "Every Monday, the clinic head reads how many patients each doctor saw last week."),
    ("Two doctors are wrong", "Dr Khan joined last week and saw nobody yet. He is missing from the report altogether, so nobody notices he is idle. Dr Mehta shows 4 appointments, though he saw 3: one patient had two follow-ups booked, and the report counted that visit twice."),
    ("The fix", "Start from every doctor, attach their appointments if there are any, count appointments themselves, and count follow-ups separately."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A report should show zero as zero, not leave it out, and count each thing once.</p>

<h2>What are we building?</h2>
<p><code>GET /reports/doctor-load?from=…&amp;to=…</code> lists every active doctor with the appointments, completed visits, no-shows, follow-ups and fees of those days, busiest first.</p>

<h2>An everyday analogy</h2>
<p>A school attendance register. It lists every student, and an absent student gets a 0, not a missing line. If one student brought two notes, they are still one student.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Start from every active doctor.</strong></li>
<li><strong>Attach appointments</strong> in the range, if any (LEFT JOIN, the range in the join condition).</li>
<li><strong>Attach follow-up counts</strong>, already totalled per appointment, so no row repeats.</li>
<li><strong>Count per doctor</strong>, turning \"no fees\" (NULL) into 0.</li>
</ol>

<details class="qa check"><summary>Check yourself: the LEFT JOIN is in place, but the query still says <code>WHERE a.starts_at &gt;= '2026-10-05'</code>. Does Dr Khan appear?</summary><p>No. For Dr Khan, <code>a.starts_at</code> is NULL, and <code>NULL &gt;= date</code> is not true, so WHERE removes his row. The condition belongs in the JOIN's ON clause.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No booking.</strong> A read-only report.</li>
<li><strong>No charts.</strong> JSON rows; a dashboard reads them.</li>
<li><strong>One clinic.</strong> Many clinics over a year is challenge 3.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Mediqo</strong> (a fictional clinic chain) gets a weekly report that hides doctors with zero appointments and double-counts appointments that have follow-ups.</p>

<h2>Acceptance criteria</h2>
<p class="muted">On the demo week, 5 to 11 October 2026.</p>
<ol class="gwt">
<li><b>Given</b> the week, <b>then</b> Dr Mehta 3, Dr Iyer 2, Dr Rao 1, Dr Khan 0, in that order; the retired Dr Das is not listed.</li>
<li><b>Given</b> Dr Mehta's appointment with two follow-ups, <b>then</b> it counts once as an appointment, and his follow-ups total 3.</li>
<li><b>Given</b> a cancelled appointment, <b>then</b> it is not counted; fees count only completed visits.</li>
<li><b>Given</b> Sunday 11 October only, <b>then</b> Dr Iyer's 23:30 appointment is in, and Dr Rao's at 00:15 on Monday is not.</li>
<li><b>Given</b> <code>minAppointments=2</code>, <b>then</b> only Dr Mehta and Dr Iyer.</li>
<li><b>Given</b> a week with no appointments, <b>then</b> every active doctor at zero. <b>Given</b> <code>to</code> before <code>from</code>, more than 92 days, or a missing or malformed date, <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Every active doctor appears, whatever the range holds.</li>
<li>Days are India days; <code>from</code> and <code>to</code> are both included.</li>
<li>No count is inflated by a one-to-many join.</li>
<li>Money in integer paise; no NULL in the output.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Choose INNER or LEFT JOIN, and put conditions in ON or WHERE on purpose.</li>
<li>Use GROUP BY, HAVING, and aggregates with FILTER.</li>
<li>Handle NULL: <code>count(column)</code> vs <code>count(*)</code>, <code>coalesce</code>.</li>
<li>Avoid join fan-out by aggregating before joining.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/reports/doctor-load?from=YYYY-MM-DD&amp;to=YYYY-MM-DD&amp;minAppointments=0</code>", "Load per active doctor, busiest first. <code>minAppointments</code> is optional."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "A report, even if every count is zero"],
    ['<span class="pill warn">400</span>', "<code>to</code> before <code>from</code>, more than 92 days, a missing or malformed date, a negative minimum"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, against the demo data. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-the-demo-week", "Case 1: 5 to 11 October", "<b>Why:</b> every active doctor, Dr Khan at zero, Dr Mehta at 3 with 3 follow-ups."),
    ("02-at-least-two-appointments", "Case 2: <code>minAppointments=2</code>", "<b>Why:</b> HAVING filters after counting."),
    ("03-one-sunday", "Case 3: Sunday 11 October", "<b>Why:</b> 23:30 on Sunday is in; 00:15 on Monday is not."),
    ("04-a-quiet-week", "Case 4: a week in January", "<b>Why:</b> no appointments: everyone at 0, fees 0, not NULL."),
    ("05-to-before-from", "Case 5: to before from", "<b>Why:</b> <code>400</code>."),
]) + """
<h2>The old report, on the same data</h2>
<p class="muted">The old SQL, run with psql against the same database after the captures (<code>docs/captures/old-report.txt</code>):</p>
""" + code(read("docs/captures/old-report.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A doctor with no appointments", "Listed at 0", "<code>theReportCountsEveryDoctorCorrectly</code>"],
    ["An appointment with two follow-ups", "Counted once", "<code>theWeekShowsEveryActiveDoctorBusiestFirst</code>"],
    ["Cancelled; retired doctor", "Not counted; not listed", "<code>theWeekShowsEveryActiveDoctorBusiestFirst</code>"],
    ["23:30 Sunday, 00:15 Monday", "In; out", "<code>theDaysAreIndiaDaysWithBothEndsIncluded</code>"],
    ["<code>minAppointments=2</code>", "Two doctors", "<code>minAppointmentsFiltersAfterCounting</code>"],
    ["A week with nothing", "Everyone at 0", "<code>aWeekWithNoAppointmentsListsEveryoneAtZero</code>"],
    ["Bad ranges", "<code>400</code>", "<code>badRangesAre400</code>"],
    ["Unknown doctor, status, negative fee, orphan follow-up", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"],
    ["A failed import of appointments", "Rolled back; the report unchanged", "<code>aRolledBackDayOfAppointmentsNeverReachesTheReport</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">INNER JOIN hides doctors with zero appointments.</p>
<p>Four tests on the demo week. The old SQL leaves out Dr Khan and gives Dr Mehta 4. Switching to LEFT JOIN but keeping the date in WHERE leaves Dr Khan out again. Moving the date into ON but keeping <code>count(*)</code> gives Dr Khan an appointment he never had. The report gives 3, 2, 1 and 0. While building, each part of the query was undone once:</p>
<ul>
<li>An INNER JOIN turned 5 tests red.</li>
<li>Conditions moved out of ON turned 5 red, and a date also in WHERE 5.</li>
<li><code>count(*)</code> turned 4 red.</li>
<li>Follow-ups joined row by row turned 2 red.</li>
<li>No <code>coalesce</code> turned 5 red (a NULL cannot become a number).</li>
<li>Including retired doctors turned 3 red.</li>
</ul>
</div>
""" + code(read(T + "InnerJoinTrapTest.java"), "java") + code(read(T + "OldReportQueries.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "ReportController.java", dwn("Reads and checks the date range, returns the report.",
        "Range rules are checked before the database is asked.",
        "A year-long report that scans every appointment.")),
    (J + "DoctorLoadReport.java", dwn("The report as one SQL query with <code>JdbcClient</code>.",
        "LEFT JOIN with conditions in ON, follow-ups pre-counted, <code>count(a.id)</code>, <code>FILTER</code>, <code>coalesce</code>.",
        "The trap and its two half-fixes.",
        "<ul><li><code>count(a.id) FILTER (WHERE …)</code> counts a subset in the same pass.</li><li>The subquery turns follow-ups into one row per appointment before the join, so nothing repeats.</li><li>Columns map to the record by name: <code>doctor_id</code> becomes <code>doctorId</code>.</li></ul>")),
    (M + "V1__doctors_appointments_follow_ups.sql", dwn("Three tables, with named constraints and an index on doctor and time.",
        "The index serves \"this doctor's appointments in this range\".",
        "A full scan of appointments for every doctor.")),
    (M + "V2__demo_week.sql", "<p>The demo week, with every edge the tests need: a doctor with none, a retired doctor, follow-ups, a cancellation, and appointments at both ends of Sunday night.</p>"),
    ("src/main/resources/application.yaml", "<p>The database.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "ReportsApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/041-clinic-appointments-report-with-joins/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/mediqo/reports/
│   ├── ReportController.java   ├── DoctorLoadReport.java   └── ReportsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__doctors_appointments_follow_ups.sql, V2__demo_week.sql
├── src/test/java/com/mediqo/reports/   (see Tests)
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
./mvnw spring-boot:run      # the API on http://localhost:8080; Flyway loads the demo week
./mvnw test                 # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>See a LEFT JOIN's empty row for yourself:</p>
""" + code("""docker compose exec postgres psql -U mediqo -d mediqo -c "SELECT d.name, a.id AS appointment FROM doctors d LEFT JOIN appointments a ON a.doctor_id = d.id WHERE d.id = 4"
docker compose exec postgres psql -U mediqo -d mediqo -c "SELECT count(*), count(a.id) FROM doctors d LEFT JOIN appointments a ON a.doctor_id = d.id WHERE d.id = 4\"""", "bash") + """
<p>One row with an empty appointment; <code>count(*)</code> is 1, <code>count(a.id)</code> is 0.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["A doctor disappears from a LEFT JOIN report", "A condition on the right table is in WHERE.", "Move it into the ON clause."],
    ["A doctor with nothing shows 1", "<code>count(*)</code> counts the empty row.", "Count a column of the right table: <code>count(a.id)</code>."],
    ["Totals are too high", "A one-to-many join repeats rows before counting.", "Aggregate the many side first, or count DISTINCT ids."],
    ["<code>null</code> instead of 0", "<code>sum</code> of no rows is NULL.", "<code>coalesce(sum(…), 0)</code>."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, and an empty range", f"<code>DoctorLoadContractTest</code> ({cnt('DoctorLoadContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>InnerJoinTrapTest</code> ({cnt('InnerJoinTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>ReportDatabaseTest</code> ({cnt('ReportDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">A report has nothing to be \"not found\": an empty range is a valid answer with every doctor at zero, and that is what the contract tests check.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "InnerJoinTrapTest.java", "<p>Written first: the old SQL and its two half-fixes, then the report.</p>"),
    (T + "DoctorLoadContractTest.java", "<p>The demo week, HAVING, the ends of a day, an empty week, and bad ranges.</p>"),
    (T + "ReportDatabaseTest.java", "<p>Named constraints, and a rolled-back import.</p>"),
    (T + "OldReportQueries.java", "<p>The old SQL, kept only in tests.</p>"),
    (T + "ApiTest.java", "<p>Shared setup and what the demo week contains.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/mediqo/reports/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=NoShowRateChallengeTest</code> (Docker must be running).</li>
<li>Change the SQL until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "No-show rate", "Beginner-friendly", 20,
    "Add <code>noShowPercent</code>: no-shows as a rounded whole percentage of appointments. A doctor with no appointments has no rate (<code>null</code>), not 0% and not an error.",
    "the test in <code>NoShowRateChallengeTest</code> passes.",
    ["<code>nullif(count(a.id), 0)</code> turns a zero divisor into NULL, and anything divided by NULL is NULL.",
     "Multiply by <code>100.0</code>, not <code>100</code>, or integer division drops the fraction first."],
    "challenge/NoShowRateChallengeTest.java", ["challenge/solution/DoctorLoadReport.java"]) + challenge(2, "Load per speciality", "Go deeper", 25,
    "Add <code>GET /reports/speciality-load?from&amp;to</code>: per speciality, active doctors and appointments, busiest first, every speciality with an active doctor included.",
    "the test in <code>SpecialityLoadChallengeTest</code> passes.",
    ["After joining appointments, a doctor appears once per appointment: <code>count(DISTINCT d.id)</code>.",
     "Keep the LEFT JOIN and the conditions in ON, as in the main report."],
    "challenge/SpecialityLoadChallengeTest.java", ["challenge/solution/DoctorLoadReport.java", "challenge/solution/ReportController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>A year, 200 clinics</h2>
<p>Head office wants this report for any range up to a year, across 200 clinics with 3 crore appointments. Compare running the query on the main database, on a read replica, and from a daily summary table filled each night. What does each cost, how fresh is it, and how would you handle an appointment edited after its day was summarised?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, index"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write demo data with every edge: zero, retired, cancelled, follow-ups, both ends of a night.</li>
<li>Write the trap test with the old SQL, then each half-fix.</li>
<li>Write the report: LEFT JOIN, conditions in ON, pre-counted follow-ups, <code>count(a.id)</code>, <code>coalesce</code>.</li>
<li>Check the whole response field by field.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["One SQL query with LEFT JOIN and FILTER", "SQL to read carefully.", '<span class="pill ok">Chosen</span>'],
    ["INNER JOIN", "Zero-rows disappear.", '<span class="pill bad">The trap</span>'],
    ["Joining follow-ups directly with <code>count(DISTINCT a.id)</code>", "Correct counts, but sums over the joined rows (fees) would still repeat.", '<span class="pill warn">Fragile</span>'],
    ["Load everything into Java and group there", "Moves every row over the network; fine for a week, not for a year.", '<span class="pill warn">Small data only</span>'],
    ["A JPA entity graph", "Many queries or huge joins for a summary.", '<span class="pill bad">Wrong tool for reports</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Key and constraints", "Why"], [
    ["<code>doctors</code>", "PK <code>id</code>; <code>active</code>", "Retired doctors stay for history but leave reports."],
    ["<code>appointments</code>", "Identity PK. <code>appointments_doctor_fk</code>, <code>appointments_status_known</code>, <code>appointments_fee_not_negative</code>. Index <code>(doctor_id, starts_at)</code>.", "The facts the report counts, with the index its join uses."],
    ["<code>follow_ups</code>", "Identity PK. <code>follow_ups_appointment_fk</code>.", "One-to-many from appointments: the source of the fan-out."]]) + """
""" + code(read(M + "V1__doctors_appointments_follow_ups.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Report load</dt><dd>Reports read many rows; run big ones on a read replica so they never slow down booking.</dd>
<dt>Check with EXPLAIN</dt><dd><code>EXPLAIN ANALYZE</code> shows whether the <code>(doctor_id, starts_at)</code> index is used. Check before the data grows, not after.</dd>
<dt>Time zones</dt><dd>Store instants; turn India days into a time range once, in one place.</dd>
<dt>Reconciling</dt><dd>A report that disagrees with the billing system is usually a join problem: compare row counts before and after each join.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("INNER JOIN or LEFT JOIN?", "INNER keeps only matching rows. LEFT keeps every row of the left table, with NULLs where nothing matches. Use LEFT when \"none\" is a valid answer you must show."),
    ("Why does a condition in WHERE break a LEFT JOIN?", "WHERE runs after the join. For unmatched rows the right-side columns are NULL, and a comparison with NULL is not true, so WHERE removes exactly the rows the LEFT JOIN kept. Put such conditions in ON."),
    ("count(*) or count(column)?", "count(*) counts rows, including the NULL row a LEFT JOIN creates; count(column) counts non-NULL values. To count matches, count a column of the right table."),
    ("What is join fan-out?", "Joining a one-to-many relation repeats the 'one' row for each 'many'. Counts and sums over the 'one' side then grow. Aggregate the many side first, or count DISTINCT."),
    ("WHERE or HAVING?", "WHERE filters rows before grouping; HAVING filters groups after aggregates are computed, such as 'at least 2 appointments'."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You predicted each half-fix's result before running it."],
    ["Joins", "LEFT JOIN with conditions in ON.", "You can explain fan-out with a two-row example."],
    ["NULL", "count(column), coalesce.", "NULLIF for safe division."],
    ["Data", "Demo data covering every edge.", "EXPLAIN shows the index in use."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any report query:</p>
<ul class="rules">
<li>Can a group have zero rows? Does the join keep it?</li>
<li>Is any condition on the right side of a LEFT JOIN in WHERE?</li>
<li>Does a one-to-many join run before a count or a sum?</li>
<li>Can any aggregate return NULL to the client?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
