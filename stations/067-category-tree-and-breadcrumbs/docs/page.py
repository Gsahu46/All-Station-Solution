"""Station 067 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 67,
    "stack": "Spring Boot 4.1.1 · Java 25 · JdbcClient · PostgreSQL 17 WITH RECURSIVE (SEARCH, CYCLE) · adjacency list · trigger with an advisory lock · Testcontainers",
    "simulation": "The category tree is demo data, not Kartwala's. No products are listed.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/kartwala/categories/"
T = "src/test/java/com/kartwala/categories/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Tree", "Each category has at most one parent; one category, Home, has none.", "A family tree, or folders on a computer.", "<code>categories</code>"),
    ("Adjacency list", "Each row stores only its parent's id.", "Each person knows only their own mother.", "<code>parent_id</code>"),
    ("Breadcrumb", "The path from the top to where you are.", "Home > Electronics > Phones > Android.", "<code>/breadcrumb</code>"),
    ("Recursive query", "A query that repeats a step until there is nothing left.", "\"Ask your mother who her mother was\", until no one knows.", "<code>WITH RECURSIVE</code>"),
    ("Cycle", "A category that is, through its parents, under itself.", "A folder inside its own subfolder.", "refused by <code>categories_no_cycle</code>"),
    ("Materialised path", "Each row stores its whole path as text.", "Writing your full address on everything you own.", "the alternative in Design"),
]
STORY = [
    ("A product page", "Shows \"Home > Electronics > Phones > Android\". The code asked for Android, then its parent, then that one's parent: four queries, one per level."),
    ("A loop", "An admin moved Electronics under Phones. Now Phones is under Electronics under Phones… The breadcrumb code followed parents forever, and the page never loaded."),
    ("The fix", "One recursive query walks the tree inside PostgreSQL, and stops if it ever meets a category twice. And the database refuses any move that would make a loop."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Walk a tree in one query, and never let it stop being a tree.</p>

<h2>What are we building?</h2>
<p><code>GET /categories/4/breadcrumb</code> gives the path from Home to Android; <code>GET /categories/8/descendants</code> gives everything under Fashion, as an indented menu.</p>

<h2>An everyday analogy</h2>
<p>A family where each person only knows their mother. To find your great-grandmother, you could phone your mother, who phones hers, and so on: one call per generation. Or you hand the whole family register to someone who reads it all at once.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Start</strong> at the category asked for.</li>
<li><strong>Repeat</strong>: join each found row to its parent (breadcrumb) or its children (descendants).</li>
<li><strong>Stop</strong> when there is nothing more, or if a category comes round a second time.</li>
<li><strong>Order</strong>: root first for breadcrumbs; depth first, by name, for menus.</li>
</ol>

<details class="qa check"><summary>Check yourself: Phones moves from Electronics to Home. How many rows change with this design? With a stored path on every row?</summary><p>Here, one: Phones' <code>parent_id</code>. Every breadcrumb under it follows automatically. With a materialised path, Phones and every category under it must be rewritten, and any link built from the old path breaks.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No products.</strong> Only the tree.</li>
<li><strong>No admin screens.</strong> Moving is Practice 2.</li>
<li><strong>No caching.</strong> Menus change rarely and cache well; that comes later.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Kartwala</strong> (a fictional marketplace) took 4 queries per product page for its breadcrumb, and a category move created a loop that hung the page.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo data: Home with Electronics and Fashion, and a Hobbies branch 12 levels deep.</p>
<ol class="gwt">
<li><b>Given</b> Android, <b>then</b> \"Home > Electronics > Phones > Android\".</li>
<li><b>Given</b> Fashion, <b>then</b> Men, Shoes, Women, Sarees, Shoes, with depths 1, 2, 1, 2, 2.</li>
<li><b>Given</b> any depth, <b>then</b> one SQL statement.</li>
<li><b>Given</b> a leaf, <b>then</b> no descendants; an unknown id, <code>404</code>; a non-number, <code>400</code>.</li>
<li><b>Given</b> a move under its own descendant, by anyone, <b>then</b> the database refuses it.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Store only the parent; derive paths when asked.</li>
<li>Every recursive query has a <code>CYCLE</code> guard.</li>
<li>The database refuses cycles, self-parents, duplicate slugs under one parent, and a second root with the same slug.</li>
<li>Moves take turns, so two moves at once cannot build a loop between them.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Model a tree as an adjacency list.</li>
<li>Write <code>WITH RECURSIVE</code> up and down a tree, with <code>SEARCH</code> and <code>CYCLE</code>.</li>
<li>Prevent cycles in the database.</li>
<li>Compare adjacency list, materialised path and closure table.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/categories/{id}/breadcrumb</code>", "<code>{id, path, trail: [{id, name, slug}]}</code>, Home first."],
    ["<code>GET</code>", "<code>/categories/{id}/descendants</code>", "<code>{id, descendants: [{id, parentId, name, slug, depth}]}</code>, depth first, siblings by name."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "A breadcrumb or a list, possibly empty"],
    ['<span class="pill warn">400</span>', "The id is not a number"],
    ['<span class="pill warn">404</span>', "No such category"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-android-breadcrumb", "Case 1: Android's breadcrumb", "<b>Why:</b> four levels, one query."),
    ("02-everything-under-fashion", "Case 2: everything under Fashion", "<b>Why:</b> depth first, siblings by name; two categories called Shoes, under different parents."),
    ("03-a-leaf", "Case 3: iPhone's descendants", "<b>Why:</b> a leaf: an empty list."),
    ("04-no-such-category", "Case 4: category 999", "<b>Why:</b> <code>404</code>."),
]) + """
<h2>The move that made the loop, tried on the real table</h2>
<p class="muted">From <code>docs/capture.sh</code>, in <code>psql</code> (<code>docs/captures/loop-refused.txt</code>).</p>
""" + code(read("docs/captures/loop-refused.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Root, 4 levels, 14 levels", "Correct trail, one statement", "<code>theBreadcrumbRunsFromHomeToTheCategory</code>"],
    ["A branch with same-named children", "Menu order, depths, parents", "<code>descendantsReadLikeAnIndentedMenu</code>"],
    ["A leaf", "Empty list", "<code>aLeafHasNoDescendants</code>"],
    ["Unknown id; not a number", "<code>404</code>; <code>400</code>", "<code>anUnknownCategoryIs404AndANonNumberIs400</code>"],
    ["A loop in old data", "Old loop: endless; recursive query: stops", "<code>aLoopInTheOldDataKeptTheOldCodeGoingForever</code>"],
    ["The loop-making move today", "Refused by the trigger", "<code>theRealTableRefusesTheMoveThatMadeTheLoop</code>"],
    ["Self-parent, duplicate slug, orphan, bad slug, second Home", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"],
    ["A move; a half-added branch", "One update; rolled back", "<code>CategoryDatabaseTest</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">One query per level, and no protection against cycles.</p>
<p>The old loop is kept in the tests as <code>OldBreadcrumb</code>. On the real tree it sends 4 queries for Android and 14 for the deepest Hobbies level; the recursive query is one statement for both.</p>
<p>On a copy of the table without the cycle check, the test makes the admin's move: Electronics under Phones. The old loop follows parents round and round, and stops only at the test's own limit of 1,000 queries. The recursive query's <code>CYCLE</code> clause notices Phones the second time and stops after 3 rows. On the real table, the same <code>UPDATE</code> is refused.</p>
<p>While building, each fix was undone once: without the trigger, the trap test's move really created the loop in the shared table, and 2 contract tests failed after it, 3 red in all: the damage outlives the request that caused it. Ordering the trail root last turned 4 red; dropping the <code>SEARCH</code> clause 1; including the category in its own descendants 2; a plain <code>UNIQUE</code> (which treats every <code>NULL</code> parent as different, allowing a second Home) 1. Removing <code>CYCLE</code> was not tried: on a loop, the query never ends.</p>
</div>
""" + code(read(T + "QueryPerLevelTrapTest.java"), "java") + code(read(T + "OldBreadcrumb.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "CategoryController.java", "<p>Two endpoints; Spring answers a non-numeric id with <code>400</code>.</p>"),
    (J + "CategoryTree.java", dwn("The two recursive queries.",
        "One statement per answer at any depth; <code>CYCLE</code> stops a loop; <code>SEARCH DEPTH FIRST</code> orders the menu.",
        "A query per level, and a loop that never ends.",
        "<ul><li>The first row of the descendants query is the category itself (depth 0), dropped before answering.</li><li><code>404</code> when the start row does not exist: the query returns nothing at all.</li></ul>")),
    (M + "V1__categories.sql", dwn("The adjacency list, named constraints, and the cycle trigger.",
        "The trigger walks up from the new parent; if it meets the category being moved, the move is a loop. The advisory lock makes moves take turns.",
        "A loop from any admin tool or script, not only this app.")),
    (M + "V2__demo_categories.sql", "<p>13 categories and a 12-level Hobbies branch.</p>"),
    ("src/main/resources/application.yaml", "<p>Problem details on.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "CategoriesApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/067-category-tree-and-breadcrumbs/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/categories/
│   ├── CategoryController.java   ├── CategoryTree.java   └── CategoriesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__categories.sql, V2__demo_categories.sql
├── src/test/java/com/kartwala/categories/   (see Tests)
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
<p>Run the recursive query by hand and watch the <code>visited</code> path grow:</p>
""" + code("""docker compose exec postgres psql -U kartwala -d kartwala
WITH RECURSIVE up (id, parent_id, name) AS (
    SELECT id, parent_id, name FROM categories WHERE id = 112
    UNION ALL SELECT c.id, c.parent_id, c.name FROM categories c JOIN up ON c.id = up.parent_id
) CYCLE id SET looped USING visited
SELECT name, visited FROM up;""", "sql") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>categories_no_cycle: category … cannot move under its own descendant …</code>", "A move would put a category inside itself.", "Expected; pick another parent."],
    ["A recursive query that never returns", "A loop in the data and no <code>CYCLE</code> clause.", "Add <code>CYCLE id SET … USING …</code> (PostgreSQL 14+), or a depth limit."],
    ["<code>syntax error at or near \"CYCLE\"</code>", "PostgreSQL older than 14.", "A <code>path</code> array column and <code>WHERE NOT id = ANY(path)</code>."],
    ["Two Home categories accepted", "A plain <code>UNIQUE</code> treats every <code>NULL</code> as different.", "<code>UNIQUE NULLS NOT DISTINCT</code> (PostgreSQL 15+)."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>CategoryContractTest</code> ({cnt('CategoryContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>QueryPerLevelTrapTest</code> ({cnt('QueryPerLevelTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>CategoryDatabaseTest</code> ({cnt('CategoryDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">Not tested: two moves at the same moment. The trigger's advisory lock makes them take turns, so the second sees the first's change; no parallel test proves it here.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "QueryPerLevelTrapTest.java", "<p>Written first: queries per level, the endless loop, and the refused move.</p>"),
    (T + "CategoryDatabaseTest.java", "<p>Named constraints, a one-row move, and a rolled-back branch.</p>"),
    (T + "CategoryContractTest.java", "<p>Both endpoints through HTTP.</p>"),
    (T + "OldBreadcrumb.java", "<p>The old loop, counting its own queries.</p>"),
    (T + "ApiTest.java", "<p>Shared setup.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/kartwala/categories/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=ChildrenChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "One level of the menu", "Beginner-friendly", 20,
    "Add <code>GET /categories/{id}/children</code>: direct children by name, each with <code>hasChildren</code> for the menu's arrow.",
    "the test in <code>ChildrenChallengeTest</code> passes.",
    ["No recursion needed: <code>WHERE parent_id = ?</code>.", "<code>EXISTS (SELECT 1 … WHERE g.parent_id = c.id)</code> per row answers the arrow."],
    "challenge/ChildrenChallengeTest.java", ["challenge/solution/CategoryTree.java", "challenge/solution/CategoryController.java"]) + challenge(2, "Move a branch", "Go deeper", 30,
    "Add <code>PUT /categories/{id}/parent</code> <code>{\"parentId\"}</code>: move the category and everything under it, answer its new breadcrumb. A loop is <code>409</code>; unknown ids <code>404</code>.",
    "both tests in <code>MoveCategoryChallengeTest</code> pass.",
    ["One <code>UPDATE</code>; the trigger decides about loops.", "The trigger raises a <code>check_violation</code>: Spring turns it into a <code>DataIntegrityViolationException</code>."],
    "challenge/MoveCategoryChallengeTest.java", ["challenge/solution/CategoryTree.java", "challenge/solution/CategoryController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Three ways to store a tree</h2>
<p>Compare the adjacency list (here), a materialised path (<code>'/1/2/3/4/'</code>, or PostgreSQL's <code>ltree</code>), and a closure table (one row per ancestor–descendant pair) for: a breadcrumb, all descendants, moving Phones with 400 subcategories, and keeping product URLs working after the move. Which one makes \"all products under Electronics\" a plain index lookup?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, trigger"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: queries per level, and the loop.</li>
<li>Keep the adjacency list; write the two recursive queries with <code>CYCLE</code>.</li>
<li>Add the trigger that refuses loops, and make moves take turns.</li>
<li>Name every constraint, and test each one with plain SQL.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Adjacency list + WITH RECURSIVE + cycle trigger", "A recursive query per read.", '<span class="pill ok">Chosen</span>'],
    ["Adjacency list, one query per level in Java", "Queries grow with depth; loops never end.", '<span class="pill bad">The trap</span>'],
    ["Materialised path / <code>ltree</code>", "Fast subtree reads; a move rewrites every row below.", '<span class="pill warn">Read-heavy, rare moves</span>'],
    ["Closure table", "Fast everything; many rows; moves rewrite many pairs.", '<span class="pill warn">Large trees</span>'],
    ["Nested sets (left/right numbers)", "Fast reads; inserts renumber half the tree.", '<span class="pill bad">Rarely worth it</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>categories_parent_fk</code>", "<code>parent_id</code> references <code>categories</code>", "No orphans."],
    ["<code>categories_not_own_parent</code>", "CHECK", "The one-step loop, without the trigger."],
    ["<code>categories_slug_per_parent</code>", "UNIQUE NULLS NOT DISTINCT (parent_id, slug)", "Unique URLs per level, and one root per slug."],
    ["<code>categories_no_cycle</code>", "Trigger before insert or a change of <code>parent_id</code>", "Every longer loop, from any writer."],
    ["<code>categories_parent</code>", "Index on <code>parent_id</code>", "The descendants query joins children by parent."]]) + """
""" + code(read(M + "V1__categories.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>URLs after a move</dt><dd>Links built from slugs (<code>/electronics/phones</code>) change when Phones moves. Keep product URLs on ids, or redirect old paths.</dd>
<dt>Caching</dt><dd>The whole tree is small and changes rarely: cache it and clear the cache on every move.</dd>
<dt>Big moves</dt><dd>Moving is one row here, but anything derived from paths (search indexes, caches) must be rebuilt for the whole branch.</dd>
<dt>The advisory lock</dt><dd>One lock for the whole tree: moves are rare, so taking turns costs nothing. With many concurrent moves, lock per branch instead.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("How do you store a tree in a relational database?", "Most simply as an adjacency list: each row has its parent's id. Alternatives are materialised paths, closure tables and nested sets."),
    ("How does WITH RECURSIVE work?", "A starting query, UNION ALL, and a step that joins the previous rows to the table; PostgreSQL repeats the step until it returns no rows."),
    ("How do you stop a recursive query from looping?", "The CYCLE clause (PostgreSQL 14+) tracks visited ids; or keep a path array and refuse ids already in it; or limit the depth."),
    ("How do you prevent cycles?", "Before changing a parent, check that the new parent is not a descendant; do it in the database (a trigger) so every writer is checked, and serialise moves."),
    ("Why not store the full path?", "Reads get simpler, but moving a category means rewriting it and everything under it, and any path-based link breaks."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the recursive query by hand."],
    ["SQL", "WITH RECURSIVE up and down.", "SEARCH and CYCLE clauses."],
    ["Integrity", "Loops refused by the database.", "Why moves must take turns."],
    ["Design", "Knows the adjacency list.", "Can argue for a closure table."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This station has no flawed version to review. Use this checklist on any hierarchy:</p>
<ul class="rules">
<li>Does any loop in Java follow parents one query at a time?</li>
<li>Does every recursive query have a cycle guard or a depth limit?</li>
<li>Can any writer create a loop, or a second root?</li>
<li>What breaks when a branch moves: URLs, caches, search?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
