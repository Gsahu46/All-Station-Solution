"""Station 054 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 54,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Data JPA (Hibernate 7) · @PrePersist / @PreUpdate · soft delete · PostgreSQL 17 (ON DELETE RESTRICT, partial unique index) · Flyway · Testcontainers",
    "simulation": "Sellers, products and the past order are demo data, not Kartwala's. The seller is named in a header because this station has no login.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/kartwala/catalog/"
T = "src/test/java/com/kartwala/catalog/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Hard delete", "Removing the row from the table.", "Tearing a page out of the register.", "What the old DELETE did"),
    ("Soft delete (archive)", "Marking the row as gone, and keeping it.", "Striking a line through the page.", "<code>archived_at</code>"),
    ("Foreign key", "A column that must point at an existing row elsewhere.", "An order slip naming a product from the catalogue.", "<code>order_lines.product_id</code>"),
    ("ON DELETE RESTRICT", "Refuse to delete a row that others still point at.", "You cannot tear out a page someone else refers to.", "<code>order_lines_product_fk</code>"),
    ("ON DELETE CASCADE", "Delete the rows that point at it too.", "Tearing out every order slip that names the product.", "The old schema"),
    ("Entity callback", "A method JPA calls just before it saves a row.", "A stamp the clerk applies to every form, every time.", "<code>@PrePersist</code>, <code>@PreUpdate</code>"),
]
STORY = [
    ("Delete means delete", "A Kartwala seller deleted \"Assam tea, 500 g\" from their catalogue. The database deleted the product row."),
    ("The order history moved", "The order lines' foreign key had ON DELETE CASCADE, added so deletes would not fail. Order KW-1001, paid ₹897, now showed one line and ₹199. Refund disputes had nothing to check against."),
    ("The fix", "\"Delete\" archives the product: it leaves the shop and stays for every order. The database refuses a real delete while any order line points at the product."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Rows that history points at are not yours to delete. Archive them, and let the database refuse the rest.</p>

<h2>What are we building?</h2>
<p>A seller "deletes" a product (<code>DELETE /seller/products/{id}</code>), and lists their products (<code>GET /seller/products</code>), with or without the archived ones (<code>?includeArchived=true</code>). Past orders keep every line.</p>

<h2>An everyday analogy</h2>
<p>A shop's price list and its sales receipts. When the shop stops selling a tea, it crosses it off the price list. It does not go back and cut that tea out of last month's receipts.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>The seller asks</strong> to delete product 1.</li>
<li><strong>The service finds it</strong> among this seller's products (anyone else's is "not found").</li>
<li><strong>It sets</strong> <code>archived_at</code>; JPA's <code>@PreUpdate</code> moves <code>updated_at</code>.</li>
<li><strong>The shop's list</strong> hides it; the order history still joins to it.</li>
</ol>

<details class="qa check"><summary>Check yourself: with soft delete, why keep ON DELETE RESTRICT at all?</summary><p>Because the next person may write a script, an admin tool or a migration that does a real <code>DELETE</code>. RESTRICT makes the database refuse it while orders point at the row, whoever wrote the code.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No login.</strong> The seller is named in a header.</li>
<li><strong>No restore or purge.</strong> Those are the challenges.</li>
<li><strong>No creating products over HTTP.</strong> The demo catalogue is loaded by a migration.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Kartwala</strong> (a fictional marketplace) lets sellers remove products. Removing one broke the order history that referenced it.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> seller 1 deletes Assam tea, <b>then</b> <code>204</code>; it leaves the default list and shows with <code>includeArchived=true</code>, marked archived.</li>
<li><b>Given</b> order KW-1001 had Assam tea, <b>then</b> both its lines and their product names are still there.</li>
<li><b>Given</b> a real <code>DELETE</code> on the products table, <b>then</b> the database refuses it while order lines point at the product.</li>
<li><b>Given</b> the same delete twice, <b>then</b> <code>204</code> both times, and the first archive date and update time stay.</li>
<li><b>Given</b> another seller's or an unknown product, <b>then</b> <code>404</code>; no seller header, or a bad parameter, <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Products are archived, never deleted, while orders reference them; the database enforces it.</li>
<li>Every row has <code>created_at</code> and <code>updated_at</code>, set by JPA callbacks, checked by the database.</li>
<li>A product name is unique per seller among products on sale only.</li>
<li>Money in integer paise.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Implement soft delete, and know what it costs.</li>
<li>Choose <code>ON DELETE</code> behaviour for each foreign key on purpose.</li>
<li>Stamp timestamps with <code>@PrePersist</code> and <code>@PreUpdate</code>.</li>
<li>Write a partial unique index for "unique among active rows".</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>DELETE</code>", "<code>/seller/products/{id}</code>", "Archive one of your products. Header <code>X-Seller-Id</code>."],
    ["<code>GET</code>", "<code>/seller/products?includeArchived=false</code>", "Your products, on sale only by default. Header <code>X-Seller-Id</code>."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">204</span>', "Archived (or already archived: nothing changes)"],
    ['<span class="pill ok">200</span>', "The list"],
    ['<span class="pill warn">400</span>', "No <code>X-Seller-Id</code>, or one that is not a number; <code>includeArchived</code> not true or false"],
    ['<span class="pill warn">404</span>', "No such product among your products"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against one fresh database. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-chaiwala-lists-its-products", "Case 1: Chaiwala Traders lists its products", "<b>Why:</b> two products on sale."),
    ("02-it-deletes-assam-tea", "Case 2: it deletes Assam tea", "<b>Why:</b> archived: <code>204</code>."),
    ("03-the-list-now", "Case 3: the list now", "<b>Why:</b> only the chai mix is on sale."),
    ("04-with-archived-products", "Case 4: with archived products", "<b>Why:</b> Assam tea is there, archived, with its new <code>updatedAt</code>."),
    ("05-another-sellers-product", "Case 5: Chaiwala deletes product 3", "<b>Why:</b> another seller's product is not found: <code>404</code>."),
    ("06-no-seller-header", "Case 6: no X-Seller-Id", "<b>Why:</b> <code>400</code>."),
]) + """
<h2>The order history, and a real DELETE</h2>
<p class="muted">Through psql, after the requests above (<code>docs/captures/order-history.txt</code>): KW-1001 still has both lines, and a real <code>DELETE</code> is refused.</p>
""" + code(read("docs/captures/order-history.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Archive, then list both ways", "Hidden by default; shown archived on request", "<code>anArchivedProductLeavesTheDefaultList</code>"],
    ["Archive twice", "<code>204</code>; dates unchanged", "<code>archivingStampsUpdatedAtAndAgainChangesNothing</code>"],
    ["Another seller's, or unknown", "<code>404</code>", "<code>anotherSellersProductIsNotFound</code>"],
    ["No header, bad header, bad parameter, bad id", "<code>400</code>", "<code>requestsWithoutASellerOrWithBadParametersAre400</code>"],
    ["Bad rows written directly", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"],
    ["Same name: same seller, other seller, after archiving", "Refused; allowed; allowed", "<code>aNameIsUniqueAmongProductsOnSaleOnly</code>"],
    ["Saved, then changed", "Equal stamps, then <code>updated_at</code> later", "<code>prePersistAndPreUpdateStampTheRows</code>"],
    ["An archive that fails after the UPDATE", "Rolled back", "<code>anArchiveThatFailsLaterIsRolledBack</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Hard-deleting rows that past orders still reference.</p>
<p>The first test rebuilds the old tables inside a transaction that is rolled back afterwards: an order-lines table whose foreign key says <code>ON DELETE CASCADE</code>. It deletes Assam tea, and order KW-1001's total drops from ₹897 to ₹199. The second test tries the same delete on today's schema: PostgreSQL refuses it, naming <code>order_lines_product_fk</code>. The third sends the seller's DELETE to the API: the product is archived, and the history still reads.</p>
<p>While building, each part was undone once. CASCADE instead of RESTRICT turned 4 tests red: the "refused" delete went through and took product 1 and its lines with it, so the tests after it found them missing. Without <code>@PreUpdate</code>, 2. Archiving that overwrites the first date, 1. The unique index without <code>WHERE archived_at IS NULL</code>, 1. A default list that includes archived products, 1.</p>
</div>
""" + code(read(T + "HardDeleteTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SellerProductController.java", dwn("Reads the seller from the header; DELETE archives; GET lists.", "HTTP only.", "Real deletes behind a DELETE verb.")),
    (J + "SellerCatalog.java", dwn("Archives one of the seller's products; lists active or all.",
        "\"Delete\" is a state change in one transaction.", "Lost order lines.",
        "<ul><li>Another seller's product is <code>404</code>, so ids reveal nothing.</li><li>The entity is managed: no <code>save()</code>; the UPDATE goes at commit.</li></ul>")),
    (J + "Product.java", dwn("The product row with archive date and timestamps.",
        "<code>@PrePersist</code> and <code>@PreUpdate</code> stamp every write; <code>archive()</code> keeps the first date.",
        "Rows with no update time, or a time that lies.",
        "<ul><li><code>@PreUpdate</code> runs only when Hibernate sends an UPDATE, which it does only when a field really changed.</li><li>Times are cut to microseconds, what PostgreSQL keeps.</li></ul>")),
    (J + "ProductRepository.java", "<p>Find one of a seller's products; list active or all.</p>"),
    (M + "V1__sellers_products_orders.sql", "<p>The tables, <code>ON DELETE RESTRICT</code>, the named checks and the partial unique index.</p>"),
    (M + "V2__demo_catalogue.sql", "<p>Two sellers, three products, one past order.</p>"),
    ("src/main/resources/application.yaml", "<p>open-in-view off; schema validation.</p>"),
    (J + "CatalogApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/054-archiving-seller-products/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/catalog/
│   ├── SellerProductController.java   ├── SellerCatalog.java   ├── Product.java
│   ├── ProductRepository.java   └── CatalogApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__sellers_products_orders.sql, V2__demo_catalogue.sql
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
""" + code("""docker compose up -d        # PostgreSQL 17 on localhost:5432
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>With the app running, try what the old code did:</p>
""" + code("""docker compose exec postgres psql -U kartwala -d kartwala -c "DELETE FROM products WHERE id = 1\"""", "bash") + """
<p>PostgreSQL refuses, naming <code>order_lines_product_fk</code>. The seller's way, <code>curl -X DELETE -H "X-Seller-Id: 1" localhost:8080/seller/products/1</code>, archives it instead.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>violates foreign key constraint \"order_lines_product_fk\"</code>", "A real DELETE of a product that orders use.", "Archive it; RESTRICT is doing its job."],
    ["A new product refused with the name of an archived one", "A plain unique index on the name.", "A partial index: <code>WHERE archived_at IS NULL</code>."],
    ["<code>updated_at</code> never changes", "Changed with a bulk query (<code>UPDATE ... </code> in JPQL or SQL): callbacks do not run.", "Change managed entities, or set the column in the query."],
    ["Archived products appear in the shop", "A query without the archive filter.", "Every customer-facing query filters; test the default list."],
    ["<code>products_updated_after_created</code> on insert", "Times set by hand in two calls to <code>now()</code> in Java.", "One value for both in <code>@PrePersist</code>."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the entity and the database.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>SellerProductContractTest</code> ({cnt('SellerProductContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>HardDeleteTrapTest</code> ({cnt('HardDeleteTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>ProductDatabaseTest</code> ({cnt('ProductDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "HardDeleteTrapTest.java", "<p>Written first: the old CASCADE in a rolled-back transaction, today's RESTRICT, and the API's archive.</p>"),
    (T + "SellerProductContractTest.java", "<p>Archive, list, idempotent DELETE, and every refusal.</p>"),
    (T + "ProductDatabaseTest.java", "<p>Named constraints, the partial index, callbacks against the rows, and a rollback.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the demo catalogue reset before each test.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/kartwala/catalog/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=RestoreChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Restore a product", "Beginner-friendly", 20,
    "Add <code>POST /seller/products/{id}/restore</code>: back on sale, <code>updatedAt</code> moved. If the seller has since listed another product with the same name, the partial unique index refuses: <code>409</code>.",
    "both tests in <code>RestoreChallengeTest</code> pass.",
    ["Clear <code>archivedAt</code>; <code>@PreUpdate</code> does the rest.",
     "Flush inside a <code>try</code>, so the index's refusal arrives where you can answer it."],
    "challenge/RestoreChallengeTest.java", ["challenge/solution/Product.java", "challenge/solution/SellerCatalog.java", "challenge/solution/SellerProductController.java"]) + challenge(2, "Purge what no order had", "Go deeper", 25,
    "Add <code>?purge=true</code> to DELETE: a real delete of an archived product no order ever had. Still on sale, or in an order: <code>409</code>. Let RESTRICT decide the second.",
    "the test in <code>PurgeChallengeTest</code> passes.",
    ["Delete and flush; catch <code>DataIntegrityViolationException</code>.",
     "A count of order lines in Java first would race with a new order."],
    "challenge/PurgeChallengeTest.java", ["challenge/solution/SellerCatalog.java", "challenge/solution/SellerProductController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Archive, history table, or copy into the order?</h2>
<p>Three ways to keep orders readable: archive products (this station), move deleted products to a history table, or copy the product's name and price into each order line at purchase. For each, what happens when a seller renames a product, and which one would an auditor prefer?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, mapping"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test with the old CASCADE, in a rolled-back transaction.</li>
<li>Change the foreign key to RESTRICT, and decide what "delete" means for the seller: archive.</li>
<li>Add timestamps with JPA callbacks and database checks.</li>
<li>Make every uniqueness rule "among active rows" where archived rows should not count.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Archive column + RESTRICT + explicit filters", "Every query must remember the filter.", '<span class="pill ok">Chosen</span>'],
    ["Hard delete with CASCADE", "History silently loses lines.", '<span class="pill bad">The trap</span>'],
    ["Hard delete with SET NULL", "Lines lose their product; names and links are gone.", '<span class="pill bad">No</span>'],
    ["Hibernate <code>@SoftDelete</code> or <code>@SQLRestriction</code>", "Filters automatically, everywhere: also where order history needs the archived row.", '<span class="pill warn">Careful</span>'],
    ["Copy name and price into each order line", "Orders read alone; a little duplication. Often done as well.", '<span class="pill ok">Good addition</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Constraints", "Mapped as"], [
    ["<code>products</code>", "<code>products_seller_fk</code>, <code>products_price_positive</code>, <code>products_updated_after_created</code>, <code>products_archived_after_created</code>; partial unique <code>products_seller_name_active</code>", "<code>Product</code>, with callbacks"],
    ["<code>order_lines</code>", "<code>order_lines_product_fk</code> (ON DELETE RESTRICT), <code>order_lines_quantity_positive</code>", "Not mapped here: read with SQL in tests"]]) + """
""" + code(read(M + "V1__sellers_products_orders.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Changing a live foreign key</dt><dd>Dropping CASCADE and adding RESTRICT is a migration: drop the old constraint, add the new one (<code>NOT VALID</code>, then <code>VALIDATE CONSTRAINT</code>, on big tables).</dd>
<dt>Lines already lost</dt><dd>Orders whose lines were cascaded away need rebuilding from payments, invoices or backups. Find them by comparing order totals with their lines.</dd>
<dt>Privacy</dt><dd>Soft delete keeps data. For personal data a person asks to erase, archive is not enough; anonymise the fields instead.</dd>
<dt>Index the filter</dt><dd>Most queries ask for active rows; a partial index <code>WHERE archived_at IS NULL</code> keeps them fast.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Soft delete or hard delete?", "Soft delete when other records refer to the row or history matters (products in orders, accounts). Hard delete when nothing refers to it, or when the law requires erasure."),
    ("What does ON DELETE RESTRICT protect?", "Rows that point at the one being deleted. The delete fails instead of leaving them dangling or deleting them with it, whatever code tried it."),
    ("How do @PrePersist and @PreUpdate work?", "JPA calls them just before it sends the INSERT or UPDATE for an entity. @PreUpdate only runs when dirty checking found a change, and never for bulk JPQL or SQL updates."),
    ("Why a partial unique index with soft delete?", "Archived rows still exist. A plain unique index would stop a seller from re-listing a product with an old name; the partial index applies uniqueness to active rows only."),
    ("What does soft delete cost?", "Every query must filter archived rows, tables keep growing, and uniqueness rules need care. In return, nothing that history depends on can vanish."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You tried the real DELETE in psql."],
    ["Foreign keys", "RESTRICT on history.", "An ON DELETE choice for every key, with a reason."],
    ["Timestamps", "Callbacks and checks.", "You know when callbacks do not run."],
    ["Soft delete", "Filtered lists.", "A partial index for active-only uniqueness."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any delete:</p>
<ul class="rules">
<li>What points at this row, and what does each foreign key's ON DELETE say?</li>
<li>Does anything (orders, invoices, audits) need the row after it is "gone"?</li>
<li>Does every customer-facing query filter archived rows?</li>
<li>Do uniqueness rules still make sense with archived rows in the table?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
