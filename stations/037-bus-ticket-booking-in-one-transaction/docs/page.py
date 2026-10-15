"""Station 037 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 37,
    "stack": "Spring Boot 4.1.1 · Java 25 · plain JDBC transactions: auto-commit, commit, rollback · generated keys · batch insert · PostgreSQL 17 · Flyway · Testcontainers",
    "simulation": "Trips and fares are demo data, not Safarbus's. A booking is a record in this app's database; no payment is taken and no ticket is issued.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/safarbus/bookings/"
T = "src/test/java/com/safarbus/bookings/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Transaction", "A group of changes that become visible together, or not at all.", "A cheque: either the whole amount moves, or none of it.", "<code>BookingStore.save</code>"),
    ("Auto-commit", "JDBC's default: every statement is its own transaction, saved the moment it runs.", "Posting each page of a letter separately.", "the trap"),
    ("Commit", "Make the transaction's changes permanent and visible.", "Signing the form.", "<code>c.commit()</code>"),
    ("Rollback", "Throw away every change since the transaction began.", "Tearing up the unsigned form.", "<code>c.rollback()</code>"),
    ("Generated key", "An id the database creates on insert and hands back.", "The token number the counter gives you.", "<code>new String[]{\"id\"}</code>"),
    ("Batch", "Many rows for one statement sent together.", "Handing over a stack of forms at once.", "<code>addBatch</code> / <code>executeBatch</code>"),
]
STORY = [
    ("A family books two seats", "The app saves the booking, then each passenger. Each insert is saved the moment it runs."),
    ("Something fails in between", "The server restarts after the booking row, or seat 12 was taken a second earlier. The booking stays, charged for two seats, with one passenger or none. Support finds bookings no conductor can match to anyone."),
    ("The fix", "Booking and passengers in one transaction: all rows are committed together, or a rollback removes them all."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Rows that only make sense together are saved together.</p>

<h2>What are we building?</h2>
<p><code>POST /bookings</code> books up to six seats on a trip, one passenger per seat, and returns the booking id and total. If any seat is taken, nothing is booked.</p>

<h2>An everyday analogy</h2>
<p>A railway reservation form for a family: the clerk enters every name, and only then presses \"confirm\". If one berth is gone, the whole form comes back. Nobody gets a ticket for half a family.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Check the request</strong>: the trip exists, seats are on the bus and different.</li>
<li><strong>Begin</strong>: switch auto-commit off.</li>
<li><strong>Insert</strong> the booking (the database returns its id), then all passengers in one batch.</li>
<li><strong>Commit</strong>, or on any failure <strong>roll back</strong>: no half-booking either way.</li>
</ol>

<details class="qa check"><summary>Check yourself: why can't a CHECK constraint stop a booking with no passengers?</summary><p>A CHECK looks at one row at a time. \"This booking has at least one passenger\" is about rows in another table, which are inserted after the booking. Only a transaction makes them appear together.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No payment.</strong> A confirmed booking is a record.</li>
<li><strong>No seat hold.</strong> A seat is free or booked; holding it while someone pays is challenge 3.</li>
<li><strong>No Spring <code>@Transactional</code>.</strong> Plain JDBC, so every step is visible; Spring does the same for you later.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Safarbus</strong> (a fictional bus operator) found bookings with no passengers: a crash between saving the booking and its passengers left half-saved bookings.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> two passengers for seats 12 and 13 on trip 101, <b>then</b> <code>201</code>, a new booking id, total ₹2,500.00, and two passenger rows.</li>
<li><b>Given</b> seats 11 and 12 when 12 is already booked, <b>then</b> <code>409</code> naming seat 12, and no new rows at all; seat 11 can be booked straight after.</li>
<li><b>Given</b> a failure after the booking row (a crash, a refused passenger, a Java error), <b>then</b> no booking row remains.</li>
<li><b>Given</b> seat 41 on a 40-seat bus, or the same seat twice, <b>then</b> <code>422</code>; an unknown trip, <code>404</code>.</li>
<li><b>Given</b> a bad phone, an age over 120, seat 0, no passengers, seven passengers, or an extra field, <b>then</b> <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>The booking and its passengers are written in one transaction.</li>
<li>One seat on one trip belongs to one booking: a database constraint decides, so two people racing for it cannot both win.</li>
<li>A passenger's trip is always its booking's trip (a composite foreign key).</li>
<li>Money in integer paise; the total is fare × passengers.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Turn auto-commit off, commit, and roll back with plain JDBC.</li>
<li>Read a generated key after an insert.</li>
<li>Insert many rows with a JDBC batch.</li>
<li>Turn a constraint violation into a clear <code>409</code>.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Body"], [
    ["<code>POST</code>", "<code>/bookings</code>", "<code>{\"tripId\", \"contactPhone\", \"passengers\": [{\"name\", \"age\", \"seatNo\"}]}</code>, 1 to 6 passengers."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Booked: every passenger saved"],
    ['<span class="pill warn">400</span>', "A bad phone, name, age or seat number; 0 or more than 6 passengers; an unknown field"],
    ['<span class="pill warn">404</span>', "No such trip"],
    ['<span class="pill warn">409</span>', "A seat is already booked; nothing was saved"],
    ['<span class="pill warn">422</span>', "A seat the bus does not have, or the same seat twice"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against one fresh database. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-a-family-of-two", "Case 1: seats 12 and 13", "<b>Why:</b> one transaction: booking, then both passengers, then commit."),
    ("02-one-seat-already-taken", "Case 2: seats 11 and 12", "<b>Why:</b> seat 12 is taken; the whole transaction is rolled back."),
    ("03-the-free-seat-was-never-held", "Case 3: seat 11 alone", "<b>Why:</b> the failed attempt left nothing behind, so seat 11 is free."),
    ("04-a-seat-the-bus-does-not-have", "Case 4: seat 41", "<b>Why:</b> the bus has 40 seats: <code>422</code>."),
    ("05-no-such-trip", "Case 5: trip 999", "<b>Why:</b> <code>404</code>."),
    ("06-a-bad-phone-number", "Case 6: phone 12345", "<b>Why:</b> <code>400</code>, before the database is touched."),
]) + """
<h2>The database after these six requests</h2>
<p class="muted">Queried with psql right after the captures (<code>docs/captures/db-after.txt</code>). Two bookings, each with all its passengers; nothing from the refused attempt. There is no booking 2: the refused attempt took that id before it was rolled back, and sequences never roll back, so ids can have gaps. Never use them to count bookings.</p>
""" + code(read("docs/captures/db-after.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Two passengers", "<code>201</code>, id 1, both rows", "<code>aBookingSavesEveryPassengerAndReturnsTheNewId</code>"],
    ["One of two seats taken", "<code>409</code>, nothing saved, the other seat stays free", "<code>aTakenSeatIs409AndNothingIsSaved</code>"],
    ["The same seat on another trip", "Allowed", "<code>theSameSeatOnAnotherTripIsFine</code>"],
    ["A passenger the database refuses", "The booking row is rolled back", "<code>aRefusedPassengerRollsBackTheWholeBooking</code>"],
    ["A Java error after the booking row", "The booking row is rolled back", "<code>aJavaErrorMidwayRollsBackToo</code>"],
    ["The process dies before commit", "Nothing is committed", "<code>aDeadConnectionCommitsNothing</code>"],
    ["Phone, age, a passenger on another trip; a seat twice on one trip", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>, <code>oneSeatOnOneTripBelongsToOneBookingOnly</code>"],
    ["Seat 41; the same seat twice", "<code>422</code>", "<code>seatsThatCannotBeBookedAre422</code>"],
    ["Bad fields, 0 or 7 passengers, an extra field", "<code>400</code>", "<code>badBodiesAre400</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Auto-commit on: a crash leaves a booking without its passengers.</p>
<p>The old code runs against the real PostgreSQL. A crash between the two inserts leaves a booking with no passengers. A taken seat halfway leaves a booking charged for two seats with one passenger. The real store, given the same failure, leaves nothing. While building, each fix was undone once. Leaving auto-commit on turned 8 tests red. Removing the rollback turned only 1 red, and only after a test was added for a Java error midway. PostgreSQL will not commit a transaction in which a statement failed, but <code>setAutoCommit(true)</code> in the <code>finally</code> block commits a transaction that had no database error. Not restoring auto-commit was not caught, because HikariCP resets it when the connection returns to the pool. The line stays, so the code does not depend on the pool.</p>
</div>
""" + code(read(T + "AutoCommitTrapTest.java"), "java") + code(read(T + "OldBookingStore.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "BookingController.java", dwn("Checks the request, saves the booking, and turns a taken seat into a <code>409</code>.",
        "Request checks that need the trip (seat range, duplicates) happen before the transaction.",
        "Checking \"is the seat free?\" in Java first: two requests can both see it free. The constraint decides.")),
    (J + "BookingStore.java", dwn("Saves a booking and its passengers as one transaction.",
        "Auto-commit off, two inserts, commit; rollback on any failure; auto-commit restored.",
        "The trap: every insert committed on its own.",
        "<ul><li><code>prepareStatement(sql, new String[]{\"id\"})</code> asks the driver to return the new id.</li><li>The passengers go as one batch: one statement, six rows, one round trip.</li><li>Calling <code>setAutoCommit(true)</code> during a transaction commits it, which is why the rollback must come first.</li></ul>")),
    (J + "Trips.java", "<p>Reads a trip with plain JDBC.</p>"),
    (J + "Passenger.java", "<p>One passenger, with validation for the request.</p>"),
    (J + "Trip.java", "<p>A trip: seats and fare.</p>"),
    (M + "V1__trips_bookings_passengers.sql", dwn("The three tables and their named constraints.",
        "The seat rule and the trip consistency are enforced for every writer.",
        "Two bookings for one seat, or a passenger on a different bus from their booking.")),
    (M + "V2__demo_trips.sql", "<p>Two demo trips.</p>"),
    ("src/main/resources/application.yaml", "<p>The database, problem details, and unknown JSON fields refused.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "BookingsApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/037-bus-ticket-booking-in-one-transaction/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/safarbus/bookings/
│   ├── BookingController.java   ├── BookingStore.java   ├── Trips.java
│   ├── Passenger.java   ├── Trip.java   └── BookingsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__trips_bookings_passengers.sql, V2__demo_trips.sql
├── src/test/java/com/safarbus/bookings/   (see Tests)
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
<p>Watch a transaction from outside. In one terminal, open psql and start a transaction by hand:</p>
""" + code("""docker compose exec postgres psql -U safarbus -d safarbus
BEGIN;
INSERT INTO bookings (trip_id, contact_phone, total_paise) VALUES (101, '9876543210', 125000);""", "sql") + """
<p>In a second terminal, count bookings with <code>docker compose exec postgres psql -U safarbus -d safarbus -c "SELECT count(*) FROM bookings"</code>: the new row is not visible. Type <code>ROLLBACK;</code> in the first, and it never will be.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>current transaction is aborted, commands ignored until end of transaction block</code>", "A statement failed inside a transaction; PostgreSQL refuses the rest.", "Roll back, then start again."],
    ["<code>Batch entry 1 … was aborted</code>", "One row of a batch failed; the message names the constraint.", "Read the constraint name; call <code>getNextException()</code> for every failing row."],
    ["<code>Could not find a valid Docker environment</code>", "Docker is not running.", "Start Docker, then run the tests again."],
    ["<code>Connection to localhost:5432 refused</code>", "PostgreSQL is not up yet.", "<code>docker compose up -d</code>, wait, start the app again."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>BookingContractTest</code> ({cnt('BookingContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>AutoCommitTrapTest</code> ({cnt('AutoCommitTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>BookingDatabaseTest</code> ({cnt('BookingDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "AutoCommitTrapTest.java", "<p>Written first: the old code's half-saved bookings, and the real store's clean failure.</p>"),
    (T + "BookingContractTest.java", "<p>Bookings through HTTP, the taken seat, and every refusal, with row counts after each.</p>"),
    (T + "BookingDatabaseTest.java", "<p>Constraints without Java, a dead connection, rollbacks, generated ids and the batch.</p>"),
    (T + "OldBookingStore.java", "<p>The old code, kept only in tests, with a hook where a crash would hit.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: empty booking tables before each test, row counters.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/safarbus/bookings/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=CancelBookingChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Cancel a booking", "Beginner-friendly", 25,
    "Add <code>DELETE /bookings/{id}</code>: delete the passengers and the booking in one transaction, then the seats are free. <code>204</code>, or <code>404</code> for no such booking.",
    "both tests in <code>CancelBookingChallengeTest</code> pass.",
    ["Children first: passengers reference the booking.",
     "<code>executeUpdate()</code> returns how many rows it deleted: 0 means no such booking."],
    "challenge/CancelBookingChallengeTest.java", ["challenge/solution/BookingStore.java", "challenge/solution/BookingController.java"]) + challenge(2, "Senior fares", "Go deeper", 30,
    "Passengers aged 60 or more pay 75% (demo rule), rounded to the nearest paisa, half up. Each passenger row stores its own fare, and the booking's total is exactly their sum.",
    "both tests in <code>SeniorFareChallengeTest</code> pass.",
    ["One method computes a passenger's fare; the total and each row both use it.",
     "In whole paise: <code>(fare × 75 + 50) / 100</code> rounds half up."],
    "challenge/SeniorFareChallengeTest.java", ["challenge/solution/BookingStore.java", "challenge/solution/BookingController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Holding a seat while the customer pays</h2>
<p>Payment takes up to 5 minutes and happens at a payment gateway, outside this database. You cannot keep a transaction open that long. Design a seat hold: what is stored, when it expires, what happens when payment succeeds after the hold expired, and how the unique constraint changes.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap tests: a crash and a taken seat on the old code.</li>
<li>Write the schema: a unique seat per trip, a composite foreign key.</li>
<li>Write the store: auto-commit off, insert with a generated key, batch, commit, rollback.</li>
<li>Test every failure path: a database error, a Java error, a dead connection.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["One JDBC transaction around both inserts", "A few lines of commit/rollback code.", '<span class="pill ok">Chosen</span>'],
    ["Auto-commit and a cleanup job for orphans", "Customers see half-bookings until the job runs; the job can delete a booking mid-save.", '<span class="pill bad">The trap, plus a patch</span>'],
    ["Spring <code>@Transactional</code>", "The same transaction, without the boilerplate.", '<span class="pill warn">From later stations</span>'],
    ["Check seats with a SELECT first", "Two requests both see the seat free.", '<span class="pill bad">A race</span>'],
    ["Passengers as a JSON column on the booking", "One row, atomic by itself; no seat constraint per trip.", '<span class="pill warn">Loses the seat rule</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Key and constraints", "Why"], [
    ["<code>trips</code>", "PK <code>id</code>. Seats 1 to 60, fare &gt; 0.", "What can be booked."],
    ["<code>bookings</code>", "Identity PK. FK to trips. <code>bookings_phone_digits</code>, total &gt; 0, <code>UNIQUE (id, trip_id)</code>.", "The unique pair lets passengers reference booking and trip together."],
    ["<code>booking_passengers</code>", "PK <code>(booking_id, seat_no)</code>. <code>booking_passengers_booking_fk (booking_id, trip_id)</code>. <code>booking_passengers_seat_once (trip_id, seat_no)</code>. Seat, age, fare checks.", "One seat on one trip, once, decided by the database; a passenger's trip always matches their booking's."]]) + """
<p><strong>Transaction boundary:</strong> <code>BookingStore.save</code>, at PostgreSQL's default <code>READ COMMITTED</code>. The seat check needs no stronger isolation: the unique constraint is checked against every committed and in-progress row, so a second booking for the same seat waits for the first and then fails.</p>
""" + code(read(M + "V1__trips_bookings_passengers.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Short transactions</dt><dd>Keep only database work inside a transaction. A slow call (payment, SMS) inside it holds locks and a pooled connection.</dd>
<dt>Batches</dt><dd>PostgreSQL's driver can rewrite a batch into one multi-row insert (<code>reWriteBatchedInserts=true</code>); measure before turning it on.</dd>
<dt>Finding orphans</dt><dd>A query for bookings without passengers is a cheap health check; after this fix it should always return zero.</dd>
<dt>Retries</dt><dd>A client that times out may retry a booking that did commit. Idempotency keys (station 085) make that safe.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is auto-commit in JDBC?", "The default mode: each statement runs in its own transaction and commits immediately. For several statements that belong together, switch it off, commit at the end, and roll back on failure."),
    ("What happens if you call setAutoCommit(true) in the middle of a transaction?", "The JDBC specification says the transaction is committed. That is why the rollback must happen before auto-commit is restored."),
    ("How do you get a generated id after an insert?", "prepareStatement(sql, new String[]{\"id\"}) or Statement.RETURN_GENERATED_KEYS, then getGeneratedKeys() after executeUpdate(). In PostgreSQL, INSERT ... RETURNING id does the same in SQL."),
    ("Why a batch insert?", "One statement, many parameter sets, sent together: fewer round trips. Inside a transaction, a failing row fails the batch and the rollback undoes it all."),
    ("Who should decide that a seat is free, Java or the database?", "The database, with a unique constraint. A Java check followed by an insert has a gap where another request can take the seat."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You watched an uncommitted row from a second session."],
    ["Transactions", "Commit at the end, rollback on failure.", "Why the rollback comes before <code>setAutoCommit(true)</code>."],
    ["JDBC", "Generated keys and a batch.", "Reading every error of a failed batch."],
    ["Database", "A unique seat per trip.", "The composite foreign key and why it needs a unique pair."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any multi-row write:</p>
<ul class="rules">
<li>Which rows only make sense together? Are they in one transaction?</li>
<li>Is there a rollback on every failure path, including Java exceptions?</li>
<li>Is anything slow (a network call) inside the transaction?</li>
<li>Is \"is it free?\" decided by a constraint, or by a check before the insert?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
