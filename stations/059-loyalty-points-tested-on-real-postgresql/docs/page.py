"""Station 059 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 59,
    "stack": "Spring Boot 4.1.1 · Java 25 · @SpringBootTest · Testcontainers with @ServiceConnection and disabledWithoutDocker · PostgreSQL 17 upsert (ON CONFLICT ... RETURNING) · H2 (trap test only) · JdbcClient · Flyway",
    "simulation": "Customers, orders and points are demo data, not Basketo's. Points are rows in a ledger; no shop or payment system calls in. The earning rate is a demo rule.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests; without Docker the tests are skipped, not passed). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/basketo/loyalty/"
T = "src/test/java/com/basketo/loyalty/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("H2", "A small database that runs inside the test, in memory.", "A practice pitch, not the stadium.", "The old tests"),
    ("Compatibility mode", "H2 imitating another database: some of its syntax, not all.", "An actor playing a doctor.", "<code>MODE=PostgreSQL</code>"),
    ("Upsert", "Insert a row, or update it if it already exists, in one statement.", "Open an account, or add to it if it exists.", "<code>ON CONFLICT ... DO UPDATE</code>"),
    ("Testcontainers", "Real databases in Docker, started by the tests.", "Playing in the real stadium for practice.", "<code>PostgresTestConfig</code>"),
    ("@ServiceConnection", "Tells Spring to connect to that container, with no URL in a config file.", "A team bus that knows where the stadium is.", "<code>@ServiceConnection</code>"),
    ("Test data isolation", "Each test makes the data it needs, so tests never depend on each other.", "Each player bringing their own ball.", "<code>newCustomer()</code>"),
]
STORY = [
    ("Green on H2", "Basketo's loyalty tests ran on H2, in PostgreSQL mode. The upsert, written in H2's MERGE ... KEY syntax, passed every test."),
    ("Red in production", "The first customer to earn points after the release got an error: PostgreSQL does not know that syntax. Nobody's points were saved until a hotfix."),
    ("The fix", "Write the upsert PostgreSQL understands, and run every test against a real PostgreSQL 17 in Docker, the same version as production."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A test proves something only about the database it ran on. Test on the one you ship to.</p>

<h2>What are we building?</h2>
<p>Customers earn points on orders (<code>POST /loyalty/{id}/earn</code>) and spend them (<code>POST /loyalty/{id}/redeem</code>). Every change is a ledger entry plus an atomic change of the balance, and every test runs on real PostgreSQL.</p>

<h2>An everyday analogy</h2>
<p>A driving test in a simulator that lets you drive on the left and the right. You pass; then the real road only allows one. H2 in PostgreSQL mode is the simulator: friendly, fast, and not the road.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>The tests start</strong> PostgreSQL 17 in Docker; Spring connects to it (<code>@ServiceConnection</code>).</li>
<li><strong>Flyway</strong> creates the real schema, constraints and all.</li>
<li><strong>Each test</strong> makes its own customers, so it never depends on another test's data.</li>
<li><strong>Without Docker</strong>, the tests are skipped, and say so: never passed, never failed.</li>
</ol>

<details class="qa check"><summary>Check yourself: why not keep H2 for speed and add a few PostgreSQL tests?</summary><p>Because every query is a chance for a dialect difference, and you do not know in advance which ones. The shared PostgreSQL container starts once per run; after that, tests are about as fast.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No order system.</strong> Earn is called directly.</li>
<li><strong>No expiry or tiers.</strong> Points stay.</li>
<li><strong>No history endpoint.</strong> That is challenge 1.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Basketo</strong> (a fictional grocery chain) shipped loyalty code whose only tests ran on H2. PostgreSQL rejected its upsert in production.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a customer with no points earns on a ₹1,499 order, <b>then</b> <code>201</code>, 14 points, and the balance row is created.</li>
<li><b>Given</b> another order, <b>then</b> the points are added to the same row; an order under ₹100 earns 0.</li>
<li><b>Given</b> the same order again, in any case, <b>then</b> <code>409</code> and the balance is unchanged.</li>
<li><b>Given</b> 20 earns at once for a new customer, <b>then</b> all 20 are counted.</li>
<li><b>Given</b> a redemption above the balance, <b>then</b> <code>422</code>; an unknown customer, <code>404</code>; a malformed body, <code>400</code>.</li>
<li><b>Given</b> Docker is not running, <b>then</b> the tests are reported as skipped.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Every test runs on the database version production runs.</li>
<li>No test depends on data another test created.</li>
<li>Balances never go below zero; an order earns once; both enforced by the database.</li>
<li>The ledger entry and the balance change commit together.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Write <code>@SpringBootTest</code> tests against a real database with Testcontainers and <code>@ServiceConnection</code>.</li>
<li>Keep tests independent of each other's data.</li>
<li>Write PostgreSQL's upsert and know why it is safe under concurrency.</li>
<li>Choose a strategy for machines without Docker that never lies.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/loyalty/{customerId}/earn</code>", "Points for an order: <code>orderRef</code> and <code>amountPaise</code>; 1 point per full ₹100 (demo rule)."],
    ["<code>POST</code>", "<code>/loyalty/{customerId}/redeem</code>", "Spend <code>points</code> (1 to 100,000)."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Points earned"],
    ['<span class="pill ok">200</span>', "Points redeemed"],
    ['<span class="pill warn">400</span>', "Malformed body"],
    ['<span class="pill warn">404</span>', "No such customer"],
    ['<span class="pill warn">409</span>', "This order already earned points"],
    ['<span class="pill warn">422</span>', "Not enough points"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against one fresh database (Asha has 120 points; Rohan none). JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-asha-earns-on-a-1499-order", "Case 1: Asha, a ₹1,499 order", "<b>Why:</b> 14 points added: 134."),
    ("02-rohans-first-points", "Case 2: Rohan's first points", "<b>Why:</b> no balance row yet: the upsert creates it."),
    ("03-the-same-order-again", "Case 3: the same order, lower case", "<b>Why:</b> one order earns once: <code>409</code>."),
    ("04-asha-redeems-100", "Case 4: Asha spends 100", "<b>Why:</b> 34 left."),
    ("05-asha-redeems-500", "Case 5: Asha spends 500", "<b>Why:</b> not enough: <code>422</code>."),
    ("06-customer-99", "Case 6: customer 99", "<b>Why:</b> <code>404</code>."),
    ("07-an-amount-of-zero", "Case 7: an amount of 0", "<b>Why:</b> <code>400</code>."),
]) + """
<h2>The old upsert, on this PostgreSQL</h2>
<p class="muted">Sent with psql to the database the captures ran against (<code>docs/captures/old-upsert.txt</code>):</p>
""" + code(read("docs/captures/old-upsert.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["First earn, second earn, under ₹100", "Row created, then added to; 0 points", "<code>theFirstEarnCreatesTheBalanceAndTheNextAddsToIt</code>"],
    ["The same order twice, in two cases", "<code>409</code>; balance unchanged", "<code>anOrderEarnsOnceInAnyCase</code>"],
    ["Redeem within, above, with no balance row", "<code>200</code>; <code>422</code>; <code>422</code>", "<code>redeemingTakesPointsAndNeverMoreThanThere</code>"],
    ["Malformed bodies", "<code>400</code>", "<code>malformedRequestsAre400</code>"],
    ["Unknown customer", "<code>404</code>", "<code>unknownCustomersAre404</code>"],
    ["Bad rows written directly", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"],
    ["An earn whose caller fails after it", "Entry and balance rolled back", "<code>anEarnThatFailsAfterItsWritesLeavesNeither</code>"],
    ["20 earns at once, no row yet", "All counted", "<code>twentyEarnsAtOnceForANewCustomerAddUp</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Testing on H2 and shipping SQL that PostgreSQL rejects.</p>
<p>The trap test runs the old upsert, <code>MERGE INTO point_balances (customer_id, points) KEY (customer_id) VALUES (?, ?)</code>, in two places. On in-memory H2 in PostgreSQL mode it works: the old suite was green. On PostgreSQL 17 it is a syntax error at the column list, because PostgreSQL's MERGE is the SQL-standard one (<code>MERGE INTO t USING …</code>). The third test turns it around: H2 cannot even parse the upsert PostgreSQL needs, so code that is right for production could never have been tested on H2.</p>
<p>While building, each part was undone once. Putting the old MERGE back turned 5 tests red; an upsert that replaces the balance instead of adding to it, 2 (including the 20-at-once test); a redemption without the <code>points &gt;= ?</code> condition, 1.</p>
</div>
""" + code(read(T + "H2VersusPostgresTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "LoyaltyController.java", dwn("Validates earn and redeem; normalises order references.", "HTTP only.", "Earn called by anyone (in a shop, only the order system).")),
    (J + "LoyaltyLedger.java", dwn("Ledger entry plus balance change, in one transaction.",
        "PostgreSQL's upsert: atomic, even for a customer's first points arriving twice at once.", "Lost or doubled points.",
        "<ul><li><code>ON CONFLICT (customer_id) DO UPDATE SET points = point_balances.points + EXCLUDED.points</code> adds, it does not replace.</li><li><code>RETURNING points</code> gives the new balance without a second query.</li><li>Redeem is <code>UPDATE ... WHERE points &gt;= ?</code>: no row means not enough.</li></ul>")),
    (M + "V1__customers_points.sql", "<p>Customers, balances and the ledger, with named constraints.</p>"),
    (M + "V2__demo_customers.sql", "<p>Asha with 120 points, Rohan with none.</p>"),
    ("pom.xml", "<p>Testcontainers and its JUnit extension; H2 for the trap test only.</p>"),
    ("src/main/resources/application.yaml", "<p>The local PostgreSQL; decimals refused for whole-number fields.</p>"),
    (J + "LoyaltyApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/059-loyalty-points-tested-on-real-postgresql/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/basketo/loyalty/
│   ├── LoyaltyController.java   ├── LoyaltyLedger.java   └── LoyaltyApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__customers_points.sql, V2__demo_customers.sql
├── src/test/java/com/basketo/loyalty/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs (with and without Docker)"""
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
<h2>Try it yourself: without Docker</h2>
<p>Stop Docker and run the tests. This was done while building the station (<code>docs/no-docker-run.txt</code>):</p>
""" + code(read("docs/no-docker-run.txt").rstrip(), "text") + """
<p>Every test is skipped and Maven still says BUILD SUCCESS. That is honest on a laptop, and dangerous in CI: see Production.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Green tests, production SQL errors", "Tests on a different database than production.", "Testcontainers with production's version."],
    ["<code>syntax error at or near \"(\"</code> on a MERGE", "H2's <code>MERGE ... KEY</code> syntax on PostgreSQL.", "<code>INSERT ... ON CONFLICT ... DO UPDATE</code>."],
    ["All tests skipped", "Docker is not running (<code>disabledWithoutDocker</code>).", "Start Docker; in CI, treat skips as failure."],
    ["A test passes alone, fails in the suite", "It depends on data another test changed.", "Each test creates its own data."],
    ["<code>Could not find a valid Docker environment</code>", "Docker stopped, without <code>disabledWithoutDocker</code>.", "Start Docker, or add the annotation so tests skip with a reason."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>LoyaltyContractTest</code> ({cnt('LoyaltyContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>H2VersusPostgresTrapTest</code> ({cnt('H2VersusPostgresTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>LoyaltyDatabaseTest</code> ({cnt('LoyaltyDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>How these tests are built</h2>
<dl class="facts">
<dt>The whole app</dt><dd><code>@SpringBootTest</code> starts everything: controllers, transactions, Flyway, on real PostgreSQL.</dd>
<dt>The database</dt><dd><code>PostgresTestConfig</code> declares a PostgreSQL 17 container with <code>@ServiceConnection</code>: Spring connects to it, no URL anywhere.</dd>
<dt>Isolation</dt><dd>No test cleans tables or relies on what another left: each makes fresh customers with <code>newCustomer()</code>.</dd>
<dt>No Docker</dt><dd><code>@Testcontainers(disabledWithoutDocker = true)</code> on the base class: skipped, with the reason, not failed and not passed.</dd>
</dl>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "H2VersusPostgresTrapTest.java", "<p>Written first: the old upsert on H2 and on PostgreSQL, and the new one on both.</p>"),
    (T + "LoyaltyContractTest.java", "<p>Earn and redeem, and every refusal.</p>"),
    (T + "LoyaltyDatabaseTest.java", "<p>Named constraints, a rollback of both rows, and 20 earns at once.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: <code>@SpringBootTest</code>, the Docker rule, and fresh customers.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers and <code>@ServiceConnection</code>.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/basketo/loyalty/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=BalanceChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in (Java files and one migration), all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Balance and history", "Beginner-friendly", 20,
    "Add <code>GET /loyalty/{customerId}</code>: the balance (0 if nothing was ever earned) and the ledger, newest first. Unknown: <code>404</code>.",
    "the test in <code>BalanceChallengeTest</code> passes.",
    ["<code>coalesce</code> turns \"no balance row\" into 0.",
     "<code>JdbcClient</code> maps <code>order_ref</code> to <code>orderRef</code> by itself."],
    "challenge/BalanceChallengeTest.java", ["challenge/solution/LoyaltyLedger.java", "challenge/solution/LoyaltyController.java"]) + challenge(2, "Reverse a returned order", "Go deeper", 30,
    "Add <code>POST /loyalty/{customerId}/earn/{orderRef}/reversal</code>: take back that order's points once, as a REVERSE entry. Already spent: <code>409</code>. Unknown order: <code>404</code>.",
    "the test in <code>ReversalChallengeTest</code> passes.",
    ["The schema must allow a third reason, and an order with both an EARN and a REVERSE entry: a migration.",
     "The conditional UPDATE decides \"already spent\"; the unique key decides \"already reversed\"."],
    "challenge/ReversalChallengeTest.java", ["challenge/solution/V3__reversals.sql", "challenge/solution/LoyaltyLedger.java", "challenge/solution/LoyaltyController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>When is an in-memory database fine?</h2>
<p>List three kinds of test in your projects (a mapping function, a repository query, a whole HTTP flow). For each, would H2 do, would a mock do, or does it need the real database? What would make you change your mind?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, mapping"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old SQL on H2 and on PostgreSQL.</li>
<li>Move every test to a shared PostgreSQL container with <code>@ServiceConnection</code>.</li>
<li>Make each test create its own data.</li>
<li>Write PostgreSQL's upsert, and test it under concurrency.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Testcontainers with production's PostgreSQL version", "Docker on every machine and in CI; a few seconds to start.", '<span class="pill ok">Chosen</span>'],
    ["H2 in compatibility mode", "Fast; accepts SQL production rejects, rejects SQL production needs.", '<span class="pill bad">The trap</span>'],
    ["A shared test database on a server", "Tests collide with each other and with people.", '<span class="pill bad">No</span>'],
    ["Embedded PostgreSQL binaries (no Docker)", "Real PostgreSQL; one more tool to keep at the right version.", '<span class="pill warn">If Docker is impossible</span>'],
    ["Clean tables before each test", "Simple; tests cannot run in parallel.", '<span class="pill warn">Fine for small suites</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Constraints"], [
    ["<code>point_balances</code>", "<code>point_balances_customer_fk</code>, <code>point_balances_not_negative</code>"],
    ["<code>point_entries</code>", "<code>point_entries_customer_fk</code>, <code>point_entries_reason_known</code>, <code>point_entries_sign_matches</code>, <code>point_entries_order_once</code>"]]) + """
""" + code(read(M + "V1__customers_points.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>CI must not go green on skips</dt><dd>Skipping without Docker is honest on a laptop. In CI it would turn "no tests ran" into a green build. Make CI fail when tests were skipped, or when Docker is missing.</dd>
<dt>Same version</dt><dd>Pin the container image to production's major version (here <code>postgres:17-alpine</code>) and upgrade both together.</dd>
<dt>Speed</dt><dd>One container per run, shared by every test, keeps the cost to a few seconds. Reusable containers can keep it across runs on a developer machine.</dd>
<dt>Upsert and sequences</dt><dd><code>ON CONFLICT DO UPDATE</code> still uses up identity values on conflict; gaps in ids are normal.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why not test with H2?", "Because H2 is not the database you ship to. Its compatibility modes accept syntax production rejects and lack features production has, so green tests prove little about production SQL."),
    ("What does @ServiceConnection do?", "It turns a container bean into Spring's connection details: the datasource URL, user and password come from the running container, with no properties to write."),
    ("How do you keep tests independent?", "Each test creates its own data (fresh ids) or resets what it uses, and never relies on the order tests run in."),
    ("What happens when Docker is missing?", "With @Testcontainers(disabledWithoutDocker = true), the tests are skipped and reported as skipped. Without it, they fail. Neither is a pass."),
    ("Why is INSERT ... ON CONFLICT DO UPDATE safe under concurrency?", "PostgreSQL resolves the conflict with the unique index inside one statement: concurrent upserts for the same key wait for each other and then update, instead of both inserting or one failing."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass, on PostgreSQL.", "You ran them without Docker and read the result."],
    ["Testcontainers", "<code>@ServiceConnection</code> and a shared container.", "CI that fails on skips."],
    ["Isolation", "Fresh data per test.", "Tests that could run in parallel."],
    ["SQL", "PostgreSQL's upsert.", "You can explain why it is safe under concurrency."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any test suite with a database:</p>
<ul class="rules">
<li>Which database, and which version, do the tests run on?</li>
<li>Does any test need another test's data, or a particular order?</li>
<li>What happens on a machine without Docker: skip, fail, or a lie?</li>
<li>Is there SQL in the code that only one database understands, and is it tested on that one?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
