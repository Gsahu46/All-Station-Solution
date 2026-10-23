"""Station 093 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 93,
    "stack": "Spring Boot 4.1.1 · Java 25 · StreamingResponseBody · JDBC fetch size and cursors · CSV escaping and formula injection · Spring Security 7 · PostgreSQL 17 · Testcontainers",
    "simulation": "The sellers, orders and buyers' cities are demo data, not Kartwala's. The link in the attacker's product name points at an example address.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/kartwala/export/"
T = "src/test/java/com/kartwala/export/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("CSV", "A text file of rows, cells separated by commas, that spreadsheets open.", "A table written on lined paper.", "<code>orders-....csv</code>"),
    ("Streaming", "Sending the file while it is being made, row by row.", "Serving food as it comes off the stove.", "<code>StreamingResponseBody</code>"),
    ("Fetch size", "How many rows the database hands over at a time.", "Bringing plates out ten at a time.", "1,000"),
    ("Formula injection", "A cell starting with = that a spreadsheet runs as a formula.", "A note in the order book that says \"call this number\".", "<code>=HYPERLINK(...)</code>"),
    ("Content-Disposition", "A header that tells the browser to save the answer as a file, with a name.", "The label on a parcel.", "<code>attachment; filename=...</code>"),
    ("Byte order mark", "Three bytes at the start that tell Excel the file is UTF-8.", "A language sticker on a book.", "<code>EF BB BF</code>"),
]
STORY = [
    ("A year of orders", "A big seller exported a year of orders. The old code read every order into a list, built the whole file as one String, and only then sent it. The server ran out of memory."),
    ("A product that clicks itself", "Another seller opened an export in Excel. One product name, typed by an attacker, was =HYPERLINK(...). Excel showed it as a link, \"Click for refund\", that sent data to the attacker's site."),
    ("The fix", "The export is written row by row while the database hands rows over a thousand at a time, so memory stays flat. Any cell that would start a formula gets a leading apostrophe, and cells are quoted the CSV way."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A file you hand to someone's spreadsheet is code they will run. Write it row by row, and never let a cell start a formula.</p>

<h2>What are we building?</h2>
<p>A CSV export of a seller's own orders between two dates, streamed from the database, safe to open in Excel.</p>

<h2>An everyday analogy</h2>
<p>A kitchen that plates each dish as it is cooked instead of waiting for all 500, and checks that no customer's note on an order is an instruction to the cashier.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Check</strong> the dates (at most a year) and who is asking: the seller comes from the sign-in.</li>
<li><strong>Record</strong> the export in a log, then start the answer: a CSV attachment.</li>
<li><strong>Stream</strong>: the database hands over 1,000 rows at a time; each row is written and forgotten.</li>
<li><strong>Escape</strong> each text cell: a leading apostrophe for formula characters, quotes for commas and quotes.</li>
</ol>

<details class="qa check"><summary>Check yourself: is putting a cell like =1+1 in quotes enough to stop the formula?</summary><p>No. Quotes are CSV syntax: the spreadsheet removes them and still sees =1+1. A leading apostrophe makes it text. That is the Review tab's second finding.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No background jobs.</strong> The export runs in the request; challenge 3 moves big ones to a job.</li>
<li><strong>No Excel files.</strong> Only CSV.</li>
<li><strong>No buyer names.</strong> Only cities, to keep personal data small.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Kartwala</strong> (a fictional marketplace): exporting a year of orders runs out of memory, and a product named <code>=HYPERLINK(...)</code> ran a formula in Excel.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo users: sellers neha.store (seller 1) and arun.mart (seller 2), support sam.help; password: the name before the dot plus <code>-demo-pass</code>. Demo rule: at most 366 days, both ends included; days are IST days.</p>
<ol class="gwt">
<li><b>Given</b> a valid range, <b>then</b> <code>200</code>, a UTF-8 CSV attachment with a header and the seller's orders, oldest first.</li>
<li><b>Given</b> a cell starting with = + - @, a tab or CR, <b>then</b> it starts with ' in the file; commas and quotes are quoted the RFC 4180 way.</li>
<li><b>Given</b> a million orders, <b>then</b> the first lines arrive about as fast as an empty export's.</li>
<li><b>Given</b> another seller's orders, <b>then</b> never in the file, whatever the request adds; support <code>403</code>; no sign-in <code>401</code>.</li>
<li><b>Given</b> a range the wrong way round, over 366 days or not a date, <b>then</b> <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>No list of all rows, no whole file in memory.</li>
<li>Every export recorded before it starts.</li>
<li>The range rule also in the database.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Stream a response with <code>StreamingResponseBody</code> and stream rows from PostgreSQL with a fetch size.</li>
<li>Escape CSV cells for both CSV and spreadsheets.</li>
<li>Name and type a download with <code>Content-Disposition</code> and a charset.</li>
<li>Prove streaming with a test that fails when rows are loaded first.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/seller/orders/export?from=YYYY-MM-DD&amp;to=YYYY-MM-DD</code>", "The signed-in seller's orders on those IST days, as a CSV attachment."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "The CSV (the header alone if there are no orders)"],
    ['<span class="pill warn">400</span>', "A date that is not a date; to before from; more than 366 days"],
    ['<span class="pill warn">401</span>', "No sign-in, or a wrong password"],
    ['<span class="pill warn">403</span>', "Not a seller (support)"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. <code>Date</code>, connection and standard security headers are left out; the byte order mark at the start of each CSV is not shown here (its bytes, read by <code>od</code>: <code>""" + read("docs/captures/bom.txt").strip() + """</code>).</p>
""" + examples([
    ("01-neha-exports-2026", "Case 1: Neha exports 2026", "<b>Why:</b> her five orders, oldest first. The comma, the quotes and the Hindi name are quoted; the formula, the + and the @ start with '."),
    ("02-arun-exports-2026", "Case 2: Arun exports 2026", "<b>Why:</b> only his order: the seller comes from the sign-in."),
    ("03-one-indian-day", "Case 3: 30 June 2026", "<b>Why:</b> 18:29 IST is that day; KW-1004 at 09:00 IST on 1 July is not."),
    ("04-more-than-a-year", "Case 4: 367 days", "<b>Why:</b> <code>400</code>."),
    ("05-not-a-date", "Case 5: month 13", "<b>Why:</b> <code>400</code>."),
    ("06-support-may-not-export", "Case 6: support", "<b>Why:</b> <code>403</code>: buyers' data is for the seller."),
    ("07-no-sign-in", "Case 7: no sign-in", "<b>Why:</b> <code>401</code>."),
]) + """
<h2>The export log afterwards</h2>
<p class="muted">Seller, from, to. Refused requests left no entry; the last line is the export <code>docs/capture.sh</code> ran to read the byte order mark.</p>
""" + code(read("docs/captures/export-log.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A year of orders", "Attachment, charset, BOM, every line exact", "<code>aYearOfOrdersAsAnAttachmentInIstDaysOldestFirst</code>"],
    ["One IST day; a month with no orders", "That day only; the header alone", "<code>theDaysAreIndianDays</code>"],
    ["Wrong way round, 367 days, month 13; 366 days; a leap year", "<code>400</code>; <code>200</code>", "<code>badRangesAre400</code>"],
    ["Signs, tabs, line breaks, empty cells, = inside text", "Escaped only where needed", "<code>cellsAreEscapedTheSpreadsheetWay</code>"],
    ["The old way", "A formula cell, a split cell", "<code>theOldWayHeldEverythingAndPassedTheFormulaOn</code>"],
    ["The API on the same orders", "Neutralised and quoted", "<code>theApiNeutralisesFormulasAndQuotesCells</code>"],
    ["A million orders", "First lines about as fast as an empty export", "<code>theFirstLinesArriveLongBeforeAllRowsCouldHaveBeenRead</code>"],
    ["No sign-in, a wrong password, support", "<code>401</code>, <code>401</code>, <code>403</code>, nothing logged", "<code>withoutASignInIt401sAndSupportMayNotExport</code>"],
    ["Another seller's orders, also with ?sellerId=1", "Never in the file", "<code>aSellerExportsOnlyTheirOwnOrdersWhateverTheyAddToTheRequest</code>"],
    ["SQL and paths in the dates", "<code>400</code>", "<code>maliciousDatesAreRefused</code>"],
    ["Rules written by plain SQL", "Refused by named constraints", "<code>orderAndExportRulesHoldWithoutJava</code>"],
    ["The log cannot be written", "No export", "<code>anExportThatCannotBeLoggedDoesNotStart</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Building the whole file in memory, and not escaping cells that start with '='.</p>
<ul>
<li><strong>The old way.</strong> The test reads every order into a list and joins the cells with commas into one String. The file has a line starting <code>KW-1003,=HYPERLINK(</code>, a formula, and \"Cotton kurta, blue\" splits into two cells.</li>
<li><strong>The API.</strong> The same orders: the formula starts with <code>'</code> and is quoted, and the kurta's name is one cell.</li>
<li><strong>Memory.</strong> <code>StreamingExportTest</code> exports a million orders on a real port: the first lines arrive about as fast as an empty export, long before every row could have been read.</li>
</ul>
<p>While building, each part was undone once: no fetch size turned 1 test red; no transaction 1; no formula guard 3; no quoting 2; no byte order mark 3; UTC days 4; any seller's orders 3; no range check 1; no export log 2.</p>
</div>
""" + code(read(T + "FormulaAndMemoryTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SecurityConfig.java", dwn("Who may export.", "HTTP Basic; sellers only; everything else refused.", "Support or anyone downloading buyers' data.")),
    (J + "ExportController.java", dwn("The endpoint.",
        "Checks the range, takes the seller from the sign-in, records the export, and returns a <code>StreamingResponseBody</code> with a CSV type, a charset and a file name.",
        "A request that names another seller's id.")),
    (J + "OrderExport.java", dwn("Reading and writing, row by row.",
        "A read-only transaction, so the PostgreSQL driver uses a cursor with the fetch size; each row goes straight to the writer.",
        "A year of orders in memory.",
        "<ul><li>The PostgreSQL driver uses a cursor only inside a transaction and with a fetch size. Without either, it reads every row before handing over the first: about 2 s instead of about 50 ms for a million rows here. Found while building.</li><li>A byte order mark first, so Excel reads UTF-8.</li><li>If the client goes away, the write fails and reading stops.</li></ul>")),
    (J + "Csv.java", dwn("One cell, safe for CSV and for spreadsheets.",
        "A leading <code>'</code> for = + - @ tab CR, then RFC 4180 quoting.",
        "Formulas run on the seller's computer; cells split at commas.")),
    (J + "ProblemResponses.java", "<p><code>401</code> and <code>403</code> in the same problem shape as other errors.</p>"),
    (M + "V1__orders_and_export_log.sql", dwn("Orders and the export log.", "Named constraints; the range rule in the log; an index on seller and time.", "Bad rows, or a log entry for an export the API would refuse.")),
    (M + "V2__demo_orders.sql", "<p>Six orders, some with names a real seller types and some an attacker would.</p>"),
    ("src/main/resources/application.yaml", "<p><code>spring.jdbc.template.fetch-size: 1000</code>.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "ExportApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/093-order-export-to-csv/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/export/
│   ├── SecurityConfig.java   ├── ExportController.java   ├── OrderExport.java   ├── Csv.java
│   └── ProblemResponses.java   └── ExportApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__orders_and_export_log.sql, V2__demo_orders.sql
├── src/test/java/com/kartwala/export/   (see Tests)
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
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature. The full test run takes longer than most stations: one test exports a million orders.</p>
<h2>Try it yourself</h2>
<p>Download Neha's 2026 orders and open the file in a spreadsheet:</p>
""" + code("""curl -u neha.store:neha-demo-pass -o orders.csv 'http://localhost:8080/seller/orders/export?from=2026-01-01&to=2026-12-31'""", "bash") + """
<p>The file is case 1. Product KW-1003 shows as text starting <code>'=HYPERLINK</code>, not as a link, and the Hindi name reads correctly.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Memory grows with the export's size", "Rows read all at once: no fetch size, or no transaction (PostgreSQL's driver then reads everything).", "Set <code>spring.jdbc.template.fetch-size</code> and read inside a transaction."],
    ["The first row takes seconds even when streaming", "The database sorts every row before the first: the plan does not follow an index, often because statistics are missing.", "<code>ANALYZE</code> (autovacuum does it in time); check with <code>EXPLAIN</code>."],
    ["Excel shows garbled Hindi", "No byte order mark: Excel guesses another encoding.", "Write <code>EF BB BF</code> first."],
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>ExportContractTest</code> ({cnt('ExportContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>FormulaAndMemoryTrapTest</code> ({cnt('FormulaAndMemoryTrapTest')}), <code>StreamingExportTest</code> ({cnt('StreamingExportTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>ExportDatabaseTest</code> ({cnt('ExportDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, one user accessing another user's data, malicious input", f"<code>ExportSecurityTest</code> ({cnt('ExportSecurityTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">How to prove streaming took three tries. A check that PostgreSQL still had the query open could not tell streaming from loading everything (the transaction is open in both). Timing a million rows works: the first lines arrive about as fast as an empty export, while reading every row takes seconds, so loading them first could not be that fast. And at first even the streaming version was slow: on a fresh table without statistics, PostgreSQL sorted the whole year before the first row; after <code>ANALYZE</code> it reads the index in order. Found while building.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "FormulaAndMemoryTrapTest.java", "<p>Written first: the old list-and-join way against the API.</p>"),
    (T + "StreamingExportTest.java", "<p>A million orders on a real port: first lines against reading every row.</p>"),
    (T + "ExportContractTest.java", "<p>The file, line by line; IST days; ranges; cell escaping.</p>"),
    (T + "ExportSecurityTest.java", "<p>401, 403, another seller's orders, malicious dates.</p>"),
    (T + "ExportDatabaseTest.java", "<p>Named constraints with plain SQL; an export that cannot be logged.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the demo orders before each test; the async helper that reads a streamed answer.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/kartwala/export/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=StatusFilterChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Only shipped orders", "Beginner-friendly", 20,
    "An optional <code>?status=PLACED|SHIPPED|DELIVERED|CANCELLED</code> exports only orders in that state; any other value is <code>400</code>.",
    "both tests in <code>StatusFilterChallengeTest</code> pass.",
    ["<code>@Pattern</code> on an optional request parameter.",
     "One query for both cases: <code>(CAST(? AS text) IS NULL OR status = ?)</code>."],
    "challenge/StatusFilterChallengeTest.java", ["challenge/solution/ExportController.java", "challenge/solution/OrderExport.java"]) + challenge(2, "Export history", "Go deeper", 30,
    "<code>GET /seller/exports</code>: the seller's own exports, newest first, each with <code>rowsSent</code>. The count is known only when the stream ends, so a V3 migration adds <code>rows_sent</code>, filled in after the last row.",
    "both tests in <code>ExportHistoryChallengeTest</code> pass.",
    ["Keep the log entry's id from the insert and update it after the last row is written.",
     "An export cut off by the client leaves <code>rows_sent</code> empty: that is information too."],
    "challenge/ExportHistoryChallengeTest.java", ["challenge/solution/OrderExport.java", "challenge/solution/ExportController.java", "challenge/solution/SecurityConfig.java", "challenge/solution/V3__rows_sent.sql"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Exports as jobs</h2>
<p>A seller with five million orders a year asks for an export. Even streamed, the request runs for minutes, through load balancers that cut it at 60 seconds. Design it as a job: <code>202</code> with a job id, the file written to object storage, a time-limited download link, and an email when ready. What still streams, and where?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old list-and-join way.</li>
<li>Write <code>Csv.text</code> with its rules and tests.</li>
<li>Stream: <code>StreamingResponseBody</code>, a read-only transaction, a fetch size, a writer per row.</li>
<li>Prove it with a test that fails when rows are loaded first; then lock down who may export what.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Stream rows from a cursor to the response", "The connection is held while the file downloads.", '<span class="pill ok">Chosen</span>'],
    ["Load all rows, build the file, send it", "Memory grows with the export; nothing is sent until the end.", '<span class="pill bad">The trap</span>'],
    ["Quote formula cells", "Quotes are CSV syntax; the formula still runs.", '<span class="pill bad">Review finding</span>'],
    ["Page through with LIMIT/OFFSET", "Many queries; later pages get slower; rows can move between pages.", '<span class="pill warn">Worse than a cursor</span>'],
    ["A background job to object storage", "More parts; no time limit on the request.", '<span class="pill warn">For huge exports</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>orders_seller_time</code>", "Index (seller, placed_at)", "The export reads one seller's range in time order."],
    ["<code>export_log_range</code>", "CHECK", "At most 366 days, in the right order, for any writer."],
    ["<code>orders_ref_once_per_seller</code>", "UNIQUE", "One order ref per seller."],
    ["<code>orders_quantity_positive</code>, <code>orders_amount_positive</code>, <code>orders_status</code>", "CHECKs", "Rows an export can trust."]]) + """
<p><strong>Transaction boundaries:</strong> the log entry is committed first. The rows are read in one read-only transaction, open for as long as the file takes to write.</p>
""" + code(read(M + "V1__orders_and_export_log.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Connections</dt><dd>A streaming export holds a database connection until the download ends; a slow client holds it longer. Limit concurrent exports per seller and size the pool for them.</dd>
<dt>Time limits</dt><dd>Load balancers and proxies cut long responses (60 seconds is common). Beyond that, use a job (challenge 3).</dd>
<dt>Personal data</dt><dd>Exports carry buyers' data out of your systems: log them, limit them, and keep columns to what the seller needs.</dd>
<dt>Async requests</dt><dd><code>StreamingResponseBody</code> runs on another thread; set <code>spring.mvc.async.request-timeout</code> to something an export can finish in.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("How do you export a million rows without running out of memory?", "Stream: write the response while reading rows from a database cursor, a few thousand at a time, keeping nothing."),
    ("What does PostgreSQL's JDBC driver need to stream rows?", "A fetch size and a transaction (autocommit off). Otherwise it reads the whole result before returning the first row."),
    ("What is CSV injection?", "Text that a spreadsheet runs as a formula because it starts with =, +, - or @. Prefix such cells with an apostrophe."),
    ("Isn't quoting the cell enough?", "No: quotes are part of CSV, not of the cell. The spreadsheet removes them and runs the formula."),
    ("How do you test that a response streams?", "Make the data big enough that loading it takes seconds, and check that the first lines arrive long before that."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Streaming", "StreamingResponseBody.", "Rows streamed from the database too, proven by a test."],
    ["Cells", "Commas and quotes handled.", "Formula characters neutralised, and you can explain why quoting is not enough."],
    ["Access", "Sellers only.", "The seller from the sign-in, exports logged."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("Rows loaded into a list before writing",
     "\"The connection goes back to the pool sooner\": and a year of orders sits in memory before the first byte is sent. The export works until a big seller uses it.",
     "<code>theFirstLinesArriveLongBeforeAllRowsCouldHaveBeenRead</code> fails."),
    ("Formula cells only quoted",
     "\"Quoted, so the spreadsheet keeps it as text\": quotes belong to CSV, not to the cell. The spreadsheet removes them and runs <code>=HYPERLINK(...)</code>. And + - @ are not handled at all.",
     "<code>theApiNeutralisesFormulasAndQuotesCells</code>, <code>cellsAreEscapedTheSpreadsheetWay</code> and <code>aYearOfOrdersAsAnAttachmentInIstDaysOldestFirst</code> fail."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate simplifies the export: rows are read into a list first, \"so the connection goes back to the pool sooner\", and the escaping becomes one rule: quote any cell with a comma, a quote, a line break, or a leading =. Read both files and list every problem before opening the findings.</p>
<p class="path">review/OrderExport.java</p>
""" + code(read("review/OrderExport.java"), "java") + """
<p class="path">review/Csv.java</p>
""" + code(read("review/Csv.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">With six orders and no attacker, the flawed export is correct. Its problems need a big seller and a hostile product name: both normal on a marketplace.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
