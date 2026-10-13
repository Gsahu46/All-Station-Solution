"""Station 002 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 2,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · Bean Validation · MockMvc",
    "simulation": "Two restaurants and their dishes are a fixed list inside the app. Nothing reads a real restaurant database.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tiffino/menu/"
T = "src/test/java/com/tiffino/menu/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Query parameter", "An optional setting after <code>?</code> in a URL, as <code>name=value</code> pairs joined by <code>&amp;</code>.", "Ticking boxes on a paper order form.", "<code>?veg=true&amp;maxPrice=200</code>"),
    ("Default value", "The value used when the client leaves a parameter out.", "\"Regular\" size when you do not say which.", "<code>limit</code> is 20, <code>sort</code> is <code>recommended</code>."),
    ("Filter", "Keep only the items that pass a test.", "Picking only the green chillies from a basket.", "Veg only; at most ₹200."),
    ("Sort", "Put items in an order.", "Lining up by height.", "Cheapest first."),
    ("Limit", "Keep only the first N items.", "\"Show me five.\"", "<code>limit=5</code>"),
    ("Stream", "Java's way to run a list through steps: filter, sort, limit, collect.", "A conveyor belt with stations along it.", "<code>MenuQuery.apply</code>"),
    ("Comparator", "A rule that says which of two items comes first.", "\"Shorter person stands in front.\"", "By price, then by name."),
    ("Validation", "Checking a value is allowed before using it.", "A form that will not take 0 as your age.", "<code>limit</code> must be 1 to 50."),
]
STORY = [
    ("Meera is hungry and has ₹200", "She opens Annapoorna Mess on Tiffino and wants a veg dish she can afford."),
    ("The menu is a wall of 140 dishes", "Every dish, unsorted, veg and non-veg mixed. She scrolls, gives up, and orders elsewhere."),
    ("The fix", "The app sends her choices to the server, <em>veg, at most ₹200, cheapest first, 5 dishes</em>, and gets exactly those back."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">The order of the steps changes the answer. "The cheapest 5" means sort everything, then take 5. Take 5 first and you get 5 random dishes that only <em>look</em> sorted.</p>

<h2>What are we building?</h2>
<p>One endpoint, <code>GET /restaurants/{id}/menu</code>, with four optional query parameters: <code>veg</code>, <code>maxPrice</code>, <code>sort</code> and <code>limit</code>. Bad values get a clear <code>400</code>, an unknown restaurant gets <code>404</code>.</p>

<h2>An everyday analogy</h2>
<p>At a sweet shop you ask: "Your five cheapest sweets, please." The shopkeeper who does it right looks at every tray, then picks the five lowest prices. The careless one grabs the first five boxes on the counter and arranges them by price. Both hand you five sweets in price order; only one answered your question.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Read the choices</strong> from the URL, with defaults for any left out.</li>
<li><strong>Check them</strong>: limit from 1 to 50, a known sort, a positive price. Anything else: <code>400</code>.</li>
<li><strong>Filter</strong> the restaurant's dishes (veg, price), then <strong>sort</strong> them, then <strong>limit</strong>.</li>
<li><strong>Answer</strong> with the dishes. No match is an empty list, not an error.</li>
</ol>

<details class="qa check"><summary>Check yourself: the kitchen added a ₹60 Idli at the end of the menu. Would "limit, then sort" ever show it as one of the cheapest 5?</summary><p>No. "Limit, then sort" only ever looks at the first 5 dishes typed in, so a cheap dish added at the end can never appear. "Sort, then limit" looks at all dishes first, so the ₹60 Idli comes first.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>Not a real restaurant database.</strong> Two restaurants are fixed in the code; databases come in later stations.</li>
<li><strong>No paging.</strong> <code>limit</code> caps the list; "next page" is a later station.</li>
<li><strong>No search by name.</strong> That is Practice challenge 1.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tiffino</strong> (a fictional food-delivery app) shows each restaurant's full menu in the order the kitchen typed it in. Customers with a budget or a diet scroll through up to 140 dishes. The product team added "Veg only", "Under ₹200" and "Cheapest first" buttons to the app, but the API ignores them and returns everything.</p>
<p>A first attempt returned the "cheapest 5" by taking the first 5 dishes and sorting those. In a demo with a 6-dish menu nobody noticed. On a real menu it showed a ₹360 dish as "cheap" and hid a ₹60 one.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> <code>veg=true&amp;maxPrice=200&amp;sort=price_asc&amp;limit=5</code>, <b>then</b> the 5 cheapest veg dishes priced at most ₹200 are returned, cheapest first.</li>
<li><b>Given</b> no parameters, <b>then</b> up to 20 dishes are returned, most ordered last week first.</li>
<li><b>Given</b> two dishes at the same price, <b>then</b> they are ordered by name, so the same request always gives the same list.</li>
<li><b>Given</b> filters that match nothing, <b>then</b> <code>200</code> with an empty <code>dishes</code> list.</li>
<li><b>Given</b> <code>limit=0</code>, <code>limit=500</code>, <code>maxPrice=-5</code>, <code>sort=cheapest</code> or <code>veg=maybe</code>, <b>then</b> <code>400</code> with a problem body naming each bad parameter.</li>
<li><b>Given</b> an unknown restaurant, <b>then</b> <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li><code>veg</code>: optional. <code>true</code> veg only, <code>false</code> non-veg only, left out means both.</li>
<li><code>maxPrice</code>: optional, whole rupees, 1 to 1,00,000, inclusive. Dish prices are stored in paise.</li>
<li><code>sort</code>: <code>recommended</code> (default, most ordered first), <code>price_asc</code> or <code>price_desc</code>. Ties by name.</li>
<li><code>limit</code>: 1 to 50, default 20.</li>
<li>Steps run in this order: filter, sort, limit.</li>
<li>Errors are RFC 9457 <code>application/problem+json</code>, with an <code>errors</code> map for bad parameters.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Read optional query parameters with <code>@RequestParam</code>, <code>required = false</code> and <code>defaultValue</code>.</li>
<li>Validate them with <code>@Min</code>, <code>@Max</code> and <code>@Pattern</code>.</li>
<li>Write a stream pipeline: <code>filter</code>, <code>sorted</code>, <code>limit</code>, <code>toList</code>.</li>
<li>Build a <code>Comparator</code> with <code>reversed()</code> and <code>thenComparing()</code>.</li>
<li>Explain why the order of <code>sorted</code> and <code>limit</code> matters.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [["<code>GET</code>", "<code>/restaurants/{id}/menu</code>", "A restaurant's dishes, filtered, sorted and limited."]]) + """
<h2>Query parameters</h2>
""" + table(["Parameter", "Type", "Default", "Rule"], [
    ["<code>veg</code>", "boolean", "both", "<code>true</code> or <code>false</code>."],
    ["<code>maxPrice</code>", "integer, rupees", "no limit", "1 to 100000. Inclusive: <code>200</code> keeps a ₹200.00 dish."],
    ["<code>sort</code>", "string", "<code>recommended</code>", "<code>recommended</code>, <code>price_asc</code> or <code>price_desc</code>."],
    ["<code>limit</code>", "integer", "20", "1 to 50."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When", "Body"], [
    ['<span class="pill ok">200</span>', "The restaurant exists (even if nothing matches)", "<code>restaurantId</code>, <code>restaurantName</code>, <code>dishes</code>"],
    ['<span class="pill warn">400</span>', "A parameter is out of range, unknown, or the wrong type", "Problem with <code>errors</code> (parameter → message) for range and sort errors"],
    ['<span class="pill warn">404</span>', "No restaurant has this id", "Problem: <em>Restaurant not found</em>"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-veg-under-200", "Case 1: Meera's question", "<b>Why:</b> every veg dish at most ₹200 is found first, then sorted by price, then cut to 5. ₹80 Curd Rice comes before ₹80 Lemon Rice because ties are ordered by name."),
    ("02-defaults", "Case 2: no filters, 3 dishes", "<b>Why:</b> the default sort is <code>recommended</code>: most ordered last week first."),
    ("03-nothing-matches", "Case 3: no veg dishes at a grill", "<b>Why:</b> the restaurant exists, so <code>200</code>; nothing matched, so the list is empty. Not a <code>404</code>."),
    ("04-invalid-filters", "Case 4: impossible filters", "<b>Why:</b> <code>limit=0</code> and an unknown sort are both rejected in one answer, each with its own message, before any dish is read."),
    ("05-unknown-restaurant", "Case 5: unknown restaurant", "<b>Why:</b> no restaurant 999, so <code>404</code> with a problem body."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What the API does", "Proved by"], [
    ["\"Cheapest 5\"", "Sort all, then take 5", "<code>sortBeforeLimitReturnsTheFiveCheapestDishes</code>"],
    ["Veg, at most ₹200, cheapest 5", "Only veg, only ≤ 20000 paise, in price order", "<code>vegUnder200CheapestFirstIsTheCustomersQuestion</code>"],
    ["A dish priced exactly at <code>maxPrice</code>", "Included", "<code>maxPriceIsInclusiveAndInRupees</code>, <code>maxPriceComparesRupeesWithPaiseExactly</code>"],
    ["<code>veg=false</code>", "Non-veg only (not \"ignore the filter\")", "<code>vegFalseMeansNonVegOnly</code>"],
    ["Two dishes at the same price", "Ordered by name, every time", "<code>equalPricesAreOrderedByNameSoTheAnswerNeverChanges</code>, <code>recommendedTiesAreBrokenByName</code>"],
    ["Nothing matches", "<code>200</code>, empty list", "<code>noMatchingDishIsAnEmptyListNotAnError</code>"],
    ["<code>limit=0</code>, <code>limit=500</code>, <code>maxPrice=-5</code>, unknown sort", "<code>400</code>, one message per parameter", "<code>outOfRangeFiltersAre400WithOneMessagePerParameter</code>, <code>limitAbove50Is400</code>"],
    ["<code>veg=maybe</code>, <code>limit=five</code>, restaurant <code>abc</code>", "<code>400</code> problem", "<code>valuesOfTheWrongTypeAre400</code>"],
    ["Unknown restaurant", "<code>404</code> problem", "<code>unknownRestaurantIs404Problem</code>"],
    ["The catalogue list itself", "Never re-ordered by a request", "<code>theInputListIsNotChanged</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Applying <code>limit</code> before <code>sort</code>, so "cheapest 5" returns 5 arbitrary dishes, neatly sorted.</p>
<p>The result looks right: five dishes in price order. A quick manual test with a short menu passes. The first test in this station proves the bug with a "before" controller: its "cheapest 5" includes a ₹360 dish and misses the ₹60 one. The second test runs the real API and gets the true five. Moving <code>limit</code> above <code>sorted</code> in <code>MenuQuery</code> turns 4 tests red; that was checked while building the station.</p>
</div>
""" + code(read(T + "LimitBeforeSortTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "MenuController.java", dwn("Reads the four query parameters with their defaults and limits, finds the restaurant, and returns the menu.",
        "The constraint annotations sit next to the parameters they guard, so the rules are visible at the door.",
        "No endpoint; and without the annotations, <code>limit=0</code> or <code>limit=1000000</code> reaches the stream.",
        "<ul><li><code>Boolean veg</code> (capital B) can be <code>null</code>, which means \"no filter\". A <code>boolean</code> could not say that.</li><li>An unknown restaurant throws <code>ErrorResponseException</code>; Spring turns it into a <code>404</code> problem body.</li></ul>")),
    (J + "MenuQuery.java", dwn("Runs the dishes through filter, sort, limit, in that order.",
        "One small class holds the whole rule, so it is easy to unit-test without Spring.",
        "The pipeline ends up in the controller, and the trap is easy to re-introduce unnoticed.",
        "<ul><li><code>thenComparing(Dish::name)</code> breaks ties, so equal prices never swap places between requests.</li><li><code>maxPrice * 100</code> converts rupees to paise once, with integers only.</li></ul>")),
    (J + "MenuCatalog.java", dwn("Holds two restaurants and their dishes, in the order a kitchen typed them.",
        "Keeps data out of the controller; a database replaces it later.",
        "The test data would live inside the controller.")),
    (J + "Dish.java", "<p>One dish. <code>pricePaise</code> is an <code>int</code> of paise, never a <code>double</code>.</p>"),
    (J + "Menu.java", "<p>The response body: restaurant id and name, and the dishes.</p>"),
    (J + "Restaurant.java", "<p>A restaurant and its dishes, used inside the app only.</p>"),
    (J + "ApiErrors.java", dwn("Adds an <code>errors</code> map (parameter → message) to validation failures.",
        "Spring's default 400 body says \"Validation failure\"; the app needs to know which filter was wrong.",
        "The app gets a 400 with no hint which parameter to fix.")),
    (J + "MenuApplication.java", "<p>Standard Spring Boot entry point.</p>"),
    ("pom.xml", "<p>Adds <code>spring-boot-starter-validation</code> to station 001's set; it brings the validator that checks <code>@Min</code>, <code>@Max</code> and <code>@Pattern</code>.</p>"),
]
tree = """stations/002-restaurant-menu-filters/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tiffino/menu/
│   ├── MenuController.java   ├── MenuQuery.java     ├── MenuCatalog.java
│   ├── Dish.java             ├── Menu.java          ├── Restaurant.java
│   ├── ApiErrors.java        └── MenuApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/tiffino/menu/   (see Tests)
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
<p>Quote the URL: <code>&amp;</code> means something else to the shell.</p>
""" + code("""# Veg, at most Rs 200, cheapest first, 5 dishes: expect Idli Sambar first
curl -i "http://localhost:8080/restaurants/101/menu?veg=true&maxPrice=200&sort=price_asc&limit=5"

# The same without sort: most ordered first
curl -i "http://localhost:8080/restaurants/101/menu?veg=true&maxPrice=200&limit=5"

# A bad limit: expect 400 with "errors": {"limit": ...}
curl -i "http://localhost:8080/restaurants/101/menu?limit=0\"""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Only the first filter seems to work", "The shell cut the URL at <code>&amp;</code>.", "Put the whole URL in double quotes."],
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>MenuContractTest</code> ({cnt('MenuContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>LimitBeforeSortTrapTest</code> ({cnt('LimitBeforeSortTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "The pipeline on its own, without Spring", f"<code>MenuQueryTest</code> ({cnt('MenuQueryTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "LimitBeforeSortTrapTest.java", "<p>Written first: \"limit, then sort\" against \"sort, then limit\".</p>"),
    (T + "MenuContractTest.java", "<p>Defaults, each filter, ties, empty results, and every kind of bad parameter.</p>"),
    (T + "MenuQueryTest.java", "<p>The stream pipeline as plain Java: order of steps, ties, rupees against paise, and the input list left untouched.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app, called through MockMvc.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tiffino/menu/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=NameSearchChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Search dishes by name", "Beginner-friendly", 30,
    "Add an optional <code>q</code> parameter: keep only dishes whose name contains it, ignoring letter case and surrounding spaces. At most 40 characters. It must work on a server running in a Turkish locale.",
    "all four tests in <code>NameSearchChallengeTest</code> pass, and the station's tests still pass.",
    ["Add the filter before <code>sorted</code>, next to the other two.",
     "<code>strip()</code> removes surrounding spaces; <code>toLowerCase(Locale.ROOT)</code> on both sides makes the match case-insensitive everywhere.",
     "<code>@Size(max = 40)</code> on the parameter gives the <code>400</code>.",
     "The station's <code>MenuQueryTest</code> builds a query with 4 arguments; keep that constructor working."],
    "challenge/NameSearchChallengeTest.java", ["challenge/solution/MenuQuery.java", "challenge/solution/MenuController.java"]) + challenge(2, "Show \"5 of 9\"", "Beginner-friendly", 20,
    "Add <code>totalMatching</code> to the response: how many dishes passed the filters, before the limit. The app uses it to show \"Showing 5 of 9\".",
    "both tests in <code>MatchCountChallengeTest</code> pass.",
    ["Count after the filters and before <code>limit</code>; that is the same question as the trap, the other way round.",
     "Put the filters in one private method that both the list and the count use, so they can never disagree."],
    "challenge/MatchCountChallengeTest.java", ["challenge/solution/Menu.java", "challenge/solution/MenuQuery.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>140 dishes become 14,000 rows</h2>
<p>All Tiffino restaurants now share one database table of dishes. Where should filtering, sorting and limiting happen: in Java after loading everything, or in SQL (<code>WHERE</code>, <code>ORDER BY</code>, <code>LIMIT</code>)? What does each choice cost in memory and time? Which index would make "veg dishes of restaurant 101, cheapest first" fast?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: "cheapest 5" must not be "first 5, sorted".</li>
<li>Declare the four parameters with defaults and limits on the controller method.</li>
<li>Put the pipeline in <code>MenuQuery</code>: filter, sort with a tie-breaker, limit.</li>
<li>Answer an unknown restaurant with <code>404</code>, an empty match with <code>200 []</code>.</li>
<li>Add the <code>errors</code> map so each bad parameter is named.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Filter, sort, limit in a stream over the restaurant's dishes", "Loads every dish of one restaurant (at most a few hundred). Simple and fast enough.", '<span class="pill ok">Chosen</span>'],
    ["Limit, then sort", "Wrong answers that look right.", '<span class="pill bad">Wrong</span>'],
    ["Sort without a tie-breaker", "Equal prices can swap between requests; paging later shows a dish twice or never.", '<span class="pill bad">Wrong</span>'],
    ["<code>sort</code> as a Java enum", "Spring converts it for you, but enum names are upper case (<code>PRICE_ASC</code>) unless you add a converter.", '<span class="pill warn">Possible</span>'],
    ["Do it in SQL (<code>WHERE</code>, <code>ORDER BY</code>, <code>LIMIT</code>)", "The right choice once dishes live in a database and menus are large. Same rule: the database sorts before it limits.", '<span class="pill warn">Later stations</span>'],
    ["Return everything and let the app filter", "Sends 140 dishes to every phone on every visit; the app's logic drifts from the server's.", '<span class="pill bad">Wrong</span>']]) + """
<h2>Database design</h2>
<p>None in this station: dishes are a fixed list in <code>MenuCatalog</code>. Challenge 3 asks you to think about the SQL version.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Security</dt><dd>Every parameter has a range, so a request cannot ask for a million rows. The <code>400</code> body names the parameter but never echoes a stack trace.</dd>
<dt>Performance</dt><dd>Sorting a few hundred dishes takes microseconds. The <code>limit</code> cap of 50 keeps responses small for phones on slow networks.</dd>
<dt>Reliability</dt><dd>The tie-breaker makes answers deterministic, which matters as soon as results are cached or paged.</dd>
<dt>Maintainability</dt><dd>Adding a filter means one parameter and one <code>filter</code> line, before the sort.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why does the order of sorted() and limit() matter?", "limit keeps the first N items of whatever reaches it. Before sorting, those are just the first N in storage order; after sorting, they are the N smallest. Same code, different question answered."),
    ("Why break ties by name?", "Without a tie-breaker, two items that compare equal can come back in either order. Clients see the list change between identical requests, and paging can skip or repeat items."),
    ("Boolean or boolean for an optional filter?", "Boolean, because it can be null, which means 'not given'. A primitive boolean defaults to false, so 'veg not given' and 'non-veg only' would look the same."),
    ("What happens when a query parameter fails @Min?", "Spring validates the method's parameters before calling it and throws HandlerMethodValidationException, which becomes a 400. The method body never runs."),
    ("No dishes match: 200 or 404?", "200 with an empty list. The restaurant exists and the query was valid; 'no results' is a valid answer. 404 would tell the app the restaurant does not exist."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can predict which tests fail if <code>limit</code> moves above <code>sorted</code>."],
    ["Robustness", "Every bad parameter gets a <code>400</code> naming it.", "You found a parameter combination the tests do not cover, and added it."],
    ["Design", "Filter, sort, limit; ties broken.", "You can explain where this belongs once dishes are in a database."],
    ["Explanation", "You can walk through the stream line by line.", "You can explain <code>Boolean</code> against <code>boolean</code> for optional filters."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on your own code instead:</p>
<ul class="rules">
<li>Is <code>limit</code> the last step, after every filter and the sort?</li>
<li>Does every sort have a tie-breaker?</li>
<li>Does every numeric parameter have both a minimum and a maximum?</li>
<li>Is "nothing matched" a <code>200</code> with an empty list?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
