"""Station 040 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 40,
    "stack": "Spring Boot 4.1.1 · Java 25 · base62 codes · PostgreSQL 17 ON CONFLICT · 302 redirects · LongAdder + @Scheduled flush · virtual threads · Testcontainers",
    "simulation": "Links and campaigns are demo data, not Chhotu's. No SMS is sent; the short links point at example addresses.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/chhotu/links/"
T = "src/test/java/com/chhotu/links/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Short link", "A short address that redirects to a long one.", "A token number that stands for a long address.", "<code>http://localhost:8080/k9Qz7Ab</code>"),
    ("Base62", "Digits 0–9, A–Z and a–z: 62 symbols, so short codes hold many values.", "Number plates using letters and digits.", "<code>CodeGenerator</code>"),
    ("Collision", "Two links getting the same random code.", "Two people drawing the same raffle ticket.", "the trap"),
    ("302 and 301", "Redirects: 302 says \"for now\", 301 says \"forever, remember it\".", "A temporary diversion sign vs a new road on the map.", "<code>follow</code>"),
    ("Buffered counting", "Count in memory, write the totals every few seconds.", "A tally on paper, entered in the register at the end of the hour.", "<code>ClickCounter</code>"),
    ("Birthday problem", "Repeats among random picks come much sooner than intuition says.", "23 people: 50% chance two share a birthday.", "<code>chanceOfARepeat</code>"),
]
STORY = [
    ("Long links in SMS", "Marketing pastes 300-character tracking links into SMS. Chhotu shortens them to a few characters."),
    ("Two campaigns, one code", "Codes were 4 random characters, saved with \"update if it exists, else insert\". A new campaign drew a code already in use, and the Diwali sale's link quietly started opening the phone launch. Lakhs of SMS were already out."),
    ("The fix", "Seven-character codes, a primary key on the code, and a retry when it is taken. A taken code is refused, never overwritten. Clicks are counted in memory so redirects stay fast."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Random is not unique. The database's key makes it unique.</p>

<h2>What are we building?</h2>
<p><code>POST /links</code> shortens a URL. <code>GET /{code}</code> sends the visitor on and counts the click, and <code>GET /links/{code}/stats</code> shows the count.</p>

<h2>An everyday analogy</h2>
<p>A coat check. You get a token; the attendant never gives out a token that is already on a hook. If the number they pick is taken, they pick another. They do not take the coat that is there off the hook.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Pick a random code</strong> of 7 base62 characters.</li>
<li><strong>Insert it</strong>; if the code is taken, the database inserts nothing, and we try another.</li>
<li><strong>On a click</strong>, look up the target, add one to a counter in memory, and answer 302.</li>
<li><strong>Every 5 seconds</strong>, write the counted clicks to the database.</li>
</ol>

<details class="qa check"><summary>Check yourself: why not answer 301, which browsers remember, so repeat clicks are faster?</summary><p>Because they are remembered: later clicks never reach us, so they are never counted, and the link's destination can never be changed. A short link for a campaign needs both.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No SMS.</strong> Links only.</li>
<li><strong>No accounts.</strong> Anyone can create a link; a real service needs owners and abuse checks.</li>
<li><strong>One app instance for counting.</strong> Stats include this instance's unflushed clicks; challenge 3 covers many servers.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Chhotu</strong> (a fictional link shortener) serves marketing teams who paste 300-character tracking links into SMS. Two campaigns got the same short code, and one overwrote the other.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a long URL, <b>then</b> <code>201</code> with a 7-character base62 code and a short URL; the same URL again gets a new code.</li>
<li><b>Given</b> a code that is already taken, <b>then</b> another code is tried; the existing link is never changed. If 5 attempts all collide, <code>503</code>.</li>
<li><b>Given</b> a click, <b>then</b> <code>302</code> to the target, and the click is counted.</li>
<li><b>Given</b> 1,000 clicks at the same moment, <b>then</b> the count is 1,000, including clicks that arrive during a flush.</li>
<li><b>Given</b> <code>javascript:</code>, <code>data:</code>, <code>ftp:</code> or an address without a host, <b>then</b> <code>400</code>.</li>
<li><b>Given</b> an unknown code, <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>The code is the primary key; a collision is never resolved by overwriting.</li>
<li>Only http and https targets, checked in Java and by a constraint.</li>
<li>A redirect never waits for a database write.</li>
<li>Codes are case-sensitive: in base62, <code>a</code> and <code>A</code> are different digits, so codes are never normalised.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Generate base62 codes and reason about collisions.</li>
<li>Use a unique key with <code>ON CONFLICT DO NOTHING</code> and retry.</li>
<li>Choose between 301 and 302.</li>
<li>Count high-volume events without slowing the request.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/links</code>", "<code>{\"targetUrl\"}</code>: a new short link."],
    ["<code>GET</code>", "<code>/{code}</code>", "<code>302</code> to the target, and one click counted."],
    ["<code>GET</code>", "<code>/links/{code}/stats</code>", "The target and the click count."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "A link was created"],
    ['<span class="pill ok">302</span>', "Following a link"],
    ['<span class="pill warn">400</span>', "Not an http or https address, blank, longer than 2,048 characters, or an unknown field"],
    ['<span class="pill warn">404</span>', "No such code"],
    ['<span class="pill bad">503</span>', "Every attempt drew a taken code; try again"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against one fresh database. curl does not follow redirects here, so the <code>302</code> and its <code>Location</code> are visible. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-shorten-a-campaign-link", "Case 1: a 109-character campaign link", "<b>Why:</b> a random 7-character code; <code>Location</code> is the short URL."),
    ("02-someone-taps-it", "Case 2: a tap", "<b>Why:</b> <code>302</code> to the long URL; the click is counted in memory."),
    ("03-someone-else-taps-it", "Case 3: another tap", "<b>Why:</b> 302 again: browsers do not cache it, so every click reaches us."),
    ("04-the-click-count", "Case 4: the stats", "<b>Why:</b> 2 clicks: stored clicks plus those not yet written."),
    ("05-a-code-that-does-not-exist", "Case 5: zzzzzzz", "<b>Why:</b> <code>404</code>."),
    ("06-a-javascript-link", "Case 6: a javascript: URL", "<b>Why:</b> a short link would hide it: <code>400</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A forced collision", "Another code is tried; the first link is untouched", "<code>nowACollisionIsRetriedAndTheFirstLinkIsUntouched</code>"],
    ["Every attempt collides", "<code>503</code>; nothing overwritten", "<code>whenEveryAttemptCollidesNothingIsOverwrittenAndTheAnswerIs503</code>"],
    ["Codes differing only in case", "Two different links", "<code>codesDifferingOnlyInCaseAreDifferentLinks</code>"],
    ["1,000 clicks at once", "1,000 counted", "<code>aThousandClicksAtOnceAreAThousandClicks</code>"],
    ["2,000 clicks while flushes run", "2,000 stored", "<code>clicksArrivingDuringAFlushAreKeptForTheNextOne</code>"],
    ["200 first clicks on each of 50 new links", "200 each", "<code>theFirstClicksOnANewLinkAreNotLost</code>"],
    ["200 links created at once", "200 different codes", "<code>twoHundredLinksAtOnceGetTwoHundredCodes</code>"],
    ["Duplicate code, bad code, javascript: target, negative clicks, written directly", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"],
    ["javascript:, data:, ftp:, no host, not a URL; too long; extra field", "<code>400</code>", "<code>LinkContractTest</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Random codes without a unique constraint, so collisions overwrite links.</p>
<p>The old store saves the Diwali link, then a launch link that drew the same code: the Diwali link now opens the launch. The birthday problem shows why it happened so soon. Among 5,000 four-character codes, the chance of at least one repeat is about 57%. With seven characters and 1 lakh links, it is under 0.2%, which is rare but still not never. That is why the key, not the length, is the fix. With the code forced to repeat, the real store tries another code and leaves the first link alone. While building, each fix was undone once. A non-atomic flush (<code>sum()</code> then <code>reset()</code>) turned 1 test red. A race when creating a new link's counter turned 1 red, but only after a test called the counter directly from 200 threads; through HTTP the requests were too spread out to hit it. No retry turned 1 red, and an upsert that overwrites 2.</p>
</div>
""" + code(read(T + "OverwritingCodesTrapTest.java"), "java") + code(read(T + "OldLinkStore.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "LinkController.java", dwn("Creates links, redirects with 302, and shows stats.",
        "Only web addresses are accepted, and a redirect does nothing slow.",
        "301 (clicks stop reaching us), or any URI (a short link hiding <code>javascript:</code>).")),
    (J + "LinkStore.java", dwn("Inserts with a random code, retrying when it is taken.",
        "<code>ON CONFLICT (code) DO NOTHING</code>: a taken code inserts 0 rows and touches nothing.",
        "The trap: \"update if it exists\", which turns a collision into an overwrite.")),
    (J + "ClickCounter.java", dwn("Counts clicks in memory and writes them every few seconds.",
        "A <code>LongAdder</code> per link: many threads add without waiting; <code>sumThenReset</code> keeps clicks that arrive during a flush.",
        "An <code>UPDATE … clicks + 1</code> per click: every click on a hot link waits for the same row lock.",
        "<ul><li>The limit: clicks not yet flushed are lost if the process crashes; a clean shutdown flushes first (<code>@PreDestroy</code>).</li></ul>")),
    (J + "CodeGenerator.java", dwn("Seven random base62 characters from <code>SecureRandom</code>.",
        "Unpredictable, so one link's code says nothing about the next.",
        "Sequential codes: anyone can walk through every link.")),
    (M + "V1__links.sql", dwn("The links table and its named constraints.",
        "The code is the primary key: no writer can create a second link with it.",
        "Two rows with one code, and a redirect that picks either.")),
    ("src/main/resources/application.yaml", "<p>The database, the base of short URLs, and the flush interval.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "LinksApplication.java", "<p>Entry point, with scheduling switched on for the flush.</p>"),
]
tree = """stations/040-short-links-with-click-counts/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/chhotu/links/
│   ├── LinkController.java   ├── LinkStore.java   ├── ClickCounter.java
│   ├── CodeGenerator.java    └── LinksApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__links.sql
├── src/test/java/com/chhotu/links/   (see Tests)
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
<p>Create a link, open the short URL in a browser a few times, then compare the stats with the database before and after 5 seconds:</p>
""" + code("""curl -X POST http://localhost:8080/links -H "Content-Type: application/json" -d '{"targetUrl":"https://example.com"}'
curl http://localhost:8080/links/<code>/stats
docker compose exec postgres psql -U chhotu -d chhotu -c "SELECT code, clicks FROM links\"""", "bash") + """
<p>The stats count every click at once; the table catches up at the next flush.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["The browser stops hitting the app after the first click", "A 301 was cached (from another service or an old version).", "Clear the browser cache; this app answers 302."],
    ["Clicks in the table lag behind the stats", "Buffered clicks are written every 5 seconds.", "Expected. Lower <code>chhotu.clicks.flush-ms</code> to see them sooner."],
    ["<code>Could not find a valid Docker environment</code>", "Docker is not running.", "Start Docker, then run the tests again."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the pieces it uses.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>LinkContractTest</code> ({cnt('LinkContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>OverwritingCodesTrapTest</code> ({cnt('OverwritingCodesTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>LinkDatabaseTest</code> ({cnt('LinkDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Concurrency", "A real concurrency test that proves the invariant holds", f"<code>LinkConcurrencyTest</code> ({cnt('LinkConcurrencyTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "OverwritingCodesTrapTest.java", "<p>Written first: the old overwrite, the birthday odds, and the retry.</p>"),
    (T + "LinkConcurrencyTest.java", "<p>Clicks and creates on virtual threads released by one latch, including clicks during flushes.</p>"),
    (T + "LinkDatabaseTest.java", "<p>Named constraints, case-sensitive codes, every attempt colliding, and a rollback.</p>"),
    (T + "LinkContractTest.java", "<p>Create, follow, stats, and every refusal through HTTP.</p>"),
    (T + "OldLinkStore.java", "<p>The old store, kept only in tests.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: no links and no buffered clicks before each test; flushes are done by hand.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/chhotu/links/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=CustomCodeChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in (two Java files and one migration), all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Custom codes", "Beginner-friendly", 25,
    "Marketing may ask for a code of its own, such as <code>Diwali7</code>. If it is free, use it; if it is taken, <code>409</code>. A chosen code is never swapped for a random one, and never takes over an existing link.",
    "both tests in <code>CustomCodeChallengeTest</code> pass.",
    ["The same <code>ON CONFLICT DO NOTHING</code> insert: 0 rows means taken.",
     "A retry makes sense for a random code, not for one a person chose."],
    "challenge/CustomCodeChallengeTest.java", ["challenge/solution/LinkStore.java", "challenge/solution/LinkController.java"]) + challenge(2, "Links that expire", "Go deeper", 30,
    "An optional <code>expiresAt</code>, in the future when the link is made. After it, following the link is <code>410 Gone</code>; its stats stay readable. The column comes in a new migration.",
    "both tests in <code>ExpiryChallengeTest</code> pass.",
    ["<code>@Future</code> on the request field refuses a past time with <code>400</code>.",
     "Let the database compare with its own clock: <code>expires_at &lt;= now()</code>."],
    "challenge/ExpiryChallengeTest.java", ["challenge/solution/V2__link_expiry.sql", "challenge/solution/LinkStore.java", "challenge/solution/LinkController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>10,000 clicks a second on six servers</h2>
<p>A cricket-final campaign link gets 10,000 clicks a second, spread over six app servers. Stats from one server miss the other five's unflushed clicks. Compare a shared counter in a cache (Valkey <code>INCR</code>), a click-event stream processed elsewhere, and this station's buffer with a shorter flush. What does each lose in a crash, and how fresh is the count?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: table, constraints"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: two campaigns forced onto one code.</li>
<li>Make the code the primary key; insert with <code>ON CONFLICT DO NOTHING</code> and retry.</li>
<li>Redirect with 302; count in memory; flush on a schedule and on shutdown.</li>
<li>Prove it with parallel clicks, clicks during flushes, and parallel creates.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Choice", "Options", "Chosen, and why"], [
    ["Code", "Sequential base62; random; hash of the URL", "Random: not guessable, and the same URL can have several campaign links. Costs a collision check, which the key gives for free."],
    ["Collision", "Overwrite; retry; longer codes only", "Retry with the key deciding. Longer codes make collisions rare, never impossible."],
    ["Redirect", "301; 302; 307", "302: every click reaches us and targets can change. 307 also keeps the method; links are only clicked (GET), so 302 is enough."],
    ["Counting", "UPDATE per click; event table; memory + flush", "Memory + flush: no lock per click. Costs up to one flush interval of clicks in a crash, a stated limit."]]) + """
<h2>Database design</h2>
""" + table(["Constraint", "Rule", "Why"], [
    ["<code>links_pkey</code>", "The code is unique", "A collision is refused, whoever writes."],
    ["<code>links_code_base62</code>", "7 characters from 0–9, A–Z, a–z", "Codes stay readable in a URL."],
    ["<code>links_target_web</code>", "Starts with http:// or https://", "A short link can never hide a <code>javascript:</code> or <code>data:</code> URL, even if Java is bypassed."],
    ["<code>links_clicks_non_negative</code>", "clicks ≥ 0", "A broken flush cannot make counts negative."]]) + """
""" + code(read(M + "V1__links.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Abuse</dt><dd>Shorteners are used to hide phishing links. Real services check targets against blocklists, rate-limit creation, and can disable a link.</dd>
<dt>Counting limits</dt><dd>Up to one flush interval of clicks can be lost in a crash; stats on one server miss other servers' unflushed clicks. State both to whoever reads the numbers.</dd>
<dt>Bots</dt><dd>Link previews in chat apps and security scanners \"click\" links too. Raw counts include them unless filtered by user agent or behaviour.</dd>
<dt>Caching</dt><dd>The target lookup is one primary-key read. A small in-memory cache helps at very high rates, as long as changed or expired links are invalidated.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("How do you generate unique short codes?", "Random base62 codes long enough that collisions are rare, a unique key on the code, and an insert that reports a conflict (ON CONFLICT DO NOTHING) followed by a retry. Never resolve a conflict by updating."),
    ("301 or 302 for a short link?", "302 if you need every click to reach you (counting) or the destination may change. 301 is cached by browsers and proxies, sometimes indefinitely."),
    ("How do you count clicks without slowing redirects?", "Do not write per click. Increment in memory (LongAdder) and flush totals periodically, or publish events to a queue. Accept and state the small loss window."),
    ("Why does a 4-character random code collide so soon?", "The birthday problem: with N possible codes, a repeat becomes likely after about √N picks. 62^4 is about 1.5 crore, whose square root is about 3,800."),
    ("Why are short codes not lower-cased like other identifiers?", "In base62, upper and lower case are different digits. Normalising would merge distinct codes."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Uniqueness", "A key and a retry.", "The birthday maths for your code length."],
    ["HTTP", "302 for counted links.", "When 301 or 307 is the right answer."],
    ["Concurrency", "Parallel clicks counted exactly.", "Why sumThenReset loses nothing during a flush."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("An upsert turns a collision into an overwrite",
     "\"An upsert never fails\" is true, and that is the problem: when the random code is taken, the existing link is silently re-pointed. The original bug again, in one SQL statement.",
     "<code>nowACollisionIsRetriedAndTheFirstLinkIsUntouched</code> and <code>whenEveryAttemptCollidesNothingIsOverwrittenAndTheAnswerIs503</code> fail."),
    ("301 instead of 302",
     "Browsers remember a 301, so repeat clicks never reach Chhotu: counts stop growing, and a campaign's destination can never be changed.",
     "<code>followingALinkIsATemporaryRedirectAndCounts</code> and <code>aThousandClicksAtOnceAreAThousandClicks</code> fail on the status."),
    ("Any parseable URI is accepted",
     "<code>javascript:</code> and <code>data:</code> parse fine. A short link would hide them. The database's <code>links_target_web</code> still refused the row, so nothing harmful was stored, but the user got a <code>500</code> instead of a clear <code>400</code>.",
     "<code>onlyWebAddressesCanBeShortened</code> errors with the constraint violation."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate simplifies the service. An upsert replaces the retry loop, because it \"never fails\". 301 replaces 302, because it is \"faster for users, less load for us\". Any URI that parses is accepted, for app deep links. Read both files and list every problem before opening the findings.</p>
<p class="path">review/LinkStore.java</p>
""" + code(read("review/LinkStore.java"), "java") + """
<p class="path">review/LinkController.java</p>
""" + code(read("review/LinkController.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the two flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">The third flaw shows a constraint doing its job: Java let the bad URL through, and the database still refused it. Defence in depth turned a security bug into an ugly error, not a stored phishing link.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
