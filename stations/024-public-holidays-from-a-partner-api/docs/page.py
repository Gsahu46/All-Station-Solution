"""Station 024 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 24,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · RestClient · @HttpExchange · JDK HttpServer stub · MockMvc",
    "simulation": "The holiday provider is simulated by a demo endpoint inside the same app, called over real HTTP; its data is a few fixed-date holidays, not an official list. Tests use a stub HTTP server instead.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/teamdesk/holidays/"
T = "src/test/java/com/teamdesk/holidays/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Partner API", "Someone else's service that our service calls.", "Calling a supplier to ask what is in stock.", "The holiday provider"),
    ("Timeout", "How long we wait before giving up.", "Hanging up after ringing for a minute.", "<code>read-timeout: 2s</code>"),
    ("502 Bad Gateway", "\"The service I depend on failed.\"", "\"The supplier gave us a wrong answer.\"", "Provider 5xx, bad key, unreadable answer"),
    ("504 Gateway Timeout", "\"The service I depend on was too slow.\"", "\"The supplier did not pick up.\"", "Provider slower than 2 s"),
    ("HTTP interface client", "An interface whose methods Spring turns into HTTP calls.", "A speed-dial button with the number already stored.", "<code>@HttpExchange</code>"),
    ("Stub server", "A fake partner, run by the test, that answers however the test says.", "A colleague playing the customer in a rehearsal.", "<code>StubProvider</code>"),
]
STORY = [
    ("Leave balances ignore holidays", "Employees in Bengaluru lose a day of leave for Kannada Rajyotsava, because Teamdesk does not know it is a holiday."),
    ("The first fix calls the provider", "It works in the demo. Then the provider has a slow morning: every leave request waits, threads pile up, and Teamdesk stops answering anyone. When the provider returns 500, Teamdesk returns 500 too."),
    ("The fix", "Call the provider with a time limit, and translate each kind of failure into an honest answer of our own: too slow, failed, or no list. Never pass their error text on."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Every call to someone else's service needs a time limit and a plan for each way it can fail.</p>

<h2>What are we building?</h2>
<p><code>GET /holidays?year=2026&amp;state=KA</code> asks the holiday provider for a state's holidays and returns them sorted, in our own shape. When the provider is slow or broken, it says so with <code>504</code> or <code>502</code>, quickly.</p>

<h2>An everyday analogy</h2>
<p>A shopkeeper phones the wholesaler for a price. If nobody answers in a minute, she tells the customer "the wholesaler is not answering, come back later" instead of standing at the phone all day while the queue grows.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Check the request</strong> first: a bad year or state is <code>400</code>, and the provider is never called.</li>
<li><strong>Call the provider</strong> through an interface client, with a 1 s connect and a 2 s read limit.</li>
<li><strong>Translate failures</strong>: their 404 is ours; their 5xx, bad key or garbage is <code>502</code>; their slowness is <code>504</code>.</li>
<li><strong>Answer in our shape</strong>: only the fields we use, sorted by date.</li>
</ol>

<details class="qa check"><summary>Check yourself: the provider says 401 because our API key expired. Should our client get 401?</summary><p>No. 401 tells our client <em>they</em> must sign in again, which will not help. The fault is between us and the provider: <code>502</code>, and an alert for us.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real holiday provider.</strong> A simulated one, with a few fixed-date holidays.</li>
<li><strong>No retries or circuit breaker.</strong> Discussed in Design; a later station builds them.</li>
<li><strong>No leave calculation.</strong> Only the holiday list.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Teamdesk</strong> (a fictional HR app) must count public holidays when it computes leave. Holidays come from a provider's API. The first integration had no timeout and no error handling: one slow morning at the provider took Teamdesk down with it, and every provider error reached users as a 500.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> 2026 and KA, <b>then</b> the provider is asked for <code>year=2026&amp;region=KA</code> and the holidays come back sorted by date, without the provider's extra fields.</li>
<li><b>Given</b> the provider takes longer than the read limit, <b>then</b> <code>504</code>, well before the provider answers.</li>
<li><b>Given</b> the provider answers 500, 401, unreadable data, or hangs up, <b>then</b> <code>502</code>, and none of its error text in our body.</li>
<li><b>Given</b> the provider has no list for the state, <b>then</b> <code>404</code>.</li>
<li><b>Given</b> an unknown state, a year outside 2000 to 2100, or no year, <b>then</b> <code>400</code>, and the provider is not called.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Connect limit 1 s, read limit 2 s, both in configuration.</li>
<li>States are normalised with <code>Locale.ROOT</code>; the demo list is KA, MH, DL, TN.</li>
<li>The provider's error bodies are logged, never returned.</li>
<li>Only the fields we use are mapped; anything else the provider adds is ignored.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Call an HTTP API with <code>RestClient</code> and an <code>@HttpExchange</code> interface.</li>
<li>Map a partner's JSON to records.</li>
<li>Set timeouts, and translate 4xx, 5xx and timeouts into honest answers.</li>
<li>Test against a stub HTTP server that can be slow or broken on demand.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/holidays?year&amp;state</code>", "A state's public holidays for a year, from the provider."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "The holidays, sorted by date"],
    ['<span class="pill warn">400</span>', "Unknown state, or a year missing or outside 2000 to 2100"],
    ['<span class="pill warn">404</span>', "The provider has no list for that state and year"],
    ['<span class="pill bad">502</span>', "The provider failed, rejected our key, sent something unreadable, or hung up"],
    ['<span class="pill bad">504</span>', "The provider did not answer within the read limit"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. The app calls its simulated provider over HTTP; year 2098 and 2099 are the simulated provider's demo switches for slow and failing. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-the-providers-raw-answer", "Case 1: what the provider sends", "<b>Why:</b> their shape: extra fields (<code>country</code>, <code>observed</code>, <code>generatedBy</code>) and their own order."),
    ("02-our-answer", "Case 2: what we send", "<b>Why:</b> only the fields we use, sorted by date, under our names."),
    ("03-no-list-for-the-state", "Case 3: a state the provider has no list for", "<b>Why:</b> their 404 becomes our 404, with our own wording."),
    ("04-unknown-state", "Case 4: an unknown state", "<b>Why:</b> refused before any call: <code>400</code>."),
    ("05-provider-fails", "Case 5: the provider fails", "<b>Why:</b> its 500 names a database host. We answer <code>502</code> and keep that text in our logs."),
    ("06-provider-too-slow", "Case 6: the provider is too slow", "<b>Why:</b> the provider takes 3 s; we stop waiting at 2 s: <code>504</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["2026, lower-case ka", "Sorted, our shape; provider asked for KA", "<code>aStatesHolidaysComeBackSortedInOurShape</code>"],
    ["Provider 404", "<code>404</code>", "<code>theProvidersNotFoundIsOurNotFound</code>"],
    ["ZZ; 1999; abc; no year", "<code>400</code>, no call made", "<code>badRequestsAre400AndNeverReachTheProvider</code>"],
    ["Provider 500 with a host name", "<code>502</code>, host not shown", "<code>aProvider500IsOur502WithoutTheirInternals</code>"],
    ["Provider 401 (our key)", "<code>502</code>, key not shown", "<code>ourExpiredKeyIsOur502NotTheClients401</code>"],
    ["HTML instead of JSON", "<code>502</code>", "<code>anAnswerWeCannotReadIs502</code>"],
    ["Connection closed with no answer", "<code>502</code> unreachable, not a timeout", "<code>aDroppedConnectionIs502NotATimeout</code>"],
    ["Provider takes 2 s, limit 400 ms (tests)", "<code>504</code> in under 1.5 s", "<code>theRealEndpointGivesUpInTimeAndSaysWhoFailed</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">No timeout and no handling of the partner's 5xx, so our API hangs or 500s.</p>
<p><code>RestClient.create(url)</code> works in every demo. The first test shows it waiting the full 2 seconds a slow provider takes, and it would wait far longer. The second shows the provider's 500 escaping as an exception, which our API turns into its own 500. The third shows the real endpoint answering <code>504</code> within its limit and <code>502</code> for the failure. While building, removing the read timeout turned 1 test red, removing the failure handling turned 4 red, and passing the provider's message through turned 2 red.</p>
</div>
""" + code(read(T + "SlowProviderTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "HolidayController.java", dwn("Validates, calls the provider, and translates every failure into our own answer.",
        "One <code>try</code> with a <code>catch</code> per kind of failure, ordered from specific to general.",
        "Letting the provider's exception become our 500.")),
    (J + "HolidayProviderClient.java", dwn("The provider's API as an interface, with records for its JSON.",
        "Spring writes the HTTP call; the interface is easy to read and easy to fake.",
        "Hand-built URLs and string JSON.")),
    (J + "ProviderClientConfig.java", dwn("Builds the client with a connect and a read time limit.",
        "Limits from configuration, so operations can tune them without a release.",
        "The trap: a client with no time limit.")),
    (J + "DemoProviderController.java", "<p>The simulated provider, so the app runs on its own. Switched off in tests, which use a stub server.</p>"),
    ("src/main/resources/application.yaml", "<p>The provider's address and time limits, and the demo provider switch.</p>"),
    (J + "HolidaysApplication.java", "<p>Standard Spring Boot entry point.</p>"),
]
tree = """stations/024-public-holidays-from-a-partner-api/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/teamdesk/holidays/
│   ├── HolidayController.java      ├── HolidayProviderClient.java
│   ├── ProviderClientConfig.java   ├── DemoProviderController.java   └── HolidaysApplication.java
├── src/test/java/com/teamdesk/holidays/   (see Tests; StubProvider is the fake partner)
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
""" + code("""curl "http://localhost:8080/holidays?year=2026&state=KA"

# The simulated provider's demo switches: 2099 fails, 2098 is too slow
curl -i "http://localhost:8080/holidays?year=2099&state=KA"
curl -i "http://localhost:8080/holidays?year=2098&state=KA\"""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>502</code> unreachable for every request", "The provider address is wrong, or the app runs on another port.", "Check <code>teamdesk.holidays.base-url</code>."],
    ["<code>504</code> for normal requests", "The read limit is shorter than the provider's normal answer.", "Raise <code>read-timeout</code> a little; never remove it."],
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>HolidayContractTest</code> ({cnt('HolidayContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>SlowProviderTrapTest</code> ({cnt('SlowProviderTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Every other provider failure; nothing of theirs leaks", f"<code>ProviderFailureTest</code> ({cnt('ProviderFailureTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "SlowProviderTrapTest.java", "<p>Written first: the old call's wait and its escaping 500, and the real endpoint's 504 and 502.</p>"),
    (T + "HolidayContractTest.java", "<p>A year's holidays, the provider's 404, and requests refused before any call.</p>"),
    (T + "ProviderFailureTest.java", "<p>500, 401, HTML and a dropped connection, each with its answer.</p>"),
    (T + "StubProvider.java", "<p>The fake partner: the JDK's own HTTP server on a random port, told per test how to behave.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: points the app at the stub, with a 400 ms read limit.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/teamdesk/holidays/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=LastGoodAnswerChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Serve the last good answer", "Go deeper", 30,
    "A year's holidays rarely change. Keep the last good answer per year and state; when the provider fails or is too slow, serve it. Say where the answer came from: <code>\"source\": \"provider\"</code> or <code>\"cache\"</code>.",
    "both tests in <code>LastGoodAnswerChallengeTest</code> pass, and the station's tests still pass.",
    ["A <code>ConcurrentHashMap</code> keyed by year and state is enough here.",
     "Catch the failure where you build the answer; rethrow it when there is nothing cached, or when it is a 404."],
    "challenge/LastGoodAnswerChallengeTest.java", ["challenge/solution/HolidayController.java"]) + challenge(2, "Send an API key", "Beginner-friendly", 15,
    "The provider wants an <code>X-Api-Key</code> header. Read the key from <code>teamdesk.holidays.api-key</code> and send it with every call. It must never appear in our responses.",
    "the test in <code>ApiKeyChallengeTest</code> passes.",
    ["<code>RestClient.builder().defaultHeader(...)</code> adds it to every request.",
     "In real deployments the property comes from an environment variable, never from the repository."],
    "challenge/ApiKeyChallengeTest.java", ["challenge/solution/ProviderClientConfig.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Retry, or stop asking?</h2>
<p>Should we retry a failed call to the provider? Which failures are worth one retry, and which never are? If the provider is down for an hour, what stops thousands of our requests from each waiting 2 seconds? Sketch a circuit breaker: when it opens, when it tries again, and what users see meanwhile.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the stub provider and the trap test: the old call waits, and its 500 escapes.</li>
<li>Declare the provider's API as an <code>@HttpExchange</code> interface with records.</li>
<li>Build the client with connect and read limits from configuration.</li>
<li>Translate each kind of failure; test each one, including a dropped connection.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["<code>@HttpExchange</code> interface over <code>RestClient</code>", "An interface and a config class.", '<span class="pill ok">Chosen</span>'],
    ["<code>RestClient</code> calls written by hand", "More code per call; fine for one or two calls.", '<span class="pill warn">Also fine</span>'],
    ["<code>RestTemplate</code>", "Deprecated in Spring Framework 7.1.", '<span class="pill bad">Avoid in new code</span>'],
    ["No timeout", "One slow partner takes us down.", '<span class="pill bad">The trap</span>'],
    ["WireMock for the stub", "A dependency; richer matching and recording.", '<span class="pill warn">For bigger integrations</span>']]) + """
<h2>Database design</h2>
<p>None in this station. Holidays change once a year: a real system would copy them into a <code>public_holidays</code> table (date, state, name) on a schedule, and answer from there, calling the provider only to refresh.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Time limits</dt><dd>The read limit must be shorter than our own clients' patience, and every thread waiting on a partner is one not serving anyone else.</dd>
<dt>Errors</dt><dd>Log the partner's error body, with the status; return our own wording. Their messages name hosts, keys and versions.</dd>
<dt>Secrets</dt><dd>API keys come from the environment (challenge 2), never from the repository or a log line.</dd>
<dt>Monitoring</dt><dd>Count 502s and 504s by cause. A rise in timeouts is often the first sign of a partner's trouble.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What happens without a timeout on an HTTP call?", "The thread waits as long as the other side likes. Under load, every request thread ends up waiting and the whole service stops answering."),
    ("502 or 504?", "504 when the upstream service did not answer in time; 502 when it answered badly (5xx, garbage) or could not be reached."),
    ("Should a partner's 401 become our 401?", "No. It means our credentials with them are wrong, which our client cannot fix. Answer 502 and alert ourselves."),
    ("What is @HttpExchange?", "A Spring annotation for declaring an HTTP API as a Java interface. HttpServiceProxyFactory turns it into a client over RestClient."),
    ("How do you test a partner integration?", "Against a stub HTTP server you control: make it slow, failing, or return garbage, and check each answer. Never against the real partner in unit tests."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can map each provider failure to our status code without looking."],
    ["Resilience", "Timeouts set, failures translated.", "You can explain thread exhaustion."],
    ["Testing", "A stub that can be slow or broken.", "Why not test against the real provider."],
    ["Explanation", "502 versus 504.", "Retries and circuit breakers, and when each helps."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any outgoing HTTP call:</p>
<ul class="rules">
<li>Is there a connect and a read time limit?</li>
<li>What does each failure (4xx, 5xx, timeout, garbage) become for our caller?</li>
<li>Can any of the partner's error text reach our caller?</li>
<li>Is there a test with a slow and a failing partner?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
