"""Station 047 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 47,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Data JPA (Hibernate 7) · @OneToMany / @ManyToOne · cascade, orphanRemoval · PostgreSQL 17 · Flyway · Testcontainers",
    "simulation": "Customers, prices and invoices are demo data, not Billora's. An invoice is a record; nothing is sent, filed with a tax authority or paid.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/billora/invoicing/"
T = "src/test/java/com/billora/invoicing/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Parent and child", "One invoice has many lines; each line belongs to one invoice.", "A bill and the items printed on it.", "<code>Invoice</code>, <code>InvoiceLine</code>"),
    ("Owning side", "The side whose field becomes the foreign key column.", "The item's own note saying which bill it is on.", "<code>InvoiceLine.invoice</code> → <code>invoice_id</code>"),
    ("Cascade", "An operation on the parent is repeated on its children.", "Filing the bill files its items with it.", "<code>cascade = ALL</code>"),
    ("Orphan removal", "A child taken out of its parent's list is deleted.", "An item crossed off the bill is thrown away, not left in the drawer.", "<code>orphanRemoval = true</code>"),
    ("Bidirectional helper", "One method that sets both sides of the link.", "Writing the item on the bill and the bill number on the item, together.", "<code>addLine</code>"),
    ("LAZY loading", "Children are read from the database only when first used.", "Opening the folder only when you need the items.", "<code>@EntityGraph</code> loads them with the invoice"),
]
STORY = [
    ("A corrected invoice", "A customer disputed 2 of 6 support hours. The account manager edited the invoice: the screen showed the corrected lines and ₹10,999."),
    ("The old lines came back", "Opened again, the invoice had four lines and ₹24,998. The finance report, which sums the lines table, had counted the old ones all along."),
    ("The fix", "Lines taken out of an invoice are deleted (orphanRemoval), lines are added through one helper that sets both sides, and a test reads the table, not just the response."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Removing a child from a Java list is not a DELETE. Say what should happen to it, and check the table.</p>

<h2>What are we building?</h2>
<p>Create an invoice with its lines (<code>POST /invoices</code>), replace its lines (<code>PUT /invoices/{id}/lines</code>), and read it with its total (<code>GET /invoices/{id}</code>). After a replacement, the table holds exactly the new lines.</p>

<h2>An everyday analogy</h2>
<p>A ring binder of bills, each with item slips clipped to it. Unclipping a slip from the bill in your hand does not take it out of the binder: the slip still says which bill it belongs to, and whoever adds up the binder counts it. Orphan removal is the rule "an unclipped slip goes in the shredder".</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>The replacement loads</strong> the invoice and its lines in one query.</li>
<li><strong>It clears</strong> the list and adds the new lines through the helper, which also sets each line's invoice.</li>
<li><strong>At commit</strong>, Hibernate deletes the lines that left the list and inserts the new ones.</li>
<li><strong>Every reader</strong>, the API or a SQL report, sees only the new lines.</li>
</ol>

<details class="qa check"><summary>Check yourself: the old code had <code>cascade = ALL</code>. Why did that not delete the old lines?</summary><p>Cascade repeats operations done to the parent (save it, delete it) on its children. Clearing a list is not an operation on the parent. Only <code>orphanRemoval</code> turns "no longer in the list" into a DELETE.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No tax or GST.</strong> Challenge 2 adds a rate per line.</li>
<li><strong>No issuing.</strong> Real invoices are locked once issued and corrected with credit notes (challenge 3).</li>
<li><strong>No concurrent edits.</strong> Two replacements at the same moment are not handled here.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Billora</strong> (a fictional B2B invoicing SaaS) lets account managers correct an invoice's lines. Removed lines stayed in the database and kept counting in totals and reports.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> hosting (₹4,999) and 6 support hours at ₹1,500, <b>then</b> <code>201</code>, a <code>Location</code>, and ₹13,999.</li>
<li><b>Given</b> the lines are replaced with hosting and 4 hours, <b>then</b> <code>200</code> with ₹10,999, <code>GET</code> shows those 2 lines, and the table holds 2 rows for the invoice.</li>
<li><b>Given</b> no lines, a blank name, quantity 0, a missing quantity, or a price with decimals, <b>then</b> <code>400</code> and nothing changes.</li>
<li><b>Given</b> a replacement the database refuses, <b>then</b> the old lines are all still there.</li>
<li><b>Given</b> an unknown invoice, <b>then</b> <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>A line belongs to exactly one invoice, also in the database (<code>NOT NULL</code> and a named foreign key).</li>
<li>Lines removed from an invoice are deleted in the same transaction.</li>
<li>Totals are computed from the lines, in integer paise.</li>
<li>Reading an invoice with its lines is one query.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Map a bidirectional <code>@OneToMany</code> / <code>@ManyToOne</code> and know which side owns the column.</li>
<li>Choose between cascade and orphanRemoval, and know what each does.</li>
<li>Keep both sides in step with helper methods and a read-only list.</li>
<li>Load a LAZY collection on purpose, not by accident.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/invoices</code>", "Create: <code>customerName</code> and 1 to 50 lines (<code>description</code>, <code>quantity</code> 1 to 10,000, <code>unitPricePaise</code>)."],
    ["<code>PUT</code>", "<code>/invoices/{id}/lines</code>", "Replace every line with the ones sent."],
    ["<code>GET</code>", "<code>/invoices/{id}</code>", "The invoice, its lines and the total."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Created; <code>Location</code> points at it"],
    ['<span class="pill ok">200</span>', "Lines replaced; or the invoice"],
    ['<span class="pill warn">400</span>', "A field missing or out of range, no lines, or a price that is not a whole number of paise"],
    ['<span class="pill warn">404</span>', "No such invoice"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against one fresh database. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-create-an-invoice", "Case 1: an invoice with two lines", "<b>Why:</b> lines saved with the invoice (cascade); total ₹13,999."),
    ("02-correct-the-lines", "Case 2: 4 support hours instead of 6", "<b>Why:</b> the new lines and ₹10,999..."),
    ("03-read-it-back", "Case 3: read it back", "<b>Why:</b> ...and still only those two lines. This is the read the old code got wrong."),
    ("04-no-lines", "Case 4: an empty list of lines", "<b>Why:</b> an invoice needs at least one line: <code>400</code>."),
    ("05-a-price-with-decimals", "Case 5: <code>1500.50</code> as a price in paise", "<b>Why:</b> refused, not truncated to 1500: <code>400</code>."),
    ("06-no-such-invoice", "Case 6: invoice 99", "<b>Why:</b> <code>404</code>."),
]) + """
<h2>What the table holds</h2>
<p class="muted">Read with psql after the requests above (<code>docs/captures/rows.txt</code>). Rows 1 and 2, the original lines, were deleted by the replacement.</p>
""" + code(read("docs/captures/rows.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Create, then read", "Lines and total", "<code>anInvoiceIsCreatedWithItsLinesAndTotal</code>"],
    ["Replace twice, down to one line", "Only the latest lines remain", "<code>replacingLinesKeepsOnlyTheNewOnes</code>"],
    ["No lines, blank name, quantity 0 or missing, decimals in paise", "<code>400</code>, invoice unchanged", "<code>badInvoicesAre400</code>"],
    ["Unknown invoice", "<code>404</code>", "<code>unknownInvoicesAre404</code>"],
    ["Bad rows written directly; deleting an invoice that has lines", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"],
    ["A replacement the database refuses halfway", "Old lines all kept: deletes roll back with inserts", "<code>aReplacementTheDatabaseRefusesKeepsTheOldLines</code>"],
    ["Reading an invoice", "One query, lines included", "<code>readingAnInvoiceWithItsLinesIsOneQuery</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Removing a line from the collection without orphanRemoval, leaving orphan rows.</p>
<p>The old mapping is kept in the tests as <code>OldInvoice</code>, on the same tables: <code>cascade = ALL</code>, no <code>orphanRemoval</code>, and a list anyone can change. The old replacement clears the list and adds the corrected lines. The new lines are inserted (cascade), the old ones are never deleted, and they still carry <code>invoice_id = 1</code>. The table has 4 rows; the API and a SUM both say ₹24,998.</p>
<p>The third test shows the other half of a bidirectional mapping: adding a line to the list without setting the line's invoice. The list is not what fills <code>invoice_id</code>; the line's own field is, so PostgreSQL refuses a line with no invoice.</p>
<p>While building, each part was undone once. Without <code>orphanRemoval</code>, 2 tests turned red; without the back reference in <code>addLine</code>, 9 (no invoice could be saved); without the <code>@EntityGraph</code>, 1. Replacing the list object (<code>lines = new ArrayList&lt;&gt;()</code>) instead of clearing it turned 2 red with Hibernate's <code>A collection with orphan deletion was no longer referenced by the owning entity instance</code>. Separately, the contract test found a real bug while the station was built: Jackson turned <code>1500.50</code> into 1500 paise without a word, until <code>accept-float-as-int</code> was switched off.</p>
</div>
""" + code(read(T + "OrphanLinesTrapTest.java"), "java") + code(read(T + "OldInvoice.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "InvoiceController.java", dwn("Validates bodies (limits, at least one line) and calls the book.", "HTTP only.", "Entity lists exposed to the client.")),
    (J + "InvoiceBook.java", dwn("Creates invoices, replaces lines, reads them; builds the response inside the transaction.",
        "Each change is one <code>@Transactional</code> method.",
        "Lazy lines read after the transaction ended.")),
    (J + "Invoice.java", dwn("The invoice and its lines.",
        "<code>orphanRemoval</code> deletes what leaves the list; helpers set both sides; the list is read-only outside.",
        "Orphan rows, and lines with no invoice.",
        "<ul><li><code>replaceLines</code> clears the same list object: Hibernate tracks that object, so replacing it fails.</li><li>The total is computed from the lines, never stored apart from them.</li></ul>")),
    (J + "InvoiceLine.java", dwn("One line; <code>@ManyToOne(LAZY)</code> to its invoice, the owning side.", "Its <code>invoice</code> field is the <code>invoice_id</code> column.", "A list change that never reaches the column.")),
    (J + "InvoiceRepository.java", "<p><code>findWithLinesById</code>: the invoice and its lines in one query.</p>"),
    (M + "V1__invoices_and_lines.sql", "<p>Both tables, the named constraints, an index on <code>invoice_id</code>.</p>"),
    ("src/main/resources/application.yaml", "<p>open-in-view off; schema validation; decimals refused for whole-number fields.</p>"),
    (J + "InvoicingApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/047-invoices-and-their-line-items/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/billora/invoicing/
│   ├── InvoiceController.java   ├── InvoiceBook.java   ├── Invoice.java   ├── InvoiceLine.java
│   ├── InvoiceRepository.java   └── InvoicingApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__invoices_and_lines.sql
├── src/test/java/com/billora/invoicing/   (see Tests)
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
<p>Remove <code>, orphanRemoval = true</code> from <code>Invoice</code>, start the app, and run the captured requests 1 to 3. Then look at the table:</p>
""" + code("""docker compose exec postgres psql -U billora -d billora -c "SELECT id, invoice_id, quantity FROM invoice_lines\"""", "bash") + """
<p>Four rows for one invoice, and the read returns all four. Put the attribute back.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Removed children come back on the next read", "No <code>orphanRemoval</code>: the rows were never deleted.", "<code>orphanRemoval = true</code>, or delete them yourself."],
    ["<code>A collection with orphan deletion was no longer referenced by the owning entity instance</code>", "The list field was replaced with a new list.", "<code>clear()</code> and <code>add</code> on the same list."],
    ["<code>null value in column \"invoice_id\"</code>", "A child added to the list without its parent set.", "Add through a helper that sets both sides."],
    ["<code>LazyInitializationException ... no session</code>", "Lines read after the transaction.", "Load them in the service (<code>@EntityGraph</code>) and map there."],
    ["A price like <code>1500.50</code> saved as 1500", "Jackson's default turns decimals into whole numbers.", "<code>spring.jackson.deserialization.accept-float-as-int: false</code>"]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the entities and the database.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>InvoiceContractTest</code> ({cnt('InvoiceContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>OrphanLinesTrapTest</code> ({cnt('OrphanLinesTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>InvoiceDatabaseTest</code> ({cnt('InvoiceDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "OrphanLinesTrapTest.java", "<p>Written first: the old mapping leaves rows; the fixed one deletes them; a list change alone fills no column.</p>"),
    (T + "InvoiceContractTest.java", "<p>Create, replace, read, and every refusal.</p>"),
    (T + "InvoiceDatabaseTest.java", "<p>Named constraints, a replacement rolled back whole, one query per read.</p>"),
    (T + "OldInvoice.java", "<p>The old mapping on the same tables, kept only in tests.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the demo invoice, and SQL counts of the line rows.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/billora/invoicing/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=RemoveLineChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in (Java files and one migration), all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Remove one line", "Beginner-friendly", 20,
    "Add <code>DELETE /invoices/{id}/lines/{position}</code>: the line at that position (1 = first) is removed and its row deleted. The last line stays (<code>409</code>); a missing position or invoice is <code>404</code>.",
    "both tests in <code>RemoveLineChallengeTest</code> pass.",
    ["A <code>removeLine</code> helper on <code>Invoice</code>; orphanRemoval does the DELETE.",
     "Check the position against the list before removing."],
    "challenge/RemoveLineChallengeTest.java", ["challenge/solution/Invoice.java", "challenge/solution/InvoiceBook.java", "challenge/solution/InvoiceController.java"]) + challenge(2, "Tax per line", "Go deeper", 30,
    "Each line may carry <code>taxPercent</code> (0 to 40, absent means 0). Show each line's tax, rounded half up to the paisa, the invoice's tax, and a total that includes it. Store the rate with a named check.",
    "both tests in <code>LineTaxChallengeTest</code> pass.",
    ["A migration adds <code>tax_percent</code> with a default, so existing rows stay valid.",
     "Integer rounding half up: <code>(amount × rate + 50) / 100</code>. Never <code>double</code> for money."],
    "challenge/LineTaxChallengeTest.java", ["challenge/solution/V2__line_tax.sql", "challenge/solution/InvoiceLine.java", "challenge/solution/Invoice.java", "challenge/solution/InvoiceBook.java", "challenge/solution/InvoiceController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Correcting an issued invoice</h2>
<p>Once an invoice is sent, accountants do not edit it: they issue a credit note against it. Design the tables and the endpoint for a credit note that reverses some lines of an issued invoice, and decide what <code>PUT /invoices/{id}/lines</code> should answer for an issued one.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, mapping"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test against the table: count the rows, sum them, not just the API answer.</li>
<li>Decide the lifecycle: lines live and die with their invoice, so cascade and orphanRemoval.</li>
<li>Make the list read-only outside the entity and add helpers that set both sides.</li>
<li>Load lines on purpose with an entity graph; count the queries once.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["<code>cascade = ALL</code> + <code>orphanRemoval</code>, helpers", "Children cannot be shared or moved between parents.", '<span class="pill ok">Chosen</span>'],
    ["<code>cascade = ALL</code> only", "Removed lines stay in the table.", '<span class="pill bad">The trap</span>'],
    ["Delete lines with a query, then insert", "Works, but the loaded list is now stale in memory.", '<span class="pill warn">Careful</span>'],
    ["Unidirectional <code>@OneToMany</code> with <code>@JoinColumn</code>", "Hibernate may insert, then update the foreign key: extra statements.", '<span class="pill warn">Fewer helpers, more SQL</span>'],
    ["Lines as an <code>@ElementCollection</code>", "No identity of their own; the whole collection is rewritten on change.", '<span class="pill warn">For small value lists</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Constraints", "Mapped as"], [
    ["<code>invoices</code>", "<code>invoices_customer_not_blank</code>", "<code>Invoice</code>, <code>@OneToMany(mappedBy = \"invoice\", cascade = ALL, orphanRemoval = true)</code>"],
    ["<code>invoice_lines</code>", "<code>invoice_lines_invoice_fk</code> (no cascade delete), <code>invoice_lines_quantity_range</code>, <code>invoice_lines_price_range</code>", "<code>InvoiceLine</code>, <code>@ManyToOne(fetch = LAZY, optional = false)</code>"]]) + """
""" + code(read(M + "V1__invoices_and_lines.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Find orphans you already have</dt><dd>Compare what users saw with what the table holds: totals in documents sent versus a SUM over lines. A one-off script then deletes or flags the extra rows, after finance agrees.</dd>
<dt>Issued documents</dt><dd>Invoices are legal records once sent. Real systems lock them and correct with credit notes; editing lines is for drafts.</dd>
<dt>Reports read tables</dt><dd>Anything that sums a child table directly (BI tools, SQL reports) trusts that the table holds only live rows. That is why orphans cost more than a wrong screen.</dd>
<dt>Large collections</dt><dd>Loading every line to replace them is fine for 50; for thousands, page them and delete with a query.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is the difference between cascade REMOVE and orphanRemoval?", "Cascade REMOVE deletes children when the parent is deleted. orphanRemoval also deletes a child when it is removed from the parent's collection, while the parent lives on."),
    ("Which side owns a bidirectional one-to-many?", "The many side (@ManyToOne): its field is the foreign key column. The @OneToMany(mappedBy) list is a mirror; changing only the list writes nothing to that column."),
    ("Why add helper methods?", "So both sides change together. Otherwise the list and the foreign key disagree until the next load, and a child can be saved with no parent."),
    ("Why must you not replace a collection field with orphanRemoval?", "Hibernate tracks the collection object it loaded. A new list object loses that tracking, and Hibernate refuses the flush rather than guess which children to delete."),
    ("Is @OneToMany LAZY by default?", "Yes. Load it on purpose (an entity graph or a fetch join) when you need it, inside the transaction."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You removed <code>orphanRemoval</code> and saw the rows in psql."],
    ["Mapping", "Owning side and <code>mappedBy</code> right.", "You can say when not to make it bidirectional."],
    ["Lifecycle", "Cascade and orphanRemoval chosen on purpose.", "Credit notes instead of edits for issued invoices."],
    ["Loading", "Lines loaded in the service.", "You counted the queries."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any parent–child mapping:</p>
<ul class="rules">
<li>When a child leaves the parent's list, what happens to its row, and is that written down?</li>
<li>Can anyone change the list without going through a helper?</li>
<li>Does a test count rows in the table after a removal, not just read the response?</li>
<li>Where are the children loaded, and how many queries does that take?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
