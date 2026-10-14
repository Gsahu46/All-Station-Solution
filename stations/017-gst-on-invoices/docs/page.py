"""Station 017 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 17,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · BigDecimal · enums with data · TreeMap · MockMvc",
    "simulation": "A tax preview only: nothing is stored, no invoice number is issued and nothing is filed with the GST portal. The rates are demo configuration modelled on how Indian GST rates are structured, not a tax reference and not tax advice.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/billora/invoices/"
T = "src/test/java/com/billora/invoices/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("GST", "India's tax on the supply of goods and services, added to the price on the invoice.", "18% on a ₹1,000 keyboard: ₹180 of tax.", "<code>totalTaxPaise</code>"),
    ("CGST + SGST", "Within one state, the tax is split in two halves: one to the Centre, one to the state.", "9% + 9% for a Bengaluru shop selling to a Bengaluru office.", "<code>cgstPaise</code>, <code>sgstPaise</code>"),
    ("IGST", "Between states, the whole tax is one integrated tax.", "18% IGST for the same shop selling to Mumbai.", "<code>igstPaise</code>"),
    ("Place of supply", "Where the supply is taxed. For goods, usually where they are delivered.", "Delivered to Pune: Maharashtra, code 27.", "<code>placeOfSupply</code>"),
    ("HSN code", "The number that classifies goods; the rate depends on it.", "6109 for T-shirts, 8471 for computers and keyboards.", "<code>hsn</code> on each line"),
    ("Slab", "A rate that applies from one price up to the next.", "T-shirts: 5% up to ₹2,500 a piece, 18% above (demo configuration).", "<code>slabs</code> in <code>application.yaml</code>"),
]
STORY = [
    ("Billora sends an invoice to an office in Bengaluru", "It charges IGST at 18% on everything, T-shirts included. The office is in Karnataka, like Billora: it should have been CGST and SGST, and the T-shirts are 5%."),
    ("The CA compares the totals", "Even with the right rates, Billora's tax is 2 paise more than the CA's, because Billora rounds tax on each line and the CA works it out per rate on the invoice's total."),
    ("The fix", "Decide the tax type from the seller's state and the place of supply. Look rates up by HSN code, date and price from configuration. Add up the taxable value per rate and round the tax once."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Which tax depends on where; how much depends on what, when and for how much. None of it belongs hard-coded.</p>

<h2>What are we building?</h2>
<p><code>POST /invoices/tax-preview</code> takes an invoice date, the place of supply and the lines. It returns each line's rate, a rate-wise tax summary (CGST and SGST, or IGST) and the invoice total. Nothing is stored.</p>

<h2>An everyday analogy</h2>
<p>A school canteen bill: tea and samosas are added up first, then the GST on each is worked out once on its subtotal. Nobody works out the tax on each cup of tea separately and adds the rounded paise.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Where</strong>: same state as the seller means CGST + SGST; another state means IGST.</li>
<li><strong>What, when and how much</strong>: find each line's rate by HSN code, invoice date and price per piece.</li>
<li><strong>Group by rate</strong>: add up the taxable value of all lines at 5%, all at 18%, and so on.</li>
<li><strong>Tax once per rate</strong>, rounded to the paisa, then the invoice total.</li>
</ol>

<details class="qa check"><summary>Check yourself: an 18% sale within a state is 9% CGST + 9% SGST. Is the total tax always the same as 18% IGST?</summary><p>Almost. Each half is rounded on its own, so it can differ by a paisa: the office invoice below is ₹551.42 within Karnataka and ₹551.40 to Maharashtra.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>Not a tax reference.</strong> The rates are demo configuration. Check the current CBIC rate notifications before using any number.</li>
<li><strong>No e-invoice, no filing.</strong> Nothing goes to the GST portal; no invoice number is issued.</li>
<li><strong>Not every rule.</strong> Services, exports, reverse charge, cess and union territories (challenge 2) are left out.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Billora</strong> (a fictional invoicing app for small sellers in Karnataka) charges IGST at a hard-coded 18% on every line. Buyers in Karnataka get the wrong tax type, T-shirts get the wrong rate, and a rate change means a release. Tax is rounded line by line, so the totals never match the CA's rate-wise working.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> the office invoice to a buyer in Karnataka (code 29), <b>then</b> CGST ₹275.71 and SGST ₹275.71, no IGST.</li>
<li><b>Given</b> the same invoice to Maharashtra (27), <b>then</b> IGST ₹551.40, no CGST or SGST.</li>
<li><b>Given</b> an air conditioner invoiced on 21 Sep 2025, <b>then</b> 28%; on 22 Sep 2025, 18% (demo configuration).</li>
<li><b>Given</b> a T-shirt at ₹2,500 a piece, <b>then</b> 5%; at ₹2,500.01, 18%.</li>
<li><b>Given</b> an HSN code with no rate on the invoice date, <b>then</b> <code>422</code> naming the line.</li>
<li><b>Given</b> an unknown state code, a wrong HSN format, no lines or a fraction of a quantity, <b>then</b> <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Amounts are whole paise. Tax is computed per rate on the summed taxable value and rounded half up to the paisa, once.</li>
<li>Within one state each half of the rate is computed and rounded separately; CGST always equals SGST.</li>
<li>Rates live in configuration: per HSN heading, dated sets of price slabs. A change is a new set, added ahead of time.</li>
<li>Demo rules: 4-digit HSN headings; 1 to 100 lines; quantity up to 10,000; at most ₹10 lakh a piece.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Choose CGST + SGST or IGST from the seller's state and the place of supply.</li>
<li>Model states as an enum that carries data (code and name).</li>
<li>Look up a dated, slabbed rate with two <code>TreeMap.floorEntry</code> calls.</li>
<li>Explain why rounding per line and rounding per invoice give different totals.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/invoices/tax-preview</code>", "Lines with their rates, a rate-wise tax summary and totals. <code>200</code>; nothing is stored."]]) + """
<h2>Request body</h2>
""" + table(["Field", "Rule"], [
    ["<code>invoiceDate</code>", "Required, <code>YYYY-MM-DD</code>. Picks the rates."],
    ["<code>placeOfSupply</code>", "Two-digit GST state code, as on an e-invoice: <code>29</code> Karnataka, <code>27</code> Maharashtra, and so on."],
    ["<code>lines</code>", "1 to 100, each with <code>description</code> (up to 80 characters), <code>hsn</code> (4 digits), <code>quantity</code> (1 to 10,000) and <code>unitPricePaise</code> (1 to 100,000,000)."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "Preview computed"],
    ['<span class="pill warn">400</span>', "A field is missing, malformed or out of range, or the state code is unknown"],
    ['<span class="pill warn">422</span>', "No rate for a line's HSN code on the invoice date; the detail names the line"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-same-state", "Case 1: the office invoice, Karnataka to Karnataka", "<b>Why:</b> same state, so each rate is split into CGST and SGST. The 5% lines are added up first (₹2,397 at 2.5% = ₹59.925, rounded to ₹59.93), then the 18% lines (₹2,397.50 at 9% = ₹215.775, rounded to ₹215.78)."),
    ("02-other-state", "Case 2: the same invoice to Maharashtra", "<b>Why:</b> another state, so IGST at the full rate. It is 2 paise less than case 1: one rounding per rate instead of two."),
    ("03-tshirt-before-22-sep-2025", "Case 3: a ₹1,499 T-shirt on 21 Sep 2025", "<b>Why:</b> the rate set valid that day taxes T-shirts above ₹1,000 a piece at 12% (demo configuration)."),
    ("04-tshirt-from-22-sep-2025", "Case 4: the same T-shirt a day later", "<b>Why:</b> a new rate set starts on 22 Sep 2025 with the slab at ₹2,500, so ₹1,499 is 5%. Only configuration changed."),
    ("05-unknown-hsn", "Case 5: an HSN code with no rate", "<b>Why:</b> no rate is guessed: <code>422</code>, naming the line."),
    ("06-unknown-state", "Case 6: state code 99", "<b>Why:</b> not a state in this demo: <code>400</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Seller and buyer in Karnataka", "CGST = SGST, per rate", "<code>aSameStateInvoiceHasCgstAndSgstPerRate</code>"],
    ["Buyer in Maharashtra", "IGST only", "<code>anotherStateGetsIgstOnly</code>"],
    ["AC on 21 and 22 Sep 2025", "28%, then 18%", "<code>theRateIsTheOneValidOnTheInvoiceDate</code>"],
    ["T-shirt at ₹1,000 / ₹1,000.01 (old set); ₹2,500 / ₹2,500.01 (new set)", "5 / 12; 5 / 18", "<code>tShirtSlabsByPricePerPieceAndDate</code>"],
    ["30 Jun 2017 (before GST); an unknown heading", "No rate", "<code>noRateBeforeGstOrForAnUnknownHeading</code>"],
    ["1,000 generated invoices, both supply types", "Within half a paisa per tax head (one paisa per rate within a state); CGST = SGST", "<code>roundingOncePerRateIsWithinHalfAPaisaPerTaxHead</code>"],
    ["HSN 1234 on line 2; a date before GST", "<code>422</code> naming the line", "<code>anUnknownHsnOrADateBeforeGstIs422NamingTheLine</code>"],
    ["State 99 or KA; no lines; HSN 847; price 0; quantity 1.5; date 13-10-2026; empty body", "<code>400</code>", "<code>badFieldsAre400</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Hard-coding rates and charging IGST on same-state sales.</p>
<p>"18% IGST" is right for many sales, so the bug hides. The first test shows the old code charging ₹863.01 on the office invoice. The second shows that fixing the rates is not enough: rounding each line's CGST and SGST adds 2 paise the CA does not have. The third shows the fixed preview. Making every sale IGST while building turned 2 tests red; ignoring the invoice date turned 4 red.</p>
</div>
""" + code(read(T + "WrongTaxTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "TaxPreviewController.java", dwn("Validates the body, finds the place of supply and each line's rate, then builds the summary and totals.",
        "Totals are sums of the rate-wise summary, so the summary and the totals can never disagree.",
        "IGST at 18% on every line.")),
    (J + "TaxPreviewRequest.java", "<p>The body with its rules: a two-digit state code, 4-digit HSN headings, whole paise.</p>"),
    (J + "GstState.java", dwn("States with their GST code and name: an enum with data.",
        "The code is what e-invoices use; the label is what gets printed.",
        "Comparing state names as free text.")),
    (J + "GstRates.java", dwn("Rates from configuration: dated sets of price slabs per HSN heading.",
        "Two <code>floorEntry</code> calls: the set valid on the date, then the slab for the price.",
        "Rates in Java, changed by a release.")),
    (J + "Gst.java", dwn("Supply type, the rate-wise summary and the one rounding.",
        "All tax arithmetic in one small class with its own tests.",
        "The trap: tax rounded per line.",
        "<ul><li>A <code>TreeMap</code> keyed by <code>BigDecimal</code> compares with <code>compareTo</code>, so <code>18</code> and <code>18.00</code> are one rate.</li><li>Within one state, half the rate is computed once and used for both CGST and SGST.</li></ul>")),
    ("src/main/resources/application.yaml", "<p>The seller's state and the demo rate configuration, with problem bodies for errors and no silent truncation of <code>1.5</code>.</p>"),
    (J + "InvoicesApplication.java", "<p>Standard Spring Boot entry point; scans the configuration properties.</p>"),
]
tree = """stations/017-gst-on-invoices/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/billora/invoices/
│   ├── TaxPreviewController.java   ├── TaxPreviewRequest.java   ├── Gst.java
│   ├── GstRates.java               ├── GstState.java            └── InvoicesApplication.java
├── src/main/resources/application.yaml   seller state and rates
├── src/test/java/com/billora/invoices/   (see Tests)
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
<p>The body is in <code>docs/office-invoice.json</code>. Change <code>placeOfSupply</code> to <code>27</code> and compare.</p>
""" + code("""# Expect cgstPaise 27571, sgstPaise 27571, totalTaxPaise 55142
curl -X POST http://localhost:8080/invoices/tax-preview -H "Content-Type: application/json" -d "@docs/office-invoice.json\"""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>400</code> Unknown state code", "Only a demo subset of states is configured.", "Use one of the codes in <code>GstState</code>, or add one."],
    ["<code>422</code> No GST rate", "The HSN heading has no rate on that date.", "Add it to <code>billora.hsn-rates</code>, or check the date (GST started on 1 Jul 2017)."],
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
    ["Every station", "HTTP contract: valid, invalid, not found (no rate for an HSN)", f"<code>TaxPreviewContractTest</code> ({cnt('TaxPreviewContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>WrongTaxTrapTest</code> ({cnt('WrongTaxTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Rates on boundary dates and prices; rounding on 1,000 generated invoices", f"<code>GstRatesTest</code> ({cnt('GstRatesTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "WrongTaxTrapTest.java", "<p>Written first: the old code's ₹863.01, 2 paise from per-line rounding, and the fixed preview.</p>"),
    (T + "TaxPreviewContractTest.java", "<p>Same state, another state, a rate change, and every refusal.</p>"),
    (T + "GstRatesTest.java", "<p>The configured rates on their boundary days and prices, and 1,000 generated invoices against the exact tax.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app through MockMvc and the office invoice.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/billora/invoices/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=DiscountChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Line discounts", "Beginner-friendly", 25,
    "Add an optional <code>discountPaise</code> to each line. Tax is on the value after the discount, and the price slab uses the price of one piece after the discount (this station's rule).",
    "all three tests in <code>DiscountChallengeTest</code> pass: two ₹2,600 jerseys with ₹400 off are 5%, not 18%.",
    ["Work out the line's taxable value first, then divide by the quantity for the slab price.",
     "A discount of the whole line or more is <code>422</code>; a negative one is <code>400</code> from validation."],
    "challenge/DiscountChallengeTest.java", ["challenge/solution/TaxPreviewRequest.java", "challenge/solution/TaxPreviewController.java", "challenge/solution/Gst.java"]) + challenge(2, "A seller in a union territory", "Go deeper", 30,
    "Add Chandigarh (code 04), a union territory. When the seller and the place of supply are both Chandigarh, the second half is UTGST, not SGST. The response gets <code>utgstPaise</code>.",
    "both tests in <code>UnionTerritoryChallengeTest</code> pass, and the station's tests still pass.",
    ["Give <code>GstState</code> one more piece of data: whether it is a union territory.",
     "The test sets <code>billora.seller-state=CHANDIGARH</code>; the seller's state is already configuration."],
    "challenge/UnionTerritoryChallengeTest.java", ["challenge/solution/GstState.java", "challenge/solution/Gst.java", "challenge/solution/TaxPreviewController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Whole rupees on the invoice</h2>
<p>Many invoices end with a "round off" line so the amount payable is in whole rupees. Where would you add it: per rate, per tax head, or only on the grand total? What must the API return so an accountant can still match every tax head to the paisa?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old code's tax, and the 2 paise from per-line rounding.</li>
<li>Model states as an enum with their codes; decide the supply type from the seller and the place of supply.</li>
<li>Move rates into configuration as dated slabs; look them up with <code>floorEntry</code>; test the boundaries.</li>
<li>Group lines by rate and round once; test 1,000 generated invoices against the exact tax.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Rates in dated configuration, tax per rate", "A configuration format to learn.", '<span class="pill ok">Chosen</span>'],
    ["Rates hard-coded in Java", "A release per rate change; old invoices can no longer be recomputed.", '<span class="pill bad">Wrong</span>'],
    ["Tax rounded per line", "Totals drift from the rate-wise summary by paise.", '<span class="pill bad">Wrong here</span>'],
    ["Per-line tax shown, adding up to the summary", "Needs the remainder rule from station 015 to hand out the rounding paise.", '<span class="pill warn">If lines must show tax</span>'],
    ["States as free-text names", "\"Karnataka\", \"karnataka\" and \"KA\" are three states.", '<span class="pill bad">Wrong</span>']]) + """
<h2>Database design</h2>
<p>None in this station. With a database: <code>gst_rates</code> (hsn, valid_from, from_paise, percent) with a unique key on (hsn, valid_from, from_paise) and a check that the percent is not negative. An invoice stores the rate it used on each line, so a later rate change never rewrites it.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Rate changes</dt><dd>Added as a new dated set before the day they apply, reviewed like code. Invoices dated before the change keep the old rates.</dd>
<dt>Money</dt><dd>Whole paise in and out; <code>BigDecimal</code> only for the percentage. One rounding per rate and tax head.</dd>
<dt>Compliance</dt><dd>Real invoices also need GSTINs, invoice numbers, e-invoice reporting above the turnover limit, and HSN digits that depend on turnover. Check current rules with a tax professional.</dd>
<dt>Testing</dt><dd>Every rate set has tests on the day before and the day it starts, and on each side of every price slab.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("When do you charge CGST + SGST and when IGST?", "Compare the seller's state with the place of supply. The same state means CGST + SGST, half the rate each; different states mean IGST at the full rate."),
    ("Why not hard-code GST rates?", "They change by date and sometimes by price. Configuration with start dates lets you add a change ahead of time and still recompute an old invoice with the rate valid on its date."),
    ("How do you find a slab or a dated rate?", "Put the starts in a TreeMap and call floorEntry: the latest start on or before the date, or the price."),
    ("Why does rounding per line give a different total?", "Each line's rounding error is up to half a paisa, and they can all go the same way. Summing first and rounding once keeps the error to half a paisa per rate."),
    ("What is an enum with data?", "Each constant carries fields, like a state's code and name, so lookups and labels live in one place and an unknown value cannot exist."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can work out the office invoice's tax by hand."],
    ["Tax rules", "CGST + SGST versus IGST, from the states.", "You know why the two can differ by a paisa."],
    ["Configuration", "Rates by date and slab, with boundary tests.", "You can add a rate change without touching Java."],
    ["Explanation", "Per-line versus per-rate rounding in two sentences.", "How you would show per-line tax that still adds up."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any tax code:</p>
<ul class="rules">
<li>Is a rate, or the tax type, a constant in code?</li>
<li>Which date picks the rate, and is there a test on the day a rate changes?</li>
<li>Where does rounding happen, and do the totals match a rate-wise summary?</li>
<li>Are states compared by code, or by free text?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
