"""Station 081 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 81,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Data JPA · Hibernate 7.4 Envers · Spring Security 7 (HTTP Basic) · PostgreSQL 17 triggers · Testcontainers",
    "simulation": "Sellers, products and prices are demo data, not Kartwala's. A price change is a row in a table: no listing goes live anywhere.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/kartwala/prices/"
T = "src/test/java/com/kartwala/prices/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Change history", "Every version of a record, with when and by whom, kept as data.", "A bank passbook: every entry, never rubbed out.", "<code>products_aud</code>"),
    ("Envers", "Hibernate's history writer: each change to an @Audited entity also writes the row as it now is.", "A carbon copy made with every letter.", "<code>@Audited</code>"),
    ("Revision", "One change set: one moment, one person, the rows it touched.", "One stamped page in the passbook.", "<code>revisions</code>"),
    ("Security context", "Who is signed in for this request, as Spring Security knows it.", "The badge, not the name someone says aloud.", "<code>ChangedByListener</code>"),
    ("Append-only", "Rows can be added, never changed or deleted.", "A ledger written in ink.", "<code>history_is_append_only</code>"),
    ("Paise", "Money as whole paise: ₹54,999 is 5499900.", "Counting coins, not weighing them.", "<code>pricePaise</code>"),
]
STORY = [
    ("A tenfold drop", "Neha's 55-inch TV on Kartwala went from ₹54,999 to ₹5,499 one evening. Hundreds of orders came in."),
    ("A log that could not answer", "The change log was lines of text in three different wordings, without dates, and the name in them was whatever the app sent. Nobody could say who had done it, or when."),
    ("The fix", "Every price change writes a revision: the time, the signed-in user, and the product as it now is, in the same transaction. Nobody can change or delete it afterwards."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">History is data: queryable, attributed by the system, and impossible to edit.</p>

<h2>What are we building?</h2>
<p><code>PUT /products/{id}/price</code> that records who changed what and when, and <code>GET /products/{id}/history</code> that answers it.</p>

<h2>An everyday analogy</h2>
<p>A shop's price board where every change is written in a bound register, signed by the person on shift (checked against their staff card, not their word), with the time, and no page can be torn out.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Sign in</strong>: the seller's name comes from the sign-in.</li>
<li><strong>Change</strong>: Hibernate updates the product.</li>
<li><strong>Record</strong>: in the same transaction Envers writes a revision (when, who) and the product as it now is.</li>
<li><strong>Ask</strong>: the history is read back newest first, each price with the one before it.</li>
</ol>

<details class="qa check"><summary>Check yourself: the request body says "changedBy": "priya.ops". Who does the history name?</summary><p>The signed-in user. The name comes from Spring Security, never from the request: <code>whoIsTheSignedInUserNotWhatTheRequestSays</code>.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No approvals.</strong> Big drops are recorded, not stopped (Practice, challenge 3).</li>
<li><strong>No general audit log.</strong> Only products are audited; logins and reads are not.</li>
<li><strong>No retention.</strong> History grows forever here (see Production).</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Kartwala</strong> (a fictional marketplace): a price dropped from ₹54,999 to ₹5,499 and nobody can tell who changed it or when.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo users: sellers neha.store (products 1 and 2) and arun.mart (3), admin priya.ops, support sam.help.</p>
<ol class="gwt">
<li><b>Given</b> a seller and their product, <b>then</b> the price changes and the history gains one entry with their name and the time.</li>
<li><b>Given</b> a history, <b>then</b> newest first, each with the price before it, back to the import.</li>
<li><b>Given</b> a name in the body or a header, <b>then</b> the history still names the signed-in user.</li>
<li><b>Given</b> another seller's product, <b>then</b> <code>404</code>; support may read any history but gets <code>403</code> on a change.</li>
<li><b>Given</b> an UPDATE or DELETE on the history tables by any writer, <b>then</b> refused.</li>
<li><b>Given</b> a price with paise after the point, <b>then</b> <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Every change and its history are one transaction.</li>
<li>No change without a signed-in user, even from code that skips the endpoints.</li>
<li>Money is whole paise from the request to the database.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Audit an entity with Hibernate Envers and a custom revision entity.</li>
<li>Take \"who\" from the security context.</li>
<li>Make history append-only in the database.</li>
<li>Query history instead of grepping it.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>PUT</code>", "<code>/products/{id}/price</code>", "<code>{pricePaise}</code>, a whole number from 100 (₹1) to 100,000,000 (₹10,00,000)."],
    ["<code>GET</code>", "<code>/products/{id}/history</code>", "Newest first: revision, changedAt, changedBy, change (ADD or MOD), pricePaise, previousPricePaise."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "Price set / history read"],
    ['<span class="pill warn">400</span>', "A price missing, out of range, a string, or with paise after the point"],
    ['<span class="pill warn">401</span>', "No or wrong credentials"],
    ['<span class="pill warn">403</span>', "Support changing a price; a path with no rule"],
    ['<span class="pill warn">404</span>', "No such product, or another seller's"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. JSON bodies are indented for reading; <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-neha-drops-the-tv-price", "Case 1: Neha sets the TV to ₹5,499", "<b>Why:</b> her product; recorded."),
    ("02-neha-puts-it-back", "Case 2: and back to ₹54,999", "<b>Why:</b> another revision."),
    ("03-support-reads-the-history", "Case 3: support reads the TV's history", "<b>Why:</b> who, when, from what to what, back to the import."),
    ("04-a-body-that-names-someone-else", "Case 4: a body that says priya.ops changed it", "<b>Why:</b> the name in the body is ignored (see the rows below)."),
    ("05-another-seller-asks", "Case 5: Arun asks for Neha's TV", "<b>Why:</b> <code>404</code>."),
    ("06-support-tries-to-change-a-price", "Case 6: support tries to change a price", "<b>Why:</b> <code>403</code>: support reads, never sets."),
    ("07-a-price-with-paise-after-the-point", "Case 7: 5499.99 paise", "<b>Why:</b> <code>400</code>: by default Jackson would have stored 5499."),
]) + """
<h2>The history rows afterwards</h2>
<p class="muted">From <code>psql</code> in <code>docs/capture.sh</code>: revision 4 is case 4, signed by neha.store whatever the body said.</p>
""" + code(read("docs/captures/history-rows.txt").rstrip(), "text") + """
<p class="muted">And an attempt to tidy it up, straight in the database:</p>
""" + code(read("docs/captures/tidy-up.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A seller changes their price", "<code>200</code>", "<code>aSellerChangesTheirPrice</code>"],
    ["Two changes", "History newest first, each with the previous price, back to the import", "<code>theHistoryIsNewestFirstWithEachPreviousPrice</code>"],
    ["The same price again", "No new history entry", "<code>theSamePriceAgainAddsNothingToTheHistory</code>"],
    ["Unknown product", "<code>404</code>", "<code>unknownProductsAre404</code>"],
    ["0, 99, too large, missing, a string, 5499.99", "<code>400</code>", "<code>badPricesAre400</code>"],
    ["No or wrong credentials", "<code>401</code>", "<code>noOrWrongCredentialsAre401</code>"],
    ["Another seller's product", "<code>404</code>, unchanged", "<code>anotherSellersProductIs404AndUnchanged</code>"],
    ["Support", "Reads any history; <code>403</code> to change", "<code>supportReadsAnyHistoryButCannotChangeAPrice</code>"],
    ["A header naming someone else", "Ignored", "<code>aHeaderNamingSomeoneElseIsIgnored</code>"],
    ["An admin's change", "Carries the admin's name", "<code>anAdminsChangeCarriesTheAdminsName</code>"],
    ["A change from code with nobody signed in", "Refused, price unchanged", "<code>aChangeWithNobodySignedInIsRefused</code>"],
    ["Odd ids, other paths", "<code>400</code>, <code>404</code> or <code>403</code>", "<code>oddInputAndOtherPathsNeverReachTheData</code>"],
    ["Rules written by plain SQL", "Refused by named constraints", "<code>rulesHoldWithoutJava</code>"],
    ["Two changes", "Two revisions, two history rows", "<code>eachChangeAddsOneRevisionAndOneHistoryRow</code>"],
    ["History that cannot be written", "The price does not change", "<code>aPriceWhoseHistoryFailsDoesNotChange</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Logging changes as free text, so history cannot be queried or trusted.</p>
<ul>
<li><strong>The old log.</strong> Three lines in three wordings; one names no product; none has a date; the name is whatever the app sent; and a line can be quietly rewritten.</li>
<li><strong>Who and when.</strong> The history answers with the signed-in user and the time, and the price before.</li>
<li><strong>Not what the request says.</strong> A <code>changedBy</code> in the body changes nothing.</li>
<li><strong>Not editable.</strong> <code>UPDATE</code> and <code>DELETE</code> on the history tables are refused by the database.</li>
</ul>
<p>While building, each part was undone once: allowing changes with nobody signed in turned 1 test red; no <code>@Audited</code> 10; no append-only trigger 1; no ownership check 1; floats accepted 1; <code>denyAll</code> replaced by <code>authenticated</code> 1.</p>
</div>
""" + code(read(T + "FreeTextLogTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "Product.java", dwn("The listing, @Audited.", "Every change Hibernate writes also writes the row to <code>products_aud</code>.", "Changes that leave no trace.")),
    (J + "Revision.java", dwn("Envers' revision entity, made our own.", "When (milliseconds, UTC) and who, in <code>revisions</code>.", "A history without names.")),
    (J + "ChangedByListener.java", dwn("Who, for every revision.",
        "The name comes from Spring Security's context; no signed-in user, no change.",
        "Names taken from the request, or anonymous changes from a batch job.")),
    (J + "Prices.java", dwn("Change and history.",
        "Sellers reach their own products, admins all, support reads any; the history is an Envers query, newest first.",
        "Another seller's prices, or a history that has to be grepped.",
        "<p>Setting the same price again writes no revision: Hibernate does not flush an unchanged row, so Envers sees nothing to record.</p>")),
    (J + "PriceController.java", "<p>The two endpoints. The body carries only the price.</p>"),
    (J + "SecurityConfig.java", "<p>HTTP Basic with demo users; who may change, who may read; everything else refused.</p>"),
    (J + "ProblemResponses.java", "<p>401 with a Basic challenge and 403 in the same problem JSON as every other error.</p>"),
    ("src/main/resources/application.yaml", dwn("Database, JPA and Jackson settings.",
        "<code>ddl-auto: validate</code> (Flyway owns the schema, audit tables included); floats refused for whole-number fields.",
        "5499.99 paise silently stored as 5499.",
        "<p>Jackson accepts a float for a <code>long</code> and drops the fraction, by default. <code>accept-float-as-int: false</code> makes it a <code>400</code>. Found while building.</p>")),
    (M + "V1__products_and_history.sql", dwn("Products, revisions, products_aud, and the append-only triggers.",
        "History rows can only be added, by any writer.",
        "Someone tidying up an embarrassing change."),),
    (M + "V2__demo_catalogue.sql", "<p>Three products and the import as revision 1, so every history starts with the original price.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "PricesApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/081-who-changed-this-price/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/prices/
│   ├── Product.java   ├── Revision.java   ├── ChangedByListener.java   ├── Products.java
│   ├── Prices.java   ├── PriceController.java   ├── SecurityConfig.java
│   ├── ProblemResponses.java   └── PricesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__products_and_history.sql, V2__demo_catalogue.sql
├── src/test/java/com/kartwala/prices/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
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
<p>Change a price, then try to rewrite the history:</p>
""" + code("""curl -s -u arun.mart:arun-demo-pass -X PUT http://localhost:8080/products/3/price -H 'Content-Type: application/json' -d '{"pricePaise": 199900}'; echo
curl -s -u arun.mart:arun-demo-pass http://localhost:8080/products/3/history; echo
docker compose exec postgres psql -U kartwala -d kartwala -c "DELETE FROM products_aud WHERE id = 3\"""", "bash") + """
<p>The history shows arun.mart and the time; the <code>DELETE</code> fails with <code>history_is_append_only</code>.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>history_is_append_only</code>", "Something tried to change or delete history.", "Do not; add a correcting change instead."],
    ["<code>A price change needs a signed-in user</code>", "Code changed a product with no user in the security context (a job, a test).", "Run it as a named technical user."],
    ["A price of 5499.99 stored as 5499", "Jackson's default <code>ACCEPT_FLOAT_AS_INT</code>.", "<code>spring.jackson.deserialization.accept-float-as-int: false</code>. Found while building this station."],
    ["<code>Could not find a valid Docker environment</code>", "Docker is not running.", "Start Docker Desktop or the Docker service."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">The entity and its history first, then the service and the endpoints.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>PriceContractTest</code> ({cnt('PriceContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>FreeTextLogTrapTest</code> ({cnt('FreeTextLogTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>PriceDatabaseTest</code> ({cnt('PriceDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, one user accessing another user's data, malicious input", f"<code>PriceSecurityTest</code> ({cnt('PriceSecurityTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">Revision times come from the system clock (Envers takes them itself), so tests check order and presence, not exact times.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Hibernate 7.4 with Envers, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "FreeTextLogTrapTest.java", "<p>Written first: what the old text log could not answer, and the history that can.</p>"),
    (T + "PriceSecurityTest.java", "<p>401, other sellers, support, names from headers, admins, changes with nobody signed in, odd input.</p>"),
    (T + "PriceDatabaseTest.java", "<p>Named constraints with plain SQL, how fast history grows, a change whose history fails.</p>"),
    (T + "PriceContractTest.java", "<p>Prices and history through HTTP.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the demo catalogue from V2 before each test, request helpers.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/kartwala/prices/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=HistoryBetweenDatesChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "History between two moments", "Beginner-friendly", 25,
    "<code>GET /products/{id}/history?from=&amp;to=</code>: only the changes from <code>from</code> (inclusive) to <code>to</code> (exclusive); the wrong way round is <code>400</code>.",
    "both tests in <code>HistoryBetweenDatesChallengeTest</code> pass.",
    ["Spring converts ISO-8601 text to <code>Instant</code> request parameters.",
     "The reference solution filters the entries it already reads; for long histories, filter in the Envers query with <code>AuditEntity.revisionProperty(\"changedAtMs\")</code>."],
    "challenge/HistoryBetweenDatesChallengeTest.java", ["challenge/solution/Prices.java", "challenge/solution/PriceController.java", "challenge/solution/SecurityConfig.java"]) + challenge(2, "The price at a moment", "Go deeper", 30,
    "A customer says \"it was ₹54,999 when I ordered\". <code>GET /products/{id}/price-at?time=</code> answers with the price live at that moment and who set it; before the product existed is <code>404</code>.",
    "both tests in <code>PriceAtChallengeTest</code> pass.",
    ["The last revision at or before the moment: <code>revisionProperty(\"changedAtMs\").le(...)</code>, newest first, one result."],
    "challenge/PriceAtChallengeTest.java", ["challenge/solution/Prices.java", "challenge/solution/PriceController.java", "challenge/solution/SecurityConfig.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>A history that grows forever, and drops nobody checked</h2>
<p>Ten million products, a few price changes each per day: how big is <code>products_aud</code> in a year? Design retention (what may be thrown away, after how long, and how without breaking \"append-only\"), monthly partitions, and an archive. Then: should a seller's 90% drop go live at once, or wait for a second person?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: questions the text log cannot answer.</li>
<li>Audit the entity with Envers; own the revision entity and its listener.</li>
<li>Take who from the security context; refuse changes without one.</li>
<li>Make the history tables append-only in the database.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Hibernate Envers with a custom revision entity", "Two rows per change; Hibernate-only writes are audited.", '<span class="pill ok">Chosen</span>'],
    ["Free-text log lines", "Cannot be queried or trusted.", '<span class="pill bad">The trap</span>'],
    ["Database triggers writing history", "Every writer audited, even SQL; \"who\" must reach the database (a session setting).", '<span class="pill warn">Stronger coverage, more plumbing</span>'],
    ["Change data capture (Debezium) to a log store", "History outside the app's database; another system.", '<span class="pill warn">At scale, many services</span>'],
    ["Spring Data's @CreatedBy and @LastModifiedBy", "Only the last change, not the history.", '<span class="pill warn">Not a history</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>revisions</code>, <code>products_aud</code>", "Envers' tables, created by Flyway", "History as rows: one revision, one row per product changed."],
    ["<code>history_is_append_only</code>", "Triggers on both", "No writer can change or delete history."],
    ["<code>revisions_changed_by_shape</code>", "CHECK", "A user name, not free text."],
    ["<code>products_price_positive</code>", "CHECK", "A price can never be zero or negative, from any writer."]]) + """
<p><strong>Transaction boundary:</strong> a price change, its revision and its history row are one transaction.</p>
""" + code(read(M + "V1__products_and_history.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Growth</dt><dd>Each change adds a whole row to <code>products_aud</code> and one to <code>revisions</code>. Plan partitions by month and an archive before the tables are large.</dd>
<dt>Who owns the tables</dt><dd>The append-only triggers stop UPDATE and DELETE, not TRUNCATE or DROP: the application's database user should not own the tables.</dd>
<dt>Writes outside Hibernate</dt><dd>Envers sees only changes made through Hibernate. Bulk SQL updates leave no history; route them through the entity, or add database-side capture.</dd>
<dt>Logs</dt><dd>The history is the record; application logs are not.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What does Hibernate Envers do?", "For each @Audited entity it keeps a _aud table and writes the row as it is after each change, tied to a revision with a number and a time."),
    ("Where should \"who\" come from?", "From the authenticated principal in the security context, set by the server. Never from the request body or a header."),
    ("How do you make history trustworthy?", "Write it in the same transaction as the change, attribute it by the server, and forbid updates and deletes in the database."),
    ("What does Envers not see?", "Changes made outside Hibernate: bulk SQL, other services, migrations."),
    ("Why does the same price twice add no history?", "Hibernate flushes only changed rows; Envers records what Hibernate writes."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["History", "Every change recorded.", "Queried by time; growth planned."],
    ["Who", "From the security context.", "No change at all without a user."],
    ["Trust", "Same transaction.", "Append-only, enforced by the database."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("The name comes from a header",
     "\"Support acts for the seller on the phone\": now any client can put any name in <code>X-Changed-By</code>, and the history says what the client wanted. That is the free-text log again, with a timestamp.",
     "<code>aHeaderNamingSomeoneElseIsIgnored</code> fails."),
    ("Support may change any price",
     "The fix for \"sellers call support\" gives every support agent every seller's prices, and their changes are recorded under the seller's name.",
     "<code>supportReadsAnyHistoryButCannotChangeAPrice</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate lets support fix prices for sellers who call in, and records the seller, not the agent, by taking the name from an <code>X-Changed-By</code> header when present. Read the three files and list every problem before opening the findings.</p>
<p class="path">review/ChangedByListener.java</p>
""" + code(read("review/ChangedByListener.java"), "java") + """
<p class="path">review/SecurityConfig.java</p>
""" + code(read("review/SecurityConfig.java"), "java") + """
<p class="path">review/Prices.java</p>
""" + code(read("review/Prices.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the three flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">If support must act for sellers, record both: the agent as who, the seller as on whose behalf. Both from the server's knowledge, neither from a header.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
