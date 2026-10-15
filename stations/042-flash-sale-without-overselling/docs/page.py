"""Station 042 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 42,
    "stack": "Spring Boot 4.1.1 · Java 25 · PostgreSQL 17 conditional UPDATE and row locks · rows-affected checks · @Transactional · JdbcClient · virtual threads · Testcontainers",
    "simulation": "Sales, products and prices are demo data, not Kartwala's. A purchase is a reservation record; no payment is taken and nothing ships.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/kartwala/flashsale/"
T = "src/test/java/com/kartwala/flashsale/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Check-then-act", "Read a value, decide in code, then change it: two steps with a gap between them.", "Two cashiers both seeing \"1 left\" on the shelf and both selling it.", "the trap"),
    ("Conditional UPDATE", "One statement that changes a row only if a condition still holds.", "\"Take one, if there is one\" said to the stockroom.", "<code>WHERE stock_left &gt; 0</code>"),
    ("Rows affected", "How many rows a statement changed; 0 means the condition was not met.", "The stockroom saying \"none left\".", "<code>taken == 0</code>"),
    ("Row lock", "While one transaction updates a row, others wanting to update it wait.", "One person at the counter at a time.", "PostgreSQL, automatically"),
    ("Transaction", "Changes that succeed or fail together.", "The phone leaves the shelf only if the bill is written.", "<code>@Transactional</code>"),
    ("Oversell", "Promising more than there is.", "Selling 517 tickets for 500 seats.", "the scenario"),
]
STORY = [
    ("500 phones, 20,000 buyers", "At noon, the sale opens. In one minute, 20,000 people tap \"Buy\"."),
    ("517 sold", "Each request read the stock, saw it was above zero, then took one. Hundreds read \"3 left\" at the same moment. 517 customers got \"Order confirmed\" for 500 phones. 17 apology emails, 17 refunds, and a trending complaint."),
    ("The fix", "Ask the database to \"take one if there is one\" in a single statement, and look at whether it did."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Never decide in code what the database can decide and change in one step.</p>

<h2>What are we building?</h2>
<p><code>POST /flash-sales/{saleId}/purchases</code> reserves one phone for a customer, or says why not: sold out, not started, ended, or already bought.</p>

<h2>An everyday analogy</h2>
<p>A token counter with one person behind it. Everyone queues and asks \"one please\"; the person hands out a token only if there is one. Nobody reads the count off a board and helps themselves.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Ask the database to take one</strong>, only if stock is above zero and the sale is open.</li>
<li><strong>Look at the answer</strong>: one row changed means a phone was taken; zero means none.</li>
<li><strong>Write the purchase</strong> in the same transaction; a second purchase by the same customer puts the phone back.</li>
<li><strong>If none was taken</strong>, say why.</li>
</ol>

<details class="qa check"><summary>Check yourself: the database has a CHECK that stock can never go below zero. Is that enough?</summary><p>It stops negative stock, but the request that hits it gets an error (a 500), not a polite \"sold out\". And a purchase written before the update would still be there without a transaction. The conditional update answers cleanly; the CHECK is the safety net.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No payment.</strong> A purchase is a reservation.</li>
<li><strong>No queue or waiting room.</strong> Challenge 3 is about 20,000 buyers a second.</li>
<li><strong>No login.</strong> The customer id in the body stands in for the signed-in customer.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Kartwala</strong> (a fictional shopping app) ran a flash sale of 500 phones; 20,000 buyers came in one minute, and the database sold 517.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> 500 buyers at once for 50 phones, <b>then</b> exactly 50 get <code>201</code>, 450 get <code>409</code>, and stock ends at 0.</li>
<li><b>Given</b> one customer tapping 20 times at once, <b>then</b> one purchase, and stock goes down by one.</li>
<li><b>Given</b> a sold-out, ended or not-yet-started sale, <b>then</b> <code>409</code> with that reason; an unknown sale, <code>404</code>.</li>
<li><b>Given</b> a customer who already bought, <b>then</b> <code>409</code> \"Already bought\", and the stock is unchanged.</li>
<li><b>Given</b> a bad customer id or an extra field such as <code>quantity</code>, <b>then</b> <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Taking stock is one conditional statement; its rows-affected count is always checked.</li>
<li>Stock update and purchase row in one transaction.</li>
<li>Constraints: stock never below 0 or above the total; one purchase per customer per sale.</li>
<li>Money in integer paise; customer ids normalised with <code>Locale.ROOT</code>.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Recognise check-then-act, and move the check into the database.</li>
<li>Write a conditional <code>UPDATE … WHERE</code> and use rows affected.</li>
<li>Keep related writes in one transaction.</li>
<li>Prove the invariant with a real concurrent test.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Body"], [
    ["<code>POST</code>", "<code>/flash-sales/{saleId}/purchases</code>", "<code>{\"customerId\": \"C-000123\"}</code>"]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "A phone was reserved for this customer"],
    ['<span class="pill warn">400</span>', "A bad customer id, a missing field, an unknown field, a non-numeric sale id"],
    ['<span class="pill warn">404</span>', "No such sale"],
    ['<span class="pill warn">409</span>', "Sold out, not started, ended, or already bought; the title says which"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against one fresh database. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-a-buyer-gets-a-phone", "Case 1: a buyer", "<b>Why:</b> one row taken, purchase written, one transaction."),
    ("02-the-same-buyer-again", "Case 2: the same buyer again", "<b>Why:</b> <code>purchases_one_per_customer</code>; the stock taken for this attempt is rolled back."),
    ("03-a-sold-out-sale", "Case 3: sale 2, stock 0", "<b>Why:</b> 0 rows affected; the sale is open but empty."),
    ("04-a-sale-that-ended", "Case 4: sale 3", "<b>Why:</b> 0 rows; outside the window."),
    ("05-a-sale-not-started", "Case 5: sale 4", "<b>Why:</b> 0 rows; not yet open."),
    ("06-no-such-sale", "Case 6: sale 99", "<b>Why:</b> <code>404</code>."),
]) + """
<h2>A rush against the running app</h2>
<p class="muted">From <code>docs/capture.sh</code>: sale 5 with 50 phones, 300 different buyers sent by <code>curl</code> with 50 requests in flight at a time, then the database queried (<code>docs/captures/rush.txt</code>).</p>
""" + code(read("docs/captures/rush.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["500 buyers, 50 phones, at once", "50 sold, 450 refused, stock 0", "<code>fiveHundredBuyersForFiftyPhones</code>"],
    ["One customer, 20 taps at once", "1 purchase, stock −1", "<code>oneCustomerTappingTwentyTimesGetsOnePhone</code>"],
    ["A second purchase by the same customer", "Refused, phone put back", "<code>aSecondPurchaseByTheSameCustomerPutsThePhoneBack</code>"],
    ["The last phone, then one more buyer", "0 rows: nothing taken", "<code>zeroRowsAffectedMeansNothingWasTaken</code>"],
    ["Negative or excess stock, bad window, unknown sale, duplicate buyer, written directly", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"],
    ["Sold out, ended, not started, unknown", "<code>409</code> with the reason; <code>404</code>", "<code>eachRefusalSaysWhy</code>"],
    ["Bad id, missing field, <code>quantity</code>, non-numeric sale", "<code>400</code>", "<code>badRequestsAre400</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Read stock, check, then update: concurrent buyers oversell.</p>
<p>The old code runs on the old tables, which have no stock constraint. 100 buyers start at the same instant for 5 phones; more than 5 get a phone, and the stock ends below zero by exactly the oversold amount. This happened in each of the 3 runs while building. The same 100 buyers against the conditional update get exactly 5. While building, each fix was undone once:</p>
<ul>
<li>Removing <code>stock_left &gt; 0</code> gave 4 errors. The CHECK constraint refused the row, so buyers got 500s instead of \"sold out\".</li>
<li>Removing <code>@Transactional</code> turned 2 tests red.</li>
<li>Ignoring rows affected turned 4 red.</li>
<li>Reading the stock and writing back the value read turned 2 red.</li>
</ul>
</div>
""" + code(read(T + "OversellTrapTest.java"), "java") + code(read(T + "OldFlashSaleStore.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "PurchaseController.java", dwn("Validates the request, buys, and explains a refusal.",
        "The reason is looked up only after nothing was taken, so the common path is one statement.",
        "Checking the stock first, which is the trap again.")),
    (J + "FlashSaleStore.java", dwn("The purchase: a conditional update and an insert, in one transaction.",
        "PostgreSQL locks the sale's row for the update, so buyers take turns on it and each sees the stock the last one left.",
        "The trap: read, decide in Java, write.",
        "<ul><li><code>update()</code> returns rows affected: 1 means a phone was taken.</li><li>A duplicate customer fails the insert; the transaction rolls the update back with it.</li></ul>")),
    (M + "V1__flash_sales_and_purchases.sql", dwn("Sales and purchases, with named constraints.",
        "Stock can never be negative or above the total, whatever the code does.",
        "A bug elsewhere sells a phone that does not exist.")),
    (M + "V2__demo_sales.sql", "<p>Four demo sales: open, sold out, ended, not started.</p>"),
    ("src/main/resources/application.yaml", "<p>The database and strict JSON.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "FlashSaleApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/042-flash-sale-without-overselling/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/flashsale/
│   ├── PurchaseController.java   ├── FlashSaleStore.java   └── FlashSaleApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__flash_sales_and_purchases.sql, V2__demo_sales.sql
├── src/test/java/com/kartwala/flashsale/   (see Tests)
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
<p>Run your own rush (macOS / Linux): 200 buyers, 40 at a time, for the 500 phones of sale 1, then count.</p>
""" + code("""seq 1 200 | xargs -P 40 -I{} sh -c 'curl -s -o /dev/null -w "%{http_code}\\n" -X POST http://localhost:8080/flash-sales/1/purchases -H "Content-Type: application/json" -d "{\\"customerId\\":\\"C-$(printf %06d {})\\"}"' | sort | uniq -c
docker compose exec postgres psql -U kartwala -d kartwala -c "SELECT stock_left FROM flash_sales WHERE id = 1\"""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>violates check constraint \"flash_sales_stock_not_negative\"</code>", "An update without <code>stock_left &gt; 0</code> reached the CHECK.", "Put the condition in the UPDATE and look at rows affected."],
    ["More purchases than stock", "Stock checked in code before updating.", "One conditional update; never read-then-write."],
    ["Stock lower than purchases", "The update ran, the insert failed, and nothing rolled back.", "Both in one <code>@Transactional</code> method."],
    ["<code>Could not find a valid Docker environment</code>", "Docker is not running.", "Start Docker, then run the tests again."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>PurchaseContractTest</code> ({cnt('PurchaseContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>OversellTrapTest</code> ({cnt('OversellTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>FlashSaleDatabaseTest</code> ({cnt('FlashSaleDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Concurrency", "A real concurrency test that proves the invariant holds", f"<code>FlashSaleConcurrencyTest</code> ({cnt('FlashSaleConcurrencyTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "OversellTrapTest.java", "<p>Written first: 100 buyers for 5 phones, old code and new.</p>"),
    (T + "FlashSaleConcurrencyTest.java", "<p>500 buyers and one impatient customer, through HTTP, released by one latch.</p>"),
    (T + "FlashSaleDatabaseTest.java", "<p>Named constraints, the rollback that puts a phone back, and zero rows affected.</p>"),
    (T + "PurchaseContractTest.java", "<p>A purchase, every refusal, and bad requests.</p>"),
    (T + "OldFlashSaleStore.java", "<p>The old code and tables, kept only in tests.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: fresh sales, a test sale of any size, and the latch helper.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/kartwala/flashsale/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=SaleStatusChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Sale status for the app", "Beginner-friendly", 20,
    "Add <code>GET /flash-sales/{id}</code> with product, stock left, stock total and a status: UPCOMING, OPEN, SOLD_OUT or ENDED, worked out by the database with its own clock.",
    "both tests in <code>SaleStatusChallengeTest</code> pass.",
    ["A SQL <code>CASE WHEN … THEN … END</code> picks the first condition that holds.",
     "Order matters: an ended sale with stock left is ENDED, not OPEN."],
    "challenge/SaleStatusChallengeTest.java", ["challenge/solution/FlashSaleStore.java", "challenge/solution/PurchaseController.java"]) + challenge(2, "Cancel and put the phone back", "Go deeper", 30,
    "Add <code>DELETE /flash-sales/{saleId}/purchases/{purchaseId}</code>: delete the purchase and add one to the stock, in one transaction. Ten cancels of the same purchase at once put back one phone.",
    "both tests in <code>CancelPurchaseChallengeTest</code> pass.",
    ["Rows affected again: only the cancel whose DELETE removed the row may add to the stock.",
     "<code>flash_sales_stock_within_total</code> would catch a double return, as an error."],
    "challenge/CancelPurchaseChallengeTest.java", ["challenge/solution/FlashSaleStore.java", "challenge/solution/PurchaseController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>20,000 buyers a second</h2>
<p>All buyers update one row, so they take turns on its lock. At 20,000 a second that row is the limit. Compare splitting the stock across 10 rows (buckets), a counter in a cache such as Valkey <code>DECR</code> with the database written after, and a queue with a waiting room. What can each oversell, and what does each customer see?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old code oversells under real concurrency.</li>
<li>Write the constraints: stock between 0 and total, one purchase per customer.</li>
<li>Write the purchase as a conditional update plus an insert, in one transaction.</li>
<li>Prove it: 500 buyers for 50 phones, through HTTP.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Conditional <code>UPDATE … WHERE stock_left &gt; 0</code> + rows affected", "Buyers queue on one row's lock.", '<span class="pill ok">Chosen</span>'],
    ["Read, check in Java, update", "Oversells under load.", '<span class="pill bad">The trap</span>'],
    ["<code>SELECT … FOR UPDATE</code>, then update", "Correct, but two statements holding the lock longer.", '<span class="pill warn">Works, slower</span>'],
    ["<code>synchronized</code> in Java", "Holds on one server only; the second server oversells.", '<span class="pill bad">Not across servers</span>'],
    ["SERIALIZABLE isolation with retries", "Correct, but many retries under a rush.", '<span class="pill warn">Heavier</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Constraints", "Why"], [
    ["<code>flash_sales</code>", "<code>flash_sales_stock_not_negative</code>, <code>flash_sales_stock_within_total</code>, <code>flash_sales_price_positive</code>, <code>flash_sales_window_order</code>", "Stock stays real whatever any code does."],
    ["<code>purchases</code>", "<code>purchases_sale_fk</code>, <code>purchases_one_per_customer (sale_id, customer_id)</code>", "One phone per customer, enforced where races cannot get past it."]]) + """
<p><strong>Transaction boundary:</strong> <code>FlashSaleStore.buy</code>, at PostgreSQL's default <code>READ COMMITTED</code>. A buyer waiting on the row lock re-checks <code>stock_left &gt; 0</code> on the row as the previous buyer committed it, which is why no stronger isolation is needed.</p>
""" + code(read(M + "V1__flash_sales_and_purchases.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Hot row</dt><dd>Every buyer updates the same row. It is correct, and each update is short, but one row has a ceiling; challenge 3 is about going past it.</dd>
<dt>Connection pool</dt><dd>Buyers waiting on the lock hold a pooled connection. Size the pool, and time out waits, so a rush cannot starve the rest of the app.</dd>
<dt>Bots</dt><dd>Flash sales attract scripts. One purchase per customer helps; rate limits and checks at login help more.</dd>
<dt>Payment</dt><dd>A real sale reserves stock, then takes payment within minutes, and releases unpaid reservations; that is a later station.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is a check-then-act race?", "Reading a value, deciding in code, then writing: between the read and the write, others read the same value and decide the same way. Fix it by making the check part of the write."),
    ("How does UPDATE … WHERE stock > 0 prevent overselling?", "The update locks the row; concurrent updates wait, then re-evaluate the WHERE on the latest committed row. When stock reaches 0, the condition fails and 0 rows are affected."),
    ("Why check rows affected?", "It is the database telling you whether the condition held. Ignoring it means acting as if you got the item when you did not."),
    ("Why does the purchase insert belong in the same transaction?", "If the insert fails (a duplicate buyer), the stock update must be undone; otherwise a phone disappears from stock with no purchase."),
    ("Would synchronized in Java fix it?", "Only on one server, and only for code that goes through that lock. Two app servers, or a script, would still race. The database is the shared point."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Concurrency", "A conditional update with rows affected.", "Why READ COMMITTED is enough here."],
    ["Transactions", "Update and insert together.", "What happens to stock when the insert fails."],
    ["Scale", "Knows the row lock serialises buyers.", "Can design past one hot row."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("Rows affected are ignored",
     "\"The UPDATE already has stock_left &gt; 0\" is true, but when it matches nothing the code still writes a purchase. Once the stock is gone, every buyer still gets a phone.",
     "<code>fiveHundredBuyersForFiftyPhones</code>, <code>oneConditionalUpdateSellsExactlyFive</code> and <code>zeroRowsAffectedMeansNothingWasTaken</code> fail: more purchases than phones."),
    ("@Transactional removed",
     "The update commits on its own. When the insert then fails, because this customer already bought, the phone is gone from stock with no purchase behind it.",
     "<code>aSecondPurchaseByTheSameCustomerPutsThePhoneBack</code> and <code>oneCustomerTappingTwentyTimesGetsOnePhone</code> fail: stock lower than purchases."),
    ("Every refusal says \"Sold out\"",
     "\"Simpler for the app\", but a customer told \"sold out\" before the sale starts does not come back at noon.",
     "<code>eachRefusalSaysWhy</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate wants a faster checkout. The update's result is not checked, because \"the WHERE already guards it\". <code>@Transactional</code> goes, to save a round trip. Every refusal says \"Sold out\". The single-buyer tests mostly pass. Read both files and list every problem before opening the findings.</p>
<p class="path">review/FlashSaleStore.java</p>
""" + code(read("review/FlashSaleStore.java"), "java") + """
<p class="path">review/PurchaseController.java</p>
""" + code(read("review/PurchaseController.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the two flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">The first flaw passes a one-buyer happy path, and the stock CHECK never fires: the update simply changes nothing, and the code does not look.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
