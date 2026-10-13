"""Station 006 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 6,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · Spring Security 7 · ProblemDetail (RFC 9457) · MockMvc",
    "simulation": "The IFSC directory is a fixed list of four branches inside the app, and beneficiaries live in memory. No bank is called and no money moves. Sign-in is HTTP Basic with three demo users.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tijori/beneficiaries/"
T = "src/test/java/com/tijori/beneficiaries/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Beneficiary", "A person or account you have saved so you can send money to them later.", "A saved contact in your phone.", "Ravi's HDFC account, saved by Asha."),
    ("IFSC", "An 11-character code that identifies one bank branch in India.", "A PIN code, but for a bank branch.", "<code>HDFC0001234</code>"),
    ("Exception", "Java's way to stop normal work and report that something went wrong.", "Pulling the emergency chain on a train.", "<code>UnknownIfsc</code>, <code>BeneficiaryNotFound</code>"),
    ("<code>@RestControllerAdvice</code>", "One class that turns exceptions from every controller into HTTP responses.", "A single complaints desk for the whole bank.", "<code>ApiErrors</code>"),
    ("Problem details (RFC 9457)", "A standard JSON shape for errors: <code>type</code>, <code>title</code>, <code>status</code>, <code>detail</code>, <code>instance</code>.", "One standard complaint form, whatever went wrong.", "Every error in this API."),
    ("Problem type", "A fixed URI naming the kind of error, so code can branch on it.", "A form's category box: \"lost card\" or \"wrong charge\".", "<code>…/problems/unknown-ifsc</code>"),
    ("Stack trace", "The list of methods that were running when an exception happened, with class names and line numbers.", "A map of the building with every room labelled.", "Goes to the log only, never to a client."),
    ("401 / 403", "401: we do not know who you are. 403: we know, and you may not do this.", "No ID card at the gate / an ID card without access to this floor.", "No credentials / a viewer adding a beneficiary."),
]
STORY = [
    ("Asha adds Ravi as a beneficiary", "She types Ravi's account number and IFSC into the Tijori app and taps Save."),
    ("Something fails, but what?", "One endpoint returns <code>{\"error\":\"…\"}</code>, another an HTML page, another a Java stack trace that names the database server. The app cannot tell \"wrong IFSC\" (Asha should fix it) from \"server down\" (try later)."),
    ("The fix", "Every error leaves the API in one shape, with a status code and a type that say what to do next, and without any internal detail an attacker could use."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">An error message has two readers: the app, which must decide what to do, and anyone probing the API, who looks for clues. Write for the first and give nothing to the second.</p>

<h2>What are we building?</h2>
<p>A small beneficiary API (add one, read one) where every failure, from bad input to a sign-in problem to a bug, comes back as an RFC 9457 problem with its own <code>type</code>. Unexpected errors return only an <code>errorId</code>; the details go to the log.</p>

<h2>An everyday analogy</h2>
<p>A bank branch with one complaints desk. Whatever goes wrong, you get the same printed form: a category ("wrong IFSC", "system down, come back in an hour"), a short explanation, and a reference number. The clerk does not hand you the internal incident report with server names and staff notes; that stays in the back office, filed under your reference number.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Code throws a business exception</strong> that says what happened: <code>UnknownIfsc</code>, <code>DuplicateBeneficiary</code>, <code>IfscDirectoryUnavailable</code>.</li>
<li><strong>One advice class catches them all</strong> and picks a status and a problem type for each.</li>
<li><strong>Anything unexpected</strong> becomes a <code>500</code> with a random <code>errorId</code>; the full exception is logged under that id.</li>
<li><strong>Sign-in errors</strong> (401, 403) happen before any controller, so the security layer writes the same shape itself.</li>
</ol>

<details class="qa check"><summary>Check yourself: Ravi asks for a beneficiary id that belongs to Asha. Why does he get 404 and not 403?</summary><p>403 would tell Ravi "this id exists, it is just not yours", which confirms that the id is real. 404 gives him exactly the same answer as for an id that does not exist, so he learns nothing about other customers.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>A simulation.</strong> The IFSC directory is four branches in a list; nothing calls a bank. No money moves.</li>
<li><strong>Demo sign-in.</strong> HTTP Basic with three in-memory users (passwords stored as bcrypt hashes). Real banking apps use stronger sign-in, covered in later stations.</li>
<li><strong>No database.</strong> Beneficiaries are lost on restart.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tijori</strong> (a fictional digital bank) has a beneficiary API that grew one endpoint at a time. Each one fails differently: a string, a map, Spring's default HTML page, or the exception message with a stack trace. The app team cannot tell "wrong IFSC" (ask the customer to check) from "IFSC service down" (ask them to retry), so every failure shows "Something went wrong". A security review found that one error response named the internal database host and the SQL being run.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> any error from any endpoint, <b>then</b> the body is <code>application/problem+json</code> with <code>type</code>, <code>title</code>, <code>status</code>, <code>detail</code> and <code>instance</code>, and never an exception name or stack trace.</li>
<li><b>Given</b> invalid fields, <b>then</b> <code>400</code> type <code>invalid-request</code> with one message per field; no message repeats what was sent.</li>
<li><b>Given</b> a well-formed IFSC that no branch has, <b>then</b> <code>400</code> type <code>unknown-ifsc</code>. <b>Given</b> the IFSC directory is down, <b>then</b> <code>503</code> type <code>ifsc-directory-unavailable</code> with <code>Retry-After</code>.</li>
<li><b>Given</b> the same account and IFSC twice, <b>then</b> <code>409</code> naming the existing beneficiary.</li>
<li><b>Given</b> an unexpected failure, <b>then</b> <code>500</code> type <code>internal-error</code> with an <code>errorId</code>, and the log holds the exception under that id.</li>
<li><b>Given</b> no or wrong credentials, <b>then</b> <code>401</code> (same body for both). <b>Given</b> a viewer adding, <b>then</b> <code>403</code>. <b>Given</b> another customer's id, <b>then</b> <code>404</code>, identical to an unknown id.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>One <code>@RestControllerAdvice</code> maps every exception. Controllers have no <code>try</code>/<code>catch</code>.</li>
<li>Each kind of error has a stable type URI under <code>https://tijori.example/problems/</code>.</li>
<li>Error text states the rule, never the input: no reflected scripts, SQL or IDs from the request.</li>
<li>The owner of a beneficiary is the signed-in customer, never a body field.</li>
<li>Responses show only the last 4 digits of an account number.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Write business exceptions and map them in one <code>@RestControllerAdvice</code>.</li>
<li>Build RFC 9457 <code>ProblemDetail</code> responses with types an app can branch on.</li>
<li>Choose 400, 404, 409 or 503 by what the client should do next.</li>
<li>Log the details, return only an id: never leak stack traces or messages.</li>
<li>Give 401 and 403 from Spring Security the same shape.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Who", "Purpose"], [
    ["<code>POST</code>", "<code>/beneficiaries</code>", "Customers (asha, ravi)", "Add a beneficiary"],
    ["<code>GET</code>", "<code>/beneficiaries/{id}</code>", "Any signed-in user; only the owner's are found", "Read one beneficiary"]]) + """
<h2>Request body</h2>
""" + table(["Field", "Rule"], [
    ["<code>name</code>", "2–100 letters, spaces, dots, apostrophes or hyphens."],
    ["<code>accountNumber</code>", "9 to 18 digits. Responses show only the last 4."],
    ["<code>ifsc</code>", "11 characters: 4 letters, <code>0</code>, 6 letters or digits. Lower case is accepted and stored upper case."]]) + """
<h2>Error catalogue</h2>
<p>Every error has the same fields. The <code>type</code> tells the app what to do.</p>
""" + table(["Status", "Type (after <code>…/problems/</code>)", "When", "What the app should do"], [
    ['<span class="pill warn">400</span>', "<code>invalid-request</code>", "Fields break a rule (with <code>errors</code>), or a path value has the wrong format", "Show the messages; let the customer fix the fields"],
    ['<span class="pill warn">400</span>', "<code>unknown-ifsc</code>", "Well-formed IFSC that no branch has", "Ask the customer to check the IFSC"],
    ['<span class="pill warn">401</span>', "<code>unauthenticated</code>", "No or wrong credentials", "Sign in again"],
    ['<span class="pill warn">403</span>', "<code>forbidden</code>", "Signed in, but this account cannot do this", "Hide the action for this user"],
    ['<span class="pill warn">404</span>', "<code>beneficiary-not-found</code>", "No such id on your account (including another customer's)", "Refresh the list"],
    ['<span class="pill warn">409</span>', "<code>duplicate-beneficiary</code>", "This account is already saved; <code>existingBeneficiaryId</code> names it", "Open the existing one"],
    ['<span class="pill bad">500</span>', "<code>internal-error</code>", "A bug or unexpected failure; only <code>errorId</code> is given", "Apologise; show the errorId for support"],
    ['<span class="pill bad">503</span>', "<code>ifsc-directory-unavailable</code>", "The IFSC check could not run; nothing was saved", "Retry after <code>Retry-After</code> seconds"]]) + """
<p class="note">Errors Spring raises itself (broken JSON, an unknown path, a wrong method) use the same fields with <code>type: about:blank</code>, which RFC 9457 defines as "the HTTP status says it all".</p>
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out. The <code>Authorization</code> header carries this station's demo passwords.</p>
""" + examples([
    ("01-add", "Case 1: Asha adds Ravi", "<b>Why:</b> valid fields, a known IFSC, not a duplicate: <code>201</code>. Only the last 4 digits of the account come back. The headers Spring Security adds (<code>Cache-Control</code>, <code>X-Frame-Options</code> and others) are visible here."),
    ("02-invalid", "Case 2: a script tag as the name", "<b>Why:</b> three fields break their rules: three messages. None repeats the input, so the <code>&lt;script&gt;</code> never comes back."),
    ("03-unknown-ifsc", "Case 3: a well-formed IFSC that no branch has", "<b>Why:</b> the shape is right, the branch does not exist: <code>400</code> with its own type, so the app can say \"check the IFSC\"."),
    ("04-duplicate", "Case 4: the same account again", "<b>Why:</b> <code>409</code>, and the body names the beneficiary that already exists."),
    ("05-other-customer", "Case 5: Ravi asks for Asha's beneficiary", "<b>Why:</b> <code>404</code>, word for word what an unknown id gets. Ravi cannot tell that the id exists."),
    ("06-no-credentials", "Case 6: no credentials", "<b>Why:</b> <code>401</code> from Spring Security's filter, in the same shape, with a <code>WWW-Authenticate</code> challenge."),
    ("07-viewer-adds", "Case 7: Meera, a viewer, tries to add", "<b>Why:</b> she is signed in but may only read: <code>403</code>."),
    ("08-sql-in-path", "Case 8: SQL where an id belongs", "<b>Why:</b> <code>400</code> naming the parameter, not its value. Spring's default message would have repeated the SQL (see Edge cases)."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What the API does", "Proved by"], [
    ["Valid beneficiary", "<code>201</code>, masked account, readable <code>Location</code>", "<code>addingIs201WithLocationAndOnlyTheLast4DigitsOfTheAccount</code>, <code>theOwnerCanReadItBack</code>"],
    ["Lower-case IFSC", "Accepted, stored upper case", "<code>aLowerCaseIfscIsAccepted</code>"],
    ["Fields break rules", "<code>400</code> <code>invalid-request</code>, one message each", "<code>invalidFieldsAre400WithOneMessagePerField</code>"],
    ["Unknown IFSC", "<code>400</code> <code>unknown-ifsc</code>", "<code>aWellFormedButUnknownIfscIs400WithItsOwnType</code>"],
    ["IFSC directory down", "<code>503</code> + <code>Retry-After</code>; internal host not shown", "<code>anIfscDirectoryOutageIs503WithRetryAfterNotA400</code>"],
    ["Duplicate", "<code>409</code> with <code>existingBeneficiaryId</code>", "<code>theSameAccountTwiceIs409NamingTheExistingBeneficiary</code>"],
    ["Unknown id", "<code>404</code>", "<code>anUnknownIdIs404</code>"],
    ["Broken JSON, unknown path, wrong method, wrong content type", "Same problem shape", "<code>brokenJsonIs400InTheSameShape</code>, <code>unknownPathsAndWrongMethodsAreProblemsToo</code>"],
    ["Any error at all", "No exception names, no stack trace", "<code>noErrorEverCarriesAnExceptionNameOrAStackTrace</code>"],
    ["Database failure inside the app", "<code>500</code> with <code>errorId</code> only", "<code>theRealApiAnswersWithAProblemAndAnErrorIdOnly</code>"],
    ["No credentials; wrong password", "<code>401</code>, identical bodies", "<code>noCredentialsIs401ProblemWithAChallenge</code>, <code>aWrongPasswordGetsTheSameAnswerAsNoCredentials</code>"],
    ["Viewer adds", "<code>403</code>", "<code>aViewerCannotAddBeneficiaries403</code>"],
    ["Another customer's beneficiary", "<code>404</code>, identical to unknown", "<code>anotherCustomersBeneficiaryLooksExactlyLikeOneThatDoesNotExist</code>"],
    ["<code>owner</code> field in the body", "Ignored; the owner is the signed-in user", "<code>anOwnerFieldInTheBodyIsIgnored</code>"],
    ["Script tag in the name", "<code>400</code>; never echoed", "<code>aScriptInTheNameIsRejectedAndNeverEchoed</code>"],
    ["SQL in the path", "<code>400</code>; never echoed", "<code>sqlInThePathIs400AndIsNotEchoed</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Returning exception messages and stack traces, leaking internals to attackers.</p>
<p>"Show the real error, it helps debugging" is how it starts. The first test makes the store fail with a realistic message and calls a "before" controller whose handler returns <code>e.getMessage()</code> and the stack trace: the response contains the database host, the SQL and the code's class names. The second test causes the same failure in the real API: a problem with an <code>errorId</code>, and none of those strings.</p>
</div>
""" + code(read(T + "LeakyErrorsTrapTest.java"), "java") + """
<h3>A leak the tests found in Spring's defaults</h3>
<p>While building this station, <code>sqlInThePathIs400AndIsNotEchoed</code> failed. For <code>GET /beneficiaries/1' OR '1'='1</code>, Spring's built-in handler answered with <code>"detail": "Failed to convert 'id' with value: '1' OR '1'='1'"</code>, repeating the attacker's text back. <code>ApiErrors</code> now overrides <code>handleTypeMismatch</code> to name the parameter only. The test was red before the override and green after. Framework defaults are a good start, not a guarantee.</p>
"""

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SecurityConfig.java", dwn("Requires sign-in for everything, lets only customers add, and points 401 and 403 at <code>ProblemResponses</code>.",
        "Security runs as servlet filters before any controller; this is where its errors are shaped.",
        "Spring Security's default 401 has an empty body and its 403 another format: two more shapes for the app to handle.",
        "<ul><li>CSRF protection is off because nothing uses cookies or sessions: credentials travel with every request.</li><li>Passwords are stored as bcrypt hashes even in this demo.</li></ul>")),
    (J + "ProblemResponses.java", dwn("Writes the 401 and 403 problem bodies by hand.",
        "<code>@RestControllerAdvice</code> only sees exceptions from controllers; these happen earlier.",
        "Sign-in errors would not match the rest.")),
    (J + "BeneficiaryController.java", dwn("Two endpoints. No <code>try</code>/<code>catch</code>: failures are exceptions.",
        "Error handling in one place means one shape.",
        "No API.",
        "<ul><li>The owner comes from <code>Principal</code>, the signed-in user, never from the body.</li></ul>")),
    (J + "BeneficiaryRequest.java", dwn("The body's rules. Messages state the rule, not the value.", "Rules apply to every client.", "Anything is stored.")),
    (J + "BeneficiaryService.java", dwn("The business rules: check the IFSC, refuse duplicates, save; find only the owner's beneficiaries.",
        "It throws exceptions that say what happened in business terms, and knows nothing about HTTP.",
        "Status codes would be chosen in many places.",
        "<ul><li>An exception from the directory becomes <code>IfscDirectoryUnavailable</code> (503); an empty answer becomes <code>UnknownIfsc</code> (400). Mixing these up is one of the Review findings.</li></ul>")),
    (J + "Exceptions.java", dwn("The four business exceptions.", "Each names one situation the client can act on.", "Everything would be a generic exception and a 500.")),
    (J + "ApiErrors.java", dwn("Maps every exception to a status and a problem type; logs unexpected ones with an <code>errorId</code>.",
        "One place decides the error contract for the whole API.",
        "Each controller invents its own error format (the business problem).",
        "<ul><li><code>unexpected(Exception)</code> is the safety net: it is chosen only when no more specific handler matches.</li><li><code>handleTypeMismatch</code> stops Spring's default message from echoing input.</li></ul>")),
    (J + "IfscDirectory.java", "<p>Simulated IFSC lookup: four branches in a map.</p>"),
    (J + "BeneficiaryStore.java", "<p>Beneficiaries in a <code>ConcurrentHashMap</code>.</p>"),
    (J + "Beneficiary.java", "<p>The stored record, with <code>view()</code> to mask the account number.</p>"),
    (J + "BeneficiaryView.java", "<p>The response body.</p>"),
    ("src/main/resources/application.yaml", "<p>States Spring Boot's safe defaults for error pages explicitly: no stack traces, no messages.</p>"),
    ("pom.xml", "<p>Adds <code>spring-boot-starter-security</code>, and <code>spring-boot-starter-security-test</code> for <code>httpBasic(...)</code> in tests.</p>"),
]
tree = """stations/006-one-error-shape-for-a-banking-api/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tijori/beneficiaries/
│   ├── SecurityConfig.java        ├── ProblemResponses.java
│   ├── BeneficiaryController.java ├── BeneficiaryRequest.java
│   ├── BeneficiaryService.java    ├── Exceptions.java
│   ├── ApiErrors.java             ├── IfscDirectory.java
│   ├── BeneficiaryStore.java      ├── Beneficiary.java, BeneficiaryView.java
│   └── BeneficiariesApplication.java
├── src/test/java/com/tijori/beneficiaries/   (see Tests)
├── review/                   the flawed version (see Review)
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
<p>Demo users: <code>asha</code> / <code>asha-demo-pass</code> and <code>ravi</code> / <code>ravi-demo-pass</code> (customers), <code>meera</code> / <code>meera-demo-pass</code> (viewer). The body is in <code>docs/beneficiary.json</code>.</p>
""" + code("""# Add: expect 201 and a masked account number
curl -i -u asha:asha-demo-pass -X POST http://localhost:8080/beneficiaries -H "Content-Type: application/json" -d "@docs/beneficiary.json"

# The same again: expect 409 duplicate-beneficiary
curl -i -u asha:asha-demo-pass -X POST http://localhost:8080/beneficiaries -H "Content-Type: application/json" -d "@docs/beneficiary.json"

# As a viewer: expect 403 forbidden
curl -i -u meera:meera-demo-pass -X POST http://localhost:8080/beneficiaries -H "Content-Type: application/json" -d "@docs/beneficiary.json"

# Without credentials: expect 401 unauthenticated
curl -i http://localhost:8080/beneficiaries/00000000-0000-0000-0000-000000000000""", "bash") + """
<p>Then stop the app and look at its console after the <code>500</code> test: the log line holds the <code>errorId</code> and the full exception, which the response did not.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>401</code> for every request", "Missing or mistyped <code>-u user:password</code>.", "Use the demo users above."],
    ["<code>403</code> on <code>POST</code>", "Signed in as <code>meera</code>, a viewer.", "Use <code>asha</code> or <code>ravi</code>."],
    ["<code>release version 25 not supported</code>", "Maven is using an older JDK.", "Point <code>JAVA_HOME</code> at JDK 25, or add <code>-Djava.version=21</code>."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels: security filters first, then the controller, the service, and the error mapping on the way out.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "Required tests come from the station's types. The validator fails a station that is missing any of them.") + """
<h2>Required tests for this station</h2>
<p>Station type: <span class="chip">Security</span></p>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>BeneficiaryContractTest</code> ({cnt('BeneficiaryContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>LeakyErrorsTrapTest</code> ({cnt('LeakyErrorsTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, one user reaching another's data, malicious input", f"<code>BeneficiarySecurityTest</code> ({cnt('BeneficiarySecurityTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Spring Security 7. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "LeakyErrorsTrapTest.java", "<p>Written first: the leaky handler hands out host, SQL and class names; the real API hands out an <code>errorId</code>.</p>"),
    (T + "BeneficiaryContractTest.java", "<p>Every status code and problem type, the 503 with a simulated outage, and a sweep that no error carries an exception name.</p>"),
    (T + "BeneficiarySecurityTest.java", "<p>401 (and the same body for a wrong password), 403, cross-customer 404, the owner field ignored, script and SQL never echoed.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app with its security filters, through MockMvc with real Basic headers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tijori/beneficiaries/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=DeleteBeneficiaryChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Delete a beneficiary", "Beginner-friendly", 30,
    "Add <code>DELETE /beneficiaries/{id}</code>: <code>204</code> for the owner; <code>404</code> (in the usual shape) for another customer's beneficiary; <code>403</code> for a viewer.",
    "all three tests in <code>DeleteBeneficiaryChallengeTest</code> pass, and the station's tests still pass.",
    ["Reuse <code>get(owner, id)</code> in the service, so delete follows exactly the same ownership rule.",
     "The <code>403</code> belongs in <code>SecurityConfig</code>, next to the rule for <code>POST</code>.",
     "No new error handling should be needed: the existing exceptions already map to the right problems."],
    "challenge/DeleteBeneficiaryChallengeTest.java", ["challenge/solution/BeneficiaryController.java", "challenge/solution/BeneficiaryService.java", "challenge/solution/BeneficiaryStore.java", "challenge/solution/SecurityConfig.java"]) + challenge(2, "A request id in every error", "Go deeper", 45,
    "Support asks customers for an id they can search the logs with. Read <code>X-Request-Id</code> from the request (keep it only if it is 8–64 letters, digits or hyphens; otherwise make a UUID), return it as a response header, and add it as <code>requestId</code> to every problem, including 401s.",
    "all three tests in <code>RequestIdChallengeTest</code> pass.",
    ["A servlet filter with <code>@Order(Ordered.HIGHEST_PRECEDENCE)</code> runs before Spring Security's filters.",
     "Never echo an id you have not checked: that is the same leak as the station's trap.",
     "Problems are built in three places: <code>ApiErrors</code> handlers, Spring's own handlers (<code>createResponseEntity</code>), and <code>ProblemResponses</code>.",
     "<code>MDC.put(\"requestId\", id)</code> puts it on every log line of the request."],
    "challenge/RequestIdChallengeTest.java", ["challenge/solution/RequestIdFilter.java", "challenge/solution/ApiErrors.java", "challenge/solution/ProblemResponses.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Error messages in Hindi and Tamil</h2>
<p>Tijori's app is used in five languages. Should the API translate <code>title</code> and <code>detail</code> (using <code>Accept-Language</code>), or should the app translate based on <code>type</code>? What happens to log searches and support tickets in each case? Which fields must never be translated?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: a leaky handler shows host, SQL and class names.</li>
<li>List every error the client can act on; give each an exception, a status and a type.</li>
<li>Write one <code>@RestControllerAdvice</code>; add a catch-all that logs with an <code>errorId</code>.</li>
<li>Make Spring Security's 401 and 403 write the same shape.</li>
<li>Test that nothing is echoed: scripts, SQL, internal hostnames.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Business exceptions + one advice + <code>ProblemDetail</code>", "A small exception class per situation.", '<span class="pill ok">Chosen</span>'],
    ["Return <code>e.getMessage()</code> and the stack trace", "Hands attackers internal hosts, SQL and code layout.", '<span class="pill bad">Wrong</span>'],
    ["<code>try</code>/<code>catch</code> in every controller", "Each one drifts into its own format.", '<span class="pill bad">Wrong</span>'],
    ["<code>ErrorResponseException</code> thrown directly from the service", "Less code (stations 001–005 did this), but the service then knows HTTP.", '<span class="pill warn">Fine for small APIs</span>'],
    ["A custom error JSON instead of RFC 9457", "Works, but every client and tool must learn yours.", '<span class="pill warn">Possible</span>'],
    ["403 for another customer's beneficiary", "Confirms the id exists.", '<span class="pill bad">Leaks</span>']]) + """
<h2>Database design</h2>
<p>None in this station. When a database arrives, its exceptions (constraint violations, timeouts) get their own mapping: a unique-constraint violation becomes the same <code>409</code>, a timeout a <code>503</code>, and anything else the <code>500</code> with an <code>errorId</code>.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Security</dt><dd>No stack traces, no exception messages, no echoed input, no "it exists but is not yours". Account numbers are masked. Demo passwords live in code only because this is a demo. One field does repeat the request: <code>instance</code> is the path that was called, URL-encoded (case 8 shows <code>%20</code> for spaces). It is JSON data for the caller's own request; an app that shows it must still escape it as text.</dd>
<dt>Operations</dt><dd>The <code>errorId</code> joins a customer's complaint to the exact log line. Count <code>500</code>s by <code>type</code>; alert when <code>internal-error</code> rises, because each one is a bug.</dd>
<dt>Reliability</dt><dd><code>503</code> with <code>Retry-After</code> tells well-behaved clients to wait instead of hammering a struggling dependency.</dd>
<dt>Maintainability</dt><dd>A new error is a new exception and one handler method. The error catalogue in the API tab is the contract; changing a <code>type</code> breaks clients.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why not return the exception message to the client?", "It is written for developers and can contain anything: SQL, hostnames, file paths, customer data. Log it with an id, and return only the id and a safe description."),
    ("What is RFC 9457 and why use it?", "A standard JSON format for HTTP API errors (it replaced RFC 7807): type, title, status, detail, instance, plus your own fields. Clients and tools already understand it, and Spring supports it with ProblemDetail."),
    ("400, 404, 409 or 503: how do you choose?", "By what the client should do next. 400: fix the request. 404: the thing is not there (for you). 409: it clashes with the current state (already exists). 503: nothing is wrong with your request, try later."),
    ("Why does @RestControllerAdvice not handle 401 and 403?", "Spring Security rejects those requests in servlet filters, before Spring MVC and its controllers run. You shape them with an AuthenticationEntryPoint and an AccessDeniedHandler."),
    ("Another customer's resource: 403 or 404?", "404, identical to a missing one. 403 confirms the id exists, which helps an attacker enumerate valid ids."),
    ("Framework default error handling is safe, right?", "Mostly. In this station Spring's default type-mismatch message echoed the request value back. Test your error responses for echoed input; do not assume."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can predict which tests the flawed version fails, and why."],
    ["Security", "Nothing internal or echoed in any error.", "You found another place where input could be echoed, and tested it."],
    ["Design", "One advice; a type per error the client can act on.", "You can defend 404 over 403 for other customers' data."],
    ["Explanation", "You can walk an exception from the service to the JSON.", "You can explain why 401 is shaped somewhere else."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("The catch-all handler returns <code>e.getMessage()</code>", "\"Helpful for debugging\": the database host and the SQL from the store's exception go straight to the client.", "<code>theRealApiAnswersWithAProblemAndAnErrorIdOnly</code>: no <code>errorId</code>, because the <code>detail</code> is the store's message, database host and SQL included."),
    ("Validation messages repeat the rejected value", "<code>'&lt;script&gt;…' must be…</code> sends the attacker's script back. If any page shows that message as HTML, it runs.", "<code>aScriptInTheNameIsRejectedAndNeverEchoed</code> and <code>invalidFieldsAre400WithOneMessagePerField</code>."),
    ("Directory outage mapped to the same 400 as an unknown IFSC", "\"Both are IFSC problems.\" The customer is told to fix a correct IFSC while the service is down, and no client retries.", "<code>anIfscDirectoryOutageIs503WithRetryAfterNotA400</code>: got 400."),
    ("403 for another customer's beneficiary", "\"Clear errors\": but it confirms the id exists, and the detail says so in words.", "<code>anotherCustomersBeneficiaryLooksExactlyLikeOneThatDoesNotExist</code> and <code>anOwnerFieldInTheBodyIsIgnored</code>: got 403."),
    ("No <code>handleTypeMismatch</code> override", "Spring's default message for a bad path value repeats the value: SQL comes back in the response.", "<code>sqlInThePathIs400AndIsNotEchoed</code>."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate "cleaned up" error handling. Every error is a <code>ProblemDetail</code> now, and the happy-path tests pass. Read both files and list every problem before opening the findings.</p>
<p class="path">review/ApiErrors.java</p>
""" + code(read("review/ApiErrors.java"), "java") + """
<p class="path">review/BeneficiaryService.java</p>
""" + code(read("review/BeneficiaryService.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the two flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">Every flaw looks like a reasonable choice in isolation ("helpful", "simple", "clear"). The security tests catch them because they ask what an attacker or a confused client would see.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
