"""Station 053 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 53,
    "stack": "Spring Boot 4.1.1 · Java 25 · JdbcClient · PostgreSQL 17 and MySQL 8.4 · Flyway per vendor · Testcontainers (both databases, shared containers)",
    "simulation": "Sign-ups are demo records; no email is sent to confirm an address.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL and MySQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/taskloom/signups/"
T = "src/test/java/com/taskloom/signups/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Collation", "A database's rules for comparing and sorting text.", "A dictionary that files \"Asha\" and \"asha\" together, or apart.", "<code>utf8mb4_0900_ai_ci</code>, <code>utf8mb4_bin</code>"),
    ("Case-insensitive", "Upper and lower case count as the same letter.", "\"ASHA\" and \"asha\" are one name.", "MySQL's default"),
    ("Accent-insensitive", "Letters with and without accents count as the same.", "\"jose\" and \"josé\" are one name.", "The <code>ai</code> in MySQL's default"),
    ("Expression index", "An index on a computed value, not the raw column.", "An index card filed under the name in lower case.", "<code>lower(email)</code>"),
    ("Testcontainers", "Real databases in Docker, started by the tests.", "A practice kitchen with the real stove.", "<code>Databases</code>"),
    ("Portability", "The same code giving the same answers on different databases.", "A recipe that works on gas and induction.", "Same tests on both"),
]
STORY = [
    ("Two databases, one schema", "Taskloom runs on MySQL for some customers and PostgreSQL for others, with the same table: <code>email VARCHAR(254) UNIQUE</code>."),
    ("One user or two?", "On MySQL, Asha@x.com and asha@x.com were one user. On PostgreSQL, they were two accounts, and Asha's projects were split between them. Support also found MySQL refusing josé@x.com because jose@x.com existed."),
    ("The fix", "Say exactly what \"the same email\" means (the same after lower-casing, nothing else), write it into each database's schema in that database's own words, and run the same tests on both."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">"UNIQUE" means "unique under this database's comparison rules", and the rules differ.</p>

<h2>What are we building?</h2>
<p><code>POST /signups</code> takes an email and a name. The same email in any case is refused with <code>409</code>, on PostgreSQL and on MySQL alike. The address is kept as the person typed it.</p>

<h2>An everyday analogy</h2>
<p>Two school offices keep the same register. One files every name in capitals; the other files names exactly as written, so "ASHA" and "Asha" get two pages. Same register, different filing rule. The fix is to agree on the rule and write it on both registers' covers.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Trim</strong> the address and check its shape (ASCII only, a demo rule).</li>
<li><strong>Look up</strong> <code>lower(email)</code>: is this person already here?</li>
<li><strong>Insert</strong>; the unique index on <code>lower(email)</code> refuses a duplicate, even one sent at the same moment.</li>
<li><strong>Answer</strong> <code>201</code>, or <code>409</code> for either refusal.</li>
</ol>

<details class="qa check"><summary>Check yourself: MySQL already ignores case. Why change its schema at all?</summary><p>Its default also ignores accents, and its rules depend on a collation setting someone can change. Making the column exact (<code>utf8mb4_bin</code>) and the index explicit (<code>lower(email)</code>) gives the same rule PostgreSQL has, written down, not inherited.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No email verification.</strong> Addresses are not confirmed.</li>
<li><strong>No international addresses.</strong> Non-ASCII emails are refused (a demo rule).</li>
<li><strong>No login.</strong> A sign-up is a record.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Taskloom</strong> (a fictional SaaS) supports both MySQL and PostgreSQL. Sign-up uniqueness behaved differently on each, creating duplicate accounts on one and refusing real addresses on the other.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> Asha@x.com signed up, <b>then</b> asha@x.com, ASHA@X.COM and " asha@x.com " are <code>409</code>, on both databases.</li>
<li><b>Given</b> 10 spellings of the same address at the same moment, <b>then</b> one sign-up, nine <code>409</code>, on both.</li>
<li><b>Given</b> jose@x.com and josé@x.com written directly to the table, <b>then</b> two rows, on both.</li>
<li><b>Given</b> an address without @, with non-ASCII letters, over 254 characters, or a blank name, <b>then</b> <code>400</code>.</li>
<li><b>Given</b> an unknown sign-up id, <b>then</b> <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>"The same email" means equal after lower-casing, and nothing more, on every database.</li>
<li>The rule is a named unique index in each schema: <code>signups_email_unique</code>.</li>
<li>Each database gets its own migration, in its own SQL.</li>
<li>Every contract and database test runs on both databases.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Explain collations, and how MySQL and PostgreSQL compare text by default.</li>
<li>Enforce case-insensitive uniqueness with an expression index on both.</li>
<li>Run the same tests on two real databases with Testcontainers.</li>
<li>Know where portability ends.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, against both databases, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/signups</code>", "Sign up: <code>email</code> (trimmed, ASCII, up to 254 characters) and <code>name</code>."],
    ["<code>GET</code>", "<code>/signups/{id}</code>", "Read a sign-up back (added so \"not found\" has something to miss)."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Signed up; <code>Location</code> points at it"],
    ['<span class="pill ok">200</span>', "The sign-up"],
    ['<span class="pill warn">400</span>', "Email or name missing or malformed"],
    ['<span class="pill warn">404</span>', "No such sign-up"],
    ['<span class="pill warn">409</span>', "This email, in any case, has already signed up"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl on """ + read("docs/captures/date.txt").strip() + """, in this order: the same jar running twice, on PostgreSQL (port 8080) and on MySQL (port 8081). JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-on-postgresql-asha-signs-up", "Case 1: PostgreSQL, Asha@x.com", "<b>Why:</b> <code>201</code>, kept as typed."),
    ("02-on-postgresql-asha-again-in-lower-case", "Case 2: PostgreSQL, asha@x.com", "<b>Why:</b> the same person: <code>409</code>. The old schema let this in."),
    ("03-on-mysql-asha-signs-up", "Case 3: MySQL, Asha@x.com", "<b>Why:</b> <code>201</code>."),
    ("04-on-mysql-asha-again-in-lower-case", "Case 4: MySQL, asha@x.com", "<b>Why:</b> <code>409</code>: the same answer as PostgreSQL, from the same rule."),
    ("05-an-email-without-an-at", "Case 5: asha.x.com", "<b>Why:</b> <code>400</code>."),
    ("06-no-such-signup", "Case 6: sign-up 99", "<b>Why:</b> <code>404</code>."),
]) + """
<h2>What "equal" means to each database</h2>
<p class="muted">Asked directly with psql and the mysql client (connected in utf8mb4, as the app is) after the requests above (<code>docs/captures/equality.txt</code>): the default text comparison, with no table and no index.</p>
""" + code(read("docs/captures/equality.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it. Each Spring test runs twice: once per database.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Mixed-case address", "Kept as typed", "<code>aSignupKeepsTheEmailAsTyped</code>"],
    ["Another case, or with spaces", "<code>409</code>, one row", "<code>theSameEmailInAnyCaseIs409</code>"],
    ["Similar but different addresses", "All accepted", "<code>differentEmailsAreDifferent</code>"],
    ["No @, non-ASCII, too long, blank name, missing email", "<code>400</code>, no row", "<code>badSignupsAre400</code>"],
    ["Unknown id", "<code>404</code>", "<code>unknownSignupsAre404</code>"],
    ["Duplicate or malformed rows written directly", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"],
    ["jose@ and josé@ written directly", "Two rows", "<code>anAccentMakesADifferentAddressOnBothDatabases</code>"],
    ["A batch with a duplicate", "Nothing kept", "<code>aBatchWithADuplicateLeavesNothing</code>"],
    ["10 spellings at the same moment", "One <code>201</code>, nine <code>409</code>", "<code>tenSpellingsAtOnceMakeOneSignup</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Assuming case-insensitive uniqueness works the same on both databases.</p>
<p>The trap test uses no Spring at all: plain JDBC on the two real databases, the old table (<code>email VARCHAR(254) NOT NULL UNIQUE</code>) created the same way on each, and the same inserts. PostgreSQL keeps both Ashas; MySQL keeps one. MySQL also refuses josé@x.com after jose@x.com, because its default collation ignores accents. The old lookup, <code>WHERE email = ?</code>, says "not signed up yet" on PostgreSQL. On the same table, an index on <code>lower(email)</code> refuses the second Asha.</p>
<p>While building, each part was undone once. A plain unique index on PostgreSQL turned 3 database tests red; the HTTP tests stayed green, because the Java lookup on <code>lower(email)</code> still answered <code>409</code> one request at a time. Only the race and the direct inserts showed the missing rule. MySQL's default collation instead of <code>utf8mb4_bin</code> turned 1 red (the accent test). Without the <code>DuplicateKeyException</code> catch, 2 (the race, on both databases). Comparing <code>email = ?</code> in the lookup turned none red: the index still answered <code>409</code>.</p>
</div>
""" + code(read(T + "CaseSensitivityTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SignupController.java", dwn("Trims and validates; <code>Location</code> on success.", "ASCII emails only, with the reason written down.", "Lower-casing rules that differ between Java and each database.")),
    (J + "SignupDesk.java", dwn("Looks up <code>lower(email)</code>, inserts, turns a duplicate key into <code>409</code>.",
        "Plain SQL that means the same on both databases.", "A lookup that misses a duplicate the index then refuses.",
        "<ul><li><code>lower(email) = ?</code> with a <code>Locale.ROOT</code> lower-cased value matches the expression index on both.</li><li>Spring turns both databases' duplicate errors into <code>DuplicateKeyException</code>.</li></ul>")),
    (M + "postgresql/V1__signups.sql", dwn("PostgreSQL's schema: an expression index on <code>lower(email)</code>.", "PostgreSQL compares exactly by default.", "Two accounts for one person.")),
    (M + "mysql/V1__signups.sql", dwn("MySQL's schema: an exact column (<code>utf8mb4_bin</code>) and a functional index on <code>lower(email)</code>.",
        "The same rule as PostgreSQL, the same name.", "Accent-insensitive comparison nobody chose.")),
    ("src/main/resources/application.yaml", "<p>PostgreSQL by default; Flyway reads <code>db/migration/{vendor}</code>.</p>"),
    ("src/main/resources/application-mysql.yaml", "<p>The <code>mysql</code> profile: the MySQL connection.</p>"),
    ("compose.yaml", "<p>Both databases, with health checks.</p>"),
    ("pom.xml", "<p>Both drivers, both Flyway modules, both Testcontainers modules.</p>"),
    (J + "SignupsApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/053-sign-up-emails-on-mysql-and-postgresql/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/taskloom/signups/
│   ├── SignupController.java   ├── SignupDesk.java   └── SignupsApplication.java
├── src/main/resources/
│   ├── application.yaml   ├── application-mysql.yaml
│   └── db/migration/postgresql/V1__signups.sql, db/migration/mysql/V1__signups.sql
├── src/test/java/com/taskloom/signups/   (see Tests)
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
""" + code("""docker compose up -d --wait                       # PostgreSQL on 5432, MySQL on 3306
./mvnw spring-boot:run                            # the API on PostgreSQL, http://localhost:8080
./mvnw spring-boot:run -Dspring-boot.run.profiles=mysql   # or the same API on MySQL
./mvnw test                                       # all """ + str(N_TESTS) + """ tests; starts its own containers""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d --wait
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd spring-boot:run "-Dspring-boot.run.profiles=mysql"
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. MySQL takes longer to start than PostgreSQL; the first test run downloads both images.</p>
<h2>Try it yourself</h2>
<p>Ask each database what "equal" means:</p>
""" + code("""docker compose exec postgres psql -U taskloom -d taskloom -c "SELECT 'Asha@x.com' = 'asha@x.com'"
docker compose exec mysql mysql --default-character-set=utf8mb4 -utaskloom -ptaskloom taskloom -e "SELECT 'Asha@x.com' = 'asha@x.com', 'jose@x.com' = 'josé@x.com'\"""", "bash") + """
<p>Compare your answers with <code>docs/captures/equality.txt</code>, from the build machine. Leave out <code>--default-character-set=utf8mb4</code> once: the client then talks latin1 to the server, and the answer about accents changes. That happened while this station was built.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Duplicate accounts on PostgreSQL only", "A plain <code>UNIQUE (email)</code>; PostgreSQL compares exactly.", "A unique index on <code>lower(email)</code>."],
    ["MySQL refuses an address that is different", "The default collation ignores accents (<code>ai</code>).", "<code>COLLATE utf8mb4_bin</code> on the column, plus the <code>lower(email)</code> index."],
    ["<code>Found non-empty schema(s) ... but no schema history table</code>", "Something created a table before Flyway ran (here: a test).", "Clean up after tests that create tables by hand."],
    ["Flyway runs the wrong SQL for the database", "One migrations folder for both.", "<code>spring.flyway.locations: classpath:db/migration/{vendor}</code>."],
    ["The mysql client gives a different answer from the app", "The client's connection character set (latin1 here) decides the collation of literals.", "<code>--default-character-set=utf8mb4</code>, as JDBC uses."],
    ["The first test run is slow", "MySQL's container takes several seconds to be ready.", "The containers are shared, so it happens once per run."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then each database's schema.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>PostgresSignupContractTest</code> ({cnt('PostgresSignupContractTest')}), <code>MySqlSignupContractTest</code> ({cnt('MySqlSignupContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>CaseSensitivityTrapTest</code> ({cnt('CaseSensitivityTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>PostgresSignupDatabaseTest</code> ({cnt('PostgresSignupDatabaseTest')}), <code>MySqlSignupDatabaseTest</code> ({cnt('MySqlSignupDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>One test, two databases</h2>
<p>The tests are written once, in <code>SignupContract</code> and <code>SignupDatabase</code>. Four tiny classes run them: each extends one and imports one database. The containers live in <code>Databases</code> and start once per run, shared by the Spring tests (through <code>@ServiceConnection</code>) and by the trap test (through plain JDBC).</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 and MySQL 8.4 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "SignupContract.java", "<p>The HTTP contract, written once.</p>"),
    (T + "SignupDatabase.java", "<p>Constraints, accents, a rollback and a race, written once.</p>"),
    (T + "PostgresSignupContractTest.java", "<p>The contract on PostgreSQL. Its three siblings are the same three lines for the other combinations.</p>"),
    (T + "Databases.java", "<p>The two shared containers and their <code>@ServiceConnection</code> configurations.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: an empty table before each test; parallel calls.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/taskloom/signups/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=FindByEmailChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Find by email", "Beginner-friendly", 15,
    "Add <code>GET /signups?email=…</code>: the sign-up for that address however it is typed, or <code>404</code>. The test runs on PostgreSQL; switch its <code>@Import</code> to try MySQL.",
    "the test in <code>FindByEmailChallengeTest</code> passes.",
    ["<code>SignupDesk.findByEmail</code> already exists.", "Trim before looking up."],
    "challenge/FindByEmailChallengeTest.java", ["challenge/solution/SignupController.java"]) + challenge(2, "Change an email", "Go deeper", 25,
    "Add <code>PATCH /signups/{id}/email</code>. Someone else's address in any case is <code>409</code>; changing the case of your own is fine. The test runs on MySQL.",
    "the test in <code>ChangeEmailChallengeTest</code> passes.",
    ["The lookup finds a holder: a conflict only if it is another row.",
     "The unique index still guards the race between the check and the update."],
    "challenge/ChangeEmailChallengeTest.java", ["challenge/solution/SignupDesk.java", "challenge/solution/SignupController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Is two databases worth it?</h2>
<p>List what Taskloom pays for supporting both: two migrations per change, every test twice, features one database lacks. Then list what it gains. When would you drop one, and how would you move its customers?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, mapping"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test on both real databases, with the old table.</li>
<li>Write the rule in words: equal after lower-casing, nothing else.</li>
<li>Translate it into each database's SQL, under one constraint name.</li>
<li>Write the tests once and run them on both.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Expression index on <code>lower(email)</code> on both; exact MySQL column", "Two migrations; queries must use <code>lower(email)</code>.", '<span class="pill ok">Chosen</span>'],
    ["Plain <code>UNIQUE (email)</code> on both", "Different answers per database.", '<span class="pill bad">The trap</span>'],
    ["Store the email lower-cased", "One plain unique index; the address is no longer shown as typed.", '<span class="pill warn">Simpler, loses the typing</span>'],
    ["PostgreSQL <code>citext</code> or a nondeterministic collation", "Neat on PostgreSQL; nothing like it on MySQL.", '<span class="pill warn">One database only</span>'],
    ["Check uniqueness in Java only", "Two requests at once both pass.", '<span class="pill bad">No</span>']]) + """
<h2>Database design</h2>
""" + table(["Database", "Column", "Constraints"], [
    ["PostgreSQL", "<code>email VARCHAR(254)</code> (exact comparison by default)", "<code>signups_email_unique</code> on <code>lower(email)</code>, <code>signups_email_shape</code>"],
    ["MySQL", "<code>email VARCHAR(254) COLLATE utf8mb4_bin</code>", "<code>signups_email_unique</code> on <code>(lower(email))</code>, <code>signups_email_shape</code>"]]) + """
""" + code(read(M + "postgresql/V1__signups.sql"), "sql") + code(read(M + "mysql/V1__signups.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Existing duplicates</dt><dd>On a live PostgreSQL database, creating the new index fails while two Ashas exist. Find them first (<code>GROUP BY lower(email) HAVING count(*) &gt; 1</code>), merge the accounts with the customers, then add the index.</dd>
<dt>Collations are settings</dt><dd>MySQL's server, database, table and column can each have a collation. Write the one you rely on into the column, not into a server setting someone may change.</dd>
<dt>Upgrades</dt><dd>MySQL changed its default collation in version 8.0. A rule inherited from a default can change with an upgrade; a rule written in the schema does not.</dd>
<dt>Index use</dt><dd>An expression index is only used when the query has the same expression. <code>WHERE email = ?</code> ignores it.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why can the same UNIQUE column behave differently on MySQL and PostgreSQL?", "Uniqueness uses the column's comparison rules. MySQL's default utf8mb4 collation is case- and accent-insensitive; PostgreSQL's default comparison is exact."),
    ("How do you make email uniqueness case-insensitive in PostgreSQL?", "A unique expression index on lower(email), and queries that compare lower(email). citext is another option, PostgreSQL-only."),
    ("What does utf8mb4_0900_ai_ci mean?", "utf8mb4 is the character set; 0900 is the Unicode collation algorithm version; ai is accent-insensitive; ci is case-insensitive."),
    ("Why run the tests on both databases?", "Because the behaviour that matters lives in the database. A test on one says nothing about the other; Testcontainers makes running both cheap."),
    ("Where does portability end?", "At SQL syntax (identity columns, functional indexes), collations, error messages and features. Keep the rule the same, and let each schema say it in its own SQL."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass, on both databases.", "You explained why the HTTP tests stayed green with a plain index."],
    ["Databases", "Collations explained.", "You can read a MySQL collation name."],
    ["Schema", "Expression index on both.", "A migration plan for existing duplicates."],
    ["Testing", "Same tests, two databases.", "Shared containers, one start per run."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any text that must be unique:</p>
<ul class="rules">
<li>What does "the same" mean here, in words?</li>
<li>Which collation does each database use for this column, and is it written in the schema?</li>
<li>Does every query compare the same expression the index is on?</li>
<li>Is the rule tested on every database the product supports?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
