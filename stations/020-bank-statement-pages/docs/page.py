"""Station 020 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 20,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · generics · Comparator chains · method validation · MockMvc",
    "simulation": "The transactions are generated in memory from a fixed seed: no bank, no real account. The same 4,000 rows appear on every run.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tijori/statements/"
T = "src/test/java/com/tijori/statements/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Page", "One slice of a long list, with enough information to ask for the next one.", "Page 3 of a printed passbook.", "<code>Page&lt;T&gt;</code>"),
    ("Offset paging", "\"Skip page × size rows, return size rows.\"", "Turning to page 40 by counting 39 pages first.", "<code>?page=1&amp;size=20</code>"),
    ("Generic class", "A class written once for any element type.", "One envelope design for letters, bills or photos.", "<code>Page&lt;Transaction&gt;</code>"),
    ("Bounded type parameter", "A generic type that must have some ability.", "\"Any envelope, as long as it has a tracking number.\"", "<code>T extends Identified</code>"),
    ("Comparator chain", "Sort by one thing, then by another to break ties.", "Sort a class by marks, then by roll number.", "<code>STATEMENT_ORDER</code>"),
    ("Integer overflow", "A number too big for its type wraps around to a negative one.", "An odometer rolling past 99999 back to 00000.", "<code>(long) page * size</code>"),
]
STORY = [
    ("Asha opens a year of statements on her phone", "The app asks for all 4,000 transactions at once. The response takes so long on mobile data that the request times out."),
    ("A script asks for size=1000000", "The server tries to load and serialise everything it has. On a real table, that is millions of rows, and the server runs out of memory."),
    ("The fix", "Pages of at most 100, newest first in a fixed order, with a limit on how deep offset paging may go."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Every list endpoint needs a maximum page size. The client may ask; the server decides.</p>

<h2>What are we building?</h2>
<p><code>GET /accounts/{id}/transactions?page=0&amp;size=20</code> returns one page of a statement, newest first, with the total count and whether there is a next page.</p>

<h2>An everyday analogy</h2>
<p>A bank passbook printer prints a few pages at a time, not the whole year in one go. It always prints in the same order, so page 2 continues exactly where page 1 stopped.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Check the request</strong>: page from 0, size from 1 to 100, and not too deep.</li>
<li><strong>Order the statement</strong>: newest first; for the same minute, the higher id first.</li>
<li><strong>Slice</strong> page × size to page × size + size, computed as a <code>long</code>.</li>
<li><strong>Answer</strong> with the items, the totals and whether there is more.</li>
</ol>

<details class="qa check"><summary>Check yourself: 19 transactions were posted at 13:15 on one day. Sorting by time alone, which comes first?</summary><p>Nothing in the time decides. In memory, Java's sort keeps them in whatever order they arrived; in a database, the order can change between two queries, so a row can appear on two pages or none. A tie-breaker (the id) makes the order total.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>Not cursor paging.</strong> Offsets drift when new transactions arrive; station 66 (keyset pagination) fixes that.</li>
<li><strong>No database.</strong> The rows are generated in memory.</li>
<li><strong>No filters or other sorts.</strong> The challenges add them.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tijori</strong> (a fictional fintech app) serves statements with whatever page size the client sends. Phones asking for a year of transactions time out; one request for a million rows took the server down. A very large page number made the offset overflow and return a 500.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> no parameters, <b>then</b> the newest 20 transactions, 4,000 in total over 200 pages, with <code>hasNext</code> true.</li>
<li><b>Given</b> page 39 of size 100, <b>then</b> the last 100 and <code>hasNext</code> false; page 40 is empty, not an error.</li>
<li><b>Given</b> size 101, size 0, page −1 or page "abc", <b>then</b> <code>400</code>.</li>
<li><b>Given</b> page × size of 10,000 or more, <b>then</b> <code>400</code> "Page too deep".</li>
<li><b>Given</b> an unknown account, <b>then</b> <code>404</code>; an account with no transactions has 0 pages.</li>
<li><b>Given</b> any page size, <b>then</b> walking every page sees each transaction exactly once, in statement order.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Pages start at 0; size defaults to 20, at most 100.</li>
<li>Statement order: newest <code>postedAt</code> first, then the higher id first.</li>
<li>Offsets are computed in <code>long</code>; page × size must be under 10,000 (a demo rule).</li>
<li>Account ids are normalised with <code>Locale.ROOT</code>.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Write a generic class, and use a bounded type parameter when the class needs something from its elements.</li>
<li>Build a total order with a <code>Comparator</code> chain.</li>
<li>Bound every list endpoint, and say why deep offsets are expensive.</li>
<li>Spot an integer overflow before it becomes a 500.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/accounts/{id}/transactions?page&amp;size</code>", "One page of the statement, newest first."]]) + """
<h2>Parameters</h2>
""" + table(["Parameter", "Rule"], [
    ["<code>page</code>", "0 or more; default 0."],
    ["<code>size</code>", "1 to 100; default 20."],
    ["<code>page × size</code>", "Under 10,000 (a demo rule)."]]) + """
<h2>Response</h2>
""" + table(["Field", "Meaning"], [
    ["<code>items</code>", "The transactions on this page. Negative amounts are debits."],
    ["<code>page</code>, <code>size</code>", "What was asked for."],
    ["<code>totalItems</code>, <code>totalPages</code>", "For the whole statement."],
    ["<code>hasNext</code>", "Whether another page has items."],
    ["<code>lastId</code>", "The id of the last item: where a cursor would continue (station 66). <code>null</code> on an empty page."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "A page, possibly empty"],
    ['<span class="pill warn">400</span>', "A parameter out of range or not a number, or a page too deep"],
    ['<span class="pill warn">404</span>', "No such account"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-first-page", "Case 1: the first page, size 3", "<b>Why:</b> the newest three. <code>lastId</code> is the third item's id."),
    ("02-next-page", "Case 2: the next page", "<b>Why:</b> continues exactly after case 1's last item, because the order has a tie-breaker."),
    ("03-past-the-end", "Case 3: page 40 of size 100", "<b>Why:</b> 4,000 rows end at page 39. Past the end is an empty page, not an error."),
    ("04-size-too-large", "Case 4: size 1,000,000", "<b>Why:</b> the request that took the old server down: <code>400</code>. Spring's default detail says only “Validation failure”; the limit of 100 is in the API contract above."),
    ("05-page-too-deep", "Case 5: page 200,000,000", "<b>Why:</b> page × size is 4,000,000,000: too deep, and too big for an <code>int</code>. <code>400</code>, not a 500."),
    ("06-empty-account", "Case 6: an account with no transactions", "<b>Why:</b> zero items and zero pages."),
    ("07-unknown-account", "Case 7: an unknown account", "<b>Why:</b> <code>404</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["No parameters, account id in capitals", "Newest 20 of 4,000; 200 pages", "<code>theFirstPageIsTheNewestTwenty</code>"],
    ["Page 39 and 40 of size 100", "Last 100 then empty; <code>hasNext</code> false", "<code>theLastPageHasNoNextAndPastTheEndIsEmpty</code>"],
    ["No transactions", "0 items, 0 pages", "<code>anAccountWithNoTransactionsHasNoPages</code>"],
    ["size 100 / 101 / 0; page −1, abc; offset 9,900 / 10,000", "OK / <code>400</code>", "<code>outOfRangeParametersAre400</code>"],
    ["Unknown account", "<code>404</code>", "<code>anUnknownAccountIs404</code>"],
    ["Every page at sizes 1, 7, 37, 100", "Each transaction once, in order", "<code>walkingEveryPageSeesEachTransactionOnceInOrder</code>"],
    ["Up to 19 rows in one minute", "Ordered by id, newest first", "<code>transactionsInTheSameMinuteAreOrderedByIdNewestFirst</code>"],
    ["Empty list; a different element type", "One empty page; <code>Page&lt;Note&gt;</code> works", "<code>PageTest</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Unbounded page size, so one request loads millions of rows.</p>
<p>"Let the client choose the page size" sounds friendly. The first test shows the old paging handing over all 4,000 rows for <code>size=1000000</code>. The second shows <code>page × size</code> overflowing an <code>int</code> into a negative offset. The third shows the fixed endpoint answering both with a <code>400</code>. Removing the size limit turned 2 tests red; dropping the tie-breaker turned 2 red. Computing the offset as an <code>int</code> again gave this, from a real run:</p>
</div>
<pre class="console">""" + e(read("docs/int-offset-run.txt")) + """</pre>
""" + code(read(T + "BottomlessPageTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "StatementController.java", dwn("Validates page and size, finds the account, refuses deep pages, and returns one page.",
        "Limits are declared on the parameters (<code>@Min</code>, <code>@Max</code>), so the rule is visible where the request arrives.",
        "Any size, offset in <code>int</code>.")),
    (J + "Page.java", dwn("A generic page for any element type that has an id.",
        "<code>T extends Identified</code> lets the page name its last id; a plain <code>T</code> could not.",
        "A page class per element type.",
        "<ul><li>The offset is a <code>long</code>, so page × size cannot wrap around.</li><li><code>List.copyOf</code> keeps the page immutable.</li></ul>")),
    (J + "Accounts.java", dwn("The two demo accounts, generated from a fixed seed, kept in statement order.",
        "One <code>Comparator</code> chain defines the order everywhere.",
        "Sorting by time only.")),
    (J + "Transaction.java", "<p>A statement line, as a record that is <code>Page.Identified</code>.</p>"),
    ("src/main/resources/application.yaml", "<p>Problem bodies for every error.</p>"),
    (J + "StatementsApplication.java", "<p>Standard Spring Boot entry point.</p>"),
]
tree = """stations/020-bank-statement-pages/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tijori/statements/
│   ├── StatementController.java   ├── Page.java   ├── Accounts.java
│   ├── Transaction.java           └── StatementsApplication.java
├── src/test/java/com/tijori/statements/   (see Tests)
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
""" + code("""# The newest 5, then the next 5
curl "http://localhost:8080/accounts/acc-1001/transactions?size=5"
curl "http://localhost:8080/accounts/acc-1001/transactions?page=1&size=5"

# The request that used to load everything: now a 400
curl -i "http://localhost:8080/accounts/acc-1001/transactions?size=1000000\"""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>400</code> Page too deep", "page × size is 10,000 or more.", "Use a smaller page number; in a real app, filter by date (challenge 1) or use a cursor."],
    ["<code>400</code> for <code>page=1</code> on PowerShell", "<code>&amp;</code> splits the command.", "Put the URL in double quotes."],
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>StatementContractTest</code> ({cnt('StatementContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>BottomlessPageTrapTest</code> ({cnt('BottomlessPageTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Every page walked at several sizes; tie order; generics", f"<code>PageTest</code> ({cnt('PageTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "BottomlessPageTrapTest.java", "<p>Written first: the old paging's 4,000 rows and its negative offset, and the fixed endpoint's 400s.</p>"),
    (T + "StatementContractTest.java", "<p>First, last and past-the-end pages, the limits, and unknown accounts.</p>"),
    (T + "PageTest.java", "<p>Walks every page at four sizes, checks the tie order, and uses <code>Page</code> with another type.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app through MockMvc and a request helper.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tijori/statements/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=DateRangeChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solution copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "A statement for a date range", "Beginner-friendly", 25,
    "Add optional <code>from</code> and <code>to</code> dates (inclusive). The page and its totals cover only that range; a backwards range is <code>400</code>.",
    "both tests in <code>DateRangeChallengeTest</code> pass: September 2026 is 346 transactions over 4 pages of 100.",
    ["<code>@DateTimeFormat(iso = DateTimeFormat.ISO.DATE)</code> parses <code>2026-09-01</code>; anything else is a <code>400</code> on its own.",
     "Filter first, then page: <code>Page.of</code> does not change."],
    "challenge/DateRangeChallengeTest.java", ["challenge/solution/StatementController.java"]) + challenge(2, "Largest first", "Go deeper", 20,
    "Add <code>sort=largest</code>: by the size of the amount, debit or credit, then the statement order. <code>sort=newest</code> stays the default; anything else is <code>400</code>.",
    "both tests in <code>LargestFirstChallengeTest</code> pass.",
    ["<code>Comparator.comparingLong(t -&gt; Math.abs(t.amountPaise())).reversed()</code>, then <code>.thenComparing(Accounts.STATEMENT_ORDER)</code>.",
     "Without the last step, two equal amounts could swap between pages."],
    "challenge/LargestFirstChallengeTest.java", ["challenge/solution/StatementController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>A new transaction arrives between two pages</h2>
<p>Asha reads page 0 (the newest 20). A new UPI payment is posted. She asks for page 1. Which transaction does she see twice? Draw the two pages. How would "the 20 transactions older than id 3979" (a cursor) avoid it, and what does the cursor need from the order?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old paging's whole-history response and its <code>int</code> overflow.</li>
<li>Write <code>Page&lt;T extends Identified&gt;</code> with a <code>long</code> offset; walk every page in a test.</li>
<li>Define the statement order as one <code>Comparator</code> chain with a unique tie-breaker.</li>
<li>Bound size and depth on the controller, with problem bodies that say the limit.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Offset paging, bounded size and depth", "Deep pages refused; drifts on live data.", '<span class="pill ok">Chosen here</span>'],
    ["Unbounded size", "One request can load everything.", '<span class="pill bad">Wrong</span>'],
    ["Silently clamp size to 100", "No error, but the client gets less than it asked and may not notice.", '<span class="pill warn">Possible; say so in the response</span>'],
    ["Keyset (cursor) paging", "No jump to page 40; stable on live data and fast at any depth.", '<span class="pill ok">Station 66</span>'],
    ["Spring Data <code>Page</code>/<code>Pageable</code>", "Ready-made with a database; this station builds the idea by hand.", '<span class="pill warn">With JPA or JDBC repositories</span>']]) + """
<h2>Database design</h2>
<p>None in this station. With a database: an index on <code>(account_id, posted_at DESC, id DESC)</code> matches the order exactly, so each page is an index range. <code>OFFSET 9900</code> still walks 9,900 index entries, which is why the depth is capped.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Limits</dt><dd>Every list endpoint gets a maximum size, documented and enforced on the server. The client can ask for less, never more.</dd>
<dt>Counting</dt><dd><code>totalItems</code> is cheap here. On a large table, <code>COUNT(*)</code> on every page request costs as much as the page; many APIs drop it or cache it.</dd>
<dt>Live data</dt><dd>New transactions shift every offset by one. Statements for closed periods are stable; the live feed needs a cursor.</dd>
<dt>Mobile</dt><dd>Twenty rows a page keeps responses small on slow networks; the app loads more as the user scrolls.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why must page size be bounded?", "Otherwise one request decides how much memory, database time and bandwidth the server spends. A maximum turns a possible outage into a 400."),
    ("What is wrong with deep offsets?", "The database still reads and discards every skipped row, so page 10,000 is slow; and on live data, inserts shift the rows between requests."),
    ("Why does the order need a tie-breaker?", "Without a unique last key, rows with equal values have no defined order, and the same row can appear on two pages or none."),
    ("What is a bounded type parameter for?", "To use something from the element type inside generic code. Page<T extends Identified> can read item ids; Page<T> could not."),
    ("How can page × size go wrong in Java?", "Two ints multiply as an int. 200,000,000 × 20 wraps to a negative number. Cast one side to long first."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can predict <code>totalPages</code> for any size."],
    ["Limits", "Size and depth are bounded with clear 400s.", "You can explain the cost of OFFSET in a database."],
    ["Generics", "<code>Page&lt;T&gt;</code> works for another type.", "You can say why the bound is there."],
    ["Explanation", "Why the order needs a tie-breaker.", "Offset versus cursor paging on live data."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any list endpoint:</p>
<ul class="rules">
<li>Is there a maximum page size, enforced on the server?</li>
<li>Is the order total, with a unique last key?</li>
<li>Can page × size overflow, or reach a depth the database cannot serve quickly?</li>
<li>What does a client see past the last page?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
