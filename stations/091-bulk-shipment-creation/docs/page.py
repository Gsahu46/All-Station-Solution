"""Station 091 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 91,
    "stack": "Spring Boot 4.1.1 · Java 25 · batch endpoints with per-item results · Bean Validation per item · JdbcClient · PostgreSQL 17 · Testcontainers",
    "simulation": "The sellers, shipments and addresses are demo data, not Dakroute's. Creating a shipment records a row; no courier is booked.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/dakroute/shipments/"
T = "src/test/java/com/dakroute/shipments/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Batch endpoint", "One call that does many things, here creating many shipments.", "Handing the post office a sack of letters.", "<code>POST /shipments/bulk</code>"),
    ("Per-item result", "An answer for each item: done, or what is wrong with it.", "A receipt line per letter.", "<code>results[]</code>"),
    ("All-or-nothing", "Either every item is done or none is.", "The clerk returns the whole sack for one bad stamp.", "the old code"),
    ("Transaction", "A group of database changes that succeed or fail together.", "One sealed envelope.", "<code>@Transactional</code>"),
    ("207 Multi-Status", "An HTTP status from WebDAV for many results in one answer, in XML.", "A form meant for another office.", "not used here"),
    ("Batch limit", "The most items one call may carry.", "\"At most 500 letters per sack.\"", "500 (demo rule)"),
]
STORY = [
    ("500 shipments, one call", "Sellers upload the day's orders as one batch of up to 500 shipments."),
    ("One bad address", "Item 312 had a five-digit PIN code. The whole batch ran in one transaction: the database refused that row, everything rolled back, and the seller got a 500 with a database message. They re-sent 500 orders, one at a time, to find it."),
    ("The fix", "Each shipment is checked and saved on its own. The answer is a report: created or failed for each item, by position and by the seller's own reference, with the field that is wrong."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">In a batch of independent items, one bad item should fail one item, and the answer should say which.</p>

<h2>What are we building?</h2>
<p>A bulk endpoint that creates every valid shipment and reports, item by item, what was created and what was wrong.</p>

<h2>An everyday analogy</h2>
<p>A good post office clerk takes the 499 letters that are fine and hands back one, with a note: \"this one, the PIN code has five digits\".</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Check the batch</strong>: there is a list, with 1 to 500 items.</li>
<li><strong>Check each item</strong> on its own: every field rule, every problem listed.</li>
<li><strong>Save each item</strong> on its own: a refusal from the database fails that item only.</li>
<li><strong>Report</strong>: how many were created, how many failed, and one result per item in order.</li>
</ol>

<details class="qa check"><summary>Check yourself: half the items fail. Should the answer be 200 or an error?</summary><p>200: the call worked, and the report says how each item went. An error status is for a call that could not be handled at all, such as an empty list or a body that is not JSON.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No courier booking.</strong> A shipment is a row.</li>
<li><strong>No background processing.</strong> 500 items are handled in the request; 50,000 would need a job (challenge 3).</li>
<li><strong>No sign-in.</strong> One seller, to keep the batch logic in view.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Dakroute</strong> (a fictional courier): sellers create 500 shipments in one call; one bad address makes the whole batch fail with no hint which.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo rules: 1 to 500 items per call; weight 1 to 50,000 g; PIN codes of six digits not starting with 0; a 10-digit Indian mobile number; refs of 3 to 40 letters, digits or dashes, unique.</p>
<ol class="gwt">
<li><b>Given</b> a batch with good and bad items, <b>then</b> <code>200</code>, the good ones created, each bad one failed by index, ref and field.</li>
<li><b>Given</b> an item with several problems, <b>then</b> all of them listed, by field.</li>
<li><b>Given</b> a ref used before or twice in the batch, <b>then</b> that item fails, the others do not.</li>
<li><b>Given</b> an item the database refuses for another reason, <b>then</b> that item fails, without SQL details.</li>
<li><b>Given</b> an empty list, more than 500 items, or a body that is not JSON of the right shape, <b>then</b> <code>400</code> and nothing saved.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>One result per item, in the order sent.</li>
<li>No item's failure can undo another item.</li>
<li>Every rule is also a named database constraint.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Design a batch endpoint with per-item results.</li>
<li>Validate items one by one instead of cascading validation over the list.</li>
<li>Know what a transaction around a batch does, in PostgreSQL in particular.</li>
<li>Choose a status for partial success, and a batch limit.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/shipments/bulk</code>", "<code>{shipments: [...]}</code>, 1 to 500: create each valid one; a report per item."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "The batch was handled: the report says, per item, created or failed"],
    ['<span class="pill warn">400</span>', "No list, an empty list, more than 500 items, or a body that is not JSON of the right shape"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. JSON bodies are indented for reading; <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-three-shipments-one-bad-pin-code", "Case 1: three shipments, the second with a five-digit PIN code", "<b>Why:</b> two created; item 1 failed, naming <code>to.pincode</code>."),
    ("02-an-item-with-three-problems", "Case 2: one item with three problems", "<b>Why:</b> all three listed, by field."),
    ("03-a-ref-already-used", "Case 3: ORD-1001 again", "<b>Why:</b> the ref is unique: that item fails."),
    ("04-an-empty-batch", "Case 4: an empty list", "<b>Why:</b> <code>400</code>: nothing to do."),
    ("05-a-weight-that-is-not-a-number", "Case 5: weightGrams \"heavy\"", "<b>Why:</b> the body is not JSON of the right shape, so there is no item to report on: <code>400</code> for the call."),
    ("06-five-hundred-and-one", "Case 6: 501 items", "<b>Why:</b> over the limit: <code>400</code>, nothing saved. The request line is shortened here; all 501 items were sent."),
]) + """
<h2>The shipments afterwards</h2>
""" + code(read("docs/captures/shipments.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A good batch", "One result per item, in order", "<code>aGoodBatchIsCreatedWithOneResultPerItemInOrder</code>"],
    ["Several problems in one item", "All listed by field", "<code>everyProblemInAnItemIsListedByField</code>"],
    ["A ref used before, or twice in the batch", "That item fails", "<code>aRefUsedBeforeOrTwiceInTheBatchFailsThatItemOnly</code>"],
    ["Empty list, no list, a wrong type, a null item", "<code>400</code>; a null item fails alone", "<code>theBatchAsAWholeMustBeUsable</code>"],
    ["500 and 501 items", "Created; <code>400</code>", "<code>fiveHundredIsTheLimit</code>"],
    ["The database refuses one item", "That item fails, the others stay", "<code>anItemTheDatabaseRefusesFailsAloneAndTheOthersStay</code>"],
    ["Rules written by plain SQL", "Refused by named constraints", "<code>shipmentRulesHoldWithoutJava</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">All-or-nothing batches with no per-item results.</p>
<ul>
<li><strong>The old way.</strong> The test inserts three shipments in one transaction; the second has a five-digit PIN code. The database refuses it, the transaction rolls back, nothing is saved, and the only message names a database constraint.</li>
<li><strong>The API.</strong> The same three items: two created, and item 1 failed with <code>to.pincode</code>: \"must be 6 digits, not starting with 0\".</li>
</ul>
<p>While building, each part was undone once: one transaction around the loop turned 2 tests red; validation cascading over the list 2; no per-item validation 2; no specific message for a used ref 1; no batch limit 1; refs not upper-cased 2; indexes off by one 3. Trimming names changed no test, so the trimming was removed.</p>
</div>
""" + code(read(T + "AllOrNothingTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "BulkShipmentController.java", dwn("The endpoint.",
        "Checks the list (present, 1 to 500) and hands it over; answers 200 with the report.",
        "One bad item turning the whole call into a 400.",
        "<ul><li>No <code>@Valid</code> on the list's items: with it, one bad item makes the whole call a 400, the all-or-nothing answer again.</li><li>Not 207 Multi-Status: that status comes from WebDAV (RFC 4918), whose clients expect an XML body.</li></ul>")),
    (J + "BulkShipments.java", dwn("Checking and saving each item on its own.",
        "A Validator per item, errors sorted by field; one INSERT per item, committed on its own; a used ref and other refusals reported as that item's failure.",
        "One item's failure undoing or hiding the others.",
        "<p>No transaction around the loop: in PostgreSQL, the first refused statement aborts the whole transaction, so every later item fails and the earlier ones are rolled back at commit. See the Review tab.</p>")),
    (M + "V1__shipments.sql", dwn("Shipments and their rules.", "Ref unique and shaped, PIN codes, phone, weight, address present.", "A bad shipment from any writer.")),
    ("src/main/resources/application.yaml", "<p>Database connection; fractions refused for whole-number fields.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "ShipmentsApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/091-bulk-shipment-creation/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/dakroute/shipments/
│   ├── BulkShipmentController.java   ├── BulkShipments.java   └── ShipmentsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__shipments.sql
├── src/test/java/com/dakroute/shipments/   (see Tests)
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
<p>Run <code>docs/capture.sh</code> against your running app (from the station folder, with <code>docker compose</code> up): it sends the six requests above and writes the answers to <code>docs/captures/</code>. Then edit one item in case 1 and send it again with the <code>curl</code> line from that file.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Every item after a failed one says \"could not be saved\"", "A transaction around the batch: PostgreSQL aborts it at the first error.", "Save each item on its own, as <code>BulkShipments</code> does."],
    ["One bad item makes the whole call a 400", "<code>@Valid</code> cascades over the list's items.", "Validate each item yourself and report it."],
    ["<code>Could not find a valid Docker environment</code>", "Docker is not running.", "Start Docker Desktop or the Docker service."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the database behind it.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>BulkContractTest</code> ({cnt('BulkContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>AllOrNothingTrapTest</code> ({cnt('AllOrNothingTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>ShipmentDatabaseTest</code> ({cnt('ShipmentDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">There is no \"not found\" here: a batch creates, it does not look anything up. The 400 cases stand in for invalid calls.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "AllOrNothingTrapTest.java", "<p>Written first: one transaction for the batch, and the API's report.</p>"),
    (T + "BulkContractTest.java", "<p>The report, field errors, used refs, bad calls, the limit.</p>"),
    (T + "ShipmentDatabaseTest.java", "<p>Named constraints with plain SQL; one item refused by the database.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: no shipments before each test, an item builder, request helpers.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/dakroute/shipments/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=ValidateOnlyChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "A dry run", "Beginner-friendly", 20,
    "<code>POST /shipments/bulk?validateOnly=true</code> checks a batch without saving it: good items <code>valid</code>, bad ones <code>failed</code> with the same errors as a real call, including a ref already used.",
    "the test in <code>ValidateOnlyChallengeTest</code> passes.",
    ["A <code>@RequestParam(defaultValue = \"false\")</code> passed down to where an item would be saved.",
     "Checking a used ref without saving means looking it up first."],
    "challenge/ValidateOnlyChallengeTest.java", ["challenge/solution/BulkShipments.java", "challenge/solution/BulkShipmentController.java"]) + challenge(2, "The same file twice", "Go deeper", 30,
    "A seller whose upload timed out sends the same file again. An item identical to the shipment already created under its ref is <code>existing</code>, with that shipment's id; the same ref with other details still fails. The report counts <code>existing</code>.",
    "both tests in <code>ResubmitChallengeTest</code> pass (the second already passes: it guards the old behaviour).",
    ["Compare every stored field, not just the ref.",
     "Leave <code>existing</code> out of the report when it is 0, so other clients see no change (<code>@JsonInclude(NON_DEFAULT)</code>)."],
    "challenge/ResubmitChallengeTest.java", ["challenge/solution/BulkShipments.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>50,000 items</h2>
<p>A marketplace wants to send 50,000 shipments at once. Design it as a job: upload, <code>202</code> with a job id, progress, and a downloadable report (station 098 does long-running work). How do you keep the per-item results, let the seller fix and resend only the failed ones, and stop one seller's job from slowing everyone else?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: one transaction for the batch.</li>
<li>Check the list; check each item with a Validator; collect errors by field.</li>
<li>Insert each item in its own statement; turn a refusal into that item's failure.</li>
<li>Return the report: counts and one result per item.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Independent items, 200 with a report", "Clients must read the report, not just the status.", '<span class="pill ok">Chosen</span>'],
    ["One transaction, all-or-nothing", "One bad item fails all; without a report, the seller cannot tell which.", '<span class="pill bad">The trap</span>'],
    ["All-or-nothing, with a report of what would fail", "Right when items depend on each other (a payment and its order lines).", '<span class="pill warn">For dependent items</span>'],
    ["207 Multi-Status", "WebDAV's status; clients expect XML.", '<span class="pill warn">Uncommon for JSON APIs</span>'],
    ["A JDBC batch insert", "Faster; a failure in the batch is harder to tie to one item.", '<span class="pill warn">When speed matters more</span>']]) + """
<p class="muted">Google's API Improvement Proposals AIP-231 to AIP-235 are Google's own design guide for batch methods, not a standard; compare their choices with this one.</p>
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>shipments_ref_unique</code>", "UNIQUE", "A ref is one shipment, even across batches."],
    ["<code>shipments_pincodes</code>, <code>shipments_phone</code>", "CHECKs", "Addresses a courier can deliver to."],
    ["<code>shipments_weight</code>", "CHECK", "1 to 50,000 g."],
    ["<code>shipments_address_present</code>, <code>shipments_ref_shape</code>", "CHECKs", "No blank names or odd refs from any writer."]]) + """
<p><strong>Transaction boundary:</strong> one INSERT per item, committed on its own. Nothing groups items: they do not depend on each other.</p>
""" + code(read(M + "V1__shipments.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Limits</dt><dd>Limit items per call and the body size (the server's request size limit), and say so in the docs; a batch that is too big is refused before any work.</dd>
<dt>Time</dt><dd>500 inserts take a moment; much more and the request time grows past what clients and load balancers wait. Move big batches to a job.</dd>
<dt>Retries</dt><dd>A client that times out re-sends the batch: unique refs stop duplicates (challenge 2 makes it friendly).</dd>
<dt>Metrics</dt><dd>Count failed items by field: a spike in one field usually means a client bug, not bad data.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("200, 207 or 400 for partial success?", "200 with a per-item report is the common choice for JSON APIs. 207 is WebDAV's and implies an XML body. 400 is for a call that cannot be handled at all."),
    ("Why not one transaction for the batch?", "Items are independent, so one item's problem should not undo the others. In PostgreSQL the first failed statement also aborts the transaction, so later items fail too."),
    ("How do you validate items one by one in Spring?", "Do not cascade @Valid over the list; inject a Validator and validate each item, collecting the violations."),
    ("How do you make a batch safe to resend?", "Give each item a client reference with a unique constraint, and answer an identical resend with the existing item."),
    ("When is all-or-nothing right?", "When the items depend on each other, like an order and its lines, or a transfer's two sides."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Results", "A result per item.", "Every problem by field, in order, with the client's reference."],
    ["Isolation", "Bad items do not stop good ones.", "You can explain what a transaction around the loop does in PostgreSQL."],
    ["Limits", "A batch limit.", "Limits on items, size and time, documented."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("One transaction for the whole batch",
     "\"Consistent, and faster than 500 commits\": but in PostgreSQL the first refused statement aborts the transaction. Every later item then fails with \"could not be saved\", and at commit the items reported as created are rolled back. Seen while building: a report saying \"created\": 1 for an item that was never stored.",
     "<code>aRefUsedBeforeOrTwiceInTheBatchFailsThatItemOnly</code> and <code>anItemTheDatabaseRefusesFailsAloneAndTheOthersStay</code> fail."),
    ("A batch limit of 5,000",
     "\"Big sellers asked for bigger batches\": ten times the work in one request, past the time clients and load balancers wait, with nothing saying where the work stopped.",
     "<code>fiveHundredIsTheLimit</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate wraps the batch in one <code>@Transactional</code>, \"so a batch is consistent and 500 commits become one\", and raises the limit to 5,000 for big sellers. The per-item report is kept. Read the file and list every problem before opening the findings.</p>
<p class="path">review/BulkShipments.java</p>
""" + code(read("review/BulkShipments.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">With only good items, the flawed version passes: one transaction commits them all. It takes one refused item to see the report lie.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
