"""Station 039 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 39,
    "stack": "Spring Boot 4.1.1 · Java 25 · PostgreSQL 17 sequences · unique constraints · Luhn check digits · JdbcClient · virtual threads · Testcontainers",
    "simulation": "Orders and outlets are demo data, not Tiffino's. An order is a record in this app's database; no kitchen, delivery or payment is involved.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tiffino/orders/"
T = "src/test/java/com/tiffino/orders/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]
CAP1 = read("docs/captures/01-an-order.txt")
NUMBER = CAP1.split('"orderNumber":"')[1].split('"')[0]   # the number the running app issued for case 1

# ---------- Level 1: Understand ----------
TERMS = [
    ("Sequence", "A counter kept by the database, shared by every app server and kept across restarts.", "The token machine at a bank: one machine, whichever counter you go to.", "<code>order_number_seq</code>"),
    ("UUID", "A 128-bit random id: unique without a central counter, but 36 characters long.", "A serial number nobody could read out on the phone.", "<code>f47ac10b-58cc-…</code>"),
    ("Check digit", "An extra digit computed from the others, so most typos are noticed at once.", "The last digit of a card number.", "the <code>-3</code> in <code>TF-1000427-3</code>"),
    ("Luhn algorithm", "The check-digit method on payment cards (ISO/IEC 7812-1).", "A quick sum the computer does on every number you type.", "<code>OrderNumbers.checkDigit</code>"),
    ("Gap", "A number that was taken and never used, because its order failed.", "A torn-off token nobody called.", "<code>aRolledBackOrderLeavesAGapNotARepeat</code>"),
    ("Race", "Two requests reading the same \"last number\" at the same moment.", "Two clerks both writing receipt 42.", "the Review tab"),
]
STORY = [
    ("Numbers nobody can say", "Support asks for the order number; the customer reads out <code>f47ac10b-58cc-4372-a567-0e02b2c3d479</code>, letter by letter."),
    ("A shorter number, kept in memory", "The fix was a counter in the app: #1, #2, #3. After a restart it said #1 again, and the second server had its own #1. Two orders shared a number, and support refunded the wrong one."),
    ("The fix", "The database's sequence hands out numbers for every server, forever. A check digit catches a misheard digit before anyone looks the order up."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A counter that matters lives where every server and every restart can see it: the database.</p>

<h2>What are we building?</h2>
<p><code>POST /orders</code> gives every order a number like <code>""" + NUMBER + """</code>, and <code>GET /orders/by-number/{number}</code> finds it however the customer reads it out.</p>

<h2>An everyday analogy</h2>
<p>The token machine at a bank branch. However many counters are open, tokens come from one machine, so no two people hold token 42. If the counters each had their own roll of tokens, two people would.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Take the next value</strong> from the database's sequence.</li>
<li><strong>Add a check digit</strong> computed from it.</li>
<li><strong>Insert the order</strong>; a unique constraint guards the number.</li>
<li><strong>On lookup</strong>, tidy the number, check the digit, then search.</li>
</ol>

<details class="qa check"><summary>Check yourself: order numbers jump from …0427 to …0429. Is an order missing?</summary><p>Not necessarily. An order that failed after taking 0428 rolled back, and sequences never hand a value out again. Numbers are labels, not a count.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No kitchen or delivery.</strong> An order is a record.</li>
<li><strong>Not secret.</strong> A readable number is guessable; challenge 1 adds a random id for apps.</li>
<li><strong>One region.</strong> Numbers across several databases are challenge 3.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tiffino</strong> (a fictional food delivery brand) had customers reading out UUIDs to support. A counter in memory then gave two orders the same number after a restart.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a new order, <b>then</b> its number is <code>TF-</code>, seven digits, <code>-</code>, and a check digit, and no other order has it, across servers and restarts.</li>
<li><b>Given</b> 100 orders at the same instant, <b>then</b> 100 different, valid numbers and no failures.</li>
<li><b>Given</b> the number in lower case with spaces, <b>then</b> the same order.</li>
<li><b>Given</b> a number with one wrong digit, <b>then</b> <code>400</code>, \"one digit is probably wrong\", without a database lookup.</li>
<li><b>Given</b> a valid number nobody has, <code>404</code>; something not shaped like an order number, <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Numbers come from a database sequence; uniqueness is also a constraint.</li>
<li>Gaps are allowed; repeats never.</li>
<li>When the sequence runs out, inserts fail; it never wraps around.</li>
<li>Numbers are normalised with <code>Locale.ROOT</code>; money in integer paise.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Use a database sequence, and explain gaps.</li>
<li>Compare UUIDs, sequences and readable codes.</li>
<li>Prove uniqueness under concurrency with a parallel test.</li>
<li>Compute and check a Luhn check digit, and know its blind spot.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/orders</code>", "<code>{\"outletId\", \"totalPaise\"}</code>: places an order; <code>Location</code> points at its number."],
    ["<code>GET</code>", "<code>/orders/by-number/{number}</code>", "Finds an order by its number, in any case, with or without spaces and dashes."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "An order was placed"],
    ['<span class="pill ok">200</span>', "The order for that number"],
    ['<span class="pill warn">400</span>', "Not shaped like an order number, a wrong check digit, or a bad order body"],
    ['<span class="pill warn">404</span>', "A valid number that no order has"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against one fresh database. Cases 3 to 5 use the number case 1 received. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-an-order", "Case 1: an order", "<b>Why:</b> the sequence's first value and its Luhn digit."),
    ("02-the-next-order", "Case 2: another outlet's order", "<b>Why:</b> the same sequence for every outlet and server."),
    ("03-looked-up-as-written", "Case 3: looked up as written", "<b>Why:</b> <code>200</code>."),
    ("04-looked-up-as-spoken", "Case 4: lower case, spaces", "<b>Why:</b> normalised to the stored form first."),
    ("05-one-digit-misheard", "Case 5: one digit off", "<b>Why:</b> the check digit no longer matches: <code>400</code>, no lookup."),
    ("06-a-valid-number-nobody-has", "Case 6: TF-9999999-7", "<b>Why:</b> a correct check digit, but no such order: <code>404</code>."),
    ("07-not-an-order-number", "Case 7: 12345", "<b>Why:</b> <code>400</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["100 orders at the same instant", "100 different, valid numbers", "<code>aHundredOrdersAtOnceGetAHundredDifferentNumbers</code>"],
    ["Two servers and a restart, one database", "101 numbers, all different", "<code>theSequenceIsSharedAndSurvivesARestart</code>"],
    ["A duplicate written straight to the table", "<code>orders_number_unique</code>", "<code>andIfARepeatEverReachedTheTableTheConstraintWouldStopIt</code>"],
    ["An order that fails after taking a number", "A gap, never a repeat", "<code>aRolledBackOrderLeavesAGapNotARepeat</code>"],
    ["The sequence's end", "No wrap-around", "<code>theSequenceRefusesToWrapAround</code>"],
    ["Any single wrong digit", "Caught by the check digit", "<code>everySingleWrongDigitIsCaught</code>"],
    ["Two neighbouring digits swapped", "Caught, except 09 ↔ 90", "<code>swappedNeighboursAreCaughtExceptZeroAndNine</code>"],
    ["Any case, spaces, no dashes", "The same number", "<code>numbersAreReadInAnyCaseWithOrWithoutSeparators</code>"],
    ["A wrong digit; an unknown valid number; not a number", "<code>400</code>; <code>404</code>; <code>400</code>", "<code>OrderContractTest</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">An in-memory counter that repeats numbers after a restart or on two servers.</p>
<p>Two servers, each with its own counter, both issue <code>#1</code>. A restarted server issues <code>#1</code> again. Two <code>OrderNumbers</code> on one database, plus a third standing in for a restarted server, issue 101 different numbers. If a repeat ever reached the table, <code>orders_number_unique</code> would refuse it. The Review tab shows a subtler version of the same mistake, a counter read from the table, failing under concurrency.</p>
</div>
""" + code(read(T + "InMemoryCounterTrapTest.java"), "java") + code(read(T + "OldOrderNumbers.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "OrderController.java", dwn("Places orders and looks them up by number.",
        "A wrong check digit is answered before the database is asked: it is a typo, not a missing order.",
        "Looking up typos: customers hear \"no such order\" instead of \"check the number\".")),
    (J + "OrderStore.java", dwn("Inserts and finds orders with <code>JdbcClient</code>.",
        "The number is taken and the order inserted in one transaction.",
        "A number shown to the customer for an order that was never saved.")),
    (J + "OrderNumbers.java", dwn("Takes the next sequence value, adds the Luhn digit, normalises and checks numbers.",
        "The database decides the value; Java only formats it.",
        "The trap: a counter in memory.",
        "<ul><li><code>nextval</code> never returns a value twice, even to transactions running at the same moment.</li><li>Luhn doubles every second digit from the right, then rounds the sum up to a multiple of 10.</li></ul>")),
    (M + "V1__orders_and_order_numbers.sql", dwn("The sequence and the orders table.",
        "<code>NO CYCLE</code>: running out is an error, not a silent repeat; the unique constraint backs up the sequence.",
        "Numbers repeating after 99,99,999, or after someone resets the sequence.")),
    ("src/main/resources/application.yaml", "<p>The database and strict JSON.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "OrdersApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/039-human-friendly-order-numbers/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/tiffino/orders/
│   ├── OrderController.java   ├── OrderStore.java   ├── OrderNumbers.java   └── OrdersApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__orders_and_order_numbers.sql
├── src/test/java/com/tiffino/orders/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/OrderNumbers.java  The flawed version (see Review)
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
<p>Place an order, stop the app, start it again, and place another: the number carries on. Then watch the sequence directly:</p>
""" + code("""curl -X POST http://localhost:8080/orders -H "Content-Type: application/json" -d '{"outletId":"TF-07","totalPaise":45000}'
docker compose exec postgres psql -U tiffino -d tiffino -c "SELECT last_value FROM order_number_seq\"""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>nextval: reached maximum value of sequence \"order_number_seq\"</code>", "All seven-digit numbers are used.", "A planned change: a new prefix or an eighth digit, in a new migration. Never cycle."],
    ["<code>duplicate key value violates unique constraint \"orders_number_unique\"</code>", "Something other than the sequence chose a number.", "Find the writer; numbers come only from <code>nextval</code>."],
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>OrderContractTest</code> ({cnt('OrderContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>InMemoryCounterTrapTest</code> ({cnt('InMemoryCounterTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>OrderDatabaseTest</code> ({cnt('OrderDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Concurrency", "A real concurrency test that proves the invariant holds", f"<code>OrderNumberConcurrencyTest</code> ({cnt('OrderNumberConcurrencyTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "What the check digit catches", f"<code>CheckDigitTest</code> ({cnt('CheckDigitTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "InMemoryCounterTrapTest.java", "<p>Written first: the old counter repeats; the sequence does not.</p>"),
    (T + "OrderNumberConcurrencyTest.java", "<p>100 orders on virtual threads, released together by a latch.</p>"),
    (T + "OrderDatabaseTest.java", "<p>Named constraints, a gap after a rollback, and no wrap-around.</p>"),
    (T + "CheckDigitTest.java", "<p>The standard Luhn example, every single-digit typo, every neighbour swap.</p>"),
    (T + "OrderContractTest.java", "<p>Placing and finding orders through HTTP, and every refusal.</p>"),
    (T + "OldOrderNumbers.java", "<p>The old counter, kept only in tests.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: an empty orders table before each test.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tiffino/orders/</code>.</li>
<li>Run it: <code>./mvnw test -Dtest=PublicIdChallengeTest</code> (Docker must be running). Challenge 2 does not compile until <code>DailyTokens</code> exists.</li>
<li>Add a migration and change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in (three Java files and two migrations), all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "A random id for apps", "Beginner-friendly", 25,
    "Readable numbers are guessable: the next order is one more. Give every order a random UUID too, generated by the database in a new migration; return it as <code>orderId</code> and add <code>GET /orders/{orderId}</code>.",
    "both tests in <code>PublicIdChallengeTest</code> pass.",
    ["<code>gen_random_uuid()</code> is built into PostgreSQL 13 and later.",
     "A <code>UUID</code> path variable makes Spring answer <code>400</code> for anything that is not one."],
    "challenge/PublicIdChallengeTest.java", ["challenge/solution/V2__public_order_ids.sql", "challenge/solution/OrderStore.java", "challenge/solution/OrderController.java"]) + challenge(2, "Kitchen tokens that start again each day", "Go deeper", 35,
    "The kitchen screen calls out 1, 2, 3…, per outlet, from 1 each day. Keep a counter row per outlet and day, and take the next token with one atomic statement, so 50 parallel orders get 1 to 50.",
    "all three tests in <code>DailyTokenChallengeTest</code> pass.",
    ["<code>INSERT … ON CONFLICT (outlet_id, day) DO UPDATE SET last_token = daily_tokens.last_token + 1 RETURNING last_token</code>.",
     "Reading the last token and writing +1 in two statements is the Review tab's mistake again."],
    "challenge/DailyTokenChallengeTest.java", ["challenge/solution/V3__daily_tokens.sql", "challenge/solution/DailyTokens.java", "challenge/solution/OrderStore.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Numbers across regions</h2>
<p>Tiffino opens in Dubai with its own database. Orders from both must never share a number, and support should tell the region from the number. Compare a region prefix with separate sequences, sequences with different ranges or increments, and a central number service. What happens when one region's database is down?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: sequence, constraints"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: two counters, a restart.</li>
<li>Create the sequence and the table with a unique, formatted number.</li>
<li>Format numbers in Java with a check digit; check digits on lookup before the database.</li>
<li>Prove it under load: 100 orders at once.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Database sequence + check digit", "Gaps; one database decides.", '<span class="pill ok">Chosen</span>'],
    ["A counter in memory", "Repeats after a restart and on every extra server.", '<span class="pill bad">The trap</span>'],
    ["<code>max(number) + 1</code> from the table", "Two requests read the same max; under load, duplicates or unique errors.", '<span class="pill bad">The review</span>'],
    ["UUID only", "Unique anywhere without coordination, but unreadable on the phone.", '<span class="pill warn">For apps, not people</span>'],
    ["Random short codes (\"7KQ2-9XM\")", "Unguessable and readable; needs a unique constraint and a retry on collision.", '<span class="pill warn">Station 040</span>'],
    ["A per-day counter table", "Short daily numbers; one row lock per outlet per day.", '<span class="pill warn">Challenge 2</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "Definition", "Why"], [
    ["<code>order_number_seq</code>", "1000001 to 9999999, <code>NO CYCLE</code>", "Seven digits, read out easily; running out is loud."],
    ["<code>orders</code>", "Identity PK (internal). <code>orders_number_unique</code>, <code>orders_number_format</code>, <code>orders_total_positive</code>.", "The sequence prevents repeats; the constraint proves it to every writer."]]) + """
<p><strong>Why gaps are fine:</strong> <code>nextval</code> is not rolled back with the transaction, so a failed order uses up its number. That is what lets thousands of transactions take numbers at once without waiting for each other. A gap-free count needs a lock that every order waits for.</p>
""" + code(read(M + "V1__orders_and_order_numbers.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Capacity</dt><dd>Seven digits give about 90 lakh orders. Watch <code>last_value</code> against the maximum, and plan the next format long before.</dd>
<dt>Restores</dt><dd>After restoring a backup, check the sequence is ahead of the highest number in the table; <code>setval</code> fixes it.</dd>
<dt>Guessability</dt><dd>Readable numbers are sequential. Never let a number alone reveal an order to someone who is not its customer; ask for the phone too, or use a random id (challenge 1).</dd>
<dt>Check digits</dt><dd>Luhn misses 09 ↔ 90 swaps. The Damm and Verhoeff algorithms catch every single-digit error and every adjacent swap.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("UUID, sequence or readable code?", "UUIDs need no coordination and are unguessable but unreadable. Sequences are short and ordered but need one source and are guessable. Readable random codes sit between, at the cost of collision handling. Systems often use two: an internal key and a customer-facing number."),
    ("Why do sequence numbers have gaps?", "nextval is not transactional: a value taken by a transaction that rolls back is never reused. That avoids making every insert wait for every other."),
    ("Why is SELECT max(id) + 1 wrong?", "Two transactions read the same max and insert the same number. With a unique constraint one fails; without it, both succeed and the data is wrong."),
    ("What does a check digit protect against?", "Typos: the Luhn digit catches every single wrong digit and most swaps of neighbours, so the system can say 'check the number' instead of 'not found'."),
    ("How do you test uniqueness under concurrency?", "Start many threads, hold them at a latch, release them together, and assert the invariant: all values distinct, no failures, row count as expected."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and read why each test failed."],
    ["Databases", "A sequence and a unique constraint.", "Why gaps are the price of no waiting."],
    ["Concurrency", "A latch-started parallel test.", "Why max()+1 passes every sequential test."],
    ["Design", "Readable number with a check digit.", "When to add a random id or a regional prefix."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("The number is read from the table: max() + 1",
     "\"No gaps, and support can count orders\" sounds tidy. But 100 requests read the same max at the same moment and all try the same number; the unique constraint refuses all but one. Sequential tests cannot see it.",
     "<code>aHundredOrdersAtOnceGetAHundredDifferentNumbers</code>: failures under load. <code>theSequenceIsSharedAndSurvivesARestart</code> and <code>aRolledBackOrderLeavesAGapNotARepeat</code> fail too, because nothing is taken from the sequence."),
    ("The check digit is the sum of the digits",
     "A digit sum notices one wrong digit, but swapped digits have the same sum, so \"1004273\" and \"1002473\" share a check digit. Swaps are the most common mistake when reading numbers aloud.",
     "<code>swappedNeighboursAreCaughtExceptZeroAndNine</code> and <code>theStandardLuhnExample</code> fail. <code>everySingleWrongDigitIsCaught</code> still passes, which is why the change looked safe."),
    ("Lookups no longer ignore letter case",
     "\"Take the number exactly as stored\" breaks every customer who types tf instead of TF: the number is refused as not an order number.",
     "<code>numbersAreReadInAnyCaseWithOrWithoutSeparators</code> and <code>anOrderGetsAReadableNumberAndALocation</code> fail."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate wants \"cleaner\" numbers. The sequence is gone and each number follows on from the last order, so there are no gaps and support can count orders. The check digit is simpler, and lookups take the number exactly as stored. Every test that places one order at a time still passes. Read the file and list every problem before opening the findings.</p>
<p class="path">review/OrderNumbers.java</p>
""" + code(read("review/OrderNumbers.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">The worst flaw, max() + 1, passes every test that places one order at a time. Only the parallel test and the sequence tests catch it.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
