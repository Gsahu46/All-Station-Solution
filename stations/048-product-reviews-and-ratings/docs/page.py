"""Station 048 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 48,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Data JPA (Hibernate 7) · @ManyToOne · @Modifying JPQL update · Slice paging · PostgreSQL 17 · Flyway · Testcontainers",
    "simulation": "Products, customers, purchases and reviews are demo data, not Kartwala's. \"Delivered\" is a date in the purchases table; no courier or order system is called. The customer is named in the request body because this station has no login.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/kartwala/reviews/"
T = "src/test/java/com/kartwala/reviews/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Verified purchase", "A review allowed only from someone whose order of that product was delivered.", "Only guests who stayed can review the hotel.", "<code>purchases.delivered_on</code>"),
    ("Unique constraint", "The database refuses a second row with the same values.", "One vote per voter ID.", "<code>reviews_one_per_customer</code>"),
    ("Aggregate", "A number summarising many rows: a count, a sum, an average.", "A cricket team's run total.", "Count and star total"),
    ("Stored aggregate", "The summary kept in its own row and updated with each change.", "The scoreboard, updated each ball.", "<code>product_ratings</code>"),
    ("Recompute", "Working the summary out again from every row when asked.", "Re-adding every ball of the match to show the score.", "The old rating query"),
    ("Atomic update", "A change the database makes in one step, so two at once cannot overwrite each other.", "Two scorers adding runs on one shared board, one at a time.", "<code>review_count = review_count + 1</code>"),
]
STORY = [
    ("Forty five-star reviews", "One customer posted 40 five-star reviews of a phone case they never bought. The page showed 4.9 stars."),
    ("Two million rows per view", "A bestseller's page recomputed the average from 2 million reviews on every view. During a sale, the database spent most of its time on that one query."),
    ("The fix", "One review per customer per product, only after delivery, both enforced by the database; and the rating kept in its own row, updated with each review."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A number read on every page view should be stored, not recomputed; and the rule for who may add to it belongs in the database too.</p>

<h2>What are we building?</h2>
<p>A buyer posts one review (<code>POST /products/{id}/reviews</code>); anyone reads the reviews ten at a time (<code>GET /products/{id}/reviews</code>) and the rating (<code>GET /products/{id}/rating</code>). The rating is one stored row, kept in step with every review.</p>

<h2>An everyday analogy</h2>
<p>A cricket scoreboard. Nobody re-adds every ball to show the score; the scorer adds each run as it happens. The board stays right only if every run goes on it, and two scorers never write over each other.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Check</strong> the product exists and the customer has a delivered order of it.</li>
<li><strong>Insert</strong> the review; the unique index refuses a second one from the same customer.</li>
<li><strong>Add</strong> one to the count and the stars to the total, in one SQL statement, in the same transaction.</li>
<li><strong>Read</strong> the rating from that one row; the average is total ÷ count.</li>
</ol>

<details class="qa check"><summary>Check yourself: why store a total of stars instead of the average?</summary><p>An average cannot be updated alone: adding a review needs the old count anyway. Count and total update by simple addition, never lose precision, and give the average with one division.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No login.</strong> The customer is named in the body.</li>
<li><strong>No moderation or photos.</strong> Text and stars only.</li>
<li><strong>No editing or deleting.</strong> Editing is challenge 1.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Kartwala</strong> (a fictional marketplace) showed ratings that one customer could inflate, and computed them so expensively that product pages slowed down during sales.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> Asha (delivered) gives 5 stars and Vikram (delivered) 3, <b>then</b> the rating is 2 reviews, 4.0.</li>
<li><b>Given</b> Asha posts again, <b>then</b> <code>409</code>; ten posts from her at the same moment make one review.</li>
<li><b>Given</b> Neha (not delivered yet), Imran (never bought) or a buyer of another product, <b>then</b> <code>422</code>.</li>
<li><b>Given</b> 20 buyers post at the same moment, <b>then</b> all 20 are counted and the stored total equals a recount.</li>
<li><b>Given</b> 0 or 6 stars, 4.5 stars, blank text, or page −1 or 100, <b>then</b> <code>400</code>; an unknown product, <code>404</code>.</li>
<li><b>Given</b> 200,000 reviews, <b>then</b> the rating is read from one row.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>One review per customer per product, enforced by a unique constraint.</li>
<li>The review's purchase must be that customer's purchase of that product (a composite foreign key). Delivery is checked in Java.</li>
<li>The review and the stored totals change in one transaction, by an atomic update.</li>
<li>The average is total ÷ count, rounded half up to one decimal; no reviews means no average (<code>null</code>).</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Enforce "one per customer" and "only buyers" in the database, and map the violation to <code>409</code>.</li>
<li>Choose between a stored aggregate and a recompute, and keep a stored one correct.</li>
<li>Update a counter with one atomic statement instead of read, change, write.</li>
<li>Page without counting every row (a <code>Slice</code>).</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/products/{id}/reviews</code>", "Post a review: <code>customerId</code>, <code>stars</code> (1 to 5), <code>text</code> (1 to 2,000 characters)."],
    ["<code>GET</code>", "<code>/products/{id}/reviews?page=0</code>", "Ten reviews, newest first; <code>hasNext</code> says whether another page exists. Pages 0 to 99 (demo limit)."],
    ["<code>GET</code>", "<code>/products/{id}/rating</code>", "Review count and average stars."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Review posted"],
    ['<span class="pill ok">200</span>', "A page of reviews; the rating"],
    ['<span class="pill warn">400</span>', "Stars outside 1 to 5 or not whole, text blank or too long, customer missing, page out of range"],
    ['<span class="pill warn">404</span>', "No such product"],
    ['<span class="pill warn">409</span>', "This customer already reviewed this product"],
    ['<span class="pill warn">422</span>', "No delivered purchase of this product by this customer"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against one fresh database. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-asha-reviews-the-headphones", "Case 1: Asha, delivered, 5 stars", "<b>Why:</b> a verified purchase: <code>201</code>."),
    ("02-vikram-reviews-them", "Case 2: Vikram, delivered, 3 stars", "<b>Why:</b> <code>201</code>."),
    ("03-the-rating", "Case 3: the rating", "<b>Why:</b> (5 + 3) ÷ 2 = 4.0, read from the stored row."),
    ("04-asha-again", "Case 4: Asha posts again", "<b>Why:</b> one review per customer: <code>409</code>."),
    ("05-neha-before-delivery", "Case 5: Neha, order not delivered", "<b>Why:</b> not verified yet: <code>422</code>."),
    ("06-the-reviews", "Case 6: the first page", "<b>Why:</b> newest first; the count comes from the stored row, not a count query."),
    ("07-no-such-product", "Case 7: product 99", "<b>Why:</b> <code>404</code>."),
    ("08-the-bottle-rating", "Case 8: the water bottle, after 200,000 reviews", "<b>Why:</b> the same one-row read, however many reviews; plans below."),
]) + """
<h2>Two ways to get the bottle's rating</h2>
<p class="muted">After the requests above, 200,000 reviews of the water bottle were written straight to the tables and its stored totals backfilled from them once. Then PostgreSQL ran both queries with <code>EXPLAIN ANALYZE</code> (<code>docs/captures/plans.txt</code>). Timings are from this one run on the build machine.</p>
""" + code(read("docs/captures/plans.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Two verified buyers review", "Count 2, average 3.5 for 5 and 2 stars", "<code>aVerifiedBuyerReviewsOnceAndTheRatingMoves</code>"],
    ["The same customer again", "<code>409</code>, still one review", "<code>theSameCustomerCannotReviewTwice</code>"],
    ["Not delivered, never bought, bought another product", "<code>422</code>, rating untouched", "<code>onlyDeliveredPurchasesCount</code>"],
    ["11 reviews", "10 on page 0, 1 on page 1, newest first", "<code>reviewsComeNewestFirstTenAPage</code>"],
    ["Bad stars, text, customer, page", "<code>400</code>", "<code>badReviewsAndPagesAre400</code>"],
    ["Unknown product", "<code>404</code> on all three endpoints", "<code>unknownProductsAre404</code>"],
    ["Duplicate, bad stars, someone else's purchase, impossible totals, written directly", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"],
    ["The totals row cannot be updated", "The review is not saved either", "<code>whenTheTotalsCannotBeUpdatedTheReviewIsNotSavedEither</code>"],
    ["20 buyers at the same moment", "All 20 counted; stored equals a recount", "<code>twentyBuyersPostingAtOnceAreAllCounted</code>"],
    ["One buyer 10 times at the same moment", "One <code>201</code>, nine <code>409</code>", "<code>oneCustomerPostingTenTimesAtOnceGetsOneReview</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Recomputing the average over millions of rows on every page view.</p>
<p>The test writes 50,000 reviews of one product straight to the tables, then asks PostgreSQL itself, with <code>EXPLAIN ANALYZE</code>, how many rows each way reads. The old JPQL average reads every review of the product; the stored rating reads one row. Both give 4.1. The test counts rows, not milliseconds, so it does not depend on the machine.</p>
<p>The second test checks the price of storing: after posts through the API, the stored totals must equal a recount. A stored aggregate is only worth having while every write keeps it right.</p>
<p>While building, each part was undone once. Without the stored-total update, 7 tests turned red; without the "delivered" condition, 1; without turning the unique violation into <code>409</code>, 1 (ten posts at once gave <code>500</code>s). Removing the "already reviewed?" check before the insert turned none red: the unique index already answers <code>409</code>; the check only saves a failed insert. The trap's own cleanup found a missing index: deleting 200,000 test customers took 76 seconds because each foreign-key check scanned the purchases table.</p>
</div>
""" + code(read(T + "RecomputedAverageTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "ReviewController.java", dwn("Validates the review and the page number.", "HTTP only.", "Stars or pages the database would have to refuse.")),
    (J + "ReviewDesk.java", dwn("Posts reviews with their totals; reads pages and ratings.",
        "One transaction per post: the review and the totals, both or neither.",
        "A review without its stars counted, or counted twice.",
        "<ul><li>The \"already reviewed?\" check is a fast path; the unique index is the guarantee, and its violation becomes <code>409</code>.</li><li>A page is a <code>Slice</code>: no <code>count(*)</code>; the count comes from the stored row.</li></ul>")),
    (J + "Repositories.java", dwn("The five repositories.", "<code>addReview</code> is one atomic JPQL UPDATE.",
        "Read, add one, write back: two posts at once would both write the same new count.")),
    (J + "ProductRating.java", dwn("The stored aggregate: count and star total.", "The average is computed when read, half up, one decimal.", "Floating-point averages stored and drifting.")),
    (J + "Review.java", "<p>A review, <code>@ManyToOne</code> to its product and customer (both LAZY).</p>"),
    (J + "Purchase.java", "<p>A purchase; <code>deliveredOn</code> decides whether it counts.</p>"),
    (J + "Product.java", "<p>A product.</p>"),
    (J + "Customer.java", "<p>A customer.</p>"),
    (M + "V1__products_purchases_reviews.sql", "<p>All tables and named constraints, including the composite foreign key from a review to its purchase.</p>"),
    (M + "V2__demo_catalogue.sql", "<p>Three products, four customers, their purchases.</p>"),
    ("src/main/resources/application.yaml", "<p>open-in-view off; schema validation; decimals refused for whole-number fields.</p>"),
    (J + "ReviewsApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/048-product-reviews-and-ratings/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/reviews/
│   ├── ReviewController.java   ├── ReviewDesk.java   ├── Repositories.java   ├── ProductRating.java
│   ├── Review.java   ├── Purchase.java   ├── Product.java   ├── Customer.java   └── ReviewsApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__products_purchases_reviews.sql, V2__demo_catalogue.sql
├── src/test/java/com/kartwala/reviews/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures (with query plans), saved runs"""
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
<p>Load the 200,000 reviews from <code>docs/capture.sh</code> into your local database (the <code>psql</code> block), then compare the two plans:</p>
""" + code("""docker compose exec postgres psql -U kartwala -d kartwala -c "EXPLAIN ANALYZE SELECT avg(stars), count(*) FROM reviews WHERE product_id = 2"
docker compose exec postgres psql -U kartwala -d kartwala -c "EXPLAIN ANALYZE SELECT * FROM product_ratings WHERE product_id = 2\"""", "bash") + """
<p>The first reads every review of the bottle; the second reads one row, and stays one row however many reviews arrive.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>500</code> when the same review is posted twice at once", "The unique violation is not mapped.", "Catch <code>DataIntegrityViolationException</code> for <code>reviews_one_per_customer</code> and answer <code>409</code>."],
    ["The stored count is lower than the rows", "A read, change, write update, or a write path that skips the totals.", "One atomic UPDATE in the same transaction; compare with a recount (challenge 2)."],
    ["Deleting many rows is very slow", "A foreign key column without an index: each delete scans the referencing table.", "Index the foreign key columns."],
    ["Paging shows a total but is slow", "<code>Page</code> runs a <code>count(*)</code> per request.", "<code>Slice</code>, with the count from the stored row."],
    ["<code>The column name stored_count was not found</code>", "<code>JdbcClient</code> maps columns to record fields by name.", "Alias each column to the field name in snake case."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>ReviewContractTest</code> ({cnt('ReviewContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>RecomputedAverageTrapTest</code> ({cnt('RecomputedAverageTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>ReviewDatabaseTest</code> ({cnt('ReviewDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "RecomputedAverageTrapTest.java", "<p>Written first: rows read by the old and the stored rating, measured by PostgreSQL; stored equals recount.</p>"),
    (T + "ReviewContractTest.java", "<p>Posting, paging, ratings, and every refusal.</p>"),
    (T + "ReviewDatabaseTest.java", "<p>Named constraints, a review rolled back with its totals, and posts in parallel (virtual threads and a start latch).</p>"),
    (T + "ApiTest.java", "<p>Shared setup: no reviews before each test; helpers for buyers and parallel calls.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/kartwala/reviews/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=EditReviewChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests). Without the row lock in the solution, the parallel edit test failed in both of two runs.</p>
""" + challenge(1, "Edit a review", "Go deeper", 35,
    "Add <code>PUT /products/{id}/reviews/{reviewId}</code>: the author changes stars and text, and the stored total moves by the difference. Someone else's review is <code>403</code>; a missing one, or one of another product, <code>404</code>. Ten edits at once must leave the total equal to the review's final stars.",
    "the three tests in <code>EditReviewChallengeTest</code> pass.",
    ["<code>starTotal = starTotal + :delta</code>, where delta = new − old.",
     "Read the old stars under a row lock (<code>@Lock(PESSIMISTIC_WRITE)</code>), or two edits compute their deltas from the same old value."],
    "challenge/EditReviewChallengeTest.java", ["challenge/solution/Review.java", "challenge/solution/Repositories.java", "challenge/solution/ReviewDesk.java", "challenge/solution/ReviewController.java"]) + challenge(2, "A drift report", "Beginner-friendly", 25,
    "Add <code>GET /admin/rating-drift</code>: every product whose stored count or total differs from a recount of its reviews, with both values. All is well when the list is empty.",
    "the test in <code>RatingDriftChallengeTest</code> passes.",
    ["One query: a <code>LEFT JOIN</code> from <code>product_ratings</code> to a grouped recount, keeping rows that differ.",
     "<code>coalesce</code> turns \"no reviews\" into 0."],
    "challenge/RatingDriftChallengeTest.java", ["challenge/solution/ReviewDesk.java", "challenge/solution/ReviewController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Where should the rating live?</h2>
<p>Compare four places for the rating of a product with 2 million reviews: recomputed per view, a stored row updated per review (this station), a materialized view refreshed every 10 minutes, and a cache in front of the recompute. For each: how stale can it be, what does a write cost, and what happens when it is wrong?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, mapping"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: many rows, and the rows each way reads, measured by the database.</li>
<li>Put both rules in the schema: a unique constraint, and a foreign key to the customer's purchase of the product.</li>
<li>Store count and total; update them atomically in the review's transaction; backfill once from the rows.</li>
<li>Prove stored equals recount, including under parallel posts.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Stored count and total, atomic update per review", "Every write path must update it.", '<span class="pill ok">Chosen</span>'],
    ["Recompute on every view", "Reads every review per page view.", '<span class="pill bad">The trap</span>'],
    ["Read the row in Java, add, save", "Two posts at once both save the same new count: a lost update.", '<span class="pill bad">No</span>'],
    ["A database trigger on <code>reviews</code>", "Always in step, even for SQL writes; logic hidden from the Java code.", '<span class="pill warn">Valid</span>'],
    ["Materialized view, refreshed on a schedule", "Stale between refreshes; a refresh still reads everything.", '<span class="pill warn">For reports</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Constraints", "Mapped as"], [
    ["<code>reviews</code>", "<code>reviews_one_per_customer</code>, <code>reviews_stars_range</code>, <code>reviews_text_not_blank</code>, <code>reviews_purchase_fk</code> (purchase, customer, product together)", "<code>Review</code>, <code>@ManyToOne(LAZY)</code> to product and customer"],
    ["<code>product_ratings</code>", "<code>product_ratings_product_fk</code>, <code>product_ratings_totals_consistent</code> (count ≥ 0, count ≤ total ≤ 5 × count)", "<code>ProductRating</code>"],
    ["<code>purchases</code>", "<code>purchases_customer_fk</code>, <code>purchases_product_fk</code>, <code>purchases_id_customer_product_unique</code>; index on customer and product", "<code>Purchase</code>"]]) + """
""" + code(read(M + "V1__products_purchases_reviews.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Backfill on release</dt><dd>When the stored row ships, fill it once from the existing reviews, in a migration or a script, before the page starts reading it.</dd>
<dt>Check for drift</dt><dd>Run a recount nightly (challenge 2) and alert when stored and actual differ. Manual SQL fixes and deleted rows are the usual causes.</dd>
<dt>Hot rows</dt><dd>Every review of a bestseller updates one row. Thousands per second would queue on that row's lock; then count in shards or batch the updates.</dd>
<dt>Fake reviews</dt><dd>Verified purchase and one per customer stop the obvious abuse, not paid reviewers with real orders. Moderation is a separate system.</dd>
<dt>Deep pages</dt><dd>OFFSET pages slow down as the offset grows. For "load more", page by "reviews older than id X" instead.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("When do you store an aggregate instead of computing it?", "When it is read far more often than the rows change and computing it reads many rows. The cost moves to writes, and you must keep it correct: same transaction, atomic updates, and a recount check."),
    ("Why update the counter in SQL instead of in Java?", "UPDATE ... SET n = n + 1 is atomic: PostgreSQL locks the row, so concurrent updates queue. Reading the entity, adding one and saving lets two transactions read the same value and both write it."),
    ("How do you enforce one review per customer?", "A unique constraint on (product_id, customer_id). A check in Java first gives a clear message, but only the constraint holds under concurrency; map its violation to 409."),
    ("How can a foreign key enforce \"only buyers review\"?", "Reference the purchase with (purchase_id, customer_id, product_id) against a unique key on the same three columns of purchases: the purchase must be that customer's purchase of that product."),
    ("Page or Slice in Spring Data?", "Page runs an extra count query for the total; Slice fetches one extra row to know whether there is a next page. Use Slice when the total is known elsewhere or not needed."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You compared the two plans yourself."],
    ["Integrity", "Unique constraint and purchase foreign key.", "You can explain what the database cannot check (delivery)."],
    ["Aggregates", "Stored, updated atomically, in one transaction.", "Backfill and drift check planned."],
    ["Concurrency", "Parallel posts all counted.", "You know when one hot row becomes the bottleneck."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any counter or summary:</p>
<ul class="rules">
<li>How many rows does the hottest read touch, measured, not guessed?</li>
<li>Does every write path update the stored number, in the same transaction?</li>
<li>Is the update one atomic statement, or read, change, write?</li>
<li>Is there a recount that would notice drift?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
