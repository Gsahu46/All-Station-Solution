"""Station 066 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 66,
    "stack": "Spring Boot 4.1.1 · Java 25 · JdbcClient · keyset (seek) pagination · row-value comparison · opaque cursors · PostgreSQL 17 · Testcontainers",
    "simulation": "Authors and posts are generated demo data (100,000 posts), not Chaupal's. There is no login; the feed is one public feed.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/chaupal/feed/"
T = "src/test/java/com/chaupal/feed/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]
import re as _re
def scan_rows(name):
    """Rows the scan nodes of a saved plan produced (the lines with 'Scan'), as numbers."""
    return sum(int(m) for l in read("docs/captures/" + name).splitlines() if "Scan" in l for m in _re.findall(r"actual rows=(\d+)", l))
R_OFFSET, R_KEYSET = scan_rows("explain-offset.txt"), scan_rows("explain-keyset.txt")
DECODED = read("docs/captures/cursor-decoded.txt").strip()

# ---------- Level 1: Understand ----------
TERMS = [
    ("Offset paging", "\"Skip the first N, give me the next 20.\"", "Counting 40,000 envelopes to reach the 40,001st.", "the old feed: <code>OFFSET</code>"),
    ("Keyset (seek) paging", "\"Give me the 20 that come after this one.\"", "A bookmark: open the book where you stopped.", "<code>WHERE (created_at, id) &lt; (…)</code>"),
    ("Cursor", "A token saying where the last page stopped.", "The bookmark itself.", "<code>nextCursor</code>"),
    ("Opaque", "Clients pass it back unchanged and do not read it.", "A cloakroom token: you hand it back, you do not decode it.", "base64url of <code>" + DECODED.replace("<", "&lt;") + "</code>"),
    ("Tie-breaking", "A second key for rows with the same first key.", "Two posts in the same second, told apart by id.", "<code>id</code> after <code>created_at</code>"),
    ("Row-value comparison", "Comparing several columns at once, in order.", "Compare dates; if equal, compare numbers.", "<code>(created_at, id) &lt; (:t, :id)</code>"),
]
STORY = [
    ("Scrolling the feed", "A Chaupal user scrolls for a long time. Each new page is \"skip N posts, show 20\"."),
    ("Slower and repeating", "Page 2,000 has to read and discard 40,000 posts first: four seconds. And when friends post while the user reads page 1, every post moves down: the bottom of page 1 shows up again at the top of page 2."),
    ("The fix", "Each page says where it stopped: the last post's time and id. The next page asks for posts older than that one, which the index finds directly, whatever was posted in between."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Page by position in the data, not by counting rows.</p>

<h2>What are we building?</h2>
<p><code>GET /feed</code> returns the newest posts and a <code>nextCursor</code>; <code>GET /feed?cursor=…</code> continues from there, at the same speed on page 2 and page 2,000.</p>

<h2>An everyday analogy</h2>
<p>Reading a long newspaper archive. Offset paging is \"start from the first issue and count 40,000 pages\". Keyset paging is a bookmark: \"the issue after 1 October, 05:33\", and you open it there.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>First page</strong>: the newest posts, one more than asked.</li>
<li><strong>If there is that extra post</strong>, there is a next page: the cursor is the last shown post's time and id.</li>
<li><strong>Next page</strong>: posts older than the cursor's post, in the same order, straight from the index.</li>
<li><strong>The end</strong>: fewer posts than asked, and no cursor.</li>
</ol>

<details class="qa check"><summary>Check yourself: why does the cursor need the id, and not just the time?</summary><p>Five posts can share one second. If page 1 ends at the second of those five, \"older than this time\" skips the other four. \"Older than (this time, this id)\" continues with them. The test shows the four lost posts.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No personal feed.</strong> One public feed; following people is a filter (Practice 1).</li>
<li><strong>No ranking.</strong> Newest first only.</li>
<li><strong>No page numbers.</strong> Keyset paging cannot jump to page 517, by design.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Chaupal</strong> (a fictional social app) pages its feed with <code>OFFSET</code>. Page 2,000 takes 4 seconds, and new posts push duplicates onto the next page.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo data: 100,000 posts, five per second, from 1 October 2026 00:00 UTC.</p>
<ol class="gwt">
<li><b>Given</b> no cursor, <b>then</b> posts 100000 down to 99981 and a <code>nextCursor</code>.</li>
<li><b>Given</b> that cursor, <b>then</b> the next posts with no gap and no repeat, even if posts were added meanwhile.</li>
<li><b>Given</b> a page boundary inside one second, <b>then</b> the posts sharing that second still appear.</li>
<li><b>Given</b> the last page, <b>then</b> <code>nextCursor</code> is <code>null</code>; a cursor past the oldest post gives an empty page.</li>
<li><b>Given</b> a cursor this feed did not make, or a limit outside 1 to 50, <b>then</b> <code>400</code>.</li>
<li><b>Given</b> page 2,000, <b>then</b> the database reads about one page of rows, not 40,000.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Order by <code>(created_at, id)</code>, both descending, everywhere.</li>
<li>The cursor holds both values; it is opaque and versioned.</li>
<li>No count query: one extra row tells whether more follow.</li>
<li>An index matches the order.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Measure what <code>OFFSET</code> costs.</li>
<li>Write a keyset page with a row-value comparison.</li>
<li>Design an opaque cursor with a tie-breaker.</li>
<li>Know what keyset paging cannot do.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/feed?limit=20</code>", "The newest posts: <code>{posts: [{id, author, body, createdAt}], nextCursor}</code>."],
    ["<code>GET</code>", "<code>/feed?cursor=…&amp;limit=20</code>", "The posts after the cursor; <code>nextCursor</code> is <code>null</code> at the end."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "A page, possibly empty"],
    ['<span class="pill warn">400</span>', "A cursor this feed did not issue; a limit outside 1 to 50"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-the-newest-three", "Case 1: the newest three", "<b>Why:</b> the first page and its cursor."),
    ("02-the-next-three", "Case 2: the cursor from case 1", "<b>Why:</b> straight on, with the id deciding inside a second."),
    ("03-a-cursor-that-is-not-ours", "Case 3: a made-up cursor", "<b>Why:</b> <code>400</code>, telling the client to start again."),
    ("04-a-limit-of-500", "Case 4: limit 500", "<b>Why:</b> <code>400</code>; at most 50."),
]) + """
<p>The cursor in case 1 decodes to <code>""" + e(DECODED) + """</code>: version, the post's time in microseconds since 1970, and its id. Clients must not build or change it; the version lets the server change its contents later.</p>"""

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["The first page", "The newest 20 and a cursor", "<code>theFirstPageIsTheNewestPosts</code>"],
    ["A boundary inside one second", "The id continues the order", "<code>theCursorContinuesExactlyWhereThePageStopped</code>"],
    ["Nineteen pages in a row; the last page", "Each post once; no cursor at the end", "<code>walkingTheLastThousandPostsShowsEachOnceAndEndsWithNoCursor</code>"],
    ["A cursor past the oldest post", "Empty page", "<code>aCursorPastTheOldestPostIsAnEmptyPage</code>"],
    ["A foreign or old-style cursor; a bad limit", "<code>400</code>", "<code>aCursorThatIsNotOursOrABadLimitIs400</code>"],
    ["Posts added while reading", "Offset repeats; keyset does not", "<code>newPostsPushRepeatsOntoTheNextOffsetPage</code>"],
    ["Bad rows; a half-added author", "Refused; rolled back", "<code>PostDatabaseTest</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Deep <code>OFFSET</code> paging that gets slower page by page and duplicates new posts.</p>
<ul>
<li><strong>Slower.</strong> <code>OFFSET 40000</code> means reading 40,000 rows in order and throwing them away. In the captured plans, the scans produced """ + f"{R_OFFSET:,}" + """ rows for the offset page and """ + f"{R_KEYSET:,}" + """ for the keyset page (including the one-row lookup of the cursor's post).</li>
<li><strong>Repeats.</strong> Three new posts move everything down by three. Page 2 by offset starts with the last three posts of page 1; the keyset page starts after the last post the reader saw.</li>
<li><strong>The first cursor people write.</strong> \"Older than this time\" skips the posts that share the last post's second. Here, four of them.</li>
</ul>
<p>While building, each fix was undone once: dropping the id from the cursor turned 4 tests red; not fetching the extra row 5; accepting any decoded text as a cursor 1; dropping the index 1.</p>
</div>
""" + code(read("docs/captures/explain-offset.txt").rstrip(), "text") + code(read("docs/captures/explain-keyset.txt").rstrip(), "text") + code(read(T + "OffsetPagingTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "FeedController.java", dwn("Checks the limit and decodes the cursor.",
        "A bad cursor is a <code>400</code> before any query.",
        "A garbage cursor reaching SQL.")),
    (J + "Cursor.java", dwn("Encodes and decodes the position: version, time in microseconds, id.",
        "Opaque and versioned; parsed strictly.",
        "Clients building offsets or timestamps themselves.",
        "<ul><li>Microseconds, because PostgreSQL stores <code>timestamptz</code> to the microsecond: a millisecond cursor would round and skip or repeat posts.</li><li>Not signed: a client can decode it, and can only ask for a position it could reach by scrolling.</li></ul>")),
    (J + "Feed.java", dwn("The first page and the seek, one row more than asked.",
        "The row-value comparison matches the index's order, so the page starts where the cursor points.",
        "<code>OFFSET</code>, and a count query to know about the next page.")),
    (M + "V1__posts.sql", dwn("Tables, named constraints and the feed index.",
        "<code>posts_feed (created_at, id)</code> read backwards is the feed.",
        "A sort of every post for every page.")),
    (M + "V2__demo_posts.sql", "<p>4 authors and 100,000 posts, five per second.</p>"),
    ("src/main/resources/application.yaml", "<p>Problem details on.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "FeedApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/066-social-feed-with-keyset-pagination/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/chaupal/feed/
│   ├── FeedController.java   ├── Cursor.java   ├── Feed.java   └── FeedApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__posts.sql, V2__demo_posts.sql
├── src/test/java/com/chaupal/feed/   (see Tests)
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
./mvnw spring-boot:run      # the API on http://localhost:8080; the first start loads 100,000 posts
./mvnw test                 # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Follow the cursors by hand (needs <code>jq</code>), then compare with a deep offset in <code>psql</code>:</p>
""" + code("""C=$(curl -s 'http://localhost:8080/feed?limit=3' | jq -r .nextCursor)
curl -s "http://localhost:8080/feed?limit=3&cursor=$C" | jq '.posts[].id'
docker compose exec postgres psql -U chaupal -d chaupal \\
  -c "EXPLAIN ANALYZE SELECT id FROM posts ORDER BY created_at DESC, id DESC LIMIT 20 OFFSET 90000\"""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Posts skipped at page boundaries", "A cursor without the id, or a time rounded to milliseconds.", "Keep both, and the full microseconds."],
    ["The seek query does a full sort", "No index matching <code>(created_at, id)</code>, or the comparison written as two separate conditions.", "One row-value comparison and a two-column index."],
    ["<code>400 Not a cursor from this feed</code> after a release", "The cursor format changed.", "Keep reading the old version, or let clients start again: the message says so."],
    ["Different results with the time zone", "Binding a local timestamp against <code>timestamptz</code>.", "Bind <code>OffsetDateTime</code> in UTC, as <code>Feed</code> does."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found (empty page)", f"<code>FeedContractTest</code> ({cnt('FeedContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>OffsetPagingTrapTest</code> ({cnt('OffsetPagingTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>PostDatabaseTest</code> ({cnt('PostDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "OffsetPagingTrapTest.java", "<p>Written first: the cost of offset, repeats under new posts, and the time-only cursor.</p>"),
    (T + "PostDatabaseTest.java", "<p>Named constraints, the database's timestamp, and a rolled-back author.</p>"),
    (T + "FeedContractTest.java", "<p>The endpoint through HTTP, following real cursors.</p>"),
    (T + "ApiTest.java", "<p>Shared setup, the EXPLAIN row counter and a feed helper.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/chaupal/feed/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=AuthorFeedChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "One author's posts", "Beginner-friendly", 25,
    "Add <code>author=kabir</code>: that author's posts, newest first, with the same cursor. Unknown author: <code>404</code>.",
    "both tests in <code>AuthorFeedChallengeTest</code> pass.",
    ["One more condition, <code>p.author_id = :author</code>, in both queries.",
     "For speed at scale, an index on <code>(author_id, created_at, id)</code>; not needed for the test."],
    "challenge/AuthorFeedChallengeTest.java", ["challenge/solution/Feed.java", "challenge/solution/FeedController.java"]) + challenge(2, "Pull to refresh", "Go deeper", 30,
    "Every page also returns <code>topCursor</code> (its first post). <code>GET /feed/new?cursor=…</code> returns the posts made since, newest first.",
    "the test in <code>PullToRefreshChallengeTest</code> passes.",
    ["Seek the other way: <code>(created_at, id) &gt; (:t, :id)</code>, ordered ascending so the limit keeps the posts right after the cursor; then reverse.",
     "A record can get a second constructor that fills <code>topCursor</code> from the first post."],
    "challenge/PullToRefreshChallengeTest.java", ["challenge/solution/Feed.java", "challenge/solution/FeedController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Should the cursor be signed?</h2>
<p>Anyone can decode the cursor and write their own. Here that only lets them start at any point in a public feed. When would it matter: a feed of private posts, a cursor that also carries filters or a user id, a cursor that expires? Compare an HMAC-signed cursor, an encrypted one, and a server-side cursor id stored for a few minutes.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, indexes"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the cost of a deep offset, repeats under new posts, and a time-only cursor.</li>
<li>Pick the order <code>(created_at, id)</code> and an index for it.</li>
<li>Seek with a row-value comparison; fetch one extra row.</li>
<li>Encode the position in an opaque, versioned cursor, parsed strictly.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Keyset on (created_at, id), opaque cursor", "No page numbers, no jumping.", '<span class="pill ok">Chosen</span>'],
    ["<code>OFFSET</code>", "Slower each page; repeats and gaps under inserts.", '<span class="pill bad">The trap</span>'],
    ["Cursor on time only", "Skips posts sharing a timestamp.", '<span class="pill bad">The trap, version 2</span>'],
    ["Cursor on id only", "Correct only if ids follow time exactly, which imports and clock skew break.", '<span class="pill warn">Fragile</span>'],
    ["Two conditions instead of a row value: <code>created_at &lt; t OR (created_at = t AND id &lt; i)</code>", "Same result; easier to get wrong; may plan worse.", '<span class="pill warn">Works</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>posts_feed</code>", "B-tree <code>(created_at, id)</code>", "The feed order, read backwards; the seek starts inside it."],
    ["<code>created_at</code>", "<code>timestamptz</code>, default <code>now()</code>", "The database's clock, to the microsecond."],
    ["<code>posts_author_fk</code>, <code>posts_body_not_blank</code>, <code>authors_handle_unique</code>, <code>authors_handle_shape</code>", "Constraints", "No orphan or empty posts."]]) + """
""" + code(read(M + "V1__posts.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Deleted posts</dt><dd>A cursor still works if its post is deleted: it is a position, not a lookup.</dd>
<dt>Edits</dt><dd>Ordering by a column that changes (\"updated at\") moves posts between pages; order by something that never changes.</dd>
<dt>Clocks</dt><dd>With several app servers, use the database's <code>now()</code> (as here), not each server's clock.</dd>
<dt>Caching</dt><dd>The first page changes constantly; later pages by cursor barely do, and cache well.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why does OFFSET get slower?", "The database must produce and discard every skipped row in order; page N costs N × page size rows."),
    ("What is keyset pagination?", "The next page is \"rows after this key\" in a fixed order, answered by an index seek; its cost does not grow with depth."),
    ("Why include the id in the cursor?", "To break ties: several rows can share a timestamp, and the cursor must name exactly one position."),
    ("Why make the cursor opaque?", "Clients cannot depend on its contents, so the server can change them; it also stops clients building offsets."),
    ("What does keyset pagination give up?", "Jumping to page N and showing \"page 3 of 100\"; it suits feeds and exports, not numbered admin lists."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You read both saved plans."],
    ["Keyset", "Row-value seek and a matching index.", "Why microseconds matter."],
    ["Cursors", "Opaque, with a tie-breaker.", "When to sign them."],
    ["Trade-offs", "Knows the cost of OFFSET.", "Knows what keyset cannot do."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This station has no flawed version to review. Use this checklist on any feed or export:</p>
<ul class="rules">
<li>Does any page use <code>OFFSET</code> on a list that grows or changes?</li>
<li>Does the cursor hold every column of the order, including a unique one?</li>
<li>Does an index match the order, in the same column order?</li>
<li>Is the cursor parsed strictly, and does a bad one give a <code>400</code>?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
