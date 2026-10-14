"""Station 023 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 23,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · Jackson 3 (tools.jackson) · java.time · MockMvc",
    "simulation": "The courier partner is simulated: its updates are the JSON bodies in the examples. Events are records in memory; no parcel moves.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/dakroute/partner/"
T = "src/test/java/com/dakroute/partner/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("snake_case / camelCase", "Two ways to join words in a name: <code>awb_number</code> and <code>awbNumber</code>.", "Two offices that write dates differently.", "<code>@JsonNaming</code>"),
    ("Tolerant reader", "Read the fields you need; ignore the rest.", "Reading a letter for the address and ignoring the decorations.", "<code>@JsonIgnoreProperties(ignoreUnknown = true)</code>"),
    ("Strict reader", "Refuse anything unexpected.", "A form that is rejected if anything is written outside the boxes.", "<code>fail-on-unknown-properties: true</code>"),
    ("AWB", "Air waybill number: the tracking number of a parcel.", "DKR100000001IN on the label.", "<code>awb_number</code>"),
    ("Local time", "A clock time with no time zone.", "\"09:15\" on a message from a friend abroad.", "<code>event_time</code>"),
    ("Instant", "One exact point in time, shown in UTC.", "The moment a rocket launches, whatever the clocks say.", "<code>at</code> in our response"),
]
STORY = [
    ("The partner adds a field", "One Monday, every delivery update gains <code>rider_phone</code>. Dakroute's webhook answers 400 to all of them; tracking pages stop moving."),
    ("A quick fix makes it worse", "Someone switches the parser to lenient and renames nothing. Now updates are accepted, and every field reads as empty, because <code>awb_number</code> never matched <code>awbNumber</code>."),
    ("The fix", "Map the partner's snake_case names on their class only, ignore fields we do not use (on that class only), and say in code which time zone their times are in."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Be strict with what you control; be tolerant, explicitly and locally, with what a partner sends.</p>

<h2>What are we building?</h2>
<p><code>POST /partner/delivery-updates</code> accepts the courier partner's JSON exactly as they send it and records a tracking event in our own shape: camelCase names, our status names, and times as exact UTC instants.</p>

<h2>An everyday analogy</h2>
<p>A post office accepts parcels from another country. It reads the address in their format and ignores the customs stickers it does not need, but it still refuses a parcel with no address.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Read their names</strong>: <code>awb_number</code> fills <code>awbNumber</code>, for this class only.</li>
<li><strong>Ignore their extras</strong>: new fields are skipped, for this class only; ours stay strict.</li>
<li><strong>Pin the time</strong>: their "09:15" is India time by contract, so it becomes 03:45 UTC.</li>
<li><strong>Translate and record</strong>: their status code becomes ours; an unknown one is kept as UNKNOWN.</li>
</ol>

<details class="qa check"><summary>Check yourself: why not make the whole API ignore unknown fields?</summary><p>Then a typo by our own app (<code>"amout"</code>) is silently ignored too, and a bug becomes missing data. Tolerance belongs where we cannot control the sender.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real partner.</strong> The updates are sample JSON.</li>
<li><strong>No webhook security.</strong> Signature checks come in a later station.</li>
<li><strong>No tracking page.</strong> Events are only recorded.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Dakroute</strong> (a fictional logistics platform) receives delivery updates from a courier partner. The partner's JSON is snake_case, its times have no zone, and it adds fields without notice. Dakroute's platform is strict about unknown fields for its own clients, so each new partner field took the webhook down until someone noticed.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> an update with fields we have never seen, <b>then</b> <code>202</code>, and the fields we know are read.</li>
<li><b>Given</b> <code>"event_time": "2026-10-14 09:15:00"</code>, <b>then</b> the event is at <code>2026-10-14T03:45:00Z</code>; 02:00 on 15 October is 20:30 UTC on the 14th.</li>
<li><b>Given</b> <code>"promised_by": "2026-10-14T18:00:00+05:30"</code>, <b>then</b> <code>2026-10-14T12:30:00Z</code>.</li>
<li><b>Given</b> a status code we do not know, <b>then</b> accepted as UNKNOWN with the raw code kept.</li>
<li><b>Given</b> an AWB we never booked, <b>then</b> <code>404</code>.</li>
<li><b>Given</b> a missing AWB, a time in another format, a bad PIN code, or our own camelCase names, <b>then</b> <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Snake_case naming and ignoring unknown fields apply to the partner's classes only.</li>
<li>Event times are India time by the partner contract; every time we return is a UTC instant.</li>
<li>AWBs are normalised to upper case with <code>Locale.ROOT</code>.</li>
<li>Our responses use our names (camelCase), never the partner's.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Use Jackson naming strategies and <code>@JsonProperty</code>-style mapping per class.</li>
<li>Decide where to ignore unknown fields, and keep the rest strict.</li>
<li>Handle a time with no zone, and an ISO time with an offset.</li>
<li>Know where Jackson 3 lives (<code>tools.jackson</code>) and its defaults.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/partner/delivery-updates</code>", "Record a partner's delivery update. <code>202</code> with the event in our shape."]]) + """
<h2>Request body (the partner's shape)</h2>
""" + table(["Field", "Rule"], [
    ["<code>awb_number</code>", "Required; 10 to 20 letters and digits; must be a shipment we booked."],
    ["<code>status_code</code>", "Required. PKD, ITR, OFD, DLV, RTO are mapped; others become UNKNOWN."],
    ["<code>event_time</code>", "Required; <code>yyyy-MM-dd HH:mm:ss</code>, India time by contract."],
    ["<code>location</code>", "Optional: <code>city_name</code>, <code>pin_code</code> (6 digits)."],
    ["<code>promised_by</code>", "Optional; ISO 8601 with an offset."],
    ["Anything else", "Ignored."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">202</span>', "Recorded"],
    ['<span class="pill warn">400</span>', "A required field missing or malformed, including the wrong time format"],
    ['<span class="pill warn">404</span>', "An AWB we never booked"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-partner-update-with-new-fields", "Case 1: an update with three fields we do not know", "<b>Why:</b> <code>hub_id</code>, <code>rider_phone</code> and <code>temperature_c</code> are ignored. 09:15 India time is 03:45 UTC; 18:00+05:30 is 12:30 UTC."),
    ("02-late-night-in-india", "Case 2: delivered at 02:00 India time", "<b>Why:</b> 02:00 on 15 October in India is 20:30 on 14 October in UTC: the date changes too. The lower-case AWB is normalised."),
    ("03-new-status-code", "Case 3: a status code we do not know", "<b>Why:</b> HLD is kept as UNKNOWN with the raw code, and a warning is logged so someone maps it."),
    ("04-unknown-awb", "Case 4: an AWB we never booked", "<b>Why:</b> <code>404</code>: there is no shipment to attach it to."),
    ("05-time-without-the-agreed-format", "Case 5: a date in another format", "<b>Why:</b> <code>14/10/2026 09:15</code> is not the agreed format: <code>400</code>, rather than a guess."),
    ("06-our-names-not-theirs", "Case 6: our own camelCase names", "<b>Why:</b> this endpoint speaks the partner's names; <code>awb_number</code> is missing: <code>400</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Snake_case in, camelCase out, times in UTC", "202; converted", "<code>snakeCaseInCamelCaseOutAndEveryTimeInUtc</code>"],
    ["02:00 India time", "20:30 UTC the day before", "<code>anIndianLateNightTimeIsTheDayBeforeInUtc</code>"],
    ["Status HLD", "UNKNOWN, raw code kept", "<code>aStatusCodeWeDoNotKnowYetIsKeptAsUnknown</code>"],
    ["AWB never booked", "<code>404</code>", "<code>anAwbWeNeverBookedIs404</code>"],
    ["No AWB; other date formats; short AWB; empty status; 4-digit PIN; camelCase names", "<code>400</code>", "<code>missingOrMalformedFieldsAre400</code>"],
    ["An unknown field on our own type", "Rejected by the app's mapper", "<code>ourOwnTypesStillRejectUnknownFields</code>"],
    ["Unknown fields on the partner type, nested too", "Ignored", "<code>onlyThePartnerTypesOptOut</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Failing on unknown fields, so every new partner field breaks parsing.</p>
<p>Jackson 2 failed on unknown fields by default; Jackson 3's plain <code>JsonMapper</code> does not, but platforms often switch it on to catch their own clients' typos (this one does). The first test shows a strict mapper throwing on <code>rider_phone</code>. The second shows the other wrong fix: a lenient mapper with camelCase names reads every field as <code>null</code>, silently. The third shows the endpoint accepting the payload. While building, removing <code>ignoreUnknown</code> turned 3 tests red, removing snake_case naming turned many red, and reading the partner's times as UTC turned 2 red.</p>
</div>
""" + code(read(T + "NewPartnerFieldTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "DeliveryUpdateController.java", dwn("Finds the shipment, maps the status, pins the time zone and records the event.",
        "The partner's zone is a named constant with a comment: the JSON cannot carry it, so the code must.",
        "Treating a zone-less time as the server's zone.")),
    (J + "PartnerUpdate.java", dwn("The partner's shape: snake_case, tolerant, with its time format.",
        "Naming and tolerance are annotations on this class only, so the rest of the API stays strict.",
        "The trap: strict parsing of a payload we do not control.",
        "<ul><li><code>@JsonNaming</code> from <code>tools.jackson.databind.annotation</code> (Jackson 3); <code>@JsonIgnoreProperties</code> and <code>@JsonFormat</code> stay in <code>com.fasterxml.jackson.annotation</code>.</li><li>The nested <code>Location</code> needs its own annotations.</li></ul>")),
    (J + "TrackingEvent.java", dwn("Our shape, and our statuses with the partner's code for each: an enum with data.",
        "An unknown code becomes UNKNOWN, kept with the raw code, not a rejected update.",
        "Rejecting the partner's whole update over a status we can map later.")),
    ("src/main/resources/application.yaml", "<p>The platform's strict rule: unknown fields are an error, except where a class opts out.</p>"),
    (J + "PartnerApplication.java", "<p>Standard Spring Boot entry point.</p>"),
]
tree = """stations/023-accepting-a-partners-snake-case-json/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/dakroute/partner/
│   ├── DeliveryUpdateController.java   ├── PartnerUpdate.java
│   ├── TrackingEvent.java              └── PartnerApplication.java
├── src/test/java/com/dakroute/partner/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     sample update, capture script, captures, saved runs"""
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
<p>The partner's update is in <code>docs/partner-update.json</code>. Add any field you like and send it again.</p>
""" + code("""curl -i -X POST http://localhost:8080/partner/delivery-updates -H "Content-Type: application/json" -d "@docs/partner-update.json\"""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>400</code> with our field names", "This endpoint reads the partner's snake_case names.", "Send <code>awb_number</code>, not <code>awbNumber</code>."],
    ["<code>404</code>", "Only DKR100000001IN and DKR100000002IN are booked.", "Use one of them."],
    ["Times an hour or 5.5 hours off", "A time read without its zone.", "Check which zone the source means, and convert in one place."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>DeliveryUpdateContractTest</code> ({cnt('DeliveryUpdateContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>NewPartnerFieldTrapTest</code> ({cnt('NewPartnerFieldTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "The app's own mapper: strict, except where a class opts out", f"<code>JsonRulesTest</code> ({cnt('JsonRulesTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "NewPartnerFieldTrapTest.java", "<p>Written first: a strict mapper throws, a camelCase DTO reads nulls, the endpoint accepts.</p>"),
    (T + "DeliveryUpdateContractTest.java", "<p>Names, times and statuses translated, and every refusal.</p>"),
    (T + "JsonRulesTest.java", "<p>Spring's configured <code>JsonMapper</code>: our types strict, partner types tolerant.</p>"),
    (T + "ApiTest.java", "<p>Shared setup and the partner's real payload.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/dakroute/partner/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=DuplicateUpdateChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "A retry is not a new event", "Beginner-friendly", 20,
    "The partner retries when we answer slowly. The same AWB, status and event time is one event: accept the copy, mark it <code>duplicate</code>, and do not store it again. Return <code>eventsForShipment</code>.",
    "the test in <code>DuplicateUpdateChallengeTest</code> passes.",
    ["A record's <code>equals</code> compares every field, so two identical events are equal.",
     "<code>CopyOnWriteArrayList.addIfAbsent</code> checks and adds in one atomic step."],
    "challenge/DuplicateUpdateChallengeTest.java", ["challenge/solution/DeliveryUpdateController.java"]) + challenge(2, "Two time formats", "Go deeper", 35,
    "The partner's v2 sends <code>event_time</code> as ISO 8601 with an offset. Accept both formats with a Jackson 3 <code>ValueDeserializer</code>; ISO without an offset is still refused.",
    "both tests in <code>TimeFormatsChallengeTest</code> pass, and the station's tests still pass.",
    ["Extend <code>tools.jackson.databind.ValueDeserializer&lt;Instant&gt;</code>; attach it with <code>@JsonDeserialize(using = ...)</code>.",
     "Try the v1 pattern with the India zone first, then <code>OffsetDateTime.parse</code>.",
     "<code>ctxt.handleWeirdStringValue</code> turns a bad value into a normal <code>400</code>."],
    "challenge/TimeFormatsChallengeTest.java", ["challenge/solution/PartnerUpdate.java", "challenge/solution/PartnerTimeDeserializer.java", "challenge/solution/DeliveryUpdateController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>A contract with a partner</h2>
<p>Write the one-page contract you would agree with the partner: field names, which are required, the time zone, how they add fields, and how they remove or rename one. What do you do when they send something the contract does not allow: reject, accept and alert, or accept silently?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test with the partner's real payload: strict throws, camelCase reads nulls.</li>
<li>Give the partner's payload its own class, with snake_case naming and tolerance on that class only.</li>
<li>Read the zone-less time with its agreed format and convert it with the agreed zone, in one place.</li>
<li>Translate their statuses into ours; keep the unknown ones visible.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["A partner class with its own naming and tolerance", "One class per partner payload.", '<span class="pill ok">Chosen</span>'],
    ["Global snake_case naming", "Our own API changes shape for everyone.", '<span class="pill bad">Wrong here</span>'],
    ["Global tolerance", "Our own clients' typos are silently ignored.", '<span class="pill bad">Hides bugs</span>'],
    ["Strict parsing of partner payloads", "Every new partner field is an outage.", '<span class="pill bad">The trap</span>'],
    ["Reading the payload as a <code>Map</code>", "No types, no validation; mistakes move into the code.", '<span class="pill bad">Avoid</span>']]) + """
<h2>Database design</h2>
<p>None in this station. With a database: <code>tracking_events</code> (awb, status, partner_status_code, at <code>timestamptz</code>) with a unique key on (awb, partner_status_code, at), so a partner retry cannot insert twice even under concurrency.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Visibility</dt><dd>Ignored fields and unknown status codes are tolerated, not forgotten: log the unknown codes, and count them, so a partner change shows up on a dashboard before it shows up in complaints.</dd>
<dt>Time</dt><dd>Store instants (<code>timestamptz</code>); convert to India time only for display. Write the partner's zone into the contract.</dd>
<dt>Security</dt><dd>A webhook must check that the update really came from the partner (a shared signature), or anyone can move parcels on the tracking page.</dd>
<dt>Retries</dt><dd>Partners retry on timeouts. Answer fast (202), and treat repeats as the same event (challenge 1).</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("How do you map snake_case JSON to Java?", "A naming strategy: @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class) on the class, or @JsonProperty on single fields. Set it per class unless your whole API is snake_case."),
    ("Should you fail on unknown JSON fields?", "For your own clients, failing catches typos. For partners you do not control, ignore unknown fields on their classes, so their additions do not break you."),
    ("What changed in Jackson 3?", "Packages moved to tools.jackson (annotations stay in com.fasterxml.jackson.annotation), JsonMapper is the main type, dates are ISO strings by default, and a plain mapper no longer fails on unknown properties."),
    ("How do you handle a time with no zone?", "Find out which zone it means, write that into the contract and the code, and convert to an instant once, at the edge."),
    ("Why keep unknown status codes instead of rejecting?", "Rejecting loses the whole update over one field you can map later. Keep it as UNKNOWN with the raw code, and alert so it gets mapped."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can predict case 2's UTC time before running it."],
    ["Jackson", "Naming and tolerance per class.", "You know Jackson 3's defaults and where they differ from 2."],
    ["Time", "Zone-less times converted with the agreed zone.", "You can explain why 02:00 IST is the previous day in UTC."],
    ["Explanation", "Strict for ours, tolerant for theirs.", "What a partner contract must say."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any partner integration:</p>
<ul class="rules">
<li>Does a new field from the partner break parsing?</li>
<li>Is tolerance limited to the partner's classes?</li>
<li>Which zone are the partner's times in, and where is that written down?</li>
<li>What happens to a value we do not recognise: rejected, kept, or silently dropped?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
