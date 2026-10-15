"""Station 038 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 38,
    "stack": "Spring Boot 4.1.1 · Java 25 · Flyway versioned migrations · PostgreSQL 17 constraints: PK, FK, UNIQUE, CHECK, EXCLUDE · JdbcClient · Testcontainers",
    "simulation": "Members, plans and prices are demo data, not FitNest's. A membership is a record; no payment is taken.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/fitnest/members/"
T = "src/test/java/com/fitnest/members/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Migration", "A numbered SQL file that changes the database from one version to the next.", "Numbered amendments to a rule book; old ones are never rewritten.", "<code>V2__plans_and_constraints.sql</code>"),
    ("Constraint", "A rule the database checks on every write, from any program.", "A turnstile: it does not care who is pushing.", "<code>members_phone_unique</code>"),
    ("Foreign key", "A column that must point at an existing row elsewhere.", "A locker number that must exist.", "<code>memberships_member_fk</code>"),
    ("CHECK", "A condition every row must meet.", "\"End date on or after start date\" printed on the form.", "<code>memberships_dates_order</code>"),
    ("EXCLUDE", "No two rows may conflict, for a meaning of \"conflict\" you choose, such as overlapping dates.", "One locker, one member per day.", "<code>memberships_no_overlap</code>"),
    ("Normalisation", "Each fact stored once, in the table it belongs to.", "A price list on the wall, not a price written by hand on every receipt.", "the <code>plans</code> table"),
]
STORY = [
    ("Rules in Java only", "The app refuses a duplicate phone and a membership that ends before it starts. The database itself only knows primary keys."),
    ("Another writer", "The front desk's spreadsheet sync writes straight to the database. Asha is now two members, \"98765 43210\" and \"+91 9876543210\", and one membership ends in October but starts in November."),
    ("The fix", "A new migration moves the rules into the database, named. Now every writer meets them, and the app turns a refusal into a clear 409."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A rule that only one program knows is a suggestion. A constraint is a rule.</p>

<h2>What are we building?</h2>
<p><code>POST /members</code> registers a member by phone; <code>POST /members/{id}/memberships</code> sells a monthly, quarterly or annual membership. The database refuses a second member with the same phone, a membership that ends before it starts, and two memberships on the same day.</p>

<h2>An everyday analogy</h2>
<p>A gym's turnstile. The receptionist checks your card, but the turnstile checks it again, and it also stops anyone who climbs in through the side door.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>At startup</strong>, Flyway applies any migration the database has not seen yet, in version order.</li>
<li><strong>Java checks the shape</strong> of a request and writes the phone in one form.</li>
<li><strong>The database checks the rules</strong> on the insert.</li>
<li><strong>A refusal's constraint name</strong> decides the answer: duplicate phone or overlap, <code>409</code>.</li>
</ol>

<details class="qa check"><summary>Check yourself: why not ask \"is this phone taken?\" before inserting?</summary><p>Two requests can both ask at the same moment, both hear \"no\", and both insert. The unique constraint lets only one of them win, every time.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No payments.</strong> A membership is a record.</li>
<li><strong>No member login.</strong> The desk registers members.</li>
<li><strong>No zero-downtime migration.</strong> Adding constraints to a large live table is challenge 3.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>FitNest</strong> (a fictional gym chain) found two members sharing one phone number and a membership that ends before it starts. The schema allowed both.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> <code>+91 98765-43210</code>, <b>then</b> the member is stored with <code>9876543210</code>; <code>098765 43210</code> for another member is <code>409</code>.</li>
<li><b>Given</b> a quarterly membership from 15 November 2026, <b>then</b> it ends on 14 February 2027 and costs ₹3,999.00.</li>
<li><b>Given</b> a membership covering any of those days, <b>then</b> <code>409</code>; one starting on 15 February, <code>201</code>.</li>
<li><b>Given</b> any writer at all, <b>then</b> a duplicate phone, a phone in another form, inverted dates, an unknown member or plan, or a zero price are refused by named constraints.</li>
<li><b>Given</b> an old database with bad rows, <b>then</b> the V2 migration fails, names the rule, and changes nothing until the rows are fixed.</li>
<li><b>Given</b> an unknown member, <code>404</code>; an unknown plan, <code>422</code>; a bad phone or date, <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Schema changes are new versioned migrations; released ones are never edited.</li>
<li>Every business rule in Java is also a named database constraint, with a test that bypasses Java.</li>
<li>Phones are stored in one form, so <code>UNIQUE</code> sees duplicates.</li>
<li>Money in integer paise.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Evolve a schema with Flyway versioned migrations.</li>
<li>Use primary, foreign, unique, check and exclusion constraints.</li>
<li>Normalise a repeated fact into its own table, and know when a copy is a fact of its own.</li>
<li>Write SQL with <code>JdbcClient</code>, and map a constraint violation to <code>409</code>.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Body"], [
    ["<code>POST</code>", "<code>/members</code>", "<code>{\"name\", \"phone\"}</code>"],
    ["<code>POST</code>", "<code>/members/{id}/memberships</code>", "<code>{\"planCode\", \"startsOn\"}</code>: MONTHLY, QUARTERLY or ANNUAL, any case."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "A member or membership was created"],
    ['<span class="pill warn">400</span>', "A bad phone, a blank name or plan, a date that does not exist"],
    ['<span class="pill warn">404</span>', "No such member"],
    ['<span class="pill warn">409</span>', "The phone is already registered, or the membership overlaps another"],
    ['<span class="pill warn">422</span>', "A plan FitNest does not sell"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against one fresh database. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-a-new-member", "Case 1: a phone with +91 and a dash", "<b>Why:</b> stored as 10 digits, the one form the database accepts."),
    ("02-the-same-phone-written-differently", "Case 2: the same number with a leading 0", "<b>Why:</b> the same 10 digits: <code>members_phone_unique</code> refuses it."),
    ("03-not-a-mobile-number", "Case 3: 12345", "<b>Why:</b> <code>400</code>, before the database."),
    ("04-a-quarterly-membership", "Case 4: quarterly from 15 November", "<b>Why:</b> ends the day before 15 February; the plan's price is stored on the membership."),
    ("05-an-overlapping-membership", "Case 5: monthly from 31 January", "<b>Why:</b> covers days already covered: <code>memberships_no_overlap</code>."),
    ("06-the-next-one-back-to-back", "Case 6: monthly from 15 February", "<b>Why:</b> starts the day after the last one ends."),
    ("07-a-plan-we-do-not-sell", "Case 7: WEEKLY", "<b>Why:</b> <code>422</code>."),
    ("08-no-such-member", "Case 8: member 99", "<b>Why:</b> <code>404</code>."),
]) + """
<h2>The database behind them</h2>
<p class="muted">Queried with psql after the captures. Flyway's record of what ran (<code>docs/captures/flyway-history.txt</code>):</p>
""" + code(read("docs/captures/flyway-history.txt").rstrip(), "text") + """
<p class="muted">Every constraint on the three tables (<code>docs/captures/constraints.txt</code>):</p>
""" + code(read("docs/captures/constraints.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Another writer, version 1 schema", "Duplicate phone and inverted dates stored", "<code>JavaOnlyRulesTrapTest</code>"],
    ["The same writer, version 2 schema", "Refused by name", "<code>JavaOnlyRulesTrapTest</code>"],
    ["Phone format, unknown member or plan, zero price", "Refused by named constraints", "<code>everyRuleIsANamedConstraint</code>"],
    ["Overlap; back-to-back; another member's same days", "Refused; allowed; allowed", "<code>overlappingMembershipsAreRefusedButBackToBackOnesAreFine</code>"],
    ["A member and a bad membership in one transaction", "Neither is kept", "<code>aFailureInsideATransactionTakesTheNewMemberWithIt</code>"],
    ["V2 run on a database with bad rows", "Fails by name, rolled back, succeeds after the fix", "<code>addingConstraintsToBadDataFailsTheMigrationUntilTheDataIsFixed</code>"],
    ["Through HTTP: duplicate phone, overlap, unknown member or plan, bad input", "<code>409</code>, <code>409</code>, <code>404</code>, <code>422</code>, <code>400</code>", "<code>MembershipContractTest</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Enforcing rules only in Java; another writer inserts invalid rows.</p>
<p>The test migrates a separate schema to version 1, as it shipped. Plain SQL, standing in for the spreadsheet sync, stores Asha twice under one phone, and a membership that ends a month before it starts. The same statements against the version 2 schema are refused by <code>members_phone_unique</code>, <code>members_phone_digits</code> and <code>memberships_dates_order</code>. While building, each fix was undone once. Dropping the unique phone turned 3 tests red, and dropping the overlap rule 2. Not normalising phones in the migration turned 1 red, not mapping a duplicate phone to 409 1, and not mapping an overlap 1.</p>
</div>
""" + code(read(T + "JavaOnlyRulesTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "MemberController.java", dwn("Validates requests, normalises the phone, and turns a named constraint violation into a <code>409</code>.",
        "Java gives the friendly message; the database gives the guarantee.",
        "Asking \"is it taken?\" first: two requests can both hear \"no\".")),
    (J + "MemberStore.java", dwn("SQL with <code>JdbcClient</code>.",
        "Named parameters, <code>RETURNING</code> for the new row, and records mapped by column name.",
        "Hand-written <code>ResultSet</code> loops for every query.")),
    (J + "Phones.java", dwn("Writes a phone in one form: 10 digits.",
        "<code>UNIQUE</code> compares exact text, so one number written two ways would slip past it.",
        "\"98765 43210\" and \"+91 9876543210\" stored as two members.")),
    (M + "V1__members_and_memberships.sql", dwn("The schema as version 1 shipped.",
        "Kept unchanged: databases already at version 1 must replay history exactly.",
        "Editing it breaks Flyway's checksum on every database that already ran it.")),
    (M + "V2__plans_and_constraints.sql", dwn("Moves every rule into the database, and plans into their own table.",
        "One transaction: if old rows break a new rule, nothing changes and the error names the rule.",
        "Rules that only the Java code knows.",
        "<ul><li>Phones are rewritten into one form before <code>UNIQUE</code> is added.</li><li>The <code>EXCLUDE</code> constraint is its own statement, after the dates check; see the Design tab.</li></ul>")),
    ("src/main/resources/application.yaml", "<p>The database and strict JSON.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "MembersApplication.java", "<p>Entry point. Flyway runs the migrations before the app takes requests.</p>"),
]
tree = """stations/038-gym-memberships-with-migrations-and-constraints/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/fitnest/members/
│   ├── MemberController.java   ├── MemberStore.java   ├── Phones.java   └── MembersApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__members_and_memberships.sql, V2__plans_and_constraints.sql
├── src/test/java/com/fitnest/members/   (see Tests)
├── challenge/                Practice tests; solutions (including new migrations) ship separately
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
./mvnw spring-boot:run      # the API on http://localhost:8080; Flyway applies V1 and V2 first
./mvnw test                 # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Be the other writer. With the app running, insert a membership that ends before it starts, straight into the database:</p>
""" + code("""docker compose exec postgres psql -U fitnest -d fitnest -c "INSERT INTO members (name, phone) VALUES ('Desk test', '9000000001')"
docker compose exec postgres psql -U fitnest -d fitnest -c "INSERT INTO memberships (member_id, plan_code, starts_on, ends_on, price_paise) SELECT id, 'MONTHLY', DATE '2026-11-30', DATE '2026-11-01', 149900 FROM members WHERE phone = '9000000001'\"""", "bash") + """
<p>Read the constraint name in the error. Then look at what Flyway recorded: <code>SELECT * FROM flyway_schema_history</code>.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>Validate failed: Migration checksum mismatch for migration version 1</code>", "A released migration was edited.", "Put it back as it was, and make the change in a new version."],
    ["<code>could not create unique index \"members_phone_unique\"</code> while migrating", "Existing rows break the new rule.", "Find them (<code>SELECT phone, count(*) FROM members GROUP BY phone HAVING count(*) &gt; 1</code>), fix them with the business, then start the app again."],
    ["<code>data type bigint has no default operator class for access method \"gist\"</code>", "The <code>btree_gist</code> extension is missing.", "V2 creates it; on a managed database you may need an administrator to allow it."],
    ["<code>Could not find a valid Docker environment</code>", "Docker is not running.", "Start Docker, then run the tests again."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the migrations behind it.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>MembershipContractTest</code> ({cnt('MembershipContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>JavaOnlyRulesTrapTest</code> ({cnt('JavaOnlyRulesTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>MembershipDatabaseTest</code> ({cnt('MembershipDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "JavaOnlyRulesTrapTest.java", "<p>Written first: version 1 in its own schema lets another writer store what Java refuses.</p>"),
    (T + "MembershipDatabaseTest.java", "<p>Every named constraint, overlap, a rollback, and the V2 migration meeting bad data.</p>"),
    (T + "MembershipContractTest.java", "<p>Members and memberships through HTTP, and every refusal.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: empty tables before each test.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/fitnest/members/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=MemberEmailChallengeTest</code> (Docker must be running).</li>
<li>Add a new migration file and change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in (two Java files and two new migrations), all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "An email, unique in any case", "Beginner-friendly", 25,
    "Members may give an email. Add it in <code>V3</code>, never by editing V1 or V2: optional, unique whatever the letter case, enforced by the database; a second member with the same email is <code>409</code>.",
    "both tests in <code>MemberEmailChallengeTest</code> pass.",
    ["A unique index on <code>lower(email)</code> treats ASHA@ and asha@ as the same.",
     "NULLs are never equal to each other, so many members can have no email."],
    "challenge/MemberEmailChallengeTest.java", ["challenge/solution/V3__member_email.sql", "challenge/solution/MemberStore.java", "challenge/solution/MemberController.java"]) + challenge(2, "Freeze a membership", "Go deeper", 35,
    "<code>POST /memberships/{id}/freeze</code> with <code>{\"days\": n}</code> moves the end n days later, up to 30 frozen days in all (a Java check and a constraint in <code>V4</code>). A freeze that runs into the next membership is refused by the overlap rule you already have.",
    "both tests in <code>FreezeChallengeTest</code> pass.",
    ["One <code>UPDATE … RETURNING</code> moves the end and adds the days.",
     "An <code>EXCLUDE</code> constraint is checked on updates too: nothing new is needed for the overlap."],
    "challenge/FreezeChallengeTest.java", ["challenge/solution/V4__membership_freeze.sql", "challenge/solution/MemberStore.java", "challenge/solution/MemberController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>A constraint on a table with a crore rows</h2>
<p>Adding <code>UNIQUE</code> or <code>CHECK</code> to a huge live table scans it while holding a lock. Find out what <code>CHECK … NOT VALID</code> followed by <code>VALIDATE CONSTRAINT</code>, and <code>CREATE UNIQUE INDEX CONCURRENTLY</code>, change. Then plan V2 as several migrations that a busy gym chain could run without downtime, and say what happens to bad rows found halfway.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, migrations"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test against version 1, in a schema of its own.</li>
<li>Write V2: the plans table, phone clean-up, then each rule as a named constraint.</li>
<li>Test each constraint with plain SQL, and V2 against a database with bad rows.</li>
<li>Write the API with <code>JdbcClient</code>, mapping constraint names to <code>409</code>.</li>
</ol>
<h2>Normalisation, briefly</h2>
""" + table(["Form", "Rule", "Here"], [
    ["1NF", "One value per column, no repeating groups.", "One phone per member row, not a list of phones in one column."],
    ["2NF", "Every column depends on the whole key.", "Tables have single-column keys here, so this holds."],
    ["3NF", "No column depends on another non-key column.", "In V1, a membership's plan name decided its length and list price. V2 moves those to <code>plans</code>."]]) + """
<p>The membership keeps <code>price_paise</code> on purpose. It is what that member paid that day, a fact about the sale. If the plan's price changes next year, past memberships must not change with it.</p>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Named constraints + friendly Java checks", "Each rule written twice, in SQL and in Java.", '<span class="pill ok">Chosen</span>'],
    ["Java checks only", "Any other writer ignores them.", '<span class="pill bad">The trap</span>'],
    ["Check first, then insert", "Two requests race past the check.", '<span class="pill bad">A race</span>'],
    ["Triggers for the overlap rule", "Hidden logic, easy to get wrong under concurrency.", '<span class="pill warn">When no constraint fits</span>'],
    ["Editing V1 instead of adding V2", "Every database already at V1 fails its checksum.", '<span class="pill bad">Never</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Key and constraints", "Why"], [
    ["<code>members</code>", "Identity PK. <code>members_phone_digits</code>, <code>members_phone_unique</code>.", "One member per phone, in one stored form."],
    ["<code>plans</code>", "PK <code>code</code>. Months 1 to 24, price &gt; 0.", "Each plan's facts stored once."],
    ["<code>memberships</code>", "Identity PK. <code>memberships_member_fk</code>, <code>memberships_plan_fk</code>, <code>memberships_dates_order</code>, <code>memberships_price_positive</code>, <code>memberships_no_overlap</code> (EXCLUDE with <code>btree_gist</code>).", "No orphan, no unknown plan, no impossible dates, no two memberships on one day for one member."]]) + """
<p><strong>Order inside V2 matters.</strong> Phones are rewritten into one form before <code>UNIQUE</code> is added. The <code>EXCLUDE</code> constraint is a separate <code>ALTER</code>, after the dates check. This was found while building: in one <code>ALTER</code>, building its index runs <code>daterange()</code> on a row that ends before it starts, and fails with \"range lower bound must be less than or equal to range upper bound\", which names no rule. As a separate statement, such a row is refused first by <code>memberships_dates_order</code>, by name.</p>
""" + code(read(M + "V2__plans_and_constraints.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Migrations at startup</dt><dd>With several app instances starting together, Flyway's lock lets one migrate and the others wait. Large migrations are better run as a separate step before the deploy.</dd>
<dt>Bad data first</dt><dd>Before adding a rule to a live table, query for rows that break it, and decide with the business what they mean. A migration that deletes \"duplicates\" can delete a real customer.</dd>
<dt>Locks</dt><dd>Adding constraints locks the table while existing rows are checked; at scale, see challenge 3.</dd>
<dt>Extensions</dt><dd><code>btree_gist</code> ships with PostgreSQL, but managed databases may need it allowed by an administrator.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why put business rules in database constraints if Java already checks them?", "Java protects one program. Constraints protect the data from every writer (scripts, other services, manual fixes, future bugs), and they are race-free."),
    ("Why must you never edit a released Flyway migration?", "Flyway stores each migration's checksum. Databases that already ran it would fail validation, and databases that run it fresh would differ from those that did not. Change things in a new version."),
    ("What does an EXCLUDE constraint do?", "It forbids two rows that conflict under the operators you give, for example the same member (=) with overlapping date ranges (&&). UNIQUE is the special case where the operator is equality."),
    ("How do you turn a constraint violation into a 409?", "Catch the data-integrity exception, check which named constraint failed, and map known business rules to 409 with a clear message; anything unexpected stays an error."),
    ("What is third normal form, simply?", "Every non-key column describes the key, the whole key, and nothing but the key. A plan's price belongs with the plan, not repeated on each membership, unless the copy is a fact of its own, such as what was paid."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You broke a constraint by hand with psql and read the name."],
    ["Migrations", "New versions, never edits.", "You can run V2 against bad data and fix it safely."],
    ["Constraints", "PK, FK, UNIQUE, CHECK.", "EXCLUDE, and why order inside a migration matters."],
    ["Design", "Plans in their own table.", "Why the paid price stays on the membership."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any schema change:</p>
<ul class="rules">
<li>Is it a new migration, with every released one untouched?</li>
<li>Does each rule in the Java code have a named constraint, and a test that bypasses Java?</li>
<li>What happens to existing rows that break the new rule?</li>
<li>Are values stored in one form, so <code>UNIQUE</code> means what it should?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
