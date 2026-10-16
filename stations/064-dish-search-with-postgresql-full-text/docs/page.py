"""Station 064 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 64,
    "stack": "Spring Boot 4.1.1 · Java 25 · JdbcClient · PostgreSQL 17 full-text search (tsvector, websearch_to_tsquery, ts_rank) · GIN index · Testcontainers",
    "simulation": "Dishes, restaurants and prices are demo data (200,008 rows), not Tiffino's. Nothing is ordered.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tiffino/dishes/"
T = "src/test/java/com/tiffino/dishes/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]
import re as _re
def pages(name):
    """Pages (8 kB blocks) the whole query touched: the first 'Buffers:' line of a saved plan, hit + read."""
    line = next(l for l in read("docs/captures/" + name).splitlines() if "Buffers:" in l)
    return sum(int(n) for n in _re.findall(r"(?:hit|read)=(\d+)", line))
P_LIKE, P_FTS = pages("explain-like.txt"), pages("explain-full-text.txt")

# ---------- Level 1: Understand ----------
TERMS = [
    ("Full-text search", "Searching by words, not by exact characters.", "Asking a waiter for \"something with paneer\".", "this station"),
    ("tsvector", "A row's text as a sorted list of normalised words (lexemes).", "The index at the back of a cookbook.", "the <code>search</code> column"),
    ("tsquery", "The words being searched for, with AND, OR, NOT.", "\"Paneer and tikka, not Mysore.\"", "<code>websearch_to_tsquery</code>"),
    ("Stemming", "Reducing words to a common root.", "dosas, dosa → dosa.", "the <code>english</code> configuration"),
    ("GIN index", "For each word, the list of rows containing it.", "The cookbook index: paneer → pages 12, 40, 77.", "<code>dishes_search</code>"),
    ("Ranking", "Ordering matches by how well they match.", "A dish named \"Paneer Tikka\" before one that mentions it.", "<code>ts_rank</code> with weights A and B"),
]
STORY = [
    ("A hungry customer", "Types \"paneer tikka\". The menu has \"Paneer Tikka Masala\"."),
    ("Nothing found, slowly", "The search compared characters: lower-case \"paneer\" is not \"Paneer\", \"dosas\" is not \"Dosa\", and descriptions were never looked at. And <code>LIKE '%…%'</code> reads every dish's name to find the few that match."),
    ("The fix", "Store each dish's words, normalised, in a <code>tsvector</code> kept by PostgreSQL; search words with a GIN index; rank name matches first."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">People search with words. Match words, not characters, and let an index find them.</p>

<h2>What are we building?</h2>
<p><code>GET /dishes/search?q=paneer tikka&amp;city=pune</code>: up to 20 dishes that contain those words, best matches first.</p>

<h2>An everyday analogy</h2>
<p>A cookbook's index. You look up \"paneer\" and get page numbers, instead of reading every recipe. The index lists \"dosa\" once for \"dosa\" and \"dosas\", and ignores \"the\" and \"with\".</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>When a dish is saved</strong>, PostgreSQL turns its name and description into words: \"Paneer Tikka Masala\" → paneer, tikka, masala.</li>
<li><strong>When someone searches</strong>, their text becomes words the same way: \"TIKKAS paneer\" → tikka AND paneer.</li>
<li><strong>The GIN index</strong> finds the dishes with all those words.</li>
<li><strong>Ranking</strong> puts dishes with the words in their name before those with them only in the description.</li>
</ol>

<details class="qa check"><summary>Check yourself: someone types \"panner\". What does full-text search return?</summary><p>Nothing: \"panner\" is not a word in any dish, and full-text search does not guess spellings. That is a real limit, tested on purpose; Practice 2 adds \"did you mean\" with trigrams.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No typo tolerance.</strong> Practice 2; a search engine does it better.</li>
<li><strong>No Hindi or Marathi.</strong> One language configuration, English.</li>
<li><strong>No ordering.</strong> Dishes are read only.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tiffino</strong> (a fictional food delivery app) has 3 million dishes. Its search missed obvious matches and scanned every dish.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo data: 7 Pune dishes and 1 Mumbai dish written out, 200,000 generated ones that never mention paneer, tikka or dosa.</p>
<ol class="gwt">
<li><b>Given</b> \"paneer tikka\" in Pune, <b>then</b> the three dishes with both words in the name, then Butter Chicken, whose description mentions paneer tikka.</li>
<li><b>Given</b> \"TIKKAS PANEER\", <b>then</b> the same four; \"dosas\" finds both dosas.</li>
<li><b>Given</b> <code>\"masala dosa\" -mysore</code>, <b>then</b> only Masala Dosa.</li>
<li><b>Given</b> characters such as <code>&amp; | ! ( :*</code>, <b>then</b> they are ignored, never a <code>500</code>.</li>
<li><b>Given</b> only stop words, a typo, or another city, <b>then</b> an empty list.</li>
<li><b>Given</b> q shorter than 2 or longer than 100, or no city, <b>then</b> <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>The search vector is kept by the database (a generated column), never by app code.</li>
<li>User text goes through <code>websearch_to_tsquery</code>, never <code>to_tsquery</code>.</li>
<li>The search uses the GIN index; checked with EXPLAIN in a test.</li>
<li>Name matches rank above description matches.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Build a weighted <code>tsvector</code> as a generated column.</li>
<li>Choose between <code>to_tsquery</code>, <code>plainto_tsquery</code> and <code>websearch_to_tsquery</code>.</li>
<li>Index it with GIN and rank with <code>ts_rank</code>.</li>
<li>Know what full-text search does not do.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/dishes/search?q=…&amp;city=…</code>", "<code>{q, city, dishes: [{id, name, restaurant, pricePaise}]}</code>, at most 20, best first."]]) + """
<p>The search text understands what people already type into search boxes: words (all must match), <code>\"exact phrase\"</code>, <code>-word</code> to exclude, and <code>or</code>.</p>
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "Results, possibly an empty list"],
    ['<span class="pill warn">400</span>', "q missing, under 2 or over 100 characters; city missing or not 3 to 30 letters"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-paneer-tikka", "Case 1: paneer tikka", "<b>Why:</b> both words anywhere in the name or description; Butter Chicken last, a description match."),
    ("02-dosas-in-capitals", "Case 2: DOSAS in Pune", "<b>Why:</b> case and plural do not matter."),
    ("03-exact-phrase-without-mysore", "Case 3: <code>\"masala dosa\" -mysore</code>", "<b>Why:</b> search-box syntax."),
    ("04-a-typo", "Case 4: panner", "<b>Why:</b> empty: full-text matches words, not spellings."),
    ("05-one-letter", "Case 5: p", "<b>Why:</b> <code>400</code>; one letter is not a search."),
]) + """
<h2>What PostgreSQL does to the words</h2>
<p class="muted">Asked directly in <code>psql</code> (<code>docs/captures/words.txt</code>).</p>
""" + code(read("docs/captures/words.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Both words, in name or description", "Name matches first", "<code>paneerTikkaFindsEveryDishWithBothWordsNameMatchesFirst</code>"],
    ["Capitals, other word order, plurals", "Same results", "<code>caseWordOrderAndPluralsDoNotMatter</code>"],
    ["Phrases, exclusions, or", "Understood", "<code>searchSyntaxPeopleAlreadyKnow</code>"],
    ["<code>&amp; | ! ( :*</code>", "Ignored, not a 500", "<code>oddCharactersAreSearchedNotParsed</code>"],
    ["Stop words only; another city", "Empty", "<code>noMatchIsAnEmptyList</code>"],
    ["A typo", "Empty: the limit", "<code>aTypoFindsNothingThatIsTheLimit</code>"],
    ["Writing the search column directly; renaming a dish", "Refused; the words follow the name", "<code>theSearchColumnIsKeptByTheDatabaseNotByTheApp</code>"],
    ["Bad rows; a half-added menu", "Refused; rolled back", "<code>DishDatabaseTest</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead"><code>LIKE '%term%'</code> that cannot use an index and misses word forms.</p>
<p>The old query is kept in the test: <code>name LIKE '%' || :q || '%'</code>.</p>
<ul>
<li><strong>Misses.</strong> \"paneer tikka\" finds nothing (the menu says \"Paneer\"); \"Paneer Tikka\" misses Butter Chicken (descriptions were never searched); \"Tikka Paneer\" and \"Masala Dosas\" find nothing.</li>
<li><strong>Reads.</strong> A B-tree is sorted from the first character; <code>'%Paneer%'</code> has no first character to start from. PostgreSQL narrowed by city, then read every Pune dish's name: """ + str(P_LIKE) + """ pages. The full-text search read """ + str(P_FTS) + """.</li>
<li><strong>The first fix that breaks.</strong> <code>to_tsquery</code> expects its own syntax: <code>to_tsquery('english', 'paneer tikka')</code> is \"syntax error in tsquery\", a <code>500</code> for an ordinary search. <code>websearch_to_tsquery</code> never fails on what people type.</li>
</ul>
<p>While building, each fix was undone once: <code>to_tsquery</code> turned 6 tests red; the name alone in the vector 4; the <code>simple</code> configuration (no stemming) 3; no ranking 2; no GIN index 1; <code>plainto_tsquery</code> 1 (no phrases or exclusions); no lower-casing of the city 1.</p>
</div>
""" + code(read("docs/captures/explain-like.txt").rstrip(), "text") + code(read("docs/captures/explain-full-text.txt").rstrip(), "text") + code(read(T + "LikeSearchTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "DishController.java", dwn("Checks the length of q and the city, lower-cases the city.",
        "One-letter searches and huge inputs never reach the database.",
        "\"p\" matching nothing useful after a full scan.")),
    (J + "DishSearch.java", dwn("One SQL query: parse, match through the index, rank, top 20.",
        "<code>websearch_to_tsquery</code> once, reused for match and rank.",
        "<code>LIKE</code>, or a <code>to_tsquery</code> that fails on spaces.")),
    (M + "V1__dishes.sql", dwn("The table, with <code>search</code> as a generated column.",
        "PostgreSQL rebuilds the words whenever the name or description changes; no app code can forget.",
        "A search column that drifts from the menu.")),
    (M + "V3__search_index.sql", dwn("The GIN index on <code>search</code>, and one on city.",
        "The search reads only the rows containing the words.",
        "A full read of every dish in the city.")),
    (M + "V2__demo_dishes.sql", "<p>8 dishes by hand, 200,000 generated.</p>"),
    ("src/main/resources/application.yaml", "<p>Problem details on.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "DishesApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/064-dish-search-with-postgresql-full-text/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/tiffino/dishes/
│   ├── DishController.java   ├── DishSearch.java   └── DishesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__dishes.sql, V2__demo_dishes.sql, V3__search_index.sql
├── src/test/java/com/tiffino/dishes/   (see Tests)
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
./mvnw spring-boot:run      # the API on http://localhost:8080; the first start loads 200,008 dishes
./mvnw test                 # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>See how text becomes words, and how a search matches them:</p>
""" + code("""docker compose exec postgres psql -U tiffino -d tiffino
SELECT to_tsvector('english', 'The spiciest dosas in Pune');
SELECT to_tsvector('english', 'Masala Dosa') @@ websearch_to_tsquery('english', 'dosas');
SELECT to_tsquery('english', 'paneer tikka');   -- the error people meet first""", "sql") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>syntax error in tsquery</code>", "<code>to_tsquery</code> given text with spaces or symbols.", "<code>websearch_to_tsquery</code> for anything a person typed."],
    ["<code>cannot insert a non-DEFAULT value into column \"search\"</code>", "Code writing the generated column.", "Leave it out; PostgreSQL computes it."],
    ["<code>text-search query contains only stop words or doesn't contain lexemes, ignored</code> (a notice)", "Only stop words were searched.", "Expected; the result is empty."],
    ["The test's error message lacks the PostgreSQL text", "Spring's exception wraps it.", "Assert on the root cause. Found while building this station."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found (empty)", f"<code>DishContractTest</code> ({cnt('DishContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>LikeSearchTrapTest</code> ({cnt('LikeSearchTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>DishDatabaseTest</code> ({cnt('DishDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "LikeSearchTrapTest.java", "<p>Written first: what LIKE misses, what it reads, and the <code>to_tsquery</code> error.</p>"),
    (T + "DishDatabaseTest.java", "<p>Named constraints, the generated column, and a rolled-back menu.</p>"),
    (T + "DishContractTest.java", "<p>The endpoint through HTTP.</p>"),
    (T + "ApiTest.java", "<p>Shared setup and the EXPLAIN reader.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tiffino/dishes/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=MaxPriceChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Within budget", "Beginner-friendly", 20,
    "Add <code>maxPrice</code> in whole rupees: only dishes at or under it, still ranked. Negative is <code>400</code>.",
    "the test in <code>MaxPriceChallengeTest</code> passes.",
    ["One more condition on <code>price_paise</code>, bound as a parameter.", "Keep <code>DishSearch.SQL</code> as it is: the trap test runs it."],
    "challenge/MaxPriceChallengeTest.java", ["challenge/solution/DishSearch.java", "challenge/solution/DishController.java"]) + challenge(2, "Did you mean…", "Go deeper", 35,
    "When nothing matches, return <code>suggestions</code>: up to 5 dish names in the city that look like what was typed.",
    "both tests in <code>DidYouMeanChallengeTest</code> pass.",
    ["The <code>pg_trgm</code> extension compares three-letter pieces: <code>lower(name) % lower(:q)</code> and <code>similarity(…)</code>.",
     "Add <code>CREATE EXTENSION pg_trgm</code> and a GIN <code>gin_trgm_ops</code> index in a new migration.",
     "Found while building: that index on <code>lower(name)</code> also makes <code>lower(name) LIKE '%paneer%'</code> indexable."],
    "challenge/DidYouMeanChallengeTest.java", ["challenge/solution/V4__trigram_suggestions.sql", "challenge/solution/DishSearch.java", "challenge/solution/DishController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>When is a search engine worth it?</h2>
<p>Product wants Hindi and Marathi names, \"paneer\" to find \"cottage cheese\", typo tolerance everywhere, results boosted by popularity and distance, and suggestions as you type, on 3 million dishes. Which can PostgreSQL do (configurations, synonym dictionaries, pg_trgm), and which point to OpenSearch or Elasticsearch? What does keeping a second copy in sync cost, and how stale can a search result be?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, indexes"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: what LIKE misses and what it reads.</li>
<li>Add a weighted, generated <code>tsvector</code> column and a GIN index.</li>
<li>Parse with <code>websearch_to_tsquery</code>, match with <code>@@</code>, rank with <code>ts_rank</code>.</li>
<li>Prove the index is used with EXPLAIN, and test the limits (typos, stop words).</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Generated tsvector + GIN + websearch_to_tsquery", "One column and index; English only.", '<span class="pill ok">Chosen</span>'],
    ["<code>LIKE '%term%'</code>", "Misses forms and case; reads every row.", '<span class="pill bad">The trap</span>'],
    ["<code>ILIKE</code> + pg_trgm index", "Indexed and typo-friendly; no stemming or ranking by words.", '<span class="pill warn">Good for names</span>'],
    ["<code>to_tsvector(…)</code> in the query, expression index", "No extra column; every query must repeat the exact expression.", '<span class="pill warn">Works</span>'],
    ["A tsvector kept by app code or a trigger", "Easy to forget a path that changes the name.", '<span class="pill warn">Generated is simpler</span>'],
    ["OpenSearch / Elasticsearch", "A second store kept in sync.", '<span class="pill warn">For relevance at scale</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>search</code>", "<code>tsvector GENERATED ALWAYS AS (…) STORED</code>: name weight A, description weight B", "Always matches the current name and description."],
    ["<code>dishes_search</code>", "GIN on <code>search</code>", "Rows per word."],
    ["<code>dishes_city</code>", "B-tree on <code>city</code>", "Every search is in one city."],
    ["<code>dishes_city_shape</code>, <code>dishes_name_not_blank</code>, <code>dishes_price_range</code>", "CHECKs", "No impossible dishes from any writer."]]) + """
""" + code(read(M + "V1__dishes.sql"), "sql") + code(read(M + "V3__search_index.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Adding the column to a big table</dt><dd>A stored generated column rewrites the table when added. On 3 million rows, plan it: a new table and a backfill, or a maintenance window.</dd>
<dt>GIN and writes</dt><dd>GIN indexes are slower to update than B-trees; PostgreSQL batches new entries in a pending list (<code>fastupdate</code>), cleaned by vacuum.</dd>
<dt>Language</dt><dd>The <code>english</code> configuration stems English words. Indian dish names stem oddly or not at all; test with real menus.</dd>
<dt>Ranking cost</dt><dd><code>ts_rank</code> reads each match's vector. For a word in a million dishes, cap the work, for example rank only the first matches.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why can't LIKE '%term%' use a B-tree index?", "A B-tree is sorted from the first character; a leading wildcard gives no starting point, so every row must be checked. A trigram index can help; a B-tree cannot."),
    ("What are tsvector and tsquery?", "A tsvector is a document as normalised words with positions; a tsquery is words joined with AND, OR, NOT; @@ tests whether one matches the other."),
    ("to_tsquery, plainto_tsquery or websearch_to_tsquery?", "to_tsquery takes its own operator syntax and fails on plain text; plainto_tsquery ANDs all words; websearch_to_tsquery also understands quotes, -word and or, and never errors."),
    ("Why a GIN index?", "It maps each word to the rows containing it, so a search reads only those rows."),
    ("When do you need a search engine instead?", "Typo tolerance, synonyms, many languages, relevance tuning and facets at large scale: things PostgreSQL does only partly, at the cost of a second store kept in sync."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You read both saved plans."],
    ["Full-text", "Generated tsvector and websearch_to_tsquery.", "Weights and ranking."],
    ["Indexes", "GIN used, proved by EXPLAIN.", "Why the trigram index made LIKE indexable."],
    ["Limits", "Knows typos find nothing.", "Can argue for or against a search engine."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This station has no flawed version to review. Use this checklist on any text search:</p>
<ul class="rules">
<li>Is user text ever passed to <code>to_tsquery</code>?</li>
<li>Can the search vector drift from the text it describes?</li>
<li>Does an EXPLAIN show the index on realistic data?</li>
<li>Are the limits (typos, languages) tested and stated?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
