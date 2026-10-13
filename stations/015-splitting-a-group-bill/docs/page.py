"""Station 015 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 15,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · integer paise · Map · MockMvc",
    "simulation": "Expenses are records in the app's memory. Nobody is charged and no money moves: settle-up only suggests who should pay whom.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/splitsaathi/groups/"
T = "src/test/java/com/splitsaathi/groups/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Remainder", "What is left after dividing into equal whole parts.", "10 laddoos for 3 children: 3 each, 1 left over.", "₹1,000 ÷ 3 = 33,333 paise each, 1 paisa left."),
    ("Paise", "Whole hundredths of a rupee. Integers, no rounding.", "₹1,000 is 1,00,000 paise.", "Every amount in this API."),
    ("Equal, exact, shares", "Three ways to split: the same for everyone, given amounts, or by weight (2:1:1).", "Splitting a cab fare, a hotel bill by room, fuel by who drove more.", "<code>splitType</code>"),
    ("Largest remainder", "Give each person their whole part, then hand out the leftover paise to whoever lost the biggest fraction.", "Handing the extra laddoo to the child who was owed the most of it.", "<code>Splitter.shares</code>"),
    ("Net balance", "What someone paid minus what they owe. Positive: others owe them.", "Asha paid ₹900, her share was ₹300: she is owed ₹600.", "<code>balancesPaise</code>"),
    ("Settle-up", "The payments that bring every balance to zero.", "At the end of a trip: \"Ravi pays Asha ₹300\".", "<code>payments</code>"),
]
STORY = [
    ("Asha pays ₹1,000 for dinner for three", "The app splits it as ₹333.33 each. Three people owe ₹999.99. One paisa is gone, and Asha is the one who lost it."),
    ("After a week in Goa", "Settling up shows 12 payments: everyone pays everyone back for every bill."),
    ("The fix", "Split in whole paise and hand the leftover paise to someone by a fixed rule, so the parts always add up. Then net everyone's balance and pair the biggest debtor with the biggest creditor: at most one payment fewer than people."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Rounding each part on its own loses money. Decide who gets the remainder.</p>

<h2>What are we building?</h2>
<p><code>POST /groups/{id}/expenses</code> records who paid and splits it equally, by exact amounts, or by shares, always adding up to the paisa. <code>GET /groups/{id}/settle-up</code> shows each member's balance and the payments that clear them.</p>

<h2>An everyday analogy</h2>
<p>A family shares 10 mangoes among 3 children: each gets 3, and the 10th goes to the youngest, because that is the family rule. Nobody cuts the mango into 3.33 pieces and throws away the crumbs.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Record an expense</strong>: who paid, how many paise, and how to split.</li>
<li><strong>Split in whole paise</strong>; the leftover paise go out one at a time by a fixed rule.</li>
<li><strong>Keep the split</strong> with the expense, so balances never divide again.</li>
<li><strong>Settle up</strong>: net balances, then the biggest debtor pays the biggest creditor, again and again.</li>
</ol>

<details class="qa check"><summary>Check yourself: why not just round ₹333.333 up to ₹333.34 for everyone?</summary><p>Then three people owe ₹1,000.02: two paise more than Asha paid. Rounding every share the same way, up or down, never adds up in general. Only giving out the remainder one paisa at a time does.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real payments.</strong> Settle-up only suggests transfers.</li>
<li><strong>No login, no database.</strong> Two groups are fixed in code.</li>
<li><strong>Not the fewest possible payments in every case.</strong> The rule guarantees at most one fewer payment than people; the true minimum is a much harder problem.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>SplitSaathi</strong> (a fictional bill-splitting app) divides expenses with <code>double</code> and rounds each share. Totals drift by a paisa, so the person who paid is always slightly short, and support gets "the numbers don't add up" tickets. Settle-up replays every expense separately, so a weekend trip ends with a dozen transfers.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> ₹1,000 split equally among three, <b>then</b> the shares are 33,334, 33,333 and 33,333 paise: the first person listed takes the extra paisa.</li>
<li><b>Given</b> shares 2:1:1 of ₹1,000, <b>then</b> 50,000, 25,000, 25,000.</li>
<li><b>Given</b> exact amounts that do not add up to the total, <b>then</b> <code>422</code> saying by how much.</li>
<li><b>Given</b> anyone outside the group, a person listed twice, or a zero share, <b>then</b> <code>422</code>.</li>
<li><b>Given</b> a trip's expenses among four people, <b>then</b> settle-up needs at most 3 payments, and making them clears every balance.</li>
<li><b>Given</b> 1,000 random splits, <b>then</b> every one adds up exactly.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>All amounts are whole paise; ₹0.01 to ₹1,00,000 per expense (a demo rule). Fractions are <code>400</code>.</li>
<li>Equal split: leftover paise go to the participants in the order listed.</li>
<li>Shares: largest-remainder method; ties go in the order listed.</li>
<li>Balances always add up to zero; settle-up refuses to run if they do not.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Divide money and distribute the remainder so parts add up.</li>
<li>Explain why <code>double</code>, and <code>BigDecimal</code> with per-share rounding, both lose paise.</li>
<li>Implement equal, exact and share-based splits.</li>
<li>Net balances with a <code>Map</code> and settle with a greedy algorithm, and state its guarantee.</li>
<li>Test a rule on a thousand generated cases, not just three hand-picked ones.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/groups/{id}/expenses</code>", "Record and split an expense. <code>201</code> with <code>owedPaise</code> per person."],
    ["<code>GET</code>", "<code>/groups/{id}/settle-up</code>", "Balances and the suggested payments."]]) + """
<h2>Request body</h2>
""" + table(["Field", "Rule"], [
    ["<code>description</code>", "Required, at most 80 characters."],
    ["<code>paidBy</code>", "A member of the group."],
    ["<code>amountPaise</code>", "1 to 10,000,000, whole number."],
    ["<code>splitType</code>", "<code>EQUAL</code> (with <code>participants</code>), <code>EXACT</code> (with <code>exactPaise</code>), <code>SHARES</code> (with <code>shares</code>, 1–1000 each)."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Expense recorded"],
    ['<span class="pill ok">200</span>', "Settle-up"],
    ['<span class="pill warn">400</span>', "A field is missing or of the wrong type (including a fraction of a paisa)"],
    ['<span class="pill warn">404</span>', "No such group"],
    ['<span class="pill warn">422</span>', "The split cannot be applied: non-members, duplicates, zero shares, exact amounts that do not add up"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-equal", "Case 1: ₹1,000 among three", "<b>Why:</b> 1,00,000 paise ÷ 3 = 33,333 with 1 left over; the first person listed, Asha, takes it. The parts add up to exactly 1,00,000."),
    ("02-shares", "Case 2: fuel by shares 2:1:1", "<b>Why:</b> Kabir drove twice as much, so he owes half."),
    ("03-exact", "Case 3: hotel by room", "<b>Why:</b> exact amounts that add up to the total are stored as given."),
    ("04-exact-wrong-total", "Case 4: exact amounts that do not add up", "<b>Why:</b> ₹9,000 of ₹12,000 assigned: <code>422</code>, saying how far off it is."),
    ("05-settle-up", "Case 5: settle up", "<b>Why:</b> each balance is paid minus owed, and together they add up to zero. Pairing the biggest debtor with the biggest creditor clears four people in at most three payments."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["₹1,000 ÷ 3", "33,334 + 33,333 + 33,333", "<code>theSplitterHandsTheLeftoverPaisaToSomeone</code>"],
    ["Shares 1:1:1 of ₹100; 1:1:2 of 101 paise", "3,334/3,333/3,333; 25/25/51", "<code>sharesUseTheLargestRemainder</code>"],
    ["1,000 random totals, group sizes and shares", "Always add up; equal parts differ by at most 1 paisa", "<code>aThousandRandomSplitsAllAddUpExactly</code>"],
    ["Exact split", "Stored as given", "<code>anExactSplitIsStoredAsGiven</code>"],
    ["Shares 2:1:1", "Half, quarter, quarter", "<code>sharesSplitByWeight</code>"],
    ["Six trip expenses, four people", "3 payments; correct balances", "<code>settleUpNeedsAtMostOneFewerPaymentThanPeople</code>"],
    ["Payments applied", "Every balance becomes zero", "<code>settleUpClearsEveryBalanceInAtMostNMinusOnePayments</code>"],
    ["No expenses", "No payments", "<code>aGroupWithNoExpensesHasNothingToSettle</code>"],
    ["Exact amounts off by ₹3,000", "<code>422</code>", "<code>exactAmountsThatDoNotAddUpAre422</code>"],
    ["A non-member pays or takes part", "<code>422</code>", "<code>someoneOutsideTheGroupIs422</code>"],
    ["Same person twice, zero share, no participants", "<code>422</code>", "<code>badSplitsAre422</code>"],
    ["0 paise, 1000.5 paise, unknown split type", "<code>400</code>", "<code>badFieldsAre400</code>"],
    ["Unknown group", "<code>404</code>", "<code>anUnknownGroupIs404</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Dividing with <code>double</code> or default rounding, so a paisa goes missing.</p>
<p>"Divide and round to two decimals" looks careful. The first test shows ₹333.33 × 3 = ₹999.99. The second shows that <code>BigDecimal</code> alone is not the fix: dividing ₹1,000 by 3 exactly throws an exception, and rounding each share still loses the paisa. The third test shows the real splitter handing the leftover paisa to the first person. Dropping that leftover paisa from the code was tried while building: 2 tests went red.</p>
</div>
""" + code(read(T + "MissingPaisaTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "GroupController.java", dwn("Validates the expense for its split type, splits it, stores it; answers settle-up.",
        "A <code>switch</code> on the split type: the compiler checks every type is handled.",
        "No API.")),
    (J + "Splitter.java", dwn("Equal and share-based splits in whole paise that always add up.",
        "The money rule lives in one small, heavily tested class.",
        "The trap: rounded shares that do not add up.",
        "<ul><li><code>total / n</code> and <code>total % n</code>: the quotient and the remainder, in exact integers.</li><li>Shares: whole part first, then the leftover paise to the biggest cut-off fractions.</li></ul>")),
    (J + "SettleUp.java", dwn("Greedy settle-up: biggest debtor pays biggest creditor until all are zero.",
        "Each payment clears at least one person: at most n − 1 payments.",
        "One payment per person per expense.",
        "<ul><li>Refuses balances that do not add up to zero: a bug elsewhere must not become wrong payments.</li><li>A <code>TreeMap</code> makes ties resolve the same way every time.</li></ul>")),
    (J + "Groups.java", dwn("Groups, members and expenses (with their split stored); computes net balances.", "Splitting once and storing the result means balances never re-divide.", "Balances recomputed from rounded shares.")),
    (J + "ExpenseRequest.java", "<p>The body, with the split type as an enum.</p>"),
    ("src/main/resources/application.yaml", "<p>Problem bodies for every error; a fraction of a paisa is a <code>400</code>, not silently truncated.</p>"),
    (J + "GroupsApplication.java", "<p>Standard Spring Boot entry point.</p>"),
]
tree = """stations/015-splitting-a-group-bill/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/splitsaathi/groups/
│   ├── GroupController.java   ├── Splitter.java   ├── SettleUp.java
│   ├── Groups.java            ├── ExpenseRequest.java   └── GroupsApplication.java
├── src/test/java/com/splitsaathi/groups/   (see Tests)
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
<p>The body is in <code>docs/dinner.json</code> (Asha pays ₹1,000 for three).</p>
""" + code("""# Split: expect owedPaise asha 33334, ravi 33333, meera 33333
curl -i -X POST http://localhost:8080/groups/1/expenses -H "Content-Type: application/json" -d "@docs/dinner.json"

# Who pays whom
curl http://localhost:8080/groups/1/settle-up""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>422</code> about members", "Group 1 is asha, kabir, meera, ravi; group 2 is neha, omar.", "Use members of the group in the URL."],
    ["<code>400</code> for 1000.5", "Amounts are whole paise.", "Send 1000 or 1001."],
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>ExpenseContractTest</code> ({cnt('ExpenseContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>MissingPaisaTrapTest</code> ({cnt('MissingPaisaTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "The money rules on 1,000 generated cases; settle-up clears all", f"<code>SplitterTest</code> ({cnt('SplitterTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "MissingPaisaTrapTest.java", "<p>Written first: the lost paisa with <code>double</code> and with rounded <code>BigDecimal</code>; the splitter keeps it.</p>"),
    (T + "ExpenseContractTest.java", "<p>Each split type, a trip settled in 3 payments, and every refusal.</p>"),
    (T + "SplitterTest.java", "<p>Largest remainder by hand, 1,000 random splits with a fixed seed, and settle-up clearing every balance.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app through MockMvc, no expenses before each test.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/splitsaathi/groups/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=PercentSplitChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Split by percentage", "Beginner-friendly", 25,
    "Add <code>PERCENT</code> with a <code>percents</code> map of whole percentages that must add up to 100.",
    "both tests in <code>PercentSplitChallengeTest</code> pass, and the station's tests still pass.",
    ["Percentages are shares out of 100: <code>Splitter.shares</code> already does the arithmetic, remainder included.",
     "Check the sum is exactly 100 before splitting; otherwise <code>422</code>."],
    "challenge/PercentSplitChallengeTest.java", ["challenge/solution/ExpenseRequest.java", "challenge/solution/GroupController.java"]) + challenge(2, "Record a settlement", "Go deeper", 30,
    "Add <code>POST /groups/{id}/settlements</code> with <code>{\"from\", \"to\", \"amountPaise\"}</code>: Ravi paid Asha back. Balances move towards zero; after the suggested payments are recorded, settle-up suggests nothing.",
    "both tests in <code>SettlementChallengeTest</code> pass.",
    ["For the balances, \"Ravi paid Asha ₹300\" is an expense that Ravi paid and Asha alone owes. No new kind of record is needed.",
     "Refuse a payment to yourself and anyone outside the group."],
    "challenge/SettlementChallengeTest.java", ["challenge/solution/GroupController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Who gets the extra paisa?</h2>
<p>This station gives leftover paise to the first person listed. Over a year, that can be the same person every time. Propose a fairer rule (for example, rotating, or giving it to the payer), and check it still always adds up. Would you show the extra paisa in the app, or hide it?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: <code>double</code> and rounded <code>BigDecimal</code> both lose a paisa.</li>
<li>Write the splitter in whole paise, with a fixed remainder rule; test it on 1,000 generated cases.</li>
<li>Store each expense's split; compute balances by adding paid and subtracting owed.</li>
<li>Write the greedy settle-up and prove it clears every balance.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Whole paise + explicit remainder rule", "A rule to decide who gets the leftover.", '<span class="pill ok">Chosen</span>'],
    ["<code>double</code> and round each share", "Loses or invents paise (the trap).", '<span class="pill bad">Wrong</span>'],
    ["<code>BigDecimal</code> divided to 2 decimals", "Exact arithmetic, same lost paisa, because each share is still rounded separately.", '<span class="pill bad">Not enough</span>'],
    ["Settle each expense separately", "Many payments.", '<span class="pill bad">Wrong</span>'],
    ["Exact minimum number of payments", "A search over subsets; slow for large groups. The greedy bound is usually enough.", '<span class="pill warn">Rarely worth it</span>']]) + """
<h2>Database design</h2>
<p>None in this station. With a database: <code>expenses</code> (payer, amount) and <code>expense_shares</code> (expense, person, owed) with a check that shares add up to the expense, enforced in the same transaction that inserts them.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Money</dt><dd>Every amount is an integer of paise; division happens once per expense, with the remainder given out by rule. A balance that does not add up to zero stops settle-up instead of producing wrong payments.</dd>
<dt>Trust</dt><dd>Users compare totals to the paisa. Show each person's share, and why someone got the extra paisa.</dd>
<dt>Security</dt><dd>No login here; real apps check the caller is a member of the group before showing balances.</dd>
<dt>Maintainability</dt><dd>A new split type is one <code>switch</code> case; the compiler flags any switch that forgets it.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("How do you split ₹1,000 three ways so it adds up?", "Work in paise: 100,000 ÷ 3 = 33,333 remainder 1. Give everyone 33,333 and the leftover paisa to one person by a fixed rule. Shares are 33,334, 33,333 and 33,333."),
    ("Does BigDecimal fix rounding problems?", "It fixes representation (0.1 is exact), not allocation. Dividing 1000 by 3 exactly throws; rounding each share to two decimals still loses a paisa. You must distribute the remainder."),
    ("What is the largest remainder method?", "Give everyone the whole part of their exact share, then hand the leftover units, one each, to those whose fractions were largest."),
    ("How many payments does greedy settle-up need?", "At most n − 1 for n people, because each payment brings at least one person to zero. The true minimum can be lower and is expensive to find in general."),
    ("Why test with 1,000 random cases?", "Hand-picked examples confirm what you already thought of. Generated cases, with a fixed seed so failures repeat, check the invariant everywhere: parts always add up to the total."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can split any amount by shares by hand."],
    ["Money", "Integers and an explicit remainder rule.", "You can explain why rounded BigDecimal still fails."],
    ["Tests", "An invariant tested on generated cases.", "You know why the seed is fixed."],
    ["Explanation", "Greedy settle-up in two sentences.", "You can state and justify its n − 1 bound."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any money-splitting code:</p>
<ul class="rules">
<li>Is any amount a <code>double</code>?</li>
<li>Is each part rounded separately? Who gets the remainder?</li>
<li>Is there a test that the parts add up, on many cases?</li>
<li>What happens if balances do not add up to zero?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
