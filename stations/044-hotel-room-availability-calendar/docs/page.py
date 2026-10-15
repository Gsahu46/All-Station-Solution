"""Station 044 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 44,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Data JPA date query methods · half-open ranges · PostgreSQL 17 EXCLUDE with daterange · virtual threads · Testcontainers",
    "simulation": "Hotels, rooms and guests are demo data, not Ghoomo's. A block is a hold record; no payment is taken and no confirmation is sent.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/ghoomo/rooms/"
T = "src/test/java/com/ghoomo/rooms/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Night", "A stay is counted in nights: the night that starts on a date.", "\"10 to 12 June\" is two nights: the 10th and the 11th.", "<code>RoomBlock.holds</code>"),
    ("Half-open range", "Start included, end excluded: [check-in, check-out).", "You leave on the morning of check-out; that night is free.", "<code>'[)'</code>"),
    ("Overlap", "Two stays share at least one night.", "Two guests given the same room on the 11th.", "<code>checkIn &lt; otherOut AND checkOut &gt; otherIn</code>"),
    ("Back-to-back", "One guest leaves the day the next arrives.", "Out at 11 a.m., in at 2 p.m.", "allowed"),
    ("EXCLUDE constraint", "No two rows may conflict, here: same room and overlapping dates.", "One key per room per night.", "<code>room_blocks_no_overlap</code>"),
    ("Deadlock", "Two transactions each waiting for the other; the database stops one.", "Two people in a doorway, each waiting for the other to go first.", "found by the concurrency test"),
]
STORY = [
    ("Asha books 10 to 12 June", "Room 101, two nights: the 10th and the 11th."),
    ("Kabir books 11 to 13 June", "The system checks whether another stay starts on the 11th. None does, so Kabir gets the room too. On the 11th, two families arrive with keys to the same room."),
    ("The fix", "Two stays clash when each starts before the other ends. That rule is checked in Java for a clear message and enforced by the database for every race."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Ranges clash when each starts before the other ends. Nothing simpler is right.</p>

<h2>What are we building?</h2>
<p><code>GET /rooms/{id}/availability</code> shows which nights a room is free; <code>POST /rooms/{id}/blocks</code> holds it for a stay, or says it is not available.</p>

<h2>An everyday analogy</h2>
<p>A hotel's paper register with one column per night. Booking 10 to 12 June ticks the boxes for the 10th and 11th, not the 12th. A new booking is allowed only if none of its boxes is ticked.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Check the dates</strong>: check-out after check-in, at most 30 nights.</li>
<li><strong>Look for a clash</strong> with the overlap rule; if found, <code>409</code>.</li>
<li><strong>Insert the hold.</strong> If another desk got there in the same instant, the database refuses: also <code>409</code>.</li>
<li><strong>The calendar</strong> marks each night free unless a hold covers it.</li>
</ol>

<details class="qa check"><summary>Check yourself: Asha holds 10 to 12 June. Can Meena hold 12 to 15 June?</summary><p>Yes. Asha's last night is the 11th; she leaves on the morning of the 12th. Meena's first night is the 12th. With a half-open range, 12 &lt; 12 is false, so they do not overlap.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No payment or confirmation.</strong> A hold is a record.</li>
<li><strong>No room types or prices.</strong> One room at a time.</li>
<li><strong>No time zones.</strong> Nights are local dates at the hotel.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Ghoomo</strong> (a fictional hotel chain) sold a room booked for 10 to 12 June again for 11 to 13 June, because the overlap check compared only start dates.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Room 101 holds 10–12 June (Asha) and 15–16 June (Ravi).</p>
<ol class="gwt">
<li><b>Given</b> 11 to 13 June, <b>then</b> <code>409</code>: the night of the 11th is taken.</li>
<li><b>Given</b> 12 to 15 June, <b>then</b> <code>201</code> for 3 nights: back to back with both stays.</li>
<li><b>Given</b> the calendar for 9 to 17 June, <b>then</b> the 10th, 11th and 15th are taken, the others free.</li>
<li><b>Given</b> 20 desks holding the same nights at once, <b>then</b> one <code>201</code> and 19 <code>409</code>, never a <code>500</code>, and no night held twice.</li>
<li><b>Given</b> zero nights, check-out before check-in, or over 30 nights, <code>400</code>; an unknown room, <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Ranges are half-open everywhere: Java check, calendar, and database.</li>
<li>The database guarantees no overlap (<code>EXCLUDE</code>), whoever writes and however fast.</li>
<li>Every way the database refuses a clash becomes <code>409</code>.</li>
<li>Dates are ISO local dates.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Model stays as half-open ranges.</li>
<li>Write the overlap condition, and test it on every shape.</li>
<li>Express it as a Spring Data JPA query method with dates.</li>
<li>Back a Java check with a database constraint for concurrency.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/rooms/{id}/availability?from=…&amp;to=…</code>", "Each night from <code>from</code> up to the night before <code>to</code>: free or not."],
    ["<code>POST</code>", "<code>/rooms/{id}/blocks</code>", "<code>{\"checkIn\", \"checkOut\", \"guestName\"}</code>: hold the nights checkIn to checkOut − 1."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "A calendar"],
    ['<span class="pill ok">201</span>', "The room is held"],
    ['<span class="pill warn">400</span>', "Zero nights, end before start, too long a range, a missing field, an unknown field"],
    ['<span class="pill warn">404</span>', "No such room"],
    ['<span class="pill warn">409</span>', "At least one night is already held"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against the demo data. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-the-calendar", "Case 1: room 101, 9 to 17 June", "<b>Why:</b> the 10th, 11th and 15th are held."),
    ("02-the-old-bug-11-to-13-june", "Case 2: 11 to 13 June", "<b>Why:</b> the original double booking, now <code>409</code>."),
    ("03-exactly-the-gap", "Case 3: 12 to 15 June", "<b>Why:</b> arrives as Asha leaves, leaves as Ravi arrives: <code>201</code>."),
    ("04-the-calendar-after", "Case 4: the calendar again", "<b>Why:</b> only the 9th and 16th left."),
    ("05-zero-nights", "Case 5: in and out the same day", "<b>Why:</b> no night to hold: <code>400</code>."),
    ("06-no-such-room", "Case 6: room 999", "<b>Why:</b> <code>404</code>."),
]) + """
<h2>Twenty desks at once</h2>
<p class="muted">From <code>docs/capture.sh</code>: 20 parallel curl requests for room 102, 1 to 4 August (<code>docs/captures/rush.txt</code>).</p>
""" + code(read("docs/captures/rush.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Eight shapes against 10–12 June", "Overlap exactly when they share a night", "<code>theOverlapRuleOnEveryShape</code>"],
    ["A free gap; an overlap; another room", "<code>201</code>; <code>409</code>; <code>201</code>", "<code>aFreeStayIsHeldAndAnOverlappingOneIsNot</code>"],
    ["The calendar", "Each night marked", "<code>theCalendarShowsEachNight</code>"],
    ["20 holds for the same nights at once", "1 held, 19 refused, no 500", "<code>twentyRequestsForTheSameNightsHoldItOnce</code>"],
    ["30 staggered overlapping holds at once", "No night held twice, no 500", "<code>staggeredOverlappingRequestsNeverShareANight</code>"],
    ["Overlap, zero nights, unknown room, written directly", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"],
    ["A group booking with one clash", "All or nothing", "<code>aGroupBookingIsAllOrNothing</code>"],
    ["Bad dates, missing or unknown fields; unknown room", "<code>400</code>; <code>404</code>", "<code>AvailabilityContractTest</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Comparing only start dates, so overlapping bookings are accepted.</p>
<p>The old checks are kept as Spring Data methods in the tests. The start-date check says 11 to 13 June is free. The first fix, with both ends included, refuses a back-to-back stay from the 12th. The real rule is then tested on eight shapes.</p>
<p>While building, each fix was undone once:</p>
<ul>
<li>Not mapping the constraint violation gave 2 errors: requests really do race past the Java check.</li>
<li>Counting the check-out night in the calendar turned 1 test red.</li>
<li>Dropping the <code>EXCLUDE</code> constraint turned 4 red.</li>
<li>Swapping the arguments of the Java overlap check was <em>not</em> caught: the database turned every clash into the same <code>409</code>. The Java check gives a clear message without a failed insert; the constraint is the guarantee.</li>
</ul>
</div>
""" + code(read(T + "StartDatesOnlyTrapTest.java"), "java") + code(read(T + "OldRoomBlockRepository.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "RoomController.java", dwn("Checks date ranges, returns the calendar or the hold.",
        "Zero-night and over-long ranges are refused before the database.",
        "A zero-night stay reaching the database's CHECK and coming back as a 500.")),
    (J + "Availability.java", dwn("Builds the calendar and holds rooms.",
        "A clear 409 from the Java check, and the same 409 when the database refuses a race.",
        "Races turning into 500s.",
        "<ul><li>The constraint violation and a deadlock abort are both answered <code>409</code>; see Design.</li><li><code>saveAndFlush</code> runs the insert now, inside the try, so a refusal is caught here.</li></ul>")),
    (J + "RoomBlockRepository.java", dwn("The overlap rule as a derived query method.",
        "<code>CheckInBefore(newCheckOut)</code> and <code>CheckOutAfter(newCheckIn)</code> are the two halves of the rule.",
        "Hand-written JPQL, or the start-date check.")),
    (J + "RoomBlock.java", dwn("A hold as an entity, with <code>holds(night)</code> for the calendar.",
        "The same half-open rule in one line.",
        "A calendar that marks the check-out night taken.")),
    (J + "Room.java", "<p>A room.</p>"),
    (J + "RoomRepository.java", "<p>Rooms, for \"does this room exist\".</p>"),
    (M + "V1__rooms_and_blocks.sql", dwn("Rooms and holds, with the <code>EXCLUDE</code> constraint.",
        "<code>daterange(check_in, check_out, '[)')</code> uses the same half-open rule as Java.",
        "Two holds for one night when two desks press \"book\" together.")),
    (M + "V2__demo_rooms.sql", "<p>Two rooms and two holds.</p>"),
    ("src/main/resources/application.yaml", "<p>open-in-view off, schema validation, strict JSON.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "RoomsApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/044-hotel-room-availability-calendar/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/ghoomo/rooms/
│   ├── RoomController.java   ├── Availability.java   ├── RoomBlockRepository.java
│   ├── RoomBlock.java   ├── Room.java   ├── RoomRepository.java   └── RoomsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__rooms_and_blocks.sql, V2__demo_rooms.sql
├── src/test/java/com/ghoomo/rooms/   (see Tests)
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
<p>Ask PostgreSQL about ranges directly:</p>
""" + code("""docker compose exec postgres psql -U ghoomo -d ghoomo -c "SELECT daterange('2026-06-10','2026-06-12','[)') && daterange('2026-06-12','2026-06-14','[)') AS back_to_back, daterange('2026-06-10','2026-06-12','[)') && daterange('2026-06-11','2026-06-13','[)') AS eleven_to_thirteen\"""", "bash") + """
<p>Back to back is <code>f</code>; 11 to 13 is <code>t</code>.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>No property 'check' found for type 'RoomBlock'; Did you mean 'checkIn'</code>", "A derived method name ending in <code>CheckIn</code>: Spring Data reads <code>In</code> as the IN keyword.", "Spell the comparison: <code>…CheckInEquals</code>. Found while building this station."],
    ["<code>conflicting key value violates exclusion constraint \"room_blocks_no_overlap\"</code>", "An overlapping hold reached the database.", "Expected under races; the app answers <code>409</code>."],
    ["<code>deadlock detected</code>", "Two overlapping holds inserted at once, each waiting for the other.", "PostgreSQL aborts one; the app answers <code>409</code>, because the other one holds those nights."],
    ["<code>data type bigint has no default operator class for access method \"gist\"</code>", "<code>btree_gist</code> is missing.", "The migration creates it; a managed database may need it allowed."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>AvailabilityContractTest</code> ({cnt('AvailabilityContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>StartDatesOnlyTrapTest</code> ({cnt('StartDatesOnlyTrapTest')} runs)", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>BlockDatabaseTest</code> ({cnt('BlockDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Concurrency", "A real concurrency test that proves the invariant holds", f"<code>BlockConcurrencyTest</code> ({cnt('BlockConcurrencyTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Hibernate 7, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "StartDatesOnlyTrapTest.java", "<p>Written first: the old checks, and the rule on eight shapes.</p>"),
    (T + "BlockConcurrencyTest.java", "<p>20 identical and 30 staggered holds, released by one latch; a self-join proves no night is shared.</p>"),
    (T + "BlockDatabaseTest.java", "<p>Named constraints, back-to-back via SQL, and an all-or-nothing group.</p>"),
    (T + "AvailabilityContractTest.java", "<p>The calendar, holds, and refusals through HTTP.</p>"),
    (T + "OldRoomBlockRepository.java", "<p>The old checks as derived methods, kept only in tests.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the demo holds before each test, and the latch helper.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/ghoomo/rooms/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=CancelBlockChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Cancel a hold", "Beginner-friendly", 20,
    "Add <code>DELETE /rooms/{id}/blocks/{blockId}</code>: <code>204</code>, and the nights are free again. A block of another room, or none, is <code>404</code>.",
    "both tests in <code>CancelBlockChallengeTest</code> pass.",
    ["<code>findById</code>, then check the room before deleting.",
     "A block id from another room must never delete that room's hold."],
    "challenge/CancelBlockChallengeTest.java", ["challenge/solution/Availability.java", "challenge/solution/RoomController.java"]) + challenge(2, "Find a free room", "Go deeper", 30,
    "Add <code>GET /rooms/free?checkIn&amp;checkOut&amp;guests</code>: rooms with enough beds and no night held in the range, by id, in one query.",
    "the test in <code>FreeRoomsChallengeTest</code> passes.",
    ["JPQL: <code>where r.capacity &gt;= :guests and not exists (select b from RoomBlock b where …)</code>.",
     "Inside, the same overlap rule: <code>b.checkIn &lt; :checkOut and b.checkOut &gt; :checkIn</code>."],
    "challenge/FreeRoomsChallengeTest.java", ["challenge/solution/RoomRepository.java", "challenge/solution/Room.java", "challenge/solution/Availability.java", "challenge/solution/RoomController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Room types instead of rooms</h2>
<p>Guests book \"a deluxe room\", not room 101; the hotel assigns rooms at check-in. The rule becomes \"never more deluxe stays on a night than deluxe rooms\". Compare a per-night counter row per room type (with a conditional update, as in the flash sale), assigning a concrete room at booking time, and a nightly inventory table. Which one can a database constraint guard?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Decide the range rule (half-open) and write the overlap condition.</li>
<li>Write the trap test with the old checks and every overlap shape.</li>
<li>Put the same rule in the database as an <code>EXCLUDE</code> constraint.</li>
<li>Write the Java check for clear messages, and map every database refusal to <code>409</code>; prove it with parallel holds.</li>
</ol>
<h2>Why two kinds of refusal</h2>
<p>When two overlapping holds arrive together, both pass the Java check. Both inserts then meet the exclusion constraint. Usually one waits for the other and gets the constraint violation. Sometimes each insert waits for the other, and PostgreSQL ends the cycle by aborting one as a deadlock. That happened once while building this station, and came back as a <code>500</code>. In both cases the surviving hold commits those nights, so the refused request truly clashed, and the app answers <code>409</code>. The deadlock cannot be produced on demand, so no test claims to cover it.</p>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Java check + <code>EXCLUDE</code> constraint", "Two places with the same rule; refusals to map.", '<span class="pill ok">Chosen</span>'],
    ["Java check only", "Races double-book.", '<span class="pill bad">Not enough</span>'],
    ["Compare start dates", "Misses most overlaps.", '<span class="pill bad">The trap</span>'],
    ["One row per room per night with a unique key", "Simple constraint; many rows; long stays are many inserts.", '<span class="pill warn">Also correct</span>'],
    ["Lock the room row (<code>SELECT … FOR UPDATE</code>) before checking", "Serialises holds per room; no deadlock between overlapping inserts.", '<span class="pill warn">Valid alternative</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Constraints", "Why"], [
    ["<code>rooms</code>", "PK, capacity 1 to 10", "What can be held."],
    ["<code>room_blocks</code>", "<code>room_blocks_room_fk</code>, <code>room_blocks_dates_order</code> (at least one night), <code>room_blocks_no_overlap</code> (EXCLUDE, <code>'[)'</code>)", "The no-double-booking rule, for every writer and every race."]]) + """
""" + code(read(M + "V1__rooms_and_blocks.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Channel managers</dt><dd>Hotels sell through several sites at once; all of them must go through one inventory that a constraint guards.</dd>
<dt>Deadlocks</dt><dd>Occasional deadlocks under contention are normal for exclusion constraints. Count them; a rising rate means many desks fight over the same rooms.</dd>
<dt>Time</dt><dd>Check-in dates are the hotel's local dates, not UTC. A guest's phone in another time zone must not shift them.</dd>
<dt>Holds that expire</dt><dd>Real holds while a guest pays expire after minutes; that needs a status or an expiry column in the constraint.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("When do two date ranges overlap?", "For half-open ranges [a, b) and [c, d): when a < d and c < b. Checking only starts, or using <= with exclusive ends, gets edge cases wrong."),
    ("Why half-open ranges for stays?", "The check-out day is not a night of the stay. Half-open ranges make back-to-back stays not overlap, and lengths are simply end − start."),
    ("Why is a Java overlap check not enough?", "Two requests can check at the same moment, both see no clash, and both insert. Only a constraint in the database decides between them."),
    ("What is an EXCLUDE constraint?", "A PostgreSQL constraint that forbids two rows for which given operators all return true, for example same room (=) and overlapping daterange (&&)."),
    ("How do you write date conditions as JPA query methods?", "With keywords on date fields: CheckInBefore(x) is check_in < x, CheckOutAfter(y) is check_out > y; Spring Data generates the query from the method name."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Ranges", "Half-open, everywhere.", "Every overlap shape from memory."],
    ["Concurrency", "A constraint behind the Java check.", "Why a deadlock abort is also a 409 here."],
    ["JPA", "Date query methods.", "Why a name ending in CheckIn breaks."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("The clash check compares start dates only",
     "The original bug again, as a stream over every block. On its own it would be masked: the database refuses the overlap anyway.",
     "With finding 2, an ordinary overlapping hold becomes a <code>500</code>: <code>aFreeStayIsHeldAndAnOverlappingOneIsNot</code> errors."),
    ("The database's refusal is not mapped",
     "Without the catch, every clash the database stops, including every race, is a <code>500</code>.",
     "<code>twentyRequestsForTheSameNightsHoldItOnce</code> and <code>staggeredOverlappingRequestsNeverShareANight</code> error."),
    ("The calendar includes the check-out night",
     "\"Inclusive on both ends, like the dates on the booking\" marks the morning-of-departure night as taken: the 12th looks booked when it is free.",
     "<code>theCalendarShowsEachNight</code> fails."),
    ("Same-day stays allowed",
     "\"Day rooms\" are a different product. A stay with no night reaches the database's <code>room_blocks_dates_order</code> and comes back as a <code>500</code>.",
     "<code>impossibleDatesAre400</code> errors."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate simplifies the room code. The clash check becomes \"a stay already starts that day\". The try/catch around the insert goes. The calendar is \"inclusive on both ends\", and same-day stays are allowed for day rooms. Read the three files and list every problem before opening the findings.</p>
<p class="path">review/Availability.java</p>
""" + code(read("review/Availability.java"), "java") + """
<p class="path">review/RoomBlock.java</p>
""" + code(read("review/RoomBlock.java"), "java") + """
<p class="path">review/RoomController.java</p>
""" + code(read("review/RoomController.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the three flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">No double booking got through: the constraint refused every one. What the flaws broke is how the app answers, which is why the database rule and the Java rule both matter.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
