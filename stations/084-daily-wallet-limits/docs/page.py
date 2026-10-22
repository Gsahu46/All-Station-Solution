"""Station 084 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 84,
    "stack": "Spring Boot 4.1.1 · Java 25 · SELECT ... FOR UPDATE on the parent row · IST day boundaries · JdbcClient · triggers · PostgreSQL 17 · Testcontainers",
    "simulation": "The wallets, owners and KYC tiers are demo data, not Tijori's, and the limits are demo rules, not RBI's. Nothing is charged: a top-up creates a record and raises a balance number; where the money comes from is another system.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tijori/wallets/"
T = "src/test/java/com/tijori/wallets/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Wallet", "Money kept in an app, spent by tapping or scanning.", "A prepaid metro card.", "<code>wallets</code>"),
    ("Top-up", "Adding money to the wallet.", "Recharging the metro card.", "<code>POST /wallets/{id}/top-ups</code>"),
    ("KYC tier", "How well the owner has been identified; better identified, higher limits.", "A library card with or without an address proof.", "<code>minimum</code>, <code>full</code>"),
    ("Daily limit", "The most that may be added in one day.", "An ATM's daily cash limit.", "₹10,000 or ₹1,00,000 (demo rules)"),
    ("Parent row", "The one row every change for a thing goes through, here the wallet.", "The one register at a shop counter.", "<code>SELECT ... FOR UPDATE</code> on <code>wallets</code>"),
    ("IST", "India Standard Time, UTC+05:30, no daylight saving.", "Midnight in Delhi is 18:30 in London the day before (in winter).", "<code>Asia/Kolkata</code>"),
]
STORY = [
    ("₹12,000 on a ₹10,000 limit", "Ananya's wallet has the minimum KYC: ₹10,000 of top-ups a day. Her app sent two top-ups of ₹6,000 in the same second (a double tap and a retry). Both went through."),
    ("Why the check did not help", "Each request added up today's top-ups (₹0), saw that ₹6,000 fits, and inserted. Neither could see the other's row, because it was not committed yet. There was no existing row to lock or wait on."),
    ("The fix", "Lock the wallet's row first, then add up, then insert. The second top-up waits at the lock for a few milliseconds, adds up again, sees ₹6,000, and is refused. The day is India's day, from midnight IST."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A limit over many rows needs one row to queue on. Lock the parent (the wallet) before you add up its children (the top-ups).</p>

<h2>What are we building?</h2>
<p>One endpoint: top up a wallet, unless today's top-ups (in India's day) would pass the wallet's KYC limit.</p>

<h2>An everyday analogy</h2>
<p>A shop allows each customer ten items on sale per day. If two cashiers each look at the customer's slip at the same moment, both see room. If the customer must hand the slip to one cashier at a time, the second cashier sees the first one's entry.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Lock</strong> the wallet row. Another top-up for this wallet waits here; other wallets do not.</li>
<li><strong>Add up</strong> this wallet's top-ups from 00:00 IST today.</li>
<li><strong>Decide</strong>: if the new one does not fit, <code>409</code> with how much is left.</li>
<li><strong>Write</strong> the top-up and the new balance, and commit, which releases the lock.</li>
</ol>

<details class="qa check"><summary>Check yourself: Ananya tops up ₹9,000 at 23:59 IST and ₹9,000 at 00:01 IST. Is the second refused?</summary><p>No: 00:01 IST is a new day in India, so ₹9,000 fits. It would be refused if the day were counted in UTC, where both are on the same date: <code>theLimitResetsAtMidnightInIndia</code>.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>Not RBI's rules.</strong> The real rules for prepaid wallets are different and change over time; the limits here are demo rules.</li>
<li><strong>No real money.</strong> A top-up records a row and raises a number; the bank or UPI side is another system.</li>
<li><strong>No retries with a key.</strong> A repeated request is a new top-up here; station 085 shows idempotency keys.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tijori</strong> (a fictional wallet app): two top-ups at the same second took a wallet past the ₹10,000 daily KYC limit.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo wallets: 1001 Ananya, minimum KYC, ₹500 balance; 1002 Vikram, full KYC. Demo rules: minimum KYC ₹10,000 of top-ups a day, full KYC ₹1,00,000; one top-up ₹1 to ₹1,00,000.</p>
<ol class="gwt">
<li><b>Given</b> room today, <b>then</b> <code>201</code>, the new balance and today's total.</li>
<li><b>Given</b> a top-up that passes the limit by even one paisa, <b>then</b> <code>409</code> with how much is left; exactly the limit is allowed.</li>
<li><b>Given</b> ten top-ups at once, <b>then</b> no more get through than fit.</li>
<li><b>Given</b> 00:00 IST, <b>then</b> a new day; 05:30 IST (midnight UTC) is not.</li>
<li><b>Given</b> an unknown wallet, <b>then</b> <code>404</code>; a fraction of a paisa, a missing or out-of-range amount, <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Money in integer paise, never a fraction.</li>
<li>The wallet row is locked before today's top-ups are added up, in the same transaction as the insert.</li>
<li>The database refuses a top-up past the limit from any writer, with the same lock.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>See why summing without a lock lets two writers through, even with correct code.</li>
<li>Lock the parent row before checking a rule over its children.</li>
<li>Count days in the business's time zone, not the server's.</li>
<li>Back the rule with a database trigger that every writer meets.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/wallets/{id}/top-ups</code>", "<code>{amountPaise}</code>: record a top-up within today's limit."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Recorded: the top-up, the new balance, today's total and the limit"],
    ['<span class="pill warn">400</span>', "Amount missing, a fraction, below ₹1 or above ₹1,00,000"],
    ['<span class="pill warn">404</span>', "No such wallet"],
    ['<span class="pill warn">409</span>', "Today's top-ups would pass the limit: <code>remainingTodayPaise</code> says how much still fits"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. JSON bodies are indented for reading; <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-ananya-tops-up-6000", "Case 1: Ananya tops up ₹6,000", "<b>Why:</b> ₹0 so far today: it fits."),
    ("02-ananya-tries-5000-more", "Case 2: ₹5,000 more", "<b>Why:</b> ₹11,000 would pass ₹10,000: <code>409</code>, and the app can offer ₹4,000."),
    ("03-ananya-tops-up-exactly-4000", "Case 3: exactly ₹4,000", "<b>Why:</b> exactly the limit is allowed."),
    ("04-vikram-full-kyc-tops-up-50000", "Case 4: Vikram, full KYC, ₹50,000", "<b>Why:</b> his tier allows ₹1,00,000 a day."),
    ("05-unknown-wallet", "Case 5: a wallet that does not exist", "<b>Why:</b> <code>404</code>."),
    ("06-rupees-sent-as-a-fraction", "Case 6: 4000.5 paise", "<b>Why:</b> paise are whole numbers: <code>400</code>, not rounded."),
    ("07-at-once-1", "Case 7: five top-ups of ₹20,000 for Vikram at the same moment (1 of 5)", "<b>Why:</b> ₹50,000 was left: two fit, three are refused. Which two depends on timing."),
    ("07-at-once-2", "Case 7 (2 of 5)", "<b>Why:</b> see above."),
    ("07-at-once-3", "Case 7 (3 of 5)", "<b>Why:</b> see above."),
    ("07-at-once-4", "Case 7 (4 of 5)", "<b>Why:</b> see above."),
    ("07-at-once-5", "Case 7 (5 of 5)", "<b>Why:</b> see above."),
]) + """
<h2>The wallets and top-ups afterwards</h2>
""" + code(read("docs/captures/wallets.txt").rstrip(), "text") + code(read("docs/captures/top-ups.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A top-up within the limit", "<code>201</code>, balance and today's total", "<code>aTopUpWithinTheLimitIsRecorded</code>"],
    ["Exactly the limit; one paisa more", "Allowed; <code>409</code> with what is left", "<code>exactlyTheLimitIsAllowedAndOnePaisaMoreIsNot</code>"],
    ["Full KYC", "The higher limit", "<code>theLimitDependsOnTheKycTier</code>"],
    ["Unknown wallet; bad amounts", "<code>404</code>; <code>400</code>", "<code>unknownWalletsAre404AndBadAmountsAre400</code>"],
    ["Amounts in messages", "₹1,00,000.00, Indian grouping", "<code>amountsAreShownWithIndianDigitGrouping</code>"],
    ["23:59:59 and 00:00 IST", "Two different days", "<code>theLimitResetsAtMidnightInIndia</code>"],
    ["00:30 and 06:30 IST", "One day, though UTC has two dates", "<code>earlyMorningInIndiaIsTheSameDayAsTheEveningBeforeInUtc</code>"],
    ["Ten top-ups of ₹4,000 at once", "Two <code>201</code>, eight <code>409</code>", "<code>tenTopUpsOfFourThousandAtOnceLetTwoThrough</code>"],
    ["Two wallets at once", "Neither waits for the other", "<code>twoWalletsDoNotWaitForEachOther</code>"],
    ["Plain SQL past the limit", "Refused by <code>top_ups_within_daily_limit</code>", "<code>theDailyLimitHoldsForEveryWriter</code>"],
    ["Two plain SQL writers at once", "The second waits, then is refused", "<code>theDailyLimitHoldsForTwoPlainSqlWritersAtOnce</code>"],
    ["Other rules written by plain SQL", "Refused by named constraints", "<code>otherRulesHoldWithoutJava</code>"],
    ["The balance cannot be raised", "No top-up recorded", "<code>aTopUpWhoseBalanceCannotBeRaisedLeavesNoRecord</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Summing today's top-ups without locking, so two top-ups pass the limit.</p>
<ul>
<li><strong>The old code.</strong> The test opens two real database connections and runs them step by step: both add up ₹0, both insert ₹6,000. A new row has nothing to wait for, so both commit: ₹12,000.</li>
<li><strong>With the wallet locked.</strong> The second connection asks for the wallet's lock and waits. The first inserts and commits; the second then adds up ₹6,000, and another ₹6,000 does not fit.</li>
</ul>
<p>The database rule is switched off in this test, because the old schema had none and because only the application's lock is tested here.</p>
<p>While building, each part was undone once: no wallet lock turned 1 test red; the day in UTC 2; <code>&gt;=</code> instead of <code>&gt;</code> 2; no database rule 4; the rule without its own lock 1; the rule's day in UTC 2; no transaction 2; the balance not raised 3.</p>
</div>
""" + code(read(T + "UnlockedSumTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "TopUpController.java", dwn("The endpoint.", "Checks the amount is whole paise between ₹1 and ₹1,00,000.", "A fraction of a paisa rounded silently.",
        "<p>Jackson accepts <code>4000.5</code> for a <code>long</code> and drops the fraction unless <code>accept-float-as-int</code> is off; <code>application.yaml</code> turns it off.</p>")),
    (J + "TopUps.java", dwn("A top-up within today's limit.",
        "Locks the wallet row, adds up the IST day's top-ups, refuses with what is left, then inserts and raises the balance, in one transaction.",
        "Two top-ups at once both fitting in the same room.",
        "<ul><li>Lock the parent row, not the rows you add up: for the day's first top-up there are none, so a lock on them locks nothing.</li><li>The day runs from 00:00 IST to the next 00:00 IST, computed with <code>Asia/Kolkata</code>; the server's own zone is never used.</li><li><code>NumberFormat</code> for <code>en-IN</code> prints <code>100,000.00</code>: Java's <code>DecimalFormat</code> keeps one grouping size, so <code>rupees</code> groups by hand. Found while building.</li><li>The database rule's refusal is not turned into a <code>409</code>: if it fires, this code let something through, and a 500 says so.</li></ul>")),
    (M + "V1__wallets_and_top_ups.sql", dwn("Tiers, wallets, top-ups and the daily rule.",
        "A trigger before each insert locks the wallet row and adds up the IST day, so plain SQL writers meet the same limit.",
        "A script or a second service topping up past the limit.",
        "<p>Its limits, written in the file: it watches inserts only (changing an amount or a wallet's tier later is not checked), and its day is IST.</p>")),
    (M + "V2__demo_wallets.sql", "<p>Two tiers, two wallets.</p>"),
    ("src/main/resources/application.yaml", "<p>Database connection, and fractions refused for whole-number fields.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "WalletsApplication.java", "<p>Entry point, and the <code>Clock</code> the day is taken from.</p>"),
]
tree = """stations/084-daily-wallet-limits/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/tijori/wallets/
│   ├── TopUpController.java   ├── TopUps.java   └── WalletsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__wallets_and_top_ups.sql, V2__demo_wallets.sql
├── src/test/java/com/tijori/wallets/   (see Tests)
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
<p>Hold Ananya's wallet locked from <code>psql</code> for five seconds, and top up meanwhile, hers and Vikram's:</p>
""" + code("""docker compose exec -T postgres psql -U tijori -d tijori -c "BEGIN; SELECT id FROM wallets WHERE id = 1001 FOR UPDATE; SELECT pg_sleep(5); COMMIT;" > /dev/null &
sleep 1
curl -s -o /dev/null -w '%{http_code} after %{time_total}s\\n' -X POST http://localhost:8080/wallets/1001/top-ups -H 'Content-Type: application/json' -d '{"amountPaise": 100000}'
curl -s -o /dev/null -w '%{http_code} after %{time_total}s\\n' -X POST http://localhost:8080/wallets/1002/top-ups -H 'Content-Type: application/json' -d '{"amountPaise": 100000}'""", "bash") + """
<p>Ananya's top-up prints <code>201</code> after about 4 seconds: it waited at the wallet lock, then added up. Vikram's prints <code>201</code> at once: his wallet was not locked.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Top-ups at the same moment fail with a 500 instead of a <code>409</code>", "The database rule refused top-ups the application let through: the application's lock is missing. Seen while building, with the lock removed.", "Lock the wallet row before adding up, in the same transaction."],
    ["The limit resets at 05:30 in the morning", "The day is counted in UTC (or the server's zone).", "Compute the day in <code>Asia/Kolkata</code>."],
    ["<code>100,000.00</code> where <code>1,00,000.00</code> was expected", "<code>DecimalFormat</code> keeps one grouping size.", "Group by hand, as <code>TopUps.rupees</code> does."],
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>TopUpContractTest</code> ({cnt('TopUpContractTest')}), <code>IstDayBoundaryTest</code> ({cnt('IstDayBoundaryTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>UnlockedSumTrapTest</code> ({cnt('UnlockedSumTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>TopUpDatabaseTest</code> ({cnt('TopUpDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Concurrency", "A real concurrency test that proves the invariant holds", f"<code>TopUpConcurrencyTest</code> ({cnt('TopUpConcurrencyTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">The parallel tests run on virtual threads released by one latch. A trigger makes each top-up take 200 ms to write, so the requests overlap every time. The database rule would stop an over-limit total even without the application's lock, so the test counts answers: with the lock removed, eight of ten requests failed with the rule's error instead of a <code>409</code>. Found while building.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "UnlockedSumTrapTest.java", "<p>Written first: two real transactions, step by step, without and with the wallet lock.</p>"),
    (T + "TopUpConcurrencyTest.java", "<p>Ten top-ups at once; two wallets side by side.</p>"),
    (T + "IstDayBoundaryTest.java", "<p>Midnight in India, and the early morning that UTC puts on another date.</p>"),
    (T + "TopUpDatabaseTest.java", "<p>The rule and named constraints with plain SQL, two plain SQL writers at once, and a rollback.</p>"),
    (T + "TopUpContractTest.java", "<p>The endpoint through HTTP, and the rupee format.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the test clock at noon IST, the demo wallets before each test, request helpers.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tijori/wallets/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=LimitsChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "What is left today", "Beginner-friendly", 20,
    "<code>GET /wallets/{id}/limits</code>: the tier, the daily limit, today's total, what is left, and when the day resets (the next 00:00 IST, as a UTC time).",
    "both tests in <code>LimitsChallengeTest</code> pass.",
    ["Reuse the sum from <code>topUp</code>; a read needs no lock.",
     "<code>resetsAt</code> is tomorrow's IST date at its start of day in <code>Asia/Kolkata</code>."],
    "challenge/LimitsChallengeTest.java", ["challenge/solution/TopUps.java", "challenge/solution/TopUpController.java"]) + challenge(2, "Reverse a top-up", "Go deeper", 35,
    "<code>POST /wallets/{id}/top-ups/{topUpId}/reversal</code>, for a top-up whose money never arrived: the balance goes back down and the amount stops counting towards today's limit. A second reversal answers the same; a top-up already spent is <code>409</code>.",
    "the three tests in <code>ReversalChallengeTest</code> pass.",
    ["Lock the wallet row first, as a top-up does: the balance and today's total change together.",
     "A V3 migration adds <code>reversed_at</code> and changes the rule's function to skip reversed top-ups."],
    "challenge/ReversalChallengeTest.java", ["challenge/solution/TopUps.java", "challenge/solution/TopUpController.java", "challenge/solution/V3__top_up_reversals.sql"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Months, years and tier changes</h2>
<p>Add a monthly and a yearly limit next to the daily one. Adding up a year of top-ups on every request gets slow: design a per-wallet, per-day totals table kept in the same transaction, and say which row to lock. Then: Ananya completes full KYC at 15:00 having topped up ₹10,000. What does she have left today, and what if her tier goes down instead?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: two connections adding up and inserting, step by step.</li>
<li>Lock the wallet row, then add up the IST day, then insert and raise the balance, in one transaction.</li>
<li>Test the day boundary at midnight IST, and the early morning that UTC dates differently.</li>
<li>Add the rule to the database with the same lock, for every other writer.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Lock the wallet row, then sum", "Top-ups for one wallet run one at a time (milliseconds each).", '<span class="pill ok">Chosen</span>'],
    ["Sum without a lock", "Two writers both see room.", '<span class="pill bad">The trap</span>'],
    ["Lock the top-up rows being summed", "For the day's first top-up there are none: nothing is locked.", '<span class="pill bad">Review finding</span>'],
    ["SERIALIZABLE and retry (station 083)", "No explicit lock; retries under contention.", '<span class="pill warn">Also correct</span>'],
    ["A daily totals row with a CHECK", "<code>INSERT ... ON CONFLICT DO UPDATE SET total = total + x</code>; the row lock does the queueing. A second table to keep right.", '<span class="pill warn">Good at high volume</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>top_ups_within_daily_limit</code>", "Trigger before insert", "The rule spans rows and a tier table, so a CHECK cannot hold it. It locks the wallet row, like the application."],
    ["<code>top_ups_wallet_time</code>", "Index on (wallet, time)", "Adding up one wallet's day reads only its rows."],
    ["<code>wallets_balance_not_negative</code>, <code>top_ups_amount_positive</code>", "CHECKs", "No negative balance, no zero top-up."],
    ["<code>wallets_tier_fk</code>, <code>kyc_tiers_limit_positive</code>", "FK, CHECK", "Every wallet has a known tier with a real limit."]]) + """
<p><strong>Transaction boundary:</strong> one transaction locks the wallet, adds up, inserts the top-up and raises the balance. The lock ends with the commit.</p>
""" + code(read(M + "V1__wallets_and_top_ups.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Regulation</dt><dd>Real wallet limits come from the regulator and the company's policy, by month and year as well as by day, and they change. Keep them in data (<code>kyc_tiers</code>), not code.</dd>
<dt>Keep the lock short</dt><dd>Nothing slow (a bank call, a notification) inside the locked transaction; station 082 shows why.</dd>
<dt>Retries</dt><dd>A phone that retries a top-up needs an idempotency key (station 085), or the limit is spent twice for one payment.</dd>
<dt>Time zones</dt><dd>Store instants (<code>timestamptz</code>); compute business days in the business's zone, in one place.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why can two top-ups pass a limit when each one checks it?", "Each transaction adds up the committed top-ups, and neither can see the other's uncommitted row. Inserting a new row waits for nothing, so both commit."),
    ("Why lock the wallet row and not the top-up rows?", "The new top-up is a row that does not exist yet; locking existing rows does not stop a new one, and for the day's first top-up there is nothing to lock. Every writer touches the wallet row, so it is the place to queue."),
    ("Does SELECT ... FOR UPDATE slow other wallets?", "No: it locks one row. Only top-ups for the same wallet wait, for as long as the transaction lasts."),
    ("Where does the day start?", "Where the business says: here 00:00 IST, which is 18:30 UTC the evening before. Never the server's zone."),
    ("Why a trigger as well?", "Scripts and other services write too. The trigger takes the same lock, so they meet the same limit, and a refusal from it shows a bug in the application."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Locking", "The limit holds under parallel top-ups.", "You can say why locking the summed rows does not work."],
    ["Time", "The day resets.", "At midnight IST, tested on both sides and at 05:30 IST."],
    ["Database", "A rule in the database.", "One that holds for two plain SQL writers at once."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("Locking the rows it adds up",
     "\"Lock only what we read\" sounds careful, but the next top-up is a new row: nothing stops it. For the day's first top-ups there are no rows at all, so ten requests at once each lock nothing and each see ₹0. The database rule then refuses the extras with an error, not a clear answer.",
     "<code>tenTopUpsOfFourThousandAtOnceLetTwoThrough</code> fails."),
    ("The day taken from the server clock",
     "<code>LocalDate.now(clock)</code> uses the clock's zone, UTC here, so the application's day runs from 05:30 IST. Just after midnight in India it refuses a top-up that fits, and at 06:30 IST it lets through one the database rule (which counts in IST) then refuses with an error.",
     "<code>theLimitResetsAtMidnightInIndia</code> and <code>earlyMorningInIndiaIsTheSameDayAsTheEveningBeforeInUtc</code> fail."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate \"narrows the lock\": instead of locking the whole wallet, the top-up locks only today's top-up rows it adds up, so other wallet updates are not blocked. They also tidy the day calculation to <code>LocalDate.now(clock)</code>. Read the file and list every problem before opening the findings.</p>
<p class="path">review/TopUps.java</p>
""" + code(read("review/TopUps.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">Both changes pass every single-request test. One shows only under parallel requests, the other only between midnight and 05:30 in India: exactly when nobody is testing by hand.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
