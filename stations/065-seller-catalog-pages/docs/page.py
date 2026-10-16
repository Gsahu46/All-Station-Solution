"""Station 065 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 65,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Data JPA Pageable, Page, Slice · PagedModel · DTO projections · PostgreSQL 17 · Testcontainers",
    "simulation": "Sellers and products are demo data, not Kartwala's. The seller comes from a request header instead of a login.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/kartwala/sellerpages/"
T = "src/test/java/com/kartwala/sellerpages/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]
EXP = {l.split("|")[0].strip(): [c.strip() for c in l.split("|")] for l in read("docs/captures/paging-experiment.txt").splitlines() if l.count("|") == 3 and "rows_shown" not in l}
PRICE_ONLY, WITH_ID, FROM_INDEX = EXP["sorted: price only"], EXP["sorted: price, then id"], EXP["from the index: price only"]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Page", "One slice of a long list, by number and size.", "Page 3 of a catalogue, 20 items a page.", "<code>?page=2&amp;size=20</code>"),
    ("Pageable", "Spring Data's page number, size and sort, built from the query string.", "\"Page 3, 20 per page, cheapest first.\"", "the controller's parameter"),
    ("Page vs Slice", "A Page also counts all rows (for \"page 3 of 100\"); a Slice only knows whether more follow.", "A book's page numbers against a scroll that keeps going.", "<code>Page&lt;ProductCard&gt;</code>; Practice 1"),
    ("Tie", "Two rows with the same value in the sort column.", "Two products at Rs 499.", "200 products per price"),
    ("Stable order", "Every row has exactly one position, every time.", "Sort by price, then by product number.", "<code>…, id</code> appended to every sort"),
    ("Maximum page size", "The largest page the server will build.", "\"At most 100 per page.\"", "<code>max-page-size: 100</code>"),
]
STORY = [
    ("A seller checks their catalog", "Sharma Electronics has 2,000 products, many at the same price. They page through, cheapest first."),
    ("Repeats and gaps", "A product seen on page 3 shows up again on page 7; another never shows at all. Nothing changed in the data: the database was free to order products with the same price any way it liked, and did so differently for each page."),
    ("The fix", "Always end the sort with the product id. Then every product has one place, and each page continues exactly where the last one stopped."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A page is only well defined if the order is. End every sort with a unique column.</p>

<h2>What are we building?</h2>
<p><code>GET /seller/products?page=0&amp;size=20&amp;sort=pricePaise</code>: one page of the seller's own products, with the totals the screen shows.</p>

<h2>An everyday analogy</h2>
<p>A class register sorted by surname. Three students are called Sharma; if the teacher lines them up differently every morning, \"the fifth student\" is a different child each day. Sort by surname, then roll number, and the fifth student is always the same one.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Read page, size and sort</strong> from the query string; a size above 100 becomes 100.</li>
<li><strong>Check the sort</strong> is one the catalog allows; add the id at the end.</li>
<li><strong>Fetch the page</strong> (<code>LIMIT</code>/<code>OFFSET</code>) and count all the seller's products.</li>
<li><strong>Answer</strong> with the rows and the page facts: number, size, total, pages.</li>
</ol>

<details class="qa check"><summary>Check yourself: nothing in the data changes between two page requests. How can a product still appear twice?</summary><p>When many rows tie on the sort value, SQL allows them in any order, and PostgreSQL's choice depends on how many rows the query needs. Page 1 and page 2 are separate queries with different <code>OFFSET</code>s, so the ties can be ordered differently in each.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No login.</strong> The seller is a header; a real app takes it from the session.</li>
<li><strong>No changing data.</strong> Pages over a list that changes while you read are station 066 (keyset paging).</li>
<li><strong>No editing.</strong> Products are read only.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Kartwala</strong> (a fictional marketplace) has sellers with 80,000 products. While paging, items repeated and vanished.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo data: seller 7 has 2,000 products at 10 prices (200 each); seller 8 has 30.</p>
<ol class="gwt">
<li><b>Given</b> no parameters, <b>then</b> 20 products by name, with <code>totalElements</code> 2000 and <code>totalPages</code> 100.</li>
<li><b>Given</b> every page of 20 sorted by price, <b>then</b> every product exactly once.</li>
<li><b>Given</b> <code>size=5000</code>, <b>then</b> 100 products, and the response says the size was 100.</li>
<li><b>Given</b> a page past the end, <b>then</b> an empty page, still with the totals.</li>
<li><b>Given</b> a sort by any other field, or no seller header, <b>then</b> <code>400</code>; an unknown seller <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Every sort ends with <code>id</code>.</li>
<li>Only whitelisted fields can be sorted on, each backed by an index ending in <code>id</code>.</li>
<li>A page never holds more than 100 products.</li>
<li>A seller only ever sees their own products.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Use Spring Data's <code>Pageable</code>, <code>Page</code> and <code>PagedModel</code>.</li>
<li>Explain why a sort on a non-unique column breaks paging, and fix it.</li>
<li>Choose between <code>Page</code> and <code>Slice</code>.</li>
<li>Know what Spring Data does silently: the size cap and annotation defaults.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Parameter", "Form", "Notes"], [
    ["<code>X-Seller-Id</code> header", "<code>7</code>", "demo stand-in for the logged-in seller"],
    ["<code>page</code>", "0, 1, 2, …", "counted from 0"],
    ["<code>size</code>", "1 to 100, default 20", "more than 100 becomes 100"],
    ["<code>sort</code>", "<code>name</code> (default), <code>pricePaise</code>, <code>createdOn</code>; add <code>,desc</code>", "others are <code>400</code>; <code>id</code> is always added last"]]) + """
<p>Response: <code>{content: [{id, name, pricePaise, createdOn}], page: {size, number, totalElements, totalPages}}</code>.</p>
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "A page, possibly empty"],
    ['<span class="pill warn">400</span>', "A sort field not on the list; the seller header missing or not a number"],
    ['<span class="pill warn">404</span>', "No such seller"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-meera-handlooms-first-page", "Case 1: seller 8, three per page", "<b>Why:</b> the page facts next to the rows."),
    ("02-dearest-first-page-two", "Case 2: seller 7, dearest first, page 1", "<b>Why:</b> 200 products tie at the top price; id decides their order."),
    ("03-a-size-of-5000", "Case 3: <code>size=5000</code>", "<b>Why:</b> cut to 100 without an error; <code>page.size</code> tells the client."),
    ("04-sort-by-a-column-not-on-the-list", "Case 4: <code>sort=sellerId</code>", "<b>Why:</b> not on the list: <code>400</code>."),
    ("05-no-such-seller", "Case 5: seller 99", "<b>Why:</b> <code>404</code>."),
]) + """
<h2>The paging experiment</h2>
<p class="muted">From <code>docs/capture.sh</code>: all 100 pages of 20 for seller 7, fetched with each <code>ORDER BY</code>, in <code>psql</code>, once with index scans switched off (PostgreSQL sorts) and once with them on (<code>docs/captures/paging-experiment.txt</code>). The two plans for page 4 come first.</p>
""" + code(read("docs/captures/paging-experiment.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["No parameters", "Page 0 of 20 by name, with totals", "<code>theFirstPageByName</code>"],
    ["200 products at one price", "Ordered by id within the price", "<code>sortedByPriceDearestFirstTiesByIdOnPageTwo</code>"],
    ["<code>size=5000</code>", "100, and the response says so", "<code>aSizeAbove100IsCutTo100AndTheResponseSaysSo</code>"],
    ["Past the last page; another seller", "Empty; only their own products", "<code>aPagePastTheEndIsEmptyAndAnotherSellersProductsNeverShow</code>"],
    ["Unknown seller", "<code>404</code>", "<code>anUnknownSellerIs404</code>"],
    ["Unknown sort, SQL in the sort, no header", "<code>400</code>", "<code>aSortOutsideTheListOrNoSellerIs400</code>"],
    ["Every page by price", "Each product exactly once", "<code>withIdAsTheTieBreakerEveryProductAppearsExactlyOnce</code>"],
    ["Bad rows; a half-done upload", "Refused; rolled back", "<code>ProductDatabaseTest</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Sorting by a non-unique column, so items repeat or vanish between pages.</p>
<p>In the experiment above, when PostgreSQL sorted the rows, price alone showed """ + PRICE_ONLY[1] + """ rows but only """ + PRICE_ONLY[2] + """ different products: """ + PRICE_ONLY[3] + """ were never shown. With <code>, id</code> added: """ + WITH_ID[2] + """ different products, """ + WITH_ID[3] + """ missing.</p>
<p>Why: SQL leaves the order of tied rows undefined. When PostgreSQL sorts for <code>ORDER BY … LIMIT</code>, it keeps only the top rows it needs in a heap (\"top-N heapsort\" in the plan), and which tied rows make the top 20 depends on <code>LIMIT</code> plus <code>OFFSET</code>, so it differs per page. The data never changed.</p>
<p><strong>The trap within the trap.</strong> With fresh statistics, PostgreSQL read the <code>(seller_id, price_paise, id)</code> index instead, and price alone showed """ + FROM_INDEX[2] + """ different products, """ + FROM_INDEX[3] + """ missing: correct by luck of the plan. Found while building: a run without statistics lost products, a run with them did not. The trap test therefore switches index scans off inside its transaction, so the sort plan is used every time, and the fix must hold under any plan.</p>
<p>While building, each fix was undone once: no tie-breaker turned 2 tests red; no sort whitelist 1; no seller check 2; no maximum page size 1; <code>@PageableDefault</code> without a size 2.</p>
</div>
""" + code(read(T + "UnstableSortTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SellerProductController.java", dwn("Takes the seller and a <code>Pageable</code>; answers a <code>PagedModel</code>.",
        "Spring Data parses <code>page</code>, <code>size</code> and <code>sort</code>, and caps the size.",
        "Hand-parsed paging, and a <code>PageImpl</code> serialised as whatever its internals are.",
        "<ul><li><code>@PageableDefault</code> has its own size, 10, which beats the configured default: the size is written out. Found while building this station.</li></ul>")),
    (J + "SellerCatalog.java", dwn("Checks the sort against the whitelist and the seller, then adds <code>id</code> to the sort.",
        "One place where every page query gets its tie-breaker.",
        "Repeats and gaps; sorting on any field a caller names.")),
    (J + "ProductRepository.java", dwn("A derived query returning a <code>Page</code> of projections.",
        "Spring Data writes the page query and the count query.",
        "Two hand-written queries that drift apart.")),
    (J + "ProductCard.java", "<p>The row as the catalog shows it: a DTO projection.</p>"),
    (J + "Product.java", "<p>The entity behind the projection.</p>"),
    (J + "Seller.java", "<p>A seller.</p>"),
    (J + "SellerRepository.java", "<p>\"Does this seller exist\".</p>"),
    ("src/main/resources/application.yaml", dwn("The page size cap and the JSON shape of pages.",
        "<code>max-page-size</code> protects the database; <code>via-dto</code> gives a stable response shape.",
        "<code>size=1000000</code> reading a whole catalog.")),
    (M + "V1__products.sql", dwn("Tables, named constraints and one index per sort, each ending in <code>id</code>.",
        "The page query reads the index in order and stops after the page.",
        "Sorting all of a seller's products for every page.")),
    (M + "V2__demo_products.sql", "<p>Seller 7: 2,000 products at 10 prices. Seller 8: 30 sarees.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "SellerPagesApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/065-seller-catalog-pages/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/sellerpages/
│   ├── SellerProductController.java   ├── SellerCatalog.java   ├── ProductRepository.java   ├── ProductCard.java
│   ├── Product.java   ├── Seller.java   ├── SellerRepository.java   └── SellerPagesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__products.sql, V2__demo_products.sql
├── src/test/java/com/kartwala/sellerpages/   (see Tests)
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
<p>Run the same page twice with different limits in <code>psql</code> and compare the tied rows:</p>
""" + code("""docker compose exec postgres psql -U kartwala -d kartwala
SELECT id FROM products WHERE seller_id = 7 ORDER BY price_paise LIMIT 5 OFFSET 20;
SELECT id FROM products WHERE seller_id = 7 ORDER BY price_paise LIMIT 25;   -- are rows 21 to 25 the same five?
SELECT id FROM products WHERE seller_id = 7 ORDER BY price_paise, id LIMIT 5 OFFSET 20;""", "sql") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Pages of 10 although the default is 20", "<code>@PageableDefault</code> without <code>size</code> uses 10.", "Write the size in the annotation."],
    ["<code>size=500</code> returns 100 rows", "<code>max-page-size</code> caps it silently.", "Expected; read <code>page.size</code> in the response."],
    ["A warning about serialising <code>PageImpl</code>", "Returning a <code>Page</code> directly from a controller.", "Return <code>PagedModel</code>, or set <code>serialization-mode: via-dto</code>."],
    ["<code>page=-1</code> gives page 0", "Spring Data treats a negative page as 0.", "Expected; validate yourself if it must be a 400."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>SellerPageContractTest</code> ({cnt('SellerPageContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>UnstableSortTrapTest</code> ({cnt('UnstableSortTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>ProductDatabaseTest</code> ({cnt('ProductDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Hibernate 7.4, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "UnstableSortTrapTest.java", "<p>Written first: all 100 pages both ways, and a Page against a Slice, queries counted.</p>"),
    (T + "ProductDatabaseTest.java", "<p>Named constraints and a rolled-back upload.</p>"),
    (T + "SellerPageContractTest.java", "<p>The endpoint through HTTP.</p>"),
    (T + "OldProducts.java", "<p>The same rows as a Slice, for the comparison.</p>"),
    (T + "ApiTest.java", "<p>Shared setup and the query counter.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/kartwala/sellerpages/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=InfiniteScrollChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "A feed for endless scrolling", "Beginner-friendly", 25,
    "Add <code>GET /seller/products/feed</code>: <code>{content, number, size, hasNext}</code>, no totals, no count query, same sort rules.",
    "both tests in <code>InfiniteScrollChallengeTest</code> pass.",
    ["A repository method returning <code>Slice</code> fetches one extra row to know about <code>hasNext</code>.",
     "Move the sort checks into one private method both endpoints use."],
    "challenge/InfiniteScrollChallengeTest.java", ["challenge/solution/SellerProductController.java", "challenge/solution/SellerCatalog.java", "challenge/solution/ProductRepository.java"]) + challenge(2, "Back to the right page", "Go deeper", 30,
    "Add <code>GET /seller/products/{id}/page?size&amp;sort=pricePaise</code>: which page that product is on, so \"edit, then back\" returns there.",
    "both tests in <code>WhichPageChallengeTest</code> pass.",
    ["Count the rows before it in the same stable order: <code>price &lt; p OR (price = p AND id &lt; id)</code>; for descending, flip the price comparison.",
     "The page is that count divided by the size."],
    "challenge/WhichPageChallengeTest.java", ["challenge/solution/SellerCatalog.java", "challenge/solution/ProductRepository.java", "challenge/solution/SellerProductController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>\"Page 3 of 4,000\" on 80,000 products</h2>
<p>Every Page runs a <code>count(*)</code> over the seller's products. Compare: keeping the exact count (and how it grows with the catalog), PostgreSQL's estimate from <code>EXPLAIN</code> or <code>pg_class.reltuples</code>, a count cached per seller and updated on change, and a Slice that shows \"more\" instead of a total. What does the screen really need?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, indexes"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: every page, sorted by price only.</li>
<li>Append <code>id</code> to every sort in one place.</li>
<li>Whitelist sort fields, each with an index ending in <code>id</code>.</li>
<li>Cap the page size, and return <code>PagedModel</code> for a stable JSON shape.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Pageable + whitelist + id tie-breaker + Page", "A count query per page.", '<span class="pill ok">Chosen</span>'],
    ["Sort by the requested column only", "Repeats and gaps.", '<span class="pill bad">The trap</span>'],
    ["Slice instead of Page", "No totals; one query.", '<span class="pill warn">For feeds (Practice 1)</span>'],
    ["Keyset (seek) paging", "No page numbers; fast at any depth; stable under inserts.", '<span class="pill warn">Station 066</span>'],
    ["Fetch everything, page in Java", "Reads the whole catalog per page.", '<span class="pill bad">Never</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>products_name_per_seller</code>", "UNIQUE (seller_id, name); also the index for the name sort", "Names are unique per seller, so this sort has no ties."],
    ["<code>products_seller_price</code>", "(seller_id, price_paise, id)", "The price sort, ties included."],
    ["<code>products_seller_created</code>", "(seller_id, created_on, id)", "The date sort."],
    ["<code>products_price_range</code>, <code>products_name_not_blank</code>, <code>products_seller_fk</code>", "CHECKs and a foreign key", "No impossible rows."]]) + """
""" + code(read(M + "V1__products.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Deep pages</dt><dd><code>OFFSET 79000</code> still reads 79,000 index entries before the page. Fine for sellers who page a little; for deep or endless paging use keyset (station 066).</dd>
<dt>The count</dt><dd><code>count(*)</code> for 80,000 rows on every page adds up. Cache it, estimate it, or use a Slice where the total is not needed.</dd>
<dt>Clients</dt><dd>Clients must read <code>page.size</code> from the response, not assume the size they asked for was used.</dd>
<dt>Changing data</dt><dd>An insert or delete between two requests still shifts every later page by one. A stable order fixes ties, not that.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why do items repeat or vanish between pages?", "Rows that tie on the sort value have no defined order; each page is a separate query, and the database may order the ties differently each time."),
    ("How do you make paging stable?", "End every sort with a unique column, usually the id, and index the sort columns plus the id."),
    ("Page or Slice?", "A Page runs a count to know the total and the number of pages; a Slice fetches one extra row to know whether more follow, and nothing else."),
    ("What does Spring Data do with size=5000?", "Caps it at max-page-size (2000 by default; 100 here) without an error; the response's page size shows what was used."),
    ("Why not return a Page from a controller?", "PageImpl's JSON is not a stable contract; PagedModel (or serialization-mode via-dto) gives a fixed {content, page} shape."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the psql experiment yourself."],
    ["Paging", "Id as the tie-breaker.", "Why top-N heapsort makes ties move."],
    ["Spring Data", "Pageable, Page, PagedModel.", "The silent size cap and the annotation default."],
    ["Cost", "Knows a Page counts.", "When a Slice or keyset is better."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This station has no flawed version to review. Use this checklist on any paged endpoint:</p>
<ul class="rules">
<li>Does every sort end with a unique column?</li>
<li>Is there a maximum page size, and does the client learn the size used?</li>
<li>Is each sortable field on a whitelist and in an index?</li>
<li>Does the screen need the total, or would a Slice do?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
