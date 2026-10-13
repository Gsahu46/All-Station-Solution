"""Station 013 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 13,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · LinkedHashMap (LRU) · virtual threads · MockMvc",
    "simulation": "Histories live in each server's memory. The trap test starts two real copies of the app on two ports and plays the load balancer itself. Product ids are just numbers: there is no catalogue.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/kartwala/recent/"
T = "src/test/java/com/kartwala/recent/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Cache", "A fast, limited store of things you are likely to need again.", "The few books on your desk, the rest on the shelf.", "Each user's last 10 products."),
    ("LRU (least recently used)", "When full, throw out what was used longest ago.", "Clearing the desk: the book untouched for weeks goes back first.", "The 11th product pushes out the oldest."),
    ("Access order", "A <code>LinkedHashMap</code> mode where every read or write moves the entry to the end.", "Putting a book on top of the pile each time you open it.", "<code>new LinkedHashMap&lt;&gt;(16, 0.75f, true)</code>"),
    ("Bounded memory", "A hard limit on how much a structure can hold.", "A desk only so big.", "10 products per user, 10,000 users per server."),
    ("Thread safety", "Correct even when many requests touch the same data at the same moment.", "One pen for the register, passed hand to hand.", "One lock (<code>synchronized</code>) around the store."),
    ("Load balancer", "Spreads requests across several servers.", "A receptionist sending visitors to any free counter.", "Two app servers in the trap test."),
    ("Sticky routing", "Sending the same user to the same server every time.", "Always seeing the same bank teller.", "The fix this station can make without new infrastructure."),
]
STORY = [
    ("Ravi browses phones on Kartwala", "The \"recently viewed\" strip shows what he looked at. Behind it, the server keeps every product every user ever opened, and its memory slowly fills up."),
    ("Kartwala adds a second server", "Now Ravi's views land on either server. Refresh, and the strip shows a different half of his history each time."),
    ("The fix", "Keep only the last 10 per user and at most 10,000 users per server, evicting the least recently used. Make the deployment route each user to one server, and say plainly that this memory is per server."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Memory inside one server is fast, limited and private to that server. Treat it as a cache with limits, never as the one shared truth.</p>

<h2>What are we building?</h2>
<p><code>POST /users/{id}/recently-viewed</code> records a view; <code>GET</code> returns the last 10 products, newest first, each once. Memory stays bounded, many requests at once stay correct, and the page is honest about what happens with several servers.</p>

<h2>An everyday analogy</h2>
<p>A chai stall owner remembers the last few orders of each regular. If a regular reorders, that order comes to the front of the owner's memory. When there are too many regulars to remember, the one who has not visited for longest is forgotten. And if the owner opens a second stall with a second person, that person remembers nothing of the first stall's customers unless each customer keeps going to the same stall.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>A view arrives</strong>. The store takes its one lock.</li>
<li><strong>The user's history</strong>, a small access-order map, puts the product at the end; viewing it again just moves it.</li>
<li><strong>If the history has 11</strong>, the least recently used product drops out. The same rule caps the number of users.</li>
<li><strong>The answer</strong> is a copy of the history, newest first.</li>
</ol>

<details class="qa check"><summary>Check yourself: why can't reads skip the lock, if they only read?</summary><p>In access order, reading is not only reading: <code>get</code> moves the entry to the end, which changes the map's links. Two threads doing that at once can corrupt the map. Every call, reads included, must hold the lock.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>Not a shared cache.</strong> Each server has its own memory; a restart forgets everything. Moving the history to Valkey, shared by all servers, is a later station.</li>
<li><strong>No login and no catalogue.</strong> User and product ids are just numbers.</li>
<li><strong>Limits are demo rules.</strong> 10 products and 10,000 users per server.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Kartwala</strong> (the marketplace from stations 003 and 009) shows a "recently viewed" strip. The first version kept every product a user ever opened, in a plain map that only grew; memory alarms started a few weeks after launch. When a second server was added for the sale, customers saw a different strip on every refresh.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> views of 101, 102, 103, <b>then</b> the history is 103, 102, 101.</li>
<li><b>Given</b> 101 viewed again, <b>then</b> it moves to the front and is listed once.</li>
<li><b>Given</b> an 11th product, <b>then</b> the least recently viewed one is dropped; a re-viewed old product is kept.</li>
<li><b>Given</b> more than 10,000 users on a server, <b>then</b> the least recently active user's history is dropped.</li>
<li><b>Given</b> 200 views by one user at the same moment, <b>then</b> every request succeeds and the history holds 10 distinct products.</li>
<li><b>Given</b> two servers and round-robin routing, <b>then</b> histories split (the trap); <b>given</b> routing by user, <b>then</b> one server holds the whole history.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>At most 10 products per user and 10,000 users per server (demo rules), least recently used out first.</li>
<li>Every operation on the store holds one lock; responses are copies.</li>
<li>User and product ids are positive numbers; anything else is <code>400</code>.</li>
<li>Deployment rule: with several servers, route by user id, and accept that a restart forgets histories.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Build an LRU cache with <code>LinkedHashMap</code> in access order and <code>removeEldestEntry</code>.</li>
<li>Bound every in-memory structure that grows with users.</li>
<li>Explain why access-order reads need a lock, and prove thread safety with a real parallel test.</li>
<li>Explain what per-server memory means behind a load balancer, and the options.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/users/{userId}/recently-viewed</code>", "Body <code>{\"productId\": 101}</code>. Records the view; returns the history."],
    ["<code>GET</code>", "<code>/users/{userId}/recently-viewed</code>", "The history: <code>userId</code>, <code>productIds</code> newest first (empty for a new user)."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "Recorded, or read"],
    ['<span class="pill warn">400</span>', "User id or product id not a positive number; missing product id"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, after viewing 101, 102 and 103. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-view-again", "Case 1: product 101 viewed again", "<b>Why:</b> in access order, putting 101 again moves it to the end, which the API lists first. Still three products."),
    ("02-after-eleven-products", "Case 2: after eleven different products", "<b>Why:</b> the history stops at 10. Product 102 was untouched the longest, so it went; 101 survived because it was viewed again."),
    ("03-new-user", "Case 3: a user with no views", "<b>Why:</b> an empty history is <code>200</code> with an empty list."),
    ("04-bad-user", "Case 4: user 0", "<b>Why:</b> ids are positive: <code>400</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Three views", "Newest first", "<code>viewsAreListedNewestFirst</code>"],
    ["The same product again", "Moves to the front, listed once", "<code>viewingAgainMovesTheProductToTheFrontWithoutADuplicate</code>"],
    ["11th product", "The oldest drops out", "<code>theEleventhProductPushesOutTheOldest</code>"],
    ["An old product re-viewed before the 11th", "Kept; the next oldest drops", "<code>reViewingAnOldProductSavesItFromEviction</code>"],
    ["Reading counts as using", "<code>get</code> saves an entry from eviction", "<code>theLeastRecentlyUsedEntryIsEvicted</code>"],
    ["10,005 users", "10,000 kept; the least recently active dropped", "<code>theServerKeepsAtMostMaxUsersAndDropsTheLeastRecentlyActive</code>"],
    ["A list kept by the caller", "Does not change later", "<code>aReturnedListDoesNotChangeAfterwards</code>"],
    ["Two users; a new user", "Separate; empty", "<code>usersHaveSeparateHistoriesAndANewUserHasNone</code>"],
    ["User 0, product -5, no product, user \"abc\"", "<code>400</code>", "<code>badInputIs400</code>"],
    ["200 views by one user at once", "All <code>200</code>; 10 distinct", "<code>twoHundredViewsByOneUserAtOnceLeaveTenDistinctProducts</code>"],
    ["1,000 mixed reads and writes for 50 users at once", "All <code>200</code>; limits hold", "<code>readsAndWritesForManyUsersAtOnceNeverBreakTheLimits</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Treating a per-server in-memory cache as shared: each server shows different history.</p>
<p>On one laptop, memory looks like "the" store. The trap test starts two real copies of the app and plays a round-robin load balancer: the first view lands on server A, the second on B, and each server shows half the history. The second test routes user 8 to the same server every time, and the history stays whole. That is the fix this station can make without new infrastructure; its limits (a restart forgets, adding a server moves users) are why a shared store comes in a later station.</p>
</div>
""" + code(read(T + "PerServerCacheTrapTest.java"), "java") + """
<h3>Measured while building: what the lock is worth</h3>
<p>With <code>synchronized</code> removed from the store, the 200-parallel-views test failed in 3 runs out of 3, with <code>ArrayIndexOutOfBoundsException</code> from inside the corrupted map. With only the read method unlocked ("reads are safe"), the same tests passed 5 runs out of 5, even though that version is broken by design. A race that tests do not catch is still a race; the rule is "every call holds the lock", not "the tests are green".</p>
"""

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "RecentlyViewedController.java", dwn("Two endpoints; validates ids.", "HTTP in one place.", "No API.")),
    (J + "RecentlyViewed.java", dwn("The store: a bounded LRU of users, each with a bounded LRU of products, behind one lock.",
        "Both limits make memory bounded whatever the traffic; one lock makes every operation safe.",
        "A plain map that grows forever, and races on access-order maps.",
        "<ul><li><code>list</code> returns a copy, so a caller's list never changes underneath it.</li><li>The class comment states the per-server limit: the next developer must see it.</li></ul>")),
    (J + "LruMap.java", dwn("A <code>LinkedHashMap</code> in access order that removes its eldest entry above a size.",
        "Ten lines give a correct LRU: the JDK already keeps the order.",
        "Hand-written linked lists and eviction code.",
        "<ul><li><code>true</code> in the constructor is access order; <code>false</code> (the default) is insertion order, where re-viewing moves nothing.</li><li><code>size() &gt; maxSize</code>, not <code>&gt;=</code>: the check runs after the new entry is added.</li></ul>")),
    ("src/main/resources/application.yaml", "<p>RFC 9457 problem bodies for every error.</p>"),
    (J + "RecentlyViewedApplication.java", "<p>Standard Spring Boot entry point.</p>"),
]
tree = """stations/013-recently-viewed-products-with-an-lru-cache/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/kartwala/recent/
│   ├── RecentlyViewedController.java   ├── RecentlyViewed.java   ├── LruMap.java
│   └── RecentlyViewedApplication.java
├── src/test/java/com/kartwala/recent/   (see Tests)
├── review/                   the flawed version (see Review)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""],
    ["Docker", "Not needed for this station", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests (the trap test starts two more servers on free ports)""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Virtual threads, used by the concurrency test, are in Java 21 and later.</p>
<h2>Try it yourself: two servers</h2>
<p>Start two copies on two ports, in two terminals, and view products on each:</p>
""" + code("""./mvnw spring-boot:run -Dspring-boot.run.arguments=--server.port=8081
./mvnw spring-boot:run -Dspring-boot.run.arguments=--server.port=8082

curl -X POST http://localhost:8081/users/7/recently-viewed -H "Content-Type: application/json" -d "@docs/view.json"
curl http://localhost:8081/users/7/recently-viewed     # [101]
curl http://localhost:8082/users/7/recently-viewed     # []  the other server has never seen it""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>Port 8081 was already in use</code>", "Something else uses the port.", "Pick other ports."],
    ["An empty history after a restart", "Memory does not survive restarts.", "Expected: see the trap."],
    ["<code>release version 25 not supported</code>", "Maven is using an older JDK.", "Point <code>JAVA_HOME</code> at JDK 25, or add <code>-Djava.version=21</code>."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "The test that reproduces the failure before the fix", "Real run output"],
                "Required tests come from the station's types. The validator fails a station that is missing any of them.") + """
<h2>Required tests for this station</h2>
<p>Station type: <span class="chip">Concurrency</span></p>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>RecentlyViewedContractTest</code> ({cnt('RecentlyViewedContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>PerServerCacheTrapTest</code> ({cnt('PerServerCacheTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Concurrency", "A real concurrency test that proves the invariant holds", f"<code>RecentlyViewedConcurrencyTest</code> ({cnt('RecentlyViewedConcurrencyTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "LRU rules and the user bound", f"<code>LruMapTest</code> ({cnt('LruMapTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="note">"Not found" here is a user with no history: <code>200</code> with an empty list.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "PerServerCacheTrapTest.java", "<p>Written first: two real servers, round robin against routing by user.</p>"),
    (T + "RecentlyViewedConcurrencyTest.java", "<p>200 and 1,000 requests released together on virtual threads; a 60-second timeout in case a broken map loops.</p>"),
    (T + "RecentlyViewedContractTest.java", "<p>Order, moves, eviction, separate users, bad input.</p>"),
    (T + "LruMapTest.java", "<p>Access order, the 10,000-user bound, copies.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app through MockMvc, empty history before each test.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/kartwala/recent/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=RemoveProductChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Remove a product from the strip", "Beginner-friendly", 20,
    "Add <code>DELETE /users/{userId}/recently-viewed/{productId}</code>: <code>204</code>, also when the product (or the user) was never there.",
    "both tests in <code>RemoveProductChallengeTest</code> pass, and the station's tests still pass.",
    ["Take the store's lock like every other method.",
     "Deleting what is not there gives the same result as deleting it: <code>204</code> (station 008)."],
    "challenge/RemoveProductChallengeTest.java", ["challenge/solution/RecentlyViewed.java", "challenge/solution/RecentlyViewedController.java"]) + challenge(2, "Forget views after 30 days", "Go deeper", 40,
    "Views older than 30 days should not be shown. Store when each product was viewed, and filter on read. Viewing again restarts the 30 days.",
    "both tests in <code>ExpiryChallengeTest</code> pass. The test brings its own movable clock.",
    ["Store an <code>Instant</code> instead of <code>Boolean.TRUE</code> as the map value.",
     "Inject a <code>Clock</code> bean so the test can move time; keep a no-argument constructor for the station's tests.",
     "Filtering on read is enough: old entries leave through the LRU limit anyway."],
    "challenge/ExpiryChallengeTest.java", ["challenge/solution/RecentlyViewed.java", "challenge/solution/RecentlyViewedApplication.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Moving the history out of the servers</h2>
<p>Kartwala will run 8 servers and restart them during deploys. Compare three designs: sticky routing (this station), a shared Valkey list per user (<code>LPUSH</code>, <code>LREM</code>, <code>LTRIM</code>), and keeping the history on the phone. For each: what is lost on a restart, what happens when two servers update the same user at once, and what it costs.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: two real servers, round robin, split history.</li>
<li>Write <code>LruMap</code>: access order plus <code>removeEldestEntry</code>.</li>
<li>Nest two of them: users, then products per user. Put one lock around every method.</li>
<li>Prove the lock with real parallel requests; prove the bounds with unit tests.</li>
<li>Write the deployment rule down where developers will read it: in the class comment and on this page.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Access-order <code>LinkedHashMap</code> + one lock", "One lock is a bottleneck at very high traffic on one server; fine here.", '<span class="pill ok">Chosen</span>'],
    ["<code>HashMap</code> of lists that only grow", "Memory grows forever.", '<span class="pill bad">Wrong</span>'],
    ["<code>ConcurrentHashMap</code> and no lock", "The outer map is safe, the per-user maps are not, and it has no size limit.", '<span class="pill bad">Wrong</span> (see Review)'],
    ["Caffeine cache", "A tested library with size limits, expiry and good concurrency; one more dependency.", '<span class="pill warn">At scale</span>'],
    ["Shared store (Valkey)", "Every server sees the same history and it survives restarts; another system to run.", '<span class="pill warn">Later station</span>']]) + """
<h2>Database design</h2>
<p>None. If history had to be kept for a long time, it would be a table of (user, product, viewed_at) with a job deleting old rows; a cache is the wrong place for data you cannot lose.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Memory</dt><dd>Worst case is 10,000 users × 10 products per server: about 100,000 small entries. Bounded, so it cannot cause a memory alarm on its own.</dd>
<dt>Concurrency</dt><dd>One lock serialises every request to the store. Each operation takes microseconds, so it is fine at this scale; at much higher traffic, use a concurrent cache library.</dd>
<dt>Reliability</dt><dd>Restarts and deploys forget histories. That is acceptable for a "recently viewed" strip, not for anything a customer would miss.</dd>
<dt>Scale</dt><dd>With several servers, route by user (sticky) or move the history to a shared store. Adding a server changes the routing, so some users see an empty strip once.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("How do you build an LRU cache in Java?", "LinkedHashMap with accessOrder = true and an override of removeEldestEntry that returns size() > max. Every get or put moves the entry to the end; the eldest is the least recently used."),
    ("Is a LinkedHashMap in access order safe to read from several threads?", "No. In access order, get() moves the entry, which changes the map's internal links. Every call needs a lock (or use a concurrent cache library)."),
    ("Why does ConcurrentHashMap not make this store thread-safe?", "It makes the outer map's own operations safe, but the per-user maps inside are ordinary LinkedHashMaps changed from many threads. It also has no size limit."),
    ("What happens to in-memory caches behind a load balancer?", "Each server has its own copy. Users see different data depending on which server they hit, and a restart empties it. Use sticky routing or a shared cache, and decide what losing it means."),
    ("How do you test thread safety?", "Release many real requests at the same moment (a latch and virtual threads), then check the invariants. Remember that a passing test does not prove the absence of races; the design must make races impossible."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can predict which tests the flawed version fails."],
    ["Concurrency", "Every method holds the lock.", "You can explain why a green test did not catch unlocked reads."],
    ["Design", "Two bounded LRUs.", "You can compare sticky routing with a shared cache."],
    ["Explanation", "Access order in one sentence.", "You can explain the trap to someone who has only ever run one server."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("<code>LinkedHashMap</code> in insertion order", "<code>super(16, 0.75f)</code> leaves access order off. Re-viewing a product does not move it, and the product the user just looked at can be the one evicted.", "<code>viewingAgainMovesTheProductToTheFrontWithoutADuplicate</code>, <code>reViewingAnOldProductSavesItFromEviction</code>, <code>theLeastRecentlyUsedEntryIsEvicted</code>."),
    ("Off by one in <code>removeEldestEntry</code>", "<code>size() &gt;= maxSize</code> runs after the new entry is added, so the map keeps 9, not 10.", "<code>theEleventhProductPushesOutTheOldest</code> (9 items) and the 200-parallel-views test, which expects 10."),
    ("\"ConcurrentHashMap makes it thread-safe\"", "The outer map is safe, but every user's history is a plain <code>LinkedHashMap</code> changed by many threads with no lock, and the outer map has no size limit at all.", "<code>theServerKeepsAtMostMaxUsersAndDropsTheLeastRecentlyActive</code> (10,005 users kept). The concurrency test failed too in our runs (see the table)."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>"Performance: removed the global lock, ConcurrentHashMap is thread-safe. Also simplified LruMap." Read both files and list every problem before opening the findings.</p>
<p class="path">review/RecentlyViewed.java</p>
""" + code(read("review/RecentlyViewed.java"), "java") + """
<p class="path">review/LruMap.java</p>
""" + code(read("review/LruMap.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the two flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">The trap test passes on the flawed version: it is about deployment, not about this code. Each test answers its own question.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
