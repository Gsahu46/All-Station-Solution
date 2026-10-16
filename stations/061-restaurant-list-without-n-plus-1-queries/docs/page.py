"""Station 061 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 61,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Data JPA · Hibernate 7.4 · @EntityGraph · DTO projections · Hibernate statistics · PostgreSQL 17 · Testcontainers",
    "simulation": "Cities, restaurants, cuisines and ratings are demo data, not Tiffino's. Nothing is ordered or delivered.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tiffino/restaurants/"
T = "src/test/java/com/tiffino/restaurants/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]
SQL = [l for l in read("docs/captures/sql.txt").splitlines()[1:] if l.strip()]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Query", "One question sent to the database.", "One trip to the storeroom.", "counted by Hibernate statistics in the tests"),
    ("Lazy loading", "A related collection is fetched only when the code first touches it.", "The menu card stays in the drawer until someone asks for it.", "<code>Restaurant.cuisines</code>"),
    ("N+1", "One query for the list, then one more for each item in it.", "Fifty trips to the storeroom, one per box, instead of one trolley.", "the old home screen: 1 + 50 + 50"),
    ("Entity graph", "Tells JPA which associations to load together with the entity.", "\"Bring the menu card with the restaurant.\"", "<code>@EntityGraph(attributePaths = \"cuisines\")</code>"),
    ("DTO projection", "The query builds a small result object directly, without loading entities.", "Asking for the total, not every receipt.", "<code>RatingSummary</code>"),
    ("Fetch join", "<code>JOIN FETCH</code> in JPQL: load the association in the same query.", "Like the entity graph, but an inner join unless you write <code>LEFT</code>.", "the trap's first fix"),
]
STORY = [
    ("The home screen", "Tiffino shows 50 restaurants of a city, each with its cuisines and its star rating."),
    ("The slow part", "The code loaded 50 restaurants, then for each one asked for its cuisines and its reviews: 101 queries for one screen. Each is fast; 101 of them on every app launch is not."),
    ("The fix", "Three queries, whatever the page size: the page, the cuisines of those restaurants, and the ratings already averaged by the database."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Count the queries. The number should not grow with the page.</p>

<h2>What are we building?</h2>
<p><code>GET /restaurants?city=pune</code> returns a page of restaurants with their cuisines and ratings, in three queries.</p>

<h2>An everyday analogy</h2>
<p>A waiter taking an order for a table of 50. The slow way: walk to the kitchen for the first plate, come back, walk again for the second. The fast way: one trip with a trolley for all the plates, one for all the drinks.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Find the page</strong>: the ids of up to 50 restaurants in the city, in name order.</li>
<li><strong>Load those restaurants</strong> with their cuisines, in one join.</li>
<li><strong>Ask for the ratings</strong>: average and count per restaurant, computed by the database in one query.</li>
<li><strong>Put the cards together</strong> in the page's order.</li>
</ol>

<details class="qa check"><summary>Check yourself: the page size goes from 20 to 50. How many queries does the new screen send? And the old one?</summary><p>The new one: still 3. The old one: from 41 (1 + 20 + 20) to 101 (1 + 50 + 50). The test checks the new one at sizes 5, 20 and 50.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No ordering or delivery.</strong> Restaurants are read only.</li>
<li><strong>No caching.</strong> Fewer queries first; a cache is another station.</li>
<li><strong>No search or ranking.</strong> Name order; Practice 2 adds rating order.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tiffino</strong> (a fictional food delivery app) opens on a list of restaurants. For 50 restaurants with their cuisines and ratings, the server ran 1 + 50 + 50 queries on every launch.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo data: Mumbai has 3 restaurants written out by hand, Pune has 60 generated ones, Nagpur none.</p>
<ol class="gwt">
<li><b>Given</b> <code>city=mumbai</code>, <b>then</b> Anand Stall, Bombay Canteen and Cafe Madras, in name order, each with its cuisines sorted and its rating rounded to one decimal.</li>
<li><b>Given</b> a restaurant with no reviews, <b>then</b> <code>average</code> is <code>null</code> and <code>count</code> is 0.</li>
<li><b>Given</b> any page of up to 50, <b>then</b> 3 queries.</li>
<li><b>Given</b> <code>city=nagpur</code> or a page past the end, <b>then</b> <code>200</code> with no restaurants; a city Tiffino does not serve, <code>404</code>.</li>
<li><b>Given</b> no city, a page size of 0 or over 50, or a negative page, <b>then</b> <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>A fixed number of queries per page, proved by counting them in a test.</li>
<li>Paging happens in the database (<code>LIMIT</code>/<code>OFFSET</code>), never in memory.</li>
<li>A restaurant with no cuisines or no reviews still appears.</li>
<li>City codes are lower-cased with <code>Locale.ROOT</code>.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Spot an N+1 in code and prove it with a query count.</li>
<li>Fix it with <code>@EntityGraph</code> or <code>JOIN FETCH</code>, and know the difference.</li>
<li>Use a DTO projection for aggregates.</li>
<li>Page safely when a collection is loaded too.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/restaurants?city=…&amp;page=0&amp;size=20</code>", "A page of the city's restaurants: <code>{city, page, size, restaurants: [{id, name, cuisines, rating: {average, count}}]}</code>."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "A page, possibly empty"],
    ['<span class="pill warn">400</span>', "No city, a city outside <code>[A-Za-z-]{3,30}</code>, page below 0 or above 1000, size below 1 or above 50 (demo limits)"],
    ['<span class="pill warn">404</span>', "A city Tiffino does not serve"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-mumbai", "Case 1: Mumbai", "<b>Why:</b> every number here can be checked against the demo data; Anand Stall has no reviews yet."),
    ("02-pune-first-five", "Case 2: the first five in Pune", "<b>Why:</b> a page, in name order."),
    ("03-nagpur-no-restaurants-yet", "Case 3: Nagpur, typed with a capital", "<b>Why:</b> a city Tiffino serves with no restaurants yet: an empty page, not a <code>404</code>."),
    ("04-a-city-tiffino-does-not-serve", "Case 4: Jaipur", "<b>Why:</b> <code>404</code>."),
    ("05-too-big-a-page", "Case 5: size 500", "<b>Why:</b> <code>400</code>; a page is at most 50."),
]) + """
<h2>The SQL behind one page of 50</h2>
<p class="muted">From <code>docs/capture.sh</code>: a second copy of the app with Hibernate's SQL log switched on, one request (<code>docs/captures/sql.txt</code>). """ + str(len(SQL)) + """ statements.</p>
""" + code("\n\n".join(SQL), "sql")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A restaurant with no reviews", "<code>average: null</code>, <code>count: 0</code>", "<code>mumbaiListsItsRestaurantsWithCuisinesAndRatings</code>"],
    ["A restaurant with no cuisines", "Still listed", "<code>aFetchJoinPageLeavesOutRestaurantsWithNoCuisines</code>"],
    ["Pages of 5, 20 and 50", "3 queries each", "<code>theNewScreenSendsThreeQueriesForAnyPageSize</code>"],
    ["Page 2 of Pune", "Continues where page 1 stopped", "<code>puneComesInPages</code>"],
    ["<code>MUMBAI</code>", "Same as <code>mumbai</code>", "<code>theCityIsMatchedInAnyCase</code>"],
    ["Nagpur; past the last page; Jaipur", "Empty; empty; <code>404</code>", "<code>aCityWithNoRestaurantsOrAPagePastTheEndIsEmpty</code>, <code>aCityTiffinoDoesNotServeIs404</code>"],
    ["Bad parameters", "<code>400</code>", "<code>badParametersAre400</code>"],
    ["Bad rows written directly; a half-added restaurant", "Refused; rolled back", "<code>RestaurantDatabaseTest</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Lazy loading inside a loop: 1 + N queries per page.</p>
<p>The old screen is kept in the tests as <code>OldHomeScreen</code>. Its results are right; the test proves the new screen gives exactly the same cards. Only the query count differs: 101 against 3.</p>
<p>The first fix people reach for is <code>JOIN FETCH</code> with the same page. Two things to know:</p>
<ul>
<li><strong>Paging.</strong> Hibernate 5 loaded <em>every</em> matching row and cut the page in memory, with the warning HHH000104. Hibernate 7.4, used here, puts the page in a subquery instead: the test counts 1 query. Check your version's SQL before trusting either.</li>
<li><strong>Inner join.</strong> <code>JOIN FETCH</code> drops rows with nothing to join. A new restaurant with no cuisines yet vanishes from the page. The entity graph uses a left join, so the new screen still lists it.</li>
</ul>
<p>While building, each fix was undone once: no entity graph turned 1 test red (the query count); an inner <code>JOIN FETCH</code> 1; losing the page order 2; no rounding 2; no <code>404</code> and no lower-casing 1 each.</p>
</div>
""" + code(read(T + "NPlusOneTrapTest.java"), "java") + code(read(T + "OldHomeScreen.java"), "java") + code(read(T + "OldRestaurants.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "RestaurantController.java", dwn("Checks the parameters and lower-cases the city.",
        "Page size and number are limited before any query.",
        "<code>size=100000</code> loading a whole city.")),
    (J + "HomeScreen.java", dwn("The three queries, then the cards in page order.",
        "The number of queries stays the same for any page size.",
        "One query per restaurant per association.",
        "<ul><li>The city is looked up only when the page is empty, so the usual path stays at three.</li><li><code>findByIdIn</code> returns rows in any order; the cards follow the ids of query 1.</li></ul>")),
    (J + "RestaurantRepository.java", dwn("Query 1 (a page of ids) and query 2 (those restaurants with cuisines).",
        "Paging ids only lets the database apply <code>LIMIT</code>; the entity graph loads cuisines with a left join.",
        "A lazy load per restaurant, or a fetch join that hides restaurants without cuisines.")),
    (J + "ReviewRepository.java", dwn("Query 3: average and count per restaurant, as <code>RatingSummary</code> objects.",
        "The database averages; no review row reaches Java.",
        "Loading every review to average them in a loop.")),
    (J + "RatingSummary.java", "<p>The projection: built by <code>select new …</code>.</p>"),
    (J + "Restaurant.java", "<p>A restaurant; its cuisines are lazy, the JPA default for collections.</p>"),
    (J + "Review.java", "<p>One rating, 1 to 5.</p>"),
    (J + "Cuisine.java", "<p>A cuisine.</p>"),
    (J + "City.java", "<p>A city Tiffino serves.</p>"),
    (J + "CityRepository.java", "<p>\"Does this city exist\", for empty pages only.</p>"),
    (M + "V1__restaurants.sql", dwn("The tables, named constraints and the page index.",
        "<code>restaurants_city_name</code> matches the page query's filter and order.",
        "A sort of the whole city on every page.")),
    (M + "V2__demo_restaurants.sql", "<p>3 Mumbai restaurants by hand, 60 in Pune generated, none in Nagpur.</p>"),
    ("src/main/resources/application.yaml", "<p>open-in-view off: a lazy association cannot load quietly while the response is written.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "RestaurantsApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/061-restaurant-list-without-n-plus-1-queries/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/tiffino/restaurants/
│   ├── RestaurantController.java   ├── HomeScreen.java
│   ├── RestaurantRepository.java   ├── ReviewRepository.java   ├── RatingSummary.java
│   ├── Restaurant.java   ├── Review.java   ├── Cuisine.java   ├── City.java   ├── CityRepository.java
│   └── RestaurantsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__restaurants.sql, V2__demo_restaurants.sql
├── src/test/java/com/tiffino/restaurants/   (see Tests)
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
<p>Watch the SQL yourself: start the app with Hibernate's SQL log on, call the endpoint once, and count the lines.</p>
""" + code("""./mvnw spring-boot:run -Dspring-boot.run.arguments=--logging.level.org.hibernate.SQL=debug
curl 'http://localhost:8080/restaurants?city=pune&size=50'""", "bash") + """
<p>The capture above did exactly this. Then remove <code>@EntityGraph</code> from <code>findByIdIn</code> and count again.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>No qualifying bean of type '…OldHomeScreen$OldRestaurants'</code>", "Spring Data ignores repository interfaces nested inside a class.", "Make each repository a top-level interface. Found while building this station."],
    ["<code>LazyInitializationException</code>", "A lazy collection touched after the transaction ended (open-in-view is off).", "Load it in the service: an entity graph or a fetch join."],
    ["<code>HHH000104: firstResult/maxResults specified with collection fetch; applying in memory</code>", "Older Hibernate paging a fetch join in memory.", "Page the ids first, as here, then load the page."],
    ["A restaurant missing from the page", "An inner <code>JOIN FETCH</code> on an empty collection.", "<code>LEFT JOIN FETCH</code>, or an entity graph."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>RestaurantContractTest</code> ({cnt('RestaurantContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>NPlusOneTrapTest</code> ({cnt('NPlusOneTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>RestaurantDatabaseTest</code> ({cnt('RestaurantDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>How the queries are counted</h2>
<p>The tests switch on Hibernate statistics (<code>hibernate.generate_statistics=true</code>, tests only) and read <code>getPrepareStatementCount()</code> around each call: every SQL statement Hibernate sends, including lazy loads.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Hibernate 7.4, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "NPlusOneTrapTest.java", "<p>Written first: 101 queries old, 3 new, the same cards, and the fetch-join page.</p>"),
    (T + "RestaurantDatabaseTest.java", "<p>Named constraints with plain SQL, a rolled-back restaurant, and cascades, in a test city removed afterwards.</p>"),
    (T + "RestaurantContractTest.java", "<p>The endpoint through HTTP.</p>"),
    (T + "OldHomeScreen.java", "<p>The old screen, kept in the tests only.</p>"),
    (T + "OldRestaurants.java", "<p>The old queries, including the fetch-join page.</p>"),
    (T + "OldReviews.java", "<p>The old per-restaurant review query.</p>"),
    (T + "ApiTest.java", "<p>Shared setup and the query counter.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tiffino/restaurants/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=CuisineFilterChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Filter by cuisine", "Beginner-friendly", 25,
    "Add <code>cuisine=…</code>: only restaurants serving it (any case), each card still with <em>all</em> its cuisines, still three queries.",
    "both tests in <code>CuisineFilterChallengeTest</code> pass.",
    ["Only query 1 changes. Filter with <code>exists (select 1 … join x.cuisines c where … lower(c.name) = lower(:cuisine))</code>.",
     "A join on cuisines in query 2 instead would cut the other cuisines off the card."],
    "challenge/CuisineFilterChallengeTest.java", ["challenge/solution/RestaurantRepository.java", "challenge/solution/HomeScreen.java", "challenge/solution/RestaurantController.java"]) + challenge(2, "Top rated first", "Go deeper", 30,
    "Add <code>sort=rating</code>: best average first, unrated last, ties by name. Any other sort value is <code>400</code>, never SQL.",
    "both tests in <code>TopRatedChallengeTest</code> pass.",
    ["Order in query 1, so page 2 continues page 1: <code>left join Review v … group by r.id, r.name order by avg(v.rating) desc nulls last, r.name, r.id</code>.",
     "Validate <code>sort</code> against a whitelist with <code>@Pattern(regexp = \"name|rating\")</code>."],
    "challenge/TopRatedChallengeTest.java", ["challenge/solution/RestaurantRepository.java", "challenge/solution/HomeScreen.java", "challenge/solution/RestaurantController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>@BatchSize, or a cache?</h2>
<p>Hibernate's <code>@BatchSize(size = 50)</code> on <code>cuisines</code> turns 50 lazy loads into one <code>… where restaurant_id in (…)</code> query, with no change to the service. A cache of ratings would remove query 3. For each: how many queries for a page of 50, what goes stale and when, and what a new developer must know so the N+1 does not come back somewhere else.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, mapping"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Count the old screen's queries in a test: 101.</li>
<li>Page ids only, so the database applies the limit.</li>
<li>Load those restaurants with cuisines through an entity graph.</li>
<li>Ask the database for ratings as a projection, then assemble in page order and compare with the old cards.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "Queries for 50", "Verdict"], [
    ["Page of ids + entity graph + rating projection", "3", '<span class="pill ok">Chosen</span>'],
    ["Lazy loads in a loop", "101", '<span class="pill bad">The trap</span>'],
    ["<code>JOIN FETCH</code> with a page", "1 + ratings, in Hibernate 7.4", '<span class="pill warn">Inner join drops rows; Hibernate 5 paged in memory</span>'],
    ["<code>@BatchSize</code> on the collection", "1 + 1 + ratings", '<span class="pill warn">Good default; hides where queries happen</span>'],
    ["One native SQL query with <code>array_agg</code>", "1", '<span class="pill warn">Fastest; no entities, PostgreSQL-only</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Constraints", "Why"], [
    ["<code>cities</code>", "<code>cities_code_shape</code>", "Lower-case codes only, as the API sends them."],
    ["<code>restaurants</code>", "<code>restaurants_city_fk</code>, <code>restaurants_name_per_city</code>; index <code>(city_code, name, id)</code>", "The index serves the page query's filter and order."],
    ["<code>restaurant_cuisines</code>", "<code>restaurant_cuisines_pk</code>, two foreign keys", "A cuisine once per restaurant."],
    ["<code>reviews</code>", "<code>reviews_rating_range</code> (1 to 5), <code>reviews_restaurant_fk</code>; index on <code>restaurant_id</code>", "The rating query groups by restaurant."]]) + """
""" + code(read(M + "V1__restaurants.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Find N+1 before users do</dt><dd>A query-count assertion in the test of every list endpoint is cheap and catches the next lazy association someone adds.</dd>
<dt>Logs</dt><dd>SQL logging is for a developer machine: it is slow and can log customer data. In production, watch query counts and times with metrics or <code>pg_stat_statements</code>.</dd>
<dt>Deep pages</dt><dd><code>OFFSET</code> gets slower page by page; station 066 replaces it with keyset paging.</dd>
<dt>Ratings at scale</dt><dd>Averaging every review on every launch is fine for thousands of reviews; for millions, keep a running count and sum per restaurant.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is the N+1 query problem?", "One query loads a list; then code touches a lazy association on each item, sending one more query per item. The total grows with the list."),
    ("How do you prove you fixed it?", "Count the statements in a test (Hibernate statistics, a datasource proxy) and assert the number stays the same for different page sizes."),
    ("@EntityGraph or JOIN FETCH?", "Both load an association in the same query. An entity graph is declared on a repository method and uses a left join; JOIN FETCH is written in JPQL and is an inner join unless you write LEFT."),
    ("Why page ids first?", "A fetch join multiplies rows (one per cuisine), so a SQL limit would cut a restaurant's cuisines. Older Hibernate therefore paged in memory; paging ids keeps the limit in the database on any version."),
    ("What is a DTO projection?", "A query that builds plain objects (select new … or an interface) instead of entities: no dirty checking, no lazy associations, only the columns needed."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You counted the queries with the entity graph removed."],
    ["JPA fetching", "An entity graph instead of lazy loops.", "Why JOIN FETCH dropped a restaurant."],
    ["Paging", "The limit runs in SQL.", "What older Hibernate did with a fetch join and a page."],
    ["Projections", "Ratings averaged by the database.", "When a native query is worth it."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This station has no flawed version to review. Use this checklist on any list endpoint:</p>
<ul class="rules">
<li>Which associations does the response touch, and how is each one loaded?</li>
<li>Is there a test that counts the queries for two different page sizes?</li>
<li>Is the page limit applied in SQL? Read the SQL, not the code.</li>
<li>Can a row with an empty collection disappear from the result?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
