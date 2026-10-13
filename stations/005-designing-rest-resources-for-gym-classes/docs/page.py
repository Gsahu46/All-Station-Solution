"""Station 005 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 5,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · Bean Validation · MockMvc",
    "simulation": "Four classes and three members are fixed in the code; bookings live in memory and are lost on restart. No login: the member id is sent in the body.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/fitnest/classes/"
T = "src/test/java/com/fitnest/classes/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Resource", "A thing the API lets you work with, named by a noun.", "A book in a library.", "A class, a booking, a member's bookings."),
    ("URL path", "The address of one resource or one collection.", "Shelf 4, row 2.", "<code>/bookings/{id}</code>"),
    ("HTTP method", "The action: read (<code>GET</code>), create (<code>POST</code>), remove (<code>DELETE</code>).", "Borrow, return, renew: the same book, different actions.", "<code>DELETE /bookings/{id}</code> cancels."),
    ("Nested resource", "A collection that only makes sense inside its parent.", "The chapters of one book.", "<code>/classes/{id}/bookings</code>, <code>/members/{id}/bookings</code>"),
    ("Query parameter", "A filter or option on a collection, after <code>?</code>.", "\"Only books by this author.\"", "<code>/classes?date=2026-10-19</code>"),
    ("204 No Content", "\"Done. Nothing to send back.\"", "A nod instead of a letter.", "A cancelled booking."),
    ("409 Conflict", "\"Your request clashes with how things are right now.\"", "Trying to borrow a book someone else has.", "The class is full, or you already booked it."),
]
STORY = [
    ("Rohan books a 6:30 yoga class", "The FitNest app calls <code>/bookClass</code>. The answer is <code>200</code>, with <code>{\"success\": false}</code>."),
    ("The app shows \"Something went wrong\"", "Was the class full? Had he already booked it? Did the class exist? The answer was the same in all three cases, so the app could only guess."),
    ("The fix", "Name things, not actions: <code>POST /classes/1/bookings</code>. Answer each outcome with its own status: <code>201</code> booked, <code>409</code> full or already yours, <code>404</code> no such class."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A status code is the first thing a client reads. When every answer is <code>200</code>, every client has to dig through the body and guess.</p>

<h2>What are we building?</h2>
<p>A small class-booking API designed around resources: list classes by date, book a class, cancel a booking, list a member's bookings. Every outcome has the status code that means it.</p>

<h2>An everyday analogy</h2>
<p>A library does not have a counter called "doBorrowBook". It has books (things), and you borrow, return or renew them (actions). When something fails, the librarian says why: "someone has it" is different from "we don't have that book". URLs are the things; HTTP methods are the actions; status codes are the librarian's reasons.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>See the timetable</strong>: <code>GET /classes?date=2026-10-19</code>. The date filters the collection, so it is a query parameter.</li>
<li><strong>Book</strong>: <code>POST /classes/1/bookings</code> with your member id. A booking belongs to a class, so it is created under the class.</li>
<li><strong>The answer says what happened</strong>: <code>201</code> with the new booking's address, or <code>409</code> (full, already booked), or <code>404</code> (no such class).</li>
<li><strong>Cancel</strong>: <code>DELETE /bookings/{id}</code>. The booking has its own address now; the answer is <code>204</code>.</li>
</ol>

<details class="qa check"><summary>Check yourself: the class is full. Why 409 and not 404 or 400?</summary><p>404 would mean the class does not exist, but it does. 400 would mean the request is malformed, but it is fine; the same request would have worked an hour ago. 409 says the request conflicts with the current state: the class is full right now.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No login.</strong> The member id is sent in the body, so anyone could book for anyone. Real APIs take the member from the signed-in user (security stations).</li>
<li><strong>No database.</strong> Bookings live in memory.</li>
<li><strong>No waitlist and no cancellation deadline.</strong> The deadline is a design task in Practice.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>FitNest</strong> (a fictional chain of gyms) has a class-booking API with URLs like <code>/bookClass</code>, <code>/cancelBooking</code> and <code>/getMemberBookings</code>, and it answers <code>200</code> to everything, with <code>{"success": false, "message": …}</code> on failure. The app team cannot show members why a booking failed, monitoring cannot count errors (every request "succeeded"), and each new feature adds another verb URL.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a date, <b>when</b> the app asks for classes, <b>then</b> <code>200</code> with that day's classes in start-time order, each with spots left.</li>
<li><b>Given</b> a class with space, <b>when</b> a member books, <b>then</b> <code>201</code> with <code>Location: /bookings/{id}</code>, and that URL returns the booking.</li>
<li><b>Given</b> a full class, <b>then</b> <code>409</code> <em>Class is full</em>. <b>Given</b> the member already booked it, <b>then</b> <code>409</code> <em>Already booked</em>, naming the existing booking.</li>
<li><b>Given</b> an unknown class, <b>then</b> <code>404</code>. <b>Given</b> an unknown or missing member id, <b>then</b> <code>400</code>.</li>
<li><b>Given</b> a booking, <b>when</b> it is cancelled, <b>then</b> <code>204</code> with no body, the spot is free again, and the booking's URL returns <code>404</code>.</li>
<li><b>Given</b> a member, <b>then</b> <code>GET /members/{id}/bookings</code> lists their bookings; an unknown member is <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>URLs are nouns. Methods are the verbs. No <code>/bookClass</code>, no <code>/cancelBooking</code>.</li>
<li>Path parameters identify a resource; query parameters filter a collection.</li>
<li>Status codes by meaning: <code>200</code> read, <code>201</code> created, <code>204</code> done with no body, <code>400</code> bad request, <code>404</code> no such resource, <code>409</code> conflicts with current state.</li>
<li>Dates are ISO (<code>2026-10-19</code>); times are the gym's local time.</li>
<li>Errors are RFC 9457 problems.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Name resources with nouns and choose between nested and top-level URLs.</li>
<li>Choose a path or a query parameter.</li>
<li>Pick 200, 201, 204, 400, 404 or 409 by what happened.</li>
<li>Return <code>Location</code> on create and <code>204</code> on delete.</li>
<li>Keep "what happened" (the outcome) separate from "which status code" (the HTTP answer).</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose", "Success"], [
    ["<code>GET</code>", "<code>/classes?date={yyyy-mm-dd}</code>", "That day's classes, with spots left", "<code>200</code>"],
    ["<code>POST</code>", "<code>/classes/{classId}/bookings</code>", "Book a class. Body: <code>{\"memberId\": 101}</code>", "<code>201</code> + <code>Location</code>"],
    ["<code>GET</code>", "<code>/bookings/{id}</code>", "Read one booking", "<code>200</code>"],
    ["<code>DELETE</code>", "<code>/bookings/{id}</code>", "Cancel a booking", "<code>204</code>"],
    ["<code>GET</code>", "<code>/members/{memberId}/bookings</code>", "A member's bookings", "<code>200</code>"]]) + """
<h2>Why these URLs</h2>
""" + table(["Choice", "Reason"], [
    ["Bookings are <em>created</em> under <code>/classes/{id}/bookings</code>", "You cannot book without a class; the class is part of the address, not repeated in the body."],
    ["Bookings are <em>read and cancelled</em> at <code>/bookings/{id}</code>", "Once it exists, a booking has its own id. The app should not need the class id to cancel it."],
    ["<code>/members/{id}/bookings</code>", "\"My bookings\" is the member's collection, so it is nested under the member."],
    ["<code>date</code> is a query parameter", "It filters the collection of classes; it does not name one thing."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "Meaning here"], [
    ['<span class="pill ok">200</span>', "Here is what you asked to read."],
    ['<span class="pill ok">201</span>', "Booking created; <code>Location</code> says where."],
    ['<span class="pill ok">204</span>', "Booking cancelled; nothing to return."],
    ['<span class="pill warn">400</span>', "The request is wrong: missing or malformed date, missing or unknown member id."],
    ['<span class="pill warn">404</span>', "No such class, booking or member."],
    ['<span class="pill warn">405</span>', "That method is not allowed on that URL."],
    ['<span class="pill warn">409</span>', "Class is full, or this member already booked it."]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-classes", "Case 1: Monday's timetable", "<b>Why:</b> a filtered read of a collection: <code>200</code>, ordered by start time, each class with its spots left."),
    ("02-book", "Case 2: Rohan (member 101) books Morning Yoga", "<b>Why:</b> a new booking, so <code>201</code>; <code>Location</code> is the booking's own address."),
    ("03-full", "Case 3: a third member tries the same class", "<b>Why:</b> Morning Yoga has 2 spots and both are taken. The request is fine, the class is not: <code>409</code>."),
    ("04-already-booked", "Case 4: Rohan taps Book again", "<b>Why:</b> also <code>409</code>, with a different title, and the detail names his existing booking so the app can show it."),
    ("05-unknown-class", "Case 5: an old timetable", "<b>Why:</b> class 999 does not exist: <code>404</code>. The app should refresh its timetable."),
    ("06-member-bookings", "Case 6: Rohan's bookings", "<b>Why:</b> the member's own collection, nested under the member."),
    ("07-cancel", "Case 7: Rohan cancels", "<b>Why:</b> <code>204</code>: the booking is gone and there is nothing to return."),
    ("08-cancel-again", "Case 8: cancel the same booking again", "<b>Why:</b> the booking no longer exists, so <code>404</code>. Whether a repeat delete should be <code>404</code> or <code>204</code> is station 008's topic."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What the API does", "Proved by"], [
    ["Timetable for a date", "<code>200</code>, by start time, spots left", "<code>classesForADateAreListedByStartTimeWithSpotsLeft</code>"],
    ["A date with no classes", "<code>200</code>, empty list", "<code>aDateWithNoClassesIsAnEmptyList</code>"],
    ["Missing date, or <code>19-10-2026</code>", "<code>400</code>", "<code>theDateIsRequiredAndMustBeIso</code>"],
    ["Booking", "<code>201</code> + readable <code>Location</code>", "<code>bookingIs201WithALocationThatCanBeRead</code>"],
    ["Full class", "<code>409</code> <em>Class is full</em>", "<code>aFullClassIs409</code>"],
    ["Booking the same class twice", "<code>409</code> <em>Already booked</em>, names the booking", "<code>bookingTheSameClassTwiceIs409AndNamesTheExistingBooking</code>"],
    ["Unknown class", "<code>404</code>", "<code>anUnknownClassIs404</code>"],
    ["Unknown or missing member", "<code>400</code>", "<code>anUnknownOrMissingMemberIs400</code>"],
    ["Cancel", "<code>204</code>, empty body, spot freed", "<code>cancellingIs204WithNoBodyAndFreesTheSpot</code>"],
    ["Read or cancel a cancelled booking", "<code>404</code>", "<code>aCancelledBookingIsGone</code>"],
    ["A member's bookings; none; unknown member", "<code>200</code> list; <code>200 []</code>; <code>404</code>", "<code>aMembersBookingsAreANestedCollection</code>"],
    ["Old verb URLs; <code>PUT</code> on a booking", "<code>404</code>; <code>405</code>", "<code>theOldVerbUrlsAndWrongMethodsAreNotPartOfTheApi</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Verbs in URLs and <code>200</code> for every outcome, so clients cannot tell what happened.</p>
<p>It feels natural to name endpoints after actions, and <code>{"success": false}</code> looks informative. The first test shows the cost: a full class, a double booking and a class that does not exist all come back as the same <code>200</code> with the same message. The second test sends the same three requests to the resource API and gets <code>409</code>, <code>409</code> (with a different title) and <code>404</code>. Removing the capacity check was tried while building: 3 tests went red.</p>
</div>
""" + code(read(T + "VerbsAndAlways200TrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "ClassController.java", dwn("Defines the five endpoints and turns each booking outcome into its status code.",
        "All the HTTP decisions (URLs, methods, codes) are in one readable place.",
        "No API.",
        "<ul><li>The <code>switch</code> over <code>BookingOutcome</code> must handle every outcome: the compiler refuses to build if one is missing.</li><li><code>@DateTimeFormat(iso = DATE)</code> makes <code>2026-10-19</code> the only accepted date format.</li></ul>")),
    (J + "BookingOutcome.java", dwn("Lists everything that can happen when booking: booked, class not found, class full, already booked.",
        "The schedule reports <em>what happened</em>; only the controller knows HTTP. Each outcome can then get its own code.",
        "The schedule would return <code>true</code>/<code>false</code>, and the reason for a failure would be lost (the trap).")),
    (J + "ClassSchedule.java", dwn("Holds classes, members and bookings; books, cancels and lists.",
        "One place owns the rules: capacity and one booking per member per class.",
        "Rules scattered across endpoints.",
        "<ul><li><code>synchronized</code>: \"count, then add\" cannot interleave with another request, so a class of 2 never gets 3.</li><li><code>clearBookings</code> exists for tests only, so each test starts empty.</li></ul>")),
    (J + "GymClass.java", "<p>A class with its date, start time, capacity and spots left.</p>"),
    (J + "Booking.java", "<p>A booking: its own id, the class, the member and when it was made.</p>"),
    (J + "BookingRequest.java", "<p>The body of a booking: only the member id. The class is in the URL.</p>"),
    (J + "ApiErrors.java", dwn("Adds an <code>errors</code> map (field → message) to validation failures.", "The app learns which field was wrong.", "A bare \"Bad Request\".")),
    (J + "ClassesApplication.java", "<p>Standard Spring Boot entry point.</p>"),
]
tree = """stations/005-designing-rest-resources-for-gym-classes/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/fitnest/classes/
│   ├── ClassController.java   ├── BookingOutcome.java   ├── ClassSchedule.java
│   ├── GymClass.java          ├── Booking.java          ├── BookingRequest.java
│   ├── ApiErrors.java         └── ClassesApplication.java
├── src/test/java/com/fitnest/classes/   (see Tests)
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
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>The booking body is in <code>docs/booking.json</code> (<code>{"memberId":101}</code>), so the commands work in every shell.</p>
""" + code("""curl "http://localhost:8080/classes?date=2026-10-19"

# Book Morning Yoga twice: expect 201, then 409 "Already booked"
curl -i -X POST http://localhost:8080/classes/1/bookings -H "Content-Type: application/json" -d "@docs/booking.json"
curl -i -X POST http://localhost:8080/classes/1/bookings -H "Content-Type: application/json" -d "@docs/booking.json"

# Cancel: paste the Location from the first answer; expect 204
curl -i -X DELETE http://localhost:8080/bookings/PASTE-THE-ID""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>400</code> for <code>/classes?date=19/10/2026</code>", "Only ISO dates are accepted.", "Use <code>2026-10-19</code>."],
    ["<code>415 Unsupported Media Type</code>", "The JSON header is missing.", "Add <code>-H \"Content-Type: application/json\"</code>."],
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>BookingContractTest</code> ({cnt('BookingContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>VerbsAndAlways200TrapTest</code> ({cnt('VerbsAndAlways200TrapTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "VerbsAndAlways200TrapTest.java", "<p>Written first: three different failures, one <code>200</code> from the old API; three distinct answers from the new one.</p>"),
    (T + "BookingContractTest.java", "<p>Every endpoint and every status code, each for its own reason.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app through MockMvc, and an empty booking list before each test.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/fitnest/classes/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=ClassRosterChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "The trainer's roster", "Beginner-friendly", 20,
    "Trainers want to see who booked their class. Add <code>GET /classes/{classId}/bookings</code>: the class's bookings in the order they were made; an empty list for nobody; <code>404</code> for an unknown class.",
    "all three tests in <code>ClassRosterChallengeTest</code> pass.",
    ["Same URL as booking, different method: <code>GET</code> reads the collection, <code>POST</code> adds to it.",
     "Return an <code>Optional</code> from the schedule so \"no such class\" and \"no bookings\" stay different."],
    "challenge/ClassRosterChallengeTest.java", ["challenge/solution/ClassSchedule.java", "challenge/solution/ClassController.java"]) + challenge(2, "Change a class's capacity", "Go deeper", 35,
    "Add <code>PATCH /classes/{classId}</code> with <code>{\"capacity\": 12}</code>: 1 to 50. Lowering capacity below the bookings already made is a <code>409</code>, and nothing changes.",
    "all four tests in <code>CapacityChangeChallengeTest</code> pass.",
    ["<code>PATCH</code> changes part of a resource; the body holds only what changes.",
     "The class map was built with <code>Map.of</code>, which cannot change. Copy it into a <code>HashMap</code>.",
     "Return an outcome from the schedule (updated, not found, below bookings) and let the controller pick the status, as booking does."],
    "challenge/CapacityChangeChallengeTest.java", ["challenge/solution/CapacityRequest.java", "challenge/solution/ClassSchedule.java", "challenge/solution/ClassController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>No cancelling in the last 2 hours</h2>
<p>FitNest wants a rule: a booking cannot be cancelled less than 2 hours before the class. Which status code would you return, and what would the problem body say? The class time is in India Standard Time and the server runs in UTC; how do you compare them? How would you test "1 hour 59 minutes before" without waiting for the clock? (Hint: give the schedule a <code>java.time.Clock</code> and fix it in tests.)</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: three different failures, one answer.</li>
<li>List the resources (classes, bookings, members' bookings) and give each a noun URL.</li>
<li>Write <code>BookingOutcome</code>: every way booking can end.</li>
<li>Map each outcome to the status code that means it.</li>
<li>Return <code>Location</code> on create and <code>204</code> on cancel.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Nouns in URLs, methods as verbs, status by meaning", "Takes a little design up front.", '<span class="pill ok">Chosen</span>'],
    ["Verb URLs, <code>200</code> + <code>success</code> flag", "Clients parse every body; monitoring sees no errors; one URL per action.", '<span class="pill bad">Wrong</span>'],
    ["<code>DELETE /classes/{classId}/bookings/{id}</code>", "Also valid, but every caller must know the class id to cancel.", '<span class="pill warn">Possible</span>'],
    ["<code>POST /bookings</code> with <code>classId</code> in the body", "Also valid and common. Nesting makes \"a booking needs a class\" visible in the URL.", '<span class="pill warn">Possible</span>'],
    ["<code>422</code> for a full class", "422 is for a request that cannot be processed as written. A full class is about the current state, which is what 409 means.", '<span class="pill warn">Debatable</span>'],
    ["<code>404</code> for an unknown member in the body", "404 is about the URL. The URL exists; the body is wrong, so 400 (some APIs choose 422).", '<span class="pill bad">Misleading</span>']]) + """
<h2>Database design</h2>
<p>None in this station. With a database, "one booking per member per class" becomes a unique constraint on <code>(class_id, member_id)</code>, and capacity is checked inside a transaction.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Security</dt><dd>Anyone can book or cancel for any member id: there is no login. Real systems take the member from the signed-in user and check that a booking belongs to the caller before cancelling it.</dd>
<dt>Reliability</dt><dd>Correct status codes let monitoring count real failures: a spike in <code>409</code> means classes are filling up, a spike in <code>404</code> means an app is showing an old timetable.</dd>
<dt>Concurrency</dt><dd>One lock around the schedule keeps capacity correct for one server. With several servers, the database must enforce it.</dd>
<dt>Maintainability</dt><dd>A new feature is a new resource or method, not a new verb URL.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why are verbs in URLs a problem?", "The HTTP method already is the verb. Verb URLs multiply (one per action), hide which resource is affected, and lose the built-in meaning of methods: caches, proxies and clients know GET is safe and DELETE removes, but nothing knows what /cancelBooking does."),
    ("Nested or top-level: /classes/{id}/bookings or /bookings?", "Nest when the child only makes sense inside its parent and you create or list it there. Give it a top-level address once it has its own id, so callers do not need the parent's id to read or cancel it. This station does both."),
    ("Path parameter or query parameter?", "A path parameter identifies a resource (/bookings/{id}). A query parameter filters, sorts or pages a collection (/classes?date=...)."),
    ("409 or 400 for a full class?", "400 means the request itself is wrong. A full class is a conflict with the current state: the same request would succeed with a free spot. That is 409."),
    ("What should DELETE return?", "204 No Content when it succeeds and there is nothing useful to send. Here, a repeat DELETE is 404 because the booking is gone; station 008 discusses when 204 for both is the better contract."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can say which test fails if the capacity check goes."],
    ["Design", "Noun URLs; every outcome has its own code.", "You can defend nested-then-top-level for bookings."],
    ["Tests", "A test for each status code.", "You wrote the trap test before designing the URLs."],
    ["Explanation", "You can explain 409 against 400 and 404.", "You can explain why the outcome type keeps HTTP out of the schedule."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any API design you are asked to review:</p>
<ul class="rules">
<li>Is there a verb in any URL?</li>
<li>Does any failure come back as <code>200</code>?</li>
<li>Does every create return <code>201</code> and a <code>Location</code> that can be read?</li>
<li>Can two different failures be told apart by status code (or at least by problem title)?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
