"""Station 090 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""
import json as _json

META = {
    "id": 90,
    "stack": "Spring Boot 4.1.1 · Java 25 · OpenAPI 3.1 · springdoc-openapi 3.1.1 · documented errors and examples, tested against the API",
    "simulation": "The tariff, zones and the list of PIN codes not served are demo rules, not Dakroute's. A quote is a price: nothing is booked or shipped. The partner server and support addresses are examples.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/dakroute/rates/"
T = "src/test/java/com/dakroute/rates/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]
SPEC = _json.loads(read("docs/captures/api-docs.json"))
REQUIRED = ", ".join(SPEC["components"]["schemas"]["QuoteRequest"]["required"])
SCHEMA = _json.dumps(SPEC["components"]["schemas"]["QuoteRequest"], indent=2)

# ---------- Level 1: Understand ----------
TERMS = [
    ("API docs", "The description partners read to call your API: paths, fields, errors, examples.", "The manual for a machine.", "<code>GET /v3/api-docs</code>"),
    ("OpenAPI", "A standard format for describing HTTP APIs, readable by people and tools.", "A standard wiring diagram any electrician can read.", "OpenAPI 3.1"),
    ("springdoc-openapi", "A library that builds the OpenAPI description from Spring code.", "A manual printed from the machine's own blueprint.", "version 3.1.1"),
    ("Example", "A real request or answer shown in the docs.", "A filled-in sample form.", "<code>@ExampleObject</code>"),
    ("Drift", "Docs and API slowly saying different things.", "A map of a town that kept building.", "the old PDF"),
    ("Contract review", "Looking at every change to the API description before it ships.", "Checking the new map before it is printed.", "<code>approved.json</code>"),
]
STORY = [
    ("A PDF from two releases ago", "Dakroute's partners integrate from a PDF someone wrote by hand. It says weight_kg and origin; the API takes weightGrams and fromPincode."),
    ("200 tickets a month", "Every partner who copies the PDF's example gets 400, writes to support, and waits. Nobody updated the PDF when the API changed, because nothing made them."),
    ("The fix", "The docs are generated from the code, with the errors and examples in it, and a test sends every example to the API and compares the answers. A change to the docs shows as a diff to review."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Docs that nothing checks will drift. Generate them from the code and test them against the API.</p>

<h2>What are we building?</h2>
<p>A rate-quote endpoint whose OpenAPI description is generated from the code, documents every error with an example, and is tested so that every example really works.</p>

<h2>An everyday analogy</h2>
<p>A recipe printed straight from the kitchen's own cards, and tasted: every recipe in the book is cooked once before the book is printed.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Describe in code</strong>: field limits come from the validation annotations, descriptions and examples from annotations next to them.</li>
<li><strong>Generate</strong>: springdoc serves the description at <code>/v3/api-docs</code>.</li>
<li><strong>Test it</strong>: every example is sent; every documented answer is compared with the real one.</li>
<li><strong>Review it</strong>: the description is compared with an approved copy; a change shows as a diff in the pull request.</li>
</ol>

<details class="qa check"><summary>Check yourself: the docs are generated from the code. Can they still be wrong?</summary><p>Yes. springdoc first said <code>weightGrams</code> was optional, because it only knows <code>@NotNull</code>, while the API refused a request without it. The test that removes each field found it: see Tests.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No docs website.</strong> The description is JSON; Swagger UI or Redoc can show it (one more dependency).</li>
<li><strong>No real tariff.</strong> Zones and prices are demo rules.</li>
<li><strong>No booking.</strong> A quote is a price.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Dakroute</strong> (a fictional courier): partners integrate from a stale PDF and open 200 tickets a month.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo tariff: same first three PIN digits LOCAL (₹40 per started 500 g), same first two REGIONAL (₹55), else NATIONAL (₹75); EXPRESS half as much again; chargeable weight is the larger of actual and volumetric (L×W×H cm / 5, in grams); GST 18%; at most 50 kg; PIN codes 744101 and 194101 not served.</p>
<ol class="gwt">
<li><b>Given</b> a valid parcel, <b>then</b> <code>200</code> with the zone, chargeable weight, price, GST and total in paise.</li>
<li><b>Given</b> invalid input, <b>then</b> <code>400</code>; a parcel the network cannot carry, <code>422</code>.</li>
<li><b>Given</b> <code>/v3/api-docs</code>, <b>then</b> an OpenAPI description with every field's limits, every error, and examples.</li>
<li><b>Given</b> any example in the docs, <b>then</b> sending it gets the documented status and answer.</li>
<li><b>Given</b> a change to the API, <b>then</b> the description differs from the approved copy until someone reviews and approves it.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>No hand-written docs that can disagree with the code.</li>
<li>Errors documented with examples, not only the happy path.</li>
<li>The docs' required fields are exactly the ones the API refuses without.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Generate OpenAPI with springdoc and enrich it with annotations.</li>
<li>Document errors and examples that are true.</li>
<li>Test docs against the API instead of trusting them.</li>
<li>Review API changes as diffs of the description.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/rate-quotes</code>", "Price one parcel between two PIN codes."],
    ["<code>GET</code>", "<code>/v3/api-docs</code>", "The OpenAPI description, generated from the code."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "The quote; the description"],
    ['<span class="pill warn">400</span>', "A field missing, of the wrong type, or out of range"],
    ['<span class="pill warn">422</span>', "Valid, but the network cannot carry it: over 50 kg, or a PIN code not served"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-a-parcel-bengaluru-to-delhi", "Case 1: 1.2 kg, Bengaluru to Delhi", "<b>Why:</b> NATIONAL, 3 started slabs of 500 g: ₹225 + ₹40.50 GST."),
    ("02-light-but-bulky-express-in-bengaluru", "Case 2: 800 g but 60×40×40 cm, EXPRESS, within Bengaluru", "<b>Why:</b> the volumetric weight, 19.2 kg, is charged."),
    ("03-too-heavy", "Case 3: 62 kg", "<b>Why:</b> valid input the network cannot carry: <code>422</code>."),
    ("04-a-pin-code-not-served", "Case 4: to 744101", "<b>Why:</b> not served yet: <code>422</code>."),
    ("05-a-five-digit-pin-code", "Case 5: a five-digit PIN code", "<b>Why:</b> <code>400</code>."),
    ("06-the-old-pdfs-example", "Case 6: the old PDF's example", "<b>Why:</b> its field names no longer exist: <code>400</code>, the ticket partners kept opening."),
]) + """
<h2>The generated description</h2>
<p class="muted">From <code>docs/captures/api-docs.json</code>, fetched from the running app (""" + read("docs/captures/api-docs-status.txt").strip() + """). The request schema, as partners see it:</p>
""" + code(SCHEMA, "json")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A national parcel", "Slabs, GST, total", "<code>aNationalParcelIsPricedBySlabWithGst</code>"],
    ["Local, regional, volumetric, express, a started slab", "Priced by the demo tariff", "<code>zonesVolumetricWeightAndExpress</code>"],
    ["GST with a fraction of a paisa", "Rounded to the nearest paisa", "<code>gstIsRoundedToTheNearestPaisa</code>"],
    ["50 kg; 50.001 kg; a PIN code not served", "<code>200</code>; <code>422</code>; <code>422</code>", "<code>whatTheNetworkCannotCarryIs422</code>"],
    ["Bad PIN codes, zero weight, 151 cm, unknown service, a fraction", "<code>400</code>", "<code>badRequestsAre400</code>"],
    ["The old PDF's example", "<code>400</code>", "<code>thePdfsExampleIsRefusedByTheRealApi</code>"],
    ["Every example in the docs", "Gets its documented status", "<code>everyRequestExampleGetsTheStatusTheDocsGiveIt</code>"],
    ["Every documented answer", "Matches the real one", "<code>everyDocumentedAnswerMatchesTheRealOne</code>"],
    ["Each field removed in turn", "<code>400</code> exactly when the docs say required", "<code>theFieldsTheDocsCallRequiredAreExactlyTheOnesTheApiRefusesWithout</code>"],
    ["Any change to the description", "Fails until the approved copy is updated", "<code>theDescriptionMatchesTheApprovedCopy</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Hand-written docs that drift from the real API.</p>
<ul>
<li><strong>The PDF.</strong> The test sends the PDF's own example to the API: <code>400</code>. Nothing ever checked the PDF, so nothing noticed.</li>
<li><strong>Generated docs.</strong> The description's request schema has exactly the fields the API takes, with the PIN code pattern and the size limits from the validation annotations.</li>
<li><strong>Generated is not enough.</strong> The generated docs were wrong twice while building (see Tests). Only the tests that send the examples and compare the answers caught it.</li>
</ul>
<p>While building, each part was undone once: an int field not marked required in the docs turned 2 tests red; a wrong total in a documented example 2; a field renamed 7; the weight limit changed 3; another volumetric divisor 1; GST cut instead of rounded 1; no LOCAL zone 1; no rounding up to a started slab 3.</p>
</div>
""" + code(read(T + "HandWrittenDocsTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "RateQuoteController.java", dwn("The endpoint, and most of its docs.",
        "Validation annotations become the docs' patterns and limits; <code>@Schema</code> adds descriptions and examples; <code>@Operation</code>, <code>@ApiResponse</code> and named <code>@ExampleObject</code>s document 200, 400 and 422.",
        "Partners guessing field names, units and errors.",
        "<ul><li>The int fields carry <code>requiredMode = REQUIRED</code> by hand: springdoc marks only <code>@NotNull</code> fields required, but Jackson 3 refuses a missing <code>int</code>. Found by a test while building.</li><li>Request and answer examples share a name, so a test can pair them and send one to check the other.</li><li>The error examples have no <code>type</code> field: Spring does not send <code>about:blank</code>. The first version had it; a test caught it.</li></ul>")),
    (J + "RateCard.java", dwn("The demo tariff.", "Zones, volumetric weight, slabs, express, GST, days.", "Prices computed differently in different places.")),
    (J + "RatesApplication.java", dwn("Entry point, and the parts of the docs not in the code.", "Title, version, contact and the partner server address.", "Docs that point partners at <code>localhost</code>.")),
    ("src/test/resources/openapi/approved.json", "<p>The approved description. A change to the API changes the generated one; the test fails and writes the new one to <code>target/openapi-generated.json</code>, to diff and approve in the pull request.</p>"),
    ("src/main/resources/application.yaml", "<p>Problem details for errors; fractions refused for whole-number fields.</p>"),
    ("pom.xml", "<p><code>springdoc-openapi-starter-webmvc-api</code> 3.1.1, the line for Spring Boot 4 (built against 4.1.0). The <code>-ui</code> starter would add Swagger UI.</p>"),
]
tree = """stations/090-partner-shipping-rate-api-docs/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/dakroute/rates/
│   ├── RateQuoteController.java   ├── RateCard.java   └── RatesApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/dakroute/rates/   (see Tests)
├── src/test/resources/openapi/approved.json
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
""" + code("""./mvnw spring-boot:run      # the API on http://localhost:8080, the docs at /v3/api-docs
./mvnw test                 # all """ + str(N_TESTS) + """ tests""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Ask the docs which fields are required:</p>
""" + code("""curl -s http://localhost:8080/v3/api-docs | python3 -c "import json,sys; print(json.load(sys.stdin)['components']['schemas']['QuoteRequest']['required'])\"""", "bash") + """
<p>It prints <code>[""" + ", ".join(f"'{f}'" for f in SPEC["components"]["schemas"]["QuoteRequest"]["required"]) + """]</code> (read from the captured description). Then remove <code>requiredMode = Schema.RequiredMode.REQUIRED</code> from <code>weightGrams</code>, restart, ask again, and run <code>./mvnw test</code>: two tests fail and <code>target/openapi-generated.json</code> shows the change.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>theDescriptionMatchesTheApprovedCopy</code> fails", "The API's description changed, on purpose or not.", "Diff <code>target/openapi-generated.json</code> with <code>approved.json</code>; if the change is right, copy it over in the same pull request."],
    ["A primitive field shown as optional", "springdoc only marks <code>@NotNull</code> fields required.", "Add <code>requiredMode = REQUIRED</code> to its <code>@Schema</code>."],
    ["A documented answer does not match the real one", "The example was written by hand and is wrong.", "Copy the real answer into the example; the test will hold it."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">The endpoint and its docs first, then the tariff and the approved description.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>RateQuoteContractTest</code> ({cnt('RateQuoteContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>HandWrittenDocsTrapTest</code> ({cnt('HandWrittenDocsTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "The docs tested against the API", f"<code>OpenApiDocsTest</code> ({cnt('OpenApiDocsTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">Two of these tests failed on the first generated docs, for real reasons: the required-fields test found <code>weightGrams</code> and the sizes marked optional, and the documented-answer test found a <code>type</code> field Spring does not send. Both were fixed in the code; the approved copy was then taken from the generated description. Found while building.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, springdoc-openapi 3.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "HandWrittenDocsTrapTest.java", "<p>Written first: the PDF's example against the real API, and the generated schema's fields.</p>"),
    (T + "OpenApiDocsTest.java", "<p>Examples sent, answers compared, required fields checked, the approved copy compared.</p>"),
    (T + "RateQuoteContractTest.java", "<p>The tariff and the errors through HTTP.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: request helpers and the generated description.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/dakroute/rates/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=NotServedExampleChallengeTest</code>.</li>
<li>Change the code until it passes. Both challenges change the description, so <code>theDescriptionMatchesTheApprovedCopy</code> fails next: review <code>target/openapi-generated.json</code> and copy it over <code>approved.json</code>. Then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, including their approved description (<code>challenge/solution/test-resources/</code>), all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Document the second 422", "Beginner-friendly", 20,
    "Add a request example named <code>not-served</code> (a parcel to 744101) and a <code>422</code> answer example with the same name. <code>OpenApiDocsTest</code> then sends it and checks the answer.",
    "the test in <code>NotServedExampleChallengeTest</code> passes, and so does <code>OpenApiDocsTest</code> after you approve the new description.",
    ["<code>examples</code> takes a list: <code>examples = {@ExampleObject(...), @ExampleObject(...)}</code>.",
     "Copy the real answer from a <code>curl</code>, not from memory."],
    "challenge/NotServedExampleChallengeTest.java", ["challenge/solution/RateQuoteController.java", "challenge/solution/test-resources/openapi/approved.json"]) + challenge(2, "Name the wrong field", "Go deeper", 35,
    "Partners still sending the old PDF's body get told which field is wrong: an unknown field by name (<code>Unknown field 'cod'</code>), a missing or mistyped one too, with where the docs are. Document it with a request example <code>from-the-old-pdf</code> and its <code>400</code>.",
    "both tests in <code>UnknownFieldChallengeTest</code> pass.",
    ["Refuse unknown fields: <code>spring.jackson.deserialization.fail-on-unknown-properties=true</code>, then name the field from the exception's path in an <code>@ExceptionHandler</code>.",
     "For a record, Jackson 3 reports a missing number before an unknown field: the PDF's body is answered about <code>weightGrams</code>. Found while writing the solution."],
    "challenge/UnknownFieldChallengeTest.java", ["challenge/solution/RateQuoteController.java", "challenge/solution/application.properties", "challenge/solution/test-resources/openapi/approved.json"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Publishing to partners</h2>
<p>Partners need the docs where they work: a docs site, a downloadable file, maybe generated client libraries. Design how the approved description is published on each release, how partners learn what changed (a changelog made from the diff), and how a breaking change is announced long enough before it ships (station 088).</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the PDF's example against the API.</li>
<li>Write the endpoint with validation annotations; add springdoc; add descriptions, errors and named examples.</li>
<li>Write the tests that send the examples, compare answers and check required fields.</li>
<li>Approve the description and test against the approved copy.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Code first: generated from annotations, tested", "Annotations next to the code; the tests to keep them true.", '<span class="pill ok">Chosen</span>'],
    ["Hand-written docs (PDF, wiki)", "Drift, and nothing notices.", '<span class="pill bad">The trap</span>'],
    ["Design first: write the OpenAPI file, generate code from it", "The contract is agreed before code; generators and their output to maintain.", '<span class="pill warn">Good for many teams</span>'],
    ["Generated, untested", "Better than a PDF; still wrong where the library guesses (required ints here).", '<span class="pill warn">Not enough</span>']]) + """
<h2>Database design</h2>
<p>This station has no database: a quote is computed, not stored. The same approach documents any table-backed API.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Exposure</dt><dd>Decide whether <code>/v3/api-docs</code> is public. Internal endpoints should not appear in partner docs; springdoc can group or hide them.</dd>
<dt>Review</dt><dd>The approved copy turns every API change into a diff in the pull request: the moment to ask \"is this breaking?\".</dd>
<dt>Tooling</dt><dd>OpenAPI feeds linters, mock servers, client generators and API gateways; a true description pays off many times.</dd>
<dt>Support</dt><dd>Name the wrong field in errors (challenge 2): it turns tickets into self-service.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Code first or design first?", "Code first generates the description from the code, so it follows the code; design first agrees the contract before coding. Either way, test the description against the running API."),
    ("Where do field limits in the docs come from?", "springdoc reads the Bean Validation annotations (pattern, min, max, not null) and @Schema; anything it cannot know, such as Jackson refusing a missing int, must be added."),
    ("How do you stop docs from drifting?", "Generate them, send every example in a test, compare documented answers with real ones, and review the description's diff on every change."),
    ("Why document errors?", "Partners spend most of their integration time on errors. Each error needs its status, when it happens and an example."),
    ("What is contract review?", "Looking at the change to the API description in the pull request, before it ships, to catch breaking or accidental changes."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Docs", "Generated docs.", "Errors and examples documented, and true."],
    ["Tests", "The endpoint is tested.", "The docs are tested against it, both ways."],
    ["Review", "Changes are reviewed.", "As a diff of the description, in the pull request."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("The documentation annotations removed",
     "\"springdoc generates the docs anyway\": it generates the paths and the schema, but not the errors, the examples, or that the int fields are required. Partners are back to guessing, and the tests that send the examples have nothing to send.",
     "<code>everyRequestExampleGetsTheStatusTheDocsGiveIt</code>, <code>theFieldsTheDocsCallRequiredAreExactlyTheOnesTheApiRefusesWithout</code> and <code>theDescriptionMatchesTheApprovedCopy</code> fail."),
    ("Too heavy answered 400",
     "\"A weight we cannot carry is a bad request\": but the request is valid; the network cannot carry it. Partners handle 400 by fixing their code and 422 by telling their customer; the change sends them the wrong way.",
     "<code>whatTheNetworkCannotCarryIs422</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate tidies the controller: the documentation annotations go, since springdoc generates the docs from the code anyway, and an over-weight parcel becomes a <code>400</code> like other invalid input. Read the file and list every problem before opening the findings.</p>
<p class="path">review/RateQuoteController.java</p>
""" + code(read("review/RateQuoteController.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">The API still answers every quote correctly. What breaks is what partners can learn from the docs, which only tests on the docs themselves can see.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
