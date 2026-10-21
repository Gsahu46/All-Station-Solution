"""Station 080 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 80,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Data JDBC @Version · ETag, If-Match, If-None-Match · PostgreSQL 17 trigger · Testcontainers",
    "simulation": "The board and its tasks are demo data, not Taskloom's. There is no sign-in in this station: editors are named only in the stories.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/taskloom/board/"
T = "src/test/java/com/taskloom/board/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Lost update", "Two people edit the same thing; the later save quietly replaces the earlier one.", "Two people editing a printed list and handing back their copies.", "the old board"),
    ("Version", "A number that goes up with every change.", "The edition number on a timetable.", "<code>tasks.version</code>"),
    ("ETag", "A label for one exact version, sent with a response.", "\"Timetable, edition 3\".", "<code>ETag: \"3\"</code>"),
    ("If-Match", "\"Save this only if it is still that version.\"", "\"Replace edition 3 with mine, if 3 is still current.\"", "on every PUT"),
    ("Optimistic locking", "No lock while people edit; the save checks the version and refuses if it moved.", "Checking the edition at the counter, not reserving the timetable.", "<code>@Version</code>"),
    ("412, 409, 428", "412: your copy is old. 409: your change breaks a rule. 428: say which version you edited.", "\"Old edition\", \"that slot is taken\", \"which edition?\"", "the three refusals"),
]
STORY = [
    ("Two managers, one card", "Meera moved \"Write the press release\" to doing. At the same moment Kabir reassigned it to Ravi."),
    ("One change vanished", "Kabir's screen still showed the card as open. His save sent the whole card back, and Meera's change disappeared. Nobody was told."),
    ("The fix", "Every card has a version. A save names the version it was based on, and only one save per version can win; the other editor is told to read again, and nothing is lost."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A save must say what it was based on. Otherwise the server cannot know it is overwriting someone.</p>

<h2>What are we building?</h2>
<p><code>GET /tasks/{id}</code> with an ETag, and <code>PUT /tasks/{id}</code> that saves only with the ETag of the current version.</p>

<h2>An everyday analogy</h2>
<p>A shared document that says \"this was changed while you were editing\" instead of saving over the other person's work.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Read</strong>: the card comes with <code>ETag: \"0\"</code>.</li>
<li><strong>Save</strong>: the editor sends <code>If-Match: \"0\"</code> with the new card.</li>
<li><strong>Check and write at once</strong>: <code>UPDATE ... WHERE id = 1 AND version = 0</code>; the version becomes 1.</li>
<li><strong>The other editor</strong> still sends <code>\"0\"</code>: no row matches, <code>412</code>; they read again and save on top.</li>
</ol>

<details class="qa check"><summary>Check yourself: Meera and Kabir press Save in the same millisecond. Can both win?</summary><p>No. The check is inside the UPDATE itself; PostgreSQL lets one of them change the row, and the other finds no row at version 0 any more. <code>tenEditsOfTheSameVersionAtOnceSaveExactlyOne</code> runs ten at once: one 200, nine 412.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No merging.</strong> A stale save is refused, not merged (Practice, challenge 3).</li>
<li><strong>No live editing.</strong> Real-time collaboration needs other tools.</li>
<li><strong>No sign-in.</strong> Stations 071 to 079 cover that.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Taskloom</strong> (a fictional team tool): two managers edit one task at once and one change silently disappears.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo board \"launch\": task 1 \"Write the press release\" and task 2 \"Book the venue\", both at version 0.</p>
<ol class="gwt">
<li><b>Given</b> a read, <b>then</b> the task and <code>ETag: \"version\"</code>.</li>
<li><b>Given</b> a save with the current ETag, <b>then</b> <code>200</code> and the next ETag.</li>
<li><b>Given</b> a save with an older ETag, <b>then</b> <code>412</code>, and the task is unchanged.</li>
<li><b>Given</b> a save without <code>If-Match</code>, <b>then</b> <code>428</code>.</li>
<li><b>Given</b> the current ETag but a title another task on the board has, <b>then</b> <code>409</code>.</li>
<li><b>Given</b> ten saves of one version at once, <b>then</b> exactly one is saved.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>The version check and the write are one statement.</li>
<li>Every writer must move the version on by one: the database enforces it.</li>
<li>A save and its activity row are one transaction.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Explain the lost update and reproduce it.</li>
<li>Use <code>@Version</code> and ETags with <code>If-Match</code>.</li>
<li>Choose between 409, 412 and 428.</li>
<li>Prove it with a real parallel test.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/tasks/{id}</code>", "The task, with <code>ETag: \"version\"</code>. With <code>If-None-Match</code> equal to it: <code>304</code>."],
    ["<code>PUT</code>", "<code>/tasks/{id}</code>", "<code>If-Match: \"version\"</code> and the whole task <code>{title, description, status, assignee}</code>."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span> / <span class="pill ok">304</span>', "Read or saved / unchanged since the ETag you have"],
    ['<span class="pill warn">400</span>', "A field missing, empty, too long, or an unknown status"],
    ['<span class="pill warn">404</span>', "No such task"],
    ['<span class="pill warn">409</span>', "Your copy is current, but the edit clashes with the board (a title already used)"],
    ['<span class="pill warn">412</span>', "Your copy is old (or the ETag is not one of ours): read again"],
    ['<span class="pill warn">428</span>', "No <code>If-Match</code>: the server cannot tell what you edited"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. JSON bodies are indented for reading; <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-both-managers-read-the-card", "Case 1: both managers read the card", "<b>Why:</b> version 0, <code>ETag: \"0\"</code>."),
    ("02-meera-saves-first", "Case 2: Meera saves first", "<b>Why:</b> <code>If-Match: \"0\"</code> matches: saved, <code>ETag: \"1\"</code>."),
    ("03-kabir-saves-his-old-copy", "Case 3: Kabir saves his old copy", "<b>Why:</b> still <code>\"0\"</code>: <code>412</code>. Meera's change stays."),
    ("04-kabir-reads-again", "Case 4: Kabir reads again", "<b>Why:</b> he sees Meera's change and <code>ETag: \"1\"</code>."),
    ("05-kabir-saves-on-top", "Case 5: Kabir saves on top", "<b>Why:</b> both changes kept, <code>ETag: \"2\"</code>."),
    ("06-no-if-match", "Case 6: a save without If-Match", "<b>Why:</b> <code>428</code>."),
    ("07-a-title-already-on-the-board", "Case 7: the current ETag, a title already on the board", "<b>Why:</b> <code>409</code>: not a stale copy, a clash."),
    ("08-the-board-polls-unchanged", "Case 8: the board polls with the ETag it has", "<b>Why:</b> <code>304</code>, no body."),
    ("09-no-such-task", "Case 9: no such task", "<b>Why:</b> <code>404</code>."),
]) + """
<h2>The activity feed afterwards</h2>
<p class="muted">From <code>psql</code> in <code>docs/capture.sh</code>: one row per accepted change, none for the refused ones.</p>
""" + code(read("docs/captures/changes.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A read", "The task with <code>ETag: \"0\"</code>", "<code>aTaskComesWithItsVersionAsETag</code>"],
    ["A save with the ETag", "<code>200</code>, the next ETag, the title trimmed", "<code>anEditWithTheETagSavesAndGivesTheNextETag</code>"],
    ["Polling with the current ETag", "<code>304</code>; after a change, <code>200</code>", "<code>anUnchangedTaskIs304ForAPollingBoard</code>"],
    ["Unknown task", "<code>404</code>", "<code>anUnknownTaskIs404</code>"],
    ["No If-Match", "<code>428</code>", "<code>anEditWithoutIfMatchIs428</code>"],
    ["A title already on the board", "<code>409</code>, version unchanged", "<code>aTitleAlreadyOnTheBoardIs409NotA412</code>"],
    ["Bad bodies", "<code>400</code>", "<code>badBodiesAre400</code>"],
    ["Ten saves of one version at once", "One <code>200</code>, nine <code>412</code>, one activity row", "<code>tenEditsOfTheSameVersionAtOnceSaveExactlyOne</code>"],
    ["Ten editors that read, edit, retry", "All ten changes land, version 10", "<code>editsThatEachReadFirstAllLandInTurn</code>"],
    ["An UPDATE without the version, in plain SQL", "Refused by the trigger", "<code>anUpdateThatForgetsTheVersionIsRefused</code>"],
    ["Other rules in plain SQL", "Refused by named constraints", "<code>taskRulesHoldWithoutJava</code>"],
    ["A save whose activity row fails", "Rolled back; the same edit works afterwards", "<code>anEditWhoseActivityRowFailsLeavesTheTaskAsItWas</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Last write wins: two editors silently overwrite each other.</p>
<ul>
<li><strong>The old board.</strong> Meera and Kabir open the card; Meera saves \"doing\"; Kabir saves his screen, which still says \"open\". The card ends with Kabir's assignee and the old status: Meera's change is gone, and nobody was told.</li>
<li><strong>The API.</strong> The same two saves: Meera's with <code>\"0\"</code> is saved; Kabir's with <code>\"0\"</code> is <code>412</code>. He reads again and saves on top: both changes are kept.</li>
</ul>
<p>While building, each part was undone once: no <code>@Version</code> turned 6 tests red (every edit then failed on the version trigger); saving on the current version instead of the one in <code>If-Match</code> 2; the save without its transaction 1; no <code>428</code> 1; no version trigger 1.</p>
</div>
""" + code(read(T + "LastWriteWinsTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "TaskController.java", dwn("Read with an ETag; save only with If-Match.",
        "No <code>If-Match</code> is <code>428</code>; a value that is not one of our strong ETags is <code>412</code>; the response carries the next ETag.",
        "Saves that do not say what they are based on.",
        "<p>Spring MVC answers <code>If-None-Match</code> by itself for a <code>ResponseEntity</code> that carries an ETag: the <code>304</code> in case 8 needs no code here. Found while building, when a planned challenge passed with nothing written.</p>")),
    (J + "TaskEdits.java", dwn("The save.",
        "<code>@Version</code> makes it one <code>UPDATE ... AND version = ?</code>; no row is <code>412</code>; a title clash is <code>409</code>; the activity row in the same transaction.",
        "Two saves of one version both winning, or a feed that lists changes that never happened.",
        "<p>Spring Data JDBC throws <code>OptimisticLockingFailureException</code> and <code>DuplicateKeyException</code> as they are, not wrapped. A first version walked the cause chain; removing the walk changed no test, so it is two catch clauses now.</p>")),
    (J + "Task.java", "<p>The card as a record; <code>@Version</code> on the version.</p>"),
    (J + "Tasks.java", "<p>A Spring Data repository.</p>"),
    (M + "V1__tasks.sql", dwn("Tasks, the activity feed, and the version trigger.",
        "Every UPDATE must move the version on by exactly one, from any writer.",
        "A script or an old service writing without a version, the way the old board did.",
        "<p>A CHECK cannot compare the old and new row, so this rule is a trigger that raises a <code>check_violation</code> named after it.</p>")),
    (M + "V2__demo_board.sql", "<p>Two demo tasks. <code>ALTER ... RESTART WITH 3</code> instead of <code>SELECT setval(...)</code>, because the tests reload this file and <code>update()</code> refuses a statement that returns a row.</p>"),
    ("src/main/resources/application.yaml", "<p>The database connection.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "BoardApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/080-task-board-edits-without-lost-updates/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/taskloom/board/
│   ├── TaskController.java   ├── TaskEdits.java   ├── Task.java
│   ├── Tasks.java   └── BoardApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__tasks.sql, V2__demo_board.sql
├── src/test/java/com/taskloom/board/   (see Tests)
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
<p>Two saves from the same read:</p>
""" + code("""for who in meera kabir; do
  curl -s -o /dev/null -w "$who %{http_code}\\n" -X PUT http://localhost:8080/tasks/2 -H 'Content-Type: application/json' -H 'If-Match: "0"' \\
    -d "{\\"title\\": \\"Book the venue\\", \\"description\\": \\"Capacity 200.\\", \\"status\\": \\"done\\", \\"assignee\\": \\"$who\\"}"
done""", "bash") + """
<p>It prints <code>meera 200</code> and <code>kabir 412</code>.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>tasks_version_must_increase: version 0 to 0</code>", "A writer updated without moving the version (here: <code>@Version</code> removed).", "Let <code>@Version</code> do it, or write <code>version = version + 1 ... AND version = ?</code>."],
    ["<code>A result was returned when none was expected</code>", "A <code>SELECT</code> run through <code>update()</code>.", "Use a statement that returns nothing, as V2 does."],
    ["Every save is <code>412</code>", "The client sends a weak ETag (<code>W/\"1\"</code>).", "Send the ETag exactly as received; <code>If-Match</code> compares strongly."],
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>TaskContractTest</code> ({cnt('TaskContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>LastWriteWinsTrapTest</code> ({cnt('LastWriteWinsTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>TaskDatabaseTest</code> ({cnt('TaskDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Concurrency", "A real concurrency test that proves the invariant holds", f"<code>TaskConcurrencyTest</code> ({cnt('TaskConcurrencyTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">The parallel tests run on virtual threads released together by one latch, against the real PostgreSQL. The invariant: one saved change per version, and the activity feed agrees with the task.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Spring Data JDBC, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "LastWriteWinsTrapTest.java", "<p>Written first: the old board drops a change; the API refuses the stale save and keeps both.</p>"),
    (T + "TaskConcurrencyTest.java", "<p>Ten saves of one version at once; ten editors that read, edit and retry.</p>"),
    (T + "TaskDatabaseTest.java", "<p>The version trigger and every named constraint with plain SQL; a save whose activity row fails.</p>"),
    (T + "TaskContractTest.java", "<p>ETags, 304, 404, 428, 409, 400 through HTTP.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the demo board from V2 before each test, request helpers.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/taskloom/board/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=PatchChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "PATCH only what changed", "Beginner-friendly", 30,
    "<code>PATCH /tasks/{id}</code> with a JSON merge patch (<code>application/merge-patch+json</code>) changes only the fields sent, with the same <code>If-Match</code> rules as PUT.",
    "both tests in <code>PatchChallengeTest</code> pass.",
    ["Merge the fields sent into the stored task, validate the result like a PUT body, then save it the same way.",
     "A PATCH changes less, but it is still based on a version: <code>If-Match</code> stays required."],
    "challenge/PatchChallengeTest.java", ["challenge/solution/TaskController.java"]) + challenge(2, "Delete only what you saw", "Go deeper", 20,
    "<code>DELETE /tasks/{id}</code> with <code>If-Match</code>: <code>204</code> if the task is still that version, <code>412</code> if it changed since, <code>428</code> without the header.",
    "both tests in <code>ConditionalDeleteChallengeTest</code> pass.",
    ["With <code>@Version</code>, Spring Data JDBC deletes with <code>AND version = ?</code> too.",
     "Pass the version from <code>If-Match</code>, not the one you just read."],
    "challenge/ConditionalDeleteChallengeTest.java", ["challenge/solution/TaskController.java", "challenge/solution/TaskEdits.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Merge instead of refuse</h2>
<p>Meera changed the status and Kabir the assignee: the two edits do not touch the same field. Design a save that merges them automatically (keep the version each field was last changed at), and decide what happens when both change the same field. When would you need live collaboration instead (operational transform, CRDTs)?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: two saves from one read.</li>
<li>A version column, <code>@Version</code>, and the version as the ETag.</li>
<li><code>If-Match</code> required; 412, 409 and 428 chosen on purpose.</li>
<li>A trigger so no writer can skip the version.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Optimistic: version in If-Match, checked in the UPDATE", "The loser reads again.", '<span class="pill ok">Chosen</span>'],
    ["Last write wins", "Changes vanish silently.", '<span class="pill bad">The trap</span>'],
    ["Read the version, compare in Java, then update", "Two editors can pass the check together.", '<span class="pill bad">A race</span>'],
    ["Pessimistic lock while editing (SELECT ... FOR UPDATE)", "A row held for as long as someone edits.", '<span class="pill warn">For seconds, never for a form</span>'],
    ["Merge field by field", "Per-field versions and a rule for clashes.", '<span class="pill warn">Kinder; more to build</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>tasks_version_must_increase</code>", "Trigger", "Every writer moves the version on by one."],
    ["<code>tasks_board_title_unique</code>", "UNIQUE", "The rule behind the 409."],
    ["<code>tasks_status</code>, <code>_title_length</code>, <code>_version_nonnegative</code>", "CHECKs", "Values the board can show."],
    ["<code>task_changes_one_per_version</code>", "UNIQUE", "One feed entry per accepted change."]]) + """
<p><strong>Transaction boundary:</strong> one save is one transaction: the task and its activity row.</p>
""" + code(read(M + "V1__tasks.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>The second editor</dt><dd>A <code>412</code> is only kind if the app shows what changed and keeps the user's text. Return or refetch the current task.</dd>
<dt>Caches and proxies</dt><dd>ETags work with caches; make sure a proxy does not turn strong ETags into weak ones (some do when compressing), or every save fails.</dd>
<dt>Every writer</dt><dd>Batch jobs and admin scripts are writers too: the trigger stops them from overwriting silently.</dd>
<dt>Standards</dt><dd>ETag, If-Match, If-None-Match, 304 and 412 are in RFC 9110 and RFC 9111 (Internet Standards); 428 is RFC 6585 (Proposed Standard); JSON merge patch is RFC 7396 (Proposed Standard).</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is a lost update?", "Two read-modify-write cycles overlap; the second write is based on old data and replaces the first change without anyone knowing."),
    ("How does @Version prevent it?", "The update includes AND version = :expected and increments it. If another write got there first, no row matches and the save fails."),
    ("409 or 412?", "412 when a precondition in the request (If-Match) is false: your copy is old. 409 when the request is current but conflicts with the resource's rules."),
    ("Why require If-Match (428)?", "Without it the server cannot know which version the client edited, so it cannot tell a stale save from a fresh one."),
    ("Why not compare versions in Java first?", "Two requests can both read version 3 and pass the check before either writes. The check must be in the same statement as the write."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Versioning", "@Version and ETags.", "A database rule so no writer skips the version."],
    ["HTTP", "412 for stale saves.", "409, 412 and 428 each where they belong."],
    ["Proof", "A test with two saves.", "Ten in parallel, and ten polite retries."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("Saving on top of the latest version",
     "\"No more read it again errors\": the save now uses the version it just read, not the one the editor saw. Every stale save succeeds and replaces the newer one: last write wins, with <code>@Version</code> still in the code.",
     "<code>theSecondSaveOnTheSameVersionIsRefusedAndNothingIsLost</code> and <code>tenEditsOfTheSameVersionAtOnceSaveExactlyOne</code> fail."),
    ("If-Match made optional",
     "Clients that send nothing are treated as editing version 0, so they can never prove what they edited; with the first flaw, it would not matter anyway.",
     "<code>anEditWithoutIfMatchIs428</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate answers two complaints: editors dislike \"read it again\" errors, so saves now apply on top of the latest version; and the mobile app does not send <code>If-Match</code> yet, so it is optional. \"<code>@Version</code> still guards the write.\" Read the two files and list every problem before opening the findings.</p>
<p class="path">review/TaskEdits.java</p>
""" + code(read("review/TaskEdits.java"), "java") + """
<p class="path">review/TaskController.java</p>
""" + code(read("review/TaskController.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the two flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note"><code>@Version</code> \"still guards the write\" is true, and useless: it now guards against a race of milliseconds inside the server, while the real race, minutes between a read and a save, is let through.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
