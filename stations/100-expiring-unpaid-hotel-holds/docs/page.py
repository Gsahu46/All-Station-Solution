"""Station 100 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 100,
    "stack": "Spring Boot 4.1.1 · Java 25 · @Scheduled (fixed delay) · idempotent batch UPDATE ... RETURNING · FOR UPDATE SKIP LOCKED · Idempotency-Key · JdbcClient · PostgreSQL 17 · Testcontainers · Awaitility",
    "simulation": "The hotel, its rooms and the guests are demo data. No payment happens: a hold only reserves a room in the database for 15 minutes.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/ghoomo/holds/"
T = "src/test/java/com/ghoomo/holds/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Hold", "A room kept for one guest for a short time while they pay.", "A shop keeping a dress aside for 15 minutes.", "<code>holds</code>"),
    ("Scheduled job", "Code the app runs by itself on a timetable.", "A watchman's round every half hour.", "<code>@Scheduled</code>"),
    ("Fixed delay", "The next run starts a set time after the last one ended.", "\"Thirty seconds after you finish, go again\".", "30 s"),
    ("Cron", "Runs at set clock times.", "\"At :00 and :30 of every hour\".", "not used"),
    ("Idempotent", "Doing it twice has the same effect as doing it once.", "Pressing a lift button twice.", "<code>WHERE status = 'HELD'</code>"),
    ("Idempotency-Key", "A key the client sends so a retried request is recognised.", "A token number at the counter.", "<code>Idempotency-Key</code> header"),
]
STORY = [
    ("Rooms that never come back", "On Ghoomo, a guest holds a room while paying. Many never pay. With no clean-up, their holds blocked rooms for days during the Christmas rush."),
    ("Two servers, one job", "A clean-up job fixed that, until a second server was added. Both ran the job at the same moment, both found the same expired hold, and both gave its room back: the hotel thought it had a free room it did not have, and sold it twice."),
    ("The fix", "The job runs on every server, but expiring a hold and giving its room back happen in one statement that only touches holds still held. Whoever runs it, however often, each room comes back once."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A scheduled job will run on every server. Write it so running it twice at once is harmless.</p>

<h2>What are we building?</h2>
<p>Room holds that last 15 minutes, a clean-up job that frees the rooms of unpaid ones, and a hold request that is safe to retry.</p>

<h2>An everyday analogy</h2>
<p>Two watchmen do the same round. If each one hands back the keys of every room past its time, a room's key is handed back twice and the counter thinks two rooms are free. If the rule is \"take the key off the hook only if it is still on the hook\", the second watchman finds nothing to do.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Hold</strong>: take a room if one is free, in one statement, and record the hold for 15 minutes.</li>
<li><strong>Retry</strong>: the same Idempotency-Key and request return the same hold, not a second room.</li>
<li><strong>Expire</strong>: every 30 s, each server marks holds that are due and still held as expired, and gets back which rooms they had.</li>
<li><strong>Give back</strong>: only those rooms, in the same transaction.</li>
</ol>

<details class="qa check"><summary>Check yourself: why not just make sure the job runs on one server only?</summary><p>That helps (and saves work), but it is a promise kept by another system: a lock that expires, a leader that changes. If the job is also harmless when it runs twice, a broken promise costs some wasted work instead of an overbooked hotel. Challenge 3 adds the lock on top.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No payments.</strong> Challenge 1 adds a confirmation; nothing is charged.</li>
<li><strong>One night per hold</strong>, one room type per request (demo rules).</li>
<li><strong>No sign-in.</strong> Holds show no guest details.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Ghoomo</strong> (a fictional hotel booking site): unpaid holds block rooms for days; the cleanup job runs twice when there are two servers.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo hotel: 5 deluxe rooms (type 1) and 1 suite (type 2) for each night from 24 to 31 December 2026. Demo rules: a hold lasts 15 minutes; the job checks every 30 s.</p>
<ol class="gwt">
<li><b>Given</b> a free room, <b>then</b> <code>201</code> with the hold and when it expires; none free <code>409</code>.</li>
<li><b>Given</b> the same <code>Idempotency-Key</code> and request again, <b>then</b> <code>200</code> with the same hold, even if that took the last room; another request with that key <code>422</code>.</li>
<li><b>Given</b> 15 minutes without payment, <b>then</b> the job marks the hold <code>EXPIRED</code> and the room is free again.</li>
<li><b>Given</b> the job running on several servers at once, <b>then</b> each expired hold gives its room back once.</li>
<li><b>Given</b> twenty guests at once for five rooms, <b>then</b> exactly five holds.</li>
<li><b>Given</b> no key, a bad date or e-mail, <b>then</b> <code>400</code>; an unknown night or hold <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Never more rooms held than there are, in the database too.</li>
<li>A hold and its room are taken, and given back, in one transaction.</li>
<li>The job is safe to run on every server at the same moment.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Schedule a job and choose fixed delay or cron.</li>
<li>Write an idempotent batch update with <code>UPDATE ... RETURNING</code> and <code>SKIP LOCKED</code>.</li>
<li>Take a limited resource with one conditional <code>UPDATE</code>.</li>
<li>Make a create request safe to retry with an Idempotency-Key.</li>
<li>Prove all of it with parallel tests and a clock you move.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/holds</code> with <code>Idempotency-Key</code>", "Hold a room for one night: <code>{roomTypeId, date, guestEmail}</code>."],
    ["<code>GET</code>", "<code>/holds/{id}</code>", "A hold and its status: <code>HELD</code> or <code>EXPIRED</code>."]]) + """
<p class="muted">The Idempotency-Key header is the one described in <i>The Idempotency-Key HTTP Header Field</i>, an Internet-Draft of the IETF httpapi working group: a draft, not a standard.</p>
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Hold created"],
    ['<span class="pill ok">200</span>', "The same key and request again: the same hold; a read"],
    ['<span class="pill warn">400</span>', "No or a malformed key; a bad date, e-mail or room type"],
    ['<span class="pill warn">404</span>', "No such room night, or hold"],
    ['<span class="pill warn">409</span>', "No room of that type is free that night"],
    ['<span class="pill warn">422</span>', "The key was used for a different hold"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. To skip 15 minutes of waiting, <code>docs/capture.sh</code> moves hold 1's times back 20 minutes in the database; the real job, every 30 s, does the rest. <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-asha-holds-the-suite-for-new-years-eve", "Case 1: Asha holds the suite for New Year's Eve", "<b>Why:</b> <code>201</code>, held for 15 minutes."),
    ("02-her-app-retries", "Case 2: her app retries", "<b>Why:</b> <code>200</code>, the same hold: although the only suite is taken, it is hers."),
    ("03-the-same-key-for-another-night", "Case 3: the same key, another night", "<b>Why:</b> <code>422</code>."),
    ("04-ravi-wants-the-suite-too", "Case 4: Ravi wants the suite too", "<b>Why:</b> <code>409</code>."),
    ("05-no-idempotency-key", "Case 5: no Idempotency-Key", "<b>Why:</b> <code>400</code>."),
    ("06-a-night-the-hotel-does-not-sell", "Case 6: a night the hotel does not sell", "<b>Why:</b> <code>404</code>."),
    ("07-asha-has-not-paid-yet", "Case 7: Asha has not paid yet", "<b>Why:</b> still <code>HELD</code>."),
    ("08-the-job-expired-it", "Case 8: after its time, the job expired it", "<b>Why:</b> <code>EXPIRED</code>, by the scheduled job, not by a request."),
    ("09-ravi-tries-again", "Case 9: Ravi tries again", "<b>Why:</b> <code>201</code>: the suite is free again."),
]) + """
<h2>The database afterwards</h2>
""" + code(read("docs/captures/holds.txt").rstrip() + "\n\n" + read("docs/captures/room-nights.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["The old job on two servers", "One hold, two rooms back; six guests in five rooms", "<code>theOldJobOnTwoServersGivesOneRoomBackTwiceAndTheHotelIsOverbooked</code>"],
    ["The API's job on two servers", "One room back; the sixth guest <code>409</code>", "<code>theApiJobOnTwoServersGivesItBackOnce</code>"],
    ["A hold, then 15 minutes", "<code>201</code>, <code>409</code> for the next guest, then expired and free", "<code>aHoldTakesARoomForFifteenMinutesThenExpires</code>"],
    ["One second before its time", "Not expired", "<code>aHoldBeforeItsTimeIsNotExpired</code>"],
    ["No key, bad key, date, e-mail, room type; unknown night or hold", "<code>400</code>; <code>404</code>; nothing taken", "<code>badRequestsAre400AndUnknownThings404</code>"],
    ["Twenty guests at once, five rooms", "Exactly five", "<code>twentyGuestsAtOnceForFiveRoomsGetExactlyFive</code>"],
    ["Four job runs at once", "Each room back once; then nothing to do", "<code>fourExpiryRunsAtOnceGiveEachRoomBackOnce</code>"],
    ["The same request twice, on the last room; the key for another night", "One hold; <code>422</code>", "<code>theSameRequestTwiceIsOneHold</code>"],
    ["Ten copies at the same moment", "One hold, the same id for all", "<code>tenCopiesAtTheSameMomentAreOneHold</code>"],
    ["Rules written by plain SQL", "Refused by named constraints", "<code>roomAndHoldRulesHoldWithoutJava</code>"],
    ["A hold that cannot be recorded", "Its room is given back too", "<code>aHoldThatCannotBeRecordedGivesItsRoomBack</code>"],
    ["An expiry that cannot give the room back", "Nothing expired; the next run does both", "<code>anExpiryThatCannotGiveTheRoomBackExpiresNothing</code>"],
    ["The real schedule and clock", "Expired without anyone asking", "<code>anUnpaidHoldExpiresOnItsOwn</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">A @Scheduled job that runs on every server at once.</p>
<ul>
<li><strong>The old job.</strong> It reads the expired holds, then for each one gives a room back and marks the hold. On two servers that both read before either writes (the test lines them up with a barrier), one expired hold gives back two rooms: the count says 3 held while 4 are. Two walk-ins are accepted: six guests holding five rooms.</li>
<li><strong>The API's job.</strong> The same two runs: one of them expires the hold and gets its room back from <code>RETURNING</code>; the other finds nothing still held. One room back, and the second walk-in is <code>409</code>.</li>
</ul>
<p>While building, each part was undone once: no free-room condition turned 3 tests red; no transaction around a hold 2; no transaction around expiry 1 (only after a test made giving the room back fail); no replay check before taking a room 1; e-mails not lower-cased 1; no request check on a reused key 1; no room given back 3; no fallback when two copies race 1. The job's two guards, <code>SKIP LOCKED</code> and <code>AND status = 'HELD'</code>, were each enough alone in the tests; without both, 2 tests turned red. Both stay: one so servers do not wait for each other, the other so correctness does not depend on the lock.</p>
</div>
""" + code(read(T + "DoubleExpiryTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "HoldController.java", dwn("The two endpoints.", "Validates the key and body; <code>201</code> or <code>200</code> for a replay; when two copies race, answers with the one that won.", "A retried request taking a second room.")),
    (J + "Holds.java", dwn("Taking rooms and expiring holds.",
        "One conditional UPDATE takes a room; the hold is recorded in the same transaction; the expiry is one UPDATE ... RETURNING over holds still held.",
        "Overbooking from two guests at once, a retry, or two servers running the job.",
        "<ul><li>The replay check comes before taking a room: on a full night, a retry must find the guest's own hold, not \"sold out\". Found by a test on the one suite.</li><li>The expiry and the rooms it gives back are one transaction: a hold expired without its room back would lose that room for good.</li><li>At most 500 holds per run; the rest wait for the next run.</li></ul>")),
    (J + "ExpirySchedule.java", dwn("The timetable.", "A fixed delay of 30 s: runs on one server never overlap.", "A slow run and the next one stepping on each other.")),
    (M + "V1__room_nights_and_holds.sql", dwn("Rooms per night and holds.", "<code>held BETWEEN 0 AND total</code>, one hold per key, states and times that agree.", "Overbooking by any writer.")),
    (M + "V2__demo_rooms.sql", "<p>The demo hotel's rooms.</p>"),
    ("src/main/resources/application.yaml", "<p>Hold time and the job's interval.</p>"),
    (J + "HoldsApplication.java", "<p>Entry point, and the <code>Clock</code>.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
]
tree = """stations/100-expiring-unpaid-hotel-holds/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/ghoomo/holds/
│   ├── HoldController.java   ├── Holds.java   ├── ExpirySchedule.java   └── HoldsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__room_nights_and_holds.sql, V2__demo_rooms.sql
├── src/test/java/com/ghoomo/holds/   (see Tests)
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
<p>Start the app twice, on two ports, against the same database, and watch both run the job without giving a room back twice:</p>
""" + code("""./mvnw spring-boot:run -Dspring-boot.run.arguments=--server.port=8081
curl -H 'Content-Type: application/json' -H 'Idempotency-Key: try-it-0001' -d '{"roomTypeId":1,"date":"2026-12-24","guestEmail":"you@example.com"}' http://localhost:8080/holds""", "bash") + """
<p>Wait 15 minutes (or set <code>ghoomo.holds.ttl=1m</code>), then read <code>room_nights</code>: the room is back once.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Rooms free that are still held", "Releases counted twice: the job read, then wrote.", "Expire with a conditional UPDATE and give back what it returned."],
    ["The job never runs", "<code>@EnableScheduling</code> missing, or the property switched it off.", "Check <code>ghoomo.holds.expiry.enabled</code>."],
    ["<code>Could not find a valid Docker environment</code>", "Docker is not running.", "Start Docker Desktop or the Docker service."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the job and the database.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>HoldContractTest</code> ({cnt('HoldContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>DoubleExpiryTrapTest</code> ({cnt('DoubleExpiryTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>HoldDatabaseTest</code> ({cnt('HoldDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Concurrency", "A real concurrency test that proves the invariant holds", f"<code>HoldConcurrencyTest</code> ({cnt('HoldConcurrencyTest')})", '<span class="pill ok">pass</span>'],
    ["Idempotency", "Replay: the same request twice gives one effect", f"<code>HoldReplayTest</code> ({cnt('HoldReplayTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">The job is switched off in the tests, which run it themselves at the moment they choose, on a clock they move: 15 minutes pass in an instant. <code>ScheduledExpiryTest</code> keeps the real schedule (every 200 ms, holds of 1 s) and waits with Awaitility.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "DoubleExpiryTrapTest.java", "<p>Written first: the old job and the API's, on two servers at once.</p>"),
    (T + "HoldContractTest.java", "<p>A hold's life; its time to the second; bad and unknown requests.</p>"),
    (T + "HoldConcurrencyTest.java", "<p>Twenty guests for five rooms; four job runs at once.</p>"),
    (T + "HoldReplayTest.java", "<p>A retry on the last room; a reused key; ten copies at once.</p>"),
    (T + "HoldDatabaseTest.java", "<p>Named constraints with plain SQL; two rollbacks.</p>"),
    (T + "ScheduledExpiryTest.java", "<p>The real schedule and clock.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: no holds, the job off, the clock at 10:00 on 20 December.</p>"),
    (T + "TestClock.java", "<p>A clock moved by hand.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/ghoomo/holds/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=ConfirmChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "The guest paid", "Beginner-friendly", 25,
    "<code>POST /holds/{id}/confirmation</code>, called when payment succeeds (simulated). A hold still within its time becomes <code>CONFIRMED</code>, keeps its room and never expires; calling it again is fine. Past its time, swept or not: <code>409</code>.",
    "both tests in <code>ConfirmChallengeTest</code> pass.",
    ["A V3 migration widens the status CHECK.",
     "One UPDATE with the conditions in its WHERE; 0 rows means 404 or 409: read the hold to tell which.",
     "\"Past its time\" is <code>expires_at</code>, not the status: the job may not have run yet."],
    "challenge/ConfirmChallengeTest.java", ["challenge/solution/V3__confirmed_and_cancelled.sql", "challenge/solution/Holds.java", "challenge/solution/HoldController.java"]) + challenge(2, "Cancel, once", "Go deeper", 30,
    "<code>DELETE /holds/{id}</code>: the guest gives the room up at once. <code>204</code> every time, but the room comes back only once, even when the app sends five DELETEs at the same moment.",
    "the test in <code>CancelChallengeTest</code> passes.",
    ["The same shape as the job: <code>UPDATE ... WHERE status = 'HELD' RETURNING</code> the room, then give back only what came back.",
     "Five at once: the row lock makes four of them find the hold already cancelled."],
    "challenge/CancelChallengeTest.java", ["challenge/solution/Holds.java", "challenge/solution/HoldController.java", "challenge/solution/V3__confirmed_and_cancelled.sql"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Exactly one server</h2>
<p>Ghoomo grows to twelve servers. The job is safe on all of them, but twelve runs every 30 s are wasted work, and a nightly job that emails guests must really run once. Compare: a lock table with a lease (ShedLock), <code>pg_try_advisory_lock</code>, a leader chosen by the platform (a Kubernetes CronJob), and a queue of due work. What happens to each when the server holding the lock pauses for a minute? Which job still needs to be idempotent, and why all of them?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old job on two servers, lined up with a barrier.</li>
<li>Write the tables: rooms per night with <code>held BETWEEN 0 AND total</code>, and holds.</li>
<li>Take a room with one conditional UPDATE; add the Idempotency-Key replay.</li>
<li>Expire with one UPDATE ... RETURNING; prove it with parallel runs and a rollback.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["An idempotent job on every server", "Some repeated work, all harmless.", '<span class="pill ok">Chosen</span>'],
    ["Read due holds, then release each", "Two servers release twice: overbooking.", '<span class="pill bad">The trap</span>'],
    ["<code>synchronized</code> on the job", "Only within one server.", '<span class="pill bad">Review finding</span>'],
    ["A distributed lock (ShedLock)", "Saves work; a lease can expire under a slow run, so still be idempotent.", '<span class="pill warn">On top, not instead</span>'],
    ["Expire on read (\"held and not past its time\")", "No job needed for correctness, but the room count must be computed from holds.", '<span class="pill warn">A valid alternative</span>']]) + """
<h2>Fixed delay or cron?</h2>
<p>Fixed delay: the next run starts 30 s after the last one ended, so one server's runs never overlap and slow runs space themselves out. Cron (<code>0/30 * * * * *</code>): runs at fixed clock times, so every server starts at the same second, which is exactly when the trap bites. Cron fits jobs tied to the clock (a report at 06:00); fixed delay fits \"keep things tidy\" jobs like this one.</p>
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>room_nights_held_range</code>", "CHECK held BETWEEN 0 AND total", "No overbooking and no negative counts, for any writer."],
    ["<code>holds_key_once</code>", "UNIQUE (idempotency_key)", "A retried request cannot make a second hold."],
    ["<code>holds_room_night</code>", "Foreign key to the room night", "Only nights the hotel sells."],
    ["<code>holds_status</code>, <code>holds_expired_has_time</code>, <code>holds_expires_after_creation</code>", "CHECKs", "States and times that agree."],
    ["<code>holds_due</code>", "Partial index on expires_at, held only", "The job reads only what is waiting."]]) + """
<p><strong>Transaction boundaries:</strong> taking a room and recording the hold commit together; so do expiring holds and giving their rooms back.</p>
""" + code(read(M + "V1__room_nights_and_holds.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Backlog</dt><dd>500 holds a run, every 30 s, per server. After an outage the backlog clears over a few runs; watch the age of the oldest due hold.</dd>
<dt>Clocks</dt><dd>\"Now\" comes from the app server; servers' clocks drift. Using the database's clock (<code>now()</code>) in both the hold and the job removes that, at the cost of testability with a moved clock.</dd>
<dt>Keys</dt><dd>Idempotency keys are kept for ever here. Expire old ones (a day) and scope them per client.</dd>
<dt>Guests</dt><dd>Tell the guest when the hold ends, and email them when it does: an expired hold is a lost booking.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What happens to a @Scheduled job when you run two instances?", "It runs on both, at about the same time. Unless the job is idempotent, its effect happens twice."),
    ("How do you make a batch job safe to run twice at once?", "Change only rows still in the old state, in one statement, and act on what it returned: UPDATE ... WHERE status = 'HELD' RETURNING. SKIP LOCKED lets runs split the work without waiting."),
    ("Fixed delay, fixed rate or cron?", "Fixed delay for clean-up (no overlap, self-spacing); fixed rate for steady sampling; cron for clock times."),
    ("How do you stop two guests taking the last room?", "One conditional UPDATE: held = held + 1 WHERE held < total. Check the row count. Back it with a CHECK."),
    ("Is a distributed lock enough?", "It saves work, but leases expire under pauses; keep the job idempotent anyway."),
    ("How do you test it?", "Run the job from several threads at once on a real database, with a clock you move."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["The job", "Expires due holds.", "Idempotent across servers, one transaction with the release, bounded batches."],
    ["Inventory", "Sold-out is a 409.", "One conditional UPDATE and a CHECK; a retry on the last room still finds its hold."],
    ["Testing", "A test that runs the job.", "Parallel runs, a barrier for the trap, a moved clock, and one real schedule."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("Check, then take",
     "\"Clearer in two steps\": twenty guests read \"4 held of 5\" at the same moment and all add one. The database's CHECK stops the count passing 5, so the extra guests get an error instead of a clean 409; without that CHECK the hotel would be overbooked. Taking must be the condition: <code>held = held + 1 WHERE held &lt; total</code>.",
     "<code>twentyGuestsAtOnceForFiveRoomsGetExactlyFive</code> fails: some of the twenty requests end in an error instead of a <code>409</code>. Printing the cause while building showed the database's <code>room_nights_held_range</code> refusing them: the constraint kept the hotel from being overbooked."),
    ("synchronized is one server's lock",
     "\"So it never runs twice at once\": on this server. The second server has its own lock, and the job reads, then gives back: the trap's shape, with a lock that does not reach the other server.",
     "None on one JVM, and that is the lesson: the four-runs-at-once test passes on the flawed version, because <code>synchronized</code> does line up threads in one process. <code>theOldJobOnTwoServersGivesOneRoomBackTwiceAndTheHotelIsOverbooked</code> runs this read-then-give-back shape as two servers would, and overbooks. A test that runs everything in one JVM cannot show a one-server lock failing; review has to."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate makes <code>Holds</code> \"easier to read\": taking a room becomes a check and an update, and the job reads due holds and releases each one, made \"safe\" with <code>synchronized</code>. Read the file and list every problem before opening the findings.</p>
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
<p class="note">Only one test fails, and that is worth a moment: the worse flaw, the job, passes every test in this suite. One guest at a time, on one server, the flawed version is correct. Christmas Eve brings both: many guests at once, and more than one server.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
