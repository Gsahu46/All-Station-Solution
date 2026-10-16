"""Station 060 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 60,
    "stack": "Spring Boot 4.1.1 · Java 25 · JdbcClient · MySQL 8.4 InnoDB · INSERT … ON DUPLICATE KEY UPDATE · deadlock retry · virtual threads · Testcontainers",
    "simulation": "Warehouses, SKUs and counts are demo data, not Basketo's. A sync writes stock rows; no warehouse system, scanner or order flow is involved.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (MySQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/basketo/inventory/"
T = "src/test/java/com/basketo/inventory/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("SKU", "Stock keeping unit: one product in one pack size.", "Rice, 5 kg bag.", "<code>RICE-5KG</code>"),
    ("Snapshot", "What a warehouse counted, for the SKUs it sends.", "A stock-take sheet.", "the <code>PUT</code> body"),
    ("Upsert", "Insert the row, or update it if it is already there, in one statement.", "\"Write 35 on the RICE line; add the line if there is none.\"", "<code>ON DUPLICATE KEY UPDATE</code>"),
    ("Unique key", "The database refuses a second row with the same values.", "One line per product on the sheet.", "<code>stock_levels_warehouse_sku</code>"),
    ("Gap lock", "InnoDB locks the space where a row would go, not just rows that exist.", "Reserving the empty shelf, not a box on it.", "taken by <code>SELECT … FOR UPDATE</code> on a missing row"),
    ("Deadlock", "Two transactions each wait for the other; InnoDB stops one (error 1213).", "Two trolleys in one aisle, each waiting for the other to back out.", "retried up to 3 times"),
]
STORY = [
    ("The nightly job", "Each warehouse sends its counts. For every SKU the job looks for its row: if there is none, it inserts one; otherwise it updates it."),
    ("Duplicates", "The job timed out and was retried while the first run was still going. Both runs looked, both found nothing, both inserted: RICE-5KG twice, and the website summed them."),
    ("Deadlocks", "A unique key and <code>SELECT … FOR UPDATE</code> stopped the duplicates. Then Bhiwandi and Hoskote synced new SKUs at the same time, and one of them failed every night with \"Deadlock found\"."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Do not look and then write. Ask the database to write, and let its unique key decide.</p>

<h2>What are we building?</h2>
<p><code>PUT /warehouses/{id}/stock</code> takes a warehouse's counts and stores them: new SKUs get a row, known SKUs get the new count. Sending the same counts twice changes nothing.</p>

<h2>An everyday analogy</h2>
<p>A shop register with one printed line per product. The old way: read the register, then walk off to write. Two clerks can both see no RICE line and both add one. The new way: hand the register \"RICE: 35\", and the register itself either fills the line or adds it, one clerk at a time.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Check the body</strong>: 1 to 1000 SKUs, each once, counts 0 to 1,000,000. SKUs are upper-cased.</li>
<li><strong>Lock the warehouse</strong>: a second sync of the same warehouse waits for the first.</li>
<li><strong>Upsert</strong> 500 rows per statement: insert, or on the unique key, update the count.</li>
<li><strong>Commit</strong> all of it, or none. If InnoDB still picks this sync as a deadlock victim, run it again.</li>
</ol>

<details class="qa check"><summary>Check yourself: Bhiwandi has RICE-5KG 40 and ATTA-10KG 12. It sends only RICE-5KG 35. What is stored?</summary><p>RICE-5KG 35 (the count, not 40 + 35) and ATTA-10KG still 12. A snapshot only speaks for the SKUs it lists; Practice challenge 2 adds a \"full\" mode that zeroes the rest.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No orders or reservations.</strong> Counts only; selling against them is a later station.</li>
<li><strong>No warehouse system.</strong> The sync is a plain HTTP call with demo data.</li>
<li><strong>No PostgreSQL code.</strong> The PostgreSQL version is compared on paper (Design, Practice 3).</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Basketo</strong> (a fictional grocery delivery company) syncs stock from its warehouses every night. The sync inserted duplicate rows on MySQL, and after a first fix, deadlocked when two warehouses synced together.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a snapshot of new SKUs, <b>then</b> <code>200</code> and one row per SKU.</li>
<li><b>Given</b> a later snapshot with some of them, <b>then</b> those rows carry the new counts, and the others are unchanged.</li>
<li><b>Given</b> the same snapshot twice, <b>then</b> the same rows, never a duplicate.</li>
<li><b>Given</b> ten syncs of two warehouses at once on the same new SKUs, <b>then</b> all <code>200</code>, and exactly one row per SKU per warehouse.</li>
<li><b>Given</b> ten different snapshots of one warehouse at once, <b>then</b> every row ends up from the same snapshot.</li>
<li><b>Given</b> the same SKU twice in one body (in any case), <b>then</b> <code>422</code>; an unknown warehouse <code>404</code>; a malformed body <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>One row per warehouse and SKU, guaranteed by a named unique key, not by a lookup.</li>
<li>A snapshot is one transaction: a bad row anywhere leaves nothing behind.</li>
<li>SKUs are normalised with <code>Locale.ROOT</code>; counts are whole units.</li>
<li>A deadlock victim is run again (at most 3 attempts), and every one is logged.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Write a multi-row <code>INSERT … ON DUPLICATE KEY UPDATE</code> with a row alias.</li>
<li>Explain why select-then-insert duplicates rows, and why <code>FOR UPDATE</code> on a missing row deadlocks.</li>
<li>Batch large writes in chunks, inside one transaction.</li>
<li>Know where MySQL's upsert and PostgreSQL's <code>ON CONFLICT</code> differ.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its MySQL, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>PUT</code>", "<code>/warehouses/{id}/stock</code>", "<code>{\"items\": [{\"sku\", \"quantity\"}, …]}</code>: store these counts. Answers <code>{warehouseId, syncedItems, skusInWarehouse}</code>."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "The snapshot is stored"],
    ['<span class="pill warn">400</span>', "No items or more than 1000, a SKU outside <code>[A-Za-z0-9-]{3,30}</code>, a count below 0, above 1,000,000 or not whole, a missing field"],
    ['<span class="pill warn">404</span>', "No such warehouse"],
    ['<span class="pill warn">422</span>', "The same SKU twice in one snapshot"],
    ['<span class="pill bad">503</span>', "Three deadlocks in a row; the snapshot was rolled back, send it again"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against the demo warehouses (1 Bhiwandi, 2 Hoskote). JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-bhiwandi-first-snapshot", "Case 1: Bhiwandi's first snapshot", "<b>Why:</b> three new rows; <code>dal-1kg</code> is stored as <code>DAL-1KG</code>."),
    ("02-the-same-job-again-rice-recounted", "Case 2: RICE-5KG recounted", "<b>Why:</b> the row is updated to 35, still three SKUs."),
    ("03-one-sku-twice", "Case 3: OIL-1L and oil-1l in one body", "<b>Why:</b> the same SKU after upper-casing; which count is right is the sender's call: <code>422</code>."),
    ("04-no-such-warehouse", "Case 4: warehouse 99", "<b>Why:</b> <code>404</code>, checked before any write."),
    ("05-half-a-bag", "Case 5: a count of 2.5", "<b>Why:</b> <code>400</code>: whole units only."),
]) + """
<h2>The rows afterwards</h2>
""" + code(read("docs/captures/rows.txt").rstrip(), "text") + """
<h2>Both warehouses at once</h2>
<p class="muted">From <code>docs/capture.sh</code>: 10 parallel curl requests, five per warehouse, each with the same 200 new SKUs (<code>docs/captures/rush.txt</code>). The last number is how many deadlocks the app logged and retried.</p>
""" + code(read("docs/captures/rush.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A snapshot, then a smaller one", "Counts set, unlisted SKUs left alone", "<code>aSnapshotSetsTheCountsAndTheNextOneOverwritesThem</code>"],
    ["The same snapshot twice", "Same rows", "<code>theSameSnapshotTwiceLeavesTheSameRows</code>"],
    ["1000 SKUs", "Two statements of 500, one transaction", "<code>aThousandSkusGoInTwoChunks</code>"],
    ["A Turkish default locale", "<code>milk-1l</code> is still <code>MILK-1L</code>", "<code>skusAreUpperCasedTheSameWayInEveryLocale</code>"],
    ["A SKU twice; an unknown warehouse; bad bodies", "<code>422</code>; <code>404</code>; <code>400</code>", "<code>StockContractTest</code>"],
    ["A deadlock; three in a row", "Run again; <code>503</code>", "<code>aDeadlockVictimIsRunAgain</code>, <code>threeDeadlocksInARowAre503</code>"],
    ["A bad row in the second chunk", "The first 500 rows roll back too", "<code>aBadRowInTheSecondChunkRollsBackTheFirst</code>"],
    ["Duplicate, negative, lower-case or orphan rows written directly", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"],
    ["Ten syncs of two warehouses, five rounds", "All <code>200</code>, 200 rows each", "<code>twoWarehousesSyncingTheSameNewSkusNeverFail</code>"],
    ["Ten different snapshots of one warehouse, half in reverse order", "One whole snapshot wins", "<code>parallelSnapshotsOfOneWarehouseLeaveOneWholeSnapshot</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Select, then insert: under concurrency it duplicates rows, and with <code>FOR UPDATE</code> it deadlocks on gap locks.</p>
<p>The test replays both old versions step by step on two plain JDBC connections, so every statement and lock is visible:</p>
<ul>
<li><strong>Version 1, no unique key.</strong> Both connections look for RICE-5KG, both find nothing, both insert: two rows.</li>
<li><strong>Version 2, unique key and <code>FOR UPDATE</code>.</strong> Warehouse 1 looks for RICE-5KG, warehouse 2 for ATTA-10KG; neither exists, so each locks the <em>gap</em> where its row would go. On an empty range it is the same gap, and gap locks do not block each other. Then both insert into that gap, each waits for the other's gap lock, and MySQL kills one with error 1213. Every time, for SKUs that never touch.</li>
<li><strong>The upsert.</strong> No look first: both warehouses get their row, and the retried job updates instead of inserting.</li>
</ul>
<p>While building, each fix was undone once:</p>
<ul>
<li>Adding the count instead of setting it turned 5 tests red.</li>
<li>No retry: 3 red, one of them the two-warehouse test hitting a real deadlock.</li>
<li>No transaction: 2 red. No duplicate check, no warehouse check, <code>toUpperCase()</code> without <code>Locale.ROOT</code>: 1 each.</li>
<li>No warehouse lock was green in 1 of 3 runs: the retry absorbed more than 20 deadlocks. See Design for why the lock stays.</li>
</ul>
</div>
""" + code(read(T + "SelectThenInsertTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "StockController.java", dwn("Validates the snapshot, upper-cases SKUs, refuses duplicates, and runs the sync again after a deadlock.",
        "A clear <code>422</code> for a SKU sent twice, and no deadlock reaching the warehouse job as a <code>500</code>.",
        "\"Which of 5 and 8 is the count?\" answered silently by whichever row came last.",
        "<ul><li>The retry wraps the whole transaction: after a deadlock InnoDB has rolled it all back, so the only safe retry is from the start.</li><li><code>PessimisticLockingFailureException</code> is what Spring makes of MySQL 1213 (and of a lock wait timeout).</li></ul>")),
    (J + "StockSync.java", dwn("Locks the warehouse row, then upserts in chunks of 500, all in one transaction.",
        "One statement per 500 rows, no look-up first, and one sync per warehouse at a time.",
        "Select-then-insert's duplicates and deadlocks, or a half-written snapshot.",
        "<ul><li><code>AS incoming … quantity = incoming.quantity</code> is the MySQL 8.0.19+ form; <code>VALUES(quantity)</code> still works but is deprecated.</li><li>The <code>404</code> check and the lock are one query.</li></ul>")),
    (M + "V1__warehouses_and_stock.sql", dwn("Warehouses and stock rows, with four named constraints.",
        "<code>ON DUPLICATE KEY UPDATE</code> only fires on a unique key; without <code>stock_levels_warehouse_sku</code> it silently inserts.",
        "Duplicates from any writer that is not this app.")),
    (M + "V2__demo_warehouses.sql", "<p>Bhiwandi (1) and Hoskote (2).</p>"),
    ("src/main/resources/application.yaml", "<p>Problem details on, whole numbers only.</p>"),
    ("compose.yaml", "<p>MySQL 8.4 for running the app.</p>"),
    (J + "InventoryApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/060-inventory-sync-with-mysql-upserts/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/basketo/inventory/
│   ├── StockController.java   ├── StockSync.java   └── InventoryApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__warehouses_and_stock.sql, V2__demo_warehouses.sql
├── src/test/java/com/basketo/inventory/   (see Tests)
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
""" + code("""docker compose up -d        # MySQL 8.4 on localhost:3306
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests; starts its own MySQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Ask MySQL how many rows an upsert \"affected\" (from <code>docs/captures/row-count.txt</code>):</p>
""" + code(read("docs/captures/row-count.txt").rstrip(), "text") + """
<p>1 for an insert, 2 for an update, and 0 when nothing changed. From Java, Connector/J asks MySQL for <em>found</em> rows, so the unchanged case comes back as 1 (<code>mySqlCountsAnUpsertedRowTwice</code>). Never use the count to mean \"how many SKUs\".</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>Deadlock found when trying to get lock; try restarting transaction</code>", "InnoDB chose this sync as a deadlock victim (error 1213); all of it was rolled back.", "Expected now and then; the app runs it again and logs it. Many per night means many writers on the same rows."],
    ["<code>Duplicate entry '1-RICE-5KG' for key 'stock_levels.stock_levels_warehouse_sku'</code>", "A plain <code>INSERT</code> of a SKU the warehouse already has.", "Use the upsert; the unique key is what makes it an update."],
    ["<code>Check constraint 'stock_levels_sku_shape' is violated.</code>", "A SKU that was not upper-cased reached the database, for example by a script.", "Upper-case with <code>Locale.ROOT</code> before writing."],
    ["<code>'VALUES function' is deprecated</code> warning", "<code>… UPDATE quantity = VALUES(quantity)</code>.", "Use a row alias: <code>VALUES (…) AS incoming … quantity = incoming.quantity</code>."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>StockContractTest</code> ({cnt('StockContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>SelectThenInsertTrapTest</code> ({cnt('SelectThenInsertTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>StockDatabaseTest</code> ({cnt('StockDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Concurrency", "A real concurrency test that proves the invariant holds", f"<code>StockConcurrencyTest</code> ({cnt('StockConcurrencyTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, MySQL 8.4 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "SelectThenInsertTrapTest.java", "<p>Written first: both old versions on two plain JDBC connections, then the upsert.</p>"),
    (T + "StockConcurrencyTest.java", "<p>Ten syncs at a time, released by one latch: two warehouses on the same new SKUs, and one warehouse with ten different snapshots.</p>"),
    (T + "StockDatabaseTest.java", "<p>Named constraints with plain SQL, a rollback across chunks, an in-place update, and MySQL's affected-row count.</p>"),
    (T + "StockContractTest.java", "<p>The endpoint through HTTP, including a deadlock injected with <code>@MockitoSpyBean</code>.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: no stock before each test, the snapshot builder and the latch helper.</p>"),
    (T + "MySqlTestConfig.java", "<p>MySQL 8.4 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/basketo/inventory/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=ReadOneSkuChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Read one SKU", "Beginner-friendly", 20,
    "Add <code>GET /warehouses/{id}/stock/{sku}</code>: <code>{warehouseId, sku, quantity}</code>. <code>rice-5kg</code> finds <code>RICE-5KG</code>; a SKU the warehouse never synced is <code>404</code>.",
    "both tests in <code>ReadOneSkuChallengeTest</code> pass.",
    ["Normalise the path the same way the sync does, with <code>Locale.ROOT</code>.",
     "<code>JdbcClient … .query(Level.class).optional()</code> maps a record by column names."],
    "challenge/ReadOneSkuChallengeTest.java", ["challenge/solution/StockController.java", "challenge/solution/StockSync.java"]) + challenge(2, "A full stock-take", "Go deeper", 30,
    "Add <code>?mode=full</code>: the snapshot is everything on the shelves, so every SKU of that warehouse it does not list is set to 0 (kept, not deleted). The response gains <code>zeroedSkus</code>.",
    "both tests in <code>FullSnapshotChallengeTest</code> pass, and the station tests still do.",
    ["Zero in the same transaction as the upserts: a sync that fails halfway must not leave SKUs zeroed.",
     "<code>… WHERE warehouse_id = ? AND sku NOT IN (?, ?, …)</code>; the warehouse lock already keeps other syncs out.",
     "Keep the existing <code>sync(id, items)</code> as it is; the contract tests stub it."],
    "challenge/FullSnapshotChallengeTest.java", ["challenge/solution/StockSync.java", "challenge/solution/StockController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>The same sync on PostgreSQL</h2>
<p>Basketo's new region runs PostgreSQL. Write the upsert with <code>INSERT … ON CONFLICT (warehouse_id, sku) DO UPDATE SET quantity = EXCLUDED.quantity</code>. Then answer: what does each database do when one statement holds the same SKU twice? (PostgreSQL refuses: \"ON CONFLICT DO UPDATE command cannot affect row a second time\"; MySQL applies both.) Which other unique keys could fire MySQL's update but not PostgreSQL's? Does the warehouse lock still make sense?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: both old versions, step by step on two connections.</li>
<li>Add the unique key, and write the multi-row upsert against it.</li>
<li>Put the snapshot in one transaction, in chunks of 500.</li>
<li>Run real parallel syncs; handle what they show (here: deadlocks, below).</li>
</ol>
<h2>Why the upsert was not the end</h2>
<p>With the upsert alone, ten parallel syncs (five per warehouse, the same 200 new SKUs) deadlocked inside InnoDB about 20 times per test run while building this station, and once a request lost all three attempts. Several syncs of the <em>same</em> warehouse were taking row and gap locks on the same new keys in a different order. Locking the warehouse row first (<code>SELECT … FOR UPDATE</code> on one existing row: no gap) makes syncs of one warehouse take turns. Afterwards a run showed 0 or 1 deadlocks, between the two warehouses; the retry covers those. The lock is a reduction, not a guarantee: InnoDB may always choose a victim, which is why the retry stays.</p>
<h2>Where MySQL and PostgreSQL differ</h2>
""" + table(["", "MySQL 8.4", "PostgreSQL 17"], [
    ["Syntax", "<code>INSERT … AS incoming ON DUPLICATE KEY UPDATE q = incoming.q</code>", "<code>INSERT … ON CONFLICT (warehouse_id, sku) DO UPDATE SET q = EXCLUDED.q</code>"],
    ["Which key", "Any unique key or the primary key that clashes", "The one you name (or a named constraint)"],
    ["Same key twice in one statement", "Both applied, in order", "Error: cannot affect row a second time"],
    ["Affected rows", "1 inserted, 2 updated, 0 unchanged", "1 per row inserted or updated"],
    ["Get the row back", "<code>LAST_INSERT_ID()</code> tricks", "<code>RETURNING</code>"]]) + """
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Unique key + multi-row upsert + warehouse lock + retry", "MySQL-specific SQL; syncs of one warehouse take turns.", '<span class="pill ok">Chosen</span>'],
    ["Select, then insert", "Duplicates under concurrency.", '<span class="pill bad">The trap</span>'],
    ["Select <code>FOR UPDATE</code>, then insert", "Gap-lock deadlocks, even between warehouses.", '<span class="pill bad">The trap, version 2</span>'],
    ["Insert, catch the duplicate, then update", "Two statements per SKU, and an error per known SKU.", '<span class="pill warn">Works, slowly</span>'],
    ["<code>READ COMMITTED</code> isolation", "No gap locks for searches; select-then-insert then fails on the unique key instead.", '<span class="pill warn">Moves the problem</span>'],
    ["Load into a staging table, then one <code>INSERT … SELECT … ON DUPLICATE KEY UPDATE</code>", "An extra table; best for very large snapshots.", '<span class="pill warn">Valid at scale</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Constraints", "Why"], [
    ["<code>warehouses</code>", "PK", "What can sync; its row is the per-warehouse lock."],
    ["<code>stock_levels</code>", "<code>stock_levels_warehouse_sku</code> (UNIQUE), <code>stock_levels_warehouse_fk</code>, <code>stock_levels_quantity_range</code>, <code>stock_levels_sku_shape</code>", "One row per SKU per warehouse; the key the upsert relies on."]]) + """
<p><strong>Transaction boundary:</strong> one snapshot, from the warehouse lock to the last chunk. A retry starts it again from the top.</p>
""" + code(read(M + "V1__warehouses_and_stock.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Count the deadlocks</dt><dd>The app logs each one. A few a night are normal for InnoDB; a rising count means more writers on the same rows.</dd>
<dt>Lock wait timeout</dt><dd>A sync waiting for another sync of the same warehouse waits up to <code>innodb_lock_wait_timeout</code> (50 s by default). A huge snapshot can make the next one time out.</dd>
<dt>Snapshot size</dt><dd>1000 SKUs per call is a demo rule. Larger warehouses send several calls; each is its own transaction.</dd>
<dt>Counts are not stock</dt><dd>Orders placed between the count and the sync are lost if the count simply overwrites. Real systems store counts with a time and apply orders after it.</dd>
<dt>Replication</dt><dd><code>ON DUPLICATE KEY UPDATE</code> on a table with more than one unique key is flagged unsafe for statement-based replication; row-based (the MySQL 8 default) is fine.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why does select-then-insert create duplicates?", "Two transactions can both look before either inserts. Without a unique key, both inserts succeed. Only a constraint decides between them."),
    ("What is a gap lock?", "In REPEATABLE READ, InnoDB locks the space between index records that a search covered, so no one can insert there. Locking a row that does not exist locks a gap."),
    ("Why did SELECT … FOR UPDATE deadlock two warehouses?", "Both locked the same gap (gap locks do not conflict with each other), then both inserted into it, which needs the other's gap lock released. A cycle: InnoDB kills one with error 1213."),
    ("How does ON DUPLICATE KEY UPDATE decide to update?", "When the insert clashes with any unique key or the primary key. With no unique key it never fires, and simply inserts."),
    ("How do you retry a deadlock correctly?", "The victim's whole transaction was rolled back, so retry the whole transaction, a bounded number of times, and log it."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["SQL", "A multi-row upsert with a row alias.", "The PostgreSQL version, and where it behaves differently."],
    ["Concurrency", "Why select-then-insert fails, both ways.", "Why the warehouse lock reduces deadlocks but the retry stays."],
    ["Transactions", "One snapshot, one transaction.", "What a retry must start from."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("The upsert adds the count",
     "\"A delivery adds to what is on the shelf\" is true for deliveries, not for a stock-take. Every resync doubles the stock.",
     "<code>aSnapshotSetsTheCountsAndTheNextOneOverwritesThem</code>, <code>theSameSnapshotTwiceLeavesTheSameRows</code>, <code>anUpsertUpdatesTheRowInPlace</code> and <code>parallelSnapshotsOfOneWarehouseLeaveOneWholeSnapshot</code> fail."),
    ("The same SKU twice is accepted",
     "MySQL applies both rows of one statement, so with finding 1 the two counts are summed; without it, the last one wins silently.",
     "<code>theSameSkuTwiceIs422EvenInDifferentCase</code> fails."),
    ("No warehouse check",
     "\"The foreign key already checks it\": it does, as a <code>500</code> with a constraint message instead of a <code>404</code>. The check was also the per-warehouse lock.",
     "<code>anUnknownWarehouseIs404</code> fails."),
    ("SKUs kept as sent",
     "<code>dal-1kg</code> and <code>DAL-1KG</code> become two products, and the database's <code>stock_levels_sku_shape</code> refuses lower case anyway: a <code>500</code>.",
     "<code>skusAreUpperCasedTheSameWayInEveryLocale</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate tidies the sync: \"the foreign key already checks the warehouse\", \"SKUs exactly as printed on the label\", and the upsert now adds, \"like a delivery\". Read the two files and list every problem before opening the findings.</p>
<p class="path">review/StockController.java</p>
""" + code(read("review/StockController.java"), "java") + """
<p class="path">review/StockSync.java</p>
""" + code(read("review/StockSync.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the two flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">No duplicate row got through: the unique key held. What the flaws broke is what the numbers mean, which no constraint can check for you.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
