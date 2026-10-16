"""Station 069 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 69,
    "stack": "Spring Boot 4.1.1 · Java 25 · JdbcClient · effective dating · timestamptz and time zones · PostgreSQL 17 EXCLUDE with tstzrange · Testcontainers",
    "simulation": "Products and prices are demo data, not Kartwala's. A price is a record; no order or payment is made.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/kartwala/prices/"
T = "src/test/java/com/kartwala/prices/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Effective dating", "Each value is stored with the time it is valid from and to.", "A rate card with \"valid until\" printed on it.", "<code>valid_from</code>, <code>valid_to</code>"),
    ("Half-open window", "Start included, end excluded: [from, to).", "A sale until midnight ends as midnight starts.", "<code>tstzrange(…, '[)')</code>"),
    ("Price as of", "The price that was, is or will be valid at a given instant.", "\"What did it cost at 9 pm yesterday?\"", "<code>GET …/price?at=…</code>"),
    ("Instant", "One moment, the same everywhere on Earth.", "The moment a rocket launches.", "<code>timestamptz</code>"),
    ("Local time", "A wall-clock reading in some place.", "\"Midnight\" in Delhi is 18:30 in London.", "what sellers type: <code>2026-11-08T00:00</code>"),
    ("Exclusion constraint", "No two rows may conflict, here: same product, overlapping windows.", "One price tag per product at any moment.", "<code>prices_no_overlap</code>"),
]
STORY = [
    ("Diwali pricing", "A seller sets Rangoli Colours to Rs 149 from midnight on 8 November."),
    ("Noon, not midnight", "A job checked for due price changes twice a day and overwrote the price when it ran: the sale went live at noon. The times had no time zone either, so a server on UTC read \"midnight\" as 05:30 in India. And when a flash sale was added inside the Diwali sale, both applied, and checkout took whichever the database returned first."),
    ("The fix", "Store every price with its window as instants. \"The price now\" is just the window containing now: nothing has to run at midnight. The database refuses two windows that overlap."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Do not change data at a scheduled time. Store data that is valid from a time, and read it as of now.</p>

<h2>What are we building?</h2>
<p><code>POST /products/2/prices</code> schedules a price for a window; <code>GET /products/2/price?at=…</code> answers the price at any instant, past or future.</p>

<h2>An everyday analogy</h2>
<p>A railway timetable. Nobody repaints the board at midnight to show tomorrow's trains; the timetable lists each train with its days, and you read the line for today. Two trains on one platform at the same time cannot both be printed.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Read the seller's local times</strong> in the shop's zone, India, and turn them into instants.</li>
<li><strong>Make room</strong>: windows inside the new one go, the one covering its start is cut there, and the old price resumes after it.</li>
<li><strong>Insert</strong> the new window. The database checks nothing overlaps.</li>
<li><strong>Answer \"price at\"</strong> with the one window containing that instant.</li>
</ol>

<details class="qa check"><summary>Check yourself: the sale ends \"at midnight on 11 November\". What does a customer pay at exactly 00:00:00 that night?</summary><p>The normal price. Windows are half-open: the sale includes its start and excludes its end, so at midnight the next window has begun. The test checks both edges.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No checkout.</strong> Freezing the price on an order line is Practice 3.</li>
<li><strong>No currencies or taxes.</strong> One price in paise.</li>
<li><strong>No several shop zones.</strong> One zone, set in configuration.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Kartwala</strong> (a fictional marketplace): a Diwali price set for midnight went live at noon, and two overlapping prices made checkout pick one at random.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo data: Rangoli Colours is Rs 199, Rs 149 from midnight 8 November to midnight 11 November, then Rs 199 again. Tests fix \"now\" at 16 October 2026, 11:30 in India.</p>
<ol class="gwt">
<li><b>Given</b> 23:59:59 on 7 November in India, <b>then</b> Rs 199; at 00:00:00 on 8 November, Rs 149, asked in IST or in UTC.</li>
<li><b>Given</b> 00:00 on 11 November, <b>then</b> Rs 199 again.</li>
<li><b>Given</b> a past instant, <b>then</b> the price that was valid then.</li>
<li><b>Given</b> a sale inside the base price, <b>then</b> three windows: base, sale, base.</li>
<li><b>Given</b> a change in the past, <b>then</b> <code>422</code>; an end before the start, <code>400</code>; an unknown product, <code>404</code>.</li>
<li><b>Given</b> an overlapping window written directly, <b>then</b> the database refuses it.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Prices are never overwritten; each has a window.</li>
<li>Windows are half-open and stored as instants (<code>timestamptz</code>).</li>
<li>Seller times are read in the shop's zone; questions may use any offset.</li>
<li>At most one price per product at any instant, enforced by the database.</li>
<li>One schedule change per product at a time.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Model effective-dated data with half-open windows.</li>
<li>Write \"as of\" queries.</li>
<li>Handle local times, zones and instants without surprises.</li>
<li>Enforce \"no overlap\" with an exclusion constraint.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/products/{id}/prices</code>", "<code>{pricePaise, from, to?}</code> in shop time (no offset); <code>201</code> with the product's schedule."],
    ["<code>GET</code>", "<code>/products/{id}/price?at=…</code>", "The price at an instant (ISO, with offset); now if absent."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span> / <span class="pill ok">201</span>', "A price / the new schedule"],
    ['<span class="pill warn">400</span>', "End not after start; price outside Rs 1 to Rs 1 lakh; a malformed time"],
    ['<span class="pill warn">404</span>', "No such product, or no price at that instant"],
    ['<span class="pill warn">409</span>', "The schedule changed under the request (an overlap from another writer); not reproduced by a test"],
    ['<span class="pill warn">422</span>', "A window starting in the past"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, on the real clock. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-one-second-before-diwali", "Case 1: 23:59:59 on 7 November, India", "<b>Why:</b> still Rs 199."),
    ("02-midnight-in-india", "Case 2: 00:00 on 8 November, India", "<b>Why:</b> the sale, exactly at midnight."),
    ("03-the-same-instant-in-utc", "Case 3: 18:30 on 7 November, UTC", "<b>Why:</b> the same instant as case 2, so the same price; answered in shop time."),
    ("04-a-sale-for-the-lamps", "Case 4: a sale for the Diya Lamp Set", "<b>Why:</b> the open-ended base price is cut in two around the sale."),
    ("05-changing-a-price-in-the-past", "Case 5: a new price from 1 March", "<b>Why:</b> <code>422</code>: history does not change."),
]) + """
<h2>Midnight, with and without a zone</h2>
<p class="muted">Asked in <code>psql</code> with the session in UTC, as on many servers (<code>docs/captures/midnight.txt</code>).</p>
""" + code(read("docs/captures/midnight.txt").rstrip(), "text") + """
<p>The value without a zone stays \"midnight\" and is compared with whatever the server's clock says; the instant is 18:30 UTC on the 7th.</p>"""

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Now", "The current window, in shop time", "<code>thePriceNow</code>"],
    ["One second before, at, and at the end of the sale", "Half-open: in at the start, out at the end", "<code>theSaleStartsAtMidnightInIndiaWhateverOffsetTheQuestionUses</code>"],
    ["A past instant", "The price then", "<code>pastPricesAreKept</code>"],
    ["A sale inside an open-ended price", "Base, sale, base", "<code>aSaleCutsTheBasePriceInTwo</code>"],
    ["A flash sale inside a sale", "Five windows", "<code>aFlashSaleInsideTheSale</code>"],
    ["A window covering a whole sale", "The sale goes", "<code>aWindowCoveringTheWholeSaleReplacesIt</code>"],
    ["A new price from then on", "Later windows replaced", "<code>aNewPriceFromThenOnReplacesEverythingAfter</code>"],
    ["Past, empty window, bad price, unknown product, no price yet, bad time", "<code>422</code>, <code>400</code>, <code>404</code>", "<code>thePastCannotChangeAndOtherMistakes</code>"],
    ["Overlap, orphan, bad price, backwards window written directly; windows touching", "Refused; allowed", "<code>PriceDatabaseTest</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Overwriting the price at a scheduled time instead of storing dated prices.</p>
<p>The old design kept one current price and a table of planned changes with <code>timestamp</code> (no zone) and no rule against overlaps. A job applied them when it ran, and lost each old price as it did. The test recreates the planned-changes table and reads it as the UTC server did:</p>
<ul>
<li><strong>Midnight in the wrong place.</strong> At 00:30 in India on 8 November, the old query finds no sale; at 05:30 in India (midnight UTC) it does. The new API answers Rs 149 at 00:30.</li>
<li><strong>Two prices at once.</strong> A flash sale added inside the Diwali sale: at noon on the 9th, both rows match. Checkout's <code>LIMIT 1</code> took one; which, depended on the plan.</li>
<li><strong>The real table refuses the overlap</strong>: <code>prices_no_overlap</code>.</li>
</ul>
<p>While building, each fix was undone once: reading seller times as UTC turned 3 tests red; dropping the exclusion constraint 3; not resuming the old price after a window 2; a closed end (<code>valid_to &gt;= at</code>) 1; not shifting a window that starts inside 1; no past check 1.</p>
</div>
""" + code(read(T + "OverwrittenPriceTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "PriceController.java", dwn("Takes local times for schedules and instants for questions.",
        "Sellers think in shop time; clients asking \"price at\" may be anywhere, so they send an offset.",
        "A bare \"00:00\" read in the server's zone.")),
    (J + "PriceSchedule.java", dwn("Answers \"price at\" and fits a new window into the schedule.",
        "One transaction, the product row locked, neighbours trimmed or continued, then the insert.",
        "Overlaps refused by the database instead of fitted, or prices overwritten.",
        "<ul><li>Instants are bound as <code>OffsetDateTime</code> in UTC: the database session's zone never matters.</li><li>The shop zone comes from <code>shop.zone</code>, and <code>Clock</code> is a bean so tests fix \"now\".</li></ul>")),
    (M + "V1__prices.sql", dwn("Products, dated prices, and the constraints.",
        "<code>prices_no_overlap</code> makes \"one price at any instant\" true for every writer.",
        "Two matching rows, and a checkout that picks one.")),
    (M + "V2__demo_prices.sql", "<p>Three products; the Diwali sale on Rangoli Colours.</p>"),
    ("src/main/resources/application.yaml", "<p>The shop's zone and whole paise.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "PricesApplication.java", "<p>Entry point and the clock.</p>"),
]
tree = """stations/069-scheduled-price-changes/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/prices/
│   ├── PriceController.java   ├── PriceSchedule.java   └── PricesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__prices.sql, V2__demo_prices.sql
├── src/test/java/com/kartwala/prices/   (see Tests)
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
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Ask for the price at instants around the sale; <code>--data-urlencode</code> keeps the <code>+</code> of the offset intact:</p>
""" + code("""curl -G http://localhost:8080/products/2/price --data-urlencode 'at=2026-11-08T00:00:00+05:30'
curl -G http://localhost:8080/products/2/price --data-urlencode 'at=2026-11-11T00:00:00+05:30'""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>400</code> for <code>at=2026-11-08T00:00:00+05:30</code> in a browser", "An unencoded <code>+</code> in a URL is a space.", "Encode it as <code>%2B</code>, or use <code>Z</code> times."],
    ["<code>conflicting key value violates exclusion constraint \"prices_no_overlap\"</code>", "Two windows for one product overlap.", "Fit the window into the schedule, as <code>PriceSchedule.set</code> does."],
    ["<code>data type bigint has no default operator class for access method \"gist\"</code>", "<code>btree_gist</code> is not installed.", "The migration creates it; a managed database may need it allowed."],
    ["Prices change at 05:30 instead of midnight", "Times stored or compared without a zone, on a UTC server.", "<code>timestamptz</code>, and read local times in the shop's zone."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>PriceContractTest</code> ({cnt('PriceContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>OverwrittenPriceTrapTest</code> ({cnt('OverwrittenPriceTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>PriceDatabaseTest</code> ({cnt('PriceDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">Not tested: two schedule changes for one product at the same moment. The product row lock makes them take turns, and the exclusion constraint is the backstop (answered <code>409</code>); no parallel test proves it here.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "OverwrittenPriceTrapTest.java", "<p>Written first: the old table's midnight, its overlaps, and the refusal.</p>"),
    (T + "PriceDatabaseTest.java", "<p>Named constraints, touching windows, and a rolled-back batch.</p>"),
    (T + "PriceContractTest.java", "<p>Both endpoints through HTTP, with \"now\" fixed.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the fixed clock and the demo schedule before each test.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/kartwala/prices/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=ScheduleChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Show the schedule", "Beginner-friendly", 15,
    "Add <code>GET /products/{id}/prices</code>: every window, oldest first, in shop time.",
    "the test in <code>ScheduleChallengeTest</code> passes.",
    ["<code>PriceSchedule.schedule</code> already builds it.", "Check the product exists first, for the <code>404</code>."],
    "challenge/ScheduleChallengeTest.java", ["challenge/solution/PriceSchedule.java", "challenge/solution/PriceController.java"]) + challenge(2, "Cancel a sale", "Go deeper", 30,
    "Add <code>DELETE /products/{id}/prices?from=…</code>: remove the future window starting then; the price before it carries on, and equal neighbours become one window.",
    "both tests in <code>CancelSaleChallengeTest</code> pass.",
    ["Find the windows before (ending at its start) and after (starting at its end).",
     "If they have the same price, delete the one after and stretch the one before over both; otherwise stretch the one before over the gap.",
     "A window that has started is history: <code>422</code>."],
    "challenge/CancelSaleChallengeTest.java", ["challenge/solution/PriceSchedule.java", "challenge/solution/PriceController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>The price on the order, and shops in other zones</h2>
<p>A customer adds a lamp to the cart at 23:58 on 7 November and pays at 00:02. Which price applies, and where is it stored so a refund next month pays back the right amount? Then: Kartwala opens in Dubai (+04:00). Is the Diwali sale \"midnight in India\" everywhere, or midnight in each country? What changes in <code>shop.zone</code>, in the API, and in the data?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the zone-less, overlapping old table.</li>
<li>Store dated prices as half-open <code>timestamptz</code> windows, with an exclusion constraint.</li>
<li>Write the \"as of\" query, and convert local times at the edge, in the shop's zone.</li>
<li>Fit new windows into the schedule inside one transaction, with the product row locked.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Dated windows + exclusion constraint + \"as of\" reads", "Writes must fit windows; reads are one indexed query.", '<span class="pill ok">Chosen</span>'],
    ["Overwrite the price from a scheduled job", "Late changes; history lost; a missed run is a wrong price.", '<span class="pill bad">The trap</span>'],
    ["Dated rows with only a start (\"from\"), the latest start wins", "No overlaps possible; ending a sale means inserting the old price again.", '<span class="pill warn">Simpler, less expressive</span>'],
    ["A base price plus a separate promotions table with priorities", "Clear for marketing; checkout must resolve priorities.", '<span class="pill warn">For many overlapping offers</span>'],
    ["Times as <code>timestamp</code> plus a zone column", "Correct if every query applies the zone.", '<span class="pill warn">Easy to get wrong</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>prices_no_overlap</code>", "EXCLUDE USING gist (product_id WITH =, tstzrange(valid_from, valid_to, '[)') WITH &amp;&amp;)", "One price per product at any instant; its GiST index can also serve the product lookup."],
    ["<code>prices_window_order</code>", "CHECK valid_to IS NULL OR valid_to &gt; valid_from", "No empty or backwards windows."],
    ["<code>prices_price_range</code>, <code>prices_product_fk</code>", "CHECK and foreign key", "No impossible prices."],
    ["<code>valid_from</code>, <code>valid_to</code>", "<code>timestamptz</code>", "Instants, not wall-clock readings."]]) + """
<p><strong>Transaction boundary:</strong> one schedule change, from locking the product row to the last insert.</p>
""" + code(read(M + "V1__prices.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Caches</dt><dd>A cached \"current price\" must expire at the next window boundary, not after a fixed time, or the sale starts late again.</dd>
<dt>Orders</dt><dd>An order stores the price it was sold at; never recompute it from the schedule later.</dd>
<dt>Time-zone rules change</dt><dd>Store instants; convert with the JDK's zone rules at the edge, and keep the JDK updated.</dd>
<dt>Audit</dt><dd>Who scheduled each window and when is worth a column; disputes ask.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is effective dating?", "Storing each value with the period it is valid for, so the value at any instant (past, present or future) can be read without anything changing at that instant."),
    ("Why half-open windows?", "Consecutive windows can share a boundary without overlapping, and each instant belongs to exactly one."),
    ("timestamp or timestamptz?", "timestamptz for instants: it stores a moment; timestamp is a wall-clock reading with no zone, interpreted by whoever reads it."),
    ("How do you stop two prices applying at once?", "An exclusion constraint on product and overlapping time range, so the database refuses the second, from any writer."),
    ("Where should time zones be handled?", "At the edges: read the user's local time in their zone, store instants, and convert back for display."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You traced each window split by hand."],
    ["Time", "Instants stored, zones at the edge.", "Why 05:30 in India is midnight UTC."],
    ["Integrity", "The exclusion constraint.", "Why the row lock is still needed."],
    ["Design", "No overwrites.", "The price frozen on the order."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This station has no flawed version to review. Use this checklist on any scheduled change:</p>
<ul class="rules">
<li>Does anything overwrite data at a scheduled time?</li>
<li>Is every time column an instant (<code>timestamptz</code>), and in which zone are inputs read?</li>
<li>Can two values be valid at once, and who would stop it?</li>
<li>Are window ends included or excluded, and is that tested?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
