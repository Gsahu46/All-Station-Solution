"""Station 003 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 3,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · TreeMap · MockMvc",
    "simulation": "26 products are a fixed list inside the app; a test adds 2 lakh generated ones to measure the index. Nothing reads a real catalogue.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/kartwala/search/"
T = "src/test/java/com/kartwala/search/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Autocomplete", "Suggestions shown while you are still typing.", "A friend finishing your sentence.", "Typing <code>sam</code> shows Samsung phones."),
    ("Prefix", "The beginning of a word.", "\"Sam\" is the prefix of \"Samsung\".", "The <code>prefix</code> parameter."),
    ("Normalise", "Bring text to one standard form before comparing.", "Writing every name in capitals on a guest list.", "Lower case, trimmed, single spaces."),
    ("TreeMap", "A Java map that keeps its keys sorted.", "A dictionary: words in alphabetical order.", "<code>SuggestionIndex</code>."),
    ("Range lookup", "Reading only the keys between two values in a sorted map.", "Opening a dictionary at \"sam\" and reading until the words stop starting with it.", "<code>subMap(\"sam\", \"sam\\uffff\")</code>."),
    ("Top-N", "The N best items by some score.", "The 5 best-selling books this week.", "The 5 most popular matches."),
    ("Index", "A structure built ahead of time so lookups are fast.", "The index at the back of a book.", "Built once at start-up from the catalogue."),
]
STORY = [
    ("Ravi wants a new phone", "He types <em>sam</em> into Kartwala's search box and waits for suggestions."),
    ("Nothing useful happens", "Suggestions appear only after he types the whole word. When they do, \"Balsamic Vinegar\" sits next to Samsung phones, because the server looks for \"sam\" anywhere in each of 2 lakh names, on every keystroke."),
    ("The fix", "The server keeps product names in sorted order and reads only the ones that start a word with \"sam\", most popular first."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Searching everything for every keystroke is slow and gives odd results. Sorting once, ahead of time, makes each keystroke cheap.</p>

<h2>What are we building?</h2>
<p><code>GET /suggestions?prefix=sam&amp;limit=5</code>: up to 5 products with a word that starts with the typed text, most popular first. Letter case and extra spaces do not matter; a too-short or too-long prefix is refused.</p>

<h2>An everyday analogy</h2>
<p>To find words starting with "sam" in a dictionary, you do not read every page. You open it near "sam", read down until the words stop starting with "sam", and close it. A sorted map lets the program do the same: jump to "sam", read the matching slice, stop.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>At start-up</strong>, every product is stored in a sorted map under each word of its name: "Samsung Galaxy M35" under "samsung…", "galaxy…" and "m35…".</li>
<li><strong>A keystroke arrives</strong>. The prefix is normalised: lower case, trimmed, single spaces. Under 2 or over 40 characters: <code>400</code>.</li>
<li><strong>Range lookup</strong>: read only the keys from "sam" up to the last key that starts with "sam".</li>
<li><strong>Rank</strong> those products by popularity, remove duplicates, keep the top N.</li>
</ol>

<details class="qa check"><summary>Check yourself: why does "vinegar" find "Balsamic Vinegar 500ml", but "amic" finds nothing?</summary><p>The product is stored under each word start: "balsamic…", "vinegar…" and "500ml". "vinegar" is the start of one of those keys. "amic" is in the middle of a word, and no key starts with it.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>Not a real catalogue.</strong> 26 products are fixed in the code. A test builds an index of 2 lakh generated products to show the difference in work.</li>
<li><strong>No spelling correction.</strong> "samsng" finds nothing. Typo tolerance needs a search engine (a later station).</li>
<li><strong>No live updates.</strong> The index is built once at start-up; adding products while running is not covered.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Kartwala</strong> (a fictional e-commerce marketplace) has about 2 lakh products. Its search box suggests nothing useful until a whole word is typed. The suggestion API loops over every product name and calls <code>contains()</code> on each keystroke, so it is slow, and it returns odd matches such as "Balsamic Vinegar" for "sam", in catalogue order rather than by popularity.</p>
<p>Customers who cannot find a product quickly leave. The search team wants suggestions from the second character, in under a few milliseconds, ranked by what people actually buy.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> <code>prefix=sam</code>, <b>then</b> the 5 most popular products with a word starting with "sam" are returned, each with its id and name.</li>
<li><b>Given</b> <code>prefix=galaxy</code>, <b>then</b> products whose second word starts with "galaxy" are found too.</li>
<li><b>Given</b> <code>prefix=msung</code> (inside "Samsung"), <b>then</b> no suggestions.</li>
<li><b>Given</b> <code>  SAMSUNG    galaxy  s</code>, <b>then</b> the same results as <code>samsung galaxy s</code>.</li>
<li><b>Given</b> a prefix under 2 or over 40 characters after trimming, a missing prefix, or a limit outside 1–10, <b>then</b> <code>400</code>.</li>
<li><b>Given</b> 2 lakh products, <b>when</b> searching "sam", <b>then</b> only the matching entries are read, not every name.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Matching is by word start, case-insensitive, with <code>Locale.ROOT</code>.</li>
<li>Results are ordered by popularity (highest first), then by name; each product appears once.</li>
<li>Names are returned in their original spelling (<code>boAt</code>, not <code>boat</code>).</li>
<li><code>prefix</code> is required: 2 to 40 characters after normalising. Raw input over 200 characters is rejected before any work.</li>
<li><code>limit</code>: 1 to 10, default 5. No match is <code>200</code> with an empty list.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Use a <code>TreeMap</code> and <code>subMap</code> for a prefix range lookup.</li>
<li>Normalise text the same way when storing and when searching.</li>
<li>Rank with a <code>Comparator</code> and take the top N.</li>
<li>Explain why input length limits protect the server.</li>
<li>Count the work an algorithm does, instead of guessing.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [["<code>GET</code>", "<code>/suggestions?prefix&amp;limit</code>", "Products whose name has a word starting with the prefix, most popular first."]]) + """
<h2>Parameters</h2>
""" + table(["Parameter", "Type", "Default", "Rule"], [
    ["<code>prefix</code>", "string", "required", "2 to 40 characters after trimming and collapsing spaces; at most 200 characters as sent."],
    ["<code>limit</code>", "integer", "5", "1 to 10."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When", "Body"], [
    ['<span class="pill ok">200</span>', "Any valid prefix, even with no match", "<code>prefix</code> (normalised) and <code>suggestions</code>: <code>productId</code>, <code>name</code>"],
    ['<span class="pill warn">400</span>', "Missing prefix, too short, too long, or limit out of range", "Problem: <em>Invalid prefix</em>, or <code>errors</code> per parameter"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-sam", "Case 1: the customer types \"sam\"", "<b>Why:</b> five products have a word starting with \"sam\"; they come back most popular first. Balsamic Vinegar is not among them: \"sam\" is in the middle of its word."),
    ("02-second-word", "Case 2: a later word, in capitals", "<b>Why:</b> the prefix is normalised to \"galaxy\", and products are stored under every word start, so a second word matches too."),
    ("03-no-match", "Case 3: text inside a word", "<b>Why:</b> \"msung\" starts no word of any product, so the list is empty. <code>200</code>: an empty result is a valid answer."),
    ("04-too-short", "Case 4: one letter", "<b>Why:</b> one letter would match a large share of the catalogue and help nobody, so the server refuses it with <code>400</code>."),
    ("05-bad-limit", "Case 5: limit too high", "<b>Why:</b> a search box shows at most 10; the cap is checked before any work."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What the API does", "Proved by"], [
    ["\"sam\"", "Top 5 word-start matches, by popularity", "<code>theIndexSuggestsOnlyWordStartsMostPopularFirst</code>, <code>prefixReturnsTheMostPopularMatchesWithIds</code>"],
    ["A later word (\"galaxy\")", "Matches", "<code>anyWordOfTheNameCanStartTheMatch</code>"],
    ["Text inside a word (\"msung\")", "No match", "<code>textInTheMiddleOfAWordIsNotAMatch</code>"],
    ["Capitals and extra spaces", "Normalised before matching", "<code>letterCaseAndExtraSpacesDoNotMatter</code>"],
    ["Mixed-case brand names", "Returned as spelled", "<code>theNameKeepsItsOriginalSpelling</code>"],
    ["Two words of one product match", "Suggested once", "<code>aProductMatchingTwoWordsIsSuggestedOnce</code>"],
    ["Equal popularity", "Ordered by name", "<code>equalPopularityIsOrderedByName</code>"],
    ["\"Samz\" against \"San\"", "The range stops exactly where the prefix stops matching", "<code>theRangeEndsWhereThePrefixStopsMatching</code>"],
    ["Turkish server locale", "\"IPHONE\" still finds iPhone", "<code>aTurkishServerLocaleDoesNotChangeMatching</code>"],
    ["No match", "<code>200</code>, empty list", "<code>noMatchIsAnEmptyListNotAnError</code>"],
    ["Missing, 1-letter, 41-letter or 5000-letter prefix", "<code>400</code>", "<code>missingPrefixIs400</code>, <code>oneLetterAfterTrimmingIs400</code>, <code>aPrefixLongerThan40CharactersIs400</code>, <code>aHugePrefixIsRejectedBeforeAnyWork</code>"],
    ["Limit 0 or 11", "<code>400</code>", "<code>limitOutsideOneToTenIs400</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Scanning every product name with <code>contains()</code> on each keystroke.</p>
<p>It is the first idea most people have, and it works on a list of 20. It has two problems. It matches text anywhere, so "sam" suggests Balsamic Vinegar. And it reads every name on every keystroke: with 2 lakh products, typing "samsung" means 7 full scans. The first test shows the odd match through a "before" controller. The last one counts the work on 2 lakh generated products: the scan reads every name, the index reads 5 entries. Indexing every character position instead of word starts was tried while building: 2 tests went red.</p>
</div>
""" + code(read(T + "ContainsScanTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SuggestionController.java", dwn("Reads <code>prefix</code> and <code>limit</code>, normalises the prefix, checks its length, and returns the suggestions.",
        "Length limits sit at the door, so a 5000-character prefix never reaches the index.",
        "No endpoint; and without the limits, one bad request could make the server do far too much work.",
        "<ul><li>Two checks on the prefix: <code>@Size(max = 200)</code> on the raw text, then 2–40 after normalising, because <code>\"  s  \"</code> is one letter.</li></ul>")),
    (J + "SuggestionIndex.java", dwn("Builds a sorted map from each word start to its product, and answers a prefix with a range lookup and a top-N.",
        "Sorted keys put every match for a prefix side by side, so a lookup reads only that slice.",
        "Back to scanning every name on every keystroke.",
        "<ul><li><code>normalise</code> is used for names and prefixes alike: if they were normalised differently, nothing would match.</li><li>The <code>\\u0000</code> and id at the end of each key keep keys unique when products share a word.</li><li><code>prefix + Character.MAX_VALUE</code> is the end of the range: just past every key that starts with the prefix.</li></ul>")),
    (J + "ProductCatalog.java", "<p>The 26 products, with popularity (orders in the last 30 days).</p>"),
    (J + "Product.java", "<p>A product: id, name, popularity.</p>"),
    (J + "Suggestion.java", "<p>The response: the normalised prefix and the suggested items.</p>"),
    (J + "ApiErrors.java", dwn("Adds an <code>errors</code> map (parameter → message) to validation failures.", "The app learns which parameter was wrong.", "A bare \"Bad Request\".")),
    (J + "SearchApplication.java", "<p>Standard Spring Boot entry point.</p>"),
    ("pom.xml", "<p>Web MVC and validation; test starters for JUnit and MockMvc.</p>"),
]
tree = """stations/003-product-search-autocomplete/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/kartwala/search/
│   ├── SuggestionController.java   ├── SuggestionIndex.java
│   ├── ProductCatalog.java         ├── Product.java
│   ├── Suggestion.java             ├── ApiErrors.java
│   └── SearchApplication.java
├── src/test/java/com/kartwala/search/   (see Tests)
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
<p>Type a product the way a customer would, one letter more each time:</p>
""" + code("""curl "http://localhost:8080/suggestions?prefix=sa"
curl "http://localhost:8080/suggestions?prefix=sam"
curl "http://localhost:8080/suggestions?prefix=sams"

# A second word works too
curl "http://localhost:8080/suggestions?prefix=gold"

# One letter: expect 400
curl -i "http://localhost:8080/suggestions?prefix=s\"""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["A space in the prefix gives an error in the shell", "The shell splits the URL.", "Quote the URL, and write a space as <code>%20</code> or <code>+</code>."],
    ["<code>release version 25 not supported</code>", "Maven is using an older JDK.", "Point <code>JAVA_HOME</code> at JDK 25, or add <code>-Djava.version=21</code>."],
    ["<code>Port 8080 was already in use</code>", "Another app uses the port.", "Stop it, or add <code>--server.port=8081</code> as an app argument."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>SuggestionContractTest</code> ({cnt('SuggestionContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>ContainsScanTrapTest</code> ({cnt('ContainsScanTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "The index on its own", f"<code>SuggestionIndexTest</code> ({cnt('SuggestionIndexTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="note">"Not found" for a search is an empty list, not a <code>404</code>: the contract tests check <code>200</code> with no suggestions.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "ContainsScanTrapTest.java", "<p>Written first: the odd match from <code>contains()</code>, the fixed ranking, and the work counted on 2 lakh products.</p>"),
    (T + "SuggestionContractTest.java", "<p>Matches, ranking, normalising, empty results and every rejected input.</p>"),
    (T + "SuggestionIndexTest.java", "<p>The index as plain Java: duplicates, ties, range edges and a Turkish locale.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app, called through MockMvc.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/kartwala/search/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=PunctuationChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Ignore punctuation", "Beginner-friendly", 25,
    "\"parle g\" should find Parle-G Biscuits, \"55 inch\" the 55-inch TV, and \"head shoulders\" the shampoo. Treat anything that is not a letter or a digit as a space, for names and prefixes alike.",
    "all four tests in <code>PunctuationChallengeTest</code> pass, and the station's tests still pass.",
    ["Change <code>normalise</code> only. Names and prefixes both go through it, so they stay in step.",
     "<code>\\p{L}</code> is any letter and <code>\\p{N}</code> any digit, in any language. <code>[^\\p{L}\\p{N}]+</code> is a run of anything else.",
     "Replace runs with one space, then <code>strip()</code>: \"--&amp;&amp;--\" becomes empty, which is too short."],
    "challenge/PunctuationChallengeTest.java", ["challenge/solution/SuggestionIndex.java"]) + challenge(2, "Hide out-of-stock products", "Go deeper", 35,
    "Saffola Gold Oil 1L (id 8) is out of stock. Hide out-of-stock products unless the app sends <code>includeOutOfStock=true</code>, and add <code>inStock</code> to each suggestion.",
    "all three tests in <code>OutOfStockChallengeTest</code> pass. The third proves the stock filter runs before the limit.",
    ["Add <code>inStock</code> to <code>Product</code>, and keep a three-argument constructor so the station's tests still compile.",
     "Filter before <code>limit</code>. Station 002's trap, in a new place.",
     "A <code>boolean</code> parameter with <code>defaultValue = \"false\"</code> is all the controller needs."],
    "challenge/OutOfStockChallengeTest.java", ["challenge/solution/Product.java", "challenge/solution/ProductCatalog.java", "challenge/solution/Suggestion.java", "challenge/solution/SuggestionIndex.java", "challenge/solution/SuggestionController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>"s" at peak traffic</h2>
<p>Product wants suggestions from the first letter. Suppose "s" matches 30,000 of the 2 lakh products: each request would then sort 30,000 to show 5. How could you prepare the top 10 for every short prefix ahead of time? How much memory would that take for all 1- and 2-letter prefixes, and when would you rebuild it as popularity changes?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: <code>contains()</code> suggests Balsamic Vinegar and reads every name.</li>
<li>Write <code>normalise</code>, used for names and prefixes alike.</li>
<li>Build the <code>TreeMap</code> once: one key per word start, made unique with the product id.</li>
<li>Answer with <code>subMap</code>, then rank by popularity, remove duplicates, take the top N.</li>
<li>Guard the input: raw length, normalised length, limit range.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["<code>TreeMap</code> of word starts, range lookup", "Memory for one key per word (about 4 per product). Lookup reads only matches.", '<span class="pill ok">Chosen</span>'],
    ["Loop with <code>contains()</code>", "Reads every name per keystroke; mid-word matches; no ranking.", '<span class="pill bad">Wrong</span>'],
    ["Loop with <code>startsWith()</code> on the full name", "No odd matches, but still reads every name, and misses second words.", '<span class="pill bad">Wrong</span>'],
    ["A trie (prefix tree)", "The classic structure for prefixes; can store a top-10 at each node. More code than a TreeMap.", '<span class="pill warn">At larger scale</span>'],
    ["SQL <code>LIKE 'sam%'</code> with an index", "Works for the start of a column, not for later words, and adds a database round trip per keystroke.", '<span class="pill warn">Possible</span>'],
    ["A search engine (OpenSearch)", "Typos, synonyms, scoring and scale, with another system to run.", '<span class="pill warn">Later stations</span>']]) + """
<h2>Database design</h2>
<p>None: the catalogue is fixed in code and the index lives in memory. Challenge 3 asks how you would keep a precomputed top-N up to date.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Security</dt><dd>Two length checks stop expensive input. The prefix is echoed back only after normalising, as JSON data, never as HTML.</dd>
<dt>Performance</dt><dd>The work is proportional to the matches, not to the catalogue. Short prefixes still match many products; Challenge 3 is the fix. Apps also usually wait a short moment after the last keystroke (debounce) before calling, so fast typists do not send every letter.</dd>
<dt>Reliability</dt><dd>The index is rebuilt only at start-up, so new products appear after a restart. Good enough for this station, not for a live shop.</dd>
<dt>Cost</dt><dd>About 4 keys per product: for 2 lakh products, around 8 lakh short strings in memory. Measure before you assume it fits.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("How do you find every key with a given prefix in a TreeMap?", "subMap(prefix, true, prefix + Character.MAX_VALUE, false). Keys are sorted, so all keys starting with the prefix sit between the prefix itself and the prefix followed by the highest character."),
    ("Why normalise both the stored names and the search text?", "Matching compares strings exactly. If names are lower-cased but the prefix is not (or the other way round), nothing matches. One normalise method used for both keeps them in step."),
    ("Why toLowerCase(Locale.ROOT)?", "Without a locale, Java uses the server's. On a Turkish server, 'I' lower-cases to a dotless 'ı', so 'IPHONE' would never match 'iphone'. Locale.ROOT gives the same result on every server."),
    ("Why limit the prefix length?", "A minimum avoids returning a large share of the catalogue for one letter. A maximum, checked before any work, stops someone sending 5000 characters to every instance."),
    ("How do you prove an index is better than a scan?", "Count the work, not just the time: the scan reads every name; the range lookup reads only matching entries. The trap test asserts 200,026 against 5."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can say which test fails if mid-word keys are indexed."],
    ["Design", "One normalise method; a range lookup.", "You can sketch a trie with a top-10 per node."],
    ["Tests", "Contract, index and trap tests pass.", "You counted the work instead of timing it, and know why."],
    ["Explanation", "You can explain <code>subMap</code>'s two ends.", "You can explain the Turkish locale bug."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on your own code instead:</p>
<ul class="rules">
<li>Are names and prefixes normalised by the same method?</li>
<li>Does any code path read every product per request?</li>
<li>Is every <code>toLowerCase</code> given <code>Locale.ROOT</code>?</li>
<li>Is input length checked before the expensive part?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
