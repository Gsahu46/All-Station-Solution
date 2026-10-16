"""Station 055 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 55,
    "stack": "Spring Boot 4.1.1 · Java 25 · @Transactional proxies · rollback rules · readOnly transactions · JdbcClient · PostgreSQL 17 · Flyway · Testcontainers",
    "simulation": "Products, orders and payments are demo data, not Kartwala's. A payment is a record in the payments table: no gateway is called and no money moves. A real gateway call could not be undone by a database rollback (see Production).",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/kartwala/checkout/"
T = "src/test/java/com/kartwala/checkout/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Transaction", "Several database changes that are kept together or undone together.", "A bank transfer: debit and credit, both or neither.", "One checkout"),
    ("Proxy", "An object Spring puts in front of yours, which starts and ends the transaction around each call.", "A receptionist who opens a file before you see the clerk and closes it after.", "<code>CheckoutService</code> as injected"),
    ("Self-invocation", "A method calling another method of the same object directly, past the proxy.", "The clerk walking to the next desk without the receptionist.", "<code>this.placeOrder()</code>"),
    ("Rollback rule", "Which exceptions undo the transaction.", "\"Any error undoes the transfer\", or only some.", "Unchecked: rolled back; checked: committed"),
    ("readOnly", "A transaction that promises not to write.", "A visitor's pass for the records room: look, do not touch.", "<code>find()</code>"),
    ("Reservation", "Stock set aside for one order.", "Items put behind the counter with a name on them.", "<code>reservations</code>"),
]
STORY = [
    ("A transaction on paper", "Kartwala's placeOrder() said @Transactional. It saved the order, then the payment record, then reserved stock line by line."),
    ("Paid, half reserved", "Customers were charged for orders whose stock was only partly reserved. Logs showed an out-of-stock exception, and no rollback. The controller called checkout(), which called this.placeOrder(): the annotation was never reached."),
    ("The fix", "Put @Transactional on the method the controller calls, through Spring's proxy; throw only exceptions that roll back; reserve stock before recording the payment."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">An annotation is only as good as the call that reaches it. Know where your transaction starts.</p>

<h2>What are we building?</h2>
<p><code>POST /checkouts</code> takes a basket. It creates the order, reserves stock for every line, and records the payment, in one transaction. If anything fails, nothing is kept. <code>GET /checkouts/{id}</code> reads it back.</p>

<h2>An everyday analogy</h2>
<p>A shop counter with a rule: the shopkeeper opens a bill, puts each item behind the counter, and takes the money last. If an item is missing, every item goes back on the shelf and the bill is torn up. The old code took the money first, and had nobody to enforce "tear it up" because it never opened the bill properly.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>The controller calls</strong> <code>checkout()</code> on the proxy: a transaction starts.</li>
<li><strong>The order is written</strong>; each line's stock is reserved only if there is enough.</li>
<li><strong>The payment record</strong> is written last.</li>
<li><strong>Any exception</strong> (all of them unchecked) rolls everything back; success commits everything.</li>
</ol>

<details class="qa check"><summary>Check yourself: the old placeOrder() had @Transactional. Why did it not work?</summary><p>Spring adds transactions with a proxy that wraps the bean. Calls from outside go through the proxy; a call from inside the same object (<code>this.placeOrder()</code>) goes straight to the method. No proxy, no transaction.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real payment.</strong> A record, not a charge.</li>
<li><strong>No cancellation.</strong> Challenge 1.</li>
<li><strong>No login.</strong> The customer is named in the body.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Kartwala</strong> (a fictional marketplace) charged customers for orders whose stock was not fully reserved, because the checkout's transaction never started.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> 2 Assam tea and 5 Kashmiri chilli (all 5 left), <b>then</b> <code>201</code>, ₹1,343 total, a payment record, and stock 48 and 0.</li>
<li><b>Given</b> 2 tea and a sold-out tiffin box, <b>then</b> <code>409</code>, and no order, reservation or payment; tea stock still 50.</li>
<li><b>Given</b> an unknown product, or the same product twice, <b>then</b> <code>422</code>.</li>
<li><b>Given</b> no lines, quantity 0, 11 or 1.5, or no customer, <b>then</b> <code>400</code>.</li>
<li><b>Given</b> an unknown checkout id, <b>then</b> <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>The order, its reservations and its payment record commit together or not at all.</li>
<li>The transaction starts at the method the controller calls.</li>
<li>Stock never goes below zero, also in the database.</li>
<li>Reads that must not write run in read-only transactions.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Explain how Spring's transaction proxy works, and why self-invocation bypasses it.</li>
<li>Know which exceptions roll back by default, and how to change it.</li>
<li>Use <code>readOnly</code> and know what it does on PostgreSQL.</li>
<li>Order the steps of a business operation so the risky ones come first.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/checkouts</code>", "Check out: <code>customerId</code> and 1 to 20 lines of <code>productId</code> and <code>quantity</code> (1 to 10)."],
    ["<code>GET</code>", "<code>/checkouts/{id}</code>", "The checkout: total, payment record and lines."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Checked out; <code>Location</code> points at it"],
    ['<span class="pill ok">200</span>', "The checkout"],
    ['<span class="pill warn">400</span>', "Malformed basket"],
    ['<span class="pill warn">404</span>', "No such checkout"],
    ['<span class="pill warn">409</span>', "Not enough stock for a line: nothing is kept"],
    ['<span class="pill warn">422</span>', "Unknown product, or a product listed twice"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against one fresh database (tea 50, chilli 5, tiffin box 0). JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-a-checkout", "Case 1: 2 tea and 5 chilli", "<b>Why:</b> everything reserved and recorded together: <code>201</code>."),
    ("02-read-it-back", "Case 2: read it back", "<b>Why:</b> a read-only transaction."),
    ("03-the-chilli-is-sold-out-now", "Case 3: another shopper wants 1 chilli", "<b>Why:</b> case 1 took the last 5: <code>409</code>."),
    ("04-tea-and-a-sold-out-box", "Case 4: 2 tea and a sold-out tiffin box", "<b>Why:</b> the tea was reserved, then the box failed, so the tea went back: <code>409</code>."),
    ("05-an-unknown-product", "Case 5: product 99", "<b>Why:</b> <code>422</code>."),
    ("06-quantity-zero", "Case 6: quantity 0", "<b>Why:</b> <code>400</code>."),
    ("07-no-such-checkout", "Case 7: checkout 99", "<b>Why:</b> <code>404</code>."),
]) + """
<h2>What the database holds afterwards</h2>
<p class="muted">Read with psql after the requests above (<code>docs/captures/state.txt</code>): one order, tea at 48 (case 4's reservation was rolled back), chilli at 0.</p>
""" + code(read("docs/captures/state.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A basket that fits", "Order, reservations, payment; stock down", "<code>aCheckoutReservesStockAndRecordsThePayment</code>"],
    ["One line out of stock", "<code>409</code>; nothing kept", "<code>outOfStockIs409AndNothingIsKept</code>"],
    ["Unknown or repeated product", "<code>422</code>; nothing kept", "<code>unknownOrRepeatedProductsAre422</code>"],
    ["Malformed baskets", "<code>400</code>; nothing kept", "<code>malformedCheckoutsAre400</code>"],
    ["Unknown checkout", "<code>404</code>", "<code>unknownCheckoutsAre404</code>"],
    ["Negative stock, second payment, orphan payment, bad quantity or status, written directly", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"],
    ["Checked vs unchecked exceptions; rollbackFor", "Checked commits by default", "<code>aCheckedExceptionCommitsUnlessToldOtherwise</code>"],
    ["A write inside a readOnly transaction", "Refused by PostgreSQL", "<code>aReadOnlyTransactionRefusesWrites</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Calling a <code>@Transactional</code> method from the same class, so no transaction starts.</p>
<p>The old service is kept in the tests as <code>OldCheckoutService</code>, and the trap test registers it as a real Spring bean, so it is proxied exactly as in production (the test checks that it is). Called the way the controller called it, through <code>checkout()</code>, the out-of-stock exception leaves 1 order, 1 reservation, 1 payment record, and tea stock down by 2: a paid order with half its stock. Calling <code>placeOrder()</code> itself through the proxy rolls everything back, which proves the annotation was fine and the call was not. The fixed API rolls back the same basket whole.</p>
<p>While building, each part was undone once. Without <code>@Transactional</code> on <code>checkout</code>, 2 tests turned red; reserving without the <code>stock &gt;= quantity</code> condition, 2 (the database's check refused it as a <code>500</code>). Adding a non-transactional method that calls <code>this.checkout()</code>, and pointing the controller at it, turned the same 2 red: the old bug, rebuilt in the new code.</p>
</div>
""" + code(read(T + "SelfInvocationTrapTest.java"), "java") + code(read(T + "OldCheckoutService.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "CheckoutController.java", dwn("Validates the basket; calls the service through its proxy.", "The transaction starts at the first call into the service.", "A non-transactional entry point.")),
    (J + "CheckoutService.java", dwn("Prices the lines, writes the order, reserves stock, records the payment last; reads back read-only.",
        "<code>@Transactional</code> on the method callers use; only unchecked exceptions.", "Half-done checkouts.",
        "<ul><li>Each reservation is <code>UPDATE ... WHERE stock &gt;= ?</code>: zero rows means not enough, safe under concurrency.</li><li>The payment record comes last, after everything that can fail.</li><li><code>readOnly = true</code> makes PostgreSQL refuse writes in <code>find</code>.</li></ul>")),
    (M + "V1__products_orders_payments.sql", "<p>Products, orders, reservations and payments, with named constraints.</p>"),
    (M + "V2__demo_products.sql", "<p>Tea (50), chilli (5) and a sold-out tiffin box.</p>"),
    ("src/main/resources/application.yaml", "<p>Problem details on; decimals refused for whole-number fields.</p>"),
    (J + "CheckoutApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/055-checkout-as-one-transaction/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/checkout/
│   ├── CheckoutController.java   ├── CheckoutService.java   └── CheckoutApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__products_orders_payments.sql, V2__demo_products.sql
├── src/test/java/com/kartwala/checkout/   (see Tests)
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
<p>See the transaction start and end. Run the app with transaction logging:</p>
""" + code("""./mvnw spring-boot:run -Dspring-boot.run.arguments=--logging.level.org.springframework.jdbc.support.JdbcTransactionManager=DEBUG""", "bash") + """
<p>Send case 4 from the API tab and look for "Creating new transaction", then "Initiating transaction rollback". The old code would print neither.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>@Transactional</code> seems to do nothing", "The method is called from the same class, or is private.", "Call it from another bean; put the annotation on the entry point."],
    ["A failed operation's rows are still there", "A checked exception: Spring commits by default.", "Throw unchecked, or <code>rollbackFor = ThatException.class</code>."],
    ["<code>cannot execute INSERT in a read-only transaction</code>", "A write inside <code>readOnly = true</code>.", "Move the write out, or drop <code>readOnly</code> for that method."],
    ["<code>500</code> with <code>products_stock_not_negative</code>", "Stock reduced without checking it first.", "<code>UPDATE ... WHERE stock &gt;= ?</code> and check the row count."],
    ["The payment is recorded for a failed order", "Payment written before the steps that can fail.", "Write it last, inside the same transaction."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>CheckoutContractTest</code> ({cnt('CheckoutContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>SelfInvocationTrapTest</code> ({cnt('SelfInvocationTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>CheckoutDatabaseTest</code> ({cnt('CheckoutDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Testing a proxy, for real</h2>
<p>A transaction bug only shows with a real Spring proxy and a real database. So the old service and the rollback-rule examples are real beans (<code>@Import</code> in the test), the database is a real PostgreSQL, and every test checks the rows, not only the HTTP answer. No test runs inside a test transaction, which would hide exactly this bug.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "SelfInvocationTrapTest.java", "<p>Written first: the old service through <code>checkout()</code> and through the proxy, and the fixed API.</p>"),
    (T + "CheckoutContractTest.java", "<p>Checkout, read-back, and every refusal, with the rows checked each time.</p>"),
    (T + "CheckoutDatabaseTest.java", "<p>Named constraints, rollback rules and read-only mode.</p>"),
    (T + "RollbackRules.java", "<p>Test-only bean: one write under four transaction settings.</p>"),
    (T + "OldCheckoutService.java", "<p>The old service, kept only in tests.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: empty orders and reset stock before each test; one string for the whole state.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/kartwala/checkout/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=CancelChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests). Without <code>rollbackFor</code> in the solution, challenge 2's test failed with one order and one reservation left behind.</p>
""" + challenge(1, "Cancel a checkout", "Beginner-friendly", 25,
    "Add <code>POST /checkouts/{id}/cancellation</code>: order CANCELLED, stock back, payment record REFUNDED, in one transaction. Again: <code>409</code>; unknown: <code>404</code>.",
    "the test in <code>CancelChallengeTest</code> passes.",
    ["Lock the order row (<code>SELECT ... FOR UPDATE</code>) so two cancellations cannot both give stock back.",
     "One UPDATE can return the stock of every line: <code>UPDATE products ... FROM reservations</code>."],
    "challenge/CancelChallengeTest.java", ["challenge/solution/CheckoutService.java", "challenge/solution/CheckoutController.java"]) + challenge(2, "A declined payment", "Go deeper", 25,
    "The demo gateway declines totals above ₹2,000 by throwing a checked <code>PaymentDeclined</code> from the payment step. The checkout must roll back everything and answer <code>422</code>.",
    "the test in <code>PaymentDeclinedChallengeTest</code> passes.",
    ["A checked exception commits by default: <code>@Transactional(rollbackFor = PaymentDeclined.class)</code>.",
     "Catch it in the controller, after the proxy has rolled back."],
    "challenge/PaymentDeclinedChallengeTest.java", ["challenge/solution/CheckoutService.java", "challenge/solution/CheckoutController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>When the payment is someone else's</h2>
<p>Replace the payment record with a call to a real gateway that charges the card. The database transaction can roll back; the charge cannot. Order the steps, and decide what happens when the charge succeeds and the commit fails, or the charge times out.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, mapping"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test with the old service as a real proxied bean.</li>
<li>Put <code>@Transactional</code> on the method the controller calls.</li>
<li>Make every failure an unchecked exception (or name it in <code>rollbackFor</code>).</li>
<li>Order the steps: the ones that can fail first, the payment last.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["<code>@Transactional</code> on the public entry method", "Know where calls come from.", '<span class="pill ok">Chosen</span>'],
    ["Annotate an inner method and call it with <code>this.</code>", "Nothing happens.", '<span class="pill bad">The trap</span>'],
    ["Inject the bean into itself, or move the method to another bean", "Works; the second is cleaner.", '<span class="pill warn">If the split is real</span>'],
    ["<code>TransactionTemplate</code> in the code", "Explicit and visible; more code.", '<span class="pill warn">For fine control</span>'],
    ["AspectJ weaving instead of proxies", "Self-invocation works; build setup and surprise for readers.", '<span class="pill warn">Rarely worth it</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Constraints"], [
    ["<code>products</code>", "<code>products_price_positive</code>, <code>products_stock_not_negative</code>"],
    ["<code>orders</code>", "<code>orders_total_positive</code>, <code>orders_status_known</code>"],
    ["<code>reservations</code>", "<code>reservations_order_fk</code>, <code>reservations_product_fk</code>, <code>reservations_one_per_product</code>, <code>reservations_quantity_range</code>"],
    ["<code>payments</code>", "<code>payments_order_fk</code>, <code>payments_one_per_order</code>, <code>payments_amount_positive</code>, <code>payments_status_known</code>"]]) + """
""" + code(read(M + "V1__products_orders_payments.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Real payments are outside the transaction</dt><dd>A gateway charge is not undone by a rollback. Reserve and commit first, then charge; or record "payment pending", charge, and confirm; and refund when a later step fails. Station 085 covers idempotent payments.</dd>
<dt>Find the damage</dt><dd>Orders with a payment but fewer reservations than lines are the old bug's leftovers. A query finds them; customer support refunds or ships.</dd>
<dt>Transactions are short</dt><dd>Hold no transaction open across a slow network call; rows stay locked meanwhile.</dd>
<dt>Logging</dt><dd><code>JdbcTransactionManager</code> at DEBUG shows every begin, commit and rollback: the fastest way to see where a transaction really is.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why does self-invocation skip @Transactional?", "Spring applies @Transactional with a proxy around the bean. A call from inside the bean uses this, the real object, not the proxy, so no transaction logic runs."),
    ("Which exceptions roll back by default?", "Unchecked ones (RuntimeException and Error). Checked exceptions commit, unless listed in rollbackFor."),
    ("What does readOnly = true do?", "It tells the transaction manager and the database that no writes will happen. On PostgreSQL the transaction is read-only, so a write fails; ORMs can also skip dirty checking."),
    ("Does @Transactional work on private methods?", "Not with Spring's proxies: they can only intercept calls they can override or forward, and private methods are neither."),
    ("How do you prove a transaction works?", "With a real proxy and a real database: make a later step fail and check the rows the earlier steps wrote are gone."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You rebuilt the self-invocation bug and watched it fail."],
    ["Proxies", "You know where the transaction starts.", "You can explain proxy, self-invocation and private methods."],
    ["Rollback", "Unchecked exceptions only.", "You know what <code>rollbackFor</code> is for."],
    ["Ordering", "Payment last.", "A plan for a real gateway."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any <code>@Transactional</code>:</p>
<ul class="rules">
<li>Is the annotated method the one callers from other beans call?</li>
<li>Can any exception thrown inside be checked, and is it in <code>rollbackFor</code>?</li>
<li>What happens to the rows already written if the last step fails?</li>
<li>Is anything inside the transaction that a rollback cannot undo (a call, an email, a file)?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
