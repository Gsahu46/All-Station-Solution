"""Station 011 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 11,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · enums · TreeSet · java.time.Clock · MockMvc",
    "simulation": "One 6-floor building with 360 slots exists only in the app's memory. No gate hardware, cameras or payments: a fee is a number on the receipt.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/parkora/parking/"
T = "src/test/java/com/parkora/parking/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Model", "Classes that mirror the real things: slot, vehicle type, ticket, receipt.", "A toy model of a building.", "<code>Slot</code>, <code>Ticket</code>, <code>Garage</code>"),
    ("Enum", "A fixed list of named values, which can also carry data.", "The sizes on a T-shirt label.", "<code>VehicleType.CAR</code> knows its slot type and rates."),
    ("TreeSet", "A set that keeps its items sorted all the time.", "A queue at a counter that reorders itself by token number.", "Free slots, nearest first."),
    ("pollFirst", "Take and remove the smallest item of a sorted set.", "Calling the next token.", "The nearest free slot."),
    ("Comparator", "The rule for which item comes first.", "\"Shorter walk first; if equal, lower slot number.\"", "<code>Slot.NEAREST_FIRST</code>"),
    ("Rounding up", "Any part of an hour counts as a whole hour.", "A taxi meter that adds a full unit when you start one.", "61 minutes is 2 hours."),
    ("Clock", "Java's source of \"now\" that tests can replace.", "A stopwatch the referee controls.", "<code>TestClock</code> in tests."),
]
STORY = [
    ("Neha drives into an empty mall parking at 9 a.m.", "The entry gate sends her to floor 5, at the far end. Ground-floor slots next to the exit stay empty all morning."),
    ("A biker gets a car slot", "The gate gave the first free slot on its list, whatever its size, so bikes took car slots and cars were turned away while bike slots stood free."),
    ("The fix", "Keep the free slots of each type in order, nearest first. Each entry takes the top one; each exit puts its slot back in its place."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">If you will ask "which is the best one?" thousands of times, keep things sorted once, instead of searching every time.</p>

<h2>What are we building?</h2>
<p>Two endpoints: an entry gate (<code>POST /parking/entries</code>) that hands out a ticket for the nearest free slot of the right size, and an exit gate (<code>POST /parking/exits/{ticketId}</code>) that frees the slot and prints a receipt, charging every started hour.</p>

<h2>An everyday analogy</h2>
<p>A hospital keeps a waiting list sorted by urgency. When a doctor is free, the nurse calls the top name; nobody re-reads the whole register each time. When a patient leaves and comes back, they go back into the list at their place. Free parking slots, sorted by distance, work the same way.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>At start-up</strong>, every slot goes into one of two sorted sets, cars or bikes, nearest first.</li>
<li><strong>A vehicle enters</strong>: the gate takes the first slot from the set for its type. Nothing left: <code>409</code>.</li>
<li><strong>The ticket</strong> records the slot and the entry time.</li>
<li><strong>At exit</strong>, the fee counts every started hour; the slot goes back into its set, in its place.</li>
</ol>

<details class="qa check"><summary>Check yourself: a car on the ground floor leaves. The next car arrives. Where does it go?</summary><p>To that ground-floor slot, if it is now the nearest free car slot. Putting the slot back into the sorted set places it at the front again, so the next <code>pollFirst</code> returns it.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No hardware.</strong> No boom barriers, cameras or number-plate readers.</li>
<li><strong>No payment.</strong> The fee is a number on the receipt. Rates are demo rules, not any city's tariff.</li>
<li><strong>One building, in memory.</strong> A restart forgets every ticket.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Parkora</strong> (a fictional smart-parking operator) runs a 6-floor mall car park. Its gate software walks the slot sheet from the top floor and takes the first free slot of any size. Customers complain about walking from floor 5 when the ground floor is empty; bikes fill car slots; and at peak hours each entry gets slower, because every car re-reads the whole sheet.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> an empty building, <b>when</b> a car enters, <b>then</b> it gets <code>F0-C01</code>, the nearest car slot; a bike gets <code>F0-B01</code>.</li>
<li><b>Given</b> a freed slot that is now the nearest, <b>then</b> the next vehicle of that type gets it.</li>
<li><b>Given</b> no free car slots, <b>then</b> a car gets <code>409</code>, while bikes can still enter.</li>
<li><b>Given</b> a vehicle already inside, <b>when</b> the same plate enters again (in any spelling), <b>then</b> <code>409</code> naming its open ticket.</li>
<li><b>Given</b> 150 minutes parked, <b>then</b> 3 hours are charged: ₹40 + 2 × ₹30 = ₹100 for a car.</li>
<li><b>Given</b> the exit gate sends the same ticket twice, <b>then</b> the same receipt comes back and the slot is freed once.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Slot types: bike and car. Each vehicle type uses only its own slot type.</li>
<li>"Nearest" = shortest walk to the exit; ties by slot id.</li>
<li>Fees (demo rules): car ₹40 first hour, ₹30 each started hour after; bike ₹20, then ₹10. Minimum one hour. Amounts in paise.</li>
<li>Plates are normalised (spaces and hyphens removed, upper case with <code>Locale.ROOT</code>) and checked against a demo pattern like <code>MH12AB1234</code>.</li>
<li>Entry and exit never interleave: two gates cannot hand out the same slot.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Model a real system with records, enums and one class that owns the rules.</li>
<li>Put data and behaviour on enums.</li>
<li>Keep a <code>TreeSet</code> ordered with a <code>Comparator</code>, and use <code>pollFirst</code> and <code>add</code>.</li>
<li>Round up correctly with <code>Math.ceilDiv</code>, and test the boundaries.</li>
<li>Inject a <code>Clock</code> so time-based rules can be tested instantly.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/parking/entries</code>", "Body <code>{\"vehicleNumber\", \"vehicleType\": \"CAR\" | \"BIKE\"}</code>. <code>201</code> with a ticket and slot."],
    ["<code>POST</code>", "<code>/parking/exits/{ticketId}</code>", "<code>200</code> with the receipt; the slot is freed."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Ticket issued"],
    ['<span class="pill ok">200</span>', "Receipt (also for a repeated exit: the same receipt)"],
    ['<span class="pill warn">400</span>', "Bad plate, unknown vehicle type, missing fields, malformed ticket id"],
    ['<span class="pill warn">404</span>', "Unknown ticket"],
    ['<span class="pill warn">409</span>', "<em>No free slot</em> of this type, or <em>Already parked</em> (with the open <code>ticketId</code>)"]]) + """
<p class="note">Why is exit a <code>POST</code> that may be repeated? The exit gate retries when its network drops. The first exit stores the receipt; every later call returns it unchanged, so the customer is charged once and the slot is freed once (the idempotency idea from station 008).</p>
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, with the real clock, so exits happen seconds after entry. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-bike", "Case 1: a bike enters an empty building", "<b>Why:</b> the nearest bike slot, <code>F0-B01</code>: never a car slot."),
    ("02-car", "Case 2: a car, plate typed loosely", "<b>Why:</b> <code>mh 12 ab-1234</code> is normalised to <code>MH12AB1234</code>; the nearest car slot is <code>F0-C01</code>."),
    ("03-same-car-again", "Case 3: the same car at another gate", "<b>Why:</b> it is already inside: <code>409</code>, with its open ticket so staff can find it."),
    ("04-bad-plate", "Case 4: not a plate", "<b>Why:</b> <code>400</code> before any slot is touched."),
    ("05-exit", "Case 5: the car leaves", "<b>Why:</b> a few seconds parked still pays the first hour: ₹40 (4000 paise). The slot goes back to the front of the free set."),
    ("06-exit-again", "Case 6: the exit gate retries", "<b>Why:</b> the same receipt, word for word: no second charge, no second free slot."),
    ("07-unknown-ticket", "Case 7: a ticket that does not exist", "<b>Why:</b> <code>404</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Bike, then car, in an empty building", "<code>F0-B01</code>, <code>F0-C01</code>", "<code>theGarageGivesEachVehicleTheNearestSlotOfItsOwnType</code>"],
    ["A freed near slot", "Given to the next car", "<code>carsFillTheNearestSlotsFirstAndAFreedNearSlotIsReused</code>"],
    ["Plate with spaces, hyphen, lower case; then the same plate again", "Normalised; <code>409</code> <em>Already parked</em>", "<code>spacesHyphensAndLowerCaseInThePlateAreTheSameCar</code>"],
    ["Bad plate, <code>TRUCK</code>, empty body", "<code>400</code>", "<code>badInputIs400</code>"],
    ["All 240 car slots taken", "Cars <code>409</code>; bikes still enter", "<code>whenCarSlotsRunOutCarsGet409ButBikesStillEnter</code>"],
    ["150 minutes", "3 hours, ₹100", "<code>exitChargesEveryStartedHour</code>"],
    ["12-minute bike stay", "1 hour, ₹20", "<code>aShortBikeStayPaysTheFirstHour</code>"],
    ["0, 1, 60, 60:01, 120, 121 minutes", "1, 1, 1, 2, 2, 3 hours", "<code>everyStartedHourCounts</code>"],
    ["119 minutes", "2 hours (integer division would give 1)", "<code>integerDivisionWouldHaveRoundedDown</code>"],
    ["Exit twice, 5 hours apart", "Same receipt; slot freed once", "<code>exitingTwiceReturnsTheSameReceiptAndFreesTheSlotOnce</code>"],
    ["Same car returns after leaving", "New ticket", "<code>theSameCarCanParkAgainAfterLeaving</code>"],
    ["Unknown or malformed ticket", "<code>404</code>; <code>400</code>", "<code>anUnknownOrMalformedTicketIsRefused</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Re-scanning every slot on each entry instead of keeping free slots ordered.</p>
<p>"Loop over the slots, take the first free one" is the first idea, and it works in a demo with 10 slots. The first test runs it on the real 360-slot sheet, which lists floor 5 first: the bike gets a car slot on the top floor, the car walks 412 m instead of 6 m, and filling the building looks at 64,980 slots. The second test sends the same two vehicles to the real gate: <code>F0-B01</code> and <code>F0-C01</code>. Rounding the fee down instead of up was tried while building: 4 tests went red.</p>
</div>
""" + code(read(T + "RescanEverySlotTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "ParkingController.java", dwn("Two gates. Normalises and checks the plate; maps each garage exception to its status.",
        "HTTP stays out of the garage, which only knows slots and tickets.",
        "No API.")),
    (J + "Garage.java", dwn("Owns the building: one <code>TreeSet</code> of free slots per type, the tickets, the receipts.",
        "The sorted sets make \"nearest free slot\" one <code>pollFirst</code>, and \"free it again\" one <code>add</code>.",
        "The trap: a loop over every slot, on every entry.",
        "<ul><li><code>synchronized</code>: two gates at the same moment cannot take the same slot.</li><li>A stored receipt makes a repeated exit harmless.</li><li><code>layout()</code> lists the building top floor first, as the old sheet did; the sorted set does not care.</li></ul>")),
    (J + "VehicleType.java", dwn("An enum whose values carry their slot type and rates.", "Add a vehicle type in one place, with its own rules.", "Rates and slot rules spread over <code>if</code>s.")),
    (J + "Fee.java", dwn("Started hours and the fee, as plain arithmetic.", "Tested without Spring, boundary by boundary.", "Rounding hidden inside the garage.",
        "<ul><li><code>Math.ceilDiv(seconds, 3600)</code> rounds up; <code>seconds / 3600</code> would round down.</li></ul>")),
    (J + "Slot.java", "<p>A slot, and the comparator that defines \"nearest\".</p>"),
    (J + "SlotType.java", "<p>Bike or car.</p>"),
    (J + "Ticket.java", "<p>What the entry gate prints.</p>"),
    (J + "Receipt.java", "<p>What the exit gate prints.</p>"),
    (J + "ParkingApplication.java", "<p>Entry point, and the <code>Clock</code> bean the garage uses for \"now\".</p>"),
    (J + "ApiErrors.java", "<p>Adds an <code>errors</code> map to validation failures (as in station 004).</p>"),
]
tree = """stations/011-smart-parking-slot-allocation/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/parkora/parking/
│   ├── ParkingController.java   ├── Garage.java      ├── Fee.java
│   ├── VehicleType.java         ├── SlotType.java    ├── Slot.java
│   ├── Ticket.java, Receipt.java, ApiErrors.java, ParkingApplication.java
├── src/test/java/com/parkora/parking/   (see Tests; TestClock moves time)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""],
    ["Docker", "Not needed for this station", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. <code>Math.ceilDiv</code> needs Java 18 or later.</p>
<h2>Try it yourself</h2>
<p>The body is in <code>docs/car.json</code>.</p>
""" + code("""# Enter: expect 201 and "slot": {"id": "F0-C01", ...}
curl -i -X POST http://localhost:8080/parking/entries -H "Content-Type: application/json" -d "@docs/car.json"

# Exit: paste the ticketId; expect "feePaise": 4000
curl -i -X POST http://localhost:8080/parking/exits/PASTE-THE-TICKET-ID""", "bash") + """
<p>Run the exit twice and compare the two receipts.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>400</code> for <code>\"vehicleType\": \"car\"</code>", "Enum names are upper case.", "Send <code>CAR</code> or <code>BIKE</code>."],
    ["<code>409 Already parked</code>", "That plate has an open ticket.", "Exit it first, or use another plate."],
    ["<code>release version 25 not supported</code>", "Maven is using an older JDK.", "Point <code>JAVA_HOME</code> at JDK 25, or add <code>-Djava.version=21</code>."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>ParkingContractTest</code> ({cnt('ParkingContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>RescanEverySlotTrapTest</code> ({cnt('RescanEverySlotTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "The tariff at every boundary", f"<code>FeeTest</code> ({cnt('FeeTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "RescanEverySlotTrapTest.java", "<p>Written first: the old allocator's wrong slots and its 64,980 looks; the real gate's nearest slots.</p>"),
    (T + "ParkingContractTest.java", "<p>Entry, reuse of freed slots, plates, a full building, fees, repeated exits.</p>"),
    (T + "FeeTest.java", "<p>The tariff as plain arithmetic, at each boundary.</p>"),
    (T + "TestClock.java", "<p>A clock the tests move forward: two hours pass in one line.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the test clock replaces the real one; an empty building and a reset clock before each test.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/parkora/parking/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=AvailabilityBoardChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "The display board", "Beginner-friendly", 25,
    "Add <code>GET /parking/availability</code>: one entry per floor, ground floor first, with free car and bike slots.",
    "both tests in <code>AvailabilityBoardChallengeTest</code> pass, and the station's tests still pass.",
    ["The free sets already know every free slot and its floor.",
     "Read inside a <code>synchronized</code> method, so the board never shows a half-finished entry."],
    "challenge/AvailabilityBoardChallengeTest.java", ["challenge/solution/Garage.java", "challenge/solution/ParkingController.java"]) + challenge(2, "A daily cap", "Go deeper", 35,
    "Customers who park all day complain. Cap the fee: each full 24 hours costs at most ₹300 for a car and ₹150 for a bike; the hours after the last full day are charged normally, but never more than one more cap.",
    "all three tests in <code>DailyCapChallengeTest</code> pass.",
    ["Give each <code>VehicleType</code> a <code>dailyCapPaise</code>: the enum already holds the other rates.",
     "<code>Duration.toDays()</code> gives the full days; subtract them to get the rest.",
     "Exactly 24 hours is one cap, not one cap plus a first hour."],
    "challenge/DailyCapChallengeTest.java", ["challenge/solution/VehicleType.java", "challenge/solution/Fee.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Five buildings, one app</h2>
<p>Parkora now runs five buildings and wants an app to show free slots and reserve one for 15 minutes. Where does the free-slot state live when several servers run the gates? What happens to a reservation that is never used? How do you stop two app users reserving the last slot?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the scanning allocator picks wrong slots and does quadratic work.</li>
<li>Model slots, slot types and vehicle types (with rates) as records and enums.</li>
<li>Keep one <code>TreeSet</code> per slot type, ordered by walk then id.</li>
<li>Entry: <code>pollFirst</code>; exit: store the receipt, <code>add</code> the slot back.</li>
<li>Inject a <code>Clock</code>; test fees at every boundary.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["<code>TreeSet</code> per slot type", "O(log n) take and return; can also remove a specific slot (for maintenance).", '<span class="pill ok">Chosen</span>'],
    ["<code>PriorityQueue</code> per slot type", "Same take and return cost; removing a specific slot is O(n), and duplicates are possible.", '<span class="pill warn">Possible</span>'],
    ["Scan every slot per entry", "Wrong slots unless you also sort; O(n) per entry, O(n²) to fill (the trap).", '<span class="pill bad">Wrong</span>'],
    ["Bikes may use car slots when bike slots run out", "More bikes in, fewer cars later. A business choice, not a technical one.", '<span class="pill warn">Ask the business</span>'],
    ["Read <code>Instant.now()</code> directly", "Tests must wait real hours, or never test fees.", '<span class="pill bad">Untestable</span>']]) + """
<h2>Database design</h2>
<p>None in this station. In a database, "nearest free slot" becomes <code>SELECT … WHERE type = ? AND free ORDER BY walk_metres LIMIT 1 FOR UPDATE SKIP LOCKED</code>, with an index on <code>(type, free, walk_metres)</code>; later stations cover row locks.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Concurrency</dt><dd>One lock around the garage is right for one building on one server. Several servers need the database to decide (row locks).</dd>
<dt>Reliability</dt><dd>Gates retry; the stored receipt makes exits safe to repeat. Entries are not: a retried entry for the same plate gets <code>409</code> with the open ticket, which the gate can print again.</dd>
<dt>Money</dt><dd>Fees are whole paise. Rounding rules are written as tests, because customers read receipts closely.</dd>
<dt>Maintainability</dt><dd>A new vehicle type is one enum value with its rates and slot type.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("How would you find the nearest free slot quickly?", "Keep free slots in a sorted structure (TreeSet or PriorityQueue) ordered by distance. Taking the nearest is O(log n), and freeing a slot puts it back in order. Scanning all slots per entry is O(n), and O(n²) to fill the building."),
    ("TreeSet or PriorityQueue?", "Both give the smallest item in O(log n). TreeSet also removes any specific item in O(log n) and refuses duplicates; PriorityQueue's remove(Object) is O(n). TreeSet treats items its comparator calls equal as duplicates, so the comparator needs a tie-breaker."),
    ("How do you round 61 minutes up to 2 hours?", "Math.ceilDiv(seconds, 3600), or (seconds + 3599) / 3600. Plain integer division rounds down. Test 60:00 and 60:01."),
    ("Why inject a Clock?", "Code that calls Instant.now() cannot be tested at 'two hours later' without waiting. With a Clock bean, tests use a clock they move forward."),
    ("Why put rates on the enum?", "Each vehicle type's data and rules live with it. Adding a type is one line, and switch statements cannot forget a rate."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can name the boundary each fee test guards."],
    ["Design", "Sorted free slots per type; rates on the enum.", "You can argue TreeSet against PriorityQueue."],
    ["Tests", "Time moves with a test clock.", "You added a test for midnight or a daylight-saving change."],
    ["Explanation", "You can draw the two sets and one entry.", "You can sketch the database version."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on allocation code:</p>
<ul class="rules">
<li>Does anything loop over every item to find the best one, on every request?</li>
<li>Does every sort have a tie-breaker?</li>
<li>Is "now" injected, or read directly?</li>
<li>Is every rounding rule pinned by a test at its boundary?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
