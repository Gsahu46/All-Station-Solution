"""Station 016 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 16,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · BigDecimal · MathContext · TreeMap · MockMvc",
    "simulation": "A quote is a record in the app's memory. No loan is sanctioned and no money moves. The rates are demo numbers, not any bank's, and nothing here is financial advice.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tijori/loans/"
T = "src/test/java/com/tijori/loans/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("EMI", "Equated Monthly Instalment: the same payment every month that repays a loan with its interest.", "₹23,769 a month for 2 years on a ₹5 lakh personal loan.", "<code>emiPaise</code>"),
    ("Principal", "The amount borrowed. Each EMI repays part of it.", "The ₹5 lakh itself.", "<code>principalPaise</code>"),
    ("Interest for a month", "What is still owed × the yearly rate ÷ 12.", "₹5,00,000 × 12.99% ÷ 12 = ₹5,412.50 in month 1.", "<code>interestPaise</code> in each row"),
    ("Amortisation schedule", "A month-by-month table: how much of each EMI is interest, how much repays principal, and what is left.", "The table a bank attaches to the loan agreement.", "<code>GET /loan-quotes/{id}/schedule</code>"),
    ("Final adjustment", "The last instalment pays exactly what is left, so the loan closes at zero.", "The last EMI is ₹11.91 smaller.", "<code>lastEmiPaise</code>"),
    ("Dated rate", "A rate that applies from a given day until the next one starts.", "\"12.99% from 1 October\".", "<code>tijori.rates</code> in <code>application.yaml</code>"),
]
STORY = [
    ("Meera checks her EMI in the Tijori app", "₹5 lakh, 24 months, 12.99%: the app says ₹23,766. The bank's letter says ₹23,769. She asks support which one is wrong."),
    ("Two years later", "The app's schedule shows her last month leaving a balance of −₹11.91: she would have paid more than she owed, and the loan never shows \"closed\"."),
    ("The fix", "Compute the formula with full precision and round once, at the end. Then work out each month's interest on what is left, and let the last instalment pay exactly the remainder."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Round once, as late as possible, and let the last instalment absorb what rounding left behind.</p>

<h2>What are we building?</h2>
<p><code>POST /loan-quotes</code> takes a product, an amount and a tenure, picks the rate valid today, and returns the EMI and the totals. <code>GET /loan-quotes/{id}/schedule</code> shows every month: interest, principal and the balance, ending at exactly zero.</p>

<h2>An everyday analogy</h2>
<p>Paying back a friend ₹1,000 in three goes: you say "₹334 each time". After two payments you owe ₹332, not ₹334. You pay ₹332 the last time; you don't pay ₹334 and ask for ₹2 back.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Pick the rate</strong> valid on today's date for the product.</li>
<li><strong>Compute the EMI</strong> with the formula, every step at full precision; round once, to whole rupees.</li>
<li><strong>Walk the months</strong>: interest on what is left, the rest of the EMI repays principal.</li>
<li><strong>Close the loan</strong>: the month that would go below zero pays only what is left.</li>
</ol>

<details class="qa check"><summary>Check yourself: the EMI was rounded up from ₹23,768.56 to ₹23,769. Does the customer pay too much?</summary><p>Each month a little more principal is repaid, so the last instalment is smaller by exactly the overpayment: ₹23,757.09. In total they pay interest only on what they actually owed.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>Not a real loan.</strong> No sanction, no credit check, no money moves.</li>
<li><strong>Not a bank's exact method.</strong> Real lenders add processing fees, broken-period interest for the first month and their own rounding rules.</li>
<li><strong>No database.</strong> Quotes live in memory and are gone when the app stops.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tijori</strong> (a fictional lending app) shows an EMI before the loan is booked. It differs from the bank's by ₹3, because the app rounds an intermediate step. Its schedule repeats the same rounded EMI every month, so the last month never closes the loan to zero. Both look like mistakes to customers, and both are.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> ₹5,00,000 at 12.99% for 24 months, <b>then</b> the EMI is ₹23,769 and the last instalment is ₹23,757.09.</li>
<li><b>Given</b> ₹1,00,000 at 12% for 12 months, <b>then</b> the EMI is ₹8,885 (the textbook ₹8,884.88, rounded).</li>
<li><b>Given</b> any schedule, <b>then</b> the principal parts add up to the loan exactly, no balance goes below zero, and the last balance is zero.</li>
<li><b>Given</b> a quote on 19 October 2026, <b>then</b> the personal-loan rate is 12.99% (valid from 1 October), not 13.50%.</li>
<li><b>Given</b> a product whose first rate starts later, <b>then</b> <code>422</code>.</li>
<li><b>Given</b> an amount or tenure out of range, <b>then</b> <code>400</code>; an unknown quote id, <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Amounts in paise: ₹10,000 to ₹1 crore (a demo rule). Tenure 6 to 360 months.</li>
<li>The EMI is rounded half up to whole rupees, once. Monthly interest is rounded half up to the paisa.</li>
<li>Rates come from configuration, each with a start date. A new rate is a new line, added ahead of time.</li>
<li>The schedule is recomputed from the stored quote, with the rate the quote was given.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Implement the EMI formula with <code>BigDecimal</code> and a <code>MathContext</code>.</li>
<li>Explain where rounding happens, and why the last instalment differs.</li>
<li>Build an amortisation schedule and test that it always closes at zero.</li>
<li>Pick a dated value with <code>TreeMap.floorEntry</code>, and make "today" testable with a <code>Clock</code>.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/loan-quotes</code>", "Quote a loan at today's rate. <code>201</code> with a <code>Location</code> to its schedule."],
    ["<code>GET</code>", "<code>/loan-quotes/{id}/schedule</code>", "Month-by-month rows for a quote."]]) + """
<h2>Request body</h2>
""" + table(["Field", "Rule"], [
    ["<code>product</code>", "<code>PERSONAL</code>, <code>HOME</code> or <code>GOLD</code>."],
    ["<code>principalPaise</code>", "1,000,000 to 1,000,000,000 (₹10,000 to ₹1 crore), whole number."],
    ["<code>tenureMonths</code>", "6 to 360."]]) + """
<h2>Response</h2>
""" + table(["Field", "Meaning"], [
    ["<code>annualRatePercent</code>, <code>rateValidFrom</code>", "The rate used, and the day it started."],
    ["<code>instalments</code>", "How many payments. Usually the tenure; fewer when a rounded-up EMI repays a small loan early."],
    ["<code>emiPaise</code>, <code>lastEmiPaise</code>", "The monthly instalment, and the adjusted last one."],
    ["<code>totalInterestPaise</code>, <code>totalPayablePaise</code>", "Sums over the schedule, not EMI × months."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Quote created"],
    ['<span class="pill ok">200</span>', "Schedule"],
    ['<span class="pill warn">400</span>', "A field is missing, out of range or of the wrong type"],
    ['<span class="pill warn">404</span>', "No quote with this id"],
    ['<span class="pill warn">422</span>', "No rate for this product is valid today"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, so "today" is that date. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-personal-quote", "Case 1: ₹5 lakh personal loan, 24 months", "<b>Why:</b> the 12.99% rate started on 1 October 2026. The EMI ₹23,768.56 is rounded once to ₹23,769; the last instalment is ₹11.91 smaller, so the total is less than 24 × EMI."),
    ("02-schedule", "Case 2: its schedule", "<b>Why:</b> each month's interest is on what is left, so the interest part shrinks and the principal part grows. Row 24 pays exactly the remaining balance and ends at 0."),
    ("03-home-quote", "Case 3: ₹50 lakh home loan, 20 years", "<b>Why:</b> month 1's interest alone is ₹35,416.67 of the ₹43,391 EMI: long loans repay little principal at first."),
    ("04-small-long-loan", "Case 4: ₹10,000 for 30 years", "<b>Why:</b> ₹110.54 rounds up to ₹111; 46 paise more each month repays the loan in 344 instalments, not 360. The schedule stops when the balance reaches zero instead of going below it."),
    ("05-gold-no-rate-yet", "Case 5: a product with no rate today", "<b>Why:</b> the gold-loan rate starts on 1 January 2027. No rate is guessed: <code>422</code>."),
    ("06-tenure-too-short", "Case 6: 3 months", "<b>Why:</b> below the 6-month minimum: <code>400</code>. Spring's default detail does not say which field; station 006 shows how to add that."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["₹1,00,000 at 12% for 12 months", "EMI ₹8,885", "<code>aTextbookExample</code>"],
    ["80 combinations of amount, rate and tenure", "Each closes at 0, repays the principal exactly, never goes negative", "<code>everyCombinationClosesAtZeroAndRepaysThePrincipalExactly</code>"],
    ["₹10,000 at 12.99% for 360 months", "Repaid in 344 instalments", "<code>aSmallLongLoanWhoseEmiWasRoundedUpClosesEarlyInsteadOfGoingNegative</code>"],
    ["The day before and the day a new rate starts", "Old rate; new rate", "<code>theRateIsTheOneValidOnTheDay</code>"],
    ["₹5 lakh personal loan", "201, 12.99%, last EMI 11.91 smaller", "<code>aQuoteUsesTheRateValidTodayAndPointsToItsSchedule</code>"],
    ["₹50 lakh home loan, 240 months", "240 rows; month 1 interest ₹35,416.67; ends at 0", "<code>theScheduleHasOneRowPerMonthAndEndsAtZero</code>"],
    ["GOLD before its first rate", "<code>422</code>", "<code>aProductWithNoRateYetIs422</code>"],
    ["₹9,999.99; 5 or 361 months; CAR; empty body", "<code>400</code>", "<code>outOfRangeOrMissingFieldsAre400</code>"],
    ["Unknown quote id", "<code>404</code>", "<code>anUnknownQuoteIs404</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Rounding every instalment the same way, so the last one never closes the loan.</p>
<p>A schedule that subtracts the same rounded EMI 24 times ends at −1,191 paise: the customer overpays ₹11.91. A calculator that keeps four decimals turns <code>(1+r)^24</code> = 1.294862 into 1.2949 and quotes ₹23,766 instead of ₹23,769: the ₹3 support tickets. The real schedule rounds once and adjusts the last instalment. Removing the final adjustment and the cap while building turned 5 tests red. Testing every combination also found a second case: a small loan over 30 years whose rounded-up EMI repays it before month 360. That month now pays only what is left, and the schedule ends there.</p>
</div>
""" + code(read(T + "LastInstalmentTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "LoanQuoteController.java", dwn("Validates the request, picks today's rate, builds the schedule once for the totals, stores the quote.",
        "Totals are sums over the real schedule, so they include the adjusted last instalment.",
        "EMI × months as the total payable.")),
    (J + "Emi.java", dwn("The formula and the schedule, in <code>BigDecimal</code>.",
        "All money arithmetic in one small class with its own tests.",
        "The trap: rounding early, and the same EMI every month.",
        "<ul><li><code>MathContext.DECIMAL128</code>: 34 significant digits for every step, so rounding only happens where the code says.</li><li>The EMI is rounded once; each month's interest is rounded to the paisa.</li><li>The last month, or any month that would go below zero, pays exactly what is left.</li></ul>")),
    (J + "RateTable.java", dwn("Dated rates from <code>application.yaml</code>; the rate on a day.",
        "<code>TreeMap.floorEntry(date)</code> is \"the latest start date on or before this day\" in one call.",
        "A single rate per product, edited on the day it changes.")),
    (J + "Product.java", "<p>The three products. An unknown name is a <code>400</code>.</p>"),
    ("src/main/resources/application.yaml", "<p>The dated rates (demo numbers), problem bodies for errors, and no silent truncation of <code>2.5</code> to <code>2</code>.</p>"),
    (J + "LoansApplication.java", "<p>Entry point, and the <code>Clock</code> in India's time zone, so tests can fix \"today\".</p>"),
]
tree = """stations/016-loan-emi-calculator-and-schedule/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tijori/loans/
│   ├── LoanQuoteController.java   ├── Emi.java   ├── RateTable.java
│   ├── Product.java               └── LoansApplication.java
├── src/main/resources/application.yaml   the dated rates
├── src/test/java/com/tijori/loans/   (see Tests)
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
<p>The body is in <code>docs/personal-loan.json</code> (₹5 lakh, 24 months).</p>
""" + code("""# Quote: expect emiPaise 2376900 and lastEmiPaise 2375709 (at the 12.99% rate valid from 1 Oct 2026)
curl -i -X POST http://localhost:8080/loan-quotes -H "Content-Type: application/json" -d "@docs/personal-loan.json"

# The schedule: use the Location header from the quote
curl http://localhost:8080/loan-quotes/<id>/schedule""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["A different rate than the examples", "Rates depend on today's date.", "Check <code>tijori.rates</code>: the latest <code>from</code> on or before today wins."],
    ["<code>422</code> for GOLD", "Its first rate starts on 1 Jan 2027.", "Add an earlier line in <code>application.yaml</code> to experiment."],
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>LoanQuoteContractTest</code> ({cnt('LoanQuoteContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>LastInstalmentTrapTest</code> ({cnt('LastInstalmentTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "The formula, every combination closing at zero, rate dates", f"<code>EmiTest</code> ({cnt('EmiTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "LastInstalmentTrapTest.java", "<p>Written first: −₹11.91 left by the same EMI every month, ₹3 lost by an early rounding, and the real schedule closing at zero.</p>"),
    (T + "LoanQuoteContractTest.java", "<p>A quote at today's rate, its schedule, and every refusal.</p>"),
    (T + "EmiTest.java", "<p>A textbook value, 80 combinations that must close at zero, a loan that closes early, and rates on their boundary days.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app through MockMvc, with \"today\" fixed at 19 Oct 2026 by a test <code>Clock</code>.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tijori/loans/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=PrepaymentChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Part-prepayment", "Go deeper", 35,
    "Add <code>?prepayMonth=6&amp;prepayPaise=10000000</code> to the schedule: ₹1 lakh paid after month 6's EMI. Keep the EMI; the loan ends sooner. Each row gets <code>prepaidPaise</code>.",
    "all three tests in <code>PrepaymentChallengeTest</code> pass: 20 instalments instead of 24.",
    ["The schedule already stops when the balance reaches zero; a prepayment only lowers the balance one month.",
     "Refuse a prepayment that would clear the whole balance (that is a foreclosure), or one after the last EMI: <code>422</code>.",
     "One parameter without the other is a <code>400</code>."],
    "challenge/PrepaymentChallengeTest.java", ["challenge/solution/Emi.java", "challenge/solution/LoanQuoteController.java"]) + challenge(2, "Quote for a disbursal date", "Beginner-friendly", 20,
    "Add an optional <code>disbursalDate</code>. The rate is the one valid on that date, so a gold loan disbursed on 5 Jan 2027 can be quoted today. Demo rule: today to 90 days ahead.",
    "all three tests in <code>DisbursalDateChallengeTest</code> pass.",
    ["<code>rateOn</code> already takes a date: pass the disbursal date instead of today.",
     "A <code>LocalDate</code> field in the body is parsed from <code>2027-01-05</code>; any other format is a <code>400</code> on its own."],
    "challenge/DisbursalDateChallengeTest.java", ["challenge/solution/LoanQuoteController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Lower EMI or shorter loan?</h2>
<p>After a prepayment, lenders often offer a choice: keep the EMI and shorten the tenure, or keep the tenure and lower the EMI. Sketch both schedules for the challenge 1 loan. Which saves more interest, and why? What would the API need to let the customer choose, and what must the quote show before they do?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the same EMI every month ends at −₹11.91; an early rounding costs ₹3.</li>
<li>Write the formula in <code>BigDecimal</code> with one <code>MathContext</code>; check it against a textbook value.</li>
<li>Write the schedule with the final adjustment; test 80 combinations for zero, exact principal, no negative balance.</li>
<li>Move rates into configuration with start dates; inject a <code>Clock</code>.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["<code>BigDecimal</code> + <code>MathContext</code>, round once", "Verbose arithmetic.", '<span class="pill ok">Chosen</span>'],
    ["<code>double</code> and <code>Math.pow</code>", "Fine for the EMI shown to 2 decimals most of the time; wrong at the paisa now and then, and hard to prove.", '<span class="pill bad">Not for money</span>'],
    ["Rounding each step to 2 or 4 decimals", "Small errors grow through the power and the division: the ₹3 bug.", '<span class="pill bad">Wrong</span>'],
    ["EMI to the paisa instead of whole rupees", "Last instalment differs less, but still differs: the adjustment is still needed.", '<span class="pill warn">A lender\'s choice</span>'],
    ["Rates hard-coded in Java", "A release for every rate change, and old quotes can no longer be explained.", '<span class="pill bad">Wrong</span>']]) + """
<h2>Database design</h2>
<p>None in this station. With a database: <code>rates</code> (product, valid_from, annual_percent) with a unique key on (product, valid_from) and a check that the rate is positive; <code>quotes</code> store the rate itself, not a reference that could change.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Money</dt><dd>Paise in, paise out; <code>BigDecimal</code> only in between. Totals come from the schedule, so the quote and the schedule can never disagree.</dd>
<dt>Rates</dt><dd>A new rate is added before its start date, never edited in place: a quote can always be explained by the rate valid on its date.</dd>
<dt>Time</dt><dd>"Today" is in India's time zone. A server in UTC would quote the old rate for the first five and a half hours of the day a rate changes.</dd>
<dt>Regulation</dt><dd>Real lenders must show the rate, fees and total cost in a key fact statement before the loan. This station shows how the numbers are computed, not the full disclosure.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is the EMI formula?", "EMI = P × r × (1+r)^n ÷ ((1+r)^n − 1), where P is the principal, r the monthly rate (annual ÷ 12 ÷ 100) and n the number of months."),
    ("Why does the last instalment differ?", "The EMI is rounded, so every month repays a little more or less principal than the exact formula. The last instalment pays exactly what is left, so the loan closes at zero."),
    ("Why BigDecimal with a MathContext?", "BigDecimal is exact for decimals, but dividing can need infinitely many digits. A MathContext says how many significant digits to keep, so the code controls where rounding happens."),
    ("How do you find the rate valid on a date?", "Keep rates in a TreeMap keyed by start date and call floorEntry(date): the latest start on or before that day."),
    ("Why inject a Clock?", "So tests can fix today and check the rate on a boundary day, instead of tests that pass or fail depending on when they run."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can compute month 1's interest and principal by hand."],
    ["Money", "Rounding happens once for the EMI and once per month for interest.", "You can explain the ₹3 and the ₹11.91."],
    ["Tests", "A schedule invariant tested on many combinations.", "You can say what bug those combinations found."],
    ["Explanation", "The final adjustment in two sentences.", "Lower EMI vs shorter loan after a prepayment."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any loan or interest code:</p>
<ul class="rules">
<li>Is any amount or rate a <code>double</code>?</li>
<li>Where does rounding happen, and how many times?</li>
<li>Does the schedule end at exactly zero, for every amount and tenure tested?</li>
<li>Where do rates come from, and which one applies on the day a rate changes?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
