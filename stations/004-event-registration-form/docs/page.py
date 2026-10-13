"""Station 004 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 4,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · Bean Validation · MockMvc",
    "simulation": "Registrations are kept in the app's memory and lost on restart. Two events are fixed in the code. No email is sent.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/seatsure/registrations/"
T = "src/test/java/com/seatsure/registrations/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Request body", "The data sent with a <code>POST</code>, here as JSON.", "The filled-in form you hand over.", "<code>{\"name\":\"Asha\",\"tickets\":2,…}</code>"),
    ("DTO record", "A small class that only describes the shape of incoming data.", "The blank form itself: which boxes exist.", "<code>RegistrationRequest</code>"),
    ("Bean Validation", "Rules written as annotations on fields, checked automatically.", "\"Required\" stars on a form.", "<code>@NotBlank</code>, <code>@Email</code>, <code>@Min(1)</code>"),
    ("<code>@Valid</code>", "Tells Spring to check those rules before your method runs.", "The clerk who checks the form before filing it.", "On the request body in the controller."),
    ("201 Created", "\"I made something new.\"", "A receipt with a reference number.", "A new registration."),
    ("Location header", "Where the new thing can be read.", "\"Your file is in cabinet 3, drawer 2.\"", "<code>/events/…/registrations/{id}</code>"),
    ("400 Bad Request", "\"Your request is wrong; fix it and send again.\"", "A form returned with the mistakes circled.", "Empty name, 0 tickets, malformed email."),
]
STORY = [
    ("Registrations open for a tech summit", "SeatSure's form collects name, email, phone and number of tickets."),
    ("Garbage gets in", "A browser plugin, an old app version and a script all skip the form's checks. The server saves empty names, emails like \"asha\" and orders for 0 tickets."),
    ("The organiser exports a mess", "Badges print blank, confirmation emails bounce, seat counts are wrong. The fix: the server checks every registration itself, and refuses bad ones with a clear list of what to fix."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Checks in the form are a convenience for the user. Checks on the server are the only ones you can rely on, because anyone can send a request without your form.</p>

<h2>What are we building?</h2>
<p>Two endpoints: <code>POST /events/{eventId}/registrations</code> creates a registration after checking every field; <code>GET /events/{eventId}/registrations/{id}</code> reads it back. A valid registration gets <code>201</code> and its address; an invalid one gets <code>400</code> listing each mistake, and nothing is saved.</p>

<h2>An everyday analogy</h2>
<p>At a passport office, the clerk checks your form before filing it: name filled in, photo attached, signature present. If something is missing, the form comes back with each problem marked, and nothing is filed. If it is fine, you get a receipt with a reference number. That receipt is <code>201 Created</code> with a <code>Location</code>.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>The form sends JSON</strong> to <code>POST /events/pune-tech-summit-2026/registrations</code>.</li>
<li><strong>Spring turns it into a record</strong>, trims spaces, and checks every rule on it. Any broken rule: <code>400</code> with one message per field.</li>
<li><strong>The server checks the event exists</strong> (<code>404</code> if not), then saves the registration with its own id and time.</li>
<li><strong>The answer</strong> is <code>201 Created</code>, a <code>Location</code> to read it back, and the saved registration.</li>
</ol>

<details class="qa check"><summary>Check yourself: the form in the browser already refuses 0 tickets. Why check again on the server?</summary><p>Because the browser form is not the only way to reach the server. Anyone can send the same request with curl, a script, or an old version of the app. The server is the last place every request passes through, so that is where the rules must hold.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No database.</strong> Registrations live in memory and vanish on restart.</li>
<li><strong>No duplicate check.</strong> The same email can register twice; Practice challenge 1 adds the rule.</li>
<li><strong>No seat limit and no payment.</strong> Tickets are a number, nothing more.</li>
<li><strong>No confirmation email.</strong> <code>@Email</code> checks the shape of an address, not that it exists.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>SeatSure</strong> (a fictional event-ticketing platform) runs registrations for conferences and festivals. Its API saves whatever it receives. The organiser of the Pune Tech Summit exported registrations and found blank names, emails without an <code>@</code>, and orders for 0 tickets. Badges could not be printed, confirmation emails bounced, and the headcount was wrong.</p>
<p>The web form had checks, but the mobile app's old version did not, and some registrations came from a partner's script. The server was trusting every client to have checked.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a name, a valid email and 1 to 10 tickets, <b>when</b> the form is sent, <b>then</b> <code>201 Created</code> with a <code>Location</code> header and the saved registration.</li>
<li><b>Given</b> the <code>Location</code>, <b>when</b> it is read, <b>then</b> the same registration comes back.</li>
<li><b>Given</b> a blank name, a malformed email, 0 or 11 tickets, or a wrong phone, <b>then</b> <code>400</code> listing every bad field, and nothing is saved.</li>
<li><b>Given</b> <code>"tickets": 2.5</code> or <code>"tickets": "two"</code>, <b>then</b> <code>400</code>: never rounded to 2.</li>
<li><b>Given</b> an <code>id</code> or <code>registeredAt</code> in the body, <b>then</b> they are ignored; the server sets both.</li>
<li><b>Given</b> an unknown event, <b>then</b> <code>404</code>. <b>Given</b> a registration id from another event, <b>then</b> <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li><code>name</code>: required, 1–100 characters after trimming.</li>
<li><code>email</code>: required, at most 254 characters, shaped like an email address.</li>
<li><code>phone</code>: optional; when given, 10 digits starting with 6–9 (a demo rule, not an official numbering rule). Blank means no phone.</li>
<li><code>tickets</code>: required whole number, 1 to 10 (a demo rule).</li>
<li>Body must be JSON (<code>415</code> otherwise). Errors are RFC 9457 problems with an <code>errors</code> map.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Receive a JSON body into a record with <code>@PostMapping</code> and <code>@RequestBody</code>.</li>
<li>Write validation rules with Bean Validation and switch them on with <code>@Valid</code>.</li>
<li>Return <code>201 Created</code> with a <code>Location</code> header.</li>
<li>Explain why the server must validate even when the client does.</li>
<li>Spot a silent conversion (2.5 tickets becoming 2) and turn it into a <code>400</code>.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/events/{eventId}/registrations</code>", "Register for an event."],
    ["<code>GET</code>", "<code>/events/{eventId}/registrations/{id}</code>", "Read one registration."]]) + """
<h2>Request body</h2>
""" + table(["Field", "Type", "Rule"], [
    ["<code>name</code>", "string", "Required. Trimmed, then 1–100 characters."],
    ["<code>email</code>", "string", "Required. Trimmed, at most 254 characters, <code>name@domain</code> shape."],
    ["<code>phone</code>", "string", "Optional. 10 digits starting with 6–9. Blank is treated as absent."],
    ["<code>tickets</code>", "integer", "Required. 1 to 10. No fractions."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When", "Body"], [
    ['<span class="pill ok">201</span>', "Registration saved", "The registration; <code>Location</code> header"],
    ['<span class="pill ok">200</span>', "<code>GET</code> of an existing registration", "The registration"],
    ['<span class="pill warn">400</span>', "Invalid field, broken or missing JSON, malformed id", "Problem with <code>errors</code> (field → message) for field rules"],
    ['<span class="pill warn">404</span>', "Unknown event, or no such registration under this event", "Problem"],
    ['<span class="pill warn">415</span>', "Body is not JSON", "Problem"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-register", "Case 1: a valid registration", "<b>Why:</b> every rule passes, so the server saves it with its own id and time: <code>201</code>, and <code>Location</code> says where to read it."),
    ("02-garbage", "Case 2: the form the old app sent", "<b>Why:</b> three rules broken, three messages, in one answer. Nothing is saved, so the organiser's export stays clean."),
    ("03-fraction", "Case 3: 2.5 tickets", "<b>Why:</b> the field is a whole number. Without a setting, Jackson would quietly store 2; here it is refused. The <code>400</code> comes from reading the JSON, before validation, so there is no <code>errors</code> map."),
    ("04-read-back", "Case 4: read it back", "<b>Why:</b> the <code>Location</code> from case 1 returns the same registration."),
    ("05-unknown-event", "Case 5: unknown event", "<b>Why:</b> the body is valid, but there is no such event, so <code>404</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What the API does", "Proved by"], [
    ["Valid registration", "<code>201</code>, <code>Location</code>, body", "<code>validRegistrationIs201WithLocationAndBody</code>"],
    ["Read back at <code>Location</code>", "Same registration", "<code>theRegistrationCanBeReadBackAtItsLocation</code>"],
    ["Spaces around values; blank phone", "Trimmed; phone <code>null</code>", "<code>surroundingSpacesAreTrimmedAndABlankPhoneMeansNoPhone</code>"],
    ["Blank name, bad email, 0 tickets", "<code>400</code>, one message each, nothing saved", "<code>withValidationTheSameRequestIs400AndNothingIsSaved</code>"],
    ["Empty object <code>{}</code>", "<code>400</code> listing name, email, tickets", "<code>everyMissingFieldIsListed</code>"],
    ["11 tickets; 0 or negative", "<code>400</code>", "<code>moreThan10TicketsIs400</code>, <code>ticketsFrom1To10</code>"],
    ["2.5 tickets, \"two\" tickets", "<code>400</code>, never rounded", "<code>ticketsMustBeAWholeNumber</code>"],
    ["Wrong phone, <code>+91</code> prefix", "<code>400</code>", "<code>aWrongPhoneIs400</code>, <code>phoneIsOptionalButMustBeAMobileNumberWhenGiven</code>"],
    ["Name of 101 characters", "Rejected", "<code>nameLongerThan100IsRejected</code>"],
    ["<code>asha@localhost</code>", "Accepted: valid shape. Only a confirmation email proves an address works", "<code>emailChecksTheShapeNotThatTheAddressExists</code>"],
    ["Broken or missing JSON", "<code>400</code>", "<code>brokenOrMissingJsonIs400</code>"],
    ["Form-encoded body", "<code>415</code>", "<code>aFormPostInsteadOfJsonIs415</code>"],
    ["Client sends <code>id</code>, <code>registeredAt</code>", "Ignored; the server sets them", "<code>theClientCannotChooseTheIdOrTheTime</code>"],
    ["Unknown event; unknown registration; another event's registration", "<code>404</code>", "<code>unknownEventIs404ForPostAndGet</code>, <code>unknownRegistrationIs404</code>, <code>aRegistrationIsNotFoundUnderAnotherEvent</code>"],
    ["Registration id that is not a UUID", "<code>400</code>", "<code>aMalformedRegistrationIdIs400</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Trusting the client: no validation, so 0 tickets and empty names are saved.</p>
<p>"The form already checks it" is the reasoning. The first test sends what a script or an old app sends, to a "before" controller without <code>@Valid</code>: it is saved. The second sends the same body to the real API: <code>400</code>, three messages, nothing saved. Removing <code>@Valid</code> from the real controller was tried while building: 4 tests went red.</p>
</div>
""" + code(read(T + "TrustingTheClientTrapTest.java"), "java") + """
<h3>A second trap the tests found</h3>
<p>While building this station, <code>ticketsMustBeAWholeNumber</code> failed: <code>"tickets": 2.5</code> was saved as 2 tickets. Jackson converts a fraction to a whole number by default, before validation ever sees it. One setting in <code>application.yaml</code> (<code>accept-float-as-int: false</code>) makes it a <code>400</code>. The test was red before the setting and green after.</p>
"""

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "RegistrationController.java", dwn("Receives the two endpoints. <code>@Valid</code> on the body makes Spring check every rule first; then it checks the event, saves, and answers <code>201</code> with <code>Location</code>.",
        "Keeps HTTP decisions (status codes, headers) in one place.",
        "No endpoints. Without <code>@Valid</code>, the rules on the record are never checked (the trap).",
        "<ul><li><code>ResponseEntity.created(location).body(saved)</code> sets the status and the header together.</li></ul>")),
    (J + "RegistrationRequest.java", dwn("The shape of the form, with every rule as an annotation. The compact constructor trims text before the rules are checked.",
        "The rules live next to the fields they guard, and the same rules apply to every client.",
        "Each client would need its own checks, and one of them would forget.",
        "<ul><li>Trimming in the constructor turns <code>\"   \"</code> into <code>\"\"</code>, which <code>@NotBlank</code> then rejects.</li><li><code>Integer tickets</code>, not <code>int</code>: a missing value is <code>null</code> and <code>@NotNull</code> reports it, instead of silently becoming 0.</li></ul>")),
    (J + "Registration.java", "<p>The saved registration and the response body. Only the server sets <code>id</code>, <code>eventId</code> and <code>registeredAt</code>.</p>"),
    (J + "RegistrationStore.java", dwn("Knows the two events and keeps registrations in a <code>ConcurrentHashMap</code>.",
        "Several requests can save at the same moment on different threads; a plain <code>HashMap</code> can lose entries or break under that.",
        "Nowhere to keep registrations.",
        "<ul><li><code>find</code> filters by event, so an id from one event is not found under another.</li></ul>")),
    (J + "ApiErrors.java", dwn("Adds an <code>errors</code> map (field → message) to validation failures.",
        "The form can show each message next to its input.",
        "The client gets \"Bad Request\" and has to guess which field is wrong.")),
    ("src/main/resources/application.yaml", "<p>Turns off Jackson's float-to-int conversion, so 2.5 tickets is a <code>400</code>.</p>"),
    (J + "RegistrationsApplication.java", "<p>Standard Spring Boot entry point.</p>"),
    ("pom.xml", "<p>Web MVC and validation; test starters for JUnit and MockMvc.</p>"),
]
tree = """stations/004-event-registration-form/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/seatsure/registrations/
│   ├── RegistrationController.java   ├── RegistrationRequest.java
│   ├── Registration.java             ├── RegistrationStore.java
│   ├── ApiErrors.java                └── RegistrationsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/seatsure/registrations/   (see Tests)
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
<p>JSON quoting differs between shells, so the bodies are files: <code>docs/registration.json</code> (valid) and <code>docs/registration-garbage.json</code> (the old app's form).</p>
""" + code("""# Valid: expect 201 and a Location header
curl -i -X POST http://localhost:8080/events/pune-tech-summit-2026/registrations -H "Content-Type: application/json" -d "@docs/registration.json"

# Garbage: expect 400 with three messages under "errors"
curl -i -X POST http://localhost:8080/events/pune-tech-summit-2026/registrations -H "Content-Type: application/json" -d "@docs/registration-garbage.json"

# Read back: paste the Location from the first answer
curl -i http://localhost:8080/events/pune-tech-summit-2026/registrations/PASTE-THE-ID""", "bash") + """
<p>In PowerShell, write <code>curl.exe</code> if <code>curl</code> opens a different command.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>415 Unsupported Media Type</code>", "The <code>Content-Type: application/json</code> header is missing.", "Add <code>-H \"Content-Type: application/json\"</code>."],
    ["<code>400</code> with \"Failed to read request\"", "The JSON is broken, often by shell quoting.", "Send the body from a file with <code>-d \"@docs/registration.json\"</code>."],
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>RegistrationContractTest</code> ({cnt('RegistrationContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>TrustingTheClientTrapTest</code> ({cnt('TrustingTheClientTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Each validation rule at its boundaries", f"<code>RegistrationRequestTest</code> ({cnt('RegistrationRequestTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "TrustingTheClientTrapTest.java", "<p>Written first: the old app's form saved without <code>@Valid</code>, then refused with it.</p>"),
    (T + "RegistrationContractTest.java", "<p>Created, read back, trimmed, and every way to be refused.</p>"),
    (T + "RegistrationRequestTest.java", "<p>The rules on their own, with a plain <code>Validator</code>: 1 and 10 tickets pass, 0 and 11 do not; what <code>@Email</code> does not check.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app through MockMvc, and a new email for each test so tests never depend on each other.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/seatsure/registrations/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=DuplicateEmailChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "One registration per email", "Beginner-friendly", 30,
    "The same email may register only once per event, whatever its letter case or spaces. A second attempt gets <code>409 Conflict</code> with the title <em>Already registered</em>. The same email may register for a different event.",
    "both tests in <code>DuplicateEmailChallengeTest</code> pass, and the station's tests still pass.",
    ["The request is already trimmed; lower-case the email with <code>Locale.ROOT</code> for the comparison.",
     "\"Check, then save\" lets two requests at the same moment both pass. <code>ConcurrentHashMap.putIfAbsent</code> does the check and the save in one step.",
     "Throw an <code>ErrorResponseException</code> with <code>HttpStatus.CONFLICT</code>; no handler needed."],
    "challenge/DuplicateEmailChallengeTest.java", ["challenge/solution/RegistrationStore.java", "challenge/solution/RegistrationController.java"]) + challenge(2, "Export for the organiser, safely", "Go deeper", 40,
    "Add <code>GET /events/{eventId}/registrations/export</code> returning <code>text/csv</code>: a header row, then one row per registration. Names with commas or quotes must stay one cell, and a name like <code>=HYPERLINK(…)</code> must not run as a formula when the file opens in a spreadsheet.",
    "all four tests in <code>CsvExportChallengeTest</code> pass.",
    ["CSV rule: wrap a field in double quotes when it contains a comma, a quote or a line break, and double any quote inside it.",
     "A cell starting with <code>=</code>, <code>+</code>, <code>-</code> or <code>@</code> runs as a formula (OWASP calls this CSV injection). Prefix such text with an apostrophe.",
     "<code>@GetMapping(value = \"/export\", produces = \"text/csv\")</code> sets the content type."],
    "challenge/CsvExportChallengeTest.java", ["challenge/solution/CsvExport.java", "challenge/solution/RegistrationStore.java", "challenge/solution/RegistrationController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Seat limits</h2>
<p>The summit has 500 seats. Where would you store "seats left", and how would you stop two registrations for the last 3 seats from both succeeding? Which status code would you return when it is full, and what should the app show? (Station 082, movie seat holds, builds this with a real concurrency test.)</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: without <code>@Valid</code>, garbage is saved.</li>
<li>Write <code>RegistrationRequest</code> with one annotation per rule, and trimming in its constructor.</li>
<li>Add <code>@Valid</code> and the <code>errors</code> map; check the event; save; answer <code>201</code> with <code>Location</code>.</li>
<li>Add <code>GET</code> by id, scoped to its event.</li>
<li>Test each boundary, and the odd inputs: fractions, extra fields, wrong content type.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Bean Validation annotations + <code>@Valid</code>", "Rules are declarative and reused by every endpoint that takes this record.", '<span class="pill ok">Chosen</span>'],
    ["<code>if</code> checks in the controller", "Works, but rules spread across methods and drift apart.", '<span class="pill warn">Possible</span>'],
    ["Trust the client's checks", "Garbage in the export; the trap.", '<span class="pill bad">Wrong</span>'],
    ["Return <code>200</code> for a create", "The client cannot tell \"made something\" from \"did something\"; no <code>Location</code>.", '<span class="pill bad">Wrong</span>'],
    ["Return the first error only", "The user fixes one field, submits, and meets the next error.", '<span class="pill bad">Wrong</span>'],
    ["Let the client send <code>id</code> and <code>registeredAt</code>", "Clients could overwrite or back-date records.", '<span class="pill bad">Wrong</span>']]) + """
<h2>Database design</h2>
<p>None in this station: registrations live in a <code>ConcurrentHashMap</code>. When a database arrives, the same rules become column constraints too (<code>NOT NULL</code>, <code>CHECK (tickets BETWEEN 1 AND 10)</code>), so a script that skips the API still cannot store garbage.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Security</dt><dd>Every field has a maximum length, so nobody can store a 10 MB name. Names are stored as text and returned as JSON; showing them in HTML safely is station 007's topic, and exporting them safely is Challenge 2. Emails and phones are personal data: do not log them in full.</dd>
<dt>Reliability</dt><dd>Memory storage loses everything on restart. Acceptable for a lesson, never for real registrations.</dd>
<dt>Maintainability</dt><dd>Demo limits (10 tickets, the phone pattern) are constants in one record; changing them is one line, and the tests show what else depends on them.</dd>
<dt>Privacy</dt><dd>Collect only what the event needs. Phone is optional for that reason.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why validate on the server if the form already validates?", "Anyone can send a request without your form: curl, a script, an old app version. Client checks are for user experience; server checks are for correctness."),
    ("What does @Valid do, and what happens when a rule fails?", "It makes Spring run the Bean Validation rules on the argument before calling your method. A failure throws MethodArgumentNotValidException, which becomes a 400; your method never runs."),
    ("Why 201 and not 200 for a create?", "201 says a new resource was created, and the Location header says where it lives. Clients can read it back without guessing the URL."),
    ("Integer or int for a required number in a request?", "Integer. A missing field becomes null, which @NotNull reports. An int would silently become 0, and the error message would be about the minimum instead of the missing value."),
    ("A client sends 2.5 for an integer field. What happens?", "By default Jackson truncates it to 2 and nobody notices. Turn off accept-float-as-int so it becomes a 400."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can predict which tests fail without <code>@Valid</code>."],
    ["Robustness", "Every rule has a boundary test.", "You found an odd input the tests do not cover, and added it."],
    ["Design", "<code>201</code> + <code>Location</code>; all errors in one answer.", "You can explain why the client must not choose the id."],
    ["Explanation", "You can say what <code>@Valid</code> does.", "You can explain the 2.5-tickets bug and its fix."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on your own code instead:</p>
<ul class="rules">
<li>Does every <code>@RequestBody</code> that has rules also have <code>@Valid</code>?</li>
<li>Does every text field have a maximum length?</li>
<li>Can a client set a field only the server should set?</li>
<li>Does a create return <code>201</code> with <code>Location</code>?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
