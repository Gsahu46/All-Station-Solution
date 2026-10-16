"""Station 062 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 62,
    "stack": "Spring Boot 4.1.1 · Java 25 · JdbcClient · PostgreSQL 17 B-tree indexes · EXPLAIN (ANALYZE, BUFFERS) · Flyway · Testcontainers",
    "simulation": "Shipments, phone numbers and airway bills are generated demo data (300,003 rows), not Dakroute's. Nothing is shipped or tracked.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/dakroute/shipments/"
T = "src/test/java/com/dakroute/shipments/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]
import re as _re
def pages(name):
    """Pages (8 kB blocks) the whole query touched: the first 'Buffers:' line of a saved plan, hit + read."""
    line = next(l for l in read("docs/captures/" + name).splitlines() if "Buffers:" in l)
    return sum(int(n) for n in _re.findall(r"(?:hit|read)=(\d+)", line))
P_NEW, P_OLD, P_DATE = pages("explain-the-search.txt"), pages("explain-the-old-search.txt"), pages("explain-date-first-index.txt")

# ---------- Level 1: Understand ----------
TERMS = [
    ("Index", "A sorted copy of some columns, pointing at the rows.", "The index at the back of a book.", "<code>shipments_phone_booked_on</code>"),
    ("B-tree", "PostgreSQL's default index: sorted, so it finds one value or a range quickly.", "A phone book sorted by name.", "every index here"),
    ("Composite index", "An index on several columns, sorted by the first, then the second.", "Sorted by surname, then first name.", "<code>(phone, booked_on)</code>"),
    ("Sequential scan", "Reading every row of the table.", "Reading the whole book to find one word.", "the old search"),
    ("EXPLAIN ANALYZE", "Runs a query and shows the plan PostgreSQL chose and what it really did.", "A route with the actual traffic, not the map.", "the tests and captures"),
    ("Page", "PostgreSQL reads and caches data 8 kB at a time.", "One page of the book.", "<code>Buffers: shared hit=… read=…</code>"),
]
STORY = [
    ("A customer calls", "\"Where is my parcel? My number is +91 98765 43210, I sent it in March.\" Support searches by phone and dates."),
    ("Nine seconds", "Phones were stored as typed, so the search cleaned them in SQL before comparing. Someone added an index on phone; the search stayed slow, because it compared a cleaned value, not the column."),
    ("The fix", "Store phones as 10 digits, clean what support types in Java, and index (phone, booked_on) in that order. The same search touches " + str(P_NEW) + " pages instead of " + str(P_OLD) + "."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">An index helps only a query that compares the indexed column itself. Check with EXPLAIN, not by hope.</p>

<h2>What are we building?</h2>
<p><code>GET /shipments/search?phone=…&amp;from=…&amp;to=…</code> returns a customer's shipments in a date range, newest first, from an index.</p>

<h2>An everyday analogy</h2>
<p>A ledger sorted by phone number, and within each number by date. Finding \"98765 43210 in March\" is opening at that number and reading a few lines. A ledger sorted by date first means reading every line of March to find one number.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Clean the phone</strong> as support typed it: <code>+91 98765 43210</code> becomes <code>9876543210</code>.</li>
<li><strong>Check the dates</strong>: forwards, at most 366 days.</li>
<li><strong>Search</strong> the stored column: the index goes straight to that phone, then to the dates.</li>
<li><strong>Return</strong> at most 50, newest first.</li>
</ol>

<details class="qa check"><summary>Check yourself: the index is on (booked_on, phone). Why is \"one phone, January to September\" slow?</summary><p>The index is sorted by date first. Every entry from January to September, for every phone, sits between the first and the last match, so PostgreSQL walks all of them to find the 3 that match: """ + str(P_DATE) + """ pages in the capture, against """ + str(P_NEW) + """ for the right order.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No tracking.</strong> A shipment's status is a stored value.</li>
<li><strong>No 30 million rows.</strong> 300,003 demo rows show the same plans; the gap only grows with size.</li>
<li><strong>No partial-number search.</strong> \"Last four digits\" is Practice 3, on paper.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Dakroute</strong> (a fictional courier) has 30 million shipments. Support's search by phone and date took 9 seconds, with an index in place.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo data: 9876543210 has shipments on 2 March, 15 March and 20 May; seller 9123456789 has 30,000; 90,000 other customers have 3 each.</p>
<ol class="gwt">
<li><b>Given</b> 9876543210 and March, <b>then</b> the 15 March and 2 March shipments, in that order.</li>
<li><b>Given</b> <code>+91 98765 43210</code>, <code>098765-43210</code> or <code>(98765) 43210</code>, <b>then</b> the same customer.</li>
<li><b>Given</b> the seller and nine months, <b>then</b> the newest 50.</li>
<li><b>Given</b> no match, <b>then</b> <code>200</code> with an empty list.</li>
<li><b>Given</b> a number that is not an Indian mobile, dates backwards or over 366 days, a non-ISO date or a missing parameter, <b>then</b> <code>400</code>.</li>
<li><b>Given</b> the search's plan, <b>then</b> an index scan on <code>shipments_phone_booked_on</code> touching at most 10 pages.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Phones are stored as 10 digits; a CHECK constraint refuses anything else.</li>
<li>Typed phones are cleaned in Java, never in the <code>WHERE</code> clause.</li>
<li>The index puts the equality column first, the range column second.</li>
<li>No index without a query that uses it: each one slows every insert.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Read <code>EXPLAIN (ANALYZE, BUFFERS)</code>: node types, index conditions, pages.</li>
<li>Choose the column order of a composite index.</li>
<li>Recognise a query that cannot use an index.</li>
<li>Measure what an index costs on writes.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/shipments/search?phone=…&amp;from=YYYY-MM-DD&amp;to=YYYY-MM-DD</code>", "<code>{phone, from, to, shipments: [{awb, bookedOn, status}]}</code>, newest first, at most 50."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "Results, possibly an empty list"],
    ['<span class="pill warn">400</span>', "Not a 10-digit Indian mobile after cleaning, dates backwards or more than 366 days apart (demo rule), a date not in ISO form, a missing parameter"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-march-for-one-customer", "Case 1: one customer, March", "<b>Why:</b> two shipments, newest first."),
    ("02-the-phone-as-the-customer-says-it", "Case 2: <code>+91 98765 43210</code>, the whole year", "<b>Why:</b> cleaned to the stored form; all three shipments."),
    ("03-nothing-in-april", "Case 3: April", "<b>Why:</b> no shipment: an empty list, not a 404."),
    ("04-not-a-mobile-number", "Case 4: <code>12345</code>", "<b>Why:</b> <code>400</code> before any query."),
    ("05-dates-backwards", "Case 5: 31 March to 1 March", "<b>Why:</b> <code>400</code>."),
]) + """
<h2>The search's plan</h2>
<p class="muted">From <code>docs/capture.sh</code>: <code>EXPLAIN (ANALYZE, BUFFERS)</code> of the app's query in <code>psql</code>, against the demo data (<code>docs/captures/explain-the-search.txt</code>).</p>
""" + code(read("docs/captures/explain-the-search.txt").rstrip(), "text") + """
<p><code>Index Scan Backward</code>: the index already holds the phone's shipments in date order, so PostgreSQL reads it from the end for \"newest first\". <code>Buffers: shared hit=""" + str(P_NEW) + """</code>: """ + str(P_NEW) + """ pages, all in memory.</p>"""

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Three ways of typing one number", "One customer", "<code>thePhoneCanBeTypedTheWaysCustomersSayIt</code>"],
    ["A seller with 30,000 shipments", "The newest 50", "<code>theBusySellerGetsTheNewestFifty</code>"],
    ["No shipment, or none in the range", "Empty list", "<code>noShipmentIsAnEmptyList</code>"],
    ["Bad phone, dates, missing parameter, SQL in the phone", "<code>400</code>", "<code>badSearchesAre400</code>"],
    ["The old cleaned-in-SQL search", "Seq Scan; the index is ignored", "<code>theOldSearchCleanedThePhoneInSqlSoItsIndexWasNeverUsed</code>"],
    ["No index, phone only, date first, phone then date", "Measured against each other", "<code>theColumnOrderOfTheIndexDecidesHowMuchIsRead</code>"],
    ["A typed phone or a duplicate airway bill written directly", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"],
    ["Indexes and inserts", "More WAL per row for each index", "<code>everyIndexIsMoreWorkForEveryInsert</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Adding an index without checking EXPLAIN, or in the wrong column order.</p>
<p><strong>The index nobody used.</strong> The old query compared <code>right(regexp_replace(phone, '[^0-9]', '', 'g'), 10)</code>, a value computed from each row. A B-tree on <code>phone</code> is sorted by the stored text, not by that value, so PostgreSQL read all 300,003 rows (<code>Rows Removed by Filter: 300001</code>), """ + str(P_OLD) + """ pages:</p>
""" + code(read("docs/captures/explain-the-old-search.txt").rstrip(), "text") + """
<p><strong>The wrong order.</strong> With <code>(booked_on, phone)</code>, the search for one customer over nine months returned 3 entries but walked every entry in those dates: """ + str(P_DATE) + """ pages.</p>
""" + code(read("docs/captures/explain-date-first-index.txt").rstrip(), "text") + """
<p><strong>Phone only.</strong> <code>(phone)</code> is fine for most customers, who have a few shipments. For the seller, a week's search reads all 30,000 of their index entries, then filters and sorts; <code>(phone, booked_on)</code> reads fewer than 300. The test asserts both.</p>
<p>While building, each fix was undone once: no index turned 1 test red; the date-first index 1; no <code>+91</code> handling 1; no <code>LIMIT</code> 2; oldest first 2; no range check 1.</p>
</div>
""" + code(read(T + "PhoneSearchTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "ShipmentController.java", dwn("Parses the dates and checks the range, then cleans the phone.",
        "Every bad input is a <code>400</code> before the database.",
        "A two-year search walking a seller's whole history.")),
    (J + "PhoneNumber.java", dwn("Turns what support typed into the 10 digits the table stores.",
        "The cleaning happens once, in Java, so SQL compares the column as stored.",
        "<code>regexp_replace</code> in the <code>WHERE</code> clause, and a sequential scan.")),
    (J + "ShipmentSearch.java", dwn("The search: equality on phone, a range on dates, newest 50.",
        "Its shape matches the index, so the plan is an index scan read backwards.",
        "A sort of every matching row for the seller.")),
    (M + "V1__shipments.sql", dwn("The table and its named constraints.",
        "<code>shipments_phone_shape</code> keeps typed phones out for every writer.",
        "Old formats creeping back in from an import script.")),
    (M + "V2__demo_shipments.sql", "<p>3 hand-written shipments and 300,000 generated ones.</p>"),
    (M + "V3__search_index.sql", dwn("The search index, built after the data, then <code>ANALYZE</code>.",
        "Equality column first, range column second.",
        "A plan that reads every row.")),
    ("src/main/resources/application.yaml", "<p>Problem details on.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "ShipmentsApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/062-shipment-search-by-phone-number/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/dakroute/shipments/
│   ├── ShipmentController.java   ├── PhoneNumber.java   ├── ShipmentSearch.java   └── ShipmentsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__shipments.sql, V2__demo_shipments.sql, V3__search_index.sql
├── src/test/java/com/dakroute/shipments/   (see Tests)
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
./mvnw spring-boot:run      # the API on http://localhost:8080; the first start loads 300,003 shipments
./mvnw test                 # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Ask PostgreSQL for the plan, then drop the index and ask again:</p>
""" + code("""docker compose exec postgres psql -U dakroute -d dakroute
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM shipments WHERE phone = '9876543210' AND booked_on BETWEEN '2026-03-01' AND '2026-03-31';
BEGIN; DROP INDEX shipments_phone_booked_on;
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM shipments WHERE phone = '9876543210' AND booked_on BETWEEN '2026-03-01' AND '2026-03-31';
ROLLBACK;""", "sql") + """
<p>Index sizes from the capture (<code>docs/captures/sizes.txt</code>): each index is a sorted copy of its columns, and every insert writes to each one.</p>
""" + code(read("docs/captures/sizes.txt").rstrip(), "text") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>Seq Scan</code> although an index exists", "The query wraps the column in a function or cast, or the table is tiny, or most rows match.", "Compare the column as stored; for a function, an expression index on exactly that function."],
    ["<code>value too long for type character varying(10)</code>", "A typed phone reached the database; the length check fires before the named CHECK.", "Clean in Java first. Found while building this station."],
    ["Different plans on your laptop", "Small tables, other statistics, other settings.", "Run <code>ANALYZE</code>, and test plans on realistic data volumes."],
    ["Parallel workers in the plan", "PostgreSQL split a big scan across processes.", "The tests set <code>max_parallel_workers_per_gather = 0</code> so pages are counted in one process."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found (empty)", f"<code>ShipmentContractTest</code> ({cnt('ShipmentContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>PhoneSearchTrapTest</code> ({cnt('PhoneSearchTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>ShipmentDatabaseTest</code> ({cnt('ShipmentDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>How plans are tested</h2>
<p>Timings vary from machine to machine; plans and page counts do not, for the same data. The tests run <code>EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)</code> without parallel workers and assert node types, index names, index entries returned and pages touched, always as comparisons (\"more than 10 times\") rather than exact page numbers. The write-cost test counts WAL records with <code>EXPLAIN (ANALYZE, WAL)</code>, inside a transaction that is rolled back.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "PhoneSearchTrapTest.java", "<p>Written first: the old search, and four index choices on a copy of the data.</p>"),
    (T + "ShipmentDatabaseTest.java", "<p>Named constraints, a rolled-back batch, and WAL records per index.</p>"),
    (T + "ShipmentContractTest.java", "<p>The endpoint through HTTP.</p>"),
    (T + "ApiTest.java", "<p>Shared setup and the EXPLAIN reader.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/dakroute/shipments/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=TrackByAwbChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Track by airway bill", "Beginner-friendly", 20,
    "Add <code>GET /shipments/{awb}</code>: one shipment, the number in any case. Unknown is <code>404</code>; not <code>DR</code> plus 10 digits is <code>400</code>.",
    "both tests in <code>TrackByAwbChallengeTest</code> pass.",
    ["No new index: <code>shipments_awb_unique</code> is one.", "Upper-case with <code>Locale.ROOT</code>, then compare the column as stored."],
    "challenge/TrackByAwbChallengeTest.java", ["challenge/solution/ShipmentController.java", "challenge/solution/ShipmentSearch.java"]) + challenge(2, "Counts from the index alone", "Go deeper", 30,
    "Add <code>GET /shipments/summary?phone&amp;from&amp;to</code>: shipments per status. The seller's month must be counted with an <code>Index Only Scan</code>.",
    "both tests in <code>StatusSummaryChallengeTest</code> pass. After a stale build, run <code>./mvnw clean test</code>: a deleted migration can linger in <code>target/</code>.",
    ["The count needs <code>status</code>; put it in the index's leaf entries with <code>INCLUDE (status)</code>, in a new migration.",
     "Replace the index under the same name, so nothing that refers to it changes.",
     "An index-only scan also needs the visibility map: the test runs <code>VACUUM</code> first, as autovacuum would."],
    "challenge/StatusSummaryChallengeTest.java", ["challenge/solution/V4__covering_index.sql", "challenge/solution/ShipmentSearch.java", "challenge/solution/ShipmentController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>\"The last four digits are 3210\"</h2>
<p>Customers often remember only the end of their number. <code>phone LIKE '%3210'</code> cannot use a B-tree on <code>phone</code>. Compare: a stored <code>phone_last4</code> column with its own index (or an expression index on <code>right(phone, 4)</code>), a <code>pg_trgm</code> GIN index, and asking for the date and pin code too. How many rows does \"3210\" match in 30 million? Which option still needs another filter to be useful?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, indexes"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old query and its plan.</li>
<li>Store phones in one form, guarded by a CHECK; clean input in Java.</li>
<li>Try index orders on a copy of the data, and keep the one EXPLAIN prefers.</li>
<li>Measure the write cost, and keep only indexes a query uses.</li>
</ol>
<h2>Column order, the rule</h2>
<p>Columns compared with <code>=</code> first, then at most one range column, then columns only needed for order. A B-tree is sorted by its first column: the entries for one phone sit together, and within them the dates are in order. With the range column first, the matches for one phone are scattered across every date in the range.</p>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Clean in Java, store 10 digits, index <code>(phone, booked_on)</code>", "A CHECK constraint and a cleaning step.", '<span class="pill ok">Chosen</span>'],
    ["Clean in SQL with an index on <code>phone</code>", "The index is never used.", '<span class="pill bad">The trap</span>'],
    ["Index <code>(booked_on, phone)</code>", "Walks every entry in the date range.", '<span class="pill bad">Wrong order</span>'],
    ["Index <code>(phone)</code> only", "Fine for most customers; reads a busy seller's whole history.", '<span class="pill warn">Almost</span>'],
    ["Expression index on <code>right(regexp_replace(phone, …), 10)</code>", "Fixes the old query without cleaning the data; every query must repeat the exact expression.", '<span class="pill warn">A patch</span>'],
    ["Two indexes, <code>(phone)</code> and <code>(booked_on)</code>", "PostgreSQL can combine them with a bitmap AND, but reads more than one composite index would, and every insert writes both. Not measured here.", '<span class="pill warn">Not better</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>shipments_phone_shape</code>", "CHECK <code>^[6-9][0-9]{9}$</code>", "One stored form, so the column can be compared directly."],
    ["<code>shipments_awb_unique</code>", "UNIQUE (an index too)", "One shipment per airway bill; also Practice 1's lookup."],
    ["<code>shipments_awb_shape</code>, <code>shipments_status_known</code>", "CHECKs", "No impossible values from any writer."],
    ["<code>shipments_phone_booked_on</code>", "B-tree <code>(phone, booked_on)</code>", "The search, read backwards for newest first."]]) + """
""" + code(read(M + "V1__shipments.sql"), "sql") + code(read(M + "V3__search_index.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Building an index on a live table</dt><dd>Plain <code>CREATE INDEX</code> blocks writes until it finishes. On a busy table use <code>CREATE INDEX CONCURRENTLY</code>, which cannot run inside a transaction: Flyway needs that migration marked to run outside one.</dd>
<dt>Cleaning old data</dt><dd>Before the CHECK constraint, existing rows must be cleaned in batches; add the constraint <code>NOT VALID</code>, then <code>VALIDATE CONSTRAINT</code>, to avoid a long lock.</dd>
<dt>Unused indexes</dt><dd><code>pg_stat_user_indexes.idx_scan</code> shows how often each index is used. An index at 0 for months still costs every insert.</dd>
<dt>Phone numbers are personal data</dt><dd>Support search should be logged and limited to support staff.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("How do you check whether a query uses an index?", "EXPLAIN shows the plan; EXPLAIN (ANALYZE, BUFFERS) runs it and shows the rows and pages each step really touched."),
    ("Why would PostgreSQL ignore an index?", "The query compares a function of the column, a cast or a different type; most rows match anyway; the table is tiny; or the statistics are stale."),
    ("How do you order columns in a composite index?", "Equality columns first, then one range column, then columns only used for ordering; the index is sorted by the first column."),
    ("What does an index cost?", "Space, and work on every insert and on updates of its columns: each one is written and WAL-logged too."),
    ("Index scan, bitmap scan, index-only scan?", "Index scan: walk the index, visit each row. Bitmap: collect row locations, then read pages in order. Index-only: every needed column is in the index and the pages are all-visible, so the table is not read."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You read each saved plan line by line."],
    ["EXPLAIN", "Can tell a sequential scan from an index scan.", "Uses BUFFERS to compare plans."],
    ["Index design", "Equality first, range second.", "Knows when phone-only is enough."],
    ["Write cost", "Knows each index slows inserts.", "Has measured it."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This station has no flawed version to review. Use this checklist on any new index or search query:</p>
<ul class="rules">
<li>Is there an EXPLAIN (ANALYZE, BUFFERS) of the query, on realistic data, in the pull request?</li>
<li>Does the <code>WHERE</code> compare columns as stored, with no function or cast around them?</li>
<li>Are equality columns before the range column in the index?</li>
<li>Which query uses each index, and is that worth its write cost?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
