"""Station 021 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 21,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · java.time formatters · checked exceptions · MockMvc",
    "simulation": "The statement is parsed and the result returned; nothing is stored and no bank is contacted. Sample files are made up.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tijori/statementimport/"
T = "src/test/java/com/tijori/statementimport/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("CSV", "Text where each line is a row and commas separate the fields.", "A bank statement exported for a spreadsheet.", "<code>text/csv</code> request body"),
    ("Quoted field", "A field in double quotes, so it can contain commas; <code>\"\"</code> inside it is one quote.", "<code>\"UPI/GROCER, BLR\"</code>", "<code>CsvLine</code>"),
    ("Date format", "The pattern a date is written in.", "31/03/2026 (dd/MM/yyyy) or 2026-03-31.", "<code>DATE_FORMATS</code>"),
    ("Strict parsing", "Refuse impossible dates instead of adjusting them.", "31 February is an error, not 28 February.", "<code>ResolverStyle.STRICT</code>"),
    ("Checked exception", "An exception the compiler makes the caller handle or declare.", "A form that cannot be filed until every box is answered.", "<code>LineException</code>"),
    ("Per-line error", "A problem reported with the line, field and value it came from.", "\"Line 4,812: date 31.03.2026 is not a real date\".", "<code>errors</code>"),
]
STORY = [
    ("Meera uploads a year of transactions", "5,000 lines from her bank's export. One line, 4,812, has a date written 31.03.2026."),
    ("The app says \"Something went wrong\"", "The parser stopped at that line and threw an exception nobody caught. Nothing was imported, and nothing says which line to fix."),
    ("The fix", "Read every line. Keep the good ones, and list each bad one with its line number, the field and what was wrong, so Meera fixes one line, once."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">An error the customer can act on names the line, the field and the value.</p>

<h2>What are we building?</h2>
<p><code>POST /statements/parse</code> takes a statement CSV and returns the transactions it could read, plus a list of every line it could not read and why.</p>

<h2>An everyday analogy</h2>
<p>A teacher marking 50 answer sheets does not stop at the first mistake and hand everything back with "wrong". She marks every sheet and writes the question number next to each mistake.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Check the header</strong>: the first line must name the five columns.</li>
<li><strong>Read each line</strong>: split the fields, parse the date strictly, turn amounts into paise.</li>
<li><strong>Catch per line</strong>: a bad line becomes an error with its line number; the loop carries on.</li>
<li><strong>Report</strong>: COMPLETE, PARTIAL or REJECTED, with the transactions and the errors.</li>
</ol>

<details class="qa check"><summary>Check yourself: why is quietly reading 31/02/2026 as 28/02/2026 worse than an error?</summary><p>The statement now contains a transaction on a day it did not happen, and nobody knows. An error is annoying once; a silent change is wrong forever.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No storage.</strong> The result is returned, not saved.</li>
<li><strong>Not a full CSV library.</strong> Line breaks inside quoted fields are not supported (a demo rule).</li>
<li><strong>One bank format.</strong> Challenge 2 accepts other banks' column names.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tijori</strong> (a fictional fintech app) imports bank statements for budgeting. Its parser stops at the first bad line and the error reaches the customer as "Something went wrong". Support cannot tell which line was wrong either, so customers retry the same file, again and again.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> 5,000 lines with a bad date on line 4,812, <b>then</b> 4,999 transactions, status PARTIAL, and one error naming line 4,812, the field <code>date</code> and the value.</li>
<li><b>Given</b> 31/02/2026, 29/02/2025 or 01/13/2026, <b>then</b> an error, never an adjusted date.</li>
<li><b>Given</b> "1,23,456.50", <b>then</b> 12,345,650 paise; "12.345", "-5" or "ten" is an error.</li>
<li><b>Given</b> quoted fields with commas or <code>""</code>, <b>then</b> they are read whole.</li>
<li><b>Given</b> no header, or more than 10,000 lines, <b>then</b> <code>422</code>; an empty body <code>400</code>; JSON <code>415</code>.</li>
<li><b>Given</b> 150 bad lines, <b>then</b> errorCount 150 and the first 100 listed.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Line numbers are as a spreadsheet shows them: the header is line 1.</li>
<li>Dates: dd/MM/yyyy, dd-MM-yyyy or yyyy-MM-dd, strictly.</li>
<li>Exactly one of debit and credit has an amount. Amounts are whole paise.</li>
<li>Error values are cut to 40 characters; at most 100 errors are listed (demo rules).</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Parse and trim text fields, including quoted CSV fields.</li>
<li>Parse dates with several formats, strictly, and know why STRICT needs <code>uuuu</code>.</li>
<li>Explain checked versus unchecked exceptions, and use a checked one on purpose.</li>
<li>Collect per-line errors instead of failing on the first.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/statements/parse</code>", "Parse a <code>text/csv</code> statement. <code>200</code> with what was read and every bad line."]]) + """
<h2>Request body</h2>
<p>A CSV file whose first line is <code>date,description,debit,credit,balance</code>, at most 10,000 more lines.</p>
<h2>Response</h2>
""" + table(["Field", "Meaning"], [
    ["<code>status</code>", "<code>COMPLETE</code> (no errors), <code>PARTIAL</code> (some lines read), <code>REJECTED</code> (none read)."],
    ["<code>linesRead</code>", "Lines after the header."],
    ["<code>transactions</code>", "Each with its file <code>line</code>, ISO <code>date</code>, description and amounts in paise."],
    ["<code>errorCount</code>, <code>errors</code>", "How many lines failed; the first 100, each with <code>line</code>, <code>field</code>, <code>value</code> and <code>message</code>."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "The file was read; the body says how much of it"],
    ['<span class="pill warn">400</span>', "Empty body"],
    ['<span class="pill warn">415</span>', "Not <code>text/csv</code>"],
    ['<span class="pill warn">422</span>', "No valid header, or more than 10,000 lines"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. The request bodies are the files in <code>docs/samples/</code>; JSON responses are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-clean", "Case 1: a clean statement", "<b>Why:</b> three date formats, a quoted description with a comma, Indian grouping in amounts: all read. COMPLETE."),
    ("02-three-bad-lines", "Case 2: three bad lines among five", "<b>Why:</b> an impossible date, an amount with three decimals, and a line with both debit and credit. Each is listed with its line number; the two good lines are kept. PARTIAL."),
    ("03-no-header", "Case 3: no header", "<b>Why:</b> without the header the columns cannot be trusted: <code>422</code> for the whole file."),
    ("04-json-instead-of-csv", "Case 4: JSON instead of CSV", "<b>Why:</b> the endpoint only consumes <code>text/csv</code>: <code>415</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["5,000 lines, bad date on 4,812", "4,999 read; error on line 4,812", "<code>theFixedParserReadsEveryOtherLineAndNamesTheBadOne</code>"],
    ["Quotes, <code>\"\"</code>, three date formats, grouping", "All read", "<code>aCleanStatementIsComplete</code>"],
    ["Impossible date, both amounts, 3 decimals, unclosed quote, 3 fields, empty description", "Six errors, each with its line", "<code>everyBadLineIsListedWithItsLineNumber</code>"],
    ["150 bad lines", "REJECTED; 150 counted, 100 listed", "<code>aFileWithNoGoodLinesIsRejectedAndOnlyTheFirstHundredErrorsAreShown</code>"],
    ["No header; 10,001 lines; 10,000 lines", "<code>422</code>; <code>422</code>; read", "<code>aMissingHeaderOrATooLongFileIs422</code>"],
    ["Empty body; JSON", "<code>400</code>; <code>415</code>", "<code>anEmptyBodyIs400AndAnotherContentTypeIs415</code>"],
    ["29/02 in 2024 and 2025; 31/04; 1/4/2026; 04/01/26", "Leap day read; the rest refused", "<code>datesAreStrictInEveryFormat</code>"],
    ["1,23,456.50; 12.345; -5; 1e3; ₹10", "12,345,650 paise; the rest refused", "<code>amountsAreWholePaiseWithIndianGrouping</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Failing the whole file on one bad line, with no line number in the error.</p>
<p>The first test shows the old loop throwing at line 4,812 with a message that does not mention the line. It is an unchecked exception, so nothing forced anyone to handle it. The second shows the default date formatter quietly turning 31 February into 28 February. The third shows the fixed parser reading 4,999 lines and naming line 4,812. While building, stopping at the first error turned 3 tests red, dropping STRICT turned 2 red, and counting lines from 1 instead of 2 turned 3 red.</p>
</div>
""" + code(read(T + "OneBadLineTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "StatementController.java", dwn("Accepts <code>text/csv</code>, parses it, and turns a file-level problem into a <code>422</code>.",
        "The controller has no parsing logic: the parser is plain Java, testable without Spring.",
        "A generic 500 \"Something went wrong\".")),
    (J + "StatementParser.java", dwn("The header check, the per-line loop, strict dates and amounts.",
        "A checked <code>LineException</code> per line: the loop must catch it, so one bad line can never end the file.",
        "The trap: the first exception ends everything.",
        "<ul><li><code>DATE_FORMATS</code> are tried in order; each is STRICT (ISO_LOCAL_DATE is strict already).</li><li>File-level problems are an unchecked <code>FileProblem</code>: there is nothing to continue with.</li><li><code>lines()</code>, not <code>strip()</code>: a leading blank line must not shift line numbers.</li></ul>")),
    (J + "CsvLine.java", dwn("Splits one line into fields, honouring quotes.",
        "Twenty lines of plain Java instead of a dependency, for one simple format.",
        "<code>line.split(\",\")</code>, which breaks on <code>\"UPI/GROCER, BLR\"</code>.")),
    (J + "LineException.java", "<p>The checked exception: field, value and message for one line.</p>"),
    ("src/main/resources/application.yaml", "<p>Problem bodies for every error.</p>"),
    (J + "StatementImportApplication.java", "<p>Standard Spring Boot entry point.</p>"),
]
tree = """stations/021-parsing-a-bank-statement-csv/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tijori/statementimport/
│   ├── StatementController.java   ├── StatementParser.java
│   ├── CsvLine.java               ├── LineException.java   └── StatementImportApplication.java
├── src/test/java/com/tijori/statementimport/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     samples/, capture script, captures, saved runs"""
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
<p>Use <code>--data-binary</code>, not <code>-d</code>: <code>-d @file</code> removes the line breaks, and the whole file becomes one line.</p>
""" + code("""curl -X POST http://localhost:8080/statements/parse -H "Content-Type: text/csv" --data-binary @docs/samples/three-bad-lines.csv""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Every line is one error, \"has 21 fields\"", "<code>curl -d @file</code> joined all lines.", "Use <code>--data-binary @file</code>."],
    ["<code>422</code> about the header", "The first line is not exactly the five column names.", "Export with headers, or add the line."],
    ["Every date fails after you change a pattern", "STRICT with <code>yyyy</code> (year of era) needs an era.", "Use <code>uuuu</code>."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found (a missing header)", f"<code>StatementContractTest</code> ({cnt('StatementContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>OneBadLineTrapTest</code> ({cnt('OneBadLineTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "CSV splitting, strict dates, amounts", f"<code>StatementParserTest</code> ({cnt('StatementParserTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "OneBadLineTrapTest.java", "<p>Written first: the old loop's nameless exception, the silent 28 February, and the fixed parser on 5,000 lines.</p>"),
    (T + "StatementContractTest.java", "<p>A clean file, a file with six kinds of bad line, a rejected file, and files that cannot be read.</p>"),
    (T + "StatementParserTest.java", "<p>The parsing pieces with no Spring at all.</p>"),
    (T + "ApiTest.java", "<p>Shared setup and a generator for long statements with one bad line.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tijori/statementimport/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=RunningBalanceChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solution copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Check the running balance", "Go deeper", 30,
    "Each line's balance must equal the line before's balance, minus its debit, plus its credit. A mismatch is an error on that line saying what it should be. After an unreadable line, skip the check for the next one.",
    "both tests in <code>RunningBalanceChallengeTest</code> pass, and the station's tests still pass.",
    ["Keep the previous line's stated balance in a <code>Long</code>; set it to <code>null</code> after an error.",
     "Compare with the stated balance, not your own running total, so one wrong line is one error, not a cascade."],
    "challenge/RunningBalanceChallengeTest.java", ["challenge/solution/StatementParser.java"]) + challenge(2, "Columns by name", "Beginner-friendly", 25,
    "Find the five columns by name in any order, accepting other banks' names: Txn Date, Narration, Withdrawal Amt, Deposit Amt, Closing Balance. Extra columns are ignored; a missing one is <code>422</code> naming it.",
    "both tests in <code>ColumnsByNameChallengeTest</code> pass.",
    ["Turn the header into a list of lower-case names and look up each column's index.",
     "Pass the indexes into <code>parseLine</code> instead of the fixed 0 to 4."],
    "challenge/ColumnsByNameChallengeTest.java", ["challenge/solution/StatementParser.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Import the good lines, or nothing?</h2>
<p>This station reports PARTIAL and lets the app decide. For a budgeting app, importing 4,999 of 5,000 lines may be fine; for a loan application that checks income, a missing salary line changes the answer. Who should decide, and how would the API let them: a flag, two endpoints, or a confirm step?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the nameless exception at line 4,812, and the silent 28 February.</li>
<li>Write the line splitter and strict date and amount parsers; test them without Spring.</li>
<li>Make a bad line a checked exception, caught in the loop with the line number.</li>
<li>Report status, transactions and errors; refuse files without a header or that are too long.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Read every line, report each error", "A result with two lists instead of one.", '<span class="pill ok">Chosen</span>'],
    ["Fail on the first error", "One fix per upload; no line number unless you add it.", '<span class="pill bad">The trap</span>'],
    ["<code>line.split(\",\")</code>", "Breaks on quoted commas.", '<span class="pill bad">Wrong</span>'],
    ["A CSV library (for example Apache Commons CSV)", "A dependency; handles line breaks in quotes and more.", '<span class="pill warn">For messier files</span>'],
    ["Default (SMART) date parsing", "Impossible dates are adjusted silently.", '<span class="pill bad">Wrong for money</span>']]) + """
<h2>Database design</h2>
<p>None in this station. When imports are stored: an <code>imports</code> row per upload (status, counts) and its <code>import_errors</code> (line, field, value, message), so support can see exactly what a customer saw.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Size</dt><dd>The whole body is read before the line limit applies. Cap the upload size at the proxy or server, or read the stream line by line, before accepting large files.</dd>
<dt>Privacy</dt><dd>Statements are personal financial data. Do not log the body; error values are cut to 40 characters and show only the field that failed.</dd>
<dt>Encoding</dt><dd>Exports may start with a byte-order mark; the header check removes it. Files that are not UTF-8 need an explicit charset.</dd>
<dt>Support</dt><dd>Line numbers match what a spreadsheet shows, so support and customers point at the same row.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Checked or unchecked: what is the difference?", "A checked exception must be caught or declared, so the compiler makes callers think about it. An unchecked one (RuntimeException) can travel up unnoticed. Use checked for failures the caller is expected to handle, like a bad line."),
    ("Why is 31/02/2026 parsed as 28 February by default?", "DateTimeFormatter.ofPattern uses ResolverStyle.SMART, which clamps an invalid day to the last day of the month. STRICT refuses it."),
    ("Why uuuu instead of yyyy with STRICT?", "yyyy is year of era and needs an era field to resolve strictly; without one every date fails. uuuu is the proleptic year and needs nothing else."),
    ("How should a parser report errors?", "With the line number, the field, the value and what was expected, for every bad line, so the user can fix them all in one go."),
    ("Why not split CSV on commas?", "Fields may be quoted because they contain commas. A small state machine that tracks whether you are inside quotes handles it."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can predict the errors for case 2 before running it."],
    ["Dates", "Strict parsing in several formats.", "You can explain SMART, STRICT and uuuu."],
    ["Exceptions", "Per-line errors with line numbers.", "When a checked exception is the right tool, and when not."],
    ["Explanation", "Why one bad line must not end the file.", "Partial import: who decides, and how."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any file import:</p>
<ul class="rules">
<li>Does one bad line end the whole import?</li>
<li>Does every error name the line, the field and the value?</li>
<li>Are dates parsed strictly, and are amounts kept exact?</li>
<li>Is there a limit on size, and is the file kept out of the logs?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
