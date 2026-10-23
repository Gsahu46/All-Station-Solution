"""Station 096 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 96,
    "stack": "Spring Boot 4.1.1 · Java 25 · servlet filter (OncePerRequestFilter) · token bucket · 429 Too Many Requests and Retry-After · @ConfigurationProperties · a test clock",
    "simulation": "The geocoder is simulated: a fixed list of five places stands in for Mapwise's maps data. The partners and their keys are demo ones.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No database, no Docker. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows). Demo keys: Zoomkart <code>mw_demo_zoomkart_7Qp2Lx9V</code>, Chalo (trial) <code>mw_demo_chalo_K3vN8sT1</code>, Old Maps (suspended) <code>mw_demo_oldmaps_P0dW5yZr</code>.",
}
J = "src/main/java/com/mapwise/geocode/"
T = "src/test/java/com/mapwise/geocode/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("API key", "A long secret string that says which partner is calling.", "A member card at a club's door.", "<code>X-Api-Key</code>"),
    ("Rate limit", "How many requests a partner may send in a short time.", "A tap that only runs so fast.", "5 a second"),
    ("Token bucket", "A bucket of tokens refilled at a steady speed; each request takes one.", "A jar of coupons refilled every few minutes.", "<code>RateLimiter.Bucket</code>"),
    ("Burst", "How many requests can come at once after a quiet spell: the bucket's size.", "How many coupons the jar holds.", "10"),
    ("Quota", "How many requests a partner may send in a whole day.", "A monthly phone data pack.", "20 a day for the trial"),
    ("429 and Retry-After", "The answer \"too many requests\", with how many seconds to wait.", "\"Come back in 5 minutes\" on a shop door.", "<code>Retry-After: 1</code>"),
]
STORY = [
    ("A loop that never stops", "A partner's app has a bug: it calls Mapwise's geocoder again and again, 3 million times in an hour."),
    ("Everyone slows down", "Mapwise had one limit for the whole API. The buggy partner used it all, and every other partner's requests were slow or refused."),
    ("The fix", "Each partner gets its own bucket and its own daily quota, keyed by its API key. The buggy partner gets 429s; everyone else carries on as usual."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A limit protects others only if it belongs to the one who is over it. Count per partner, not per API.</p>

<h2>What are we building?</h2>
<p>A geocoding API for partners: every request carries a key, and every partner has its own limits.</p>

<h2>An everyday analogy</h2>
<p>A water tank with one tap per flat. A flat that leaves its tap open drains its own share, not the whole building's.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Who</strong>: read the key from the <code>X-Api-Key</code> header and find the partner. No key or a wrong key: <code>401</code>.</li>
<li><strong>Allowed?</strong> A suspended partner: <code>403</code>.</li>
<li><strong>How much?</strong> Take a token from that partner's bucket and count the request for the day. None left: <code>429</code> and how long to wait.</li>
<li><strong>Answer</strong>: look up the address.</li>
</ol>

<details class="qa check"><summary>Check yourself: a partner sends nothing for an hour, then 100 requests at once. How many get through with a bucket of 10 refilled at 5 a second?</summary><p>10 at once (the bucket is full, but never more than its size), then about 5 a second as tokens come back. A quiet hour does not save up 18,000 requests.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real maps.</strong> Five places in a list.</li>
<li><strong>One server.</strong> The counters live in this server's memory; with several servers each would count on its own (Production).</li>
<li><strong>No sign-up.</strong> Keys and plans are in configuration.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Mapwise</strong> (a fictional maps company): one partner's bug sent 3 million requests in an hour and slowed the API for everyone.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo plans: Zoomkart 5 a second, bursts of 10, 100,000 a day; Chalo (trial) 1 a second, bursts of 3, 20 a day; Old Maps suspended. Days are UTC days.</p>
<ol class="gwt">
<li><b>Given</b> a valid key and a known address, <b>then</b> <code>200</code> with the place; any case and spacing.</li>
<li><b>Given</b> no key, a wrong key, or a key in the URL, <b>then</b> <code>401</code>; a suspended key <code>403</code>.</li>
<li><b>Given</b> a full bucket, <b>then</b> a burst of its size gets through, the next is <code>429</code> with <code>Retry-After</code>, and a token comes back every 1/rate seconds.</li>
<li><b>Given</b> the day's quota used, <b>then</b> <code>429</code> with the seconds until 00:00 UTC; refused requests do not count.</li>
<li><b>Given</b> one partner over its limit, <b>then</b> other partners are not affected.</li>
<li><b>Given</b> another partner's id on <code>/usage</code>, <b>then</b> <code>403</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>The key is checked and the limit applied before any controller runs.</li>
<li>Two requests at once can never both take the last token.</li>
<li>Keys are not stored, only their SHA-256.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Authenticate API keys in a servlet filter and pass the caller on.</li>
<li>Write a token bucket, and explain why it beats a fixed window.</li>
<li>Answer <code>429</code> with a correct <code>Retry-After</code> in the RFC 9457 problem shape.</li>
<li>Test time-based limits with a clock you move, and concurrency with real threads.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
zoom50 = read("docs/captures/zoomkart-50-requests.txt").strip()
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/geocode?address=...</code> with <code>X-Api-Key</code>", "Coordinates for an address."],
    ["<code>GET</code>", "<code>/partners/{id}/usage</code> with <code>X-Api-Key</code>", "The partner's plan and what is left (this call counts too)."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "Found; or the partner's usage"],
    ['<span class="pill warn">400</span>', "No address, under 3 or over 200 characters, control characters; an id that is not a number"],
    ['<span class="pill warn">401</span>', "No key, an unknown key, or the key in the URL"],
    ['<span class="pill warn">403</span>', "A suspended key; another partner's usage"],
    ['<span class="pill warn">404</span>', "No place for this address"],
    ['<span class="pill warn">429</span>', "The partner's bucket is empty, or its day's quota is used: <code>Retry-After</code> says how many seconds to wait"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-zoomkart-geocodes", "Case 1: Zoomkart looks up MG Road", "<b>Why:</b> <code>200</code>."),
    ("02-any-case-and-spacing", "Case 2: odd case and spaces", "<b>Why:</b> the same place: addresses are normalised with <code>Locale.ROOT</code>."),
    ("03-not-a-known-place", "Case 3: an unknown address", "<b>Why:</b> <code>404</code>."),
    ("04-too-short", "Case 4: two letters", "<b>Why:</b> <code>400</code>."),
    ("05-no-key", "Case 5: no key", "<b>Why:</b> <code>401</code>."),
    ("06-key-in-the-url", "Case 6: a real key in the URL", "<b>Why:</b> <code>401</code>: keys in URLs end up in logs; it is refused, not read."),
    ("07-a-suspended-key", "Case 7: a suspended key", "<b>Why:</b> <code>403</code>."),
    ("08-chalo-reads-zoomkarts-usage", "Case 8: Chalo reads Zoomkart's usage", "<b>Why:</b> <code>403</code>."),
    ("09-zoomkarts-50th-request", "Case 9: Zoomkart's request after its 50", "<b>Why:</b> its bucket is empty: <code>429</code>, wait a second."),
    ("10-chalo-right-after", "Case 10: Chalo, right after", "<b>Why:</b> <code>200</code>: Zoomkart's bug did not touch Chalo's bucket."),
    ("11-chalos-fourth-in-a-second", "Case 11: Chalo's fourth request in a second", "<b>Why:</b> its own bucket holds 3: <code>429</code>."),
    ("12-chalos-usage", "Case 12: Chalo's usage, a second later", "<b>Why:</b> the token that came back paid for this call."),
]) + """
<h2>Zoomkart's 50 requests</h2>
<p class="muted">Before case 9, <code>docs/capture.sh</code> sent 50 requests with Zoomkart's key one after another, as fast as curl could. Status codes counted:</p>
""" + code(zoom50, "text") + """
<p class="muted">More than 10 got through because tokens came back while the 50 ran (5 a second): the bucket at work, not a leak.</p>
"""

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["One global limit, one buggy partner", "Everyone refused", "<code>oneGlobalLimitLetsOnePartnersBugSlowEveryone</code>"],
    ["Per-partner buckets", "The buggy partner gets its 10; another is not affected", "<code>eachPartnerHasItsOwnBucket</code>"],
    ["A known address, any case and spacing", "<code>200</code>, the same place", "<code>aKnownAddressIsFoundWhateverItsCaseAndSpacing</code>"],
    ["Unknown, too short, too long, missing; a trailing slash", "<code>404</code>, <code>400</code>, <code>404</code>", "<code>unknownAddressesAre404AndBadOnes400</code>"],
    ["Usage", "Plan, tokens left, used today, reset time", "<code>aPartnerReadsItsOwnLimitsAndWhatIsLeft</code>"],
    ["10 at once, then 0.2 s, then a quiet minute", "10, then 1, then 10 again (not 300)", "<code>aBurstOfTenThenOneEveryFifthOfASecond</code>"],
    ["The trial's 21st request of the day; midnight UTC", "<code>429</code> until midnight; then <code>200</code>", "<code>theDailyQuotaStopsAtTwentyAndComesBackAtMidnightUtc</code>"],
    ["100 requests at the same moment", "Exactly 10 answered", "<code>aHundredRequestsAtOnceGetExactlyTheBurst</code>"],
    ["8 threads, 20,000 takes, a bucket of 5,000", "Exactly 5,000", "<code>parallelTakesNeverHandOutMoreThanTheBucketHolds</code>"],
    ["No key, wrong, upper-cased, 10,000 characters, in the URL", "<code>401</code>; none counted", "<code>withoutAValidKeyInTheHeaderIt401s</code>"],
    ["A suspended key", "<code>403</code>", "<code>aSuspendedKeyIs403</code>"],
    ["Another partner's usage", "<code>403</code>", "<code>aPartnerCannotReadAnotherPartnersUsage</code>"],
    ["CRLF, NUL, tab, 5,000 characters; SQL, paths, lookup strings", "<code>400</code>; <code>404</code>", "<code>maliciousAddressesAreRefusedOrHarmless</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">One global limit, so one partner's bug slows everyone.</p>
<ul>
<li><strong>The old way.</strong> The test makes one bucket for the whole API (5 a second, bursts of 10). Zoomkart's loop sends 50 requests; Chalo's single request is then refused.</li>
<li><strong>The API.</strong> The same 50 from Zoomkart: 10 answered, 40 refused with <code>429</code>. Chalo's request: <code>200</code>.</li>
</ul>
<p>While building, each part was undone once: one bucket for all partners turned 4 tests red; refused requests counted against the day 1; no daily quota 1; no cap on the refill 4; no <code>Retry-After</code> 2; the key read from the URL 1; suspended keys let in 1; any partner's usage 1; control characters allowed 1; addresses not normalised 1. Removing <code>synchronized</code> at first turned nothing red (see Tests).</p>
</div>
""" + code(read(T + "GlobalLimitTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "ApiKeyFilter.java", dwn("Key, suspension and limit, before any controller.",
        "Reads <code>X-Api-Key</code>, finds the partner by hash, refuses suspended ones, takes a token, and answers <code>401</code>, <code>403</code> or <code>429</code> in the problem shape.",
        "Requests without a key reaching the geocoder; one partner using everyone's capacity.",
        "<ul><li>A key in the URL is refused with a message, not read: URLs are written to access logs.</li><li>Unknown keys never get a bucket, so random keys cost no memory.</li></ul>")),
    (J + "RateLimiter.java", dwn("A token bucket and a daily count per partner.",
        "Refills by elapsed time, capped at the burst; takes a token; counts only answered requests; works out <code>Retry-After</code>.",
        "Bursts at window edges; a partner locked out for the day by its own refused retries.",
        "<ul><li>The check and the take are one synchronized step per partner: partners never wait for each other.</li><li>Shortcut: in memory, per server. With N servers each partner gets N times the limit.</li></ul>")),
    (J + "Partners.java", dwn("Partners and plans from configuration.", "Finds a partner by the SHA-256 of its key.", "Keys readable by anyone who reads the configuration.")),
    (J + "GeocodeController.java", dwn("The two endpoints.", "Validates the address; checks the usage id against the caller.", "One partner reading another's usage.")),
    (J + "Geocoder.java", "<p>Simulated: five places in a map, addresses normalised with <code>Locale.ROOT</code>.</p>"),
    ("src/main/resources/application.yaml", "<p>The partners, their key hashes and plans.</p>"),
    (J + "GeocodeApplication.java", "<p>Entry point, and the <code>Clock</code> the buckets refill by.</p>"),
]
tree = """stations/096-partner-api-keys-and-quotas/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/mapwise/geocode/
│   ├── ApiKeyFilter.java   ├── RateLimiter.java   ├── Partners.java
│   ├── GeocodeController.java   ├── Geocoder.java   └── GeocodeApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/mapwise/geocode/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Send Chalo's trial key four times in a row:</p>
""" + code("""for i in 1 2 3 4; do curl -s -o /dev/null -w '%{http_code}\\n' -H 'X-Api-Key: mw_demo_chalo_K3vN8sT1' 'http://localhost:8080/geocode?address=Charminar,%20Hyderabad'; done""", "bash") + """
<p>Three <code>200</code>s and a <code>429</code>. Then read <code>/partners/2/usage</code> with the same key, and send Zoomkart's key in between: it is never refused because of Chalo.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Every request is 401", "The key is in the URL or misspelt; keys are exact, case included.", "Send it in the <code>X-Api-Key</code> header."],
    ["429 although you sent few requests", "The trial bucket holds 3; or the daily 20 are used.", "Read <code>/partners/2/usage</code>; wait <code>Retry-After</code> seconds."],
    ["A limit twice as high in production", "Two servers, each with its own counters.", "Shared counters (Production)."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>GeocodeContractTest</code> ({cnt('GeocodeContractTest')}), <code>RateLimitTest</code> ({cnt('RateLimitTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>GlobalLimitTrapTest</code> ({cnt('GlobalLimitTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, one user accessing another user's data, malicious input", f"<code>ApiKeySecurityTest</code> ({cnt('ApiKeySecurityTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">Time stands still in the tests unless a test moves it (<code>TestClock</code>), so \"0.2 s later\" means exactly that, however slow the machine. Each test starts on a new day, so buckets are full and daily counts are zero without any reset hook in the app.</p>
<p class="muted">Found while building: with <code>synchronized</code> removed, the 100-requests-at-once test still passed in most runs: through MockMvc the requests rarely meet inside the few lines that check and take a token. A second test hits the bucket itself from 8 threads, 20,000 times, with room for 5,000: without <code>synchronized</code> it handed out more in each of three runs.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "GlobalLimitTrapTest.java", "<p>Written first: one bucket for everyone against one per partner.</p>"),
    (T + "RateLimitTest.java", "<p>Burst, refill, cap, daily quota, midnight, and two concurrency tests.</p>"),
    (T + "GeocodeContractTest.java", "<p>Found, not found, bad input, usage.</p>"),
    (T + "ApiKeySecurityTest.java", "<p>401, 403, another partner's usage, malicious addresses.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the demo keys, a new day at 10:00 UTC before each test.</p>"),
    (T + "TestClock.java", "<p>A clock moved by hand.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/mapwise/geocode/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=RemainingHeadersChallengeTest</code>.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Say what is left", "Beginner-friendly", 20,
    "Every answer after the key check carries <code>X-RateLimit-Remaining</code> (whole requests left in the bucket) and <code>X-Quota-Remaining</code> (requests left today), on <code>200</code>, <code>404</code> and <code>429</code> alike. Partners can slow down before they hit the wall.",
    "both tests in <code>RemainingHeadersChallengeTest</code> pass.",
    ["Let the decision carry what is left, and set the headers in the filter.",
     "An IETF draft standardises <code>RateLimit</code> headers; it is still a draft, so this challenge uses the common <code>X-</code> names."],
    "challenge/RemainingHeadersChallengeTest.java", ["challenge/solution/RateLimiter.java", "challenge/solution/ApiKeyFilter.java"]) + challenge(2, "A batch costs what it asks for", "Go deeper", 35,
    "<code>POST /geocode/batch</code> with <code>{\"addresses\": [...]}</code> (1 to 10) answers each address. It costs one request per address, from the bucket and from the day: all or nothing. An invalid body costs nothing.",
    "both tests in <code>BatchGeocodeChallengeTest</code> pass.",
    ["The filter cannot know the cost before the body is read: let it skip the take for this path and the controller take <i>n</i>.",
     "<code>ErrorResponseException.getHeaders()</code> carries <code>Retry-After</code> on a <code>429</code> thrown from a controller."],
    "challenge/BatchGeocodeChallengeTest.java", ["challenge/solution/RateLimiter.java", "challenge/solution/ApiKeyFilter.java", "challenge/solution/GeocodeController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Six servers, one limit</h2>
<p>Mapwise runs six copies of this API behind a load balancer. Each counts on its own, so Zoomkart really gets 30 a second. Design shared limits: what you store in Valkey (Redis) per partner, how one request takes a token atomically (a Lua script, or <code>INCR</code> with an expiry per second), what happens when Valkey is slow or down (refuse, or allow and log?), and how many milliseconds that adds to every request.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: one bucket for all against one per partner.</li>
<li>Write the filter: key, suspension, then the limit, all before the controller.</li>
<li>Write the bucket with a clock you can move, and test burst, refill, cap and quota.</li>
<li>Prove the bucket under threads.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["A token bucket per partner", "A few numbers per partner; a lock per partner.", '<span class="pill ok">Chosen</span>'],
    ["One limit for the whole API", "One partner's bug refuses everyone.", '<span class="pill bad">The trap</span>'],
    ["A fixed one-second window", "Twice the burst across a window edge; a second of nothing after a burst.", '<span class="pill bad">Review finding</span>'],
    ["A sliding log of timestamps", "Exact, but memory grows with the rate.", '<span class="pill warn">Rarely worth it</span>'],
    ["Limits at the API gateway", "Another system to configure; no code here.", '<span class="pill warn">At larger scale</span>']]) + """
<h2>Database design</h2>
<p>No database: partners and plans are configuration, counters are memory. Nothing survives a restart, which is acceptable for counters that refill in seconds; the daily quota restarts too (a demo rule). With several servers or a quota that must survive restarts, keep the counters in Valkey.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Several servers</dt><dd>Memory counters multiply the limit by the number of servers. Use a shared store (Valkey; Redis 8 is AGPL) or limits at the gateway.</dd>
<dt>Keys</dt><dd>Generate them long and random (at least 128 bits), show them once, store only a hash, let partners rotate them, and give them a prefix (<code>mw_live_</code>) so secret scanners can spot leaked ones.</dd>
<dt>Before the key check</dt><dd>Unknown keys are refused before any bucket exists, but a flood of them still costs a hash each. Limit by address at the edge too.</dd>
<dt>Clients</dt><dd>Tell partners to honour <code>Retry-After</code> and back off with jitter; a client that retries at once makes a 429 storm.</dd>
<dt>Monitoring</dt><dd>Count 429s per partner: a sudden rise is usually a partner's bug, worth an email.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why per-key limits rather than one global limit?", "So one client's bug or abuse only affects that client. A global limit is a shared resource any one client can use up."),
    ("Token bucket or fixed window?", "A token bucket: smooth refill, bursts capped at its size. A fixed window lets twice the limit through across a window edge."),
    ("What goes in a 429?", "Retry-After with the seconds to wait, and a body that says which limit was hit."),
    ("Where do API keys go?", "In a header. Query strings end up in access logs, proxies and browser history."),
    ("How do you store API keys?", "Only a hash. Long random keys do not need a slow hash like passwords do; SHA-256 is enough."),
    ("How do you test a rate limiter?", "With a clock you control, so refill is exact; and with real threads for the check-and-take."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Limits", "Per-key 429s.", "A token bucket with a cap, a daily quota that only counts answered requests, a correct Retry-After."],
    ["Security", "Keys checked before controllers.", "Keys hashed, refused in URLs, suspended keys 403."],
    ["Testing", "A burst test.", "A moved clock, and a thread test that fails without the lock."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("A fixed one-second window is not a bucket",
     "\"Simpler than a bucket: count the requests in each second\": and a partner can send 10 at 10:00:00.999 and 10 more at 10:00:01.000, twice the burst in a millisecond. After a burst it allows nothing until the second turns, then everything at once. The plan says 5 a second; this allows 10.",
     "<code>aBurstOfTenThenOneEveryFifthOfASecond</code> fails: 0.2 s after the burst, the token that should be back is not."),
    ("Refused requests are counted against the day",
     "<code>usedToday++</code> runs before the checks, so every 429 also uses up the quota. A partner whose client retries a burst without waiting burns its whole day in seconds, and is then locked out until midnight by its own refused requests.",
     "<code>theDailyQuotaStopsAtTwentyAndComesBackAtMidnightUtc</code> and <code>parallelTakesNeverHandOutMoreThanTheBucketHolds</code> fail: the day counts 20,000 instead of 5,000."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate replaces the bucket with \"a simpler counter per second\" and moves the daily count to the top \"so every request is counted\". Read the file and list every problem before opening the findings.</p>
<p class="path">review/RateLimiter.java</p>
""" + code(read("review/RateLimiter.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">The trap test passes on the flawed version: limits are still per partner. Its problems are in how the limit counts, which only tests that look at time and at refused requests can see.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
