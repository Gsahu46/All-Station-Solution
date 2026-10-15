"""Station 032 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 32,
    "stack": "Spring Boot 4.1.1 · Java 25 · JUnit 6 parameterized tests · Mockito · AssertJ · fixed Clock · MockMvc",
    "simulation": "Orders, prices and return windows are demo data and demo rules, not Kartwala's. The endpoint only answers whether a return would be accepted; nothing is returned, refunded or picked up.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/kartwala/refunds/"
T = "src/test/java/com/kartwala/refunds/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Happy path", "The case where everything goes right.", "Testing a lock only with the right key.", "electronics, day 3"),
    ("Parameterized test", "One test method run once per row of a table of inputs and expected results.", "A teacher checking every answer against the answer key.", "<code>theRuleTable</code>"),
    ("Pure function", "Gives the same answer for the same inputs and touches nothing else.", "A calculator.", "<code>RefundRules.check</code>"),
    ("Stub", "A stand-in that returns a prepared answer to a question.", "A friend reading out a script.", "<code>when(orders.find(…))</code>"),
    ("Verify", "Checking a stand-in was told to do something.", "Checking the letter was posted.", "<code>verify(audit).record(…)</code>"),
    ("Fixed clock", "A clock that always says the same time, so tests about dates give the same result every day.", "A stopped watch in a photo.", "<code>Clock.fixed(…)</code>"),
]
STORY = [
    ("A rule changes", "Electronics returns go from 30 days to 7. A developer edits the switch statement, runs the one test (an electronics return on day 3), sees green, and ships."),
    ("Something else breaks", "Clothing shared that case of the switch. Customers returning a kurta on day 10 are refused. Support finds out from complaints."),
    ("The fix", "Each category owns its window. The rules become one function tested with a table: every category, every reason, the last day and the day after."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A test suite that checks only what you changed cannot see what you broke.</p>

<h2>What are we building?</h2>
<p><code>POST /refund-eligibility-checks</code> answers, before a customer books a pickup: can this order be returned for this reason, how much comes back, and until which day? If not, it lists every reason.</p>

<h2>An everyday analogy</h2>
<p>A shop's returns desk with a printed rule card per department. Changing the electronics card cannot change the clothing card, and the manager tests a new card against a list of real situations, not just one.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Find the order</strong> and its category, price and delivery date.</li>
<li><strong>Find today</strong> in India's calendar.</li>
<li><strong>Apply the rules</strong>: window, accepted reasons, hygiene items, tags, seal.</li>
<li><strong>Answer and record</strong>: eligible or every reason why not, the refund, the last day.</li>
</ol>

<details class="qa check"><summary>Check yourself: the old suite had one test and it passed after the change. What would have caught the bug?</summary><p>Any test of a clothing return between day 8 and day 30. A table with one row per category at its last day would have turned red the moment clothing's window changed.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No refunds.</strong> A check only: no money moves, no pickup is booked.</li>
<li><strong>One item per order.</strong> Real orders have many lines, each checked the same way.</li>
<li><strong>No database.</strong> Demo orders in memory.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
RULES = [
    ["Clothing", "30 days", "All five", "Innerwear: only damaged or wrong item. Changed mind or size: tags attached."],
    ["Electronics", "7 days", "Damaged, wrong item, not as described", "Seal broken: only damaged."],
    ["Books", "10 days", "Damaged, wrong item, changed mind", ""],
    ["Grocery", "2 days", "Damaged, wrong item", ""],
]
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Kartwala</strong> (a fictional shopping app) has refund rules with many conditions and no tests but one. A change for electronics broke refunds for clothing, and no test noticed.</p>

<h2>The rules (demo)</h2>
""" + table(["Category", "Window after delivery", "Accepted reasons", "Extra conditions"], RULES) + """
<p class="muted">Changed mind and size issue are the customer's choice: ₹49 pickup fee is deducted. For damaged, wrong or not-as-described items, the full price comes back. Not delivered yet: nothing to return (cancel instead).</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a kurta delivered 14 days ago that did not fit, tags attached, <b>then</b> eligible, ₹1,250.00 back (₹1,299 minus ₹49), last day 16 days from now.</li>
<li><b>Given</b> earbuds delivered 9 days ago, changed mind, seal broken, <b>then</b> refused for all three reasons: <code>WINDOW_CLOSED</code>, <code>REASON_NOT_ACCEPTED</code>, <code>SEAL_BROKEN</code>.</li>
<li><b>Given</b> the last day of any category's window, <b>then</b> open; the day after, closed.</li>
<li><b>Given</b> 01:30 in India on the day after the last day (still the last day on a UTC server), <b>then</b> closed.</li>
<li><b>Given</b> clothing without a <code>tagsAttached</code> answer, or electronics without <code>sealIntact</code>, <b>then</b> <code>400</code>.</li>
<li><b>Given</b> an unknown order, <code>404</code>; an unknown reason or field, <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Each category owns its window and reasons; no rule is shared by accident.</li>
<li>The rules are a pure function; "today" comes from a <code>Clock</code>, in India's time zone.</li>
<li>Every decision is recorded for support.</li>
<li>Money in integer paise; a refund is never negative.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Write table-driven tests with <code>@ParameterizedTest</code>, <code>@CsvSource</code> and <code>@EnumSource</code>.</li>
<li>Know when to stub and when to verify with Mockito.</li>
<li>Use AssertJ for readable assertions.</li>
<li>Make time testable with a <code>Clock</code>.</li>
<li>Shape code so the important part is easy to test.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Body"], [
    ["<code>POST</code>", "<code>/refund-eligibility-checks</code>", "<code>{\"orderId\", \"reason\", \"tagsAttached\"?, \"sealIntact\"?}</code>. <code>reason</code> is one of <code>DAMAGED</code>, <code>WRONG_ITEM</code>, <code>NOT_AS_DESCRIBED</code>, <code>CHANGED_MIND</code>, <code>SIZE_ISSUE</code>."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "A decision: eligible, or refused with every reason"],
    ['<span class="pill warn">400</span>', "A bad order id, a missing or unknown reason, an unknown field, or a missing tags or seal answer"],
    ['<span class="pill warn">404</span>', "No such order"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. The demo orders are delivered a fixed number of days before the app starts, so the dates are relative to that day. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-a-kurta-that-did-not-fit", "Case 1: a kurta, day 14, size issue", "<b>Why:</b> inside 30 days, tags attached. ₹49 pickup fee because it is the customer's choice."),
    ("02-innerwear-changed-mind", "Case 2: innerwear, changed mind", "<b>Why:</b> hygiene item: only damaged or wrong items come back."),
    ("03-earbuds-every-reason", "Case 3: earbuds, day 9, changed mind, seal broken", "<b>Why:</b> three reasons, all listed, so the app can explain them at once."),
    ("04-a-damaged-phone", "Case 4: a phone that arrived damaged", "<b>Why:</b> the seal is broken, but the reason is damage: full refund."),
    ("05-groceries-changed-mind", "Case 5: groceries, changed mind", "<b>Why:</b> groceries come back only if damaged or wrong."),
    ("06-not-delivered-yet", "Case 6: a book not yet delivered", "<b>Why:</b> nothing to return; no last day."),
    ("07-no-such-order", "Case 7: KW-9999", "<b>Why:</b> <code>404</code>."),
    ("08-clothing-without-the-tags-answer", "Case 8: clothing, no tags answer", "<b>Why:</b> the rules need it for clothing, so the request is incomplete: <code>400</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["17 combinations of category, day, reason, tags and seal", "As in the rule table", "<code>theRuleTable</code>"],
    ["The last day and the day after, every category", "Open, then closed", "<code>theLastDayIsOpenAndTheNextDayIsClosedInEveryCategory</code>"],
    ["Innerwear, each reason", "Only damaged or wrong item", "<code>hygieneItemsComeBackOnlyWhenItWasOurFault</code>"],
    ["Changed mind vs damaged; a ₹30 item with the fee", "₹49 deducted only for the customer's choice; never below 0", "<code>theCustomersChoicePaysThePickupFeeAndOurMistakeDoesNot</code>"],
    ["Not delivered", "<code>NOT_DELIVERED</code>, no last day", "<code>anOrderNotYetDeliveredCannotBeReturned</code>"],
    ["01:30 in India, 20:00 the day before in UTC", "India's date decides", "<code>theLastDayIsCountedInIndiaNotOnTheServer</code>"],
    ["Unknown order; missing answers", "Nothing recorded", "<code>anUnknownOrderOrAMissingAnswerRecordsNothing</code>"],
    ["Unknown reason; missing reason; bad id; extra field", "<code>400</code>", "<code>badRequestsAre400</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Testing only the happy path: one changed rule breaks another category unnoticed.</p>
<p>The test file rebuilds the old switch, where clothing and electronics shared a case. The old suite's only test, an electronics return on day 3, still passes against it. A clothing return on day 20 is refused by it, and accepted by the new rules. While building, each fix was undone once. Clothing back at 7 days turned 5 tests red. Dropping the hygiene rule turned 3 red, and counting days on the server's date instead of India's turned 1 red. Charging the fee for every reason turned 2 red, not recording the decision 1, and letting a broken seal block a damaged phone 2. Listing only the first reason turned 2 red.</p>
</div>
""" + code(read(T + "HappyPathOnlyTrapTest.java"), "java") + code(read(T + "OldRefundRules.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "RefundController.java", dwn("Validates the request and returns the decision.",
        "Only the shape is checked here; what the rules need per category is checked where the category is known.",
        "Business rules in the controller, where only an HTTP test can reach them.")),
    (J + "RefundService.java", dwn("Finds the order, works out today, asks the rules, records the decision.",
        "The only class that knows the time, and the one place with side effects.",
        "<code>LocalDate.now()</code> inside the rules: a test then depends on the day it runs.")),
    (J + "RefundRules.java", dwn("Every rule, as one pure function that returns all the reasons.",
        "No Spring and no clock: a test passes everything in and gets a value back.",
        "Stopping at the first reason, so the customer fixes one thing and is refused again.")),
    (J + "Category.java", dwn("Each category's window and accepted reasons.",
        "Data per category: changing electronics cannot touch clothing.",
        "The trap: a switch with shared cases.")),
    (J + "Reason.java", "<p>The five reasons, and which are the customer's choice.</p>"),
    (J + "Order.java", "<p>One order with one item.</p>"),
    (J + "OrderLookup.java", "<p>Where orders come from: a query.</p>"),
    (J + "DemoOrders.java", "<p>Six demo orders, delivered a fixed number of days before startup.</p>"),
    (J + "EligibilityAudit.java", "<p>Records each decision: a command.</p>"),
    (J + "LoggingAudit.java", "<p>The demo audit: one log line per decision.</p>"),
    (J + "RefundsApplication.java", "<p>Entry point, and the <code>Clock</code> bean tests replace.</p>"),
    ("src/main/resources/application.yaml", "<p>Problem details, and unknown JSON fields refused.</p>"),
]
tree = """stations/032-return-and-refund-eligibility/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/kartwala/refunds/
│   ├── RefundController.java   ├── RefundService.java   ├── RefundRules.java
│   ├── Category.java   ├── Reason.java   ├── Order.java
│   ├── OrderLookup.java   ├── DemoOrders.java
│   ├── EligibilityAudit.java   ├── LoggingAudit.java   └── RefundsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/kartwala/refunds/   (see Tests)
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
""" + code("""./mvnw spring-boot:run                       # the API on http://localhost:8080
./mvnw test                                  # all """ + str(N_TESTS) + """ tests
./mvnw test -Dtest=RefundRulesTest           # just the rule table, in well under a second""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Make the March mistake: change <code>CLOTHING(30,</code> to <code>CLOTHING(7,</code> in <code>Category.java</code> and run <code>RefundRulesTest</code>. Read which rows turn red, then put it back.</p>
""" + code("""curl -X POST http://localhost:8080/refund-eligibility-checks -H "Content-Type: application/json" \\
     -d '{"orderId":"KW-1001","reason":"CHANGED_MIND","tagsAttached":false}'""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>UnnecessaryStubbingException</code>", "Mockito strict stubs: a stub the code never used.", "Remove the stub, or ask whether the code should have used it."],
    ["A date test passes today and fails tomorrow", "Something calls <code>LocalDate.now()</code> directly.", "Take the date from the <code>Clock</code> bean, and fix the clock in the test."],
    ["A row in <code>@CsvSource</code> gets <code>null</code> where you wanted an empty string", "<code>nullValues = \"-\"</code> and <code>''</code> mean different things.", "Use <code>''</code> for empty and <code>-</code> for null."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>RefundContractTest</code> ({cnt('RefundContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>HappyPathOnlyTrapTest</code> ({cnt('HappyPathOnlyTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Every rule as a table", f"<code>RefundRulesTest</code> ({cnt('RefundRulesTest')} runs)", '<span class="pill ok">pass</span>'],
    ["This station", "Stub vs verify; India's date", f"<code>RefundServiceTest</code> ({cnt('RefundServiceTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">A parameterized test counts once per row: <code>RefundRulesTest</code> has five test methods.</p>
<h2>Stub the question, verify the command</h2>
""" + table(["Collaborator", "Kind", "In the test", "Why"], [
    ["<code>OrderLookup.find</code>", "Query: returns data, changes nothing", "<code>when(...).thenReturn(...)</code>", "What it returns shapes the result. How often it is called is a detail; verifying it makes tests break on harmless refactors."],
    ["<code>EligibilityAudit.record</code>", "Command: does something, returns nothing", "<code>verify(audit).record(...)</code>", "Its effect is the behaviour. Nothing else would notice if it stopped being called."]]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "RefundRulesTest.java", "<p>The rule table, the last day of every category, hygiene items, the fee, and undelivered orders.</p>"),
    (T + "RefundServiceTest.java", "<p>Mockito with strict stubs, a fixed clock at 01:30 in India, and the audit verified.</p>"),
    (T + "RefundContractTest.java", "<p>HTTP, with the app's <code>Clock</code> replaced by a fixed one.</p>"),
    (T + "HappyPathOnlyTrapTest.java", "<p>Written first: the old suite's only test, and what it missed.</p>"),
    (T + "OldRefundRules.java", "<p>The old window rule, kept only in tests.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/kartwala/refunds/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=FootwearChallengeTest</code>.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code>: the rule table must stay green.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass. That count is higher than the station's """ + str(N_TESTS) + """ plus the challenge tests alone, because <code>@EnumSource</code> runs once more for the new category.</p>
""" + challenge(1, "Footwear, without breaking clothing", "Beginner-friendly", 25,
    "Add a <code>FOOTWEAR</code> category: 15 days, every reason except not-as-described, and like clothing, tags attached for a customer's-choice return. The tags question becomes required for footwear.",
    "both tests in <code>FootwearChallengeTest</code> pass, and <code>RefundRulesTest</code> stays green.",
    ["Which rule is \"clothing\" and which is \"needs tags\"? Hygiene stays clothing-only.",
     "A small method on <code>Category</code> says which categories need tags; the rules and the service both ask it."],
    "challenge/FootwearChallengeTest.java", ["challenge/solution/Category.java", "challenge/solution/RefundRules.java", "challenge/solution/RefundService.java"]) + challenge(2, "A festive-season extension", "Go deeper", 30,
    "Clothing and books delivered from 15 October to 15 November 2026 can be returned until 30 November, or until their normal last day if that is later. Other categories are unchanged.",
    "all twelve runs of <code>FestiveExtensionChallengeTest</code> pass.",
    ["Test the day before, the first day, the last day and the day after: that is where date bugs live.",
     "<code>!d.isBefore(from) &amp;&amp; !d.isAfter(to)</code> includes both ends."],
    "challenge/FestiveExtensionChallengeTest.java", ["challenge/solution/RefundRules.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Who owns the rule table?</h2>
<p>The category team wants to change windows and reasons without a developer. Compare: rules in code (as now), rules in a database table with an admin screen, and a rules engine. For each, where do the table tests live, and what stops a change for one category from reaching another?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old switch passes its own test and refuses clothing.</li>
<li>Move each category's window and reasons onto the category.</li>
<li>Pull the rules into a pure function and test it as a table.</li>
<li>Keep time, lookups and recording in the service, and test it with Mockito and a fixed clock.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Pure rules + table tests", "Inputs passed explicitly.", '<span class="pill ok">Chosen</span>'],
    ["A switch with shared cases", "One edit can change several categories.", '<span class="pill bad">The trap</span>'],
    ["Only HTTP tests", "Seconds per case, so few cases get written.", '<span class="pill warn">For the contract only</span>'],
    ["A rules engine (Drools and the like)", "A new language and toolchain for a dozen rules.", '<span class="pill warn">When rules number in hundreds</span>'],
    ["Verifying every mock call", "Tests break on harmless refactors.", '<span class="pill bad">Brittle</span>']]) + """
<h2>Database design</h2>
<p>None in this station. If the rules move to a table: <code>return_policy(category primary key, window_days check (window_days between 0 and 90))</code> and <code>return_policy_reason(category, reason, primary key (category, reason))</code>, so a category cannot have two windows.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Time zones</dt><dd>Servers usually run in UTC. Windows promised to customers are in their calendar; a refusal at 1 a.m. that should have been an approval is a support ticket.</dd>
<dt>Audit</dt><dd>Recording every decision with its reasons answers "why was I refused?" weeks later, and shows which rule refuses most.</dd>
<dt>Consumer law</dt><dd>Real return policies must respect consumer protection rules (in India, the Consumer Protection (E-Commerce) Rules, 2020); the windows here are demo values.</dd>
<dt>Test speed</dt><dd>The rule table runs in milliseconds, so it runs on every build. Slow tests get skipped; fast tests get run.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is a parameterized test, and when do you use one?", "One test method run for each row of inputs and expected outputs (@CsvSource, @MethodSource, @EnumSource). Use it when the same rule must hold across many cases, such as every category."),
    ("Stub or verify?", "Stub queries: you care what they return. Verify commands: you care that they happened. Verifying queries couples the test to how the code works, not what it does."),
    ("How do you test code that depends on the current time?", "Inject a java.time.Clock and call LocalDate.now(clock). In tests use Clock.fixed. Never call LocalDate.now() with no argument in logic."),
    ("What makes code testable?", "Separating decisions (pure functions) from effects (database, clock, network). The decisions are tested with many fast cases; the effects with a few."),
    ("What does Mockito's strict stubbing catch?", "A stub the code never used, often a sign the test no longer tests what it claims, or a wrong argument."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You made the March mistake and read which rows failed."],
    ["Test design", "A table with one row per rule.", "Boundaries: the last day and the day after."],
    ["Mocks", "Stub queries, verify commands.", "You can say why a test that verifies a query is brittle."],
    ["Design", "Rules are a pure function.", "Time comes from a Clock, in the customer's zone."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any rule change:</p>
<ul class="rules">
<li>Which other cases share the code that changed, and is there a test for each?</li>
<li>Is there a test at each boundary: the last day and the day after?</li>
<li>Does anything call <code>now()</code> without a clock?</li>
<li>Do the mocks verify what matters, or every call?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
