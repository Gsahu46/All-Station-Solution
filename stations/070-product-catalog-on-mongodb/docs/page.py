"""Station 070 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 70,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Data MongoDB · MongoDB 8.0 ($jsonSchema, wildcard index, aggregation, transactions on a replica set) · Testcontainers",
    "simulation": "Products, sellers, stock and orders are demo data, not Kartwala's. Nothing is sold; an order is a document in a test.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (MongoDB for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/kartwala/catalog/"
T = "src/test/java/com/kartwala/catalog/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Document", "One record as a nested JSON-like object (BSON).", "A filled-in form, with any extra pages it needs.", "a product"),
    ("Collection", "A set of documents; MongoDB's table.", "A drawer of forms.", "<code>products</code>"),
    ("Schema validation", "Rules the server checks on every write.", "The clerk refusing a form with a blank price.", "the <code>$jsonSchema</code> validator"),
    ("Wildcard index", "One index over every key under a path.", "One card index for every extra page, whatever it asks.", "<code>attributes.$**</code>"),
    ("Aggregation", "A pipeline of steps: match, group, join, sort.", "Sorting the drawer into piles and counting them.", "<code>$group</code>, <code>$lookup</code>"),
    ("Replica set", "Several MongoDB servers holding the same data; needed for transactions.", "A ledger kept in duplicate.", "one node, <code>rs0</code>"),
]
STORY = [
    ("A catalog that changes weekly", "Phones, shoes, and now sarees with fabric and length. Each category brings its own attributes; a document store keeps each product as one document, whatever it carries."),
    ("Then: orders too?", "Someone proposes moving stock and orders to MongoDB as well. An order takes one from stock and writes an order: two documents. A retried request fails halfway, and a phone vanishes from stock with no order for it. Seller names copied into every listing go stale when a seller is renamed."),
    ("The decision", "The catalog fits a document store well. Stock and orders, with rules across documents and frequent joins, stay in PostgreSQL, or must use transactions everywhere."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Choose the store by the shape of the data and the rules between records, not by fashion.</p>

<h2>What are we building?</h2>
<p><code>POST /catalog/products</code> stores a product of any category as one document; <code>GET /catalog/products?category=phones&amp;attr.ram=8GB</code> finds them through an index.</p>

<h2>An everyday analogy</h2>
<p>A shop's catalogue binder: each product is a page, and a saree page simply has different boxes from a phone page. The binder is perfect for that. The till and the stock book are different: one sale must change both, or neither.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>At start</strong>, the app makes sure the collection exists with its validator and indexes.</li>
<li><strong>A new product</strong> is checked in Java, written as a document, and checked again by MongoDB's validator.</li>
<li><strong>A search</strong> becomes equality filters on <code>attributes.&lt;name&gt;</code>, answered by the wildcard index.</li>
<li><strong>Several documents that must change together</strong> need a transaction, on a replica set.</li>
</ol>

<details class="qa check"><summary>Check yourself: a seller is renamed. Their name is copied into 3,000 product documents. What has to happen?</summary><p>All 3,000 copies must be updated, ideally in one transaction; until then, listings show the old name. Or store only the seller's id and look the name up (<code>$lookup</code>) on every read. The trap test shows both.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>Not a migration.</strong> PostgreSQL stays; this is an evaluation with working code.</li>
<li><strong>No sharding or replicas for scale.</strong> One node, a replica set only so transactions work.</li>
<li><strong>No orders API.</strong> Orders appear only in the trap test, to show what goes wrong.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Kartwala</strong> (a fictional marketplace): catalog attributes differ per category and change weekly. The team is evaluating a document database, and must decide what goes in it.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo data: three phones and three shoes, seeded at first start.</p>
<ol class="gwt">
<li><b>Given</b> a saree with fabric and length, a category nobody planned, <b>then</b> <code>201</code>, and it can be searched at once.</li>
<li><b>Given</b> <code>category=phones&amp;attr.ram=8GB</code>, <b>then</b> the two 8GB phones, by SKU.</li>
<li><b>Given</b> a duplicate SKU, <b>then</b> <code>409</code>.</li>
<li><b>Given</b> a negative or fractional price, or a query operator as a value or field name, <b>then</b> <code>400</code>.</li>
<li><b>Given</b> a bad document written with the driver directly, <b>then</b> MongoDB refuses it.</li>
<li><b>Given</b> a transaction where one write fails, <b>then</b> none of its writes remain.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>The collection has a validator: required fields, types and ranges, checked by the server.</li>
<li>SKUs are unique (an index); attribute searches use the wildcard index.</li>
<li>User input never becomes a field name or an operator.</li>
<li>Multi-document changes use a transaction; data that needs them constantly belongs elsewhere.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Model a catalog as documents with Spring Data MongoDB.</li>
<li>Add schema validation and indexes to a \"schemaless\" store.</li>
<li>Use the aggregation pipeline: <code>$group</code> and <code>$lookup</code>.</li>
<li>Decide when a document store fits and when it does not.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its MongoDB, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/catalog/products</code>", "<code>{sku, name, category, sellerId, pricePaise, attributes: {name: text}}</code>; <code>201</code>, Location with the document id."],
    ["<code>GET</code>", "<code>/catalog/products?category=…&amp;attr.&lt;name&gt;=…</code>", "Products matching every filter, at most 50, by SKU."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span> / <span class="pill ok">201</span>', "Results (possibly none) / created"],
    ['<span class="pill warn">400</span>', "A malformed product (price out of range or fractional, a value that is not text, a bad attribute name); a search with neither category nor filter, or a parameter that is not <code>category</code> or <code>attr.&lt;name&gt;</code>"],
    ['<span class="pill warn">409</span>', "The SKU exists"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-a-saree-a-category-nobody-planned", "Case 1: a saree", "<b>Why:</b> a new category with its own attributes, and no schema change."),
    ("02-phones-with-8gb", "Case 2: phones with 8GB", "<b>Why:</b> a category and an attribute filter."),
    ("03-the-same-sku-again", "Case 3: the same SKU again", "<b>Why:</b> the unique index: <code>409</code>."),
    ("04-an-operator-as-a-value", "Case 4: <code>{\"$gt\": \"\"}</code> as a value", "<b>Why:</b> attributes are text: <code>400</code>, never a query operator."),
    ("05-an-operator-as-a-field", "Case 5: <code>attr.$where</code>", "<b>Why:</b> attribute names are checked: <code>400</code>."),
]) + """
<h2>What MongoDB says</h2>
<p class="muted">From <code>docs/capture.sh</code>, in <code>mongosh</code>: the plan for an attribute search (<code>docs/captures/explain-attributes.txt</code>) and the validator refusing a negative price written directly (<code>docs/captures/validator-refuses.txt</code>).</p>
""" + code(read("docs/captures/explain-attributes.txt").rstrip(), "json") + code(read("docs/captures/validator-refuses.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A new category", "Stored and searchable", "<code>aNewCategoryNeedsNoSchemaChange</code>"],
    ["Category and attributes; cross-category; no match", "Equality filters", "<code>searchByCategoryAndAttributes</code>"],
    ["Duplicate SKU", "<code>409</code>", "<code>aDuplicateSkuIs409</code>"],
    ["Negative or fractional price; <code>$where</code> as a name; an operator as a value", "<code>400</code>", "<code>malformedProductsAre400</code>"],
    ["<code>attr.$where</code>, a dotted path, an operator as category, nothing", "<code>400</code>", "<code>queryOperatorsInParametersAreRefused</code>"],
    ["Bad documents written with the driver", "Refused by the validator and the unique index", "<code>theValidatorAndTheUniqueIndexHoldWithoutJava</code>"],
    ["Three inserts, the third invalid, in a transaction", "None remain", "<code>aTransactionMakesSeveralDocumentsAllOrNothing</code>"],
    ["An attribute search", "The wildcard index", "<code>attributeSearchesUseTheWildcardIndex</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Using a document store for data that needs joins and multi-document transactions.</p>
<ul>
<li><strong>Two writes, no transaction.</strong> Placing an order takes one phone from <code>stock</code>, then inserts into <code>orders</code>. A retried request reuses order number ORD-1, the insert fails, and stock is 4 with no order for the missing phone. In a transaction, the same failure leaves stock at 5.</li>
<li><strong>Copies go stale.</strong> Listings carry a copy of the seller's name, the usual document-store habit. After the rename, every listing still says \"Meera Footwear\". The fresh name needs a <code>$lookup</code>, MongoDB's join, on every read.</li>
</ul>
<p>Neither is impossible in MongoDB; both are work you must remember everywhere, while PostgreSQL gives them by default. The catalog has neither problem, which is why it fits.</p>
<p>While building, each fix was undone once: no validator turned 2 tests red; no unique index 2; no wildcard index 1; no attribute-name check 1.</p>
</div>
""" + code(read(T + "DocumentStoreTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "CatalogController.java", dwn("Validates products; turns <code>attr.*</code> parameters into filters, refusing any name that is not plain lower-case.",
        "No user text becomes a field path or an operator.",
        "<code>attr.$where</code> or <code>{\"$gt\": \"\"}</code> reaching the query.")),
    (J + "Catalog.java", dwn("Inserts with <code>MongoTemplate</code>; searches with <code>Criteria</code> equality filters.",
        "A duplicate SKU becomes <code>409</code>; each filter is a value, never parsed.",
        "Queries built from JSON text.")),
    (J + "CatalogSchema.java", dwn("Creates the collection with its <code>$jsonSchema</code> validator and the three indexes, at every start; seeds the demo data once.",
        "MongoDB applies the validator to every writer, not only this app.",
        "\"Schemaless\" meaning \"anything goes\".",
        "<ul><li>Index creation is idempotent: the same name and keys again do nothing.</li><li>The validator is only applied when this app creates the collection; an existing collection needs <code>collMod</code>.</li></ul>")),
    (J + "CatalogProduct.java", "<p>The document as a Java record.</p>"),
    (J + "CatalogApplication.java", "<p>Entry point, and the <code>MongoTransactionManager</code> Spring Boot does not create by itself.</p>"),
    ("src/main/resources/application.yaml", "<p>The MongoDB URI (<code>spring.mongodb.uri</code> in Spring Boot 4) and whole paise only.</p>"),
    ("compose.yaml", "<p>MongoDB 8.0 as a one-node replica set; the healthcheck starts it on first run.</p>"),
]
tree = """stations/070-product-catalog-on-mongodb/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/catalog/
│   ├── CatalogController.java   ├── Catalog.java   ├── CatalogSchema.java
│   ├── CatalogProduct.java   └── CatalogApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/kartwala/catalog/   (see Tests)
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
""" + code("""docker compose up -d --wait  # MongoDB 8.0 on localhost:27017, as replica set rs0
./mvnw spring-boot:run       # the API on http://localhost:8080
./mvnw test                  # all """ + str(N_TESTS) + """ tests; starts its own MongoDB container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d --wait
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Look at the documents and the validator in <code>mongosh</code>:</p>
""" + code("""docker compose exec mongo mongosh kartwala
db.products.find({"attributes.ram": "8GB"}, {sku: 1, attributes: 1})
db.getCollectionInfos({name: "products"})[0].options.validator
db.products.aggregate([{$group: {_id: "$category", products: {$sum: 1}}}])""", "javascript") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>Transaction numbers are only allowed on a replica set member or mongos</code>", "A standalone MongoDB; Testcontainers 2.0's <code>MongoDBContainer</code> is standalone unless asked.", "<code>.withReplicaSet()</code> in tests; <code>--replSet</code> in compose. Found while building this station."],
    ["<code>Invalid bean definition with name 'mongo'</code>", "A bean called <code>mongo</code> next to Spring Boot's MongoClient bean of that name.", "Name your bean something else. Found while building this station."],
    ["<code>Document failed validation</code>", "A write breaking the <code>$jsonSchema</code>.", "Expected; the error's <code>errInfo</code> names the rule."],
    ["<code>E11000 duplicate key error</code>", "A second product with the same SKU.", "Answered <code>409</code> by the app."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the collection behind it.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found (empty)", f"<code>CatalogContractTest</code> ({cnt('CatalogContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>DocumentStoreTrapTest</code> ({cnt('DocumentStoreTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>CatalogDatabaseTest</code> ({cnt('CatalogDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<p>\"Constraints\" here are the collection's validator and unique index; \"rollback\" is a multi-document transaction, on a real replica set.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, MongoDB 8.0 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "DocumentStoreTrapTest.java", "<p>Written first: an order across two collections, and copied names.</p>"),
    (T + "CatalogDatabaseTest.java", "<p>The validator and unique index with the driver, a transaction, the wildcard index, an aggregation.</p>"),
    (T + "CatalogContractTest.java", "<p>Both endpoints through HTTP, including operator injection.</p>"),
    (T + "ApiTest.java", "<p>Shared setup.</p>"),
    (T + "MongoTestConfig.java", "<p>MongoDB 8.0 in Docker as a replica set, via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/kartwala/catalog/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=ProductByIdChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "One product by id", "Beginner-friendly", 20,
    "Add <code>GET /catalog/products/{id}</code>: the product behind the Location header. Not 24 hex digits: <code>400</code>; unknown: <code>404</code>.",
    "both tests in <code>ProductByIdChallengeTest</code> pass.",
    ["<code>ObjectId.isValid(id)</code> before <code>new ObjectId(id)</code>, which throws otherwise.", "<code>mongo.findById</code> returns <code>null</code> when nothing matches."],
    "challenge/ProductByIdChallengeTest.java", ["challenge/solution/Catalog.java", "challenge/solution/CatalogController.java"]) + challenge(2, "Counts per value", "Go deeper", 30,
    "Add <code>GET /catalog/facets?category&amp;facet=ram</code>: the category's products per value of one attribute, with an aggregation.",
    "the test in <code>FacetChallengeTest</code> passes.",
    ["<code>Aggregation.match(…category…and(\"attributes.\" + facet).exists(true))</code>, then <code>Aggregation.group(\"attributes.\" + facet).count()</code>.",
     "Check the facet name with the same pattern as attribute names: it becomes a field path."],
    "challenge/FacetChallengeTest.java", ["challenge/solution/Catalog.java", "challenge/solution/CatalogController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>MongoDB, PostgreSQL, or both?</h2>
<p>For each of these, choose a store and say why: the product catalog, stock levels, orders and payments, reviews, the search index, sellers. If both stores are used, which is the source of truth for what, and how does a product's price reach an order? Compare with station 068, where the same catalog lives in PostgreSQL jsonb.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: collection, validator, indexes"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: an order across two collections, and copied seller names.</li>
<li>Model a product as one document; keep references (seller id) rather than copies.</li>
<li>Give the collection a validator and indexes, created by the app at start.</li>
<li>Refuse operators and field paths from users; use transactions where documents must change together.</li>
</ol>
<h2>When a document store fits</h2>
""" + table(["Fits well", "Fits badly"], [
    ["Records read and written whole, like a product page", "Records that must change together, like stock and orders"],
    ["Fields that differ per record and change often", "Data joined in many ways, like reports across sellers and orders"],
    ["Nested data owned by one record", "Shared data copied into many records, like seller names"],
    ["Scaling reads and writes across servers", "Strict invariants across records, like \"never oversell\""]]) + """
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Catalog in MongoDB, with validator and indexes", "A second database to run.", '<span class="pill ok">Chosen for the catalog</span>'],
    ["Orders and stock in MongoDB too", "Transactions everywhere, or inconsistent stock.", '<span class="pill bad">The trap</span>'],
    ["Catalog in PostgreSQL jsonb (station 068)", "One database; constraints and joins for the rest.", '<span class="pill warn">Often enough</span>'],
    ["Copies of seller data in each product", "Fast reads; stale copies after changes.", '<span class="pill warn">Only with an update plan</span>'],
    ["References plus <code>$lookup</code>", "Always fresh; a join on every read.", '<span class="pill warn">For data that changes</span>']]) + """
<h2>The collection</h2>
""" + table(["Object", "What", "Why"], [
    ["Validator", "<code>$jsonSchema</code>: required fields, types, ranges, patterns", "Rules for every writer."],
    ["<code>products_sku_unique</code>", "Unique index on <code>sku</code>", "One product per SKU."],
    ["<code>products_category_sku</code>", "Index on <code>category, sku</code>", "Category pages, in SKU order."],
    ["<code>products_attributes_wildcard</code>", "Wildcard index on <code>attributes.$**</code>", "Any attribute filter, without an index per key."]]) + """
""" + code(read(J + "CatalogSchema.java"), "java")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Replica sets</dt><dd>Production MongoDB runs as a replica set of at least three members; one node here only enables transactions.</dd>
<dt>Changing the validator</dt><dd>Use <code>collMod</code> with <code>validationLevel: moderate</code> first, so existing documents that break new rules can be fixed before they are enforced.</dd>
<dt>Two databases</dt><dd>Keeping MongoDB and PostgreSQL consistent (a product's price reaching an order) needs an outbox or events; nothing spans both stores' transactions.</dd>
<dt>Licence</dt><dd>MongoDB Community is under the SSPL; check that it suits how the service is offered.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("When would you choose a document database?", "When records are read and written whole, vary in shape, and rarely need joins or rules across records; a product catalog is the classic case."),
    ("Is MongoDB schemaless?", "It does not require a schema, but it supports $jsonSchema validators that the server enforces on writes; a production collection should have one."),
    ("Does MongoDB support transactions?", "Yes, multi-document ACID transactions since 4.0, on replica sets (and sharded clusters since 4.2); they have limits and costs, so designs avoid needing them constantly."),
    ("Embed or reference?", "Embed data owned by the document and read with it; reference data shared by many documents or changed independently, and join with $lookup or a second query."),
    ("What is NoSQL injection?", "User input becoming a query operator or field path, such as {\"$gt\": \"\"} or $where; prevent it by validating types and names and never building queries from JSON text."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the explain in mongosh."],
    ["MongoDB", "Documents, validator, indexes.", "Wildcard index and aggregation."],
    ["Safety", "No operator injection.", "Why a replica set is needed."],
    ["Judgement", "Catalog in, orders out.", "Embed vs reference, argued for one field."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This station has no flawed version to review. Use this checklist when data moves to a document store:</p>
<ul class="rules">
<li>Which writes touch more than one document, and are they in a transaction?</li>
<li>What is copied into documents, and who updates every copy?</li>
<li>Does the collection have a validator and the indexes its queries need?</li>
<li>Can any request value become a field name or an operator?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
