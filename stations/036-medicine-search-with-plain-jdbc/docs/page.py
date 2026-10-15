"""Station 036 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 36,
    "stack": "Spring Boot 4.1.1 · Java 25 · plain JDBC: DataSource, PreparedStatement, ResultSet · HikariCP · PostgreSQL 17 · Flyway · Testcontainers",
    "simulation": "The catalogue and prices are demo data, not Mediqo's. The prescriptions belong to fictional patients, with phone numbers that are not real; they exist so the trap test can show what the old search leaked.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/mediqo/pharmacy/"
T = "src/test/java/com/mediqo/pharmacy/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("JDBC", "Java's standard way to talk to a relational database.", "A phone line to the database.", "<code>java.sql</code>"),
    ("DataSource and Connection", "A DataSource hands out connections; a connection is one open line to the database.", "A switchboard and one call.", "<code>dataSource.getConnection()</code>"),
    ("Connection pool", "A few connections kept open and lent out, because opening one is slow.", "Library books: borrow, then return.", "HikariCP"),
    ("PreparedStatement", "SQL with <code>?</code> where values go; values are sent separately and never read as SQL.", "A form with boxes: whatever you write in a box stays in the box.", "<code>MedicineSearch</code>"),
    ("SQL injection", "User text that becomes part of the SQL and changes what the query does.", "Writing \"and also give me the safe keys\" on a bank slip, and the clerk obeying.", "the trap"),
    ("try-with-resources", "A <code>try</code> that closes what it opened, on every path.", "A door that shuts itself.", "<code>try (Connection c = …)</code>"),
]
STORY = [
    ("A search box", "Customers type a medicine name. The code glues their text into the SQL: <code>… WHERE name ILIKE '%</code> + text + <code>%'</code>."),
    ("Someone types SQL", "One search for <code>x' UNION SELECT patient_name, patient_phone, doctor FROM prescriptions --</code> returns every patient's name, phone and doctor. A customer searching for St. John's Wort gets an error, and after a busy hour searches stop working: every search kept a database connection and never gave it back."),
    ("The fix", "Fixed SQL with a <code>?</code>, the text sent as a parameter, wildcards escaped, and everything closed by try-with-resources."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">User text is data. It goes into a parameter, never into the SQL itself.</p>

<h2>What are we building?</h2>
<p><code>GET /medicines?name=para</code> finds medicines whose name contains the text, in any letter case, with strength, form, price and whether a prescription is needed.</p>

<h2>An everyday analogy</h2>
<p>A pharmacist's order form with a box for the medicine name. Whatever is written in the box is looked up as a name. Nobody reads it as an instruction to open the patient files.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Check the text</strong>: 2 to 50 characters.</li>
<li><strong>Borrow a connection</strong> from the pool.</li>
<li><strong>Run fixed SQL</strong> with the text as a parameter; read each row into a <code>Medicine</code>.</li>
<li><strong>Close everything</strong>: the connection goes back to the pool, whatever happened.</li>
</ol>

<details class="qa check"><summary>Check yourself: the box allows only 50 characters. Is that enough to stop injection?</summary><p>No. <code>x' OR 1=1 --</code> is 12 characters and returned every medicine from the old code. Only parameters stop injection; length limits are for usability.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No ORM.</strong> Plain JDBC, every step visible; later stations use helpers.</li>
<li><strong>No prescriptions endpoint.</strong> The table exists so the trap can show what leaked.</li>
<li><strong>No fuzzy search.</strong> \"Contains\", not \"sounds like\".</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Mediqo</strong> (a fictional clinic and pharmacy chain) built its medicine search by string concatenation. One query dumped every customer's prescriptions.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> <code>name=PARA</code>, <b>then</b> the three paracetamol products, ordered by name, strength and form.</li>
<li><b>Given</b> <code>name=john's</code>, <b>then</b> St. John's Wort, not an error.</li>
<li><b>Given</b> an injection attempt such as <code>x' OR 1=1 --</code>, <b>then</b> an empty list: it is just text no medicine is named.</li>
<li><b>Given</b> <code>%%</code> or <code>a_</code>, <b>then</b> they match those characters, not \"anything\".</li>
<li><b>Given</b> 50 searches in a row, <b>then</b> no connection is left in use.</li>
<li><b>Given</b> a missing, blank, 1-character or 51-character name, <b>then</b> <code>400</code>. No match is <code>200</code> with an empty list.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>No user text in SQL text: values only through <code>PreparedStatement</code> parameters.</li>
<li>Every JDBC resource is closed with try-with-resources.</li>
<li>Catalogue rules are database constraints too: positive price, known form, one row per product.</li>
<li>Money in integer paise; search text lower-cased with <code>Locale.ROOT</code>.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Use <code>DataSource</code>, <code>Connection</code>, <code>PreparedStatement</code> and <code>ResultSet</code> directly.</li>
<li>Explain and prevent SQL injection.</li>
<li>Close resources on every path, and see what a leak does to a pool.</li>
<li>Escape <code>LIKE</code> wildcards.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/medicines?name=para</code>", "Up to 20 medicines whose name contains the text, any letter case."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "Results, possibly an empty list"],
    ['<span class="pill warn">400</span>', "No name, or blank, shorter than 2 or longer than 50 characters"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. Special characters are URL-encoded in the address (<code>%27</code> is an apostrophe, <code>%25</code> a percent sign). JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-part-of-a-name", "Case 1: <code>para</code>", "<b>Why:</b> a contains-search in any case; ordered by name, strength, form."),
    ("02-an-apostrophe", "Case 2: <code>john's</code>", "<b>Why:</b> the apostrophe is a character in a parameter, not the end of a SQL string."),
    ("03-an-injection-attempt", "Case 3: <code>x' OR 1=1 --</code>", "<b>Why:</b> no medicine is called that. On the old code, this returned every medicine."),
    ("04-wildcards-are-just-characters", "Case 4: <code>%%</code>", "<b>Why:</b> escaped, so it means two percent signs, not \"everything\"."),
    ("05-no-match", "Case 5: <code>aspirin</code>", "<b>Why:</b> not in this catalogue: an empty list, not a 404."),
    ("06-too-short", "Case 6: <code>p</code>", "<b>Why:</b> one character would match most of the catalogue: <code>400</code>."),
    ("07-no-name", "Case 7: no name", "<b>Why:</b> <code>400</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["UNION payload; <code>x' OR 1=1 --</code>", "The old code leaks; the real one returns nothing", "<code>ConcatenatedSqlTrapTest</code>"],
    ["An apostrophe", "The old code fails; the real one finds the product", "<code>theOldSearchBreaksOnAnApostrophe</code>, <code>anApostropheIsJustACharacter</code>"],
    ["Connections after many searches", "The old code empties the pool; the real one returns every connection", "<code>theOldSearchLeaksAConnectionEveryTime</code>, <code>theRealSearchGivesEveryConnectionBack</code>"],
    ["<code>%%</code>, <code>a_</code>", "Literal characters", "<code>wildcardsAreLiteral</code>, <code>escapingKeepsWildcardsLiteral</code>"],
    ["Price 0, form POWDER, a duplicate product", "Refused by named constraints", "<code>namedConstraintsRefuseBadRowsFromAnyWriter</code>"],
    ["A prescription for a missing medicine", "Refused by the foreign key", "<code>aPrescriptionMustPointAtARealMedicine</code>"],
    ["Two inserts, the second bad, in one transaction", "Neither is kept after rollback", "<code>aFailedStatementInATransactionLeavesNothingAfterRollback</code>"],
    ["The same with auto-commit on", "The first is kept", "<code>withAutoCommitTheFirstRowStaysWhenTheSecondFails</code>"],
    ["Missing, blank, 1 or 51 characters", "<code>400</code>", "<code>aMissingTooShortOrTooLongNameIs400</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Building SQL by string concatenation (SQL injection) and leaking connections.</p>
<p>Every test here runs the old code against the real PostgreSQL. The UNION payload returns the three fictional patients' names, phones and doctors. A 12-character payload returns all 15 medicines. An apostrophe ends the SQL string early, and the driver refuses the query with \"Unterminated string literal\". On a pool of 3 connections, the old search keeps all 3, and the 4th search times out. The real search, given the same text, returns nothing to leak, and after 50 searches no connection is in use. While building, each fix was undone once. Removing the LIKE escaping turned 1 test red, not closing the connection 8, and putting the text into the SQL string 5.</p>
</div>
""" + code(read(T + "ConcatenatedSqlTrapTest.java"), "java") + code(read(T + "OldMedicineSearch.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "MedicineController.java", dwn("Validates the text and returns the results.",
        "Validation at the edge keeps nonsense away from the database; it is not what stops injection.",
        "Relying on a length limit or a blacklist of quotes to stop injection.")),
    (J + "MedicineSearch.java", dwn("The search in plain JDBC.",
        "Fixed SQL, one parameter for the text, one for the limit; try-with-resources closes the connection, statement and result set.",
        "The trap: text glued into SQL, and connections never returned.",
        "<ul><li><code>prepareStatement(SQL)</code> sends the SQL once; <code>setString</code> sends the value separately.</li><li><code>ESCAPE '\\'</code> plus <code>escapeLike</code> make <code>%</code> and <code>_</code> literal.</li><li>Closing a pooled connection returns it to the pool; it does not close the socket.</li></ul>")),
    (J + "Medicine.java", "<p>One catalogue row.</p>"),
    (M + "V1__medicines_and_prescriptions.sql", dwn("The two tables and their named constraints.",
        "Rules the database enforces for every writer, not just this app.",
        "A script or another service inserts a free medicine, or a duplicate in different letter case.")),
    (M + "V2__demo_catalogue.sql", "<p>15 demo medicines and 3 fictional prescriptions. <code>''</code> is an apostrophe inside a SQL string.</p>"),
    ("src/main/resources/application.yaml", "<p>The database the app connects to (compose.yaml starts it).</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app, with a healthcheck.</p>"),
    (J + "PharmacyApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/036-medicine-search-with-plain-jdbc/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/mediqo/pharmacy/
│   ├── MedicineController.java   ├── MedicineSearch.java
│   ├── Medicine.java             └── PharmacyApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__medicines_and_prescriptions.sql, V2__demo_catalogue.sql
├── src/test/java/com/mediqo/pharmacy/   (see Tests)
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
./mvnw spring-boot:run      # the API on http://localhost:8080; Flyway creates and fills the tables
./mvnw test                 # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Search, then look at the same rows in the database:</p>
""" + code("""curl "http://localhost:8080/medicines?name=cillin"
docker compose exec postgres psql -U mediqo -d mediqo -c "SELECT name, strength, form FROM medicines WHERE lower(name) LIKE '%cillin%'\"""", "bash") + """
<p>Then try to insert a free medicine directly, and read the constraint's name in the error:</p>
""" + code("""docker compose exec postgres psql -U mediqo -d mediqo -c "INSERT INTO medicines (name, strength, form, price_paise, prescription_required) VALUES ('Free pill', '1 mg', 'TABLET', 0, false)\"""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>Could not find a valid Docker environment</code>", "Docker is not running. Testcontainers needs it.", "Start Docker, then run the tests again."],
    ["<code>Connection to localhost:5432 refused</code>", "PostgreSQL is not up yet.", "<code>docker compose up -d</code>, wait a few seconds, start the app again."],
    ["<code>Connection is not available, request timed out after 30000ms</code>", "Connections are not returned to the pool: a leak.", "Find the <code>getConnection()</code> outside a try-with-resources."],
    ["<code>port 5432 is already allocated</code>", "A local PostgreSQL uses the port.", "Stop it, or map <code>\"5433:5432\"</code> in compose.yaml and change the URL in application.yaml."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found (empty)", f"<code>MedicineContractTest</code> ({cnt('MedicineContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>ConcatenatedSqlTrapTest</code> ({cnt('ConcatenatedSqlTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>MedicineDatabaseTest</code> ({cnt('MedicineDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "ConcatenatedSqlTrapTest.java", "<p>Written first: the old search's leak of prescriptions, its error on an apostrophe, and its connection leak, on a pool of its own.</p>"),
    (T + "MedicineContractTest.java", "<p>Searches through HTTP, wildcards, the injection attempt, and every refusal.</p>"),
    (T + "MedicineDatabaseTest.java", "<p>Plain JDBC against the schema: named constraints, the foreign key, rollback and auto-commit.</p>"),
    (T + "OldMedicineSearch.java", "<p>The old code, kept only in tests.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the app with a real PostgreSQL.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/mediqo/pharmacy/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=FormFilterChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Filter by form", "Beginner-friendly", 25,
    "Add an optional <code>?form=</code> (any case). The SQL gains <code>AND form = ?</code> only when a form is given; an unknown form is a <code>400</code> before the database is asked.",
    "both tests in <code>FormFilterChallengeTest</code> pass.",
    ["Building SQL from fixed fragments you wrote is safe; the values still go in as parameters.",
     "Count the parameters as you add them: the limit moves from position 2 to 3."],
    "challenge/FormFilterChallengeTest.java", ["challenge/solution/MedicineSearch.java", "challenge/solution/MedicineController.java"]) + challenge(2, "How many matches?", "Go deeper", 30,
    "Add <code>?size=</code> (1 to 20) and a <code>total</code> of every match, from the same single query.",
    "both tests in <code>TotalAndSizeChallengeTest</code> pass.",
    ["<code>count(*) OVER ()</code> counts the rows before <code>LIMIT</code> and repeats the number on every row.",
     "With no rows, there is no row to read the total from: it is 0."],
    "challenge/TotalAndSizeChallengeTest.java", ["challenge/solution/MedicineSearch.java", "challenge/solution/MedicineController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>A search for 2 lakh products</h2>
<p><code>LIKE '%text%'</code> cannot use a normal index, so it reads every row. With 2,00,000 products and typos (\"paracitamol\"), compare a trigram index (<code>pg_trgm</code>), PostgreSQL full-text search, and a search engine. Which handles typos, which handles brand and generic names, and what each costs to keep in sync?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transactions"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap tests against a real PostgreSQL: leak, apostrophe, pool exhaustion.</li>
<li>Write the schema with named constraints, and test them with plain inserts.</li>
<li>Write the search: fixed SQL, parameters, escaped wildcards, try-with-resources.</li>
<li>Check that after many searches the pool has no connection in use.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["<code>PreparedStatement</code> with parameters", "A few more lines than concatenation.", '<span class="pill ok">Chosen</span>'],
    ["Concatenation with quote escaping by hand", "One missed case (encodings, backslashes) and it is injectable again.", '<span class="pill bad">Never</span>'],
    ["Blocking characters such as <code>'</code> and <code>--</code>", "Breaks St. John's Wort; attackers find other ways.", '<span class="pill bad">Not a defence</span>'],
    ["<code>JdbcClient</code> or <code>JdbcTemplate</code>", "Same safety, less code: they prepare and close for you.", '<span class="pill warn">From the next stations</span>'],
    ["A database user that can only read <code>medicines</code>", "One more role to manage; limits the damage of any mistake.", '<span class="pill warn">Defence in depth</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Key and constraints", "Why"], [
    ["<code>medicines</code>", "Identity PK. <code>medicines_price_positive</code>, <code>medicines_form_known</code>, unique index <code>medicines_unique_product</code> on <code>(lower(name), strength, form)</code>.", "The catalogue's rules hold for every writer; \"Paracetamol\" and \"PARACETAMOL\" 500 mg tablets cannot both exist."],
    ["<code>prescriptions</code>", "Identity PK, <code>prescriptions_medicine_fk</code> to <code>medicines</code>.", "Personal health data: exactly what injection reached. No search reads it."]]) + """
<p><strong>Transactions:</strong> the search is one read with auto-commit on. <code>MedicineDatabaseTest</code> shows the difference a transaction makes: with <code>setAutoCommit(false)</code> and a rollback, a failed second insert takes the first with it; with auto-commit, the first stays. The next station builds on this.</p>
<p><strong>Index:</strong> <code>lower(name) LIKE '%…%'</code> cannot use a B-tree index, so it scans the table. At 15 rows that is nothing; challenge 3 is about when it is not.</p>
""" + code(read(M + "V1__medicines_and_prescriptions.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Least privilege</dt><dd>The app's database user should read and write only what it needs. A search that cannot read <code>prescriptions</code> cannot leak it, even with a bug.</dd>
<dt>Leak detection</dt><dd>HikariCP's <code>leakDetectionThreshold</code> logs where a connection was borrowed when it is held too long; watch active connections next to request rate.</dd>
<dt>Health data</dt><dd>Prescriptions are sensitive personal data under India's Digital Personal Data Protection Act, 2023; a leak is a reportable incident, not only a bug.</dd>
<dt>Logging</dt><dd>Log that a search happened, not the patient behind it; search text can contain names.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is SQL injection, and how do you prevent it?", "User input that becomes part of the SQL text and changes the query. Prevent it with parameters (PreparedStatement or a library that uses them); never build SQL from input. Validation and least privilege reduce the damage but do not prevent it."),
    ("What does closing a pooled connection do?", "It returns the connection to the pool for the next request. Not closing it keeps it borrowed until the pool runs out and requests time out."),
    ("Why try-with-resources?", "It closes every resource declared in it, in reverse order, on every path, including exceptions, which hand-written finally blocks often get wrong."),
    ("Can a PreparedStatement parameter be a table or column name?", "No. Parameters are values only. Identifiers must come from a fixed list in your code (an allowlist)."),
    ("Why escape % and _ in a LIKE parameter?", "They are wildcards inside the pattern. Without escaping, a user's '%' matches everything; it is not injection, but it is wrong results and extra load."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the trap and read the leaked rows."],
    ["Security", "Parameters for every value.", "An allowlist for anything that must be part of the SQL text."],
    ["Resources", "try-with-resources everywhere.", "You can watch a pool's active connections."],
    ["Database", "Named constraints with tests.", "Auto-commit vs a transaction, from the test."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any JDBC code:</p>
<ul class="rules">
<li>Is any <code>+</code> joining input into SQL text?</li>
<li>Is every <code>getConnection()</code>, statement and result set in a try-with-resources?</li>
<li>Are <code>LIKE</code> wildcards in user text escaped?</li>
<li>Can this database user read tables this feature never needs?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
