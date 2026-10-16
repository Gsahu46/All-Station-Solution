"""Station 051 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 51,
    "stack": "Spring Boot 4.1.1 · Java 25 · java.time (Instant, LocalDateTime, ZonedDateTime, ZoneRules, TemporalAdjusters) · Clock with @TestBean · RFC 9457 problem details",
    "simulation": "Webinars are demo records kept in memory: no video room, invitation or reminder is created, and they are gone when the app restarts. Time zone rules are the ones shipped with the JDK that ran the captures.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/taskloom/webinars/"
T = "src/test/java/com/taskloom/webinars/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Instant", "One moment on the world's timeline, the same everywhere.", "The moment a cricket match's first ball is bowled.", "<code>startsAt</code> (UTC)"),
    ("LocalDateTime", "A date and a clock time, with no place: it is not a moment.", "\"10:00 on 5 Nov\" written on a sticky note.", "What the host types"),
    ("Time zone", "A region's rules for its clocks, including daylight saving.", "Asia/Kolkata, Europe/London.", "<code>zone</code>, <code>viewerZone</code>"),
    ("Offset", "How far a clock is from UTC at one moment.", "India is always +05:30; London is +00:00 or +01:00.", "<code>+05:30</code> in each time shown"),
    ("Daylight saving gap / overlap", "An hour that does not exist, or happens twice, when clocks jump.", "02:30 on the night US clocks spring forward.", "<code>422</code> answers"),
    ("Clock", "Where the program asks \"what time is it now?\".", "The office wall clock everyone checks.", "A fixed Clock in tests"),
]
STORY = [
    ("10:00 for everyone", "Taskloom's host in Bengaluru set a webinar for 10:00. Attendees in London saw 10:00 too, and joined five and a half hours late."),
    ("Then an hour off", "A fix stored the moment in UTC, but repeated series by adding a month in UTC. When the US left daylight saving, a New York host's 10:00 sessions moved to 09:00."),
    ("The fix", "Turn the host's wall-clock time into a moment using the host's zone, separately for every session; store the moment; show it in each viewer's zone."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A clock time without a place is not a moment. Store the moment; show it in each person's own clock.</p>

<h2>What are we building?</h2>
<p>A host creates a webinar at their own wall-clock time and zone (<code>POST /webinars</code>), optionally repeating monthly. Anyone reads it in their zone (<code>GET /webinars/{id}?viewerZone=…</code>), and every session shows the moment in UTC, the host's time and the viewer's time, each with its offset.</p>

<h2>An everyday analogy</h2>
<p>A train timetable says 10:00 because everyone reading it is at that station. A video call has no single station: you send "10:00 in Bengaluru", and each person's phone turns it into their own time. The phone needs the place, not just "10:00".</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>The host sends</strong> 10:00, 5 Nov, Asia/Kolkata.</li>
<li><strong>The server asks the zone's rules</strong> which offset that wall time has on that date (+05:30), refusing a time that is skipped or repeated.</li>
<li><strong>It stores</strong> the moment, 04:30 UTC, with the host's zone.</li>
<li><strong>Each viewer</strong> sees that moment in their own zone: 04:30 in London, 20:30 the evening before in Los Angeles.</li>
</ol>

<details class="qa check"><summary>Check yourself: a monthly New York webinar at 10:00. Why does it move from 19:30 to 20:30 in India in November?</summary><p>New York leaves daylight saving on 1 November (−04:00 becomes −05:00); India has no daylight saving. The host's 10:00 stays 10:00, so the moment moves one hour later, and India sees it an hour later. That is correct. The old code kept the moment fixed and moved the host.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No reminders or invitations.</strong> Times only.</li>
<li><strong>No weekly series.</strong> Challenge 1.</li>
<li><strong>No database.</strong> Webinars live in memory.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Taskloom</strong> (a fictional SaaS for project teams) runs webinars for customers in many countries. Times were shown wrongly abroad and drifted when daylight saving changed.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> 10:00 on 5 Nov 2026 in Asia/Kolkata, <b>then</b> London sees 04:30 and Los Angeles 20:30 on 4 Nov.</li>
<li><b>Given</b> a monthly 10:00 series in New York from 20 Oct, <b>then</b> the host sees 10:00 both months, and India sees 19:30, then 20:30.</li>
<li><b>Given</b> monthly from 31 Jan 2027, <b>then</b> 28 Feb, 31 Mar, 30 Apr; from 31 Jan 2028, 29 Feb.</li>
<li><b>Given</b> a time the clocks skip (02:30, 14 Mar 2027, New York), <b>then</b> <code>422</code>; a time that happens twice (01:30, 1 Nov 2026), <code>422</code> unless the offset is named.</li>
<li><b>Given</b> a first session that has already started by the server's clock, <b>then</b> <code>422</code>.</li>
<li><b>Given</b> <code>IST</code> or <code>+05:30</code> as a zone, a malformed date, or 10 minutes, <b>then</b> <code>400</code>; an unknown webinar, <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Store moments (<code>Instant</code>) and the host's zone; never a bare <code>LocalDateTime</code>.</li>
<li>Each session of a series is resolved on its own date in the host's zone.</li>
<li>Zones are region ids (<code>Asia/Kolkata</code>), never abbreviations or fixed offsets.</li>
<li>"Now" comes from an injected <code>Clock</code>.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Tell <code>Instant</code>, <code>LocalDateTime</code>, <code>ZonedDateTime</code> and <code>OffsetDateTime</code> apart and pick the right one.</li>
<li>Handle daylight saving gaps and overlaps on purpose.</li>
<li>Do date arithmetic in the right zone, and with month ends and leap years.</li>
<li>Test time-dependent code with a fixed <code>Clock</code>.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/webinars</code>", "Create: <code>title</code>, <code>startsAt</code> (host's wall-clock time, no offset), <code>zone</code>, <code>durationMinutes</code> (15 to 480), optional <code>repeat</code> (<code>NONE</code>, <code>MONTHLY</code>, <code>MONTHLY_LAST_WEEKDAY</code>) and <code>sessions</code> (1 to 12), optional <code>offset</code> for a time that happens twice."],
    ["<code>GET</code>", "<code>/webinars/{id}?viewerZone=Europe/London</code>", "Every session as <code>startsAt</code> (UTC), <code>hostTime</code> and <code>viewerTime</code>. Without <code>viewerZone</code>, the host's zone."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Created; <code>Location</code> points at it"],
    ['<span class="pill ok">200</span>', "The webinar, in the viewer's zone"],
    ['<span class="pill warn">400</span>', "Malformed body, an unknown zone (including <code>IST</code> and <code>+05:30</code>), duration or sessions out of range"],
    ['<span class="pill warn">404</span>', "No such webinar"],
    ['<span class="pill warn">422</span>', "Already started; a time skipped or repeated by daylight saving; a series that does not fit its rule"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-a-webinar-in-india", "Case 1: 10:00 on 5 Nov in Asia/Kolkata", "<b>Why:</b> stored as 04:30 UTC; shown to the host as 10:00+05:30."),
    ("02-seen-from-london", "Case 2: seen from London", "<b>Why:</b> 04:30 (London is on +00:00 in November). The old app said 10:00."),
    ("03-seen-from-los-angeles", "Case 3: seen from Los Angeles", "<b>Why:</b> 20:30 on 4 November, the evening before."),
    ("04-a-new-york-series-across-daylight-saving", "Case 4: monthly from 20 Oct, 10:00 New York", "<b>Why:</b> 10:00 both months for the host; the offset changes from −04:00 to −05:00."),
    ("05-the-series-seen-from-india", "Case 5: the series seen from India", "<b>Why:</b> 19:30, then 20:30: the moment moved, the host's 10:00 did not."),
    ("06-monthly-from-january-31", "Case 6: monthly from 31 January", "<b>Why:</b> each month's last day when the 31st does not exist, counted from the first date."),
    ("07-a-time-the-clocks-skip", "Case 7: 02:30 on 14 Mar 2027 in New York", "<b>Why:</b> clocks jump from 02:00 to 03:00: <code>422</code>."),
    ("08-a-time-that-happens-twice", "Case 8: 01:30 on 1 Nov 2026 in New York", "<b>Why:</b> clocks go back, so 01:30 happens at −04:00 and −05:00: <code>422</code> until an offset is sent."),
    ("09-ist-is-not-a-zone", "Case 9: zone \"IST\"", "<b>Why:</b> IST means India, Ireland or Israel: <code>400</code>."),
    ("10-no-such-webinar", "Case 10: webinar 99", "<b>Why:</b> <code>404</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Created in India, viewed in Los Angeles", "The evening before, 20:30", "<code>createdInTheHostZoneAndShownInAnyOther</code>"],
    ["Starts this minute, or the next", "<code>422</code>, then <code>201</code> (fixed Clock)", "<code>theFirstMinuteThatCountsIsTheClocks</code>"],
    ["A skipped time, US and UK", "<code>422</code>", "<code>aTimeTheClocksSkipIsRefused</code>"],
    ["A repeated time, with and without offset", "<code>422</code>; <code>201</code> with the right offset; <code>422</code> with a wrong one", "<code>aTimeThatHappensTwiceNeedsAnOffset</code>"],
    ["Monthly from the 31st; leap year", "Month ends kept; 29 Feb 2028", "<code>monthlyFromThe31stKeepsToTheMonthEnd</code>"],
    ["Last Friday of each month", "30 Oct, 27 Nov, 25 Dec; a date that is not the last Friday is <code>422</code>", "<code>lastFridayOfEachMonth</code>"],
    ["IST, +05:30, a non-ISO date, 10 minutes, 13 sessions, unknown repeat, bad viewer zone", "<code>400</code>", "<code>brokenRequestsAre400</code>"],
    ["Unknown webinar", "<code>404</code>", "<code>unknownWebinarsAre404</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Storing <code>LocalDateTime</code> without a zone, so times shift for other countries.</p>
<p>The old code is kept in the tests as <code>OldWebinarStore</code>, in both versions. The first stored <code>LocalDateTime</code>: asked for London, it can only answer 10:00, because the zone was never kept. The second stored an <code>Instant</code> but added months in UTC: a New York session at 10:00 on 20 October came back at 09:00 on 20 November, after the US left daylight saving. The fixed API runs the same two webinars and gets 04:30 for London, and 10:00 for the New York host in both months.</p>
<p>While building, each part was undone once. Adding 30 days instead of a month turned 2 tests red; dropping the "happens twice" check, 1; showing the host's time to the viewer, 3; repeating in UTC, 2; asking <code>Instant.now()</code> instead of the <code>Clock</code>, 1 (the fixed-clock test); accepting offsets and abbreviations as zones, 1.</p>
</div>
""" + code(read(T + "LocalDateTimeTrapTest.java"), "java") + code(read(T + "OldWebinarStore.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "WebinarController.java", dwn("Validates the body; accepts only region zone ids; reads <code>viewerZone</code>.", "Zones checked at the edge, with a reason.", "\"IST\" meaning three countries.")),
    (J + "Schedule.java", dwn("Turns each session's wall-clock time into a moment in the host's zone, and moments into anyone's time.",
        "One place knows about gaps, overlaps, month ends and the Clock.", "Times that shift abroad or at daylight saving.",
        "<ul><li><code>getValidOffsets</code> returns 0 offsets in a gap and 2 in an overlap; both are refused unless the client chose.</li><li>Monthly sessions are <code>startsAt.plusMonths(i)</code> from the first date, never chained: 31 Jan → 28 Feb → 31 Mar.</li><li><code>TemporalAdjusters.lastInMonth</code> finds the last Friday.</li></ul>")),
    (J + "WebinarsApplication.java", "<p>Entry point and the <code>Clock</code> bean (UTC); tests replace it.</p>"),
    ("src/main/resources/application.yaml", "<p>Problem details on; decimals refused for whole-number fields.</p>"),
]
tree = """stations/051-webinar-scheduling-across-time-zones/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/taskloom/webinars/
│   ├── WebinarController.java   ├── Schedule.java   └── WebinarsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/taskloom/webinars/   (see Tests)
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
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>; <code>@TestBean</code> needs Spring Framework 6.2 or later, which Boot 4 brings.</p>
<h2>Try it yourself</h2>
<p>In <code>Schedule</code>, replace <code>startsAt.plusMonths(i)</code> with <code>startsAt.plusDays(30L * i)</code> and run:</p>
""" + code("""./mvnw test -Dtest=WebinarContractTest#monthlyFromThe31stKeepsToTheMonthEnd""", "bash") + """
<p>"A month" is not 30 days: the sessions drift off the month end. Put it back.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["The same time shown in every country", "A <code>LocalDateTime</code> stored without a zone.", "Store an <code>Instant</code> and the host's zone."],
    ["A repeating session moves by an hour for its host", "Repeated in UTC (or by adding hours).", "Add months or weeks to the local time, then resolve in the host's zone."],
    ["<code>Unknown time zone</code> for <code>IST</code>", "Abbreviations are ambiguous and not region ids.", "Send <code>Asia/Kolkata</code>."],
    ["A test fails only after a certain date", "It asked the real clock.", "Inject a <code>Clock</code>; fix it in tests with <code>@TestBean</code>."],
    ["Feb 28, Mar 28, Apr 28 for a 31st-of-the-month series", "Months added to the previous session, not the first.", "<code>first.plusMonths(i)</code>."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>WebinarContractTest</code> ({cnt('WebinarContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>LocalDateTimeTrapTest</code> ({cnt('LocalDateTimeTrapTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>A clock the tests control</h2>
<p><code>ApiTest</code> replaces the app's <code>Clock</code> bean with <code>@TestBean</code>: "now" is 16 Oct 2026, 06:00 UTC, in every run. That is what lets one test say exactly which minute has started, and keeps the suite green next year.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "LocalDateTimeTrapTest.java", "<p>Written first: both old versions, and the same webinars through the fixed API.</p>"),
    (T + "WebinarContractTest.java", "<p>Zones, the Clock, gaps, overlaps, month ends, last Fridays, and every refusal.</p>"),
    (T + "OldWebinarStore.java", "<p>The old code, kept only in tests.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the fixed Clock and a webinar body.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/taskloom/webinars/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=WeeklyChallengeTest</code>.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solution copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Weekly webinars", "Beginner-friendly", 15,
    "Add <code>\"repeat\": \"WEEKLY\"</code>: same weekday, same wall-clock time for the host, every week. Across 1 Nov 2026 a New York series stays at 10:00 for the host and moves by an hour in India.",
    "the test in <code>WeeklyChallengeTest</code> passes.",
    ["<code>startsAt.plusWeeks(i)</code> on the local time, then resolve as for every session.",
     "Seven times 24 hours would be wrong in the week the clocks change."],
    "challenge/WeeklyChallengeTest.java", ["challenge/solution/Schedule.java"]) + challenge(2, "The viewer's day and end time", "Go deeper", 20,
    "Show each session's <code>viewerEndTime</code> (start plus duration, in the viewer's zone) and <code>viewerDayShift</code>: the viewer's date minus the host's (−1 for \"the evening before\").",
    "the test in <code>ViewerDayChallengeTest</code> passes.",
    ["Add the duration to the instant, then convert: never to a local time.",
     "<code>ChronoUnit.DAYS.between(hostDate, viewerDate)</code>."],
    "challenge/ViewerDayChallengeTest.java", ["challenge/solution/Schedule.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>When a country changes its clocks</h2>
<p>A government announces, six months ahead, that it will stop daylight saving. Webinars in that zone are already stored as instants. Which ones are now wrong, how would you find them, and would storing the host's local time and zone (and computing the instant later) have been better for future events?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test with both old versions.</li>
<li>Decide what the client sends (wall-clock time and zone) and what the server keeps (moment and zone).</li>
<li>Resolve every session on its own date; refuse gaps and overlaps unless the client is explicit.</li>
<li>Inject a <code>Clock</code>, and pin it in tests.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Store <code>Instant</code> + host zone; resolve each session in the zone", "Zone rule changes after creation are not followed.", '<span class="pill ok">Chosen</span>'],
    ["Store <code>LocalDateTime</code> only", "No moment at all: wrong for everyone elsewhere.", '<span class="pill bad">The trap</span>'],
    ["Store local time + zone; compute the instant on read", "Follows rule changes; every read recomputes, and sorting by moment needs care.", '<span class="pill warn">Better for far-future events</span>'],
    ["Store <code>OffsetDateTime</code>", "Keeps one offset; a series cannot follow daylight saving.", '<span class="pill warn">For past events</span>'],
    ["Silently shift gap times (Java's default)", "02:30 becomes 03:30 without anyone choosing it.", '<span class="pill warn">Surprising</span>']]) + """
<h2>Database design</h2>
<p>None in this station. In PostgreSQL, a moment is a <code>timestamptz</code> column (stored as UTC), and the host's zone a text column holding the region id. A <code>timestamp</code> column without time zone is this station's trap in SQL form.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Time zone data changes</dt><dd>Governments change their rules several times a year somewhere. The JDK ships the IANA time zone database; keep the JDK updated, or use the tzupdater tool between releases.</dd>
<dt>Servers run in UTC</dt><dd>Never rely on the server's default zone. Ask for a zone explicitly everywhere, as this code does.</dd>
<dt>Show offsets</dt><dd>Times sent to clients carry their offset, so no client has to guess.</dd>
<dt>One clock</dt><dd>Code that asks the real clock directly cannot be tested at midnight, at month end or on 29 February. Inject a <code>Clock</code>.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Instant, LocalDateTime, ZonedDateTime, OffsetDateTime: when each?", "Instant for a moment (storage, logs). LocalDateTime for a wall-clock reading with no place (what a user types). ZonedDateTime for a moment in a region with rules, for arithmetic across daylight saving. OffsetDateTime for a moment with a fixed offset, for sending over the wire."),
    ("What happens with 02:30 on a spring-forward night?", "It does not exist. getValidOffsets returns nothing; ZonedDateTime.of would silently move it forward. Decide: refuse it, or move it on purpose."),
    ("Why not add 24 hours to get tomorrow at the same time?", "On a daylight saving day, a day is 23 or 25 hours. Add a day to the local date-time, then resolve it in the zone."),
    ("How do you test code that depends on the current time?", "Inject java.time.Clock and call LocalDate.now(clock) or clock.instant(). In tests, use Clock.fixed, here through Spring's @TestBean."),
    ("What is Jan 31 plus one month?", "Feb 28 (29 in a leap year): plusMonths clamps to the month end. Always add from the original date for a series, or you get stuck on the 28th."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You broke the month arithmetic and watched it fail."],
    ["Types", "The right java.time type at each step.", "You can explain why the response carries offsets."],
    ["Daylight saving", "Gaps and overlaps refused.", "You can argue for refusing vs shifting."],
    ["Testing", "A fixed Clock.", "No test depends on today's date."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any code with dates and times:</p>
<ul class="rules">
<li>Is there a <code>LocalDateTime</code> stored or sent without a zone?</li>
<li>Is date arithmetic done in the zone that the rule belongs to?</li>
<li>What does the code do at 02:30 on a spring-forward night?</li>
<li>Does anything call <code>now()</code> without a <code>Clock</code>?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
