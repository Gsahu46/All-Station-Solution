"""Station 102 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 102,
    "stack": "Spring Boot 4.1.1 · Java 25 · HikariCP · TransactionTemplate · RestClient with timeouts · Actuator and Micrometer · PostgreSQL 17 · Testcontainers",
    "simulation": "The payment gateway is simulated: a small server answers each charge (no money moves). The sales and buyers are demo data.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). Python 3 runs the test gateway in Try it yourself. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/seatsure/sales/"
T = "src/test/java/com/seatsure/sales/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Connection pool", "A few ready database connections the app lends to requests and takes back.", "A bank with ten counters.", "HikariCP, 10"),
    ("Connection timeout", "How long a request waits for a free connection before giving up.", "How long you stand in the queue for a counter.", "2 s (Hikari's default: 30 s)"),
    ("Transaction", "Work on the database that commits or rolls back together; it holds a connection until it ends.", "Your time at the counter.", "<code>TransactionTemplate</code>"),
    ("Remote call", "A request to another system over the network: slow, sometimes very slow.", "The clerk phoning head office mid-transaction.", "the payment gateway"),
    ("Pool metrics", "Numbers the pool publishes: waiting requests, timeouts, how long connections are held.", "The token display over the counters.", "<code>hikaricp.connections.*</code>"),
    ("Bulkhead", "A limit on how many requests may wait on one slow thing.", "Only three customers allowed at the foreign-exchange desk.", "challenge 2"),
]
STORY = [
    ("Sale opens", "Tickets for India vs Australia go on sale. Thousands of fans press \"Buy\" at once."),
    ("Thirty seconds, then an error", "Each order took a database connection, then called the payment gateway inside the same transaction. The gateway took a second or two. Ten slow charges held all ten connections; every other request waited 30 seconds for one and failed. The database itself was nearly idle."),
    ("The fix", "The order is split: take the seats and commit, call the gateway with no connection held, then record the result in a second short transaction. A connection is held for milliseconds, and a request that cannot get one is told so in 2 seconds."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Never hold a database connection while you wait for someone else. A pool runs dry long before the database does.</p>

<h2>What are we building?</h2>
<p>A ticket order that takes seats, charges the buyer and records the result, without holding a connection during the charge, with metrics and drills for the night of the sale.</p>

<h2>An everyday analogy</h2>
<p>A bank clerk who phones head office in the middle of serving you blocks the counter for everyone behind you. A good clerk takes your form, sends you to wait while head office answers, and calls the next customer.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Reserve</strong>: one short transaction takes the seats (only if they are there) and records the order as waiting for payment.</li>
<li><strong>Charge</strong>: call the gateway with no connection held, for at most 3 seconds.</li>
<li><strong>Record</strong>: a second short transaction marks the order paid, or failed and gives the seats back.</li>
<li><strong>Watch</strong>: the pool's metrics show waiting requests and timeouts; the alerts read them.</li>
</ol>

<details class="qa check"><summary>Check yourself: why not just make the pool bigger?</summary><p>A bigger pool only moves the wall: 10 or 100 connections, slow charges fill them all, and each connection costs the database memory. Holding none during the charge removes the wall.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real payments.</strong> A test gateway answers.</li>
<li><strong>No seat map.</strong> A sale is a count of seats.</li>
<li><strong>No reconciliation job.</strong> A timed-out charge's seats are given back (a shortcut, see Code).</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>SeatSure</strong> (a fictional ticketing site): during a cricket ticket sale every request waits 30 seconds, then fails, while the database is idle.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo rules: 10 connections, 2 s to get one; 1 to 6 seats per order; the gateway gets 1 s to connect and 3 s to answer.</p>
<ol class="gwt">
<li><b>Given</b> seats and a paying buyer, <b>then</b> <code>201</code>, PAID, the amount in paise and the charge id.</li>
<li><b>Given</b> a declined payment, a gateway error or a gateway slower than 3 s, <b>then</b> <code>402</code>, <code>502</code> or <code>504</code>, and the seats are given back.</li>
<li><b>Given</b> many orders while the gateway is slow, <b>then</b> no connection is held during charges, and other requests answer at once.</li>
<li><b>Given</b> no free connection, <b>then</b> <code>503</code> with <code>Retry-After</code> within the pool's timeout, not after 30 s.</li>
<li><b>Given</b> too few seats, an unknown sale or bad input, <b>then</b> <code>409</code>, <code>404</code>, <code>400</code>, and nothing charged.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>No transaction is open during a remote call.</li>
<li>Never more seats sold than there are, in the database too.</li>
<li>Pool metrics published; drills for the two failures that matter.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Size a Hikari pool and set its connection timeout.</li>
<li>Split a request into short transactions around a remote call.</li>
<li>Put timeouts on every remote call.</li>
<li>Read pool metrics and write alerts and a runbook from them.</li>
<li>Prove pool behaviour with concurrent tests and drills.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/sales/{id}/orders</code>", "Buy 1 to 6 seats: <code>{buyer, seats}</code>."],
    ["<code>GET</code>", "<code>/sales/{id}</code>", "Capacity, sold and left."],
    ["<code>GET</code>", "<code>/actuator/metrics/hikaricp.connections.*</code>", "The pool's metrics, for dashboards and alerts."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Paid"],
    ['<span class="pill warn">400</span>', "No buyer; seats not 1 to 6"],
    ['<span class="pill warn">402</span>', "The payment was declined"],
    ['<span class="pill warn">404</span>', "No such sale"],
    ['<span class="pill warn">409</span>', "Not enough seats left"],
    ['<span class="pill warn">502</span> / <span class="pill warn">504</span>', "The gateway failed / did not answer within 3 s"],
    ['<span class="pill warn">503</span>', "No database connection within 2 s; <code>Retry-After: 5</code>"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against <code>docs/test-gateway.py</code>, a small simulated gateway. <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-two-seats-for-the-big-match", "Case 1: two seats for the big match", "<b>Why:</b> <code>201</code>, paid; 2 × ₹1,500 = 300000 paise."),
    ("02-the-sale-afterwards", "Case 2: the sale afterwards", "<b>Why:</b> two seats fewer."),
    ("03-four-seats-at-the-small-match", "Case 3: all four seats of the small match", "<b>Why:</b> <code>201</code>."),
    ("04-one-more-at-the-small-match", "Case 4: one more", "<b>Why:</b> <code>409</code>; nothing charged."),
    ("05-seven-seats", "Case 5: seven seats", "<b>Why:</b> <code>400</code>."),
    ("06-no-such-sale", "Case 6: no such sale", "<b>Why:</b> <code>404</code>."),
]) + """
<h2>The drill, captured</h2>
<p class="muted"><code>docs/capture.sh</code> makes the gateway hang for 10 s, sends 20 orders at once (twice the pool), and reads the sale while they wait. Status codes of the 20, and the slowest one:</p>
""" + code(read("docs/captures/drill.txt").strip(), "text") + code(read("docs/captures/drill-read.txt").strip(), "text") + examples([
    ("07-the-sale-after-the-drill", "Case 7: the sale after the drill", "<b>Why:</b> the 20 failed orders gave their seats back."),
]) + """
<p class="muted">And the pool's metrics at the end:</p>
""" + code(read("docs/captures/pool-metrics.txt").strip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["The old way: 16 fans, pool 4, a 0.7 s gateway", "Some get no connection; pool timeouts rise", "<code>theOldWayHoldsAConnectionThroughEachChargeAndFansTimeOut</code>"],
    ["The API, the same 16", "All paid; no pool timeouts", "<code>theApiHoldsAConnectionForMillisecondsAndEveryFanGetsASeat</code>"],
    ["A paid order", "<code>201</code>, amount, charge id, Idempotency-Key", "<code>aPaidOrderTakesItsSeats</code>"],
    ["A declined payment", "<code>402</code>, order FAILED, seats back", "<code>aDeclinedPaymentGivesTheSeatsBack</code>"],
    ["0 or 7 seats, no buyer, no sale, too few seats", "<code>400</code>, <code>404</code>, <code>409</code>; nothing charged", "<code>badOrdersAre400UnknownSales404AndASoldOutSale409</code>"],
    ["Rules written by plain SQL", "Refused by named constraints", "<code>saleAndOrderRulesHoldWithoutJava</code>"],
    ["An order that cannot be recorded", "No seats taken", "<code>anOrderThatCannotBeRecordedTakesNoSeats</code>"],
    ["Drill: the gateway hangs", "<code>504</code> after 1 s each; reads answer at once; seats back", "<code>aHangingGatewayIsCutOffAndTheDatabaseStaysFree</code>"],
    ["Drill: the pool is held by something else", "<code>503</code> after about 1 s, logged; recovers", "<code>withNoConnectionFreeTheAnswerIs503AfterOneSecondNotThirty</code>"],
    ["The alerts' metrics", "Published", "<code>theMetricsTheAlertsReadArePublished</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Calling remote services inside a transaction while holding a connection.</p>
<ul>
<li><strong>The old way.</strong> One <code>@Transactional</code> method takes the seats, charges the buyer and records the result. Sixteen fans at once, a pool of four, a gateway that takes 0.7 s: four charges at a time, each holding a connection, and the fans still waiting after 1 s get none. <code>hikaricp.connections.timeout</code> rises.</li>
<li><strong>The API.</strong> The same sixteen: every one paid, and no request waited too long for a connection, because none was held during a charge.</li>
</ul>
<p>While building, each part was undone once: one transaction around the order turned 3 tests red; no read timeout 1; no seat check in the UPDATE 1; seats kept after a decline 1; seats kept after a gateway failure 1; no <code>503</code> for an empty pool 1; no Idempotency-Key 1; timeouts taken for other errors 1.</p>
</div>
""" + code(read(T + "PoolExhaustionTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SaleController.java", dwn("The endpoints, and the empty pool.", "Validates the order; turns \"no connection within the pool's timeout\" into <code>503</code> with <code>Retry-After</code>, logged at ERROR.", "A 500 after 30 s; nobody knowing why.",
        "<ul><li>Inside a transaction, the pool's timeout arrives as <code>CannotCreateTransactionException</code>; outside one, as <code>CannotGetJdbcConnectionException</code>. Both are handled. Found while building.</li></ul>")),
    (J + "TicketOrders.java", dwn("The order in three short transactions.",
        "Reserve and commit; charge with nothing open; record PAID, or FAILED and give the seats back.",
        "A connection held for the length of a charge.",
        "<ul><li>Shortcut: a charge that timed out may still have gone through. Here the seats are given back; production asks the gateway about the order's Idempotency-Key first, or keeps the order pending until a reconciliation job does.</li></ul>")),
    (J + "PaymentGateway.java", dwn("The gateway client.", "Sends the order id as Idempotency-Key; tells a decline, a timeout and other failures apart.", "A slow gateway taken for a broken one.",
        "<ul><li>A timeout is recognised by its cause (<code>HttpTimeoutException</code>), not by the words of its message: the first version looked for \"timed out\" and called every timeout a 502. Found while building.</li></ul>")),
    (J + "SalesApplication.java", dwn("The gateway's HTTP client.", "Connect 1 s, read 3 s.", "A request thread waiting for ever.")),
    ("src/main/resources/application.yaml", dwn("The pool.", "10 connections, 2 s to get one; metrics exposed.", "Hikari's default 30 s wait.",
        "<ul><li><code>spring.datasource.hikari.*</code> binds straight to Hikari's setters: <code>connection-timeout</code> is milliseconds as a number. <code>2s</code> stops the app at start-up. Found while building.</li></ul>")),
    (M + "V1__sales_and_orders.sql", dwn("Sales and orders.", "Named constraints for seats, amounts and states.", "Overselling from any writer.")),
    (M + "V2__demo_sales.sql", "<p>A big match and a small one.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
]
tree = """stations/102-ticket-sale-when-the-pool-runs-dry/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/seatsure/sales/
│   ├── SaleController.java   ├── TicketOrders.java   ├── PaymentGateway.java   └── SalesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__sales_and_orders.sql, V2__demo_sales.sql
├── src/test/java/com/seatsure/sales/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, test gateway, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Docker", "Docker Desktop (Windows, macOS) or Docker Engine (Linux), running", "<code>docker info</code>"],
    ["Python 3", "Only for the test gateway in Try it yourself", "<code>python3 --version</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""docker compose up -d        # PostgreSQL 17 on localhost:5432
python3 docs/test-gateway.py 9099 &   # the simulated payment gateway
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d
Start-Process python -ArgumentList 'docs/test-gateway.py','9099'
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Make the gateway hang, then watch the pool while orders wait:</p>
""" + code("""curl -d '{"seconds":10}' http://127.0.0.1:9099/delay
for i in $(seq 1 20); do curl -s -o /dev/null -w '%{http_code}\\n' -H 'Content-Type: application/json' -d '{"buyer":"fan","seats":1}' localhost:8080/sales/1/orders & done
curl localhost:8080/actuator/metrics/hikaricp.connections.pending""", "bash") + """
<p>Every order ends <code>504</code> after 3 s; <code>pending</code> stays 0. Then put the transaction back around the whole order (the Review tab's version) and try again.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Requests fail after exactly 30 s", "Hikari's default connection timeout; the pool is empty.", "Find what holds connections (<code>hikaricp.connections.usage</code>); set a shorter timeout."],
    ["<code>NumberFormatException: For input string: \"2s\"</code> at start-up", "Hikari properties take milliseconds as numbers.", "<code>connection-timeout: 2000</code>."],
    ["Connections held for seconds", "A remote call, a file, or a slow query inside a transaction.", "Move it out; keep transactions short."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the configuration and the database.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>TicketOrderContractTest</code> ({cnt('TicketOrderContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>PoolExhaustionTrapTest</code> ({cnt('PoolExhaustionTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>TicketDatabaseTest</code> ({cnt('TicketDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Operations", "Metric, alert, rollback, runbook; a controlled failure drill", f"<code>OperationsDrillTest</code> ({cnt('OperationsDrillTest')}), and the Production tab", '<span class="pill ok">pass</span>']]) + """
<p class="muted">A pool of 4, 1 s to get a connection, and a test gateway with a 1 s limit: a full pool and a hanging gateway are reached in a second instead of thirty. Concurrency is real: sixteen threads released together.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "PoolExhaustionTrapTest.java", "<p>Written first: the old one-transaction order against the API, sixteen fans at once.</p>"),
    (T + "TicketOrderContractTest.java", "<p>Paid, declined, bad and unknown orders.</p>"),
    (T + "TicketDatabaseTest.java", "<p>Named constraints with plain SQL; a rollback.</p>"),
    (T + "OperationsDrillTest.java", "<p>The drills: a hanging gateway, an empty pool; the metrics.</p>"),
    (T + "TestGateway.java", "<p>A gateway that answers when, and how, the test says.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the small pool, the gateway's address, fresh sales.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/seatsure/sales/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=OrderOutcomeMetricChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "How did the orders end?", "Beginner-friendly", 20,
    "The pool's metrics say whether the database is coping; add one that says how orders end: a counter <code>ticket.orders</code> tagged <code>outcome</code> = paid, declined, gateway_timeout, gateway_error or no_seats.",
    "both tests in <code>OrderOutcomeMetricChallengeTest</code> pass.",
    ["Inject <code>MeterRegistry</code>; <code>counter(name, \"outcome\", value).increment()</code> where each path ends.",
     "Keep tag values few and fixed: never a buyer or an order id."],
    "challenge/OrderOutcomeMetricChallengeTest.java", ["challenge/solution/TicketOrders.java"]) + challenge(2, "A bulkhead for the gateway", "Go deeper", 30,
    "No connection is held during a charge, but a request thread is. Let at most <code>seatsure.payments.max-concurrent</code> charges wait on the gateway at once (4 in the test); the next order is refused at once with <code>503</code> and its seats are given back.",
    "the test in <code>GatewayBulkheadChallengeTest</code> passes.",
    ["A <code>Semaphore</code> with <code>tryAcquire()</code>: refuse instead of queueing.",
     "Release it in a <code>finally</code>, or one exception leaks a place for good.",
     "A generous default (100) keeps normal days unaffected."],
    "challenge/GatewayBulkheadChallengeTest.java", ["challenge/solution/TicketOrders.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>The final, ten times bigger</h2>
<p>The World Cup final sale expects ten times the traffic, on eight servers against one PostgreSQL that allows 200 connections. Work out the pool per server, what happens when the gateway slows to 5 s, and where a queue (a virtual waiting room) belongs. Which number would you alert on first, and at what value?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the one-transaction order, sixteen at once, a small pool.</li>
<li>Split the order into reserve, charge (nothing open), record.</li>
<li>Timeouts on the gateway; a short pool timeout and a <code>503</code> for it.</li>
<li>Metrics, alerts and drills.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Short transactions around the remote call", "Two writes per order; a pending state to handle.", '<span class="pill ok">Chosen</span>'],
    ["One transaction around everything", "A connection per waiting charge: the pool empties.", '<span class="pill bad">The trap</span>'],
    ["A bigger pool", "More database memory; the wall moves, it does not go away.", '<span class="pill warn">Not a fix</span>'],
    ["Charge asynchronously (queue, webhook)", "The buyer waits for a callback; more moving parts.", '<span class="pill warn">For very slow gateways</span>'],
    ["Hikari's default 30 s timeout", "Users wait 30 s for an error.", '<span class="pill bad">Shorten it</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>sales_sold_range</code>", "CHECK sold BETWEEN 0 AND capacity", "No overselling, no negative counts, for any writer."],
    ["<code>orders_seats_range</code>, <code>orders_amount_positive</code>", "CHECKs", "1 to 6 seats; a real amount."],
    ["<code>orders_status</code>, <code>orders_paid_has_charge</code>", "CHECKs", "Known states; paid exactly when a charge id exists."]]) + """
<p><strong>Transaction boundaries:</strong> reserve (seats and pending order) commits on its own; no transaction is open during the charge; the outcome (paid, or failed with seats back) commits on its own.</p>
""" + code(read(M + "V1__sales_and_orders.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["14. Operations: metric, alert, rollback, runbook, failure drill", "15. Real-world considerations"],
               "An Operations station: everything someone on call needs, and a drill to prove it works.") + """
<h2>Operations</h2>
<dl class="facts">
<dt>Metrics</dt><dd><code>hikaricp.connections.pending</code> (requests waiting for a connection), <code>hikaricp.connections.timeout</code> (requests that gave up), <code>hikaricp.connections.usage</code> (how long connections are held). With challenge 1, <code>ticket.orders{outcome}</code>.</dd>
<dt>Alerts</dt><dd>Page when <code>timeout</code> rises at all during a sale, or <code>pending</code> stays above 0 for 1 minute. Warn when the 99th percentile of <code>usage</code> passes 100 ms: something is holding connections. (Starting points; tune them on real traffic.)</dd>
<dt>Rollback</dt><dd>No data shape changes in this release: rolling back is redeploying the previous version. If a release puts a remote call back inside a transaction, <code>usage</code> jumps from milliseconds to seconds: roll back first, investigate after.</dd>
</dl>
<h2>Runbook: \"orders are failing during the sale\"</h2>
<ol class="steps">
<li>Look at the status codes. <code>503</code>s: the pool is empty. <code>504</code>s: the gateway is slow. <code>409</code>s: sold out, not an incident.</li>
<li>For <code>503</code>s: check <code>hikaricp.connections.usage</code>. Connections held for seconds mean a slow query or a remote call inside a transaction; the ERROR line \"No database connection within the pool's timeout\" marks each refusal.</li>
<li>For <code>504</code>s: check the gateway's status page; reads and other pages should still answer at once. If they do not, connections are being held after all: see step 2.</li>
<li>Tell fans to retry: the <code>503</code> says <code>Retry-After: 5</code>. Never raise the pool to fix a slow gateway.</li>
</ol>
<h2>Failure drills</h2>
<ol class="steps">
<li><strong>Gateway hangs.</strong> Make the test gateway wait 10 s (<code>POST /delay</code>), send 20 orders at once: all <code>504</code> after 3 s, <code>GET /sales/1</code> answers at once, <code>timeout</code> stays 0. (Captured on the API contract tab.)</li>
<li><strong>Pool held.</strong> Take every connection from outside the app (a long query, or a test holding them): orders get <code>503</code> after 2 s, the ERROR line appears, and orders work again once the connections are released.</li>
</ol>
<p class="muted">Both drills run on every build as <code>OperationsDrillTest</code> (""" + str(cnt("OperationsDrillTest")) + """ tests, passing in <code>docs/test-run.txt</code>).</p>
<h2>Real-world considerations</h2>
<dl class="facts">
<dt>Pool size</dt><dd>Start small: connections ≈ cores × 2 on the database, divided across servers. Eight servers × 10 = 80 connections.</dd>
<dt>Virtual threads</dt><dd>They make waiting threads cheap, not connections: the pool is still the limit.</dd>
<dt>Leak detection</dt><dd><code>leak-detection-threshold</code> logs a stack trace when a connection is held too long: useful in staging.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why do requests time out while the database is idle?", "The connection pool is empty: every connection is held by a request doing something else (here, waiting on a remote call)."),
    ("What does Hikari's connection timeout do?", "How long a request waits for a free connection before an exception. The default 30 s is far too long for a web request."),
    ("How do you call a payment gateway safely from an order?", "Commit the reservation, call it with no transaction open and with timeouts, then record the result in a new short transaction."),
    ("Is a bigger pool the fix?", "No: the slow calls fill any size, and connections cost database memory."),
    ("Which metrics show this problem?", "Pending requests and timeouts on the pool, and how long connections are held."),
    ("How do you test it?", "A small pool, a slow fake gateway, and many concurrent requests: count the pool timeouts."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Transactions", "Short ones.", "No transaction during any remote call, with the pending state handled."],
    ["Timeouts", "On the gateway.", "On the gateway and the pool, each with an honest answer to the user."],
    ["Operations", "Metrics exposed.", "Alerts, a runbook and drills that run on every build."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("A connection held through every charge",
     "\"One transaction: if anything fails, everything rolls back. No release code needed\": true, and while the gateway thinks, the order holds a database connection. On the night of the sale, slow charges hold the whole pool, and every other request, even a read, waits for one.",
     "<code>theApiHoldsAConnectionForMillisecondsAndEveryFanGetsASeat</code> and <code>aHangingGatewayIsCutOffAndTheDatabaseStaysFree</code> fail."),
    ("A declined order vanishes",
     "The rollback also removes the order row: there is no record that the buyer tried and was declined, nothing for support to look up, nothing to count.",
     "<code>aDeclinedPaymentGivesTheSeatsBack</code> fails: there is no FAILED order."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate \"simplifies\" the order: one <code>@Transactional</code> method, \"so if anything fails, everything rolls back, seats included, and the release code can go\". Read the file and list every problem before opening the findings.</p>
<p class="path">review/TicketOrders.java</p>
""" + code(read("review/TicketOrders.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">With a fast gateway and a few buyers, the flawed version is correct and even simpler. It fails only on the one night that matters: the sale.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
