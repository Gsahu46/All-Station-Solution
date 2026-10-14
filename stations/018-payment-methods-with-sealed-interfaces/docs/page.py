"""Station 018 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 18,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · sealed interfaces · records · switch pattern matching · Jackson 3 · MockMvc",
    "simulation": "A payment intent is a response describing what the payer does next. No UPI app, bank or card network is contacted, no money moves, and nothing is stored in this station. Card tokens are made-up strings.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/paysetu/payments/"
T = "src/test/java/com/paysetu/payments/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Payment intent", "A record of \"this order wants to be paid this way\", before any money moves.", "The checkout screen after you pick UPI.", "<code>POST /payment-intents</code>"),
    ("Sealed interface", "An interface that lists every type allowed to implement it. No one else can.", "A menu with exactly four dishes printed on it.", "<code>PaymentMethod permits Upi, Card, NetBanking, Wallet</code>"),
    ("Record", "A small class that is just its data, with equals and toString for free.", "A filled-in form.", "<code>record Upi(String vpa)</code>"),
    ("Pattern matching switch", "A switch that picks a branch by type and unpacks its fields.", "\"If it is a UPI payment, take its UPI ID and…\"", "<code>case Upi(String vpa) -&gt;</code>"),
    ("Exhaustive", "Covers every case. For a sealed type, the compiler checks it.", "A checklist the inspector will not sign until every line is ticked.", "No <code>default</code> in <code>Methods</code>"),
    ("Card token", "A stand-in for a card number that is useless outside one merchant.", "A cloakroom ticket instead of the coat.", "<code>token</code>, accepted but never returned"),
]
STORY = [
    ("Paysetu adds wallets", "The payment class gets one more nullable field, <code>walletMobile</code>. Checkout works; the tests for checkout pass."),
    ("The first wallet refund", "The refund code checks UPI, then card, then net banking, and returns nothing for anything else. Wallet refunds silently go nowhere, and support finds out from customers."),
    ("The fix", "Model \"one of four\" as a sealed interface with a record per method, and handle them with switches that have no default. Adding a fifth method now stops the build at every place that forgot it."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Let the compiler keep the list of cases, so a new one cannot be forgotten quietly.</p>

<h2>What are we building?</h2>
<p><code>POST /payment-intents</code> takes an order, an amount and exactly one payment method. It answers with what the payer does next (approve in a UPI app, enter an OTP, log in to the bank, confirm a wallet debit) and where a refund would go.</p>

<h2>An everyday analogy</h2>
<p>A paper form with a separate box for each way to pay, where you may fill in only one box. Nobody can tick "UPI" and also write a card number, and the clerk's checklist has a line for every box on the form.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Read the type</strong>: <code>"type": "UPI"</code> picks the UPI record; other fields are refused.</li>
<li><strong>Validate</strong> that record's own fields: a UPI ID, a 4-letter bank code, a 10-digit mobile.</li>
<li><strong>Switch on the method</strong> for the next action; the compiler checks all four are handled.</li>
<li><strong>Switch again</strong> for the refund route, with the same guarantee.</li>
</ol>

<details class="qa check"><summary>Check yourself: why not keep the old class and add a test for wallet refunds?</summary><p>That test catches wallets, once. The next method (say, pay later) needs someone to remember every place again. With a sealed interface and no default branch, the build itself fails at each place that does not handle the new method.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real payment.</strong> Nothing contacts NPCI, a bank or a card network.</li>
<li><strong>No card numbers.</strong> Only a token, the network and the last 4 digits; a full number is refused.</li>
<li><strong>No storage.</strong> Challenge 1 adds it.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Paysetu</strong> (a fictional payment gateway) has one <code>Payment</code> class with a nullable field for every method. Each new method means hunting for every <code>if (vpa != null) … else if …</code> chain. The refund chain was missed when wallets launched, so wallet refunds returned nothing. The class also accepts a payment that is UPI and card at once.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a UPI ID in any case, <b>then</b> it is stored lower-case and the payer is asked to approve in their UPI app.</li>
<li><b>Given</b> a card, <b>then</b> the response shows the network and last 4 digits, never the token.</li>
<li><b>Given</b> net banking at <code>hdfc</code>, <b>then</b> a redirect to the (simulated) HDFC login; at a bank that is not offered, <code>422</code>.</li>
<li><b>Given</b> a wallet, <b>then</b> the refund route is the wallet, with the mobile number masked.</li>
<li><b>Given</b> a UPI method with card fields, an unknown or missing type, or a bad field, <b>then</b> <code>400</code>.</li>
<li><b>Given</b> every permitted payment method, <b>then</b> it can arrive as JSON and has a next action and a refund route.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>One record per method; each has only its own fields. A <code>switch</code> over methods has no <code>default</code>.</li>
<li>Identifiers are normalised with <code>Locale.ROOT</code>: UPI IDs lower-case, bank codes upper-case.</li>
<li>Amounts are whole paise, ₹1 to ₹1,00,000 (a demo rule).</li>
<li>Secrets are write-only: the card token and wallet mobile are accepted, never returned in full.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Model "exactly one of" data with a sealed interface and records.</li>
<li>Use switch pattern matching and record patterns, and explain exhaustiveness.</li>
<li>Read polymorphic JSON with a <code>type</code> field, and refuse fields that do not belong.</li>
<li>Write a test that covers every subtype without listing them.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/payment-intents</code>", "Create an intent for one method. <code>201</code> with the next action and refund route."]]) + """
<h2>Request body</h2>
""" + table(["Field", "Rule"], [
    ["<code>orderId</code>", "1 to 40 letters, digits, <code>-</code> or <code>_</code>."],
    ["<code>amountPaise</code>", "100 to 10,000,000, whole number."],
    ["<code>method</code>", "An object with <code>type</code> and only that type's fields (below)."]]) + """
""" + table(["type", "Fields"], [
    ["<code>UPI</code>", "<code>vpa</code>: a UPI ID like <code>name@bank</code>"],
    ["<code>CARD</code>", "<code>network</code> (<code>VISA</code>, <code>MASTERCARD</code>, <code>RUPAY</code>), <code>last4</code>, <code>token</code> (<code>tok_…</code>, write-only)"],
    ["<code>NET_BANKING</code>", "<code>bankCode</code>: 4 letters; offered: HDFC, ICIC, KKBK, SBIN, UTIB"],
    ["<code>WALLET</code>", "<code>mobile</code>: 10 digits starting 6 to 9 (write-only; returned as <code>maskedMobile</code>)"]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Intent created"],
    ['<span class="pill warn">400</span>', "Unknown or missing type, a field from another method, or a bad field"],
    ['<span class="pill warn">422</span>', "Net banking at a bank that is not offered"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-upi", "Case 1: UPI", "<b>Why:</b> the UPI ID is normalised to lower-case; the payer approves in their app."),
    ("02-card", "Case 2: a saved card", "<b>Why:</b> the token was accepted but is not in the response: only the network and last 4 digits are."),
    ("03-net-banking", "Case 3: net banking", "<b>Why:</b> <code>hdfc</code> becomes <code>HDFC</code>; the next action is a redirect to a simulated bank page."),
    ("04-wallet", "Case 4: wallet", "<b>Why:</b> the case the old refund code forgot. The refund route is the wallet; the number is masked."),
    ("05-two-methods-at-once", "Case 5: UPI with a card field", "<b>Why:</b> <code>last4</code> is not a UPI field: <code>400</code> instead of guessing which method was meant."),
    ("06-unknown-type", "Case 6: a cheque", "<b>Why:</b> not one of the four types: <code>400</code>."),
    ("07-bank-not-offered", "Case 7: a bank that is not offered", "<b>Why:</b> a valid code shape, but no such option: <code>422</code> listing the banks."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["UPI ID in capitals", "Lower-case; approve in app", "<code>upiAsksThePayerToApproveInTheirApp</code>"],
    ["Card with a token", "Token not in the response", "<code>aCardNeverEchoesItsToken</code>"],
    ["Net banking <code>hdfc</code>; wallet", "Redirect to HDFC; masked mobile", "<code>netBankingRedirectsAndAWalletShowsAMaskedNumber</code>"],
    ["Bank ABCD", "<code>422</code>", "<code>aBankThatIsNotOfferedIs422</code>"],
    ["CHEQUE; no type; bad UPI ID; full card number; short mobile; 99 paise; empty body", "<code>400</code>", "<code>badMethodsAre400</code>"],
    ["Every permitted method", "Registered for JSON; has a next action and refund route", "<code>EveryMethodTest</code>"],
    ["A <code>case</code> removed from a switch", "The build fails (below)", "The compiler"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">One class with nullable fields for every method, so a new method is silently missed.</p>
<p>The first test shows the old refund chain returning <code>null</code> for a wallet. The second shows the old class taking a UPI-and-card payment and picking whichever <code>if</code> comes first. The third shows the sealed model refunding the wallet and refusing the mixed body. While building, making JSON lenient, echoing the token, and unregistering wallets each turned tests red.</p>
</div>
""" + code(read(T + "ForgottenWalletTrapTest.java"), "java") + """
<h2>And when a case is forgotten now</h2>
<p>Removing the wallet branch from <code>refundRoute</code> no longer compiles. This is the real output, saved in <code>docs/missing-case-compile.txt</code>:</p>
<pre class="console">""" + e(read("docs/missing-case-compile.txt")) + """</pre>
"""

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "PaymentIntentController.java", dwn("Validates the request, checks the bank is offered, and builds the intent.",
        "The controller never asks which method it has, except for the one rule that only applies to net banking.",
        "<code>if (vpa != null) … else if …</code> chains.")),
    (J + "PaymentMethod.java", dwn("The sealed interface and its four records, with the JSON type names.",
        "\"Exactly one of\" written as a type: impossible states cannot be built.",
        "One class with four nullable fields.",
        "<ul><li><code>@JsonTypeInfo</code> and <code>@JsonSubTypes</code> map <code>\"type\"</code> to a record.</li><li>Compact constructors normalise UPI IDs and bank codes with <code>Locale.ROOT</code>.</li><li><code>WRITE_ONLY</code> keeps the token and mobile out of responses.</li></ul>")),
    (J + "Methods.java", dwn("Next action and refund route: one switch each, no default.",
        "Record patterns unpack fields in the <code>case</code>; the compiler checks every method is handled.",
        "The trap: a refund chain with no wallet branch.")),
    ("src/main/resources/application.yaml", "<p>Problem bodies for errors, and <code>fail-on-unknown-properties</code>: a field from another method is a <code>400</code>.</p>"),
    (J + "PaymentsApplication.java", "<p>Standard Spring Boot entry point.</p>"),
]
tree = """stations/018-payment-methods-with-sealed-interfaces/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/paysetu/payments/
│   ├── PaymentIntentController.java   ├── PaymentMethod.java
│   ├── Methods.java                   └── PaymentsApplication.java
├── src/test/java/com/paysetu/payments/   (see Tests)
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
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Sealed interfaces, record patterns and pattern-matching switches are all final in Java 21.</p>
<h2>Try it yourself</h2>
<p>The body is in <code>docs/upi-intent.json</code>. Then try adding <code>"last4": "4242"</code> to the method.</p>
""" + code("""# Expect 201 with nextAction APPROVE_IN_UPI_APP
curl -i -X POST http://localhost:8080/payment-intents -H "Content-Type: application/json" -d "@docs/upi-intent.json\"""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>400</code> for a body that looks right", "A field that belongs to another method, or a misspelt one.", "Send only the fields of the chosen <code>type</code>."],
    ["<code>the switch expression does not cover all possible input values</code>", "A method was added and a switch does not handle it.", "Add the <code>case</code>. That error is the feature."],
    ["<code>release version 25 not supported</code>", "Maven is using an older JDK.", "Point <code>JAVA_HOME</code> at JDK 25, or add <code>-Djava.version=21</code>."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found (a bank that is not offered)", f"<code>PaymentIntentContractTest</code> ({cnt('PaymentIntentContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>ForgottenWalletTrapTest</code> ({cnt('ForgottenWalletTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Every permitted method, found by reflection", f"<code>EveryMethodTest</code> ({cnt('EveryMethodTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "ForgottenWalletTrapTest.java", "<p>Written first: the old refund chain's <code>null</code>, the old class's mixed payment, and the sealed model's answers.</p>"),
    (T + "PaymentIntentContractTest.java", "<p>Each method, what is never echoed, and every refusal.</p>"),
    (T + "EveryMethodTest.java", "<p>Builds a placeholder of every permitted record by reflection, so a method added later is tested without editing this file.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app through MockMvc and a helper that posts an intent.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/paysetu/payments/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=ReadBackChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Read an intent back", "Beginner-friendly", 20,
    "Keep each intent in memory, answer <code>GET /payment-intents/{id}</code>, and return a <code>Location</code> header from the POST. An unknown id is <code>404</code>.",
    "both tests in <code>ReadBackChallengeTest</code> pass, and the card token is still never returned.",
    ["A <code>ConcurrentHashMap</code> keyed by id is enough here.",
     "<code>ResponseEntity.created(uri).body(intent)</code> gives the 201 and the header together."],
    "challenge/ReadBackChallengeTest.java", ["challenge/solution/PaymentIntentController.java"]) + challenge(2, "A fifth method: pay later", "Go deeper", 25,
    "Add <code>PAY_LATER</code> (Paysetu Pay Later, fictional) with a <code>mobile</code>. Add the record to the <code>permits</code> list and build: the compiler names every switch that needs a new case.",
    "both tests in <code>PayLaterChallengeTest</code> pass, and <code>EveryMethodTest</code> covers the new method without changes.",
    ["Copy the wallet record's shape: a write-only mobile and a masked one.",
     "Register the JSON name in <code>@JsonSubTypes</code>, or <code>EveryMethodTest</code> will tell you."],
    "challenge/PayLaterChallengeTest.java", ["challenge/solution/PaymentMethod.java", "challenge/solution/Methods.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Switches or methods on the records?</h2>
<p>This station keeps <code>nextAction</code> and <code>refundRoute</code> as switches in one class. They could instead be methods on each record. With twelve methods and six operations, which is easier to change when a method is added, and which when an operation is added? Where would you want the compiler to help?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old refund chain returns <code>null</code> for a wallet.</li>
<li>Write the sealed interface and one record per method, with their own validation.</li>
<li>Map JSON <code>type</code> to records; refuse unknown fields.</li>
<li>Write the switches without <code>default</code>; check by reflection that every method is reachable and handled.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Sealed interface + records + switches", "A switch to update per operation when a method is added; the compiler finds them all.", '<span class="pill ok">Chosen</span>'],
    ["One class with nullable fields", "Impossible states (UPI and card at once); every new method is a hunt.", '<span class="pill bad">Wrong</span>'],
    ["A <code>default</code> branch in each switch", "Compiles when a method is forgotten: the trap, back again.", '<span class="pill bad">Wrong</span>'],
    ["An enum <code>type</code> plus a map of fields", "Loose typing; validation by hand.", '<span class="pill bad">Avoid</span>'],
    ["Methods on each record (polymorphism)", "Easy to add a method, harder to add an operation; logic spread across records.", '<span class="pill warn">Good when operations are few</span>']]) + """
<h2>Database design</h2>
<p>None in this station. With a database: one <code>payment_intents</code> table with a <code>method_type</code> column and a check constraint per type that exactly its own columns are set (for example, <code>method_type = 'UPI'</code> requires <code>vpa</code> and forbids <code>card_last4</code>). The database then refuses mixed methods too.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Card data</dt><dd>In India, RBI's card-on-file tokenisation rules stop merchants from storing card numbers. This API accepts only a token and what may be displayed, and refuses a full number.</dd>
<dt>Privacy</dt><dd>Mobile numbers and tokens are write-only. Logs need the same care: never log the request body as-is.</dd>
<dt>Evolution</dt><dd>A new method changes the API: old clients that do not know <code>PAY_LATER</code> must still read responses. Document new <code>type</code> values before shipping them.</dd>
<dt>Real gateways</dt><dd>UPI, cards and net banking each have their own flows, timeouts and failure states. This station models only the first step.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What does a sealed interface give you?", "A closed list of implementations, known to the compiler. A switch over it can be exhaustive without a default, so adding an implementation makes every incomplete switch a compile error."),
    ("Why no default branch?", "A default branch makes an incomplete switch compile. Without it, the compiler tells you every place a new case must be handled."),
    ("What is a record pattern?", "case Upi(String vpa) -> matches a Upi and binds its component in one step, instead of a cast and a getter."),
    ("How do you read polymorphic JSON safely?", "A type property mapped to known subtypes, so an unknown type fails, and fail-on-unknown-properties, so fields from another type are refused instead of ignored."),
    ("How do you test every subtype without listing them?", "Class.getPermittedSubclasses() gives the list at runtime; build a placeholder of each and check the behaviour, so a new subtype is covered automatically."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can add a method and follow the compiler to every switch."],
    ["Modelling", "One record per method, no nullable fields for other methods.", "You can explain why a default branch brings the trap back."],
    ["Security", "Tokens and mobile numbers are never returned.", "You know why a full card number is refused."],
    ["Explanation", "Sealed interfaces in two sentences.", "Switches versus methods on records, and when each wins."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any "one of several kinds" code:</p>
<ul class="rules">
<li>Can an object be two kinds at once, or none?</li>
<li>Does any switch or if-chain over the kinds have a default that hides a missing case?</li>
<li>Can every kind arrive from JSON, and are other kinds' fields refused?</li>
<li>Is any secret field echoed back in a response or a log?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
