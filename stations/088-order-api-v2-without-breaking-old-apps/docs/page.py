"""Station 088 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 88,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Framework 7 API versioning · Deprecation (RFC 9745) and Sunset (RFC 8594) headers · Jackson 3",
    "simulation": "The orders are two demo orders kept in memory, not Kartwala's; the \"old app\" is a model class in the tests that reads JSON the way an app release would. The migration guide link is an example address.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/kartwala/orders/"
T = "src/test/java/com/kartwala/orders/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("API version", "A fixed shape of answers that clients can rely on.", "An edition of a timetable.", "<code>/v1</code>, <code>/v2</code>"),
    ("Breaking change", "A change that makes an existing client fail or show wrong data: renaming, removing, changing a type or meaning.", "Renumbering every bus route overnight.", "<code>customerName</code> to <code>customer.name</code>"),
    ("Compatible change", "A change existing clients do not notice, such as a new field, if they ignore fields they do not know.", "A new bus stop on the route.", "<code>trackingUrl</code> added to v1"),
    ("Tolerant reader", "A client that reads only the fields it needs and ignores the rest.", "Reading only your own stop on the timetable.", "<code>@JsonIgnoreProperties(ignoreUnknown = true)</code>"),
    ("Deprecation", "A notice that a version will go away; it still works.", "\"This timetable ends in April.\"", "<code>Deprecation</code> header"),
    ("Sunset", "The date a version stops working.", "The last day the old timetable runs.", "<code>Sunset</code> header"),
]
STORY = [
    ("A tidy rename", "Kartwala's team cleaned up the order API: customerName became customer.name, qty became quantity, the total moved to paise. The new app used the new names. It shipped on a Friday."),
    ("Two days of broken orders", "30% of users still had app 5.x. Its order screen read the old names, found nothing, and crashed. Users cannot be forced to update, and app store reviews take days."),
    ("The fix", "The old shape comes back as v1, frozen, and the new shape is v2 beside it. v1 tells clients it is deprecated and when it ends. Old apps keep working until that date."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">You cannot update the apps in people's pockets. Never rename, remove or change the meaning of a field in place: add a version.</p>

<h2>What are we building?</h2>
<p>One order, two shapes: <code>/v1</code> exactly as old apps read it, <code>/v2</code> with the new names, side by side, with v1 announcing its end date.</p>

<h2>An everyday analogy</h2>
<p>A city changes its bus numbers. It does not repaint every stop overnight: old and new numbers are shown together for months, with a notice saying when the old ones go.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Freeze v1</strong>: its names, types and values stay as old apps read them.</li>
<li><strong>Add v2</strong> beside it with the new shape; both read the same order.</li>
<li><strong>Announce</strong> on every v1 answer: deprecated since, ends on, where to read how to move.</li>
<li><strong>Only add</strong> to a version afterwards, never rename or remove; clients ignore what they do not know.</li>
</ol>

<details class="qa check"><summary>Check yourself: v1 sends total as rupees (1299.50). Is sending it in paise (129950) under the same name a compatible change?</summary><p>No. The name and the type look the same, but the meaning changed: old apps would show ₹1,29,950 without any error. That is the flawed version in the Review tab.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No database.</strong> Two demo orders in memory: this station is about the API's shape.</li>
<li><strong>No writes.</strong> Only reading orders; versioning a write is challenge 3.</li>
<li><strong>No real app.</strong> The \"old app\" is a model class in the tests that reads JSON like the app did.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Kartwala</strong> (a fictional shopping app): renaming a field broke 30% of users on old app versions for two days.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo dates: v1 deprecated from 1 Oct 2026 and ends on 1 Apr 2027 (midnight IST).</p>
<ol class="gwt">
<li><b>Given</b> <code>/v1/orders/{id}</code>, <b>then</b> exactly the fields, types and values app 5.x reads, plus fields added since.</li>
<li><b>Given</b> <code>/v2/orders/{id}</code>, <b>then</b> the new shape: customer object, paise, lower-case states.</li>
<li><b>Given</b> any v1 answer, <b>then</b> <code>Deprecation</code>, <code>Sunset</code> and a <code>Link</code> to the migration guide; v2 has none.</li>
<li><b>Given</b> an unknown order, <b>then</b> <code>404</code>; a non-numeric id or an unknown version, <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>One order model; one response shape per version, built from it.</li>
<li>A test reads v1 the way the old app does.</li>
<li>Money in v1 stays an exact decimal of rupees, from paise, never through a <code>double</code>.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Tell breaking changes from compatible ones, including changes of meaning.</li>
<li>Use Spring Framework 7's API versioning on paths.</li>
<li>Announce deprecation and sunset with standard headers, citing their status.</li>
<li>Write clients and tests as tolerant readers.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/v1/orders/{id}</code>", "The frozen v1 shape, deprecated, with its end date."],
    ["<code>GET</code>", "<code>/v2/orders/{id}</code>", "The new shape."]]) + """
<h2>Headers on v1</h2>
""" + table(["Header", "Meaning", "Standard"], [
    ["<code>Deprecation: @1790793000</code>", "Deprecated since this moment (seconds since 1970: 1 Oct 2026, 00:00 IST).", "RFC 9745, Proposed Standard (2025)"],
    ["<code>Sunset: Wed, 31 Mar 2027 18:30:00 GMT</code>", "Stops working at this moment (1 Apr 2027, 00:00 IST).", "RFC 8594, Informational (2019)"],
    ["<code>Link: &lt;...&gt;; rel=\"deprecation\"</code>", "Where to read how to move to v2.", "RFC 9745"]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "The order, in the version asked for"],
    ['<span class="pill warn">400</span>', "An id that is not a number; a version that does not exist"],
    ['<span class="pill warn">404</span>', "No such order; a path that does not exist"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-v1-the-shape-old-apps-read", "Case 1: v1", "<b>Why:</b> the old names, rupees as an exact decimal, and the three deprecation headers."),
    ("02-v2-the-new-shape", "Case 2: v2", "<b>Why:</b> the same order in the new shape; no deprecation headers."),
    ("03-v2-an-order-not-shipped-yet", "Case 3: v2, an order not shipped yet", "<b>Why:</b> <code>trackingUrl</code> is <code>null</code>: present, so clients can rely on the field."),
    ("04-a-version-that-does-not-exist", "Case 4: /v3", "<b>Why:</b> Spring answers <code>400</code> for a version no endpoint has."),
    ("05-v1-an-unknown-order", "Case 5: v1, an unknown order", "<b>Why:</b> <code>404</code>, still with the deprecation headers."),
    ("06-v2-an-id-that-is-not-a-number", "Case 6: v2, a non-numeric id", "<b>Why:</b> <code>400</code>."),
    ("07-v1-0-is-version-1-too", "Case 7: /v1.0", "<b>Why:</b> Spring's version parser reads <code>v1</code>, <code>1</code> and <code>v1.0</code> as the same version."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["v1, field by field", "Exactly the old shape", "<code>v1KeepsTheShapeOldAppsParse</code>"],
    ["v2, field by field; an order not shipped", "The new shape; <code>trackingUrl</code> null", "<code>v2HasTheNewShape</code>"],
    ["Deprecation headers", "On v1 only, with the dates in standard form", "<code>v1IsMarkedDeprecatedWithItsEndDateAndV2IsNot</code>"],
    ["Unknown order, bad id, /v3, a trailing slash", "<code>404</code>, <code>400</code>, <code>400</code>, <code>404</code>", "<code>unknownOrdersAre404AndBadIdsOrVersionsAre400</code>"],
    ["The old app reads the renamed shape", "It fails; a lenient reader shows no customer, no total", "<code>theRenamedShapeIsWhatBrokeTheOldApp</code>"],
    ["The old app reads v1", "Every field it knows, exactly", "<code>theOldAppStillReadsV1Completely</code>"],
    ["A field added to v1", "Fine for a tolerant reader, fatal for a strict one", "<code>anAddedFieldIsCompatibleOnlyForATolerantReader</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Renaming or removing fields in place, breaking old app versions.</p>
<ul>
<li><strong>The rename.</strong> The test reads the new shape with app 5.x's own model. Jackson 3 refuses it: <code>qty</code> became <code>quantity</code>, and a missing <code>int</code> is an error. That is the crash. Even a reader that lets it pass shows an order with no customer and no total.</li>
<li><strong>v1 today.</strong> The same model reads <code>/v1</code> completely, value for value.</li>
<li><strong>Adding is compatible, for tolerant readers.</strong> <code>trackingUrl</code> was added to v1 later. A model that ignores unknown fields reads it; a strict one fails. Write clients the first way.</li>
</ul>
<p>While building, each part was undone once: a v1 field renamed turned 3 tests red; v1's total in paise 2; v1's status in lower case 2; a v1 field removed 1; no deprecation headers 1; the Sunset date in IST 1; v2's status in upper case 1.</p>
</div>
""" + code(read(T + "RenameInPlaceTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "ApiVersions.java", dwn("Versioning and deprecation, in one place.",
        "The version is the first path segment; v1 gets Deprecation, Sunset and Link headers from Spring's <code>StandardApiVersionDeprecationHandler</code>.",
        "Version checks spread through controllers; deprecation only in a blog post.",
        "<p>The Sunset date is configured in UTC. Given in IST, Spring wrote <code>+0530</code> into the header, but an HTTP date is written in GMT. Found while building.</p>")),
    (J + "OrderController.java", dwn("One record per version, built from one order.",
        "<code>@GetMapping(..., version = \"1\")</code> and <code>version = \"2\"</code> on the same path pattern.",
        "One shape changed for everyone at once.",
        "<ul><li>v1 is frozen: it may gain fields, never lose, rename or change one.</li><li>v1's rupees are <code>BigDecimal.valueOf(paise, 2)</code>: exact.</li></ul>")),
    (J + "Orders.java", "<p>The order model and two demo orders, shared by both versions.</p>"),
    ("src/main/resources/application.yaml", "<p>Problem details for errors.</p>"),
    (J + "OrdersApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/088-order-api-v2-without-breaking-old-apps/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/kartwala/orders/
│   ├── ApiVersions.java   ├── OrderController.java   ├── Orders.java   └── OrdersApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/kartwala/orders/   (see Tests)
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
<p>Ask for the same order in both versions and compare:</p>
""" + code("""curl -s http://localhost:8080/v1/orders/1002; echo
curl -s http://localhost:8080/v2/orders/1002; echo""", "bash") + """
<p>The answers, as <code>docs/capture.sh</code> saved them: the same order, the old names and rupees in v1, the new shape in v2.</p>
""" + code(read("docs/captures/try-1002.txt").strip(), "text") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>Invalid API version: '3.0.0'.</code>", "No endpoint declares that version.", "Use <code>/v1</code> or <code>/v2</code>."],
    ["<code>Sunset</code> with <code>+0530</code> in it", "The sunset date was given with a time zone; Spring prints its offset.", "Give the date in UTC, as <code>ApiVersions</code> does."],
    ["An old client fails on a new field", "It is a strict reader.", "Ignore unknown fields in clients (<code>@JsonIgnoreProperties(ignoreUnknown = true)</code>)."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">Configuration first, then the request's path.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>OrderContractTest</code> ({cnt('OrderContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>RenameInPlaceTrapTest</code> ({cnt('RenameInPlaceTrapTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">The contract tests compare whole bodies in strict mode, so a removed or renamed field fails them. The trap test was first written expecting an empty name; the real old-app model failed harder, on the renamed <code>qty</code>, and the test now checks that. Found while building.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "RenameInPlaceTrapTest.java", "<p>Written first: the old app's model reading the renamed shape, v1, and a field added later.</p>"),
    (T + "OrderContractTest.java", "<p>Both versions field by field, the deprecation headers, errors.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/kartwala/orders/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=SunsetChallengeTest</code>.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "After the sunset", "Beginner-friendly", 20,
    "From 1 Apr 2027, 00:00 IST, <code>/v1</code> answers <code>410 Gone</code> with a link to the migration guide; <code>/v2</code> carries on.",
    "the test in <code>SunsetChallengeTest</code> passes.",
    ["Add a <code>Clock</code> bean and compare with <code>ApiVersions.V1_SUNSET</code>.",
     "The deprecation handler still adds its <code>Link</code> header to the <code>410</code>."],
    "challenge/SunsetChallengeTest.java", ["challenge/solution/OrderController.java", "challenge/solution/OrdersApplication.java"]) + challenge(2, "Dated versions", "Go deeper", 35,
    "<code>GET /orders/{id}</code> with <code>Kartwala-Version: 2026-10-01</code>: the shape current on that date, as Stripe names its versions. Before 1 Oct 2026, the v1 shape; from then, v2. No date, or not a date, <code>400</code>.",
    "both tests in <code>DatedVersionChallengeTest</code> pass.",
    ["The path versioning must now apply only to paths starting with <code>/v</code>: <code>usePathSegment(0, predicate)</code>, and a version is no longer required everywhere.",
     "Reuse the v1 and v2 shapes; the date only picks one."],
    "challenge/DatedVersionChallengeTest.java", ["challenge/solution/OrderController.java", "challenge/solution/ApiVersions.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Writes, and the end of v1</h2>
<p>Add <code>POST /v2/orders</code>. What does an old app sending a v1-shaped body need: a separate v1 endpoint, or a translation into the one model? Then plan v1's end: how do you learn who still calls it (logs by app version), when is it safe to switch it off, and what should the app show users who never update?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old app's model against the renamed shape and against v1.</li>
<li>Configure path-segment versioning and the deprecation handler.</li>
<li>Write one record per version, both built from the same order.</li>
<li>Compare whole bodies strictly in contract tests, so any rename shows.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Version in the path (<code>/v1</code>, <code>/v2</code>)", "Visible, easy to cache and log; URLs change between versions.", '<span class="pill ok">Chosen</span>'],
    ["Version in a header (<code>API-Version: 2</code>)", "Clean URLs; easy to forget, harder to see in logs.", '<span class="pill warn">Also fine</span>'],
    ["Version in the media type (<code>application/json;v=2</code>)", "Fits HTTP content negotiation; clumsy for most clients.", '<span class="pill warn">Rarely worth it</span>'],
    ["Dated versions (Stripe)", "Many small changes, each with a date; a translation layer to keep.", '<span class="pill warn">Challenge 2</span>'],
    ["Rename in place", "Old apps break the day it ships.", '<span class="pill bad">The trap</span>']]) + """
<h2>Database design</h2>
<p>This station has no database: the versions are a question of the API's shape, not of storage. The point that carries over: a database column can be renamed in one migration; an API field cannot, because its readers are outside your control.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Who still calls v1</dt><dd>Log requests by version and app version; switch v1 off when its traffic is small enough to accept, not on a date alone.</dd>
<dt>Force updates carefully</dt><dd>A minimum supported app version (station 089) lets the app tell users to update before v1 ends.</dd>
<dt>Contract tests</dt><dd>Keep a copy of what each released app reads, and test v1 against it on every build.</dd>
<dt>Standards</dt><dd>RFC 9745 (Deprecation, Proposed Standard, 2025) and RFC 8594 (Sunset, Informational, 2019). Many clients ignore these headers: they help tools and partners, not users.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Which changes are breaking?", "Renaming or removing a field, changing its type, changing its meaning (rupees to paise under one name), changing allowed values, and making an optional input required."),
    ("Is adding a field safe for every client?", "Only for tolerant readers that ignore unknown fields. A strict client fails on it, which is why clients should be tolerant."),
    ("How does Spring Framework 7 version APIs?", "A version attribute on mappings and an ApiVersionConfigurer that reads the version from a path segment, a header, a query parameter or a media type, with a deprecation handler for headers."),
    ("What do Deprecation and Sunset say?", "Deprecation: since when the version is deprecated (RFC 9745). Sunset: when it stops working (RFC 8594). A Link with rel=\"deprecation\" points to the guide."),
    ("How long do you keep v1?", "Until the apps and partners that use it have moved, measured by traffic, with a date announced well ahead."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Compatibility", "v1 unchanged.", "You can name changes of meaning that look compatible."],
    ["Deprecation", "Headers on v1.", "Dates in the right format, the standards with their status."],
    ["Tests", "Contract tests.", "A test that reads answers the way an old app does."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("v1's total in paise, under the same name",
     "\"Money is integer paise everywhere\" is right for new APIs, wrong for a frozen one. The name and the JSON type (a number) are unchanged, so nothing fails: app 5.x shows ₹1,29,950 for a ₹1,299.50 order. Item prices too.",
     "<code>v1KeepsTheShapeOldAppsParse</code> and <code>theOldAppStillReadsV1Completely</code> fail."),
    ("v1's states in lower case",
     "\"One way to write states\": app 5.x compares <code>status</code> with <code>SHIPPED</code>, so every order now looks like an unknown state.",
     "The same two tests fail on <code>status</code> as well."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate makes the versions consistent: money as integer paise in both, and states written in lower case in both, \"so we have one rule\". No field is renamed or removed. Read the file and list every problem before opening the findings.</p>
<p class="path">review/OrderController.java</p>
""" + code(read("review/OrderController.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">No field was renamed, so a check of names alone passes. The breakage is in the values: worse than a crash, because the old app shows a wrong price without any error.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
