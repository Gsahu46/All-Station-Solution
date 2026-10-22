"""Station 089 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 89,
    "stack": "Spring Boot 4.1.1 · Java 25 · ETag and If-None-Match · 304 Not Modified · Cache-Control · minimum supported app version",
    "simulation": "The config is demo data in memory, not Streamo's, and much smaller than a real 40 KB config; the byte counts on this page are for the demo config. The endpoints in it are example addresses.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/streamo/config/"
T = "src/test/java/com/streamo/config/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("App config", "Settings the app downloads at launch: which features are on, where the servers are, which version is needed.", "The day's menu at a restaurant.", "<code>GET /app-config</code>"),
    ("ETag", "A short fingerprint of an answer. Same answer, same fingerprint.", "A version number printed on the menu.", "<code>ETag: \"LFOu...\"</code>"),
    ("If-None-Match", "The app sends the fingerprint it has: \"only send the answer if it changed\".", "\"I have menu 12; anything new?\"", "request header"),
    ("304 Not Modified", "\"Nothing changed, keep yours\": no body.", "\"Still menu 12.\"", "the answer to a match"),
    ("Cache-Control: max-age", "How long the app may reuse its copy without asking at all.", "\"This menu is good until lunch.\"", "300 seconds (demo rule)"),
    ("Minimum supported version", "Apps older than this must update before they can be used.", "\"This card no longer works; get a new one.\"", "<code>updateRequired</code>"),
]
STORY = [
    ("The same bytes, millions of times", "Every launch of the Streamo app downloaded the full config: 40 KB, 20 million times a day, almost always identical to the copy already on the phone."),
    ("And no way to retire old apps", "Old app versions with a playback bug kept being used. There was no way to tell them they must update."),
    ("The fix", "Each answer carries a fingerprint (ETag) and a time it may be reused (max-age). The app sends its fingerprint back; if nothing changed, the answer is an empty 304. The config also says which versions must update."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Most of what a busy endpoint sends is something the client already has. Let it ask \"changed?\" and answer \"no\" for free.</p>

<h2>What are we building?</h2>
<p>One endpoint: the config for a platform and an app version, with an ETag and Cache-Control, answering <code>304</code> when the app's copy is current, and telling old apps to update.</p>

<h2>An everyday analogy</h2>
<p>A newspaper stand that, when you show yesterday's paper, says \"there is no new edition yet\" instead of selling you the same paper again.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Build</strong> the answer for this platform and version, including whether it must update.</li>
<li><strong>Fingerprint</strong> it: a hash of its JSON is the ETag.</li>
<li><strong>Compare</strong> with the app's <code>If-None-Match</code>: the same, <code>304</code> with no body; different, <code>200</code> with the new config.</li>
<li><strong>Say how long</strong> the app may keep it without asking: <code>max-age=300</code>.</li>
</ol>

<details class="qa check"><summary>Check yourself: the minimum version is 5.9.0 and the app is 5.10.0. Must it update?</summary><p>No: 10 is more than 9. Compared as text, \"5.10.0\" sorts before \"5.9.0\" and the app would be wrongly forced to update: <code>versionsAreComparedAsNumbersNotText</code>.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No CDN.</strong> The same headers let a CDN answer for you; challenge 3 is about that.</li>
<li><strong>No publishing API.</strong> Config changes come from the code's demo data and the tests.</li>
<li><strong>No real 40 KB.</strong> The demo config is about 500 bytes; the saving is the same in proportion.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Streamo</strong> (a fictional streaming app): 20 million app launches a day download the same 40 KB config, and old app versions need a forced update.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo config: Android latest 6.2.0, minimum 5.9.0; iOS latest 6.1.3, minimum 5.8.0. Demo rule: reuse for 5 minutes.</p>
<ol class="gwt">
<li><b>Given</b> a launch, <b>then</b> <code>200</code> with the config, an <code>ETag</code> and <code>Cache-Control: max-age=300, public</code>.</li>
<li><b>Given</b> <code>If-None-Match</code> with the current ETag, <b>then</b> <code>304</code>, no body, the same ETag and Cache-Control.</li>
<li><b>Given</b> a published change, <b>then</b> the next revalidation gets <code>200</code> and a new ETag.</li>
<li><b>Given</b> an app below the minimum, <b>then</b> <code>updateRequired: true</code>; versions compared as numbers.</li>
<li><b>Given</b> an unknown platform or a malformed version, <b>then</b> <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>The ETag changes when the answer changes, and only then.</li>
<li>Nothing in the answer changes on every request.</li>
<li>A 304 repeats the caching headers.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Use ETag and If-None-Match for conditional GETs, and get 304s from Spring.</li>
<li>Choose a max-age with its cost: how late a change can arrive.</li>
<li>Compare versions as numbers.</li>
<li>Measure the saving instead of assuming it.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/app-config?platform=android|ios&amp;version=x.y.z</code>", "The config for this app, with caching headers. Send <code>If-None-Match</code> to revalidate."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "The config: first launch, or it changed"],
    ['<span class="pill ok">304</span>', "If-None-Match matches: keep your copy; no body"],
    ['<span class="pill warn">400</span>', "Platform not android or ios; version not three numbers; a parameter missing"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-an-app-launch", "Case 1: an app launch", "<b>Why:</b> the config, its ETag, and how long it may be reused."),
    ("02-the-next-launch-sends-the-etag", "Case 2: the next launch sends the ETag back", "<b>Why:</b> unchanged: <code>304</code> with no body, and the same caching headers."),
    ("03-an-app-older-than-the-minimum", "Case 3: app 5.8.9", "<b>Why:</b> below 5.9.0: <code>updateRequired: true</code>. Its own ETag, since the answer differs."),
    ("04-version-5-10-is-newer-than-5-9", "Case 4: app 5.10.0", "<b>Why:</b> compared as numbers, it is above 5.9.0."),
    ("05-if-none-match-star", "Case 5: If-None-Match: *", "<b>Why:</b> Spring answers <code>200</code> here; RFC 9110 (section 13.1.2) calls for <code>304</code>. Apps never send <code>*</code>, so it is left and recorded."),
    ("06-an-unknown-platform", "Case 6: platform windows", "<b>Why:</b> <code>400</code>."),
    ("07-a-version-without-patch", "Case 7: version 6.1", "<b>Why:</b> <code>400</code>: three numbers are expected."),
]) + """
<h2>What 20 launches download</h2>
<p class="muted">Measured by <code>docs/capture.sh</code> with <code>curl -w '%{size_download}'</code> on the demo config:</p>
""" + code(read("docs/captures/bytes.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Below, at and above the minimum; IOS in capitals", "<code>updateRequired</code> only below", "<code>theConfigTellsTheAppWhetherItMustUpdate</code>"],
    ["5.10.0 against 5.9.0", "Newer: no update needed", "<code>versionsAreComparedAsNumbersNotText</code>"],
    ["The same request twice; another version or platform", "The same ETag; a different one", "<code>theETagChangesWhenAndOnlyWhenTheAnswerChanges</code>"],
    ["A published change", "<code>200</code> and a new ETag on the next revalidation", "<code>aPublishedChangeReachesAppsOnTheirNextRevalidation</code>"],
    ["A weak ETag, a list, <code>*</code>, another ETag", "<code>304</code>, <code>304</code>, <code>200</code> (Spring), <code>200</code>", "<code>conditionalRequestsFollowHttpRules</code>"],
    ["Bad platform, version, missing parameter, trailing slash", "<code>400</code>; <code>404</code>", "<code>badQueriesAre400</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">No ETag or Cache-Control, so every launch downloads the same config.</p>
<ul>
<li><strong>The old way.</strong> The test launches the app 20 times without an ETag to send: 20 full downloads of the same bytes.</li>
<li><strong>With the ETag.</strong> The first launch downloads the config and keeps the ETag; the next 19 send it back and get <code>304</code> with an empty body. One download in 20.</li>
</ul>
<p>While building, each part was undone once: no ETag turned 4 tests red; no Cache-Control 2; a fixed ETag that never changes 3; versions compared as text 1; the platform not lower-cased 1; <code>&lt;=</code> instead of <code>&lt;</code> for the minimum 1.</p>
</div>
""" + code(read(T + "EveryLaunchDownloadsTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "AppConfigController.java", dwn("The endpoint.",
        "Builds the answer, hashes its JSON into an ETag, sets Cache-Control, and lets Spring answer <code>304</code> when If-None-Match matches.",
        "Every launch downloading the same bytes.",
        "<ul><li>Spring compares If-None-Match with the ETag of a <code>ResponseEntity</code> by itself, weakly, and keeps Cache-Control on the <code>304</code>. Found while building: no <code>checkNotModified</code> code was needed.</li><li>Maps are sorted (<code>TreeMap</code>) so the same config always gives the same JSON, and the same ETag.</li></ul>")),
    (J + "AppVersion.java", dwn("An app version, compared number by number.", "Three integers, compared in order.", "5.10.0 treated as older than 5.9.0.")),
    (J + "AppConfigs.java", "<p>The published config per platform, demo data in memory; <code>publish</code> stands for an operator publishing a change.</p>"),
    ("src/main/resources/application.yaml", "<p>Problem details for errors.</p>"),
    (J + "AppConfigApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/089-app-config-with-http-caching/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/streamo/config/
│   ├── AppConfigController.java   ├── AppVersion.java   ├── AppConfigs.java   └── AppConfigApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/streamo/config/   (see Tests)
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
<p>Download once, then revalidate with the ETag you got, and compare the sizes:</p>
""" + code("""U='http://localhost:8080/app-config?platform=android&version=6.1.0'
ETAG=$(curl -s -i "$U" | tr -d '\\r' | sed -n 's/^ETag: //p')
curl -s -o /dev/null -w '%{http_code} %{size_download} bytes\\n' "$U"
curl -s -o /dev/null -w '%{http_code} %{size_download} bytes\\n' "$U" -H "If-None-Match: $ETAG\"""", "bash") + """
<p>The first prints <code>200</code> and the size of the config, the second <code>304 0 bytes</code>: the numbers in <code>docs/captures/bytes.txt</code> come from the same two requests.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Never a <code>304</code>", "Something in the answer changes on every request (a timestamp, a random id), so the ETag does too.", "Keep per-request values out of cached answers; see the Review tab."],
    ["A <code>304</code> without Cache-Control", "The headers were set only on the <code>200</code> path.", "Set them on the <code>ResponseEntity</code> and let Spring answer the <code>304</code>."],
    ["Apps forced to update that are new enough", "Versions compared as text.", "Compare number by number, as <code>AppVersion</code> does."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>AppConfigContractTest</code> ({cnt('AppConfigContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>EveryLaunchDownloadsTrapTest</code> ({cnt('EveryLaunchDownloadsTrapTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted"><code>conditionalRequestsFollowHttpRules</code> records one place where Spring differs from RFC 9110: <code>If-None-Match: *</code> gets <code>200</code>. It was first written expecting <code>304</code> and failed; the running app answers the same (case 5). Found while building.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "EveryLaunchDownloadsTrapTest.java", "<p>Written first: bytes for 20 launches, without and with the ETag.</p>"),
    (T + "AppConfigContractTest.java", "<p>The answer, versions, ETags, publishing, conditional rules, bad queries.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the demo config before each test, request helpers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/streamo/config/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=RolloutBucketChallengeTest</code>. The Last-Modified test needs a <code>Clock</code> bean before it starts.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Last-Modified", "Beginner-friendly", 25,
    "Each answer carries <code>Last-Modified</code>: when its platform's config was published, to the second. <code>If-Modified-Since</code> with that date (and no If-None-Match) gets <code>304</code> until the next publish.",
    "the test in <code>LastModifiedChallengeTest</code> passes.",
    ["Record the publish time with a <code>Clock</code>, cut to seconds: HTTP dates have no fractions.",
     "<code>ResponseEntity.ok().lastModified(...)</code>; Spring checks If-Modified-Since too."],
    "challenge/LastModifiedChallengeTest.java", ["challenge/solution/AppConfigs.java", "challenge/solution/AppConfigController.java", "challenge/solution/AppConfigApplication.java"]) + challenge(2, "A 10% rollout that stays cacheable", "Go deeper", 30,
    "The app sends <code>bucket=0..99</code>, stable per install. Demo rule: <code>watchParty</code> is on for buckets 0 to 9. Installs on the same side of the rollout share one ETag.",
    "both tests in <code>RolloutBucketChallengeTest</code> pass.",
    ["Let only \"in or out\" reach the answer, never the bucket number itself.",
     "<code>@Min(0) @Max(99)</code> on an optional <code>Integer</code> parameter."],
    "challenge/RolloutBucketChallengeTest.java", ["challenge/solution/AppConfigController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>A CDN in front, and an urgent update</h2>
<p>Put a CDN in front of <code>/app-config</code>. With <code>max-age=300, public</code>, what does it store, and how many requests still reach the app? Now a security bug means 6.1.x must update today: how quickly can a new minimum reach every phone, and what do you add (a shorter max-age, a purge, <code>stale-while-revalidate</code>) to make it faster?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: bytes for 20 launches.</li>
<li>Build a deterministic answer (sorted maps, no per-request values).</li>
<li>Hash it into an ETag; set Cache-Control; let Spring answer If-None-Match.</li>
<li>Compare versions as numbers for <code>updateRequired</code>.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["ETag from a hash of the answer + max-age", "The answer is built and hashed for each request, even for a 304.", '<span class="pill ok">Chosen</span>'],
    ["No caching headers", "Every launch downloads everything.", '<span class="pill bad">The trap</span>'],
    ["ETag from a config version number", "No hashing; the answer must then depend only on that version.", '<span class="pill warn">Faster, easier to get wrong</span>'],
    ["<code>ShallowEtagHeaderFilter</code>", "One line; hashes every response in the app, including ones that should not be cached.", '<span class="pill warn">Broad</span>'],
    ["A long max-age, no revalidation", "Fewest requests; a change or forced update arrives late.", '<span class="pill bad">Review finding</span>']]) + """
<h2>Database design</h2>
<p>This station has no database: the config is demo data in memory. With a table behind it, an <code>updated_at</code> or version column could give Last-Modified (challenge 1) or the ETag without building the answer.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>max-age is a delay</dt><dd>Every minute of max-age is a minute a change may take to arrive. Pick it with the forced-update case in mind.</dd>
<dt>CDNs and gzip</dt><dd>A CDN can answer revalidations for you. Compression changes the bytes; CDNs often turn a strong ETag weak, which If-None-Match still matches.</dd>
<dt>Measure</dt><dd>Count <code>304</code>s against <code>200</code>s; a sudden drop in <code>304</code>s means something in the answer started changing per request.</dd>
<dt>Clients</dt><dd>Mobile HTTP clients revalidate only if they keep a cache: make sure the app's HTTP client has one, or stores and sends the ETag itself.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What does an ETag do?", "It identifies one version of an answer. The client sends it back in If-None-Match; if it still matches, the server answers 304 with no body."),
    ("max-age or ETag?", "Both: max-age says how long the client may skip asking; the ETag makes asking cheap afterwards."),
    ("What breaks ETags?", "Anything in the answer that changes per request: timestamps, request ids, unordered maps."),
    ("Strong or weak ETags?", "Strong means byte-for-byte equal; weak means equivalent. If-None-Match compares weakly, so both give 304s."),
    ("How do you force old apps to update?", "Send the minimum supported version (or a flag) in the config, compare versions as numbers, and keep max-age short enough for the update to arrive in time."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Caching", "ETag and 304.", "Cache-Control on the 304 too; nothing per-request in the answer."],
    ["Versions", "updateRequired works.", "Compared as numbers, with the 5.10 case tested."],
    ["Evidence", "It caches.", "You measured the bytes before and after."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("A timestamp in a cached answer",
     "\"Apps compare serverTime with the phone's clock\" is useful, but it makes every answer different. The ETag changes on every request, no app ever gets a <code>304</code>, and every launch downloads everything again: the original problem, back.",
     "<code>anAppThatKeepsTheETagDownloadsOnceAndThenGets304s</code>, <code>theETagChangesWhenAndOnlyWhenTheAnswerChanges</code> and <code>conditionalRequestsFollowHttpRules</code> fail."),
    ("A one-day max-age",
     "\"Far fewer requests\": also a day before a raised minimum version, a turned-off feature or a moved server reaches the apps that already have a copy.",
     "The Cache-Control checks in the same tests fail; the cost shows only on the day an update is urgent."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate adds <code>serverTime</code> to the config, so apps can warn users whose phone clock is wrong, and raises max-age to a day, since the config rarely changes. Read the file and list every problem before opening the findings.</p>
<p class="path">review/AppConfigController.java</p>
""" + code(read("review/AppConfigController.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">Every request still gets a correct config, so nothing looks broken in the app. The cost shows on the bandwidth bill, and on the day an update cannot wait.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
