"""Station 078 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 78,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Security 7 (HTTP Basic, JDBC users) · authorisation in SQL · JdbcClient · PostgreSQL 17 · Testcontainers",
    "simulation": "Customers, accounts and statement lines are demo rows, not Tijori's; no bank is involved. Balances are numbers in a table: nothing is paid or transferred.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tijori/accounts/"
T = "src/test/java/com/tijori/accounts/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("IDOR", "Insecure direct object reference: the server returns whatever id you ask for, without asking whose it is.", "A cloakroom that hands over any coat for any ticket number you say.", "the old statement page"),
    ("Ownership check", "Is this signed-in person allowed this record?", "The cloakroom checks the ticket is yours.", "<code>account_holders</code>"),
    ("Authorisation in the query", "The WHERE clause names both the record and the person, so a stranger's request finds no row.", "Looking in your own locker, not checking each locker's name tag.", "<code>JOIN ... c.email = ?</code>"),
    ("404 or 403", "404: no such thing (for you). 403: it exists, and you may not do this.", "\"No coat under that number\" against \"that coat is yours, but not the umbrella\".", "stranger 404, balance-only 403"),
    ("Joint account", "One account, several holders.", "A shared locker.", "account 1003"),
    ("Paise", "Money as whole paise, never fractions of a rupee in a floating point.", "Counting coins, not weighing them.", "<code>balance_paise</code>"),
]
STORY = [
    ("A number in the URL", "Tijori's statement page opened <code>/accounts/1001/statements</code>. Account numbers count up."),
    ("The next number", "A customer changed 1001 to 1002 and saw another customer's statement. The server had looked the account up by its number alone."),
    ("The fix", "Every query names the signed-in customer as well as the account. Someone else's account finds no row, and gets the same 404 as a number that does not exist."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">An id in a URL is a request, not a right. Ask whose it is in the same query that fetches it.</p>

<h2>What are we building?</h2>
<p><code>GET /accounts/{id}</code> and <code>GET /accounts/{id}/statements?month=</code> that return a row only to its holders.</p>

<h2>An everyday analogy</h2>
<p>A bank teller who reads out a balance only after checking the customer's name is on that account, and who says \"no such account\" both for numbers that do not exist and for numbers that are not yours.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Sign in</strong>: email and password with every request.</li>
<li><strong>Ask</strong>: the URL names an account.</li>
<li><strong>Query</strong>: account, holders and customer joined; the signed-in email is in the WHERE clause.</li>
<li><strong>Answer</strong>: no row is 404; a holder without statement rights is 403; otherwise the data.</li>
</ol>

<details class="qa check"><summary>Check yourself: why 404 and not 403 for someone else's account?</summary><p>A 403 says the account exists. Walking through the numbers would then map every account. With 404 for both, the numbers reveal nothing: <code>walkingThroughTheNumbersFindsOnlyYourOwn</code>.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No payments.</strong> Statement lines are demo rows.</li>
<li><strong>No list of accounts.</strong> Practice, challenge 1 adds it.</li>
<li><strong>No staff access.</strong> Bank staff viewing accounts is Practice, challenge 3.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tijori</strong> (a fictional bank): changing the account id in the URL showed another customer's statement.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo data: Zoya holds 1001 and the joint 1003; Dev holds 1002, 1003 and the shop's 1004; Ravi, the shop assistant, may see 1004's balance only.</p>
<ol class="gwt">
<li><b>Given</b> a holder, <b>then</b> the account and its balance.</li>
<li><b>Given</b> a full holder and a month, <b>then</b> that month's lines with opening and closing balances that add up.</li>
<li><b>Given</b> an account that is not the caller's, or does not exist, <b>then</b> the same <code>404</code>.</li>
<li><b>Given</b> a balance-only holder asking for statements, <b>then</b> <code>403</code>.</li>
<li><b>Given</b> a holder removed from a joint account, <b>then</b> <code>404</code> on the next request.</li>
<li><b>Given</b> an id or month that is not one, <b>then</b> <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Every query that reads an account names the signed-in customer.</li>
<li>Answers never tell an outsider whether an account number exists.</li>
<li>Money is integer paise.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Recognise IDOR and fix it in the query, not in a later check.</li>
<li>Choose 404 or 403 on purpose.</li>
<li>Model joint holders and partial access in tables.</li>
<li>Test by walking through ids as an attacker would.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/accounts/{id}</code>", "Kind, name, balance in paise, and this sign-in's access (<code>full</code> or <code>balance_only</code>)."],
    ["<code>GET</code>", "<code>/accounts/{id}/statements?month=YYYY-MM</code>", "That month's lines, oldest first, with opening and closing balances."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "The account or statement, for a holder"],
    ['<span class="pill warn">400</span>', "An id that is not a number; a month that is not <code>YYYY-MM</code>"],
    ['<span class="pill warn">401</span>', "No or wrong credentials"],
    ['<span class="pill warn">403</span>', "A balance-only holder asking for statements; a path with no rule"],
    ['<span class="pill warn">404</span>', "Not the caller's account, or no such account: the same answer"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-zoyas-own-account", "Case 1: Zoya's own account", "<b>Why:</b> she is a full holder."),
    ("02-the-next-number", "Case 2: the next number, 1002", "<b>Why:</b> Dev's: <code>404</code>."),
    ("03-a-number-that-does-not-exist", "Case 3: a number that does not exist", "<b>Why:</b> the same <code>404</code> as case 2, word for word."),
    ("04-zoyas-september-statement", "Case 4: Zoya's September statement", "<b>Why:</b> opening plus the lines is the closing balance; October's bill is after it."),
    ("05-the-joint-account-as-dev", "Case 5: the joint account, as Dev", "<b>Why:</b> both holders see it."),
    ("06-the-shop-account-balance-only", "Case 6: the shop's account, as Ravi", "<b>Why:</b> balance only, and the answer says so."),
    ("07-the-shop-statement-balance-only", "Case 7: the shop's statement, as Ravi", "<b>Why:</b> <code>403</code>: a holder, without the right to statements."),
    ("08-a-month-that-is-not-a-month", "Case 8: month 2026-13", "<b>Why:</b> <code>400</code>."),
    ("09-no-credentials", "Case 9: no credentials", "<b>Why:</b> <code>401</code> with a Basic challenge."),
]) + """
<h2>Who holds what</h2>
<p class="muted">From <code>psql</code> in <code>docs/capture.sh</code>.</p>
""" + code(read("docs/captures/holders.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Own account", "<code>200</code>", "<code>aCustomerSeesTheirAccount</code>"],
    ["A month's statement", "Lines in order; balances add up", "<code>aMonthsStatementHasItsLinesAndBalancesThatAddUp</code>"],
    ["A joint account", "Both holders", "<code>bothHoldersOfAJointAccountSeeIt</code>"],
    ["A month with no lines", "Empty, opening equals closing", "<code>aMonthWithNoLinesIsEmptyNotAnError</code>"],
    ["Unknown account; bad id or month", "<code>404</code>; <code>400</code>", "<code>unknownAccountsAre404AndBadParametersAre400</code>"],
    ["No, wrong or unknown credentials", "<code>401</code>", "<code>noOrWrongCredentialsAre401</code>"],
    ["Balance-only holder; a stranger", "<code>403</code> for statements; <code>404</code>", "<code>aBalanceOnlyHolderGets403ForStatementsAndAStrangerGets404</code>"],
    ["A joint holder removed", "<code>404</code> on the next request", "<code>removingAJointHolderTakesEffectOnTheNextRequest</code>"],
    ["SQL-looking, negative, huge, encoded ids; an injected month", "<code>400</code> or <code>404</code>, never an error", "<code>oddIdsAndMonthsAre400Or404NeverAnError</code>"],
    ["Writes and unknown paths", "<code>403</code>", "<code>writesAndOtherPathsAreRefused</code>"],
    ["Rules written by plain SQL", "Refused by named constraints", "<code>accountRulesHoldWithoutJava</code>"],
    ["A debit that would overdraw", "Line and balance both rolled back", "<code>aDebitThatWouldOverdrawLeavesNeitherLineNorBalance</code>"],
    ["The current month", "Closes at the current balance", "<code>theNewestStatementClosesAtTheCurrentBalance</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Trusting the id in the URL without an ownership check (IDOR).</p>
<ul>
<li><strong>The next number.</strong> The old query returns Dev's account 1002 to Zoya. The API: <code>404</code>, for the account and its statements.</li>
<li><strong>Walking the numbers.</strong> Zoya asks for 1000 to 1005. Only 1001 and 1003 answer; the others, Dev's and the ones that do not exist, look the same.</li>
<li><strong>The control.</strong> Her own account and statement work.</li>
</ul>
<p>While building, each part was undone once: trusting the id (the customer join made always true) turned 4 tests red; no balance-only check 1; <code>denyAll</code> replaced by <code>authenticated</code> 1. Two changes turned nothing red, explained in the Code tab.</p>
</div>
""" + code(read(T + "UrlIdTrustTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SecurityConfig.java", dwn("Sign-in against the customers table, and the two paths.",
        "HTTP Basic, bcrypt, stateless; both paths need a sign-in; everything else refused. Which accounts is decided per query.",
        "Writes or new paths open to every signed-in customer.")),
    (J + "AccountController.java", dwn("The two endpoints.",
        "The customer comes from the sign-in, the account from the URL; the month is checked before it is parsed.",
        "A parameter choosing the customer, or a bad month turning into a 500.")),
    (J + "Accounts.java", dwn("The ownership rule, inside the SQL.",
        "The account query joins holders and customers on the signed-in email; no row is <code>404</code>; balance-only holders get <code>403</code> for statements; the statement reads in one REPEATABLE READ transaction.",
        "IDOR, and statements whose lines and balances disagree.",
        "<ul><li>The lines query repeats the ownership join. Removing it turned no test red, because <code>account()</code> already refused; it stays so the query is safe on its own if someone reuses it.</li><li>No test proves the REPEATABLE READ: none makes a payment commit between the statement's queries. Under READ COMMITTED it could, and the opening balance would be wrong for that one request.</li></ul>")),
    (J + "ProblemResponses.java", "<p>401 with a Basic challenge and 403 in the same problem JSON as every other error.</p>"),
    (M + "V1__customers_accounts_holders.sql", dwn("Customers, accounts, holders, statement lines.",
        "A holder table with an access level; non-negative balances; non-zero lines.",
        "An account with no rule about who may see it.")),
    (M + "V2__demo_data.sql", "<p>Three customers, four accounts (one joint, one shop), September 2026 lines.</p>"),
    ("src/main/resources/application.yaml", "<p>The database connection.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "AccountsApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/078-customers-see-only-their-own-accounts/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/tijori/accounts/
│   ├── SecurityConfig.java   ├── AccountController.java   ├── Accounts.java
│   ├── ProblemResponses.java   └── AccountsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__customers_accounts_holders.sql, V2__demo_data.sql
├── src/test/java/com/tijori/accounts/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
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
<p>Walk through the account numbers as Zoya, as an attacker would:</p>
""" + code("""for id in 1000 1001 1002 1003 1004 1005; do
  curl -s -o /dev/null -w "$id %{http_code}\\n" -u zoya@example.com:zoya-demo-pass http://localhost:8080/accounts/$id
done""", "bash") + """
<p>Only 1001 and 1003 print 200. 1002 and 1004 exist, but print the same 404 as 1000 and 1005.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>403</code> for someone else's account", "The ownership check runs after the lookup and answers \"forbidden\".", "Put the customer into the query, and answer 404."],
    ["A statement whose balances do not add up", "Lines and balance read at different moments.", "Read them in one REPEATABLE READ transaction, as <code>Accounts.statement</code> does."],
    ["<code>Could not find a valid Docker environment</code>", "Docker is not running.", "Start Docker Desktop or the Docker service."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>AccountContractTest</code> ({cnt('AccountContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>UrlIdTrustTrapTest</code> ({cnt('UrlIdTrustTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>AccountDatabaseTest</code> ({cnt('AccountDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, one user accessing another user's data, malicious input", f"<code>AccountSecurityTest</code> ({cnt('AccountSecurityTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Spring Security 7.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "UrlIdTrustTrapTest.java", "<p>Written first: the old lookup by id, and the same requests to the API, including a walk through the numbers.</p>"),
    (T + "AccountSecurityTest.java", "<p>401, 404 against 403, a removed joint holder, odd ids and months, writes.</p>"),
    (T + "AccountDatabaseTest.java", "<p>Every named constraint with plain SQL; a debit that overdraws rolls back with its line.</p>"),
    (T + "AccountContractTest.java", "<p>Accounts and statements through HTTP, balances that add up.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: request helpers with HTTP Basic.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tijori/accounts/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=MyAccountsChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "My accounts", "Beginner-friendly", 15,
    "<code>GET /accounts</code> lists the signed-in customer's own accounts, by number, with this sign-in's access.",
    "the test in <code>MyAccountsChallengeTest</code> passes.",
    ["The same joins as the account query, without the account id.", "The filter chain needs a rule for the new path."],
    "challenge/MyAccountsChallengeTest.java", ["challenge/solution/Accounts.java", "challenge/solution/AccountController.java", "challenge/solution/SecurityConfig.java"]) + challenge(2, "Statement as CSV", "Go deeper", 30,
    "<code>GET /accounts/{id}/statements.csv?month=</code>: the same rules as the JSON statement, amounts in rupees with two decimals, descriptions with a comma quoted, as a download.",
    "both tests in <code>StatementCsvChallengeTest</code> pass.",
    ["Call the same <code>statement</code> method: the rules come with it.",
     "<code>BigDecimal.valueOf(paise, 2).toPlainString()</code> turns paise into rupees without a double."],
    "challenge/StatementCsvChallengeTest.java", ["challenge/solution/AccountController.java", "challenge/solution/SecurityConfig.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>When bank staff need to look</h2>
<p>A support agent must see a customer's statement to answer a complaint. Design it without opening every account to every agent: a ticket the customer agreed to, a time limit, read-only access, and an audit the customer can see. Which parts belong in the query, and which in a separate check?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old lookup, and a walk through the numbers.</li>
<li>Model holders with an access level.</li>
<li>Join the signed-in customer into every account query.</li>
<li>Decide 404 and 403 on purpose, and test both.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Customer in the WHERE clause; 404 for strangers", "Every query must carry the customer.", '<span class="pill ok">Chosen</span>'],
    ["Look up by id only", "IDOR: any number, any account.", '<span class="pill bad">The trap</span>'],
    ["Look up, then check, then 403", "Safe for the data; tells outsiders which numbers exist.", '<span class="pill warn">Leaks existence</span>'],
    ["Random account ids (UUIDs) in URLs", "Harder to guess; still IDOR when one leaks.", '<span class="pill warn">A second layer, never the only one</span>'],
    ["PostgreSQL row-level security", "Rules in the database for every query; the app must set the customer per connection.", '<span class="pill warn">Strong; needs care with pooling</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>account_holders</code>", "PK (account, customer), access <code>full</code> or <code>balance_only</code>", "Joint accounts and partial access, as data."],
    ["<code>accounts_balance_nonnegative</code>", "CHECK", "No writer can overdraw a savings account."],
    ["<code>transactions_amount_nonzero</code>, <code>_description_length</code>", "CHECKs", "Every line moves something and can be shown."],
    ["<code>account_holders_by_customer</code>", "Index", "The ownership join stays fast."]]) + """
<p><strong>Transaction boundary:</strong> a statement is one REPEATABLE READ read-only transaction. A line and its balance change are written in one transaction (the rollback test).</p>
""" + code(read(M + "V1__customers_accounts_holders.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Every new query</dt><dd>IDOR comes back with each new endpoint. A code review rule (\"which customer does this query name?\") and a test that walks ids for each endpoint keep it out.</dd>
<dt>Watching</dt><dd>Many 404s for one customer across nearby numbers is someone walking ids: alert on it.</dd>
<dt>Logs</dt><dd>Account numbers in logs are personal data; statement lines more so.</dd>
<dt>Standards</dt><dd>OWASP's API Security Top 10 (2023 edition) lists this first, as Broken Object Level Authorization.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is IDOR?", "Returning a record because its id was asked for, without checking the caller may see it. The fix is an ownership condition in the same query."),
    ("404 or 403 for someone else's record?", "404 when even its existence is private, as for bank accounts; 403 when the caller may know it exists but not do this, like a balance-only holder asking for statements."),
    ("Do random ids fix IDOR?", "They make guessing harder, not access correct. Ids leak through links, logs and screenshots."),
    ("Why put the check in the query and not after it?", "The query cannot return what it never selects. A check after it can be forgotten in one code path, and its answer tends to leak existence."),
    ("How do you test for IDOR?", "Sign in as one user and ask for another's ids, and for ids that do not exist; the answers must match."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Ownership", "Customer in every query.", "Joint and partial access as data."],
    ["Answers", "404 for strangers.", "403 only where existence may be known."],
    ["Money", "Paise as integers.", "Statements that add up, read consistently."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("403 \"belongs to another customer\"",
     "The lookup by id, then a holder check, keeps the data safe but answers differently for numbers that exist: walking the numbers now maps every account. The answer itself confirms the account is someone else's.",
     "<code>changingTheIdInTheUrlShowedTheNextCustomersAccount</code>, <code>walkingThroughTheNumbersFindsOnlyYourOwn</code> and <code>removingAJointHolderTakesEffectOnTheNextRequest</code> fail (they expect 404)."),
    ("Balance-only holders see statements",
     "The access level is no longer read: the account query returns <code>'full'</code> for everyone, so the shop assistant reads every sale and every withdrawal.",
     "<code>aBalanceOnlyHolderGets403ForStatementsAndAStrangerGets404</code> fails."),
    ("The lines query trusts the id",
     "It is safe today only because a check ran first. Reused anywhere else, it is the original IDOR.",
     "No test fails on this alone: the check above it still runs. That is why it is a review finding."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate splits the account query into \"two simple queries\": find the account, then check the holder, with a clear 403 when it is someone else's. The lines query drops its joins, since \"the holder was checked above\". Read the file and list every problem before opening the findings.</p>
<p class="path">review/Accounts.java</p>
""" + code(read("review/Accounts.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">No customer sees another's data in this version. It still fails review: it tells strangers which accounts exist, and it gives the shop assistant the statements.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
