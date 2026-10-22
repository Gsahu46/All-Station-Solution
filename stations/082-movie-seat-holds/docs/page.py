"""Station 082 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 82,
    "stack": "Spring Boot 4.1.1 · Java 25 · SELECT ... FOR UPDATE, lock_timeout, SKIP LOCKED · JdbcClient · TransactionTemplate · PostgreSQL 17 · Testcontainers",
    "simulation": "The show, seats and customers are demo data, not SeatSure's. Payments are simulated: a charge records a reference after a short wait, a refund records that it happened; nothing is charged.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/seatsure/holds/"
T = "src/test/java/com/seatsure/holds/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Hold", "A seat kept for one customer for 10 minutes while they pay.", "A shop assistant putting a shirt aside.", "<code>holds</code>"),
    ("Row lock", "While one transaction works on a row, others wanting it wait.", "One hand on the shirt at a time.", "<code>SELECT ... FOR UPDATE</code>"),
    ("Lock timeout", "The longest a request waits for a lock before giving up.", "Waiting two minutes at the counter, then coming back later.", "<code>lock_timeout</code>, 2 s"),
    ("SKIP LOCKED", "Take rows nobody is locking right now, instead of waiting.", "Picking any free till instead of the busy one.", "\"any two seats\""),
    ("Remote call", "A request to another system, here the payment provider: slow, sometimes very slow.", "Phoning the bank.", "<code>Payments.charge</code>"),
    ("Pessimistic and optimistic", "Lock first, then decide; or decide, then check nobody changed it.", "Reserving a table, or walking in and seeing.", "this station locks; station 080 checks a version"),
]
STORY = [
    ("F12, twice", "Two people paid for seat F12 at the same show. Both saw it free, both bought it."),
    ("A fix that froze the box office", "The first fix locked the seat, then called the payment provider while still holding the lock, and waited for locks forever. One evening the provider took 30 seconds per payment: every customer for that seat, and the servers, waited with it."),
    ("The fix", "Lock only for the milliseconds it takes to mark the seat held, never wait longer than two seconds, and pay with no lock at all. Booking is one short update afterwards."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Hold a lock for as little as possible, never across a call to someone else, and never wait for one forever.</p>

<h2>What are we building?</h2>
<p>Hold named seats (or any free ones) for 10 minutes, then confirm: pay, then book.</p>

<h2>An everyday analogy</h2>
<p>At a ticket window, the clerk puts your tickets in an envelope with your name and a time on it. You go to the bank machine with nothing locked. When you come back, the envelope is either still yours, or it expired and went back on sale.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Hold</strong>: lock the seat rows, check they are free, mark them held for 10 minutes, unlock. Milliseconds.</li>
<li><strong>Busy?</strong> If someone else has them locked for more than 2 seconds, answer \"try again\" instead of waiting.</li>
<li><strong>Pay</strong>: the provider is called with no lock held.</li>
<li><strong>Book</strong>: one update turns this hold's seats into bookings, if they are still this hold's.</li>
</ol>

<details class="qa check"><summary>Check yourself: Meera's payment takes 20 seconds. Can Arjun hold F13, next to her F12, meanwhile?</summary><p>Yes, at once. Nothing is locked while Meera pays, so F12 answers \"taken\" immediately and F13 is simply free: <code>theApiPaysWithoutHoldingAnyLock</code>.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real payments.</strong> A simulated provider waits, then records a reference.</li>
<li><strong>No seat map.</strong> Seats are read in the captures with <code>psql</code>.</li>
<li><strong>No sign-in.</strong> The customer is a name in the body.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>SeatSure</strong> (a fictional cinema booking app): two people paid for seat F12 in the same show.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo show: rows E, F and G, seats 10 to 14; row F ₹350, the others ₹250. Demo rules: holds last 10 minutes, at most 6 seats, nobody waits more than 2 seconds for a lock.</p>
<ol class="gwt">
<li><b>Given</b> free seats, <b>then</b> a hold for all of them, or none (<code>201</code>).</li>
<li><b>Given</b> a seat someone holds or booked, <b>then</b> <code>409</code> naming it.</li>
<li><b>Given</b> a seat someone else is locking for more than 2 seconds, <b>then</b> <code>503</code> with <code>Retry-After</code>.</li>
<li><b>Given</b> ten people holding F12 at once, <b>then</b> one hold.</li>
<li><b>Given</b> a confirm, <b>then</b> payment with no lock held, then the seats booked; a second confirm answers the same.</li>
<li><b>Given</b> a hold whose seats someone took after it ran out, <b>then</b> the payment is refunded and the confirm is <code>409</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>No transaction holds a lock while calling another system.</li>
<li>Every lock wait has a limit.</li>
<li>The database refuses a seat that is both booked and held.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Use <code>SELECT ... FOR UPDATE</code> for all-or-nothing holds.</li>
<li>Set a lock timeout per transaction and turn it into a useful answer.</li>
<li>Use <code>SKIP LOCKED</code> for \"any free one\" and for work queues.</li>
<li>Keep remote calls out of transactions, and handle what changes while they run.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/shows/{id}/holds</code>", "<code>{customer, seats: [\"F12\", ...]}</code> or <code>{customer, count}</code>: a hold for 10 minutes."],
    ["<code>POST</code>", "<code>/holds/{id}/confirm</code>", "Pay (simulated), then book the hold's seats."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span> / <span class="pill ok">201</span>', "Confirmed (also for a second confirm) / held"],
    ['<span class="pill warn">400</span>', "Both or neither of seats and count; a seat name of the wrong shape; more than 6"],
    ['<span class="pill warn">404</span>', "No such show, seat or hold"],
    ['<span class="pill warn">409</span>', "A seat taken; a hold expired; the seats taken after the hold ran out (payment refunded)"],
    ['<span class="pill warn">503</span>', "Someone else is locking the seat for longer than 2 seconds: <code>Retry-After: 1</code>"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. JSON bodies are indented for reading; <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-meera-holds-f12-and-f13", "Case 1: Meera holds F12 and F13", "<b>Why:</b> both free: one hold, ₹700, for 10 minutes."),
    ("02-arjun-asks-for-f12", "Case 2: Arjun asks for F11 and F12", "<b>Why:</b> F12 is held: <code>409</code>, and F11 is not held either (all or none)."),
    ("03-arjun-asks-for-any-two", "Case 3: Arjun asks for any two", "<b>Why:</b> the first two free seats."),
    ("04-meera-confirms", "Case 4: Meera confirms", "<b>Why:</b> paid with no lock held, then booked."),
    ("05-meera-confirms-again", "Case 5: Meera's app retries", "<b>Why:</b> the same answer, no second charge."),
    ("06-a-seat-locked-by-someone-else", "Case 6: G12, locked for 4 seconds by another transaction", "<b>Why:</b> <code>503</code> after the 2-second limit, with <code>Retry-After</code>."),
    ("07-both-seats-and-count", "Case 7: seats and count together", "<b>Why:</b> <code>400</code>."),
]) + """
<p class="muted">Case 6, timed by <code>docs/capture.sh</code>: """ + read("docs/captures/lock-wait.txt").strip() + """.</p>
<h2>The seats and holds afterwards</h2>
""" + code(read("docs/captures/seats.txt").rstrip(), "text") + code(read("docs/captures/holds.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Named seats", "Held for 10 minutes, priced", "<code>namedSeatsAreHeldForTenMinutes</code>"],
    ["Any two seats", "The first two free", "<code>anyTwoSeatsCanBeAskedFor</code>"],
    ["Confirm, and confirm again", "Booked; the same answer", "<code>confirmingBooksTheSeatsAndASecondConfirmAnswersTheSame</code>"],
    ["A taken seat among others", "<code>409</code> naming it; the others not held", "<code>aTakenSeatIs409AndNamesIt</code>"],
    ["An expired hold", "<code>409</code>; the seat is free again", "<code>anExpiredHoldCannotBeConfirmedAndTheSeatIsFreeAgain</code>"],
    ["Unknown seat or hold; bad bodies", "<code>404</code>; <code>400</code>", "<code>unknownThingsAre404AndBadBodiesAre400</code>"],
    ["Ten holds of F12 at once", "One hold", "<code>tenPeopleHoldingF12AtOnceGetOneHold</code>"],
    ["Seven \"any two\" at once", "Fourteen different seats", "<code>sevenPeopleAskingForAnyTwoGetFourteenDifferentSeats</code>"],
    ["A hold taken over while paying", "Refunded, <code>409</code>, the seat not booked for Meera", "<code>aHoldThatRunsOutWhilePayingIsRefunded</code>"],
    ["Rules written by plain SQL", "Refused by named constraints", "<code>seatAndHoldRulesHoldWithoutJava</code>"],
    ["A hold that cannot be written", "No seat held", "<code>aHoldThatCannotBeWrittenHoldsNoSeat</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Locking without a timeout, or holding locks across remote calls.</p>
<ul>
<li><strong>The old confirm.</strong> The test runs it against the real database: lock F12, then \"call the provider\" for 3 seconds inside the same transaction. The old code had no lock timeout, so everyone asking for F12 waited too. The API answers within the half-second limit set for tests: <code>503</code>, <code>Retry-After: 1</code>; once the lock is gone, F12 can be held.</li>
<li><strong>The API's confirm.</strong> With a 2-second provider, F12 answers \"taken\" at once and F13 next to it is free: nothing is locked while paying.</li>
</ul>
<p>While building, each part was undone once: no <code>FOR UPDATE</code> turned 1 test red; no lock timeout 1; no <code>SKIP LOCKED</code> 1; a confirm that charges again 1; the lock timeout not turned into a <code>503</code> 1. The first parallel tests passed with <code>FOR UPDATE</code> and <code>SKIP LOCKED</code> removed: see Tests.</p>
</div>
""" + code(read(T + "LockAcrossPaymentTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "Holds.java", dwn("Holding, picking and confirming seats.",
        "Short transactions with a lock timeout; <code>FOR UPDATE</code> for named seats, <code>SKIP LOCKED</code> for any; payment outside any transaction; booking by one update on the hold id.",
        "Double-sold seats, customers stuck behind a slow provider, and seats paid for twice.",
        "<ul><li>Spring 7 reports PostgreSQL's lock timeout (SQLState 55P03) as <code>UncategorizedSQLException</code>, not <code>CannotAcquireLockException</code>: the code matches the SQLState. Found while building.</li><li>The lock timeout is set with <code>set_config('lock_timeout', ..., true)</code>, the function form of <code>SET LOCAL</code>, so it ends with the transaction.</li><li>A hold that ran out while paying, but whose seats nobody took, still books. A first version also required <code>held_until &gt; now</code>; removing it changed no test, because the hold id already changes when someone else takes the seat.</li><li>Times are cut to microseconds: PostgreSQL keeps no more, and the API answered a different <code>expiresAt</code> before and after storing it. Found in the captures.</li></ul>")),
    (J + "HoldController.java", dwn("The two endpoints.", "Seats or count, never both; the lock timeout becomes <code>503</code> with <code>Retry-After</code>.", "A request hanging until a load balancer gives up.")),
    (J + "Payments.java", "<p>The simulated provider: waits, then records a reference; the same hold always gets the same reference.</p>"),
    (M + "V1__shows_seats_holds.sql", dwn("Shows, seats and holds.",
        "One row per seat (its row lock is the seat's lock); a hold has an id and an end together; a booked seat is not held.",
        "Seat states that cannot exist.")),
    (M + "V2__demo_show.sql", "<p>One show, fifteen seats.</p>"),
    ("src/main/resources/application.yaml", "<p>The demo rules: 10-minute holds, a 2-second lock timeout, the simulated provider's delay.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "HoldsApplication.java", "<p>Entry point, and the <code>Clock</code> every expiry uses.</p>"),
]
tree = """stations/082-movie-seat-holds/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/seatsure/holds/
│   ├── Holds.java   ├── HoldController.java   ├── Payments.java   └── HoldsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__shows_seats_holds.sql, V2__demo_show.sql
├── src/test/java/com/seatsure/holds/   (see Tests)
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
<p>Lock a seat from <code>psql</code> for five seconds, and ask the API for it meanwhile:</p>
""" + code("""docker compose exec -T postgres psql -U seatsure -d seatsure -c "BEGIN; SELECT * FROM seats WHERE seat_no = 'G10' FOR UPDATE; SELECT pg_sleep(5); COMMIT;" > /dev/null &
sleep 1
curl -s -o /dev/null -w '%{http_code} after %{time_total}s\\n' -X POST http://localhost:8080/shows/1/holds -H 'Content-Type: application/json' -d '{"customer": "you", "seats": ["G10"]}'""", "bash") + """
<p>It prints <code>503</code> after about 2 seconds. Run the <code>curl</code> again once the five seconds are over: <code>201</code>.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>canceling statement due to lock timeout</code> (SQLState 55P03) as a 500", "Spring's translation of 55P03 is not <code>CannotAcquireLockException</code>.", "Match the SQLState, as <code>Holds</code> does. Found while building this station."],
    ["Parallel tests pass even with the lock removed", "The race window is too small for the test to hit it.", "Widen it on purpose (here a 200 ms trigger), and check the test fails without the lock."],
    ["<code>expiresAt</code> differs between create and read", "Java nanoseconds against PostgreSQL microseconds.", "Truncate the clock to microseconds."],
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>HoldContractTest</code> ({cnt('HoldContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>LockAcrossPaymentTrapTest</code> ({cnt('LockAcrossPaymentTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>HoldDatabaseTest</code> ({cnt('HoldDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Concurrency", "A real concurrency test that proves the invariant holds", f"<code>HoldConcurrencyTest</code> ({cnt('HoldConcurrencyTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">The parallel tests run on virtual threads released by one latch. Their first version passed with <code>FOR UPDATE</code> and <code>SKIP LOCKED</code> removed: the requests barely overlapped, so the race never happened. A trigger now makes each hold take 200 ms to write, as on a busy database, and without the locks those tests fail every time. Found while building. Tests use a lock timeout of 500 ms.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "LockAcrossPaymentTrapTest.java", "<p>Written first: the old lock held across a payment, against the API's timeout and lock-free payment.</p>"),
    (T + "HoldConcurrencyTest.java", "<p>Ten holders of one seat, seven pickers, a hold taken over while paying.</p>"),
    (T + "HoldDatabaseTest.java", "<p>Named constraints with plain SQL; a hold that cannot be written holds nothing.</p>"),
    (T + "HoldContractTest.java", "<p>Holds and confirms through HTTP.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the test clock, free seats and a fast provider before each test, request helpers.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/seatsure/holds/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=ReleaseHoldChallengeTest</code> (Docker must be running). The sweeper test does not compile until <code>HoldSweeper</code> exists.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Give the seats back", "Beginner-friendly", 25,
    "<code>DELETE /holds/{id}</code> frees the hold's seats at once (<code>204</code>); a confirmed hold stays (<code>409</code>).",
    "both tests in <code>ReleaseHoldChallengeTest</code> pass.",
    ["Lock the hold row, check it is still held, clear its seats, mark it released.",
     "The database refuses the new status until a V3 migration changes <code>holds_status</code>; challenge 2 needs the same."],
    "challenge/ReleaseHoldChallengeTest.java", ["challenge/solution/Holds.java", "challenge/solution/HoldController.java", "challenge/solution/V3__expired_holds.sql"]) + challenge(2, "Sweep expired holds, twice at once", "Go deeper", 35,
    "<code>HoldSweeper.sweep(batchSize)</code> marks expired holds <code>expired</code> and clears their seats. Two app instances run it at the same moment: they share the work and no hold is swept twice.",
    "the test in <code>ExpiredHoldSweepChallengeTest</code> passes.",
    ["<code>SELECT ... FOR UPDATE SKIP LOCKED LIMIT n</code> makes the holds table a work queue.",
     "<code>holds_confirmed_paid</code> must allow released and expired holds without a payment reference."],
    "challenge/ExpiredHoldSweepChallengeTest.java", ["challenge/solution/HoldSweeper.java", "challenge/solution/V3__expired_holds.sql"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Without row locks, and on release day</h2>
<p>Design holds without <code>FOR UPDATE</code>: one conditional <code>UPDATE seats ... WHERE hold_id IS NULL</code> per seat, and what \"all or none\" then needs. Then: tickets for a big release open at 10:00 and 200,000 people arrive. Where do locks stop scaling, and how would a waiting room (a queue in front of holds) change the design?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: a lock held across a slow payment.</li>
<li>One row per seat; hold with <code>FOR UPDATE</code> in a short transaction with a lock timeout.</li>
<li>Pick \"any\" seats with <code>SKIP LOCKED</code>.</li>
<li>Pay outside any transaction; book with one update; refund if the seats were taken meanwhile.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Short FOR UPDATE with a lock timeout; pay without locks", "A hold can run out while paying: refund needed.", '<span class="pill ok">Chosen</span>'],
    ["Lock across the payment call", "Everyone waits on the slowest provider.", '<span class="pill bad">The trap</span>'],
    ["Locks with no timeout", "Requests pile up behind one stuck transaction.", '<span class="pill bad">The trap</span>'],
    ["Optimistic: conditional UPDATE per seat", "No waiting at all; all-or-none needs care across several seats.", '<span class="pill warn">Good for one seat</span>'],
    ["Holds in Valkey with expiring keys", "Fast; a second store to keep consistent with bookings.", '<span class="pill warn">At very high load</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>seats_pk</code>", "One row per seat per show", "The row lock is the seat's lock."],
    ["<code>seats_hold_complete</code>, <code>seats_booked_not_held</code>", "CHECKs", "A seat is free, held until a time, or booked: nothing in between."],
    ["<code>holds_confirmed_paid</code>", "CHECK", "No confirmed hold without a payment reference."],
    ["<code>holds_some_seats</code>, <code>holds_total_positive</code>", "CHECKs", "Every hold is for something."]]) + """
<p><strong>Transaction boundaries:</strong> a hold is one short transaction (seats and hold row). The payment is outside any transaction. Booking is one more short transaction.</p>
""" + code(read(M + "V1__shows_seats_holds.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Timeouts everywhere</dt><dd>Lock timeout per transaction, a statement timeout for the rest, and a time limit on the provider call. The lock timeout must be shorter than whatever sits in front of the app (load balancer, client).</dd>
<dt>Lock waits</dt><dd>Watch lock waits in PostgreSQL (<code>pg_locks</code>, <code>log_lock_waits</code>); a rising count of 503s means a long transaction somewhere.</dd>
<dt>Refunds</dt><dd>A refund after a taken-over hold must really happen: put it in an outbox and retry it, not in a log line.</dd>
<dt>Expired holds</dt><dd>Expired holds free their seats by time alone; a sweeper (challenge 2) keeps the tables tidy.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why not hold a lock while calling the payment provider?", "The provider's slowest moment becomes everyone's waiting time, and connections and threads pile up behind the lock. Keep transactions short and make remote calls outside them."),
    ("What does lock_timeout do?", "It makes a statement give up after waiting that long for a lock, instead of waiting forever; the error (SQLState 55P03) can become a \"try again\" answer."),
    ("When is SKIP LOCKED right?", "When any of several rows will do: picking free seats, taking jobs from a queue. It is wrong when you need specific rows."),
    ("Pessimistic or optimistic?", "Pessimistic (lock, then check) when conflicts are common and the work is short, like hot seats. Optimistic (check a version on write) when conflicts are rare, like editing a task."),
    ("How do you test a race?", "Run the requests in parallel with a start latch, and make sure the test fails without the fix; widen the window if it does not."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Locking", "No seat sold twice.", "Locks short, bounded, never across a remote call."],
    ["Answers", "409 for taken.", "503 with Retry-After for busy, and a refund path."],
    ["Proof", "A parallel test.", "One that fails without the lock, every time."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("Payment inside the seat transaction",
     "\"Never booked without a payment\" is bought by holding the seat locks for the whole provider call. A slow provider now freezes every request for those seats, and the confirm that re-holds the seats waits behind it.",
     "<code>theApiPaysWithoutHoldingAnyLock</code> and <code>aHoldThatRunsOutWhilePayingIsRefunded</code> fail."),
    ("No lock timeout",
     "\"Customers saw try-again errors\": now they wait, as long as the longest lock. With the first flaw, that is as long as the slowest payment.",
     "<code>aLockHeldAcrossASlowPaymentMadeEveryoneElseWait</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate makes booking \"atomic\": the confirm locks the hold's seats, charges, and books, all in one transaction. They also remove the lock timeout, because customers complained about \"try again\" errors. Read the file and list every problem before opening the findings.</p>
<p class="path">review/Holds.java</p>
""" + code(read("review/Holds.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">Both changes answer real complaints, and both look safer. The tests that fail are the ones with a slow provider: in production that is a bad evening, not a normal day.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
