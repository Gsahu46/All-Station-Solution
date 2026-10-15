"""Station 034 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 34,
    "stack": "Spring Boot 4.1.1 · Java 25 · Streams: groupingBy, reducing, sorted map entries · BigDecimal · java.time zones · MockMvc",
    "simulation": "Outlets and sales are generated demo data, not Tiffino's: 7 days of bills for 40 outlets, created with fixed seeds when the app starts. Nothing is read from a real till.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tiffino/reports/"
T = "src/test/java/com/tiffino/reports/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]
import json
YESTERDAY = json.loads(read("docs/captures/01-yesterdays-report.txt").split("\n\n")[2])   # the captured body

# ---------- Level 1: Understand ----------
TERMS = [
    ("Group by", "Put items into buckets by a key, then total each bucket.", "Sorting receipts into one envelope per outlet.", "<code>groupingBy(Sale::outletId, …)</code>"),
    ("Reduce", "Combine many values into one, two at a time.", "Adding up a pile of receipts.", "<code>reducing(ZERO, Totals::of, Totals::plus)</code>"),
    ("BigDecimal", "An exact decimal number, for amounts like 261.45.", "Counting money in coins, not by weight.", "<code>Sale.amountRupees</code>"),
    ("double", "A fast binary number that cannot store most decimals exactly.", "A ruler with marks that never land on 0.1.", "the trap"),
    ("Mutable key", "A map key whose fields can change after it is stored.", "Re-labelling an envelope after filing it.", "<code>OldDailyReport.OutletHourKey</code>"),
    ("Business day", "The day as the business sees it: midnight to midnight in India.", "A shop's day ends at its own midnight, not London's.", "<code>INDIA</code>"),
]
STORY = [
    ("Every morning, a spreadsheet", "Someone copies 40 outlets' till totals into a sheet by hand. It takes an hour, and a typo once doubled an outlet's sales."),
    ("The first program is a little wrong", "It adds rupees as <code>double</code>, so ₹293.90 becomes ₹293.89. It also reuses one key object while grouping, and every row comes out labelled with the last bill's outlet and hour."),
    ("The fix", "Group with immutable keys, add exact decimals, convert to paise once, and count the day from midnight in India."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Money adds up exactly or not at all, and a key must never change once it is in a map.</p>

<h2>What are we building?</h2>
<p><code>GET /reports/daily-sales?date=…</code> gives one day's sales for the whole chain: each outlet's total, number of bills and busiest hour, highest first, and the chain's total per hour.</p>

<h2>An everyday analogy</h2>
<p>A cashier closing the day: receipts sorted into one envelope per counter, each envelope added up in rupees and paise, envelopes ranked by total. Nobody re-labels an envelope after it is filed.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Find the day's bills</strong>: from midnight to midnight in India.</li>
<li><strong>Group them</strong> by outlet, by hour, and by outlet and hour.</li>
<li><strong>Add up each group</strong> exactly, and count the bills.</li>
<li><strong>Sort and convert</strong>: outlets highest first, amounts to whole paise.</li>
</ol>

<details class="qa check"><summary>Check yourself: why is a bill at 00:05 on the 14th in India not on the 13th's report, although the server's clock still says the 13th?</summary><p>The server runs in UTC, five and a half hours behind India. The outlet's day, and the owner's report, follow India's midnight.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No database.</strong> Seven days of generated bills in memory.</li>
<li><strong>No refunds or taxes split out.</strong> A bill's amount is what the till printed.</li>
<li><strong>No live day.</strong> Reports are for days that are over.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tiffino</strong> (a fictional restaurant chain) has 40 outlets. Owners get daily totals per outlet and per hour from a spreadsheet someone fills by hand.</p>

<h2>Acceptance criteria</h2>
<p class="muted">On a small test day whose totals can be checked by hand (<code>Fixture</code>).</p>
<ol class="gwt">
<li><b>Given</b> bills of ₹261.45, ₹157.40 and ₹524.95 at TF-01, <b>then</b> its total is exactly 94,380 paise.</li>
<li><b>Given</b> ₹188.95 and ₹104.95 at TF-02, <b>then</b> 29,390 paise, not 29,389.</li>
<li><b>Given</b> a bill at 00:05 India time on the 14th and one at 00:10 on the 15th, <b>then</b> the first is on the 14th's report and the second is not.</li>
<li><b>Given</b> two outlets with equal totals, <b>then</b> the lower outlet id first; two hours with equal sales, <b>then</b> the earlier hour is the busiest.</li>
<li><b>Given</b> a day with no bills, <code>404</code>; today or a future day, <code>422</code>; a missing or malformed date, <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Amounts are summed exactly (<code>BigDecimal</code>) and returned as integer paise.</li>
<li>Group keys are immutable: <code>String</code>, <code>Integer</code>, or a record.</li>
<li>The day and the hours are India's (<code>Asia/Kolkata</code>).</li>
<li>A bill with a fraction of a paisa is an error, not something to round quietly.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Group and total with <code>Collectors.groupingBy</code> and <code>reducing</code>.</li>
<li>Sum <code>BigDecimal</code> with <code>reduce</code>, and know why <code>double</code> is wrong for money.</li>
<li>Sort map entries by value, then by key.</li>
<li>Compare a stream with a loop, and choose for readability.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/reports/daily-sales?date=YYYY-MM-DD</code>", "One day's totals: per outlet (highest first) and per hour."]]) + """
<h2>Response fields</h2>
""" + table(["Field", "Meaning"], [
    ["<code>chainTotalPaise</code>, <code>bills</code>", "The whole chain for the day."],
    ["<code>outlets[]</code>", "<code>outletId</code>, <code>name</code>, <code>totalPaise</code>, <code>bills</code>, <code>busiestHour</code> (0 to 23, India time). Highest total first."],
    ["<code>hours[]</code>", "<code>hour</code>, <code>totalPaise</code>, <code>bills</code> for the whole chain. Only hours with bills, in order."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "A past day with bills"],
    ['<span class="pill warn">400</span>', "No date, or not <code>YYYY-MM-DD</code>"],
    ['<span class="pill warn">404</span>', "A past day with no bills"],
    ['<span class="pill warn">422</span>', "Today or later in India: the day is not over"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. The demo data covers the 7 days before the app started, so the capture asks for yesterday. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-yesterdays-report", "Case 1: yesterday", f"<b>Why:</b> {YESTERDAY['bills']:,} bills from {len(YESTERDAY['outlets'])} outlets, totalled per outlet and per hour."),
    ("02-a-day-with-no-sales", "Case 2: eight days ago", "<b>Why:</b> before the demo data starts: <code>404</code>."),
    ("03-today-is-not-over", "Case 3: today", "<b>Why:</b> the day has not ended in India: <code>422</code>."),
    ("04-a-date-in-another-format", "Case 4: <code>14-10-2026</code>", "<b>Why:</b> not ISO: <code>400</code>."),
    ("05-no-date", "Case 5: no date", "<b>Why:</b> <code>400</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Bills at 00:05 on the day and 00:10 the next day, India time", "The first counts, the second does not", "<code>theDayIsMidnightToMidnightInIndia</code>"],
    ["Names, bill counts and busiest hours", "As on the fixture", "<code>eachOutletHasNameBillsAndBusiestHour</code>"],
    ["Equal totals; equal hours", "Lower id first; earlier hour", "<code>equalTotalsAreOrderedByOutletIdAndEqualHoursByTheEarlierOne</code>"],
    ["A bill of ₹10.005", "An error, not a rounding", "<code>aFractionOfAPaisaIsAnErrorNotARounding</code>"],
    ["Seven days of demo bills", "A plain loop over paise gives the same totals", "<code>bothWaysGiveTheSameTotals</code>"],
    ["The whole response", "Exactly as expected, field by field", "<code>aClosedDayHasTotalsPerOutletAndPerHour</code>"],
    ["No bills; today; next year; no date; 30 February", "<code>404</code>; <code>422</code>; <code>422</code>; <code>400</code>; <code>400</code>", "<code>DailySalesContractTest</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Summing money in double, and grouping by a mutable key.</p>
<p>The first test shows <code>(188.95 + 104.95) * 100</code> is <code>29389.999999999996</code> in <code>double</code>, so the old report gave TF-02 29,389 paise for 29,390 of bills. The second shows the reused key: the map has several entries, and every one reads "TF-03 20", the last bill's outlet and hour, because they are all the same object. The third shows the real report's exact, correctly labelled rows. While building, each fix was undone once. Hours in UTC turned 2 tests red, and a UTC day 4. Ascending order turned 3 red, and a <code>double</code> sum 11 (the paise conversion refuses the drift). Ties going to the later hour turned 1 red, and allowing today's report 1.</p>
</div>
""" + code(read(T + "DoubleMoneyMutableKeyTrapTest.java"), "java") + code(read(T + "OldDailyReport.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "ReportController.java", dwn("Reads an ISO date and returns the report.",
        "Spring turns a missing or malformed date into a 400 on its own.",
        "Accepting a date as a string and parsing it by hand.")),
    (J + "DailySalesReport.java", dwn("Finds the day's bills and groups, totals, sorts and converts them.",
        "Three <code>groupingBy</code> calls into an immutable <code>Totals</code> record; the composite key is a record; paise once, at the end.",
        "<code>double</code> totals, and a key object reused while grouping.",
        "<ul><li><code>reducing(identity, mapper, op)</code> turns each bill into <code>Totals</code> and adds them.</li><li>Sorting entries: <code>comparingByValue(...).reversed().thenComparing(comparingByKey())</code>.</li><li><code>longValueExact()</code> throws rather than rounding a fraction of a paisa.</li></ul>")),
    (J + "Sale.java", "<p>One bill, with the amount as the till printed it.</p>"),
    (J + "SalesFeed.java", "<p>Where bills come from: every bill in a time range.</p>"),
    (J + "DemoSalesFeed.java", "<p>Seven days of seeded demo bills for 40 outlets, menu price plus 5% GST.</p>"),
    (J + "Outlets.java", "<p>The 40 outlets' ids and names.</p>"),
    (J + "ReportsApplication.java", "<p>Entry point, and the <code>Clock</code> bean tests replace.</p>"),
]
tree = """stations/034-restaurant-chain-daily-sales-report/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tiffino/reports/
│   ├── ReportController.java   ├── DailySalesReport.java
│   ├── Sale.java   ├── SalesFeed.java   ├── DemoSalesFeed.java
│   ├── Outlets.java   └── ReportsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/tiffino/reports/   (see Tests)
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
<p>Ask for yesterday (India's date). On macOS use <code>date -v-1d +%F</code> instead of <code>date -d yesterday +%F</code>.</p>
""" + code("""curl "http://localhost:8080/reports/daily-sales?date=$(TZ=Asia/Kolkata date -d yesterday +%F)\"""", "bash") + """
<p>Then open <code>jshell</code> and type <code>(188.95 + 104.95) * 100</code>.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>ArithmeticException: Rounding necessary</code>", "An amount with more than two decimals reached <code>longValueExact</code>.", "Find the bill: tills print paise; a third decimal is a data problem to fix at the source."],
    ["Yesterday's report is <code>404</code>", "The demo data covers the 7 days before the app started, in India's calendar.", "Use India's date: <code>TZ=Asia/Kolkata date -d yesterday +%F</code>."],
    ["A <code>groupingBy</code> map in a different order each run", "<code>HashMap</code> has no order.", "Sort the entries, or collect into a <code>TreeMap</code> as the hours do."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>DailySalesContractTest</code> ({cnt('DailySalesContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>DoubleMoneyMutableKeyTrapTest</code> ({cnt('DoubleMoneyMutableKeyTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Day edges, order, ties, bad amounts", f"<code>DailySalesReportTest</code> ({cnt('DailySalesReportTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Streams and a loop agree on 7 days of bills", f"<code>StreamsAndLoopAgreeTest</code> ({cnt('StreamsAndLoopAgreeTest')} runs)", '<span class="pill ok">pass</span>']]) + """
<h2>Streams or a loop?</h2>
""" + table(["", "Streams (the report)", "Loop (the test's check)"], [
    ["Reads as", "What is computed: group, total, sort", "How: walk, look up, add"],
    ["Good for", "Several groupings of the same data, sorting, chaining", "One simple total; early exit; complex state"],
    ["Here", "Three groupings and a sort", "An independent second way to the same totals"]]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "Fixture.java", "<p>A day small enough to check by hand, with a bill just outside each end.</p>"),
    (T + "DoubleMoneyMutableKeyTrapTest.java", "<p>Written first: the double paisa, the mislabelled rows, and the exact report.</p>"),
    (T + "DailySalesReportTest.java", "<p>The report without Spring: India's day, names, ties, a fraction of a paisa.</p>"),
    (T + "StreamsAndLoopAgreeTest.java", "<p>A loop over whole paise checks the streams on 7 demo days.</p>"),
    (T + "DailySalesContractTest.java", "<p>The full response compared strictly, and every refusal.</p>"),
    (T + "OldDailyReport.java", "<p>The old code, kept only in tests.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tiffino/reports/</code>.</li>
<li>Run it: <code>./mvnw test -Dtest=WeeklyTotalsChallengeTest</code>. It does not compile until the new method exists; add an empty one and watch the test fail.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "A week at a glance", "Beginner-friendly", 25,
    "Add <code>weekTotals(lastDay)</code>: each outlet's total in paise for the 7 India days ending on <code>lastDay</code>, highest first. It must agree with the seven daily reports, and a week that includes today is refused.",
    "both tests in <code>WeeklyTotalsChallengeTest</code> pass.",
    ["The same grouping as the daily report, over a longer time range.",
     "A <code>LinkedHashMap</code> keeps the order you put entries in."],
    "challenge/WeeklyTotalsChallengeTest.java", ["challenge/solution/DailySalesReport.java"]) + challenge(2, "The busiest hour in each city", "Go deeper", 30,
    "TF-01 to TF-20 are in Bengaluru, TF-21 to TF-40 in Pune. Add <code>Outlets.city</code> and <code>busiestHourByCity(day)</code>: each city's hour with the highest sales across its outlets, the earlier hour on a tie.",
    "both tests in <code>CityPeakHourChallengeTest</code> pass.",
    ["<code>groupingBy</code> can take another <code>groupingBy</code> as its downstream collector: city, then hour.",
     "For each city's inner map, the entry with the highest amount, with the hour as a tie-break."],
    "challenge/CityPeakHourChallengeTest.java", ["challenge/solution/Outlets.java", "challenge/solution/DailySalesReport.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Compute on request, or once a night?</h2>
<p>With 400 outlets and a year of history, owners want any day, week or month in under a second. Compare computing from bills on each request with storing one row per outlet per day after midnight. What happens when a late bill or a refund arrives for a day already totalled?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test on a day small enough to add up by hand.</li>
<li>Fix the day's edges in India's time zone.</li>
<li>Group into an immutable totals record; use a record for the composite key.</li>
<li>Sort entries, convert to paise once, and check the streams against a plain loop.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["<code>BigDecimal</code> from the till's text, paise in the API", "Exact; slower than <code>long</code> (irrelevant at this size).", '<span class="pill ok">Chosen</span>'],
    ["Parse straight to <code>long</code> paise", "Exact and fast; needs a careful parser for \"261.4\" and \"261\".", '<span class="pill ok">Also fine</span>'],
    ["<code>double</code> rupees", "Off by a paisa after a few additions.", '<span class="pill bad">The trap</span>'],
    ["A reused mutable key", "Every row labelled with the last bill.", '<span class="pill bad">The trap</span>'],
    ["SQL <code>GROUP BY</code> in the database", "The usual choice once bills are in a table.", '<span class="pill warn">With a database</span>']]) + """
<h2>Database design</h2>
<p>None in this station. With a table, <code>bill(outlet_id, billed_at timestamptz, amount_paise bigint check (amount_paise &gt; 0))</code>, and the report is one <code>GROUP BY outlet_id, extract(hour from billed_at at time zone 'Asia/Kolkata')</code> over the day's range.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Late data</dt><dd>Tills go offline and send bills hours later. A report for yesterday can change; say when it was computed, or close the day only after every outlet has synced.</dd>
<dt>Time zones</dt><dd>Store instants; convert to India's time only to decide the day and the hour.</dd>
<dt>Size</dt><dd>1,400 bills a day fit in memory easily. At millions, group in the database or keep daily totals.</dd>
<dt>Money</dt><dd>Use <code>BigDecimal</code> or integer paise everywhere money flows; one <code>double</code> in the middle undoes it.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why not use double for money?", "double is binary floating point; most decimal amounts like 0.1 or 188.95 cannot be stored exactly, and the errors show up after additions or when converting to paise. Use BigDecimal or integer minor units."),
    ("What happens if you mutate an object used as a HashMap key?", "Its hashCode changes, so the map looks in the wrong bucket: lookups fail and entries can be duplicated. Keys must be immutable; records with final fields are ideal."),
    ("How do you sum BigDecimal in a stream?", "map to the amount, then reduce(BigDecimal.ZERO, BigDecimal::add). Inside groupingBy, use reducing(BigDecimal.ZERO, mapper, BigDecimal::add)."),
    ("How do you sort a map by value?", "Stream its entrySet and sort with Map.Entry.comparingByValue(), reversed for highest first, thenComparing(comparingByKey()) to make ties stable."),
    ("Streams or loops?", "Whichever reads more clearly. Streams suit grouping, mapping and sorting pipelines; loops suit early exit and complex state. Performance is rarely the deciding factor at this size."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You found a double sum that loses a paisa yourself."],
    ["Streams", "groupingBy with a downstream collector.", "Nested grouping and sorted entries."],
    ["Money", "BigDecimal or paise, never double.", "You know where the conversion to paise belongs."],
    ["Time", "The day in India's time zone.", "Late bills and when a day is final."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any report:</p>
<ul class="rules">
<li>Does a <code>double</code> or <code>float</code> touch money anywhere?</li>
<li>Can any map key change after it is stored?</li>
<li>Whose midnight does "a day" use?</li>
<li>Is the order of rows defined, including ties?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
