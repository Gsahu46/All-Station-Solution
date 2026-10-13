"""Station 001 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 1,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · MockMvc",
    "simulation": "Store statuses are a fixed list inside the app. Nothing reads a real store-operations system.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/basketo/stores/"
T = "src/test/java/com/basketo/stores/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Endpoint", "One address the app can call, such as <code>GET /stores/{id}/status</code>.", "A counter in a bank: each one does one job.", "The only endpoint in this station."),
    ("Path variable", "A part of the URL that changes from call to call.", "The flat number in an address.", "<code>BLR-KOR-01</code> in <code>/stores/BLR-KOR-01/status</code>."),
    ("Status code", "A three-digit number that says how the request went, before you read the body.", "A green or red light at a gate.", "<code>200</code> found, <code>404</code> no such store, <code>400</code> the id is malformed."),
    ("JSON", "Text the app can read as named fields.", "A form with labelled boxes.", "<code>{\"open\":false,\"reason\":\"Closed for stock-taking\"}</code>"),
    ("Record", "A Java class that just carries data; Spring turns it into JSON.", "A printed receipt: fixed fields, no surprises.", "<code>StoreStatus</code>."),
    ("Problem body", "A standard JSON shape for errors (RFC 9457): <code>type</code>, <code>title</code>, <code>status</code>, <code>detail</code>, <code>instance</code>.", "A rejection slip that says which rule you broke.", "The <code>404</code> and <code>400</code> answers."),
    ("MockMvc", "A test tool that sends requests to your controllers without starting a real server.", "A flight simulator for the API.", "Every test in this station."),
]
STORY = [
    ("Priya opens the app", "She lives near the Indiranagar dark store and the app says <em>Delivering in 10 minutes</em>."),
    ("The store is closed", "Staff are counting stock. Her order is accepted, then cancelled 15 minutes later."),
    ("The fix", "Before promising anything, the app asks the server: is this store open? The server answers clearly: open with a promise, closed with a reason, or \"no such store\"."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">An API that answers vaguely is as bad as no API: the app guesses, and the guess shows up as a broken promise to a customer.</p>

<h2>What are we building?</h2>
<p>One read-only endpoint, <code>GET /stores/{storeId}/status</code>. It says whether a dark store is open, why it is closed, and how fast it can deliver. For a store that does not exist it says so, with <code>404</code>.</p>

<h2>An everyday analogy</h2>
<p>You call a shop. Three answers are useful: "Yes, we're open, come in 10 minutes", "We're closed today for stock-taking", or "Wrong number, there's no shop here." The useless answer is silence: the line picks up and nobody speaks. That silence is what an empty <code>200</code> response is.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>The app sends</strong> <code>GET /stores/BLR-IND-01/status</code>.</li>
<li><strong>The server checks the id's shape.</strong> If it does not look like <code>BLR-KOR-01</code>, it answers <code>400</code>.</li>
<li><strong>The server looks the store up.</strong> Not found: <code>404</code> with a problem body.</li>
<li><strong>Found:</strong> <code>200</code> with the status. A closed store has a reason and no delivery promise.</li>
</ol>

<details class="qa check"><summary>Check yourself: Indiranagar is closed for stock-taking. Should the API answer 404?</summary><p>No. The store exists; being closed is its current state. The answer is <code>200</code> with <code>"open": false</code> and a reason. <code>404</code> means "there is no such store", which is a different fact the app handles differently (for example, by asking the customer to pick a store again).</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>Not connected to real stores.</strong> Four stores are fixed in the code. Reading live status from a database comes in later stations.</li>
<li><strong>No opening hours or time zones.</strong> A store is open or closed because the list says so.</li>
<li><strong>No login.</strong> Store status is public information here, so no authentication is needed.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Basketo</strong> (a fictional quick-commerce app) delivers groceries from small "dark stores" in about 10 minutes. The home screen shows a delivery promise for the customer's nearest store. Today the promise is shown even when that store is closed for stock-taking, so orders are accepted and then cancelled. Customers lose trust; support handles the complaints.</p>
<p>The app's developers say they call the status API, but for a store id that does not exist it answers <code>200</code> with an empty body, which their code reads as "no problem", and nothing stops it from showing the default promise.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> an open store, <b>when</b> the app asks for its status, <b>then</b> the API returns <code>200</code> with <code>open: true</code> and a delivery promise in minutes.</li>
<li><b>Given</b> a closed store, <b>then</b> <code>200</code> with <code>open: false</code>, a reason, and no delivery promise.</li>
<li><b>Given</b> a well-formed id that matches no store, <b>then</b> <code>404</code> with a problem body.</li>
<li><b>Given</b> an id that is not shaped like <code>BLR-KOR-01</code>, <b>then</b> <code>400</code> with a problem body.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Store ids are three capital letters, a dash, three capital letters, a dash, two digits.</li>
<li>Every error is an RFC 9457 <code>application/problem+json</code> body.</li>
<li>A closed store has <code>deliveryPromiseMinutes: null</code>, never a number.</li>
<li>The endpoint only reads; other methods get <code>405</code>.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Read a Maven project: <code>pom.xml</code>, <code>src/main</code>, <code>src/test</code>, the wrapper.</li>
<li>Write a <code>@RestController</code> with <code>@GetMapping</code> and <code>@PathVariable</code>.</li>
<li>Return a record as JSON, and choose <code>200</code>, <code>400</code> or <code>404</code> with <code>ResponseEntity</code>.</li>
<li>Explain the difference between "exists but closed" and "does not exist".</li>
<li>Write your first MockMvc test.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [["<code>GET</code>", "<code>/stores/{storeId}/status</code>", "Is this dark store open, and how fast can it deliver?"]]) + """
<h2>Response fields</h2>
""" + table(["Field", "Type", "Meaning"], [
    ["<code>storeId</code>", "string", "The store's id, e.g. <code>BLR-KOR-01</code>."],
    ["<code>name</code>", "string", "Area name for display."],
    ["<code>open</code>", "boolean", "Whether the store takes orders now."],
    ["<code>reason</code>", "string or null", "Why it is closed; <code>null</code> when open."],
    ["<code>deliveryPromiseMinutes</code>", "integer or null", "Minutes to promise; <code>null</code> when closed."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When", "Body"], [
    ['<span class="pill ok">200</span>', "The store exists (open or closed)", "The status"],
    ['<span class="pill warn">400</span>', "The id is not shaped like <code>BLR-KOR-01</code>", "Problem: <em>Invalid store id</em>"],
    ['<span class="pill warn">404</span>', "No store has this id", "Problem: <em>Store not found</em>"],
    ['<span class="pill warn">405</span>', "Any method other than <code>GET</code>", "Problem"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-open", "Case 1: an open store", "<b>Why:</b> the store exists and is open, so <code>200</code> with a 10-minute promise."),
    ("02-closed", "Case 2: a closed store", "<b>Why:</b> the store exists, so still <code>200</code>. <code>open</code> is false, the reason is given, and there is no promise for the app to show."),
    ("03-unknown", "Case 3: a store that does not exist", "<b>Why:</b> the id is well-formed but matches no store, so <code>404</code> with a problem body the app can act on."),
    ("04-malformed", "Case 4: a malformed id", "<b>Why:</b> <code>koramangala</code> is an area name, not a store id, so <code>400</code>: the request itself is wrong."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What the API does", "Proved by"], [
    ["Open store", "<code>200</code>, promise in minutes", "<code>openStoreIs200WithADeliveryPromise</code>"],
    ["Closed store", "<code>200</code>, reason, promise <code>null</code>", "<code>closedStoreIs200WithAReasonAndNoDeliveryPromise</code>"],
    ["Well-formed id, no such store", "<code>404</code> problem with the path in <code>instance</code>", "<code>unknownStoreIs404Problem</code>"],
    ["Area name instead of an id", "<code>400</code> problem", "<code>malformedStoreIdIs400Problem</code>"],
    ["Lower-case id", "<code>400</code> in this version; Practice challenge 1 accepts it", "<code>CaseInsensitiveIdChallengeTest</code> (Practice)"],
    ["Wrong path or trailing slash", "<code>404</code>", "<code>anotherPathUnderStoresIs404</code>"],
    ["<code>POST</code> to the status", "<code>405</code>", "<code>postIsNotAllowedOnTheStatus</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Returning null for an unknown store, which Spring sends as <code>200</code> with an empty body.</p>
<p>It looks harmless: the lookup found nothing, so return nothing. But <code>200</code> tells the app "all good". The app has no field to read, falls back to its default, and shows "Delivering in 10 minutes". The first test reproduces this with a "before" controller kept only in the tests, then shows the fixed API answering <code>404</code>.</p>
</div>
""" + code(read(T + "UnknownStoreTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "StoreController.java", dwn("Receives <code>GET /stores/{storeId}/status</code>, checks the id's shape, and picks <code>200</code>, <code>400</code> or <code>404</code>.",
        "HTTP decisions (status codes, error bodies) live in one place.",
        "No endpoint at all.",
        "<ul><li><code>ResponseEntity</code> lets one method return a status with a body or a problem.</li><li><code>Optional.map(...).orElseGet(...)</code> forces both cases, found and not found, to be handled.</li></ul>")),
    (J + "StoreStatus.java", dwn("The response shape, as a record. Two factory methods make an open or a closed status.",
        "<code>closed(...)</code> cannot take a delivery promise, so a closed store with \"10 minutes\" cannot be built by mistake.",
        "Each caller builds the JSON differently, and one forgets to clear the promise.")),
    (J + "StoreDirectory.java", dwn("Holds the four stores and finds one by id, returning <code>Optional</code>.",
        "The controller should not know where data comes from; a later station swaps this for a database.",
        "The store list ends up inside the controller.")),
    (J + "StoresApplication.java", "<p>Standard Spring Boot entry point: <code>main</code> starts the embedded server on port 8080.</p>"),
    ("src/main/resources/application.yaml", "<p>Only the application name. Nothing else to configure.</p>"),
    ("pom.xml", "<p>The parent pins Spring Boot 4.1.1 and every library version. <code>spring-boot-starter-webmvc</code> brings Spring MVC, Jackson and Tomcat; the two test starters bring JUnit, AssertJ and MockMvc.</p>"),
]
tree = """stations/001-is-the-dark-store-open/
├── pom.xml                 what to build and with which libraries
├── mvnw, mvnw.cmd, .mvn/   the Maven wrapper: downloads Maven on first run
├── src/main/java/com/basketo/stores/
│   ├── StoresApplication.java   ├── StoreController.java
│   ├── StoreStatus.java         └── StoreDirectory.java
├── src/main/resources/application.yaml
├── src/test/java/com/basketo/stores/   the tests (see Tests)
├── challenge/              Practice tests; solutions ship in a separate pack
└── docs/                   capture script, captures, saved test runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""],
    ["Docker", "Not needed for this station", ""],
    ["curl", "Built into Windows 10+, macOS and Linux", "<code>curl --version</code>"]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests, no server needed""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>, for example <code>./mvnw -Djava.version=21 test</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
""" + code("""# Open store: expect 200 and "deliveryPromiseMinutes":10
curl -i http://localhost:8080/stores/BLR-KOR-01/status

# Closed store: expect 200, "open":false and a reason
curl -i http://localhost:8080/stores/BLR-IND-01/status

# No such store: expect 404 and Content-Type: application/problem+json
curl -i http://localhost:8080/stores/BLR-XYZ-99/status""", "bash") + """
<p>In PowerShell, write <code>curl.exe</code> if <code>curl</code> opens a different command.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>release version 25 not supported</code>", "Maven is using an older JDK.", "Point <code>JAVA_HOME</code> at JDK 25, or add <code>-Djava.version=21</code>."],
    ["<code>Port 8080 was already in use</code>", "Another app uses the port.", "Stop it, or run <code>./mvnw spring-boot:run -Dspring-boot.run.arguments=--server.port=8081</code>."],
    ["<code>'./mvnw' is not recognized</code>", "PowerShell needs the <code>.cmd</code> file.", "Use <code>.\\mvnw.cmd</code>."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>StoreStatusContractTest</code> ({cnt('StoreStatusContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>UnknownStoreTrapTest</code> ({cnt('UnknownStoreTrapTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "UnknownStoreTrapTest.java", "<p>Written first: the empty <code>200</code>, then the <code>404</code> fix.</p>"),
    (T + "StoreStatusContractTest.java", "<p>Open, closed, unknown, malformed, wrong path, wrong method.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app, called through MockMvc. <code>perform</code> sends a request; each <code>andExpect</code> checks one thing about the answer.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/basketo/stores/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=CaseInsensitiveIdChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Accept ids in any letter case", "Beginner-friendly", 20,
    "Customers type <code>blr-kor-01</code>. Accept any letter case, answer with the canonical upper-case id, and make sure a server running in a Turkish locale still works.",
    "all three tests in <code>CaseInsensitiveIdChallengeTest</code> pass.",
    ["Normalise once, at the start of the method, then use the normalised id everywhere.",
     "<code>\"i\".toUpperCase()</code> on a Turkish server gives <code>İ</code>, not <code>I</code>. Pass a fixed locale."],
    "challenge/CaseInsensitiveIdChallengeTest.java", ["challenge/solution/StoreController.java"]) + challenge(2, "List the stores in a city", "Beginner-friendly", 30,
    "Add <code>GET /stores?city=BLR</code>: every store in the city, open or closed, sorted by id. A city with no stores is an empty list.",
    "all three tests in <code>CityStoresChallengeTest</code> pass.",
    ["<code>@RequestParam String city</code> is required by default: Spring answers <code>400</code> when it is missing.",
     "<code>Map.of</code> has no fixed order. Sort, or the same request can give a different list.",
     "An empty list is <code>200 []</code>. <code>404</code> is for one thing that does not exist."],
    "challenge/CityStoresChallengeTest.java", ["challenge/solution/StoreDirectory.java", "challenge/solution/StoreController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Closing time is 1 a.m.</h2>
<p>Stores now open at 6 a.m. and close at 1 a.m. the next day. Sketch how the status is worked out. Where does "now" come from, and how would you test 00:59 and 01:00 without waiting for the clock? Which time zone is "1 a.m." in when a store is in Delhi and the server runs in UTC?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test first: an unknown store must not be a silent <code>200</code>.</li>
<li>Model the answer as a record with two factory methods, open and closed.</li>
<li>Keep the data behind a small class that returns <code>Optional</code>.</li>
<li>In the controller: check the id's shape (<code>400</code>), look it up (<code>404</code>), answer (<code>200</code>).</li>
<li>Write the contract tests for each status code.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["<code>200</code> with the status; <code>404</code> problem for no such store", "Two code paths in the app, both clear.", '<span class="pill ok">Chosen</span>'],
    ["Return <code>null</code> (empty <code>200</code>)", "The app cannot tell \"missing\" from \"fine\".", '<span class="pill bad">Wrong</span>'],
    ["<code>404</code> for a closed store", "Mixes \"does not exist\" with \"exists but closed\"; the app would ask the customer to pick a store again.", '<span class="pill bad">Wrong</span>'],
    ["<code>200</code> with <code>{\"error\":\"not found\"}</code>", "Every client must parse the body to learn it failed; caches and monitoring see success.", '<span class="pill bad">Wrong</span>'],
    ["Throw an exception and map it to <code>404</code> in a handler", "Scales better when many endpoints share errors. Station 006 does this.", '<span class="pill warn">Later</span>']]) + """
<h2>Database design</h2>
<p>None: four stores are fixed in <code>StoreDirectory</code>. Because the controller only sees <code>find(id)</code>, swapping in a database later changes one class.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Security</dt><dd>Store status is public, so no login. The error body never echoes anything except the id you sent, and nothing about the server's internals.</dd>
<dt>Performance</dt><dd>A map lookup: microseconds. The home screen calls this on every open, so in production it would be cached for a few seconds.</dd>
<dt>Reliability</dt><dd>If the status source is down, answering "open" by default is the dangerous choice: it brings back the broken promise. Prefer an error the app can show as "status unavailable".</dd>
<dt>Maintainability</dt><dd>The id rule lives in one regular expression. Change it in one place when Basketo adds 3-digit store numbers.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("When do you return 404 and when 200 with an empty list?", "404 when one specific resource does not exist, like store BLR-XYZ-99. A collection, like 'stores in Pune', always exists; when it has nothing in it, the answer is 200 with []."),
    ("Why not return null from a controller?", "Spring sends null as 200 with an empty body. The client sees success, has nothing to read, and has to guess. A 404 with a problem body says exactly what happened."),
    ("What is the difference between 400 and 404 here?", "400 means the request itself is wrong: the id is not even shaped like a store id, so asking again will never work. 404 means the request is fine but nothing matches it."),
    ("What does @RestController add over @Controller?", "@ResponseBody on every method: return values are written to the response body as JSON instead of being treated as view names."),
    ("What does MockMvc test, and what does it skip?", "It runs the real Spring MVC stack (routing, JSON, status codes) without a network or a server port. It skips the servlet container itself, so things like real ports or TLS are not tested."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can say which test fails if you return <code>null</code> again."],
    ["Design", "Closed is <code>200</code>, unknown is <code>404</code>.", "You can explain why <code>404</code> for closed would hurt the app."],
    ["Tests", "Contract tests for every status code.", "You wrote the trap test before the fix and watched it fail."],
    ["Explanation", "You can walk a request through the controller.", "You can explain what MockMvc does and does not test."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on your own code instead, the way a reviewer would:</p>
<ul class="rules">
<li>Can any path return <code>200</code> with an empty body?</li>
<li>Does a closed store ever carry a delivery promise?</li>
<li>Is every error <code>application/problem+json</code>?</li>
<li>Is there a test for every status code the endpoint can return?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
