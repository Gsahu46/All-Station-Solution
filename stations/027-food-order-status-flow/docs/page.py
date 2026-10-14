"""Station 027 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 27,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · enum state machine · EnumMap · ConcurrentHashMap · Optional · MockMvc",
    "simulation": "Three demo orders in memory. No food is cooked or delivered, and nobody is charged: a status change only updates the record.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tiffino/orders/"
T = "src/test/java/com/tiffino/orders/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Status", "Where an order is in its life.", "Placed, accepted, being prepared, out for delivery.", "<code>OrderStatus</code>"),
    ("State machine", "A fixed set of statuses and the moves allowed between them.", "A board game: you can only move along the arrows.", "<code>OrderStatus</code> and its table"),
    ("Transition table", "The list of allowed moves, from each status.", "A train timetable: which stations follow which.", "<code>NEXT</code> (an <code>EnumMap</code>)"),
    ("Terminal status", "A status with no way out.", "A cancelled ticket stays cancelled.", "DELIVERED, CANCELLED, REJECTED"),
    ("409 Conflict", "\"Your request is valid, but it conflicts with the current state.\"", "Asking to board a train that has left.", "A move the table does not allow"),
    ("Optional", "A value that may be missing, said in the type.", "An envelope that may be empty: you check before reading.", "<code>orders.find(id)</code>"),
]
STORY = [
    ("A tablet sends the wrong button", "A busy kitchen taps DELIVERED instead of ACCEPTED. The customer is told their food arrived; it has not been cooked."),
    ("A cancelled order gets picked up", "The customer cancels; the rider's app still shows the order and marks it PICKED_UP. Food is made and carried for nobody."),
    ("The fix", "Write the allowed moves down once, as a table. Every status change is checked against it, and a move it does not allow is refused with what is allowed instead."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A status is not a field anyone may set. It moves only along the arrows you drew.</p>

<h2>What are we building?</h2>
<p><code>POST /orders/{id}/status-changes</code> moves an order to a new status if the table allows it from where it is now. <code>GET /orders/{id}</code> shows the order and its history.</p>

<h2>An everyday analogy</h2>
<p>A railway signal box: a train can only go from one block to the next one the signals allow. The signalman cannot send it from Pune straight to Delhi, and a cancelled train never leaves the platform.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Find the order</strong>: no such order, <code>404</code>.</li>
<li><strong>Same status again?</strong> A double tap: return the order unchanged.</li>
<li><strong>Check the table</strong>: not an allowed move, <code>409</code> naming what is allowed.</li>
<li><strong>Move</strong>: the check and the change are one step, and the change goes into the history.</li>
</ol>

<details class="qa check"><summary>Check yourself: the kitchen taps PREPARING and the customer taps cancel at the same moment. Both are allowed from ACCEPTED. What should happen?</summary><p>Exactly one wins, and the other is told the order has moved on. If both "won", the kitchen would cook a cancelled order, or the customer would pay for food they cancelled.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No sign-in.</strong> Anyone may ask for any move here; challenge 1 adds who may do what.</li>
<li><strong>No refunds or payments.</strong> Cancelling only changes the status.</li>
<li><strong>No database.</strong> Three demo orders in memory.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tiffino</strong> (a fictional food delivery app) stores an order's status as whatever the last tablet or app sent. Kitchens mark orders DELIVERED before cooking them, riders pick up cancelled orders, and support cannot tell what really happened.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a placed order, <b>then</b> it can go ACCEPTED, PREPARING, READY_FOR_PICKUP, PICKED_UP, DELIVERED, one step at a time, with each step in its history.</li>
<li><b>Given</b> a placed order, <b>when</b> DELIVERED is asked, <b>then</b> <code>409</code> naming ACCEPTED, REJECTED and CANCELLED as allowed.</li>
<li><b>Given</b> a cancelled order, <b>when</b> any move is asked, <b>then</b> <code>409</code>: nothing can change now.</li>
<li><b>Given</b> the current status asked again, <b>then</b> <code>200</code> and no new history entry.</li>
<li><b>Given</b> two allowed moves at the same instant, <b>then</b> exactly one happens.</li>
<li><b>Given</b> an unknown status or no status, <b>then</b> <code>400</code>; an unknown order, <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>The table is the only rule: PLACED → ACCEPTED, REJECTED, CANCELLED; ACCEPTED → PREPARING, CANCELLED; PREPARING → READY_FOR_PICKUP; READY_FOR_PICKUP → PICKED_UP; PICKED_UP → DELIVERED.</li>
<li>DELIVERED, CANCELLED and REJECTED are final.</li>
<li>Status names are exact (<code>ACCEPTED</code>, not <code>accepted</code>).</li>
<li>Each move is checked and applied atomically; history times come from an injected clock.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Model a lifecycle as an enum state machine with a transition table.</li>
<li>Use <code>409</code> for a valid request that conflicts with the current state.</li>
<li>Use <code>Optional</code> for "may not exist" instead of <code>null</code>.</li>
<li>Test a table exhaustively, and test two moves racing.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/orders/{id}</code>", "The order, its status and its history."],
    ["<code>POST</code>", "<code>/orders/{id}/status-changes</code>", "Move to <code>{\"to\": \"…\"}</code> if the table allows it."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "The order (after the move, or unchanged for a repeat)"],
    ['<span class="pill warn">400</span>', "No status, or a status that does not exist"],
    ['<span class="pill warn">404</span>', "No such order"],
    ['<span class="pill warn">409</span>', "The move is not allowed from the current status; the body names <code>currentStatus</code> and <code>allowedNext</code>"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-a-new-order", "Case 1: a new order", "<b>Why:</b> PLACED, with its history."),
    ("02-delivered-before-accepted", "Case 2: DELIVERED straight away", "<b>Why:</b> not an arrow from PLACED: <code>409</code>, naming the three moves that are."),
    ("03-accepted", "Case 3: ACCEPTED", "<b>Why:</b> allowed: the status moves and the history grows."),
    ("04-the-tablet-taps-twice", "Case 4: ACCEPTED again", "<b>Why:</b> a double tap is not a move: <code>200</code>, history unchanged."),
    ("05-picking-up-a-cancelled-order", "Case 5: picking up a cancelled order", "<b>Why:</b> CANCELLED is final: <code>409</code>, and nothing can change now."),
    ("06-a-status-that-does-not-exist", "Case 6: a made-up status", "<b>Why:</b> not one of the statuses: <code>400</code>."),
    ("07-an-unknown-order", "Case 7: an unknown order", "<b>Why:</b> <code>404</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["PLACED to DELIVERED, one step at a time", "Each 200; 6 history entries", "<code>anOrderGoesFromPlacedToDeliveredOneStepAtATime</code>"],
    ["The same status twice", "200, no new entry", "<code>aDoubleTapIsNotAnErrorAndNotASecondStep</code>"],
    ["PREPARING to DELIVERED", "<code>409</code>; status unchanged", "<code>aRefusedMoveSaysWhatIsAllowed</code>"],
    ["Order 9999", "<code>404</code>", "<code>anUnknownOrderIs404</code>"],
    ["TELEPORTED, lower case, none, a non-numeric id", "<code>400</code>", "<code>anUnknownStatusOrNoStatusIs400</code>"],
    ["All 64 from–to pairs", "Match the hand-written rule", "<code>everyPairOfStatusesMatchesTheRule</code>"],
    ["Reachability", "Every status reachable; only the three ends are final", "<code>everyStatusIsReachableFromPlacedAndOnlyEndsHaveNoWayOut</code>"],
    ["PREPARING and CANCELLED at once, 50 rounds", "Exactly one wins each time", "<code>whenTheKitchenAndTheCustomerTapAtOnceExactlyOneWins</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Setting any status the client sends, so DELIVERED can come before PREPARING.</p>
<p>A setter is the simplest thing that works in a demo. The first test shows the old order accepting DELIVERED before anything else; the second, a cancelled order being picked up. The third shows the real flow refusing both with <code>409</code>. While building, skipping the table check turned 3 tests red, treating a double tap as an error turned 1 red, and replacing the atomic move with get, check, put made the racing test fail in round 0 or 1 on each of 3 runs.</p>
</div>
""" + code(read(T + "AnyStatusTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "OrderController.java", dwn("Finds the order or 404s; asks for the move; turns a refused move into a 409 with what is allowed.",
        "The controller has no rules: it translates <code>Optional</code> and <code>IllegalMove</code> into HTTP.",
        "Rules in <code>if</code> statements in the controller.")),
    (J + "OrderStatus.java", dwn("The statuses and the transition table.",
        "One <code>EnumMap</code> is the whole rule: easy to read, easy to test exhaustively.",
        "The trap: no table at all.",
        "<ul><li>The table is filled in a <code>static</code> block, because an enum constant cannot refer to constants declared after it.</li><li>Terminal statuses map to empty sets.</li></ul>")),
    (J + "Orders.java", dwn("The orders, and the only method that changes a status.",
        "<code>computeIfPresent</code>: check the table and write the new status as one step per order.",
        "Read, check, then write: two moves at once both pass the check.")),
    ("src/main/resources/application.yaml", "<p>Problem bodies for every error.</p>"),
    (J + "OrdersApplication.java", "<p>Entry point, and the <code>Clock</code> for history times.</p>"),
]
tree = """stations/027-food-order-status-flow/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tiffino/orders/
│   ├── OrderController.java   ├── OrderStatus.java   ├── Orders.java   └── OrdersApplication.java
├── src/test/java/com/tiffino/orders/   (see Tests)
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
<p>Order 1003 is being prepared. Try to deliver it, then follow the arrows.</p>
""" + code("""curl -i -X POST http://localhost:8080/orders/1003/status-changes -H "Content-Type: application/json" -d '{"to":"DELIVERED"}'
curl -X POST http://localhost:8080/orders/1003/status-changes -H "Content-Type: application/json" -d '{"to":"READY_FOR_PICKUP"}'""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>409</code>", "The move is not an arrow from the current status.", "Read <code>allowedNext</code> in the body."],
    ["<code>400</code> for <code>accepted</code>", "Status names are exact.", "Send <code>ACCEPTED</code>."],
    ["Orders back to the start after a restart", "Orders live in memory.", "Expected in this station."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>OrderStatusContractTest</code> ({cnt('OrderStatusContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>AnyStatusTrapTest</code> ({cnt('AnyStatusTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "The table, pair by pair, and two moves racing", f"<code>TransitionTableTest</code> ({cnt('TransitionTableTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "AnyStatusTrapTest.java", "<p>Written first: the old setter's DELIVERED-first and picked-up-after-cancel, and the real 409s.</p>"),
    (T + "OrderStatusContractTest.java", "<p>The whole happy path, a double tap, a refused move, and bad requests.</p>"),
    (T + "TransitionTableTest.java", "<p>All 64 pairs against a rule written by hand, reachability, and two moves racing for 50 rounds.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: fresh demo orders before each test, and a helper that sends each move as the party that would make it.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tiffino/orders/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=WhoMayMoveChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Who may make which move", "Beginner-friendly", 25,
    "Read an <code>X-Actor</code> header (RESTAURANT, RIDER or CUSTOMER; a stand-in for real sign-in). Kitchens accept, reject, prepare, mark ready and may cancel; riders pick up and deliver; customers may only cancel. The wrong party is <code>403</code>; the table still gives <code>409</code>.",
    "both tests in <code>WhoMayMoveChallengeTest</code> pass, and the station's tests still pass.",
    ["An <code>Actor</code> enum with the statuses each party may move to: data on the enum, like the table.",
     "A header Spring can turn into the enum: a missing or unknown one is a <code>400</code> on its own."],
    "challenge/WhoMayMoveChallengeTest.java", ["challenge/solution/Actor.java", "challenge/solution/OrderController.java"]) + challenge(2, "Undo a mistaken READY", "Go deeper", 30,
    "Kitchens tap READY_FOR_PICKUP too early. Allow going back to PREPARING within 2 minutes of becoming ready; refuse it after. Keep the table as it is: this is a rule about time on top of it.",
    "the test in <code>UndoReadyChallengeTest</code> passes, and the exhaustive table test still passes.",
    ["The time of the last change is in the history.",
     "Compare with the injected <code>Clock</code>, so the test can move time instead of waiting."],
    "challenge/UndoReadyChallengeTest.java", ["challenge/solution/Orders.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Keeping the history</h2>
<p>With a database, would you keep only the current status in the <code>orders</code> table, or also every change in an <code>order_status_changes</code> table? How do you stop two servers making conflicting moves: a version column, a row lock, or a check constraint? What does support need to see when a customer says "my order says delivered but I have nothing"?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old setter's impossible orders.</li>
<li>Write the statuses and the table; test every pair against a rule written separately.</li>
<li>Make the move one atomic step; race two moves to prove it.</li>
<li>Map refused moves to <code>409</code> with the allowed list; make repeats harmless.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Enum and a transition table", "A table to keep up to date.", '<span class="pill ok">Chosen</span>'],
    ["A status setter", "Any status from anywhere.", '<span class="pill bad">The trap</span>'],
    ["<code>if</code> chains in each endpoint", "The rule is spread out and drifts.", '<span class="pill bad">Avoid</span>'],
    ["A method per move (<code>accept()</code>, <code>cancel()</code>)", "Clear names; more endpoints and code.", '<span class="pill warn">Good for few moves</span>'],
    ["A state machine library", "A dependency and its concepts; worth it with guards, actions and many states.", '<span class="pill warn">For bigger flows</span>']]) + """
<h2>Database design</h2>
<p>None in this station. With a database: <code>orders.status</code> with a check constraint listing the valid statuses, an <code>order_status_changes</code> table (order, from, to, at, by), and the move as one <code>UPDATE … WHERE id = ? AND status = ?</code>: if no row changed, someone else moved first.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Tablets and apps</dt><dd>Clients retry and double tap. Repeating the current status is harmless, and a <code>409</code> names what is allowed, so the app can show the right buttons.</dd>
<dt>Concurrency</dt><dd>Kitchen, rider and customer act at the same time. One atomic move per order; across servers, a conditional update in the database does the same.</dd>
<dt>Support</dt><dd>The history answers "what happened when". Keep who made each move as well (challenge 1).</dd>
<dt>Change</dt><dd>A new status is a new enum constant and new table rows; the exhaustive test fails until the written rule is updated too.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why model order status as a state machine?", "Because only some moves make sense. A table of allowed moves turns every impossible order (delivered before cooked) into a refused request instead of bad data."),
    ("Which status code for an illegal move?", "409 Conflict: the request is well formed, but it conflicts with the order's current state. 400 is for a malformed request."),
    ("How do you stop two moves at once from both happening?", "Make the check and the write one atomic step: compute on a ConcurrentHashMap in memory, or UPDATE … WHERE status = expected in a database."),
    ("Why return 200 for the same status twice?", "Clients retry and double tap. The order is already in that state, so the request has its intended effect; an error would only confuse the app."),
    ("What is Optional for?", "To say in the type that a value may be missing, and make the caller decide what to do (orElseThrow, map) instead of meeting a null later."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can draw the state diagram from the table."],
    ["Modelling", "One table, terminal statuses empty.", "Where a rule about time or people goes, outside the table."],
    ["Concurrency", "Moves are atomic per order.", "The database version of the same guarantee."],
    ["Explanation", "409 versus 400.", "Why a double tap is a 200."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any status field:</p>
<ul class="rules">
<li>Can a client set any status directly?</li>
<li>Is there one table of allowed moves, tested pair by pair?</li>
<li>Are final statuses really final?</li>
<li>Can two moves at once both succeed?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
