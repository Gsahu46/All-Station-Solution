"""Station 025 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 25,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · ConcurrentHashMap.compute · CompletableFuture · virtual threads · MockMvc",
    "simulation": "No SMS is sent: a simulated sender waits as long as a provider call and counts what it would have sent. OTP codes are generated but never returned or logged. Limits are kept in this server's memory.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tijori/otp/"
T = "src/test/java/com/tijori/otp/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("OTP", "A one-time password sent by SMS to prove you hold the phone.", "The 6-digit code your bank texts you.", "<code>POST /otp-requests</code>"),
    ("Race condition", "Two things happening at once give a result neither would alone.", "Two people book the last seat because both saw it free.", "Check, then send, then record"),
    ("Atomic", "Done as one step that nothing can come between.", "Taking the last token from the counter in one grab.", "<code>ConcurrentHashMap.compute</code>"),
    ("Idempotency key", "An id the app sends with a request, and again on a retry, so the server does it once.", "A cheque number: paying the same cheque twice is refused.", "<code>Idempotency-Key</code> header"),
    ("429 and Retry-After", "\"Too many requests\", and how many seconds to wait.", "\"Counter closed, back in 10 minutes.\"", "<code>Retry-After: 360</code>"),
    ("Injectable clock", "Code asks a Clock object for the time, so tests can set it.", "A stage clock the director moves forward between scenes.", "<code>TestClock</code>"),
]
STORY = [
    ("A bot targets one number", "It sends 20 OTP requests at the same instant. Each one checks \"fewer than 3 sent in 10 minutes?\", sees yes, and calls the SMS provider. 20 SMS go out, and Tijori pays for each."),
    ("The app retries a slow request", "The customer taps once, the network is slow, the app retries. The old code counts it as a second request and sends a second code."),
    ("The fix", "Check and book the slot in one atomic step, before calling the SMS provider. Remember each Idempotency-Key, so a retry, even one arriving at the same instant, gets the first answer."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">"Check, then act" is two steps. Under load, something always fits between them.</p>

<h2>What are we building?</h2>
<p><code>POST /otp-requests</code> sends (simulated) an OTP to a number, at most 3 times in any 10 minutes per number. Beyond that it answers <code>429</code> with how long to wait. A retried request gets the same answer and no second SMS.</p>

<h2>An everyday analogy</h2>
<p>A temple gives 3 tokens per family per hour. A careless counter looks at the register, hands over the token, then writes the entry: four relatives at four windows all get one. A careful counter writes the entry and hands the token in one movement, at one register.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Normalise the number</strong>: +91 98765 43210 and 098765-43210 are 9876543210.</li>
<li><strong>Look up the key</strong>: seen before? Return that answer, even if it is still being made.</li>
<li><strong>Check and book in one step</strong>: fewer than 3 in the window? Take a slot. Otherwise <code>429</code> with the wait.</li>
<li><strong>Send the SMS</strong> only after the slot is booked.</li>
</ol>

<details class="qa check"><summary>Check yourself: the count is a ConcurrentHashMap. Why is that not enough?</summary><p>Each call on it is safe, but "read the count, decide, then add" is three calls. Another request can run between them. The decision and the update must be one atomic call: <code>compute</code>.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>Not across servers.</strong> The count lives in one server's memory: with N servers, a number can get 3 × N. Station 125 shares the count.</li>
<li><strong>No real SMS.</strong> A simulated sender counts messages.</li>
<li><strong>No OTP verification.</strong> Only requesting one.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tijori</strong> (a fictional fintech app) pays for every OTP SMS. Bots request thousands for one number, to run up costs or to flood someone's phone. The existing limit fails exactly when it matters: requests that arrive together all slip past it. App retries are counted as new requests.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> 20 requests for one number at the same instant, <b>then</b> exactly 3 are accepted, 17 get <code>429</code>, and 3 SMS are sent.</li>
<li><b>Given</b> requests at 09:00, 09:02 and 09:04, <b>then</b> a 4th at 09:05 gets <code>429</code> with <code>Retry-After: 300</code>, and one at 09:10 is accepted.</li>
<li><b>Given</b> the same Idempotency-Key twice, <b>then</b> the same requestId, no second SMS, no slot used; 10 copies at once are still one request.</li>
<li><b>Given</b> a key reused for another number, <b>then</b> <code>422</code>.</li>
<li><b>Given</b> +91 98765 43210, 098765-43210 and 9876543210, <b>then</b> one number, one limit.</li>
<li><b>Given</b> a number that is not a 10-digit Indian mobile, or a missing or malformed key, <b>then</b> <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>3 requests per number in any 10 minutes (a demo rule); different numbers never wait for each other.</li>
<li>The slot is booked before the SMS is sent; Retry-After counts from the oldest request in the window, rounded up.</li>
<li>The code is never in a response or a log; responses show the number masked.</li>
<li>Time comes from an injected <code>Clock</code>.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Recognise check-then-act races, and fix them with an atomic operation.</li>
<li>Choose between <code>synchronized</code> and <code>ConcurrentHashMap.compute</code>.</li>
<li>Make a request idempotent, including two copies arriving at once.</li>
<li>Answer <code>429</code> with an honest <code>Retry-After</code>, and test time with an injectable clock.</li>
<li>Prove an invariant with a real parallel test.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/otp-requests</code>", "Send an OTP to a number. <code>202</code>: accepted, SMS on its way (simulated)."]]) + """
<h2>Request</h2>
""" + table(["Part", "Rule"], [
    ["<code>Idempotency-Key</code> header", "8 to 64 letters, digits or <code>-</code>. A new key per tap of \"Send OTP\"; the same key when retrying that tap."],
    ["<code>mobile</code>", "An Indian mobile number; +91, a leading 0, spaces and dashes are allowed."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">202</span>', "Accepted (or a retry of an accepted request: the same body)"],
    ['<span class="pill warn">400</span>', "Not a mobile number, or the key is missing or malformed"],
    ['<span class="pill warn">422</span>', "The key was already used for another number"],
    ['<span class="pill warn">429</span>', "3 requests in the last 10 minutes; <code>Retry-After</code> says how many seconds to wait"]]) + """
<p class="muted"><code>Idempotency-Key</code> is described in an IETF draft (draft-ietf-httpapi-idempotency-key-header); check its current status before calling it a standard. <code>429</code> is defined in RFC 6585 and <code>Retry-After</code> in RFC 9110.</p>
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, within a few seconds. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-first-request", "Case 1: the first tap", "<b>Why:</b> accepted; the code is not in the response, the number is masked, two attempts left."),
    ("02-the-app-retries-the-same-tap", "Case 2: the app retries that tap", "<b>Why:</b> the same key (and the same number, written with +91): the same requestId, no second SMS, no slot used."),
    ("03-second-tap", "Case 3: a second tap", "<b>Why:</b> a new key: a new request. 098765-43210 is the same number."),
    ("04-third-tap", "Case 4: a third tap", "<b>Why:</b> the last slot in this window."),
    ("05-fourth-tap", "Case 5: a fourth tap", "<b>Why:</b> <code>429</code>. <code>Retry-After</code> counts to when the first request leaves the 10-minute window."),
    ("06-key-reused-for-another-number", "Case 6: a key reused for another number", "<b>Why:</b> a bug in the app, not a retry: <code>422</code>, and no SMS."),
    ("07-not-a-mobile-number", "Case 7: not a mobile number", "<b>Why:</b> <code>400</code>, before any limit or SMS."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["First request", "202, masked, no code, 2 left", "<code>anOtpRequestIsAcceptedWithoutShowingTheCodeOrTheNumber</code>"],
    ["Three formats of one number, then a 4th", "One limit; <code>429</code>, Retry-After 360", "<code>theFourthIn10MinutesIs429WithRetryAfterFromTheOldest</code>"],
    ["09:00, 09:02, 09:04, then 09:05, 09:09:59, 09:10", "Retry-After 300, then 1, then accepted", "<code>retryAfterCountsFromTheOldestRequestInTheWindow</code>"],
    ["20 requests at once, one number", "3 accepted, 17 × 429, 3 SMS", "<code>twentyBotRequestsAtOnceGetThreeSms</code>"],
    ["3 numbers × 5 requests at once", "3 each", "<code>differentNumbersEachGetTheirOwnThree</code>"],
    ["Same key twice", "Same answer, 1 SMS, no slot", "<code>aRetryWithTheSameKeyGetsTheSameAnswerAndNoSecondSms</code>"],
    ["Same key 10 times at once", "One requestId, 1 SMS", "<code>tenCopiesOfOneRequestAtTheSameInstantAreOneRequest</code>"],
    ["Key reused for another number", "<code>422</code>, no SMS", "<code>aKeyReusedForAnotherNumberIs422</code>"],
    ["A refused request's key, retried later", "Accepted", "<code>aRefusedRequestCanBeRetriedWithItsKeyOnceTheWindowMoves</code>"],
    ["Bad numbers, keys, bodies", "<code>400</code>", "<code>badRequestsAre400</code>"],
    ["Two servers", "6: the limit is per server", "<code>theLimitIsPerServerSoTwoServersAllowSix</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">An in-memory limiter that only works on one server, and check-then-act races.</p>
<p>The old limiter uses thread-safe pieces: a <code>ConcurrentHashMap</code> and a synchronized list. The first test sends 20 requests at once and more than 3 get through: each checked before any had recorded. The second runs the real limiter the same way: exactly 3. The third states the limit that remains: two servers, each with its own count, allow 6. That is not fixed here; it needs a shared store (station 125).</p>
</div>
""" + code(read(T + "CheckThenActTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "OtpController.java", dwn("Reads the key and the body, and hands them to the service. <code>202</code> on success.",
        "The controller has no rules; the service is where retries, limits and the SMS meet.",
        "Rules spread across controllers.")),
    (J + "OtpService.java", dwn("Normalises the number, handles replays, asks the limiter, sends the SMS.",
        "<code>putIfAbsent</code> of a <code>CompletableFuture</code>: the first request with a key does the work; any copy waits for the same result.",
        "Storing the answer only after it is ready, so two copies both do the work.",
        "<ul><li>A refused request removes its key: nothing happened, so a later retry may try again.</li><li><code>Retry-After</code> is rounded up, never inviting an early retry.</li><li>The code goes to the SMS text only.</li></ul>")),
    (J + "OtpLimiter.java", dwn("3 per number per 10 minutes, checked and booked in one <code>compute</code>.",
        "Atomic per key: requests for one number take turns; other numbers do not wait.",
        "The trap: check, send, then record.")),
    (J + "SimulatedSmsSender.java", "<p>Waits like a provider, counts per number, logs the masked number and never the text.</p>"),
    (J + "SmsSender.java", "<p>The one-method interface the real provider would implement.</p>"),
    ("src/main/resources/application.yaml", "<p>Problem bodies for errors, and the simulated SMS latency.</p>"),
    (J + "OtpApplication.java", "<p>Entry point, and the <code>Clock</code> bean tests replace.</p>"),
]
tree = """stations/025-otp-request-limiter/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tijori/otp/
│   ├── OtpController.java   ├── OtpService.java   ├── OtpLimiter.java
│   ├── SmsSender.java       ├── SimulatedSmsSender.java   └── OtpApplication.java
├── src/test/java/com/tijori/otp/   (see Tests)
├── review/                   The flawed version for the Review tab
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
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Virtual threads are final in Java 21.</p>
<h2>Try it yourself</h2>
""" + code("""# Run this four times, changing the key each time; the 4th answers 429 with Retry-After
curl -i -X POST http://localhost:8080/otp-requests -H "Content-Type: application/json" \\
     -H "Idempotency-Key: my-tap-0001" -d '{"mobile":"9876543210"}'""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["The same requestId every time", "You are resending the same key.", "Change the key for a new tap."],
    ["<code>400</code> with a valid number", "The key has characters other than letters, digits and dashes, or is under 8 long.", "Use a UUID or similar."],
    ["<code>429</code> straight away after a restart", "Not possible: counts live in memory and start empty.", "If you see it, another instance answered."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>OtpContractTest</code> ({cnt('OtpContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>CheckThenActTrapTest</code> ({cnt('CheckThenActTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Concurrency", "A real parallel test proving the invariant", f"<code>OtpConcurrencyTest</code> ({cnt('OtpConcurrencyTest')})", '<span class="pill ok">pass</span>'],
    ["Idempotency", "The same request twice gives one effect", f"<code>OtpReplayTest</code> ({cnt('OtpReplayTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">The parallel tests use virtual threads released together by a <code>CountDownLatch</code>. While building, the concurrency, replay and trap classes were run five more times in a row: no failures.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "CheckThenActTrapTest.java", "<p>Written first: the old limiter's race, the atomic limiter's exact 3, and the per-server limit.</p>"),
    (T + "OtpConcurrencyTest.java", "<p>Twenty bot requests at once, and three numbers at once, through the whole app.</p>"),
    (T + "OtpReplayTest.java", "<p>Retries, ten copies at once, a reused key, and a retry after a refusal.</p>"),
    (T + "OtpContractTest.java", "<p>The first request, the limit with Retry-After, the window moving, and bad requests.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: a clock the tests move by hand, and empty limits before each test.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tijori/otp/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=KeyExpiryChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Forget keys after a day", "Beginner-friendly", 20,
    "Keys are kept forever (the <code>shortcut:</code> comment in <code>OtpService</code>). Remember each key for 24 hours, then treat it as new and free its memory.",
    "the test in <code>KeyExpiryChallengeTest</code> passes.",
    ["Store the time with each key, from the injected <code>Clock</code>.",
     "<code>map.values().removeIf(...)</code> drops the old ones."],
    "challenge/KeyExpiryChallengeTest.java", ["challenge/solution/OtpService.java"]) + challenge(2, "A limit per address too", "Go deeper", 35,
    "Bots rotate numbers. Also allow at most 20 requests per client address in 10 minutes, whatever the numbers, with its own <code>429</code>.",
    "the test in <code>PerIpLimitChallengeTest</code> passes, and the station's tests still pass.",
    ["Give the limiter a key and a maximum: <code>tryAcquire(\"ip:\" + address, 20)</code>.",
     "Decide whether a request refused by the number limit still uses an address slot, and write the reason down.",
     "Behind a load balancer, the remote address is the balancer's: trust forwarded headers only from it."],
    "challenge/PerIpLimitChallengeTest.java", ["challenge/solution/OtpLimiter.java", "challenge/solution/OtpService.java", "challenge/solution/OtpController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Three servers, one limit</h2>
<p>Tijori runs three instances. Where should the count live so all three share it: a database row with a lock, an atomic counter in Valkey with an expiry, or something else? What happens to OTP requests when that store is down: refuse all, or allow and alert? Station 125 builds one answer.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: 20 requests at once through the old limiter.</li>
<li>Make check-and-book one <code>compute</code> call; test 20 at once again: exactly 3.</li>
<li>Add the idempotency map with a future per key; test 10 copies at once.</li>
<li>Inject the clock; test Retry-After and the window moving.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["<code>compute</code> per number", "Requests for one number take turns; others never wait.", '<span class="pill ok">Chosen</span>'],
    ["<code>synchronized</code> on the whole limiter", "Correct, but every number waits for every other.", '<span class="pill warn">Works, slower</span>'],
    ["Check, send, then record", "Races exactly when a bot attacks.", '<span class="pill bad">The trap</span>'],
    ["Book after the SMS succeeds", "Sounds kind to customers; reopens the race for the whole SMS call.", '<span class="pill bad">Wrong</span>'],
    ["A shared store (Valkey, a database)", "Infrastructure, and a plan for when it is down.", '<span class="pill warn">For more than one server</span>']]) + """
<h2>Database design</h2>
<p>None in this station. Across servers: an <code>otp_requests</code> table (mobile, requested_at) and a count in the same transaction with a row lock per number, or a Valkey key per number with an expiry and an atomic increment.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Servers</dt><dd>The guarantee is "3 per number per 10 minutes per server instance". With more than one instance, the count must be shared.</dd>
<dt>Restarts</dt><dd>Counts and keys live in memory: a restart forgets them, and a bot gets a fresh 3. Acceptable for a demo; not for a bank.</dd>
<dt>Secrets</dt><dd>The OTP itself appears only in the SMS text. It is not in responses or logs, and the number is masked in both.</dd>
<dt>Cost</dt><dd>Count 429s per number and per address; a spike is an attack, and the SMS bill is the first place it shows.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is a check-then-act race?", "Code reads a value, decides, then writes. Between the read and the write another thread does the same, so both decide on stale information."),
    ("synchronized or ConcurrentHashMap.compute?", "Both make the step atomic. A synchronized method locks everything; compute locks only the entry for that key, so different numbers do not wait for each other."),
    ("How do you make a request idempotent?", "The client sends a key; the server stores the result under it. A repeat returns the stored result. To cover two copies arriving at once, store a placeholder (a future) atomically before doing the work."),
    ("Why inject a Clock?", "So tests can set and move time: a 10-minute window is tested in milliseconds, and Retry-After can be checked exactly."),
    ("Why is an in-memory limiter not enough?", "Each server counts on its own, and restarts forget. Behind a load balancer the real limit is N times the intended one."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You found all four flaws in the Review tab before opening them."],
    ["Concurrency", "Check and book in one atomic step.", "You can say why compute beats synchronized here."],
    ["Idempotency", "A retry returns the first answer.", "Two copies at the same instant, too."],
    ["Explanation", "Why the old limiter let 20 through.", "What changes with three servers."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("The slot is booked after the SMS is sent", "\"A failed SMS should not cost the customer an attempt\" is a kind thought, and it brings back check-then-act with a 50 ms gap: every request checks before any books.", "<code>twentyBotRequestsAtOnceGetThreeSms</code> and <code>differentNumbersEachGetTheirOwnThree</code> both fail: more than 3 accepted per number."),
    ("The replay is stored after the request completes", "Sequential retries still work, so it looks fine; two copies arriving together both miss the map and both send an SMS.", "<code>tenCopiesOfOneRequestAtTheSameInstantAreOneRequest</code>: more than one requestId."),
    ("Retry-After counts from the newest request", "The wait looks plausible, but it is too long: the slot frees when the oldest request leaves the window.", "<code>retryAfterCountsFromTheOldestRequestInTheWindow</code>: 540 instead of 300."),
    ("Numbers keep their +91 or leading 0", "\"Accept any 10 to 12 digits\" makes 9876543210, 919876543210 and 09876543210 three numbers: a bot gets 9 OTPs, and a retry written with +91 looks like a different number.", "<code>theFourthIn10MinutesIs429WithRetryAfterFromTheOldest</code> (2 attempts left instead of 0), <code>badRequestsAre400</code> and <code>aRetryWithTheSameKeyGetsTheSameAnswerAndNoSecondSms</code> (422)."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate made the limiter "kinder": customers keep their attempt when the SMS provider fails, retries are remembered once the answer is ready, Retry-After is "simpler", and numbers are accepted in any common format. The sequential tests still pass. Read both files and list every problem before opening the findings.</p>
<p class="path">review/OtpService.java</p>
""" + code(read("review/OtpService.java"), "java") + """
<p class="path">review/OtpLimiter.java</p>
""" + code(read("review/OtpLimiter.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the two flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">Two of the four flaws pass every test that sends one request at a time. Only the parallel tests catch them, which is why this station has them.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
