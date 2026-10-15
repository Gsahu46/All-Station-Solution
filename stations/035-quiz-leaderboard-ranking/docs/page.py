"""Station 035 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 35,
    "stack": "Spring Boot 4.1.1 · Java 25 · Comparator chains · PriorityQueue top-N · competition and dense ranking · MockMvc",
    "simulation": "Quizzes, students and scores are demo data, not Shikshalab's. The X-Student-Id header stands in for a signed-in student; a real app takes the student from the login, never from a header.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/shikshalab/leaderboard/"
T = "src/test/java/com/shikshalab/leaderboard/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Competition ranking", "Equal scores share a rank, and the next rank skips: 1, 2, 2, 4.", "Two runners tie for silver; nobody gets bronze; the next is 4th.", "<code>rank</code>"),
    ("Dense ranking", "Equal scores share a rank, and the next rank does not skip: 1, 2, 2, 3.", "Counting distinct scores above you.", "<code>denseRank</code>"),
    ("Tie-break", "A rule that orders equal items, here only for display.", "Who finished first, among equal marks.", "time taken, then student id"),
    ("Comparator", "A rule that says which of two items comes first.", "The judging criteria, in order.", "<code>Leaderboard.ORDER</code>"),
    ("Top N", "The best N items, without sorting everyone.", "Keeping the 10 best cards in your hand while dealing a whole deck.", "<code>topN</code>"),
    ("Priority queue (heap)", "A collection that always knows its smallest item.", "A queue where the weakest card is always on top, ready to drop.", "<code>PriorityQueue</code>"),
]
STORY = [
    ("Two students, one score", "Kabir and Meera both score 88. The board shows Kabir 3rd and Meera 4th, only because of the order rows came back in. Meera's parents write in."),
    ("A quick fix, a new bug", "Equal scores now share a rank, and \"top 10\" becomes \"rank 10 or better\". When two students tie for 10th, the top 10 shows 11 names."),
    ("The fix", "Rank by score so ties share a rank; show at most N rows, ordered by score, then time, then id; say how many tied students did not fit."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A rank comes from the score, not from where a row happens to sit in a list.</p>

<h2>What are we building?</h2>
<p><code>GET /quizzes/{id}/leaderboard?top=10</code> shows the best students with their ranks, and <code>…/leaderboard/me</code> shows a student their own rank among everyone.</p>

<h2>An everyday analogy</h2>
<p>A school sports day. Two children tie for silver: both get silver, and the next child is 4th. The notice board has room for ten names; if there are two 10th places, the board says \"and 1 more tied\" instead of squeezing in an eleventh.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Order</strong> attempts: higher score first, then less time, then student id.</li>
<li><strong>Keep the best N</strong> with a small heap, without sorting all 2,000.</li>
<li><strong>Give ranks</strong>: equal scores share the rank of the first of them.</li>
<li><strong>Count</strong> how many students tied with the last row did not fit.</li>
</ol>

<details class="qa check"><summary>Check yourself: Saanvi and Reyansh both scored 70. Saanvi took 240 seconds, Reyansh 270. What are their ranks?</summary><p>Both 10th: ranks come from the score. Saanvi is shown first because she was faster, and in a top 10 she is the one that fits.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No live updates.</strong> The board is computed per request.</li>
<li><strong>No login.</strong> A header stands in for the signed-in student.</li>
<li><strong>One attempt per student.</strong> Challenge 2 allows retries.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Shikshalab</strong> (a fictional learning app) shows quiz leaderboards. Two students with the same score get ranks 3 and 4, and the \"top 10\" sometimes shows 11 names.</p>

<h2>Acceptance criteria</h2>
<p class="muted">On quiz 3, \"Algebra sprint\": 12 students, ties at 3rd, 6th and 10th.</p>
<ol class="gwt">
<li><b>Given</b> Kabir and Meera both at 88, <b>then</b> both are rank 3 (dense 3), Kabir shown first (250 s against 310 s), and the next student is rank 5 (dense 4).</li>
<li><b>Given</b> <code>top=10</code> with a tie for 10th, <b>then</b> exactly 10 rows, the faster of the two shown, and <code>moreTiedAtCutoff: 1</code>.</li>
<li><b>Given</b> Reyansh asks for his place, <b>then</b> rank 10, dense 8, of 12, though he is not in the top 10 rows.</li>
<li><b>Given</b> equal score and equal time, <b>then</b> the same rank, ordered by student id, the same on every request.</li>
<li><b>Given</b> an unknown quiz, or a student who did not attempt it, <code>404</code>; <code>top</code> outside 1 to 100, or a missing or malformed student id, <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Ranks depend on the score only; time and id decide only the display order.</li>
<li>Top N is at most N rows; ties beyond the cut are counted.</li>
<li>Top N uses a heap of N + 1, not a sort of every attempt.</li>
<li>Student ids normalised with <code>Locale.ROOT</code>.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Tell competition from dense ranking, and compute both.</li>
<li>Build a comparator chain, and know what <code>reversed()</code> applies to.</li>
<li>Find the top N with a <code>PriorityQueue</code>.</li>
<li>Define \"top N\" precisely when there are ties.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/quizzes/{id}/leaderboard?top=10</code>", "The best <code>top</code> students (1 to 100, default 10)."],
    ["<code>GET</code>", "<code>/quizzes/{id}/leaderboard/me</code>", "Your own rank. Header <code>X-Student-Id</code> (demo stand-in for the login)."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "A board, or your place"],
    ['<span class="pill warn">400</span>', "<code>top</code> outside 1 to 100 or not a number; a missing or malformed student id"],
    ['<span class="pill warn">404</span>', "No such quiz, or no attempt by that student"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-the-top-ten", "Case 1: the top ten of quiz 3", "<b>Why:</b> ranks 3, 3 and 6, 6 shared; ten rows; one more tied at 10th."),
    ("02-the-top-three", "Case 2: the top three", "<b>Why:</b> Kabir fits, Meera (also 88, slower) does not: <code>moreTiedAtCutoff: 1</code>."),
    ("03-my-place", "Case 3: Reyansh's place", "<b>Why:</b> rank 10, though not in the ten rows."),
    ("04-the-top-five-of-two-thousand", "Case 4: top five of 2,000", "<b>Why:</b> the heap keeps five while reading 2,000 attempts."),
    ("05-a-student-who-did-not-attempt", "Case 5: S-9999", "<b>Why:</b> <code>404</code>."),
    ("06-top-zero", "Case 6: <code>top=0</code>", "<b>Why:</b> <code>400</code>."),
    ("07-no-such-quiz", "Case 7: quiz 99", "<b>Why:</b> <code>404</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Ties at 3rd, 6th and 10th", "Shared competition and dense ranks", "<code>competitionAndDenseRanksOnTheHandCheckedQuiz</code>"],
    ["Equal score and equal time", "Ordered by id, same rank", "<code>equalScoreAndEqualTimeAreOrderedByStudentIdAndShareTheRank</code>"],
    ["<code>reversed()</code> on the whole chain", "Slower first on ties: the slip to avoid", "<code>reversingTheWholeChainWouldPutTheSlowerFirst</code>"],
    ["N = 1, 10, 100, 1,999, 2,000, 2,500", "The heap equals sorting everyone", "<code>theHeapGivesTheSameTopNAsSortingEveryone</code>"],
    ["Each of the top 100 of 2,000 asks for their place", "The same rank as on the board", "<code>myPlaceMatchesTheBoardForEveryStudent</code>"],
    ["Ties beyond the cut on the 2,000", "Counted exactly", "<code>theCutoffCountIsEveryoneTiedWithTheLastRowWhoDidNotFit</code>"],
    ["Unknown quiz; no attempt", "<code>404</code>", "<code>unknownQuizzesAndStudentsAre404</code>"],
    ["<code>top</code> 0, 101, \"ten\"; quiz \"abc\"; no or bad header", "<code>400</code>", "<code>badParametersAre400</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Ranking by list position, so tied scores get different ranks.</p>
<p>The first test ranks by position: Kabir and Meera, both 88, get 3 and 4. The second shows the quick fix: shared ranks, but \"rank 10 or better\" gives 11 names. The third shows the fix: ten rows, shared ranks, and one more tied counted. While building, each fix was undone once. Ranking by position turned 4 tests red, and a heap that keeps the worst 9. No time tie-break turned 1 red, no cutoff count 4, counting equal scores as ahead in \"me\" 2, and dense equal to competition ranks 2.</p>
</div>
""" + code(read(T + "ListPositionRankTrapTest.java"), "java") + code(read(T + "OldLeaderboard.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "LeaderboardController.java", dwn("Validates <code>top</code> and the student id, and returns the board or your place.",
        "<code>@Min</code>/<code>@Max</code> on a parameter: Spring answers 400 by itself.",
        "Taking the student from a header in a real app: anyone could ask as anyone.")),
    (J + "Leaderboard.java", dwn("The order, the top N, the ranks, and your place.",
        "One comparator for the display order; ranks from the score alone; a heap of N + 1.",
        "Rank = position + 1, and top N = \"rank N or better\".",
        "<ul><li><code>comparingInt(score).reversed()</code> reverses only the score; the time and id keys keep their natural order.</li><li>The heap uses <code>ORDER.reversed()</code> so its head is the worst of the best, ready to drop.</li><li>A row's rank: the previous row's rank on equal scores, its position otherwise. Correct because every higher score is already in the list.</li></ul>")),
    (J + "Attempt.java", "<p>One attempt: student, score, seconds taken.</p>"),
    (J + "Quiz.java", "<p>A quiz and its attempts.</p>"),
    (J + "Quizzes.java", "<p>Quiz 3, checked by hand, and quiz 7, 2,000 seeded attempts.</p>"),
    (J + "LeaderboardApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/035-quiz-leaderboard-ranking/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/shikshalab/leaderboard/
│   ├── LeaderboardController.java   ├── Leaderboard.java
│   ├── Attempt.java   ├── Quiz.java   ├── Quizzes.java   └── LeaderboardApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/shikshalab/leaderboard/   (see Tests)
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
<p>Move <code>.reversed()</code> in <code>Leaderboard.ORDER</code> to the end of the chain and run <code>RankingTest</code>. Read which test fails and why, then put it back.</p>
""" + code("""curl "http://localhost:8080/quizzes/3/leaderboard?top=4"
curl http://localhost:8080/quizzes/3/leaderboard/me -H "X-Student-Id: S-1004\"""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Ties in a different order on each request", "The comparator has no final key, and the source order changes.", "End the chain with a unique key, such as the student id."],
    ["The top N comes back worst first", "The heap's comparator was not reversed, or the result was not sorted.", "Heap with <code>ORDER.reversed()</code>; sort the kept items with <code>ORDER</code>."],
    ["<code>400</code> for <code>?top=50</code> after changing the limit", "<code>@Max(100)</code> is on the parameter.", "Change the constraint, and the tests that check it."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the pieces it uses.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>LeaderboardContractTest</code> ({cnt('LeaderboardContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>ListPositionRankTrapTest</code> ({cnt('ListPositionRankTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Ranks, tie-breaks, heap against sorting, my place", f"<code>RankingTest</code> ({cnt('RankingTest')} runs)", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "ListPositionRankTrapTest.java", "<p>Written first: both complaints, then the fix.</p>"),
    (T + "RankingTest.java", "<p>Hand-checked ranks, the <code>reversed()</code> slip, the heap against a full sort, and my place against the board.</p>"),
    (T + "LeaderboardContractTest.java", "<p>Full responses compared strictly, and every refusal.</p>"),
    (T + "OldLeaderboard.java", "<p>The old code and its quick fix, kept only in tests.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/shikshalab/leaderboard/</code>.</li>
<li>Run it: <code>./mvnw test -Dtest=AroundMeChallengeTest</code>. Challenge 1 does not compile until <code>around</code> exists; add an empty one and watch it fail.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Who is around me?", "Beginner-friendly", 25,
    "Add <code>around(quizId, studentId, k)</code>: up to k rows above and k below the student, in board order, with ranks from the whole board.",
    "both tests in <code>AroundMeChallengeTest</code> pass.",
    ["Rank the whole sorted board once, then take a slice around the student.",
     "<code>Math.max(0, i - k)</code> and <code>Math.min(size, i + k + 1)</code> keep the slice inside the list."],
    "challenge/AroundMeChallengeTest.java", ["challenge/solution/Leaderboard.java"]) + challenge(2, "Best of several attempts", "Go deeper", 30,
    "Students may now try a quiz more than once. The board and \"me\" use each student's best attempt (highest score, then fastest), and participants counts students.",
    "both tests in <code>BestAttemptChallengeTest</code> pass, and the station's tests still pass.",
    ["<code>Collectors.toMap(Attempt::studentId, identity(), BinaryOperator.minBy(ORDER))</code> keeps the best per student.",
     "Use the same list for the board, the cutoff count and \"me\"."],
    "challenge/BestAttemptChallengeTest.java", ["challenge/solution/Leaderboard.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>A live board for two lakh students</h2>
<p>A national quiz has 2,00,000 students submitting in the same 10 minutes, and the board must update every few seconds. Compare recomputing from all attempts, keeping a sorted structure in memory, and a sorted set in a cache such as Valkey. How does each one answer \"my rank\" for a student at 1,50,000th place?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test on a quiz small enough to rank by hand.</li>
<li>Decide the rules in words: what decides a rank, what decides display order, what \"top N\" means with ties.</li>
<li>Write the comparator, then the heap, then the ranks.</li>
<li>Check the heap against a full sort, and \"me\" against the board, on 2,000 attempts.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Heap of N + 1", "O(attempts × log N) time, memory for N.", '<span class="pill ok">Chosen</span>'],
    ["Sort everyone, take N", "O(attempts × log attempts); simpler; fine at 2,000.", '<span class="pill warn">Also fine here</span>'],
    ["Rank = position + 1", "Ties get different ranks.", '<span class="pill bad">The trap</span>'],
    ["Top N = rank N or better", "More than N rows when there are ties.", '<span class="pill bad">The quick fix</span>'],
    ["Time as part of the rank", "No ties, but the rule must be announced before the quiz.", '<span class="pill warn">A product choice</span>']]) + """
<h2>Database design</h2>
<p>None in this station. In SQL, <code>rank() over (order by score desc)</code> and <code>dense_rank() over (…)</code> compute both rankings, with <code>order by score desc, seconds, student_id limit 10</code> for the display order; <code>unique (quiz_id, student_id)</code> on attempts enforces one attempt each.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Fairness</dt><dd>Whatever decides ties must be written in the quiz rules before students start. Changing it afterwards changes who \"won\".</dd>
<dt>Identity</dt><dd>\"Me\" must come from the login. A header the client sets would let anyone see anyone's place.</dd>
<dt>Scale</dt><dd>Recomputing per request is fine for thousands of attempts; for lakhs with frequent reads, keep a sorted structure or cache the board for a few seconds.</dd>
<dt>Children's data</dt><dd>Leaderboards for minors often show first names only, or let a student hide their name; check the school's and the law's rules on children's data.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Competition vs dense ranking?", "Both give equal values the same rank. Competition skips the following ranks (1, 2, 2, 4); dense does not (1, 2, 2, 3). SQL has rank() and dense_rank()."),
    ("How do you find the top N of a large list efficiently?", "A min-heap of size N: offer each item, poll when it exceeds N. O(n log N) time and O(N) memory, versus O(n log n) for a full sort."),
    ("What does Comparator.reversed() reverse?", "The whole comparator it is called on. comparingInt(score).reversed().thenComparing(time) reverses only the score; ...thenComparing(time).reversed() reverses both."),
    ("Why end a comparator with a unique key?", "Otherwise equal items keep whatever order the input had, which can change between requests, so the board flickers."),
    ("How do you compute one student's rank without sorting?", "Count the students with a higher score and add one (competition); count distinct higher scores and add one (dense)."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You moved <code>reversed()</code> and explained the failure."],
    ["Ranking", "Ties share a rank.", "You can state what \"top N\" means with ties, in one sentence."],
    ["Algorithms", "A heap for top N.", "When a full sort is just as good."],
    ["Testing", "Hand-checked examples.", "Checking two methods against each other on large data."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any ranking:</p>
<ul class="rules">
<li>Is a rank ever computed from a position in a list?</li>
<li>What exactly does \"top N\" return when the Nth place is tied?</li>
<li>Does the comparator end with a unique key?</li>
<li>Where does <code>reversed()</code> sit in the chain, and what does it reverse?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
