"""Station 010 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 10,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · HashMap · recursion with a limit · MockMvc",
    "simulation": "Three posts are fixed in the code: a normal discussion, one reply chain 100,000 comments deep (a bot replying to itself), and an empty post. Everything is in memory.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/chaupal/threads/"
T = "src/test/java/com/chaupal/threads/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Flat list", "Every comment stored side by side, each with the id of the comment it answers.", "A pile of letters, each saying \"in reply to letter 4\".", "<code>parentId</code> on each comment."),
    ("Tree", "Comments nested inside the comments they answer.", "A family tree.", "<code>replies</code> inside each node."),
    ("Map lookup by parent id", "Group replies by the comment they answer, once, so finding them later is instant.", "Sorting letters into folders by \"in reply to\".", "<code>Map&lt;Long, List&lt;Comment&gt;&gt;</code>"),
    ("Recursion", "A method that calls itself for a smaller piece of the problem.", "Opening a box to find a smaller box inside.", "Building each node's replies."),
    ("Stack overflow", "The crash when recursion goes deeper than the thread's memory for method calls allows.", "Boxes nested so deep you run out of hands.", "<code>StackOverflowError</code> on the 100,000-deep thread."),
    ("Depth limit", "Stop nesting after N levels and show \"n more replies\" instead.", "\"Continue this thread →\" on forums.", "<code>maxDepth</code>, 1 to 10."),
    ("Siblings", "Replies to the same comment.", "Children of the same parents.", "Ordered oldest first, then by id."),
]
STORY = [
    ("Comments are stored flat", "Each reply just remembers which comment it answers. The app showed them in storage order, so replies sometimes appeared above the comment they answered."),
    ("A bot replies to itself 100,000 times", "The new \"nested replies\" feature built the tree with recursion that went as deep as the data. On that thread the server ran out of stack and every reader got an error page."),
    ("The fix", "Group replies by parent with one map, nest them up to a depth limit, and below the limit only count them, without recursion."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Data from users has no natural limits. Any code whose depth or size follows the data needs a limit of its own.</p>

<h2>What are we building?</h2>
<p><code>GET /posts/{id}/comment-tree?maxDepth=5</code>: the post's comments as a tree, replies under the comment they answer, oldest first. Below <code>maxDepth</code>, replies are not nested; the last shown comment says how many are hidden.</p>

<h2>An everyday analogy</h2>
<p>A wedding invitation list grows as "Sharma family → Rahul's family → Rahul's cousins → …". To print it, you first sort every name into a folder labelled with whose guest they are. Then you print a few levels deep and write "+ 37 more" for the rest, instead of following every branch to the end.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Group</strong>: one pass over the comments puts each into a map under its parent's id. Top-level comments, and replies whose parent is missing, go in a separate list.</li>
<li><strong>Sort</strong> each group oldest first (ties by id).</li>
<li><strong>Nest</strong> from the top, one level at a time, up to <code>maxDepth</code> levels.</li>
<li><strong>Count</strong> what is below the last level with a loop and a to-do list, not recursion: <code>moreReplies</code>.</li>
</ol>

<details class="qa check"><summary>Check yourself: recursion is used in step 3 too. Why is that safe and step 4 not?</summary><p>Step 3 stops at <code>maxDepth</code>, at most 10 levels, whatever the data. Step 4 must go all the way down, and that depth comes from the data: 100,000 on post 2. So step 4 uses a loop with its own list of comments still to visit.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No database.</strong> Comments are fixed in memory; post 2's chain is generated at start-up.</li>
<li><strong>No posting.</strong> Station 007 covers adding comments safely.</li>
<li><strong>No paging of wide threads.</strong> A comment with 5,000 replies returns all 5,000.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Chaupal</strong> (the forum from station 007) stores comments flat. Its app showed them in storage order, so replies sometimes came before the comments they answered. The first version of "nested replies" fixed the order but crashed on a thread where a misconfigured bot had replied to itself 100,000 times: the recursive builder threw <code>StackOverflowError</code> and the post became unreadable for everyone.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a post, <b>then</b> top-level comments come oldest first, and each reply sits under the comment it answers, oldest first; equal times are ordered by id.</li>
<li><b>Given</b> <code>maxDepth=N</code>, <b>then</b> at most N levels are nested; a comment on level N has empty <code>replies</code> and <code>moreReplies</code> = the number of comments below it.</li>
<li><b>Given</b> the 100,000-deep thread, <b>then</b> <code>200</code>, quickly, with <code>moreReplies</code> counting the rest.</li>
<li><b>Given</b> a reply whose parent is gone, <b>then</b> it is shown at the top level. <b>Given</b> comments in a loop (corrupt data), <b>then</b> the request still finishes.</li>
<li><b>Given</b> <code>maxDepth</code> outside 1–10, <b>then</b> <code>400</code>. <b>Given</b> an unknown post, <b>then</b> <code>404</code>. <b>Given</b> a post with no comments, <b>then</b> an empty list.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>One pass to group by parent id; no searching the list for each comment's replies.</li>
<li>No recursion whose depth depends on the data.</li>
<li><code>maxDepth</code>: default 5, 1 to 10.</li>
<li>Errors are RFC 9457 problems.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Build a tree from a flat list with a map from parent id to children.</li>
<li>Order siblings with a comparator and a tie-breaker.</li>
<li>Explain why unbounded recursion fails on user data, and bound it.</li>
<li>Rewrite a recursive count as a loop with an explicit stack.</li>
<li>Handle broken data: missing parents and loops.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [["<code>GET</code>", "<code>/posts/{postId}/comment-tree?maxDepth</code>", "The post's comments as a tree, up to <code>maxDepth</code> levels (default 5, 1–10)."]]) + """
<h2>Each node</h2>
""" + table(["Field", "Meaning"], [
    ["<code>id</code>, <code>author</code>, <code>text</code>, <code>createdAt</code>", "The comment."],
    ["<code>replies</code>", "Its replies, oldest first, each a node of the same shape. Empty at the depth limit."],
    ["<code>moreReplies</code>", "How many comments are below this one but not shown (0 above the limit)."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "The post exists (an empty <code>comments</code> list if it has none)"],
    ['<span class="pill warn">400</span>', "<code>maxDepth</code> outside 1–10, or not a number"],
    ['<span class="pill warn">404</span>', "No such post"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-tree", "Case 1: the chai discussion", "<b>Why:</b> two top-level comments; the deepest reply (\"Closed on Mondays\") is 5 levels down, within the default limit. Comments 2 and 3 were posted in the same minute, so they are ordered by id."),
    ("02-depth-2", "Case 2: only two levels", "<b>Why:</b> level-2 comments show no replies, and <code>moreReplies</code> says how many are hidden below each."),
    ("03-deep-thread", "Case 3: the 100,000-deep thread", "<b>Why:</b> three levels are nested, then the rest is counted with a loop: <code>moreReplies: 99997</code>. No stack overflow, no error page."),
    ("04-too-deep", "Case 4: maxDepth=1000", "<b>Why:</b> the limit is part of the contract; a client cannot switch it off. <code>400</code>."),
    ("05-unknown-post", "Case 5: unknown post", "<b>Why:</b> <code>404</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Normal thread", "Nested, oldest first, ties by id", "<code>repliesAreNestedUnderTheCommentTheyAnswerOldestFirst</code>, <code>siblingsAreOldestFirstThenById</code>"],
    ["Depth limit", "Replies counted, not shown", "<code>atTheDepthLimitRepliesAreCountedNotShown</code>, <code>maxDepthOneShowsOnlyTopLevelComments</code>"],
    ["100,000-deep thread over HTTP", "<code>200</code>, <code>moreReplies: 99997</code>", "<code>theRealEndpointStopsAtTheDepthLimitAndCountsWhatIsBelow</code>"],
    ["Counting 100,000 levels directly", "No recursion, no overflow", "<code>countingBelowAHundredThousandLevelsUsesNoRecursion</code>"],
    ["5,000 replies to one comment", "All kept", "<code>aWideThreadKeepsEveryReply</code>"],
    ["Parent deleted", "Reply shown at the top", "<code>aReplyWhoseParentIsGoneIsShownAtTheTop</code>"],
    ["Comments in a loop; a comment replying to itself", "Finishes in time; loop left out", "<code>commentsInALoopDoNotHangTheBuilder</code>"],
    ["No comments", "Empty list", "<code>aPostWithNoCommentsIsAnEmptyTree</code>"],
    ["maxDepth 0, 11, 100000, -1, \"deep\"", "<code>400</code>", "<code>maxDepthOutsideOneToTenIs400</code>"],
    ["Unknown post", "<code>404</code>", "<code>anUnknownPostIs404</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Unbounded recursion on deep threads, crashing with <code>StackOverflowError</code>.</p>
<p>"A node's replies are the nodes of its children" is a beautiful three-line method, and every normal thread works. The first test runs it on post 2: <code>StackOverflowError</code>. In a controller that is a <code>500</code> for every reader of the post. The second test asks the real endpoint for the same thread and gets an answer. Rewriting <code>countBelow</code> recursively was tried while building: 2 tests went red with <code>StackOverflowError</code>.</p>
</div>
""" + code(read(T + "UnboundedRecursionTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "CommentTreeController.java", dwn("Reads <code>maxDepth</code> (1–10), finds the post, and returns the tree.",
        "The limit is checked at the door, so no request can ask for unlimited depth.",
        "No endpoint; without the cap, <code>maxDepth=100000</code> would bring the overflow back.")),
    (J + "ThreadBuilder.java", dwn("Groups comments by parent id, sorts siblings, nests up to <code>maxDepth</code>, and counts the rest with a loop.",
        "Each step has a cost that does not depend on how deep users go.",
        "The trap.",
        "<ul><li>Replies whose parent is missing become top-level comments, so nothing is silently lost.</li><li><code>countBelow</code> keeps its own to-do list (<code>ArrayDeque</code>) instead of using the call stack.</li><li>Comments in a loop never have a top-level ancestor, so they are never visited and cannot hang the request.</li></ul>")),
    (J + "CommentStore.java", dwn("The three posts. Post 1 is stored newest first on purpose; post 2's chain is generated.",
        "Realistic and hostile data in one place.", "Nothing to show.")),
    (J + "Comment.java", "<p>A stored comment, with <code>parentId</code> (null at the top).</p>"),
    (J + "Node.java", "<p>A comment in the tree, with <code>replies</code> and <code>moreReplies</code>.</p>"),
    (J + "ApiErrors.java", "<p>Adds an <code>errors</code> map to parameter validation failures (as in station 002).</p>"),
    (J + "ThreadsApplication.java", "<p>Standard Spring Boot entry point.</p>"),
]
tree = """stations/010-threaded-comment-replies/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/chaupal/threads/
│   ├── CommentTreeController.java   ├── ThreadBuilder.java   ├── CommentStore.java
│   ├── Comment.java                 ├── Node.java            ├── ApiErrors.java
│   └── ThreadsApplication.java
├── src/test/java/com/chaupal/threads/   (see Tests)
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
./mvnw test                 # all """ + str(N_TESTS) + """ tests""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
""" + code("""curl "http://localhost:8080/posts/1/comment-tree"
curl "http://localhost:8080/posts/1/comment-tree?maxDepth=2"

# The thread that crashed the old code: expect "moreReplies":99997
curl "http://localhost:8080/posts/2/comment-tree?maxDepth=3\"""", "bash") + """
<p>Then copy the trap test's <code>naive</code> method into a scratch class and call it on post 2 yourself: seeing the <code>StackOverflowError</code> once makes the lesson stick.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>400</code>", "<code>maxDepth</code> outside 1–10.", "Use a value from 1 to 10."],
    ["Only part of the URL is used", "The shell cut at <code>?</code> or <code>&amp;</code>.", "Put the URL in double quotes."],
    ["<code>release version 25 not supported</code>", "Maven is using an older JDK.", "Point <code>JAVA_HOME</code> at JDK 25, or add <code>-Djava.version=21</code>."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>CommentTreeContractTest</code> ({cnt('CommentTreeContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>UnboundedRecursionTrapTest</code> ({cnt('UnboundedRecursionTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "The builder on broken, deep and wide data", f"<code>ThreadBuilderTest</code> ({cnt('ThreadBuilderTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "UnboundedRecursionTrapTest.java", "<p>Written first: the naive builder overflows on post 2; the endpoint answers.</p>"),
    (T + "CommentTreeContractTest.java", "<p>Shape, order, depth limits and every refusal.</p>"),
    (T + "ThreadBuilderTest.java", "<p>Missing parents, loops (with a 2-second timeout), ties, 100,000 deep, 5,000 wide.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app through MockMvc.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/chaupal/threads/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=TotalRepliesChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "\"12 replies\" on every comment", "Beginner-friendly", 25,
    "Add <code>totalReplies</code> to every node: all comments below it at any depth, shown or not. It must work on the 100,000-deep thread.",
    "both tests in <code>TotalRepliesChallengeTest</code> pass, and the station's tests still pass.",
    ["<code>countBelow</code> already counts without recursion; call it for every node you build.",
     "Adding a field to the <code>Node</code> record breaks <code>new Node(...)</code> calls in the tests: keep a six-argument constructor.",
     "Notice the cost: a node and its parent count the same comments again. Fine for 10 levels; think about it for larger trees."],
    "challenge/TotalRepliesChallengeTest.java", ["challenge/solution/Node.java", "challenge/solution/ThreadBuilder.java"]) + challenge(2, "Continue this thread", "Go deeper", 30,
    "Behind \"moreReplies\" the app shows \"Continue this thread\". Add an optional <code>rootId</code>: the tree then starts at that comment. An unknown comment, or one from another post, is <code>404</code>.",
    "all three tests in <code>ContinueThreadChallengeTest</code> pass.",
    ["The grouping by parent does not change; only the starting point does.",
     "Look the root up in this post's comments only, or one post could read another's thread."],
    "challenge/ContinueThreadChallengeTest.java", ["challenge/solution/ThreadBuilder.java", "challenge/solution/CommentTreeController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>A post with 2 lakh comments</h2>
<p>A viral post has 2 lakh comments. Loading all of them for every reader to build a 5-level tree is wasteful. Which comments would you load first, and how would you page through top-level comments? How could a database help (for example, storing each comment's depth and its top-level ancestor)? What would "continue this thread" load?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the naive recursive builder overflows on 100,000 levels.</li>
<li>Group by parent id in one pass; treat missing parents as top level.</li>
<li>Sort siblings with a comparator and a tie-breaker.</li>
<li>Nest with recursion capped by <code>maxDepth</code>; count below the cap with a loop.</li>
<li>Test broken data: missing parents and loops.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Map by parent id, capped nesting, iterative counting", "One pass to group; work below the cap is a loop.", '<span class="pill ok">Chosen</span>'],
    ["Recursion as deep as the data", "<code>StackOverflowError</code> on deep threads (the trap).", '<span class="pill bad">Wrong</span>'],
    ["For each comment, search the list for its replies", "Correct but O(n²): 100,000 comments means 10 billion comparisons.", '<span class="pill bad">Too slow</span>'],
    ["Increase the thread stack size (<code>-Xss</code>)", "Moves the crash further away; a deeper thread still crashes, and every thread pays the memory.", '<span class="pill bad">Not a fix</span>'],
    ["Return the flat list; let the app build the tree", "Moves the same problem to every client, on weaker devices.", '<span class="pill warn">Possible</span>'],
    ["Recursive SQL (<code>WITH RECURSIVE</code>) with a depth column", "The database does the walk and can stop at a depth; the right tool once comments are in a database.", '<span class="pill warn">Later stations</span>']]) + """
<h2>Database design</h2>
<p>None in this station. A table would have <code>id</code>, <code>post_id</code>, <code>parent_id</code> (nullable, foreign key to <code>id</code>), <code>created_at</code>, and an index on <code>(post_id, parent_id, created_at)</code> so each group of siblings comes back already sorted.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Reliability</dt><dd>One hostile thread must not make a post unreadable. Every loop or recursion that follows user data needs a limit, and a test at that limit.</dd>
<dt>Performance</dt><dd>Grouping is one pass; nesting is bounded. Very wide threads (thousands of replies to one comment) are the next limit: page them.</dd>
<dt>Security</dt><dd>A depth or size parameter is an attack surface: the cap of 10 is enforced by the server, whatever the client asks.</dd>
<dt>Data quality</dt><dd>Missing parents and loops are real in old data. Show what you can, never hang, and log loops for someone to repair.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("How do you build a tree from a flat list of (id, parentId)?", "One pass to group children by parentId in a HashMap; roots are those with no parent (or a missing one). Then walk from the roots, looking up each node's children in the map. O(n) to group, instead of O(n²) searching."),
    ("Why did the recursive version crash?", "Each recursive call uses a stack frame. The JVM thread stack is limited (often around 1 MB), so tens of thousands of nested calls exceed it and throw StackOverflowError. The depth came from user data, so it had no limit."),
    ("How do you turn recursion into a loop?", "Keep your own stack (an ArrayDeque) of work still to do. Pop one item, process it, push its children. The depth now lives in heap memory, which is much larger, instead of the call stack."),
    ("Why still use recursion for nesting?", "Because its depth is capped by maxDepth (at most 10), not by the data. Bounded recursion is fine and easier to read."),
    ("What can go wrong with real comment data?", "Parents deleted (orphans), loops from bad migrations or bugs, and very wide or deep threads. Decide what to show for each and test it."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can say which tests fail with a recursive <code>countBelow</code>."],
    ["Design", "Grouping by map; capped nesting.", "You can explain why <code>-Xss</code> is not a fix."],
    ["Tests", "A test at 100,000 levels.", "You added a test for another kind of broken data."],
    ["Explanation", "You can turn a small recursion into a loop on paper.", "You can sketch the SQL version."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any code that walks user data:</p>
<ul class="rules">
<li>Does any recursion or loop depth depend on user data? What caps it?</li>
<li>Is there a nested loop that searches a list for every item?</li>
<li>What happens with a missing parent, or a loop?</li>
<li>Is there a test at the limit, not just below it?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
