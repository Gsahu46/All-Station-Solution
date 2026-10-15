"""Station 045 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 45,
    "stack": "Spring Boot 4.1.1 · Java 25 · MapStruct 1.6.3 (unmappedTargetPolicy ERROR) · Spring Data JPA · @Embedded, @OneToMany · PostgreSQL 17 · Flyway · Testcontainers",
    "simulation": "Orders, customers and prices are demo data, not Tiffino's. An order is a record; no kitchen, rider or payment is involved.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tiffino/ordering/"
T = "src/test/java/com/tiffino/ordering/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("DTO", "An object shaped for the API: what clients send and receive.", "The order slip, not the kitchen's ledger.", "<code>OrderDtos</code>"),
    ("Mapping", "Copying values between an entity and a DTO.", "Copying an order slip into the ledger.", "<code>OrderMapper</code>"),
    ("MapStruct", "A tool that writes the mapping code for you when the project compiles.", "A stamp that copies every box at once.", "<code>OrderMapperImpl</code> (generated)"),
    ("Unmapped target", "A field on the destination that nothing fills.", "A box on the ledger left blank.", "<code>unmappedTargetPolicy = ERROR</code>"),
    ("Nested mapping", "Mapping an object inside an object, or a list of them.", "The address block inside the slip.", "<code>address</code>, <code>lines</code>"),
    ("Custom mapping", "A rule you write for one field.", "Writing only the last 4 digits of the phone.", "<code>maskPhone</code>"),
]
STORY = [
    ("600 lines of copying", "Tiffino's code copied fields between entities and API objects by hand: name to name, phone to phone, for every class."),
    ("A new field, half added", "In March, \"delivery instructions\" was added to the table, the entity, the request and the response. Nobody added it to the copying code. It compiled, tests passed, and every \"ring twice, baby sleeping\" went nowhere."),
    ("The fix", "Let MapStruct write the copying code, and make the build fail when any field is left unmapped without saying why."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A forgotten field should fail the build, not the customer's order.</p>

<h2>What are we building?</h2>
<p><code>POST /orders</code> takes an order with an address, lines and delivery instructions; <code>GET /orders/{id}</code> returns it, phone masked, totals computed. Every field travels both ways.</p>

<h2>An everyday analogy</h2>
<p>A printed form with numbered boxes and a checker who refuses any form with an empty box, unless it is stamped \"not needed\". A clerk copying by hand skips a box now and then; the checker never does.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>You declare</strong> the mappings as an interface, with the few special rules.</li>
<li><strong>At compile time</strong>, MapStruct writes the code, field by field.</li>
<li><strong>Any target field</strong> nobody fills, and nobody marked as ignored, stops the build.</li>
<li><strong>At runtime</strong>, the generated code is plain Java: no reflection, no surprises.</li>
</ol>

<details class="qa check"><summary>Check yourself: why do <code>id</code>, <code>status</code> and <code>totalPaise</code> say <code>ignore = true</code>?</summary><p>They must not come from the client: the database assigns the id, the service sets the status and computes the total. \"Ignore\" is a written decision; forgetting is not, and the build refuses it.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No order workflow.</strong> Orders stay PLACED.</li>
<li><strong>No payment.</strong> A total, not a charge.</li>
<li><strong>No editing.</strong> Changing lines is station 047.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tiffino</strong> (a fictional food delivery brand) has 600 lines of hand-written mapping between entities and DTOs; a field added to one was silently missed in the other.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> an order with delivery instructions, <b>then</b> <code>201</code> and the same instructions in the response and on <code>GET</code>.</li>
<li><b>Given</b> 2 paneer thalis at ₹249 and 1 chaas at ₹49, <b>then</b> line totals ₹498 and ₹49, order total ₹547.</li>
<li><b>Given</b> any response, <b>then</b> the phone shows only its last 4 digits.</li>
<li><b>Given</b> a mapper that leaves a field unmapped, <b>then</b> the build fails, naming the field.</li>
<li><b>Given</b> a 5-digit PIN, quantity 0, a bad phone, no lines, or a <code>totalPaise</code> sent by the client, <b>then</b> <code>400</code>; an unknown order, <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Mapping is generated by MapStruct with <code>unmappedTargetPolicy = ERROR</code>.</li>
<li>Fields the client must not set are ignored explicitly, with a reason.</li>
<li>Totals are computed on the server; money in integer paise.</li>
<li>An order and its lines are saved together, or not at all.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Keep entities and DTOs apart, and map between them.</li>
<li>Write MapStruct mappers with nested, list and custom mappings.</li>
<li>Use compile-time unmapped-field checks, and know their blind spot.</li>
<li>Map a bidirectional parent–child relation correctly.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/orders</code>", "Place an order: customer, phone, address, optional instructions, 1 to 20 lines."],
    ["<code>GET</code>", "<code>/orders/{id}</code>", "Read it back."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Placed; <code>Location</code> points at it"],
    ['<span class="pill ok">200</span>', "The order"],
    ['<span class="pill warn">400</span>', "A field fails validation, or an unknown field such as <code>totalPaise</code>"],
    ['<span class="pill warn">404</span>', "No such order"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against one fresh database. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-place-an-order", "Case 1: an order with instructions", "<b>Why:</b> every field mapped in and out; phone masked; total computed."),
    ("02-read-it-back", "Case 2: the same order, read back", "<b>Why:</b> the instructions survived the round trip through the database."),
    ("03-no-such-order", "Case 3: order 99", "<b>Why:</b> <code>404</code>."),
    ("04-a-five-digit-pin", "Case 4: PIN 41104", "<b>Why:</b> <code>400</code>."),
    ("05-the-client-sets-the-total", "Case 5: <code>totalPaise</code> in the request", "<b>Why:</b> not a request field: <code>400</code>."),
]) + """
<h2>The code MapStruct wrote</h2>
<p class="muted">The <code>OrderMapperImpl</code> generated by the build the captures ran against (<code>docs/captures/generated-OrderMapperImpl.java.txt</code>). Nobody wrote or edits this file.</p>
""" + code(read("docs/captures/generated-OrderMapperImpl.java.txt"), "java")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A full order, posted and read back", "Every field, phone masked, totals", "<code>anOrderComesBackWithEveryField</code>"],
    ["No instructions", "Allowed; absent in the response", "<code>instructionsAreOptional</code>"],
    ["A mapper missing a field", "The build fails", "<code>theBuildFailsWhenAMapperMissesAField</code>"],
    ["A package-private setter", "Silently not mapped", "<code>butAPackagePrivateSetterIsInvisibleAndSilentlySkipped</code>"],
    ["Bad phone, PIN, status, total, quantity, orphan line, written directly", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"],
    ["A line the database refuses", "The whole order rolls back", "<code>aBadLineRollsBackTheWholeOrder</code>"],
    ["Bad fields; unknown order", "<code>400</code>; <code>404</code>", "<code>OrderContractTest</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Hand-written mapping that silently skips a newly added field.</p>
<p>The old mapper, kept in the tests, drops the delivery instructions on the way in and on the way out. MapStruct carries them both ways.</p>
<p>The last two tests run the Java compiler with the MapStruct processor, on a tiny mapper each. A mapper that misses a field fails to compile, naming it. A setter that is not public compiles with no error and is never called. That second case is how this station was first built: MapStruct filled only the list of lines, and the ERROR policy did not fire, because it only checks setters it can see.</p>
<p>While building, each part was undone once. Not linking lines to their order turned 4 tests red, ignoring the instructions on purpose 2, and dropping the phone mask 1. Leaving out the <code>totalPaise</code> decision made the project fail to compile.</p>
</div>
""" + code(read(T + "HandWrittenMappingTrapTest.java"), "java") + code(read(T + "OldOrderMapper.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "OrderController.java", dwn("Validates the request; returns the response with <code>Location</code>.", "HTTP only; no mapping here.", "Mapping code mixed into the controller.")),
    (J + "OrderService.java", dwn("Maps, sets the status, computes the total, saves; maps back inside the transaction.",
        "The server decides what the client must not.", "A total taken from the client.")),
    (J + "OrderMapper.java", dwn("The mappings MapStruct turns into code.",
        "Every target field is mapped, or ignored with a reason; anything else fails the build.",
        "600 lines of copying, and the next forgotten field.",
        "<ul><li><code>@AfterMapping linkLines</code> sets each line's <code>order</code>, without which Hibernate cannot fill <code>order_id</code>.</li><li><code>@Named(\"maskPhone\")</code> is a rule for one field; <code>expression</code> computes <code>linePaise</code>.</li></ul>")),
    (J + "OrderDtos.java", dwn("Request and response records, with validation.", "The API's shape, apart from the tables.", "Entities in JSON (station 043).")),
    (J + "Order.java", dwn("The orders table, with an embedded address and its lines.",
        "Setters are public: MapStruct does not see package-private ones.",
        "A mapper that compiles and fills nothing.")),
    (J + "OrderLine.java", "<p>One line, linked to its order.</p>"),
    (J + "Address.java", "<p>The address, embedded in the orders row.</p>"),
    (J + "OrderRepository.java", "<p>Spring Data repository.</p>"),
    (M + "V1__orders_and_lines.sql", "<p>Both tables with named constraints. Column types match the entities, or Hibernate's validation stops the start.</p>"),
    ("pom.xml", "<p>MapStruct and its annotation processor; the processor is also on the test classpath for the javac tests.</p>"),
    ("src/main/resources/application.yaml", "<p>open-in-view off, schema validation, strict JSON.</p>"),
    (J + "OrderingApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/045-order-dtos-with-mapstruct/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/tiffino/ordering/
│   ├── OrderController.java   ├── OrderService.java   ├── OrderMapper.java   ├── OrderDtos.java
│   ├── Order.java   ├── OrderLine.java   ├── Address.java   ├── OrderRepository.java   └── OrderingApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__orders_and_lines.sql
├── src/test/java/com/tiffino/ordering/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures (with the generated mapper), saved runs"""
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
<p>Make the March mistake on purpose: add <code>String deliverySlot</code> to <code>OrderResponse</code> and to <code>Order</code> (with a public setter), and compile.</p>
""" + code("""./mvnw -q compile""", "bash") + """
<p>The build stops with <code>Unmapped target property: "deliverySlot"</code> until the column, the request and the mapping agree. Put it back.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>Unmapped target property: \"…\"</code>", "A target field nobody fills.", "Map it, or <code>@Mapping(target = \"…\", ignore = true)</code> with a reason."],
    ["Fields silently null after mapping, no error", "The target's setters are not public.", "Make them public; MapStruct only sees accessible setters."],
    ["<code>Can't map \"0\" to \"long …\". Reason: L/l mandatory for long types</code>", "A <code>defaultValue</code> for a long.", "Write <code>\"0L\"</code>."],
    ["<code>Schema validation: wrong column type … found [int2], but expecting [integer]</code>", "A SMALLINT column for an <code>int</code> field.", "Match the types in a migration; validation only checks."],
    ["<code>null value in column \"order_id\"</code>", "Lines not linked to their order.", "The <code>@AfterMapping</code> that sets <code>line.order</code>."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the entities and the database.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>OrderContractTest</code> ({cnt('OrderContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>HandWrittenMappingTrapTest</code> ({cnt('HandWrittenMappingTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>OrderDatabaseTest</code> ({cnt('OrderDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, MapStruct 1.6.3, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "HandWrittenMappingTrapTest.java", "<p>Written first: the old mapper, MapStruct, and two javac runs with the processor.</p>"),
    (T + "OrderContractTest.java", "<p>A full order in and out, and every refusal.</p>"),
    (T + "OrderDatabaseTest.java", "<p>Named constraints, and an order rolled back with its lines.</p>"),
    (T + "OldOrderMapper.java", "<p>The old hand-written mapping, kept only in tests.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the demo order, and requests read by the app's JSON mapper.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tiffino/ordering/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=TipChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in (Java files and one migration), all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "A tip for the rider", "Beginner-friendly", 25,
    "Add an optional <code>tipPaise</code> (0 to ₹500): in the request, a new migration with a check, the entity and the response; the total includes it. Watch what the build says each time the field exists in one place but not the next.",
    "both tests in <code>TipChallengeTest</code> pass.",
    ["<code>@Mapping(target = \"tipPaise\", source = \"tipPaise\", defaultValue = \"0L\")</code> turns a missing tip into 0.",
     "The total is still computed in the service."],
    "challenge/TipChallengeTest.java", ["challenge/solution/V2__order_tip.sql", "challenge/solution/Order.java", "challenge/solution/OrderDtos.java", "challenge/solution/OrderMapper.java", "challenge/solution/OrderService.java"]) + challenge(2, "A kitchen ticket", "Go deeper", 25,
    "Add <code>GET /orders/{id}/kitchen-ticket</code>: the order id, each line as \"2 x Paneer thali\", and the instructions. No name, phone, address or prices.",
    "the test in <code>KitchenTicketChallengeTest</code> passes.",
    ["A second mapping method from <code>Order</code> to a new record, with <code>source</code> renames.",
     "A <code>default</code> method from <code>OrderLine</code> to <code>String</code> is used for each element of the list."],
    "challenge/KitchenTicketChallengeTest.java", ["challenge/solution/OrderMapper.java", "challenge/solution/OrderService.java", "challenge/solution/OrderController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>When is a mapper worth it?</h2>
<p>For a public API, a mobile app, an internal admin tool and a service-to-service event, decide between: MapStruct, hand-written mapping with a test per field, returning entities, and reusing one DTO everywhere. What does each cost when a column is added, and who notices when something is missed?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, mapping"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test with the old mapper.</li>
<li>Write the DTOs and the mapper interface; let the build tell you every field you have not decided.</li>
<li>Read the generated code once; check it fills what you expect.</li>
<li>Prove the compile-time check with javac in a test, including its blind spot.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["MapStruct with <code>unmappedTargetPolicy = ERROR</code>", "An annotation processor; public setters or constructors.", '<span class="pill ok">Chosen</span>'],
    ["Hand-written mapping", "Every new field needs someone to remember.", '<span class="pill bad">The trap</span>'],
    ["Reflection mappers (ModelMapper and similar)", "Mistakes found at runtime, matching by guesswork.", '<span class="pill warn">Late errors</span>'],
    ["Returning entities", "Leaks and lazy loading (station 043).", '<span class="pill bad">No</span>'],
    ["Records with constructors only", "MapStruct uses the constructor; immutable entities do not suit JPA.", '<span class="pill warn">For DTOs, yes</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Constraints", "Mapped as"], [
    ["<code>orders</code>", "<code>orders_phone_digits</code>, <code>orders_pincode_digits</code>, <code>orders_status_known</code>, <code>orders_total_positive</code>", "<code>Order</code>, with <code>@Embedded Address</code> for the address columns"],
    ["<code>order_lines</code>", "<code>order_lines_order_fk</code>, <code>order_lines_quantity_range</code>, <code>order_lines_price_positive</code>", "<code>OrderLine</code>, <code>@ManyToOne</code> to its order; <code>@OneToMany(cascade = ALL)</code> from it"]]) + """
""" + code(read(M + "V1__orders_and_lines.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Build as a reviewer</dt><dd>The ERROR policy turns a review comment (\"did you map the new field?\") into a build step nobody can skip.</dd>
<dt>Read the generated code</dt><dd>It is plain Java in <code>target/generated-sources</code>. When a mapping surprises you, read it before guessing.</dd>
<dt>Personal data</dt><dd>Masking in the mapper means no response can forget it; logs and exports need the same care.</dd>
<dt>Versions</dt><dd>Generated code depends on the MapStruct version; pin it and upgrade deliberately.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why separate entities and DTOs?", "The API is a contract with clients; the table is an implementation detail. Separating them lets either change without breaking the other, and keeps private columns private."),
    ("What does MapStruct do?", "It generates mapping code at compile time from an interface. The result is plain Java, fast and debuggable, and mistakes are compile errors."),
    ("What does unmappedTargetPolicy = ERROR give you?", "A build failure when a target property has no source and no explicit ignore, so a newly added field cannot be forgotten silently."),
    ("What can it not catch?", "Properties it cannot see, such as fields with non-public setters, and wrong-but-present mappings (two fields of the same type swapped). Tests still matter."),
    ("How do you map a parent with a list of children in JPA?", "Map the list, then set each child's back-reference to the parent (an @AfterMapping here), because the child's foreign key comes from that reference."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You added a field and followed the build's errors to the end."],
    ["MapStruct", "Nested, list and custom mappings.", "You read the generated code."],
    ["Safety", "ERROR policy, explicit ignores.", "You know what the policy cannot see."],
    ["JPA", "Parent and children saved together.", "Why the back-reference matters."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any mapping change:</p>
<ul class="rules">
<li>Is every <code>ignore = true</code> explained, and still true?</li>
<li>Are the target's setters public, or is there a constructor MapStruct can use?</li>
<li>Can any field the client sends override something the server decides?</li>
<li>Is personal data masked in the mapping, not left to each caller?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
