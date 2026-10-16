"""Station 068 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 68,
    "stack": "Spring Boot 4.1.1 · Java 25 · JdbcClient · PostgreSQL 17 jsonb · containment (@>) · GIN jsonb_path_ops · rules as data · Testcontainers",
    "simulation": "Sellers, categories and products are demo data (60,006 products), not Kartwala's. Nothing is sold.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/kartwala/attributes/"
T = "src/test/java/com/kartwala/attributes/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Attribute", "A property that only some products have.", "RAM for a phone, size for a shoe.", "<code>attributes</code>"),
    ("jsonb", "PostgreSQL's binary JSON type: stored parsed, queryable, indexable.", "A labelled box of small notes.", "the <code>attributes</code> column"),
    ("Containment", "\"The document includes all these key-value pairs.\"", "\"Has RAM 8GB and storage 256GB.\"", "<code>attributes @&gt; '{…}'</code>"),
    ("GIN index", "An index of the keys and values inside each document.", "A card index of every note in every box.", "<code>products_attributes</code>"),
    ("Rules as data", "The allowed attributes of a category live in a table, not in code.", "A form template per product type.", "<code>attribute_definitions</code>"),
    ("Column", "A field every row has, with a type, a check and joins.", "The printed boxes on every form.", "<code>sku</code>, <code>price_paise</code>, <code>seller_id</code>"),
]
STORY = [
    ("140 columns", "Phones need RAM and storage, shoes need size and colour, sarees need fabric. Each new category added columns that are empty for every other product."),
    ("Everything in JSON", "The first fix put the whole product in one jsonb column. A seller typed \"free\" as the price, and every customer's price filter failed. Duplicate SKUs and unknown sellers got in too."),
    ("The fix", "Columns for what every product has and the rules it needs; jsonb only for what differs per category, checked against that category's rules."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Flexible data still needs rules. Keep the rules close to the data.</p>

<h2>What are we building?</h2>
<p><code>POST /products</code> adds a product with its category's attributes, checked; <code>GET /products?attr.ram=8GB</code> finds products by any mix of attributes, through an index.</p>

<h2>An everyday analogy</h2>
<p>A registration form: printed boxes everyone fills (name, price, seller), and a page of extra questions that depends on what you register: a phone asks for RAM, a shoe for size. The clerk checks the extra page against that type's list.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Check the printed boxes</strong>: SKU, name, price range, seller.</li>
<li><strong>Load the category's rules</strong> and check the attributes: known names, allowed values, nothing required missing.</li>
<li><strong>Store</strong> the fixed fields in columns, the attributes as one jsonb object.</li>
<li><strong>Search</strong> with \"the attributes contain these pairs\", answered by the GIN index.</li>
</ol>

<details class="qa check"><summary>Check yourself: should \"brand\" be a column or an attribute?</summary><p>If every product has a brand, people filter and sort by it, and brands are their own table you join to, it is a column with a foreign key. If only some categories have it and it is just shown, an attribute is fine. The test is the one in this station: does it need a constraint or a join?</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No admin screen for rules.</strong> Rules are rows; Practice 1 reads them.</li>
<li><strong>No numeric ranges on attributes.</strong> Values are text; \"RAM at least 8GB\" needs typed attributes.</li>
<li><strong>No document database.</strong> That is station 070.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Kartwala</strong> (a fictional marketplace) has a products table with 140 nullable columns, one set per category.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo data: phones need ram and storage (colour optional); shoes need size and colour (material optional).</p>
<ol class="gwt">
<li><b>Given</b> a phone with ram, storage and colour, <b>then</b> <code>201</code> with the attributes stored.</li>
<li><b>Given</b> a shoe of size 13 with ram and no colour, <b>then</b> <code>422</code> naming each problem.</li>
<li><b>Given</b> an unknown category or seller, <b>then</b> <code>422</code>; a duplicate SKU, <code>409</code>.</li>
<li><b>Given</b> <code>attr.ram=8GB&amp;attr.storage=256GB</code>, <b>then</b> only products with both.</li>
<li><b>Given</b> an attribute no category has (or not this category), <b>then</b> <code>400</code>.</li>
<li><b>Given</b> any search, <b>then</b> the GIN index is used.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Price, seller, category and SKU are columns with constraints.</li>
<li>Attributes are a jsonb <em>object</em>, checked against the category's rules before saving.</li>
<li>A new category or attribute is a row in <code>attribute_definitions</code>, not a release.</li>
<li>Searches use containment, which the GIN index answers.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Store and query jsonb from Java.</li>
<li>Index jsonb with GIN and know which operators use it.</li>
<li>Validate per-category attributes from data.</li>
<li>Decide what is a column and what is an attribute.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/products</code>", "<code>{sku, name, category, sellerId, pricePaise, attributes: {name: value}}</code>; <code>201</code> with the product."],
    ["<code>GET</code>", "<code>/products?category=…&amp;attr.&lt;name&gt;=&lt;value&gt;</code>", "Products whose attributes include every pair; at most 50."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span> / <span class="pill ok">201</span>', "Results / created"],
    ['<span class="pill warn">400</span>', "A malformed body (fractional price, empty value, a bad attribute name, attributes not an object); a search with no or more than 10 filters, an unknown attribute or category, or another parameter"],
    ['<span class="pill warn">409</span>', "The SKU exists"],
    ['<span class="pill warn">422</span>', "Attributes that break the category's rules; an unknown category or seller"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-a-new-phone", "Case 1: a phone", "<b>Why:</b> the attributes fit the phone rules; the SKU is upper-cased."),
    ("02-a-shoe-that-breaks-the-rules", "Case 2: a shoe that breaks three rules", "<b>Why:</b> every problem at once, by attribute."),
    ("03-phones-with-8gb-and-256gb", "Case 3: 8GB and 256GB phones", "<b>Why:</b> both pairs must be contained."),
    ("04-size-9-leather", "Case 4: size 9, leather, any category", "<b>Why:</b> attributes search across categories that share names."),
    ("05-ram-on-a-shoe", "Case 5: shoes with 8GB RAM", "<b>Why:</b> <code>400</code>: shoes have no ram attribute."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A valid phone", "<code>201</code>, stored as sent", "<code>aPhoneWithItsOwnAttributesIsCreated</code>"],
    ["Unknown, not-allowed and missing attributes", "<code>422</code> listing each", "<code>attributesAreCheckedAgainstTheCategorysRules</code>"],
    ["Unknown category or seller; duplicate SKU", "<code>422</code>; <code>409</code>", "<code>unknownCategorySellerOrADuplicateSku</code>"],
    ["Fractional price, empty value, bad name, an array", "<code>400</code>", "<code>malformedBodiesAre400</code>"],
    ["Two filters; a cross-category filter; no match", "Containment", "<code>searchByAnyMixOfAttributes</code>"],
    ["A filter no category has", "<code>400</code>", "<code>searchingForSomethingNoCategoryHasIs400</code>"],
    ["An array as attributes; a bad rule; a half upload", "Refused; rolled back", "<code>ProductDatabaseTest</code>"],
    ["Duplicate keys in the JSON", "The last one wins", "<code>jsonbStoresTheDocumentNormalised</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Putting everything in jsonb, including fields that need constraints and joins.</p>
<p>The test builds the old table: one <code>data</code> column per product, price and seller inside. Then:</p>
<ul>
<li><strong>Anything gets in.</strong> A second <code>PH-NOVA-8-128</code>, a price of <code>\"free\"</code>, seller 999, RAM <code>\"lots\"</code>: all accepted. There is nothing to attach a constraint to.</li>
<li><strong>One bad row breaks everyone.</strong> <code>(data->>'price')::int &lt; 200000</code> worked, until the \"free\" row: then it fails for every customer with \"invalid input syntax for type integer: \"free\"\".</li>
<li><strong>The real table refuses the same rows</strong>: <code>products_sku_unique</code>, <code>products_price_range</code>, <code>products_seller_fk</code>.</li>
<li><strong>The index only helps the right operator.</strong> <code>attributes @&gt; '{\"ram\": \"12GB\"}'</code> uses the GIN index; <code>attributes->>'ram' = '12GB'</code> reads every row.</li>
</ul>
<p>While building, each fix was undone once: without the allowed-values check, the required check, the search's name check, the GIN index, or the \"must be an object\" CHECK, 1 test turned red each.</p>
</div>
""" + code(read("docs/captures/explain-containment.txt").rstrip(), "text") + code(read("docs/captures/explain-arrow.txt").rstrip(), "text") + code(read(T + "EverythingInJsonbTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "ProductController.java", dwn("Validates the body; turns <code>attr.*</code> parameters into the wanted pairs.",
        "Every value is checked for shape and size before the database.",
        "A 10 MB attribute value, or an attribute name with SQL in it.")),
    (J + "ProductCatalog.java", dwn("Checks attributes against the rules, inserts with <code>CAST(? AS jsonb)</code>, searches with <code>@&gt;</code>.",
        "One containment query for any number of filters, through one index.",
        "A <code>-&gt;&gt;</code> comparison per filter, and no index.",
        "<ul><li>The wanted pairs are written as a JSON object by Jackson and bound as one parameter: no JSON is built by string concatenation.</li></ul>")),
    (J + "AttributeRules.java", dwn("Reads a category's rules and lists every problem with a set of attributes.",
        "Rules are rows, so a new category needs no code.",
        "Attributes nobody can search or display consistently.")),
    (M + "V1__products.sql", dwn("Columns with constraints, jsonb with a shape check, the GIN index, and the rules table.",
        "<code>jsonb_path_ops</code> is smaller and faster for <code>@&gt;</code>, the one question asked.",
        "A table that accepts anything.")),
    (M + "V2__demo_products.sql", "<p>Rules for phones and shoes, 6 products by hand and 60,000 generated.</p>"),
    ("src/main/resources/application.yaml", "<p>Whole paise only.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "AttributesApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/068-flexible-product-attributes-with-jsonb/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/attributes/
│   ├── ProductController.java   ├── ProductCatalog.java   ├── AttributeRules.java   └── AttributesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__products.sql, V2__demo_products.sql
├── src/test/java/com/kartwala/attributes/   (see Tests)
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
<p>See how jsonb stores what you send:</p>
""" + code("""docker compose exec postgres psql -U kartwala -d kartwala
SELECT '{"size": "8", "colour": "Red", "colour": "Blue"}'::jsonb;    -- keys reordered, the last duplicate wins
SELECT '{"ram": "8GB", "storage": "128GB"}'::jsonb @> '{"ram": "8GB"}';
SELECT attributes->>'ram', count(*) FROM products WHERE category_code = 'phones' GROUP BY 1;""", "sql") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>Not allowed to mix named and traditional ? placeholders</code>", "The jsonb operators <code>?</code>, <code>?|</code>, <code>?&amp;</code> look like JDBC placeholders.", "Use <code>jsonb_exists(…)</code> or <code>-&gt;&gt; … IS NOT NULL</code>. Found while building this station."],
    ["<code>column \"attributes\" is of type jsonb but expression is of type character varying</code>", "A JSON string bound as text.", "<code>CAST(? AS jsonb)</code>, as here."],
    ["A search that ignores the GIN index", "<code>-&gt;&gt;</code> comparisons; <code>jsonb_path_ops</code> only supports <code>@&gt;</code> (and jsonpath).", "Use containment, or an expression index for one hot key."],
    ["<code>invalid input syntax for type integer</code>", "A cast of a jsonb value that is not a number.", "Fields you compute with belong in typed columns."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found (empty)", f"<code>ProductContractTest</code> ({cnt('ProductContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>EverythingInJsonbTrapTest</code> ({cnt('EverythingInJsonbTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>ProductDatabaseTest</code> ({cnt('ProductDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "EverythingInJsonbTrapTest.java", "<p>Written first: the old one-column table, its failures, and which operator the index helps.</p>"),
    (T + "ProductDatabaseTest.java", "<p>Named constraints, a rolled-back upload, and how jsonb normalises.</p>"),
    (T + "ProductContractTest.java", "<p>Both endpoints through HTTP.</p>"),
    (T + "ApiTest.java", "<p>Shared setup and the plan reader.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/kartwala/attributes/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=AttributeFormChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "The seller's form", "Beginner-friendly", 20,
    "Add <code>GET /categories/{code}/attributes</code>: the category's rules, by name, so a form can be built from data.",
    "the test in <code>AttributeFormChallengeTest</code> passes.",
    ["<code>AttributeRules.of</code> already reads them.", "An empty result means the category does not exist: <code>404</code>."],
    "challenge/AttributeFormChallengeTest.java", ["challenge/solution/ProductCatalog.java", "challenge/solution/ProductController.java"]) + challenge(2, "Counts per value", "Go deeper", 30,
    "Add <code>GET /products/facets?category&amp;facet=ram&amp;attr.*</code>: products per value of one attribute, among those matching the other filters.",
    "the test in <code>AttributeFacetChallengeTest</code> passes.",
    ["<code>GROUP BY attributes-&gt;&gt;:facet</code>, filtered with the same containment as the search.",
     "Do not write <code>attributes ? :facet</code>: JDBC reads that <code>?</code> as a placeholder. Found while building this station."],
    "challenge/AttributeFacetChallengeTest.java", ["challenge/solution/ProductCatalog.java", "challenge/solution/ProductController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Promote an attribute to a column</h2>
<p>Product wants \"brand\" on every product, filterable and sortable, with a brand page that lists the brand's products and a logo from a <code>brands</code> table. Write the migration that moves <code>attributes-&gt;&gt;'brand'</code> into a <code>brand_id</code> column: adding it, backfilling in batches, cleaning values that match no brand, adding the foreign key <code>NOT VALID</code> then validating it, and removing the key from the jsonb. What does the API look like during the change?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, indexes"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the all-jsonb table and what goes wrong with it.</li>
<li>Split fields: columns for what every product has and needs rules or joins, jsonb for the rest.</li>
<li>Put each category's rules in a table, and check attributes against them before saving.</li>
<li>Search by containment, with a GIN index built for it.</li>
</ol>
<h2>Column or attribute?</h2>
""" + table(["Question", "Yes → column", "No → attribute"], [
    ["Does every product have it?", "price, seller, SKU", "RAM, size"],
    ["Does it need a constraint?", "price range, unique SKU", "free text like colour"],
    ["Is it joined to another table?", "seller, category", "storage size"],
    ["Is it summed, sorted or compared as a number?", "price", "a size shown as text"]]) + """
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Columns for common fields + jsonb attributes + rules table", "Validation in the app; text values.", '<span class="pill ok">Chosen</span>'],
    ["One wide table with a column per attribute", "Hundreds of nullable columns; a migration per category.", '<span class="pill bad">The starting point</span>'],
    ["Everything in jsonb", "No constraints, no joins, fragile casts.", '<span class="pill bad">The trap</span>'],
    ["Entity-attribute-value rows (product_id, name, value)", "Flexible; every filter is a self-join; no types.", '<span class="pill warn">Hard to query</span>'],
    ["A table per category", "Typed and constrained; cross-category search is a UNION.", '<span class="pill warn">Few, stable categories</span>'],
    ["A document database", "Flexible documents; joins and transactions are harder.", '<span class="pill warn">Station 070</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>products_sku_unique</code>, <code>products_price_range</code>, <code>products_seller_fk</code>, <code>products_category_fk</code>", "Constraints on columns", "The rules the old table could not hold."],
    ["<code>products_attributes_object</code>", "CHECK <code>jsonb_typeof(attributes) = 'object'</code>", "No arrays or strings where an object belongs."],
    ["<code>products_attributes</code>", "GIN <code>(attributes jsonb_path_ops)</code>", "Containment searches."],
    ["<code>attribute_definitions</code>", "PK (category, name), name shape CHECK", "The rules, as data."]]) + """
""" + code(read(M + "V1__products.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Changing rules</dt><dd>A new required attribute applies to new products only; existing rows do not change. Decide whether to backfill, or to require it only on edit.</dd>
<dt>Typos in values</dt><dd>Free-text attributes drift (\"Blue\", \"blue\", \"Navy\"). Use allowed lists wherever people filter.</dd>
<dt>Index size</dt><dd>A GIN index covers every key and value; watch its size and update cost on large, write-heavy tables.</dd>
<dt>Wide documents</dt><dd>jsonb values over about 2 kB are compressed and stored out of line (TOAST); keep attributes small.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("json or jsonb?", "jsonb: stored parsed, so it can be indexed and queried efficiently; json keeps the exact text, including key order and duplicates."),
    ("Which jsonb queries can a GIN index answer?", "With jsonb_ops: containment (@>), key existence (?, ?|, ?&) and jsonpath; with jsonb_path_ops: containment and jsonpath only, with a smaller index."),
    ("When should a field be a column instead of jsonb?", "When every row has it, it needs a constraint, it is joined, or it is computed with; jsonb cannot carry those rules."),
    ("How do you validate jsonb?", "In the app, against rules (here a table per category); in the database, at least its shape with CHECK constraints."),
    ("What is the risk of casting a jsonb value in a query?", "One row with an unexpected value makes the cast fail and the whole query fail for every user."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You read both saved plans."],
    ["jsonb", "Stored, searched with @>.", "Knows what jsonb_path_ops gives up."],
    ["Rules", "Attributes checked per category.", "Rules as data, not code."],
    ["Design", "Price, seller, SKU as columns.", "Can plan promoting an attribute."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This station has no flawed version to review. Use this checklist on any jsonb column:</p>
<ul class="rules">
<li>Is anything in the jsonb that needs a constraint, a join or arithmetic?</li>
<li>Is the document checked before it is saved, and its shape checked by the database?</li>
<li>Do searches use operators the index supports?</li>
<li>Is any JSON built by string concatenation?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
