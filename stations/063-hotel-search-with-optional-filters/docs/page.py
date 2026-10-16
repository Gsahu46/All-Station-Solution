"""Station 063 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 63,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Data JPA Specifications · Criteria API · bound parameters · sort whitelist · PostgreSQL 17 · Testcontainers",
    "simulation": "Hotels, prices and amenities are demo data, not Ghoomo's. Nothing is booked.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/ghoomo/hotels/"
T = "src/test/java/com/ghoomo/hotels/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]
SQL = [l for l in read("docs/captures/sql.txt").splitlines()[1:] if l.strip()]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Optional filter", "A condition applied only when the user sets it.", "\"Pool: yes\" ticked or not.", "every query parameter"),
    ("SQL injection", "User text that becomes part of the SQL itself and changes what it does.", "A form where writing \"and also give me the safe key\" in the name box works.", "the old search"),
    ("Bound parameter", "A value sent separately from the SQL text, so it can only ever be a value.", "Filling a blank on a printed form; you cannot change the form.", "every <code>?</code> in the SQL capture"),
    ("Specification", "Spring Data JPA's small, combinable piece of a WHERE clause, built with the Criteria API.", "One rule card per filter, clipped together.", "<code>HotelSpecs</code>"),
    ("Whitelist", "Only values on a fixed list are accepted.", "A menu: you order what is on it.", "<code>HotelSearch.SORTS</code>"),
    ("EXISTS subquery", "\"There is at least one matching row\", without joining rows in.", "\"Has a pool?\" yes or no, not one line per pool.", "<code>hasAmenity</code>"),
]
STORY = [
    ("Twelve filters", "City, price, stars, amenities, sort and more, each optional. The old code added a piece of SQL text for each one the user set."),
    ("Two kinds of bug", "A city of <code>goa' OR '1'='1</code> returned every hotel in India; a sort parameter could run an <code>UPDATE</code>. And \"Wi-Fi and breakfast\" listed hotels with only Wi-Fi, some of them twice."),
    ("The fix", "Each filter is a Specification with its value bound as a parameter; amenities are \"exists\" checks; sort is chosen from a fixed list."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">User input is a value, never SQL. Where a value cannot be bound (a column to sort by), choose from a list.</p>

<h2>What are we building?</h2>
<p><code>GET /hotels</code> with any mix of city, price range, stars, amenities and sort, returning a page of hotels.</p>

<h2>An everyday analogy</h2>
<p>A travel agent with a printed form: tick boxes and fill blanks. Whatever you write in the \"city\" blank, the agent only ever looks it up as a city. The old system let customers write on the agent's instructions instead.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Check each parameter</strong>: shape, range, known amenity, sort on the list.</li>
<li><strong>Collect one Specification per filter set</strong>; skip the ones not given.</li>
<li><strong>Run them together</strong>: one query with bound parameters (Spring Data adds a count query only when it cannot tell the total from the page itself).</li>
<li><strong>Return the page</strong> with each hotel once.</li>
</ol>

<details class="qa check"><summary>Check yourself: why can't the sort column be a bound parameter like the city?</summary><p>A parameter is a value. <code>ORDER BY ?</code> would sort by a constant, the same for every row. Column names are part of the SQL text, so the only safe way is to map allowed words (<code>price</code>, <code>-stars</code>) to columns you chose yourself.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No booking or availability.</strong> That is station 044's calendar.</li>
<li><strong>No text search.</strong> Practice 1 adds a name filter; full-text is station 064.</li>
<li><strong>No ranking.</strong> Sorts are plain columns.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Ghoomo</strong> (a fictional travel site) built its hotel search by string concatenation. It was open to SQL injection and gave wrong results for amenities.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo data: six hotels in Goa, three in Jaipur, five amenities.</p>
<ol class="gwt">
<li><b>Given</b> no filters, <b>then</b> all 9, cheapest first.</li>
<li><b>Given</b> Goa, Wi-Fi and pool, at most Rs 5,000, <b>then</b> Calangute Sands and Candolim Palms.</li>
<li><b>Given</b> Wi-Fi and breakfast, <b>then</b> only hotels with both, each once.</li>
<li><b>Given</b> a sort not on the list, an unknown amenity, stars outside 1 to 5, or minPrice above maxPrice, <b>then</b> <code>400</code>.</li>
<li><b>Given</b> SQL in any parameter, <b>then</b> <code>400</code> or no match, and nothing in the database changes.</li>
<li><b>Given</b> no match, <b>then</b> <code>200</code> with <code>total: 0</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>No user input is ever part of the SQL text.</li>
<li>Sort fields come from a whitelist; the API's names (<code>price</code>) are not the entity's (<code>pricePerNightPaise</code>).</li>
<li>Every sort ends with the id, so equal values keep one order across pages.</li>
<li>Prices are paise inside the system; the query string takes whole rupees.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Show SQL injection in a concatenated query, and why bound parameters stop it.</li>
<li>Build optional filters with JPA Specifications.</li>
<li>Filter on a collection with EXISTS, not a join.</li>
<li>Whitelist sort fields.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Parameter", "Form", "Notes"], [
    ["<code>city</code>", "<code>goa</code>", "3 to 30 letters or hyphens; any case"],
    ["<code>minPrice</code>, <code>maxPrice</code>", "whole rupees per night", "0 to 1,00,000 (demo limit); converted to paise"],
    ["<code>stars</code>", "<code>4,5</code>", "any of these ratings, 1 to 5"],
    ["<code>amenities</code>", "<code>wifi,pool</code>", "up to 5; the hotel must have all of them"],
    ["<code>sort</code>", "<code>price</code> (default), <code>-price</code>, <code>stars</code>, <code>-stars</code>, <code>name</code>", "anything else is <code>400</code>"],
    ["<code>page</code>, <code>size</code>", "0 to 100; 1 to 50, default 20", ""]]) + """
<p>Response: <code>{total, page, sort, hotels: [{id, name, city, stars, pricePerNightPaise, amenities}]}</code>.</p>
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "A page, possibly empty"],
    ['<span class="pill warn">400</span>', "Any parameter outside the rules above, an unknown amenity, a sort not on the list, minPrice above maxPrice"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-goa-wifi-and-pool-under-rs-5000", "Case 1: Goa, Wi-Fi and pool, up to Rs 5,000", "<b>Why:</b> three filters; each hotel once, with all its amenities."),
    ("02-jaipur-4-and-5-stars-dearest-first", "Case 2: Jaipur, 4 or 5 stars, dearest first", "<b>Why:</b> a list filter and a descending sort."),
    ("03-a-sort-that-is-not-on-the-list", "Case 3: <code>sort=name; DELETE FROM hotel_amenities</code>", "<b>Why:</b> not on the list: <code>400</code>, and nothing runs."),
    ("04-an-amenity-ghoomo-does-not-list", "Case 4: Wi-Fi and sauna", "<b>Why:</b> <code>400</code> naming the unknown one, instead of silently ignoring it."),
    ("05-no-hotel-in-shimla", "Case 5: Shimla", "<b>Why:</b> no match: <code>total: 0</code>."),
]) + """
<h2>The SQL behind case 1</h2>
<p class="muted">From <code>docs/capture.sh</code>: a second copy of the app with Hibernate's SQL log on, one request (<code>docs/captures/sql.txt</code>). Every value is a <code>?</code>; the city, price and amenity codes are sent separately.</p>
""" + code("\n\n".join(SQL), "sql")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["No filters", "All 9, cheapest first", "<code>noFiltersListsEveryHotelCheapestFirst</code>"],
    ["<code>Goa</code>, <code>POOL</code>", "Matched in any case", "<code>goaWithWifiAndPoolUnderRs5000</code>"],
    ["Two amenities", "Hotels with both, each once", "<code>everyAmenityMustMatchAndEachHotelAppearsOnce</code>"],
    ["A list of stars, a price range, a sort", "Combined", "<code>starsPriceRangeAndSort</code>"],
    ["Page 2 of size 2", "The next two in sort order", "<code>pagesFollowTheSortWithoutGapsOrRepeats</code>"],
    ["Unknown sort or amenity, bad numbers, a quote in the city", "<code>400</code>", "<code>anythingOutsideTheRulesIs400</code>"],
    ["A sort carrying a <code>DELETE</code>", "<code>400</code>, no row removed", "<code>aSortThatLooksLikeSqlIsRefusedAndRunsNothing</code>"],
    ["Bad rows written directly", "Refused by named constraints", "<code>HotelDatabaseTest</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Concatenating optional filters and sort fields into SQL.</p>
<p>The old search is kept in the tests as <code>OldHotelSearch</code>, run against the same data:</p>
<ul>
<li><strong>A quote in the city.</strong> <code>goa' OR '1'='1</code> closes the string and adds a condition that is always true: 9 hotels instead of 6. The new search binds the same text as a value: no city has that name, 0 hotels.</li>
<li><strong>A second statement in the sort.</strong> <code>h.name; UPDATE hotels SET price_per_night_paise = 50000 --</code> ran the <code>UPDATE</code> on every hotel; the <code>--</code> turned the appended <code>LIMIT 20</code> into a comment. The caller only saw an error, \"Multiple ResultSets were returned by the query.\" The test runs it in a transaction and rolls it back.</li>
<li><strong>Amenities by join.</strong> <code>JOIN hotel_amenities … IN ('wifi', 'breakfast')</code> returns a row per matching amenity (Calangute Sands twice) and hotels with either one (Baga Beach Inn, Wi-Fi only). The new search asks \"exists\" once per amenity.</li>
</ul>
<p>Passing the user's sort straight to <code>Sort.by(…)</code> was tried too: Spring Data refused <code>name; DELETE …</code> itself (\"must only contain property references\"), but as a <code>500</code>, and <code>price</code> failed as a <code>500</code> because the field is <code>pricePerNightPaise</code>. The whitelist answers both with a <code>400</code> that lists the choices.</p>
<p>While building, each fix was undone once: amenities as \"any of\" turned 3 tests red; the sort straight to <code>Sort.by</code> 2; rupees used as paise 2; no lower-casing, no min/max check and no amenity check 1 each. Removing the entity graph turned nothing red: no test here counts queries (station 061 does).</p>
</div>
""" + code(read(T + "ConcatenatedSqlTrapTest.java"), "java") + code(read(T + "OldHotelSearch.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "HotelController.java", dwn("Validates every parameter, lower-cases city and amenities, turns rupees into paise.",
        "Bad input is a <code>400</code> before any query.",
        "Typos becoming silent \"no filter\"s.")),
    (J + "HotelSearch.java", dwn("Checks sort and amenities, collects one Specification per filter, runs the page.",
        "Only set filters become conditions; the sort comes from <code>SORTS</code>.",
        "Text built from input, and a sort on any column a caller names.")),
    (J + "HotelSpecs.java", dwn("One Specification per filter.",
        "Each is tiny, combinable and bound; amenities use <code>EXISTS</code>.",
        "Joined amenities: duplicates and \"any of\".")),
    (J + "HotelRepository.java", dwn("<code>JpaSpecificationExecutor</code>, with the amenities loaded in the same query.",
        "<code>findAll(spec, pageable)</code> runs the page and a count.",
        "A lazy load of amenities per hotel.")),
    (J + "Hotel.java", "<p>A hotel, with its amenities.</p>"),
    (J + "Amenity.java", "<p>An amenity code.</p>"),
    (J + "AmenityRepository.java", "<p>Known amenities, to refuse unknown ones.</p>"),
    (M + "V1__hotels.sql", dwn("Tables, named constraints and two indexes.",
        "<code>hotel_amenities_amenity</code> serves the EXISTS check.",
        "Hotels with impossible stars or prices from any writer.")),
    (M + "V2__demo_hotels.sql", "<p>Nine hotels and their amenities.</p>"),
    ("src/main/resources/application.yaml", "<p>open-in-view off, schema validation.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "HotelsApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/063-hotel-search-with-optional-filters/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/ghoomo/hotels/
│   ├── HotelController.java   ├── HotelSearch.java   ├── HotelSpecs.java   ├── HotelRepository.java
│   ├── Hotel.java   ├── Amenity.java   ├── AmenityRepository.java   └── HotelsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__hotels.sql, V2__demo_hotels.sql
├── src/test/java/com/ghoomo/hotels/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Docker", "Docker Desktop (Windows, macOS) or Docker Engine (Linux), running", "<code>docker info</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""docker compose up -d        # PostgreSQL 17 on localhost:5432
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Send the attack yourself; <code>-G --data-urlencode</code> encodes the spaces and quotes for you:</p>
""" + code("""curl -G 'http://localhost:8080/hotels' --data-urlencode "city=goa' OR '1'='1"
curl -G 'http://localhost:8080/hotels' --data-urlencode "sort=name; DELETE FROM hotel_amenities\"""", "bash") + """
<p>Both are <code>400</code>. Then open <code>OldHotelSearch</code> in the tests and see why the same text was dangerous there.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>No property 'price' found for type 'Hotel'</code>", "An API sort name passed straight to <code>Sort.by</code>.", "Map API names to fields in a whitelist."],
    ["<code>Sort expression '…' must only contain property references</code>", "Spring Data refusing an unsafe sort string.", "Never pass user text to <code>Sort</code>; it is a 500, not a 400."],
    ["<code>Multiple ResultSets were returned by the query.</code>", "A second statement ran inside a concatenated query.", "Treat it as an attack in progress; use bound parameters."],
    ["The same hotel twice", "A join on a collection used as a filter.", "<code>EXISTS</code> subqueries, as in <code>hasAmenity</code>."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the database behind it.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found (empty)", f"<code>HotelContractTest</code> ({cnt('HotelContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>ConcatenatedSqlTrapTest</code> ({cnt('ConcatenatedSqlTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>HotelDatabaseTest</code> ({cnt('HotelDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Hibernate 7.4, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "ConcatenatedSqlTrapTest.java", "<p>Written first: two injections and the amenity join, old against new.</p>"),
    (T + "HotelDatabaseTest.java", "<p>Named constraints, a rolled-back hotel, and the cascade.</p>"),
    (T + "HotelContractTest.java", "<p>The endpoint through HTTP.</p>"),
    (T + "OldHotelSearch.java", "<p>The concatenated search, kept in the tests only.</p>"),
    (T + "ApiTest.java", "<p>Shared setup.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/ghoomo/hotels/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=NameSearchChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Search by name", "Beginner-friendly", 25,
    "Add <code>q=…</code>: hotels whose name contains the text, any case, with the other filters. <code>%</code>, <code>_</code> and quotes are just characters.",
    "both tests in <code>NameSearchChallengeTest</code> pass.",
    ["A bound value is safe from injection, but inside <code>LIKE</code> it is still a <em>pattern</em>: escape <code>\\</code>, <code>%</code> and <code>_</code>, and pass the escape character to <code>cb.like</code>.",
     "Keep the old five-value <code>Filters</code> constructor working: a record can have a second constructor."],
    "challenge/NameSearchChallengeTest.java", ["challenge/solution/HotelSpecs.java", "challenge/solution/HotelSearch.java", "challenge/solution/HotelController.java"]) + challenge(2, "Counts per star rating", "Go deeper", 35,
    "Add <code>starsFacet</code> to every result: hotels per star rating with all filters except stars, for the \"4 stars (2)\" boxes.",
    "the test in <code>StarsFacetChallengeTest</code> passes.",
    ["Build the list of Specifications without stars, count with it, then add stars and search.",
     "A Specification is just <code>toPredicate(root, query, cb)</code>: use it in your own Criteria query with <code>groupBy</code>."],
    "challenge/StarsFacetChallengeTest.java", ["challenge/solution/HotelSearch.java", "challenge/solution/HotelSpecs.java", "challenge/solution/HotelController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>When Specifications are not enough</h2>
<p>Product wants \"near the beach\", typo-tolerant names, \"popular first\" and facets on every filter, on 2 lakh hotels. Which of these can PostgreSQL do well (indexes, full-text, PostGIS), and at what point does a search engine (OpenSearch, Elasticsearch) earn its cost: a second copy of the data, kept in sync, that can be minutes behind?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, indexes"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test with the old search: both injections and the amenity join.</li>
<li>One Specification per filter, each with its value bound.</li>
<li>Amenities as EXISTS; sorts from a whitelist ending in the id.</li>
<li>Validate everything at the controller; check unknown amenities against the table.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Specifications + bound values + sort whitelist", "A class of small methods.", '<span class="pill ok">Chosen</span>'],
    ["Concatenated SQL", "Injection; quoting bugs; joins that duplicate.", '<span class="pill bad">The trap</span>'],
    ["Concatenated SQL with escaping", "Every value escaped correctly, forever; the sort is still open.", '<span class="pill bad">Fragile</span>'],
    ["One JPQL query with <code>(:city IS NULL OR h.city = :city)</code>", "Safe; one plan for all combinations, often a poor one.", '<span class="pill warn">Small cases only</span>'],
    ["Querydsl or jOOQ", "A code generator and a dependency; type-safe.", '<span class="pill warn">Good at scale</span>'],
    ["A search engine", "A second store to keep in sync.", '<span class="pill warn">For text and relevance</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Constraints", "Why"], [
    ["<code>hotels</code>", "<code>hotels_city_shape</code>, <code>hotels_stars_range</code>, <code>hotels_price_range</code> (demo: Rs 500 to Rs 1 lakh), <code>hotels_name_per_city</code>; index <code>(city, price_per_night_paise)</code>", "The common search: a city by price."],
    ["<code>amenities</code>", "<code>amenities_code_shape</code>", "Lower-case codes."],
    ["<code>hotel_amenities</code>", "<code>hotel_amenities_pk</code>, two foreign keys; index <code>(amenity_code, hotel_id)</code>", "The EXISTS check per amenity."]]) + """
""" + code(read(M + "V1__hotels.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Least privilege</dt><dd>The app's database user needs <code>SELECT</code> on these tables, not <code>UPDATE</code> or <code>DELETE</code>. The injected <code>UPDATE</code> in the trap would then have failed.</dd>
<dt>Multiple statements</dt><dd>The injection worked because the PostgreSQL driver ran two statements sent as one string through a plain <code>Statement</code>. Prepared statements never do.</dd>
<dt>Filter combinations</dt><dd>Twelve optional filters are 4,096 combinations. Index the common ones (city plus price); watch slow queries for the rest.</dd>
<dt>Logs</dt><dd>Log the parameters of a search, not a SQL string with them inside: one is data, the other is a template for the next attack.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is SQL injection?", "User input that becomes part of the SQL text, so it can change the query: add conditions, run other statements, read other tables."),
    ("Why do bound parameters prevent it?", "The SQL text is fixed and sent first; values travel separately and are only ever used as values, never parsed as SQL."),
    ("How do you sort by a user-chosen column safely?", "Map a fixed set of API names to columns you chose; refuse everything else. A column name cannot be a parameter."),
    ("What is a JPA Specification?", "A function (root, query, criteriaBuilder) → Predicate. Small ones combine with and/or into a query, each value bound."),
    ("Why EXISTS instead of a join for \"has amenity\"?", "A join returns a row per matching amenity, duplicating hotels; EXISTS asks one yes/no question per hotel."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran both injections against the old search."],
    ["Security", "No input in SQL text; a sort whitelist.", "Least privilege for the app's database user."],
    ["JPA", "One Specification per filter.", "Reusing them for counts (Practice 2)."],
    ["Results", "Each hotel once; all amenities required.", "Why the join duplicated."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This station has no flawed version to review. Use this checklist on any search endpoint:</p>
<ul class="rules">
<li>Is any request value concatenated into SQL, JPQL or a <code>Sort</code>?</li>
<li>Is the sort chosen from a fixed list, ending in a unique column?</li>
<li>Can a filter on a collection return the same row twice?</li>
<li>Is <code>LIKE</code> input escaped?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
