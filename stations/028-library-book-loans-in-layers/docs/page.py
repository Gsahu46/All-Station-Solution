"""Station 028 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 28,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · controller/service/repository · Mockito · @WebMvcTest · MockMvc",
    "simulation": "A demo library in memory: three members, eight books, three loans. Fines are records; no money is paid or collected.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/citylibrary/loans/"
T = "src/test/java/com/citylibrary/loans/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Controller", "Turns an HTTP request into a method call, and the answer back into HTTP.", "The library's front desk.", "<code>LoanController</code>, <code>KioskController</code>"),
    ("Service", "Where the rules live.", "The librarian who knows the lending rules.", "<code>LoanService</code>"),
    ("Repository", "Where records are kept and found.", "The card catalogue and the ledger.", "<code>MemberRepository</code> and friends"),
    ("Constructor injection", "A class receives what it needs through its constructor.", "A new librarian is handed the keys on day one.", "<code>LoanService(members, books, loans, clock)</code>"),
    ("Mock", "A stand-in object a test controls and checks.", "A rehearsal with a stand-in actor.", "<code>@Mock</code>, <code>@MockitoBean</code>"),
    ("Slice test", "A test that starts only one layer of the app.", "Testing the front desk with a cardboard librarian.", "<code>@WebMvcTest</code>"),
]
STORY = [
    ("The web app gets loan rules", "\"At most 3 books, nothing while a fine is unpaid\" is written straight into the web controller."),
    ("A kiosk arrives", "Its developer copies the rules into the kiosk's controller. A year later someone \"simplifies\" the copy: the kiosk now lends a 4th book and ignores fines. Nobody notices for months."),
    ("The fix", "Move every rule into one service. Both the web app and the kiosk call it, so there is one copy of each rule, and changing a rule changes it everywhere."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A rule written twice will, one day, say two different things.</p>

<h2>What are we building?</h2>
<p>A lending API with two ways in, the web (<code>POST /loans</code>) and a self-service kiosk (<code>POST /kiosk/checkouts</code>), plus returns and a member's loans. Every rule is in one service behind both.</p>

<h2>An everyday analogy</h2>
<p>A library with a front desk and a self-service machine. Both ask the same librarian's rule book; the machine does not keep its own photocopy that nobody updates.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Controller</strong>: reads the request (ids from the web, card and barcode from the kiosk).</li>
<li><strong>Service</strong>: finds the member and book, applies every rule, decides.</li>
<li><strong>Repository</strong>: saves the loan, or the return and its fine.</li>
<li><strong>Back out</strong>: a refusal becomes the same <code>409</code> with a reason, whichever way in was used.</li>
</ol>

<details class="qa check"><summary>Check yourself: the library changes the limit from 3 books to 5. How many files change?</summary><p>One line in <code>LoanService</code> (and its test). Neither controller knows the limit exists.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No database.</strong> Repositories are interfaces with in-memory implementations; a database version would replace them without changing the service.</li>
<li><strong>No sign-in.</strong> Members are named by id or card.</li>
<li><strong>No payments.</strong> Fines are recorded; challenge 1 records paying them.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>City Library</strong> (a fictional public library) lends books through its website and a self-service kiosk. The rules were written into the website's controller and copied into the kiosk's. The copies drifted, so the kiosk enforced different rules from the desk, and members found out first.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a member with fewer than 3 books and no fine, <b>then</b> a loan for 14 days (<code>201</code>), from the web or the kiosk.</li>
<li><b>Given</b> a member with 3 books out, <b>then</b> <code>409</code> LIMIT_REACHED, from either way in.</li>
<li><b>Given</b> a member with an unpaid fine, <b>then</b> <code>409</code> UNPAID_FINE, from either way in.</li>
<li><b>Given</b> a book already on loan, <b>then</b> <code>409</code> BOOK_ON_LOAN.</li>
<li><b>Given</b> a return 5 days late, <b>then</b> a fine of ₹25, added to the member; returning twice is <code>409</code> ALREADY_RETURNED.</li>
<li><b>Given</b> an unknown member, book, card or loan, <b>then</b> <code>404</code>; a missing field, <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Demo rules: 3 books at a time, 14 days per loan, ₹5 per late day, no loans with a fine unpaid.</li>
<li>Controllers hold no rules; the service holds all of them; repositories only store and find.</li>
<li>Dependencies arrive through constructors; "today" comes from an injected clock, in India time.</li>
<li>Kiosk card numbers and barcodes are trimmed and upper-cased with <code>Locale.ROOT</code>.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Split an API into controller, service and repository, and say what belongs in each.</li>
<li>Use constructor injection and repository interfaces.</li>
<li>Unit-test a service with Mockito mocks.</li>
<li>Choose between a unit test, a <code>@WebMvcTest</code> slice and a full <code>@SpringBootTest</code>.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/loans</code>", "Borrow: <code>{\"memberId\", \"bookId\"}</code>. <code>201</code>."],
    ["<code>POST</code>", "<code>/loans/{id}/return</code>", "Return, with any late fine. <code>200</code>."],
    ["<code>GET</code>", "<code>/members/{id}/loans</code>", "A member's loans, by borrowing date."],
    ["<code>POST</code>", "<code>/kiosk/checkouts</code>", "Borrow at the kiosk: <code>{\"cardNumber\", \"barcode\"}</code>. Same rules."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Loan made"],
    ['<span class="pill ok">200</span>', "Returned; a member's loans"],
    ['<span class="pill warn">400</span>', "A field missing or blank"],
    ['<span class="pill warn">404</span>', "No such member, book, card or loan"],
    ['<span class="pill warn">409</span>', "A rule said no; <code>reason</code> says which"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, with "today" from the real clock. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-borrow-on-the-web", "Case 1: Asha borrows on the web", "<b>Why:</b> no books out, no fine: lent for 14 days."),
    ("02-borrow-at-the-kiosk", "Case 2: Asha borrows at the kiosk", "<b>Why:</b> card and barcode instead of ids; the same service decides."),
    ("03-a-members-loans", "Case 3: Asha's loans", "<b>Why:</b> both loans, whichever way they were made."),
    ("04-a-fourth-book-at-the-kiosk", "Case 4: Meera tries a 4th book at the kiosk", "<b>Why:</b> the kiosk that used to allow this now asks the same rule: <code>409</code> LIMIT_REACHED."),
    ("05-a-loan-with-a-fine-unpaid", "Case 5: Ravi owes ₹20", "<b>Why:</b> <code>409</code> UNPAID_FINE, with the amount."),
    ("06-a-book-already-out", "Case 6: a book already on loan", "<b>Why:</b> one copy, one loan at a time: <code>409</code> BOOK_ON_LOAN."),
    ("07-a-return", "Case 7: Meera returns a book", "<b>Why:</b> due 15 October; the fine depends on the day it was captured (₹5 a day late)."),
    ("08-an-unknown-member", "Case 8: an unknown member", "<b>Why:</b> <code>404</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A loan on 14 October", "Due 28 October; listed", "<code>aBookIsLentForFourteenDays</code>"],
    ["Card and barcode with spaces, lower case", "Normalised; lent", "<code>theKioskLendsByCardAndBarcode</code>"],
    ["Returned 5 days late", "₹25 fine; next loan refused", "<code>aLateReturnIsFinedFiveRupeesADayAndBlocksTheNextLoan</code>"],
    ["Returned on time", "No fine; the book is free again", "<code>anOnTimeReturnHasNoFineAndFreesTheBook</code>"],
    ["Book out; returned twice", "<code>409</code> with the reason", "<code>refusalsAre409WithAReason</code>"],
    ["Unknown member, book, card, loan; blank body", "<code>404</code>; <code>400</code>", "<code>unknownMembersBooksAndLoansAre404AndBadBodiesAre400</code>"],
    ["A refused loan", "Never saved", "<code>aRefusedLoanIsNeverSaved</code>"],
    ["Two books out", "One more is allowed, due in 14 days", "<code>anAllowedLoanIsSavedDueInFourteenDays</code>"],
    ["4 days late", "₹20 added to the member", "<code>aLateReturnAddsTheFineToTheMember</code>"],
    ["A refusal, through the web layer only", "<code>409</code> with the reason", "<code>aRefusalFromTheServiceBecomesA409WithItsReason</code>"],
    ["A blank body, through the web layer only", "<code>400</code>; the service is never called", "<code>anInvalidBodyNeverReachesTheService</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Business rules in controllers, copied into a second entry point and drifting.</p>
<p>The first test runs the two inline copies side by side: the web says no, the kiosk says yes, for a 4th book and for a member with a fine. The second sends the same members through the real web API and the real kiosk: the same <code>409</code> and the same reason from both. While building, letting the kiosk save loans without the service turned 1 test red, an off-by-one in the limit turned 2 red, and dropping the fine rule turned 2 red.</p>
</div>
""" + code(read(T + "RulesInControllersTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "LoanController.java", dwn("The web way in: HTTP to service calls and back.",
        "No rule here, only translation; validation of the body's shape stays at the edge.",
        "The trap: the rules written here, then copied.")),
    (J + "KioskController.java", dwn("The kiosk way in: card and barcode instead of ids.",
        "A second controller, the same service: a new way in adds no rules.",
        "A kiosk with its own copy of the rules.")),
    (J + "LoanErrors.java", "<p>One <code>@RestControllerAdvice</code> turns the service's refusals and not-founds into problems for both controllers.</p>"),
    (J + "LoanService.java", dwn("Every rule, with constructor injection and an injected clock.",
        "One place to read, change and unit-test the rules.",
        "Rules spread across controllers.",
        "<ul><li>Refusals carry a <code>Reason</code>, so every way in explains them the same way.</li><li><code>synchronized</code>: the checks and the save cannot interleave. Safe while one instance runs; across servers, the database must enforce it.</li></ul>")),
    (J + "Repositories.java", dwn("The three repository interfaces.",
        "The service depends on what it needs, not on how it is stored.",
        "A service that talks to maps or SQL directly.")),
    (J + "InMemoryRepositories.java", "<p>In-memory implementations with the demo data. A database version would implement the same interfaces.</p>"),
    (J + "Model.java", "<p>Members, books and loans as records: data only.</p>"),
    ("src/main/resources/application.yaml", "<p>Problem bodies for framework errors.</p>"),
    (J + "LibraryApplication.java", "<p>Entry point, and the clock in India time.</p>"),
]
tree = """stations/028-library-book-loans-in-layers/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/citylibrary/loans/
│   ├── LoanController.java   ├── KioskController.java   ├── LoanErrors.java      (web layer)
│   ├── LoanService.java                                                          (rules)
│   ├── Repositories.java     ├── InMemoryRepositories.java                       (storage)
│   └── Model.java            └── LibraryApplication.java
├── src/test/java/com/citylibrary/loans/   (see Tests)
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
<p>Meera has 3 books out. Try both ways in.</p>
""" + code("""curl -i -X POST http://localhost:8080/loans -H "Content-Type: application/json" -d '{"memberId":"m-3","bookId":"b-1"}'
curl -i -X POST http://localhost:8080/kiosk/checkouts -H "Content-Type: application/json" -d '{"cardNumber":"CL-0003","barcode":"LIB100001"}'""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>409</code> BOOK_ON_LOAN for b-6, b-7, b-8", "Meera has them out in the demo data.", "Use b-1 to b-5."],
    ["A fine on the first return", "Meera's books were due on 15 October 2026.", "Expected after that date: ₹5 a day."],
    ["<code>release version 25 not supported</code>", "Maven is using an older JDK.", "Point <code>JAVA_HOME</code> at JDK 25, or add <code>-Djava.version=21</code>."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels: web layer, rules, storage.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>LoanContractTest</code> ({cnt('LoanContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>RulesInControllersTrapTest</code> ({cnt('RulesInControllersTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "The rules alone, with Mockito", f"<code>LoanServiceTest</code> ({cnt('LoanServiceTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "The web layer alone, with @WebMvcTest", f"<code>LoanControllerSliceTest</code> ({cnt('LoanControllerSliceTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Three kinds of test, side by side</h2>
""" + table(["Test", "Starts", "Replaces", "Use it for"], [
    ["<code>LoanServiceTest</code>", "Nothing: plain JUnit", "Repositories, with Mockito mocks", "Rules: fast, exact, every edge"],
    ["<code>LoanControllerSliceTest</code>", "The web layer only", "The service, with <code>@MockitoBean</code>", "HTTP: status codes, validation, error bodies"],
    ["<code>LoanContractTest</code>", "The whole app", "Only the clock", "That the layers work together"]]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "RulesInControllersTrapTest.java", "<p>Written first: the two drifted copies, and the real web and kiosk agreeing.</p>"),
    (T + "LoanServiceTest.java", "<p>Mockito mocks for the repositories; checks what the service saves, and what it never saves.</p>"),
    (T + "LoanControllerSliceTest.java", "<p><code>@WebMvcTest</code> with the service mocked: HTTP only.</p>"),
    (T + "LoanContractTest.java", "<p>The whole app: borrowing, returning, fines, refusals and not-founds.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: fresh demo data, and \"today\" set by each test.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/citylibrary/loans/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=PayFineChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Pay a fine", "Beginner-friendly", 25,
    "Add <code>POST /members/{id}/fine-payments</code> with <code>{\"amountPaise\"}</code>: part or all of a fine, recorded at the desk. More than is owed is <code>422</code>; zero is <code>400</code>.",
    "both tests in <code>PayFineChallengeTest</code> pass.",
    ["Controller: one method. Service: the rule (not more than owed). Repository: <code>save</code> already exists.",
     "The advice can map this one refusal to <code>422</code> and keep the rest as <code>409</code>."],
    "challenge/PayFineChallengeTest.java", ["challenge/solution/LoanService.java", "challenge/solution/LoanController.java", "challenge/solution/LoanErrors.java", "challenge/solution/Model.java"]) + challenge(2, "Renew a loan", "Go deeper", 30,
    "Add <code>POST /loans/{id}/renewals</code>: 14 more days from the due date, at most twice, never once overdue, never with a fine owed. Every new rule goes in the service.",
    "both tests in <code>RenewLoanChallengeTest</code> pass, and the station's tests still pass.",
    ["The loan needs a renewal count; keep the old record constructor so existing code still compiles.",
     "Write the new rules as <code>LoanServiceTest</code>-style unit tests first: they are the fast ones."],
    "challenge/RenewLoanChallengeTest.java", ["challenge/solution/LoanService.java", "challenge/solution/LoanController.java", "challenge/solution/Model.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Where does each rule belong?</h2>
<p>For each rule, decide: the entity (a <code>Loan</code> knows if it is overdue), the service (the 3-book limit needs other loans), or the database (one active loan per book, as a unique index). Which rules would you enforce in two places, and why is that different from the trap?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the two drifted copies, and the real API from both ways in.</li>
<li>Define the repository interfaces the rules need; implement them in memory.</li>
<li>Move every rule into the service; unit-test it with Mockito.</li>
<li>Thin the controllers to translation; slice-test the web layer; contract-test the whole.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Rules in a service, thin controllers", "A class and some interfaces.", '<span class="pill ok">Chosen</span>'],
    ["Rules in controllers", "Every new way in copies them.", '<span class="pill bad">The trap</span>'],
    ["Rules on the entities (rich domain model)", "Good for rules about one record; rules across records still need a service.", '<span class="pill warn">Mix with a service</span>'],
    ["Spring Data repositories", "A database; no hand-written implementations.", '<span class="pill warn">With a database</span>'],
    ["Field injection (<code>@Autowired</code> on fields)", "Hidden dependencies; tests need Spring or reflection.", '<span class="pill bad">Avoid</span>']]) + """
<h2>Database design</h2>
<p>None in this station. With a database: <code>members</code>, <code>books</code>, <code>loans</code> (member, book, borrowed_on, due_on, returned_on, fine_paise), and a unique index on <code>loans(book_id) WHERE returned_on IS NULL</code>, so two servers can never lend the same book twice.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>More ways in</dt><dd>A mobile app, a staff tool or a batch import each get a controller (or a listener) that calls the same service. None gets its own rules.</dd>
<dt>Concurrency</dt><dd><code>synchronized</code> keeps one instance correct. With several instances, the database must enforce "one active loan per book" and the limit inside a transaction.</dd>
<dt>Testing</dt><dd>Most tests should be fast service tests; a few slice tests for HTTP; fewer full-app tests to prove the wiring.</dd>
<dt>Change</dt><dd>A new rule touches the service and its test. If it touches a controller, it is in the wrong place.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What goes in a controller, a service and a repository?", "Controller: HTTP in and out, input shape. Service: business rules and decisions. Repository: storing and finding records. Rules never go in the controller."),
    ("Why constructor injection?", "Dependencies are explicit and final, the object is complete after construction, and a test can build it with mocks in one line, without Spring."),
    ("Why repository interfaces?", "The service depends on what it needs, not on how it is stored: an in-memory, JDBC or JPA implementation can be swapped without touching the rules."),
    ("Unit test, @WebMvcTest or @SpringBootTest?", "Unit tests for rules (fast, precise); @WebMvcTest for HTTP mapping with the service mocked; @SpringBootTest to prove the whole app works together. Most tests should be the first kind."),
    ("What does a Mockito mock let you check?", "What the code under test asked for and saved: verify(loans, never()).save(any()) proves a refused loan is never stored."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "Both ways in give the same answer for every case."],
    ["Layers", "No rule in a controller.", "You can say where each rule in challenge 3 belongs."],
    ["Testing", "A Mockito test for each rule.", "You can choose the right kind of test for a new change."],
    ["Explanation", "Why rules drift when copied.", "Why a database constraint is still needed with many servers."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any new endpoint:</p>
<ul class="rules">
<li>Does the controller decide anything a business person would call a rule?</li>
<li>Is any rule written in more than one place?</li>
<li>Are dependencies passed in through the constructor?</li>
<li>Is there a fast unit test for each rule?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
