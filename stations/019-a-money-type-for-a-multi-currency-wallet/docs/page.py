"""Station 019 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 19,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · records as value objects · BigDecimal · java.util.Currency · MockMvc",
    "simulation": "Wallet balances are numbers in the app's memory. A credit creates a record; no money moves, no currency is bought or sold, and there are no exchange rates in the station itself.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tijori/wallets/"
T = "src/test/java/com/tijori/wallets/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Value object", "An object defined only by its values: two with the same values are the same thing.", "Two ₹10 notes are interchangeable.", "<code>record Money</code>"),
    ("Minor unit", "The smallest unit of a currency: paise, cents. Some currencies have none.", "₹10.50 is 1,050 paise; ¥1,500 is just 1,500.", "<code>minorUnits</code>"),
    ("Scale", "How many digits a <code>BigDecimal</code> keeps after the point.", "10.5 has scale 1; 10.50 has scale 2.", "Why <code>equals</code> differs from <code>compareTo</code>"),
    ("ISO 4217", "The standard list of currency codes and their minor units.", "INR, USD, AED (2 decimals); JPY (0).", "<code>java.util.Currency</code>"),
    ("Immutable", "Never changes after it is made; operations return a new one.", "Adding to a ₹10 note does not change the note: you get a new total.", "<code>plus</code> returns a new <code>Money</code>"),
    ("Currency-safe", "Arithmetic that refuses to mix currencies.", "A cashier does not add rupees and dollars into one number.", "<code>CurrencyMismatchException</code>"),
]
STORY = [
    ("Asha gets ₹100 of cashback and a $5 refund", "The wallet shows a balance of 105. Of what? The app treats it as rupees."),
    ("A reconciliation check fails", "The ledger says ₹10.5, the bank file says ₹10.50, and the code says they are different amounts, because <code>BigDecimal.equals</code> compares the number of decimals too."),
    ("The fix", "A <code>Money</code> type that stores whole minor units with its currency, refuses to add different currencies, and is compared by value. The wallet keeps one balance per currency."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">An amount without its currency is not money. Make the type carry both, and compare by value.</p>

<h2>What are we building?</h2>
<p><code>POST /wallets/{id}/credits</code> adds an amount in one currency. <code>GET /wallets/{id}/balance</code> shows one balance per currency, each with that currency's own number of decimals.</p>

<h2>An everyday analogy</h2>
<p>A travel pouch with one pocket per currency. Rupees go in the rupee pocket and dollars in the dollar pocket. Nobody counts them together without first asking at what rate.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Read the amount as text</strong>, like <code>"10.5"</code>, with its currency code.</li>
<li><strong>Convert to minor units</strong> for that currency: 1,050 paise. Refuse anything that would lose a digit.</li>
<li><strong>Add to that currency's pocket</strong>; adding a different currency is an error in the type itself.</li>
<li><strong>Show each pocket</strong> with the currency's own decimals: <code>10.50</code> INR, <code>1500</code> JPY.</li>
</ol>

<details class="qa check"><summary>Check yourself: is ₹10.5 the same as ₹10.50? Is 10.50 rupees the same as 10.50 dollars?</summary><p>Yes, then no. Same value in the same currency is the same money, whatever the trailing zeros. The same number in two currencies is two different things.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No currency exchange.</strong> Balances are never added across currencies (challenge 2 adds an indicative total at demo rates).</li>
<li><strong>No debits.</strong> Challenge 1 adds them.</li>
<li><strong>No database.</strong> Two demo wallets live in memory.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tijori</strong> (a fictional fintech app) added foreign-currency wallets for travellers. Its wallet keeps one <code>BigDecimal</code> balance, so a dollar refund was added to rupee cashback. Reconciliation compares amounts with <code>equals</code>, so ₹10.5 and ₹10.50 fail to match and land in a manual-review queue.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> credits of "10.5" and "10.50" INR, <b>then</b> both show as 10.50 and the balance is 21.00.</li>
<li><b>Given</b> ₹100 and $5 credited, <b>then</b> the balance shows 100.00 INR and 5.00 USD, separately.</li>
<li><b>Given</b> "1500" JPY, <b>then</b> 1500 with no decimals; "1500.5" JPY or "10.505" INR is <code>422</code>.</li>
<li><b>Given</b> an unsupported currency or a zero amount, <b>then</b> <code>422</code>; a negative or malformed amount, <code>400</code>.</li>
<li><b>Given</b> an unknown wallet, <b>then</b> <code>404</code>.</li>
<li><b>Given</b> two <code>Money</code> values, <b>then</b> they are equal exactly when the currency and the minor units are equal.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Amounts arrive as decimal strings; up to 999,999 per credit (a demo rule). Currency codes are normalised with <code>Locale.ROOT</code>.</li>
<li>Money is stored as whole minor units with its <code>Currency</code>; conversion to minor units never rounds.</li>
<li>Adding different currencies throws; overflow throws instead of wrapping around.</li>
<li>Supported currencies (a demo set): INR, USD, AED, JPY.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Write a value object as a record: immutable, compared by value.</li>
<li>Explain <code>BigDecimal</code> scale, and why <code>equals</code> and <code>compareTo</code> disagree.</li>
<li>Use <code>Currency.getDefaultFractionDigits</code> instead of assuming two decimals.</li>
<li>Make the wrong operation (rupees plus dollars) impossible to do quietly.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/wallets/{id}/credits</code>", "Add an amount in one currency. <code>201</code> with the credit and that currency's new balance."],
    ["<code>GET</code>", "<code>/wallets/{id}/balance</code>", "One balance per currency."]]) + """
<h2>Request body</h2>
""" + table(["Field", "Rule"], [
    ["<code>amount</code>", "A string like <code>\"10.50\"</code>: digits, optionally a point and up to 4 decimals; at most 999999. The currency decides how many decimals are allowed."],
    ["<code>currency</code>", "Three letters, any case: INR, USD, AED or JPY."],
    ["<code>reference</code>", "1 to 40 characters, echoed back."]]) + """
<h2>Money in responses</h2>
<p><code>{"amount": "10.50", "currency": "INR", "minorUnits": 1050}</code>: the amount as a string with the currency's decimals, and the exact integer for machines.</p>
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Credited"],
    ['<span class="pill ok">200</span>', "Balance"],
    ['<span class="pill warn">400</span>', "A field is missing or malformed (negative, exponent, too large, not 3 letters)"],
    ['<span class="pill warn">404</span>', "No such wallet"],
    ['<span class="pill warn">422</span>', "Unsupported currency, more decimals than the currency has, or zero"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, on a fresh start. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-credit-10.5-inr", "Case 1: ₹10.5", "<b>Why:</b> stored as 1,050 paise and shown with INR's two decimals: 10.50."),
    ("02-credit-10.50-inr", "Case 2: ₹10.50", "<b>Why:</b> the same Money as case 1; the balance is 21.00."),
    ("03-credit-usd", "Case 3: $5", "<b>Why:</b> a new pocket. The INR balance is untouched."),
    ("04-credit-jpy", "Case 4: ¥1,500", "<b>Why:</b> JPY has no minor unit, so 1,500 minor units is ¥1,500 and there is no \".00\"."),
    ("05-balance", "Case 5: the balance", "<b>Why:</b> three balances, sorted by code, never added together."),
    ("06-too-many-decimals", "Case 6: ¥1,500.5", "<b>Why:</b> half a yen cannot be stored: <code>422</code> instead of rounding it away."),
    ("07-unsupported-currency", "Case 7: BTC", "<b>Why:</b> not a currency this wallet holds: <code>422</code>."),
    ("08-unknown-wallet", "Case 8: an unknown wallet", "<b>Why:</b> <code>404</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["10.5 and 10.50 INR", "Equal, same hash code", "<code>equalAmountsAreEqualWhateverTheTrailingZeros</code>"],
    ["₹100 + $5 in code", "<code>CurrencyMismatchException</code>", "<code>addingDifferentCurrenciesIsRefused</code>"],
    ["a + b", "A new value; a and b unchanged", "<code>plusReturnsANewValueAndChangesNeither</code>"],
    ["¥1,500; ₹0.1; ₹0.105; ¥1.5", "1500 JPY; 0.10 INR; refused; refused", "<code>decimalsFollowTheCurrency</code>"],
    ["Long.MAX_VALUE + 1", "<code>ArithmeticException</code>, not a negative balance", "<code>overflowIsAnErrorNotAWrapAround</code>"],
    ["\"10.5\" then \"10.50\" via HTTP; mixed-case ids and codes", "21.00; normalised", "<code>aCreditIsShownInTheCurrencysOwnDecimals</code>"],
    ["JPY with decimals; INR with 3 decimals; \"1500.00\" JPY", "<code>422</code>, <code>422</code>, accepted", "<code>yenHaveNoDecimals</code>"],
    ["No credits yet", "Empty list", "<code>anEmptyWalletHasNoBalances</code>"],
    ["BTC; 0.00; -5; 1e3; 1000000; RUPEES; empty body", "<code>422</code> or <code>400</code>", "<code>badCreditsAreRefused</code>"],
    ["Unknown wallet", "<code>404</code>", "<code>anUnknownWalletIs404</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Adding amounts in different currencies, or comparing <code>BigDecimal</code> with <code>equals</code>.</p>
<p>The first test shows the old wallet's balance of 105 after ₹100 and $5. The second shows <code>equals</code> calling 10.5 and 10.50 different, and a <code>HashSet</code> keeping both, while two <code>Money</code> values are one. The third shows the wallet keeping separate balances. While building, removing the currency check turned a test red, and so did rounding instead of refusing extra decimals. Keying every balance under INR made the <code>Money</code> type itself refuse the addition: the type caught a bug in the code around it.</p>
</div>
""" + code(read(T + "RupeesPlusDollarsTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "WalletController.java", dwn("Validates the request, checks the currency, parses the amount into Money, and adds it to that currency's balance.",
        "<code>ConcurrentHashMap.merge</code> with <code>Money::plus</code>: atomic per currency, and the type does the arithmetic.",
        "One <code>BigDecimal</code> balance per wallet.")),
    (J + "Money.java", dwn("The value object: minor units and a currency.",
        "A record gives value equality for free; the compact constructor and methods keep it correct.",
        "The trap: amounts without currencies, compared with <code>equals</code>.",
        "<ul><li><code>setScale(digits)</code> with no rounding mode throws if a digit would be lost.</li><li><code>plus</code> checks the currency and uses <code>Math.addExact</code>.</li><li><code>amount()</code> formats with the currency's own decimals.</li></ul>")),
    ("src/main/resources/application.yaml", "<p>Problem bodies for every error.</p>"),
    (J + "WalletsApplication.java", "<p>Standard Spring Boot entry point.</p>"),
]
tree = """stations/019-a-money-type-for-a-multi-currency-wallet/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tijori/wallets/
│   ├── WalletController.java   ├── Money.java   └── WalletsApplication.java
├── src/test/java/com/tijori/wallets/   (see Tests)
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
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>The body is in <code>docs/credit.json</code>. Send it twice, once with <code>"10.5"</code>, and compare.</p>
""" + code("""# Credit: expect credited.amount "10.50" and minorUnits 1050
curl -i -X POST http://localhost:8080/wallets/w-asha/credits -H "Content-Type: application/json" -d "@docs/credit.json"

# Balances, one per currency
curl http://localhost:8080/wallets/w-asha/balance""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>404</code>", "Only <code>w-asha</code> and <code>w-ravi</code> exist.", "Use one of them."],
    ["<code>422</code> Too many decimal places", "The currency has fewer decimals (JPY has none).", "Send the amount in that currency's decimals."],
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>WalletContractTest</code> ({cnt('WalletContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>RupeesPlusDollarsTrapTest</code> ({cnt('RupeesPlusDollarsTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "The value object: equality, currency safety, immutability, decimals, overflow", f"<code>MoneyTest</code> ({cnt('MoneyTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "RupeesPlusDollarsTrapTest.java", "<p>Written first: the old balance of 105, <code>equals</code> versus <code>compareTo</code>, and separate balances.</p>"),
    (T + "WalletContractTest.java", "<p>Credits in each currency's decimals, an empty wallet, and every refusal.</p>"),
    (T + "MoneyTest.java", "<p>The value object with no Spring at all.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app through MockMvc, every wallet empty before each test.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tijori/wallets/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=DebitChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Debits", "Beginner-friendly", 25,
    "Add <code>POST /wallets/{id}/debits</code> with the same body. Take the amount from that currency's balance, never below zero; <code>422</code> otherwise.",
    "both tests in <code>DebitChallengeTest</code> pass.",
    ["Add <code>minus</code> to <code>Money</code> by reusing <code>plus</code>; the currency check comes for free.",
     "<code>ConcurrentHashMap.compute</code> is atomic per key, and throwing inside it leaves the balance unchanged."],
    "challenge/DebitChallengeTest.java", ["challenge/solution/Money.java", "challenge/solution/WalletController.java"]) + challenge(2, "An indicative total", "Go deeper", 35,
    "Add <code>?in=USD</code> to the balance: an <code>indicativeTotal</code> converting each balance at demo rates (in rupees: INR 1, USD 88.00, AED 24.00, JPY 0.60), each rounded half-even to the target's decimals, then added.",
    "both tests in <code>IndicativeTotalChallengeTest</code> pass: 16.37 USD, 1440.00 INR, 2400 JPY for the same wallet.",
    ["Convert through rupees: amount × rate of its currency ÷ rate of the target.",
     "Round each converted balance once, then add them as <code>Money</code> in the target currency."],
    "challenge/IndicativeTotalChallengeTest.java", ["challenge/solution/Money.java", "challenge/solution/WalletController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Money in a database</h2>
<p>How would you store <code>Money</code> in PostgreSQL: a <code>bigint</code> of minor units and a <code>char(3)</code> currency, or a <code>numeric</code>? What constraint stops a JPY row from holding a fraction, and what happens if ISO 4217 changes a currency's minor unit?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old balance of 105, and <code>equals</code> on 10.5 and 10.50.</li>
<li>Write <code>Money</code> as a record of minor units and a currency; test it without Spring.</li>
<li>Parse amounts with the currency's decimals, refusing any loss.</li>
<li>Keep one balance per currency in the wallet.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Minor units (<code>long</code>) + <code>Currency</code>", "A conversion at the edges.", '<span class="pill ok">Chosen</span>'],
    ["<code>BigDecimal</code> + currency, compared with <code>compareTo</code>", "Works, but every map, set and <code>equals</code> must remember to normalise the scale first.", '<span class="pill warn">Error-prone</span>'],
    ["<code>BigDecimal</code> with <code>stripTrailingZeros</code>", "10 becomes 1E+1; formatting and equality get surprising.", '<span class="pill bad">Avoid</span>'],
    ["<code>double</code>", "0.1 + 0.2 is not 0.3.", '<span class="pill bad">Wrong</span>'],
    ["A money library (for example JSR 354 / Moneta)", "Another dependency; worth it with many currencies and conversions.", '<span class="pill warn">Later, maybe</span>']]) + """
<h2>Database design</h2>
<p>None in this station. With a database: <code>wallet_balances</code> (wallet_id, currency <code>char(3)</code>, minor_units <code>bigint</code>) with a primary key on (wallet_id, currency) and a check that minor_units is not negative. The currency's decimals stay in code, from ISO 4217.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Regulation</dt><dd>Holding foreign currency for customers in India is regulated. This station shows the data model only.</dd>
<dt>JSON</dt><dd>Amounts travel as strings, with the integer minor units alongside. A client that parses JSON numbers as floating point cannot damage a string.</dd>
<dt>Concurrency</dt><dd><code>merge</code> on a <code>ConcurrentHashMap</code> is atomic per key, so two credits at once both count. A database would need the same guarantee from a row lock or an atomic update.</dd>
<dt>Display</dt><dd>Show the currency with every amount. Formatting for a locale (₹1,00,000.00 or $100,000.00) belongs in the client.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why are new BigDecimal(\"10.5\") and new BigDecimal(\"10.50\") not equal?", "equals compares the unscaled value and the scale: 105 with scale 1 versus 1050 with scale 2. compareTo compares only the value, so it returns 0. HashMap and HashSet use equals and hashCode, so they keep both."),
    ("What makes a good value object?", "Immutable, compared by its values, valid from construction, and with operations that return new values. A Java record gives the first two for free."),
    ("Why store minor units as a long?", "Integers are exact, fast and compare simply. The currency says where the decimal point goes. A long holds more than any wallet needs; addExact turns an overflow into an error."),
    ("How do you stop rupees being added to dollars?", "Make Money carry its currency and make plus refuse a different one. The mistake then fails loudly at the first test, not in a customer's balance."),
    ("Are all currencies two decimals?", "No. ISO 4217 gives each currency's minor unit: JPY has none, some have three. java.util.Currency.getDefaultFractionDigits returns it."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can explain each refusal in the contract test."],
    ["Value objects", "Money is immutable and equal by value.", "You know what a record does and does not give you."],
    ["BigDecimal", "<code>equals</code> versus <code>compareTo</code>.", "Why <code>setScale</code> without rounding throws."],
    ["Explanation", "Why amounts carry their currency.", "Minor units versus BigDecimal, with the trade-offs."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any money code:</p>
<ul class="rules">
<li>Does every amount travel with its currency?</li>
<li>Is any <code>BigDecimal</code> compared with <code>equals</code>, or used as a map key?</li>
<li>Does any code assume two decimals?</li>
<li>Can an addition overflow, and what happens if it does?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
