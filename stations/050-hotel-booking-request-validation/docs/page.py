"""Station 050 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 50,
    "stack": "Spring Boot 4.1.1 · Java 25 · Jakarta Bean Validation (Hibernate Validator) · custom ConstraintValidator · validation groups · RFC 9457 problem details",
    "simulation": "Hotels, room types and guests are demo data, not Ghoomo's. A booking request is a record kept in memory: no room is held, nothing is paid, and it is gone when the app restarts. Stay limits (30 nights, 365 days ahead) are demo rules.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/ghoomo/bookings/"
T = "src/test/java/com/ghoomo/bookings/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Field validation", "A rule about one value on its own.", "\"The date must be a real date.\"", "<code>@NotNull</code>, <code>@Min</code>, <code>@IndianMobile</code>"),
    ("Cross-field validation", "A rule that compares two or more values.", "\"Check-out comes after check-in.\"", "<code>@ValidStay</code>, <code>@RoomFitsGuests</code>"),
    ("ConstraintValidator", "A class you write to check a rule Bean Validation does not have built in.", "A custom stamp at the counter.", "<code>ValidStay.Validator</code>"),
    ("Validation group", "A named set of rules you run at a chosen moment.", "Checking the form is filled in, then checking it makes sense.", "<code>Consistency</code>"),
    ("400 Bad Request", "The request is broken: unreadable, or a field breaks its own rule.", "A form with the phone box empty.", "Default group"),
    ("422 Unprocessable Content", "Every field is fine, but together they describe something impossible.", "A neat form asking to leave before arriving.", "Consistency group"),
]
STORY = [
    ("Careful field checks", "Ghoomo's booking API checked every field: dates required and in the future, 1 to 10 adults, 0 to 10 children, a valid phone."),
    ("Impossible bookings got through", "Support found requests with check-out before check-in, and 6 guests in a room for 2. Every field was valid on its own; nothing compared them."),
    ("The fix", "Rules that look at the whole request, written as custom validators, run only once each field has passed, and answered with 422 instead of 400."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Valid parts do not make a valid whole. Some rules can only be checked by looking at two fields at once.</p>

<h2>What are we building?</h2>
<p><code>POST /hotel-bookings</code> takes a booking request and either records it (<code>201</code>), says a field is broken (<code>400</code>), or says the fields do not add up (<code>422</code>), naming each field with its message. <code>GET /hotel-bookings/{id}</code> reads a recorded request back.</p>

<h2>An everyday analogy</h2>
<p>A hotel front desk. First the clerk checks the form is filled in properly: dates written as dates, a phone number with 10 digits. Only then do they check it makes sense: leaving after arriving, and a room big enough for everyone. A form with an empty box goes back for the box, not for a lecture on room sizes.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Read</strong> the JSON; unreadable bodies and wrong types are <code>400</code>.</li>
<li><strong>Field rules</strong> (the Default group) run on <code>@Valid</code>; any failure is <code>400</code>, with every broken field named.</li>
<li><strong>Cross-field rules</strong> (the <code>Consistency</code> group) run next; any failure is <code>422</code>, again naming fields.</li>
<li><strong>Record</strong> the request and answer <code>201</code> with its <code>Location</code>.</li>
</ol>

<details class="qa check"><summary>Check yourself: why not run all the rules at once?</summary><p>A cross-field rule needs its fields. With check-in missing, "the stay is impossible" would be a confusing second error about the same mistake. Running the groups in order reports the missing date alone.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No availability.</strong> Whether the room is free is station 044.</li>
<li><strong>No database.</strong> Hotels and requests live in memory.</li>
<li><strong>No payment.</strong> A request record, not a confirmed booking.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Ghoomo</strong> (a fictional travel app) accepted booking requests that could never be honoured, because each field was checked alone. Staff had to call guests back to sort them out.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> 2 adults, a STANDARD room, 3 nights starting in 30 days, <b>then</b> <code>201</code>, 3 nights, the phone as 10 digits, and <code>GET</code> returns it.</li>
<li><b>Given</b> check-out before check-in, or on the same day, <b>then</b> <code>422</code> naming <code>checkOut</code>.</li>
<li><b>Given</b> 4 adults and 2 children in a STANDARD room (sleeps 2), <b>then</b> <code>422</code> naming <code>guests</code>.</li>
<li><b>Given</b> check-in yesterday, over 365 days ahead, a stay over 30 nights, an unknown hotel or room type, <b>then</b> <code>422</code> naming the field.</li>
<li><b>Given</b> 0 adults, a phone of 5 digits, no room type, a date as 30-11-2026, 2.5 adults, or broken JSON, <b>then</b> <code>400</code>.</li>
<li><b>Given</b> a missing check-in and 6 guests, <b>then</b> only the <code>400</code> for check-in.</li>
<li><b>Given</b> an unknown booking id, <b>then</b> <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>A rule about one field is a field constraint; a rule about several is a class-level constraint.</li>
<li>Field failures are <code>400</code>, cross-field failures <code>422</code>, both RFC 9457 problems with an <code>errors</code> map, field to message.</li>
<li>"Today" is today in India (<code>Asia/Kolkata</code>).</li>
<li>Room types are identifiers, normalised with <code>Locale.ROOT</code>.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Write a custom <code>ConstraintValidator</code> for one field and for a whole object.</li>
<li>Use validation groups to order checks and to separate <code>400</code> from <code>422</code>.</li>
<li>Give a validator Spring beans (a <code>Clock</code>, a catalogue).</li>
<li>Report every error on the field it concerns.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/hotel-bookings</code>", "Request a booking: <code>hotelId</code>, <code>roomType</code>, <code>checkIn</code>, <code>checkOut</code>, <code>adults</code> (1 to 10), <code>children</code> (0 to 10, optional), <code>guestName</code>, <code>phone</code>."],
    ["<code>GET</code>", "<code>/hotel-bookings/{id}</code>", "Read a recorded request back (added so \"not found\" has something to miss)."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Recorded; <code>Location</code> points at it"],
    ['<span class="pill ok">200</span>', "The request, read back"],
    ['<span class="pill warn">400</span>', "Unreadable JSON, a wrong type, or a field that breaks its own rule"],
    ['<span class="pill warn">404</span>', "No such booking request"],
    ['<span class="pill warn">422</span>', "Every field is fine, but together they are impossible: dates, stay length, hotel, room type or guests"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. Dates are relative to that day (check-in in 30 days). JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-a-valid-request", "Case 1: a valid request", "<b>Why:</b> every field fine, and they add up: recorded."),
    ("02-read-it-back", "Case 2: read it back", "<b>Why:</b> <code>200</code>."),
    ("03-check-out-before-check-in", "Case 3: check-out before check-in", "<b>Why:</b> the first support ticket: <code>422</code> on <code>checkOut</code>."),
    ("04-six-guests-in-a-standard-room", "Case 4: 4 adults and 2 children in a STANDARD room", "<b>Why:</b> the second ticket: <code>422</code> on <code>guests</code>."),
    ("05-a-bad-phone-and-no-adults", "Case 5: a 5-digit phone and 0 adults", "<b>Why:</b> two broken fields, both named: <code>400</code>."),
    ("06-a-missing-date-and-six-guests", "Case 6: no check-in and 6 adults", "<b>Why:</b> the field error alone; the room rule waits: <code>400</code>."),
    ("07-no-such-booking", "Case 7: booking 999", "<b>Why:</b> <code>404</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A valid request, read back", "<code>201</code>, <code>200</code>", "<code>aValidRequestIsRecordedAndCanBeReadBack</code>"],
    ["\"family\" and \"+91 98765-43210\" on a Turkish server", "FAMILY, 9876543210", "<code>phoneAndRoomTypeAreNormalisedEvenOnATurkishServer</code>"],
    ["0 adults, bad phone, no room type, non-ISO date, 2.5 adults, broken JSON", "<code>400</code>", "<code>brokenFieldsAre400AndNamed</code>"],
    ["0 nights, 31 nights, yesterday, 366 days ahead, unknown hotel or room", "<code>422</code>, field named", "<code>fieldsThatDoNotAddUpAre422AndNamed</code>"],
    ["Tonight for one night; exactly 30 nights; 4 in a room for 4; no children field", "Allowed", "<code>theEdgesAreAllowed</code>"],
    ["A missing date and too many guests", "Only the <code>400</code>", "<code>aBrokenFieldIsReportedAloneNotAsAnImpossibleStay</code>"],
    ["Unknown booking", "<code>404</code>", "<code>unknownBookingsAre404</code>"],
    ["Default group vs Consistency group", "Cross-field rules run only in their group", "<code>BookingValidatorTest</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Validating each field alone, so check-out before check-in passes.</p>
<p>The old request is kept in the tests as <code>OldHotelBookingRequest</code>: careful field rules, including <code>@FutureOrPresent</code> on both dates. The test runs the two bookings from the support tickets through the app's own validator: no violations at all. Then it sends the same bookings to the fixed API, which answers <code>422</code> and names the field.</p>
<p>While building, each part was undone once. Without <code>@ValidStay</code>, 3 tests turned red; without <code>@RoomFitsGuests</code>, 3; uppercasing room types with the server's locale instead of <code>Locale.ROOT</code>, 1 (the Turkish test). Moving the room rule into the Default group turned 5 red: it ran next to the field rules, so a missing date also produced a guests error, and too many guests became a <code>400</code>.</p>
</div>
""" + code(read(T + "FieldByFieldTrapTest.java"), "java") + code(read(T + "OldHotelBookingRequest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "BookingController.java", dwn("<code>@Valid</code> runs the field rules; then the desk; <code>Location</code> on success.", "Field errors stop here with <code>400</code>.", "Cross-field checks on half-filled requests.")),
    (J + "BookingDesk.java", dwn("Runs the <code>Consistency</code> group; answers <code>422</code> with an errors map, or records the request.",
        "The second step, on purpose after the first.", "Impossible bookings recorded.")),
    (J + "HotelBookingRequest.java", dwn("The request: field rules on components, two class-level rules in the <code>Consistency</code> group.",
        "Which rule is which, visible in one place.", "Rules scattered through the service.")),
    (J + "ValidStay.java", dwn("Dates: today or later (India), within a year, check-out after check-in, at most 30 nights.",
        "A class-level validator, made by Spring so it gets the <code>Clock</code>.", "\"Today\" in UTC, and a check-out before check-in.",
        "<ul><li>Each failure is put on its field (<code>addPropertyNode</code>), so the form can show it in the right place.</li><li>Missing dates return <code>true</code>: they are <code>@NotNull</code>'s errors, already reported.</li></ul>")),
    (J + "RoomFitsGuests.java", dwn("Hotel, room type, and adults + children within what the room sleeps.", "Gets the catalogue bean injected.", "6 guests in a room for 2.")),
    (J + "IndianMobile.java", dwn("A field-level validator: 10 digits starting 6 to 9, with +91, 0, spaces or hyphens allowed.", "One reusable annotation.", "A regex copied into every request.")),
    (J + "Consistency.java", "<p>The validation group: an empty interface used as a name.</p>"),
    (J + "ApiErrors.java", "<p>Adds the <code>errors</code> map to Spring's <code>400</code> problem.</p>"),
    (J + "HotelCatalog.java", "<p>Demo hotels and what each room type sleeps; room types normalised with <code>Locale.ROOT</code>.</p>"),
    (J + "BookingsApplication.java", "<p>Entry point; a <code>Clock</code> in India time.</p>"),
    ("src/main/resources/application.yaml", "<p>Problem details on; decimals refused for whole-number fields.</p>"),
]
tree = """stations/050-hotel-booking-request-validation/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/ghoomo/bookings/
│   ├── BookingController.java   ├── BookingDesk.java   ├── HotelBookingRequest.java   ├── Consistency.java
│   ├── ValidStay.java   ├── RoomFitsGuests.java   ├── IndianMobile.java
│   ├── ApiErrors.java   ├── HotelCatalog.java   └── BookingsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/ghoomo/bookings/   (see Tests)
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
<p>In <code>HotelBookingRequest</code>, remove <code>groups = Consistency.class</code> from <code>@RoomFitsGuests</code> and run the contract tests.</p>
""" + code("""./mvnw test -Dtest=BookingContractTest""", "bash") + """
<p>Too many guests now comes back as <code>400</code>, and a request missing its check-in also gets a guests error. Put it back.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["A class-level rule never runs", "It is in a group nobody validates.", "Validate that group (<code>validator.validate(r, Consistency.class)</code>), or list it in a <code>@GroupSequence</code>."],
    ["<code>NullPointerException</code> inside a validator", "A cross-field validator ran with a field missing.", "Return <code>true</code> for missing values, and run after the field rules."],
    ["A cross-field error shows at the top, not on a field", "The default violation has no property path.", "<code>disableDefaultConstraintViolation()</code>, then <code>addPropertyNode(\"checkOut\")</code>."],
    ["Constructor injection fails in a validator", "It was created outside Spring.", "Validate with Spring's <code>Validator</code> bean, not <code>Validation.buildDefaultValidatorFactory()</code>."],
    ["\"FAMİLY\" with a dotted İ", "<code>toUpperCase()</code> uses the server locale.", "<code>toUpperCase(Locale.ROOT)</code> for identifiers."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the validators.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>BookingContractTest</code> ({cnt('BookingContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>FieldByFieldTrapTest</code> ({cnt('FieldByFieldTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station's concepts", "Groups and validators on their own", f"<code>BookingValidatorTest</code> ({cnt('BookingValidatorTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Hibernate Validator. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "FieldByFieldTrapTest.java", "<p>Written first: both support tickets pass the old rules, and fail the new API with <code>422</code>.</p>"),
    (T + "BookingContractTest.java", "<p>Valid, <code>400</code>, <code>422</code>, edges, the order of checks, <code>404</code>.</p>"),
    (T + "BookingValidatorTest.java", "<p>Which group runs which rule; the mobile formats accepted and refused.</p>"),
    (T + "OldHotelBookingRequest.java", "<p>The old request, kept only in tests.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: a valid request with dates relative to today in India.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/ghoomo/bookings/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=ChildAgesChallengeTest</code>.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "One age per child", "Beginner-friendly", 25,
    "Add <code>childAges</code>: one age, 0 to 17, per child. An age out of range is a broken field (<code>400</code>); a list that does not match <code>children</code> is a request that does not add up (<code>422</code>).",
    "both tests in <code>ChildAgesChallengeTest</code> pass.",
    ["Field rules on list elements: <code>List&lt;@NotNull @Min(0) @Max(17) Integer&gt;</code>.",
     "A new class-level constraint in the <code>Consistency</code> group compares the list's size with <code>children</code>.",
     "Keep an eight-argument constructor so existing code still compiles."],
    "challenge/ChildAgesChallengeTest.java", ["challenge/solution/ChildAgesMatch.java", "challenge/solution/HotelBookingRequest.java", "challenge/solution/BookingDesk.java"]) + challenge(2, "A GSTIN for the invoice", "Go deeper", 30,
    "Add an optional <code>gstin</code> with a field-level validator: the 15-character shape and the published check character. Show it upper case. A format check only: it does not prove the GSTIN is registered.",
    "both tests in <code>GstinChallengeTest</code> pass.",
    ["Check character: for the first 14 characters (digits 0 to 9, letters 10 to 35), multiply by 1 and 2 alternately, add each product's quotient and remainder by 36, and the check is (36 − sum mod 36) mod 36.",
     "<code>null</code> is valid: optional means the validator says yes to nothing."],
    "challenge/GstinChallengeTest.java", ["challenge/solution/Gstin.java", "challenge/solution/HotelBookingRequest.java", "challenge/solution/BookingDesk.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Where does each check belong?</h2>
<p>For each rule here (date format, check-out after check-in, room sleeps everyone, room free on those nights, phone is real), decide where it is checked: in the app's form, in the request (400), in the service (422), in the database, or by calling someone else. Which ones must be repeated on the server even if the app checks them?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the support tickets through the old rules.</li>
<li>Sort every rule: about one field, or about several (or about the catalogue)?</li>
<li>Write the cross-field rules as class-level constraints in their own group; put each violation on its field.</li>
<li>Run the groups in order and map them to <code>400</code> and <code>422</code>.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Class-level constraints in a group, run after <code>@Valid</code>", "Two small annotations and validators.", '<span class="pill ok">Chosen</span>'],
    ["Field rules only", "Impossible combinations pass.", '<span class="pill bad">The trap</span>'],
    ["<code>if</code> checks in the service", "Works, but rules scatter and errors take ad-hoc shapes.", '<span class="pill warn">Fine for one rule</span>'],
    ["A <code>@GroupSequence</code> on the request", "One <code>@Valid</code> runs both in order, but both failures become the same status.", '<span class="pill warn">When 400 for all is fine</span>'],
    ["<code>400</code> for everything", "Clients cannot tell \"fix this field\" from \"rethink the booking\".", '<span class="pill warn">Common, less helpful</span>']]) + """
<h2>Database design</h2>
<p>None in this station: requests live in a <code>ConcurrentHashMap</code>. When they move to a table, the stay rule becomes a constraint too (<code>CHECK (check_out &gt; check_in)</code>), so a script that skips the API still cannot store one.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Time zones</dt><dd>"Check-in today" depends on whose today. The app uses India time; a hotel abroad would use the hotel's zone.</dd>
<dt>Clients read your errors</dt><dd>The <code>errors</code> map lets a form put each message beside its field. Changing a key breaks every client that reads it.</dd>
<dt>Rules change</dt><dd>30 nights and 365 days are business numbers. Keep them in one place, and test the edges so a change is a one-line diff.</dd>
<dt>Validation is not authorisation</dt><dd>A valid request from the wrong user is still wrong; that check is separate.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("How do you validate that one field depends on another?", "A class-level constraint: an annotation on the type and a ConstraintValidator that receives the whole object. Put the violation on the relevant field with addPropertyNode."),
    ("What are validation groups for?", "To run subsets of rules at chosen moments: here, field rules first and cross-field rules only once the fields are valid. Groups can also differ between create and update."),
    ("400 or 422?", "400 when the request is malformed or a field breaks its own rule; 422 when it is well-formed but describes something the server cannot do. Many APIs use 400 for both; the split helps clients know what to fix."),
    ("Can a ConstraintValidator use Spring beans?", "Yes, when validation goes through Spring's Validator: Spring creates the validator and injects its constructor arguments, such as a Clock or a repository."),
    ("Why return true for null in a custom validator?", "Each constraint checks one thing. Whether a value is required is @NotNull's job; returning false for null would report the same mistake twice."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You moved a rule between groups and explained the result."],
    ["Validators", "A field and a class-level validator.", "A validator using Spring beans."],
    ["Errors", "Every error on its field.", "A clear rule for 400 vs 422 you can defend."],
    ["Edges", "Zero nights refused, one night allowed.", "Time zone and locale considered."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any request validation:</p>
<ul class="rules">
<li>Which rules compare two fields, and where are they checked?</li>
<li>Can a cross-field rule run on a half-filled request?</li>
<li>Does each error name the field the user must change?</li>
<li>Are the edges (zero, one, the maximum) tested on both sides?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
