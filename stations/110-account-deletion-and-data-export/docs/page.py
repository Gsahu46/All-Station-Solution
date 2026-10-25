"""Station 110 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 110,
    "stack": "Spring Boot 4.1.1 · Java 25 · JdbcClient · @Scheduled jobs · Spring Security with database users · PostgreSQL 17 (jsonb, information_schema) · Testcontainers",
    "simulation": "Members, posts, invoices and phone numbers are demo data; nothing is sent to anyone. The legal points are summarised for learning, not legal advice: the retention periods and the 90-day deadline here are demo rules.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/chaupal/accounts/"
T = "src/test/java/com/chaupal/accounts/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Personal data", "Anything that identifies a person: name, phone, email, what they wrote, where they signed in from.", "Your name on a parcel.", "phone, posts, sign-ins"),
    ("Data inventory", "A list of every place personal data is kept and what happens to it.", "A list of every cupboard in the house, and what is in it.", "<code>PersonalData</code>"),
    ("Delete or anonymise", "Remove the row, or keep the row with nothing that identifies the person in it.", "Shredding a form, or blacking out the name on it.", "posts deleted; the user row anonymised"),
    ("Keeping what the law requires", "Some records must stay for a set time, deletion request or not.", "A shop keeps its sales receipts for the tax office.", "invoices, sign-in records"),
    ("Export as a job", "Collecting someone's data takes a while; it is prepared in the background and fetched later.", "Ordering a photo print and picking it up.", "<code>POST /me/data-export</code>"),
    ("DPDP Act", "India's Digital Personal Data Protection Act, 2023, and its Rules of 2025.", "The rulebook for how a business treats your data.", "the station's reason"),
]
STORY = [
    ("Delete my account", "A Chaupal member asked for a copy of their data and then for their account to be deleted, as India's data protection law lets them."),
    ("Still in nine tables", "The deletion code followed the member's user id. Weeks later their phone number was still in the table of sign-in codes, in another member's address-book upload, in a queue of unsent notifications and in old support tickets: tables that know the number, not the id."),
    ("The fix", "An inventory of every table, checked against the database on every build. Deleting runs the whole inventory in one transaction; what the law requires is kept, and says why; and a test searches every text column of every table for the number afterwards."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">You can only delete what you know you have. Keep the list of where personal data lives, and make the build fail when it is incomplete.</p>

<h2>What are we building?</h2>
<p>A data export and an account deletion that reach every copy of a person's data, keep only what the law requires, and prove it.</p>

<h2>An everyday analogy</h2>
<p>Moving out of a flat: you do not just take your name off the door. You collect your post, cancel deliveries, take your number off the building's contact list, and leave only the rent receipts the landlord must keep.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Inventory</strong>: every table is listed with how it points at a person and what happens to it.</li>
<li><strong>Close</strong>: <code>DELETE /me</code> closes the account at once and books the erasure.</li>
<li><strong>Erase</strong>: a job runs the inventory in one transaction: delete, anonymise, or keep with a reason.</li>
<li><strong>Prove</strong>: a test searches every text column for the person afterwards; another fails when a table is missing from the inventory.</li>
</ol>

<details class="qa check"><summary>Check yourself: why not delete the user row and let ON DELETE CASCADE do the rest?</summary><p>Cascades follow foreign keys. The sign-in codes, others' address books and the notification queue hold the phone number with no key to the user row, so nothing cascades to them. And the invoices, which do have a key, must not be deleted at all.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>Not legal advice.</strong> The law is summarised with its status; the numbers are demo rules.</li>
<li><strong>No backups or log files.</strong> They are discussed in Production and challenge 3, not simulated.</li>
<li><strong>No consent screens.</strong> Consent notices are another part of the DPDP Rules.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Chaupal</strong> (a fictional community app): a member's phone number survived their deletion request in nine tables.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo rules: erasure due within 90 days of the request (done by the next job run, every 5 s here); sign-in records kept 180 days; invoices kept until their retention date.</p>
<ol class="gwt">
<li><b>Given</b> a member, <b>then</b> <code>POST /me/data-export</code> answers <code>202</code>; the export becomes READY and holds their own data, not others' address books that mention them.</li>
<li><b>Given</b> <code>DELETE /me</code>, <b>then</b> <code>202</code>; from that moment the account cannot sign in.</li>
<li><b>Given</b> the erasure has run, <b>then</b> the person's phone, email and name appear only in invoices, and nowhere else in any table.</li>
<li><b>Given</b> another member's export id, or an unknown one, <b>then</b> <code>404</code>; not ready, <code>409</code>; a support account, <code>403</code>; no sign-in, <code>401</code>.</li>
<li><b>Given</b> a new table, <b>then</b> the build fails until the inventory says what to do with it.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>The erasure is all or nothing.</li>
<li>A deleted account's row holds nothing that identifies the person: a named CHECK.</li>
<li>Logs never hold the data being erased.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Build a personal data inventory and keep it true with a test.</li>
<li>Choose delete, anonymise or keep, per table, with a reason.</li>
<li>Run exports and erasures as background jobs.</li>
<li>Prove an erasure by searching the data, not by trusting the code.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/me/data-export</code>", "Ask for a copy of your data: <code>202</code> and its address."],
    ["<code>GET</code>", "<code>/me/data-exports/{id}</code>", "PENDING or READY."],
    ["<code>GET</code>", "<code>/me/data-exports/{id}/file</code>", "The JSON, as an attachment."],
    ["<code>DELETE</code>", "<code>/me</code>", "Close the account and book the erasure: <code>202</code> with its due date."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">202</span> / <span class="pill ok">200</span>', "Accepted as a job / read"],
    ['<span class="pill warn">400</span>', "An id that is not a number"],
    ['<span class="pill warn">401</span>', "Not signed in, or the account is closed"],
    ['<span class="pill warn">403</span>', "A support account: it has no \"me\""],
    ['<span class="pill warn">404</span>', "No such export of yours"],
    ['<span class="pill warn">409</span>', "The export is not ready yet"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. <code>Date</code>, connection and standard security headers are left out.</p>
""" + code(read("docs/captures/scan-before.txt").strip(), "text") + examples([
    ("01-imran-asks-for-his-data", "Case 1: Imran asks for his data", "<b>Why:</b> <code>202</code>: a job."),
    ("02-the-export-is-ready", "Case 2: a moment later", "<b>Why:</b> READY."),
    ("03-the-file", "Case 3: the file", "<b>Why:</b> his account, profile, posts, comments, invoices, sign-ins, tickets and his own address book; not Zoya's upload that mentions him."),
    ("04-zoya-tries-imrans-export", "Case 4: Zoya asks for export 1", "<b>Why:</b> <code>404</code>: it is not hers."),
    ("05-a-support-account-has-no-me", "Case 5: a support account calls <code>DELETE /me</code>", "<b>Why:</b> <code>403</code>."),
    ("06-imran-deletes-his-account", "Case 6: Imran deletes his account", "<b>Why:</b> <code>202</code>; due within 90 days."),
    ("07-and-can-no-longer-sign-in", "Case 7: Imran signs in again", "<b>Why:</b> <code>401</code>: closed at once."),
]) + """
<h2>After the erasure</h2>
<p class="muted">The same search of every text column, then his row and the ledger:</p>
""" + code(read("docs/captures/scan-after.txt").strip(), "text") + code(read("docs/captures/after.txt").strip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["The old delete by user id", "The number left in 3 tables besides invoices", "<code>theOldWayLeavesHisNumberInTablesThatDoNotKnowHisUserId</code>"],
    ["The API's erasure", "Phone and name only in invoices; email, posts gone; Zoya's post kept; the account closed", "<code>theApiErasesHimEverywhereExceptWhatTheLawKeeps</code>"],
    ["An export", "A job; the person's own data, not others' that mention them", "<code>anExportIsAJobAndHoldsThePersonsOwnDataOnly</code>"],
    ["Deleting", "Closed at once; due within 90 days; recent sign-ins kept, old ones gone", "<code>deletingClosesTheAccountAtOnceAndBooksTheErasureWithin90Days</code>"],
    ["Unknown export; bad id", "<code>404</code>; <code>400</code>", "<code>anUnknownExportIs404AndABadIdIs400</code>"],
    ["No sign-in; a support account", "<code>401</code>; <code>403</code>", "<code>noSignInIs401AndASupportAccountHasNoMe</code>"],
    ["Another member's export", "<code>404</code>", "<code>onePersonCannotReadAnothersExport</code>"],
    ["Not ready", "<code>409</code>", "<code>anExportNotYetReadyIs409</code>"],
    ["A table missing from the inventory", "The build fails", "<code>everyTableHasAnEntryInTheInventoryAndEveryEntryATable</code>"],
    ["An entry with no reason or no SQL", "The build fails", "<code>everyEntryThatKeepsOrDeletesSaysWhy</code>"],
    ["Plain SQL against the rules", "Named constraints", "<code>theRulesAreNamedConstraintsInTheDatabase</code>"],
    ["An erasure that fails half-way", "Nothing erased", "<code>anErasureThatFailsHalfWayErasesNothing</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Deleting from one table while copies remain in logs, backups and other tables.</p>
<ul>
<li><strong>The old way.</strong> Delete every row that hangs off the user id, blank the user row. Every table that knows the id is clean. The test then searches every text column of every table for his number: it is still in other members' address-book uploads, the unsent notification queue and the sign-in codes, besides the invoices the law keeps.</li>
<li><strong>The API.</strong> The same search after <code>DELETE /me</code> finds the number in the invoices only.</li>
</ul>
<p>While building, each part was undone once: the sign-in codes left out turned 1 test red; others' address books left out 1; the user row not anonymised 2; no transaction around the erasure 1; deleted accounts still able to sign in 1; others' address books in the export 1; another member's export readable 1; recent sign-in records deleted 1; a table missing from the inventory 1.</p>
</div>
""" + code(read(T + "AccountDeletionTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "PersonalData.java", dwn("The inventory.", "Every table: what links it to a person, the action, the reason, the SQL. The erasure runs it in order.", "A table nobody remembered.",
        "<ul><li>Tables found by phone, not user id, are the ones the old code missed: <code>otp_requests</code>, <code>notification_outbox</code>, and <code>contact_uploads.contact_phone</code> in other members' rows.</li></ul>")),
    (J + "Accounts.java", dwn("Exports and erasures.", "Exports built from a list of the person's own data; the erasure runs the inventory in one transaction; a nightly purge of old sign-ins.", "Half an erasure; one failing account holding up the others.",
        "<ul><li>The job calls <code>erase</code> through the Spring proxy (<code>self</code>), so each account gets its own transaction; called directly, <code>@Transactional</code> would be skipped.</li></ul>")),
    (J + "MeController.java", "<p>The four endpoints; \"me\" is always the signed-in account.</p>"),
    (J + "SecurityConfig.java", dwn("Sign-in.", "Accounts from the database, ACTIVE only: a deletion request closes the account at once.", "Signing in to an account being erased.")),
    (M + "V1__chaupal.sql", dwn("Tables.", "Named CHECKs: a deleted user holds nothing; erasures due within 90 days; invoices kept past their date of issue.", "A \"deleted\" account with its phone number still in it.")),
    (M + "V2__demo_data.sql", "<p>Imran, Zoya and a support account; Imran's number is in seven columns of seven tables (the scan before, on the API contract tab).</p>"),
    ("src/main/resources/application.yaml", "<p>Job timings.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
]
tree = """stations/110-account-deletion-and-data-export/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/chaupal/accounts/
│   ├── PersonalData.java   ├── Accounts.java   ├── MeController.java   ├── SecurityConfig.java
│   └── ProblemResponses.java, AccountsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__chaupal.sql, V2__demo_data.sql
├── src/test/java/com/chaupal/accounts/   (see Tests)
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
""" + code("""docker compose up -d --wait   # PostgreSQL 17 on localhost:5432
./mvnw spring-boot:run        # the API on http://localhost:8080
./mvnw test                   # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d --wait
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Add a table that holds a phone number, without touching <code>PersonalData</code>, and run the tests:</p>
""" + code("""printf 'CREATE TABLE referral_invites (id BIGSERIAL PRIMARY KEY, phone TEXT NOT NULL);\\n' > src/main/resources/db/migration/V3__invites.sql
./mvnw test -Dtest=PersonalDataInventoryTest   # fails: referral_invites has no entry""", "bash") + """
<p>Then decide what happens to it, add the entry, and run the trap test too.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>PersonalDataInventoryTest</code> fails after a migration", "A new table with no decision.", "Add an entry: action, reason, SQL."],
    ["An erasure keeps failing in the log", "Something blocks a delete (a new foreign key, for instance); it rolls back and retries.", "Add the new table to the inventory, in the right order."],
    ["<code>401</code> right after <code>DELETE /me</code>", "Expected: the account is closed.", ""]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">The inventory first, then in the order a request travels.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>AccountContractTest</code> ({cnt('AccountContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>AccountDeletionTrapTest</code> ({cnt('AccountDeletionTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>AccountDatabaseTest</code> ({cnt('AccountDatabaseTest')}), <code>PersonalDataInventoryTest</code> ({cnt('PersonalDataInventoryTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, another user's data, malicious input", f"<code>AccountSecurityTest</code> ({cnt('AccountSecurityTest')}), and the 400 in the contract test", '<span class="pill ok">pass</span>']]) + """
<p class="muted">The trap test does not trust the deletion code: it lists every text column of every table from <code>information_schema</code> and searches each one for the person's number, name and email. The jobs run when a test calls them, not on their timer: the first version let the 100 ms job run beside each test's reset of the data, and a mutation run ended in a database deadlock between the two.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "AccountDeletionTrapTest.java", "<p>Written first: the old delete and the API, searched column by column.</p>"),
    (T + "PersonalDataInventoryTest.java", "<p>The inventory against the database.</p>"),
    (T + "AccountContractTest.java", "<p>Exports, deletion, bad ids.</p>"),
    (T + "AccountSecurityTest.java", "<p>Sign-in, roles, another member's export.</p>"),
    (T + "AccountDatabaseTest.java", "<p>Named constraints; an erasure that fails half-way.</p>"),
    (T + "ApiTest.java", "<p>Shared setup and the search of every column.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/chaupal/accounts/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=ExportExpiryChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Exports expire", "Beginner-friendly", 25,
    "An export is a full copy of a person's data. Seven days after it is ready, the file answers <code>410 Gone</code>, and the job empties its content.",
    "the test in <code>ExportExpiryChallengeTest</code> passes.",
    ["Compare <code>ready_at</code> with now in the query that reads the file.",
     "An emptied export is no longer READY with content: mind the <code>data_exports_ready_has_content</code> CHECK (a new status, EXPIRED)."],
    "challenge/ExportExpiryChallengeTest.java", ["challenge/solution/V3__expiry_and_inactivity.sql", "challenge/solution/Accounts.java", "challenge/solution/MeController.java"]) + challenge(2, "Accounts nobody uses", "Go deeper", 40,
    "<code>Accounts.sweepInactive()</code>: a member with no sign-in for three years gets one notice (\"... erased in 48 hours unless you sign in\"); 48 hours after it, still with no sign-in, their erasure is booked. A sign-in after the notice keeps the account.",
    "both tests in <code>InactiveAccountChallengeTest</code> pass.",
    ["Record when the notice went out (a column, in a new migration), so one sweep never sends two.",
     "\"No sign-in since\" is the newest <code>login_events.at</code>.",
     "Reuse <code>requestDeletion</code>."],
    "challenge/InactiveAccountChallengeTest.java", ["challenge/solution/V3__expiry_and_inactivity.sql", "challenge/solution/Accounts.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>The backup from last week</h2>
<p>The database is restored from a backup taken eight days ago. Five accounts erased since then are back, with their data. Design what happens next using the <code>erasures</code> ledger (it holds no personal data, so it can live outside the backup), how long backups are kept, and what you tell a member who asks whether their data is \"really\" gone.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: delete the old way, then search every column.</li>
<li>Write the inventory, every table, with a test that compares it with the database.</li>
<li>Run it as one transaction; anonymise the user row; keep what the law requires.</li>
<li>Exports as jobs, from a list of the person's own data.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["An explicit inventory checked against the schema", "A list to keep up; the test makes it impossible to forget.", '<span class="pill ok">Chosen</span>'],
    ["Follow foreign keys to users", "No list; misses everything keyed by phone or email, and deletes what the law keeps.", '<span class="pill bad">See Review</span>'],
    ["Delete the user row with ON DELETE CASCADE", "Same blind spots, and no way to keep invoices.", '<span class="pill bad">Avoid</span>'],
    ["Anonymise everything, delete nothing", "Content can still identify (a post with a phone number in it).", '<span class="pill warn">Only where content is not personal</span>'],
    ["Crypto-shredding (encrypt per person, delete the key)", "Reaches backups too; every read decrypts.", '<span class="pill warn">For large systems</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "Rule", "Why"], [
    ["<code>users_deleted_holds_nothing</code>", "DELETED means login, password, name, phone, email are NULL", "\"Deleted\" cannot be a label on a full row."],
    ["<code>erasures_within_90_days</code>", "due_by ≤ requested_at + 90 days", "The deadline is part of the record."],
    ["<code>invoices_retained_after_issue</code>", "retain_until &gt; issued_on", "A kept record says until when."],
    ["<code>data_exports_ready_has_content</code>", "READY means content", "No empty \"ready\" exports."]]) + """
<p><strong>Transaction boundaries:</strong> the deletion request (close the account, book the erasure) is one transaction; each account's erasure is another, all or nothing; an export is built in its own.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["14. Operations: metric, alert, rollback, runbook, failure drill", "15. Real-world considerations"],
               "What changes when this runs for real.") + """
<h2>Real-world considerations</h2>
<dl class="facts">
<dt>The law, with its status</dt><dd>India's Digital Personal Data Protection Act, 2023 gives people the right to have their data erased. The DPDP Rules, 2025 were notified in November 2025 and apply in phases; the duties on keeping and erasing data are due to apply from May 2027. They include erasing data once its purpose is served or consent is withdrawn, unless a law requires keeping it, and, for some large platforms, erasing after three years of inactivity with notice 48 hours before. This station's 90-day deadline is a demo rule, not a figure taken from the law. Not legal advice: read the current text with counsel.</dd>
<dt>Keeping what the law requires</dt><dd>Tax invoices: India's GST law asks for accounts and records to be kept for years (72 months from the due date of the annual return under the CGST Act). Security logs: CERT-In's directions of April 2022 ask for system logs to be kept for 180 days. Keep these, restrict who can read them, and delete them when the period ends.</dd>
<dt>Logs</dt><dd>Do not write personal data into application logs at all: then there is nothing to erase there. This station logs account ids only.</dd>
<dt>Backups</dt><dd>You cannot edit a backup. Keep backups for a short, stated period, and re-apply the erasure ledger after any restore (challenge 3).</dd>
<dt>Other systems</dt><dd>Search indexes, analytics, the email provider, the data warehouse: each needs its own entry in the inventory and its own erasure step.</dd>
<dt>Watching it</dt><dd>Alert on any erasure not completed one day after its request, long before its due date.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("How do you make sure a deletion reaches every copy?", "An inventory of every place personal data is kept, checked against the schema in a test, and a test that searches the data afterwards."),
    ("Delete or anonymise?", "Delete what has no reason to stay; anonymise rows others depend on (keep the id, remove what identifies); keep what a law requires, with an end date."),
    ("Why is an export a background job?", "Collecting everything can be slow and large; a job can be retried, and the result fetched when ready."),
    ("What about backups?", "Short retention, and a ledger of erasures re-applied after any restore; or crypto-shredding."),
    ("What must not be in an export?", "Other people's data, even when it mentions the person: someone else's address book is theirs."),
    ("How do you stop a deleted account being used during the erasure?", "Close it in the same request: sign-in only for ACTIVE accounts."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Inventory", "Tables listed.", "The build fails when one is missing, and each entry says why."],
    ["Erasure", "Rows deleted.", "All or nothing, proven by searching every column, with the kept records named."],
    ["The law", "Knows there is a right to erasure.", "Can say what the Rules require, when they apply, and what to keep."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("Following foreign keys misses what is keyed by phone",
     "\"Everything personal points at users, so read the foreign keys and nothing is ever forgotten\": the sign-in codes, the notification queue and other members' address books hold the phone number with no foreign key. They are never reached.",
     "<code>theApiErasesHimEverywhereExceptWhatTheLawKeeps</code> fails: the number is still in the codes, the queue and Zoya's upload."),
    ("It deletes what the law keeps",
     "The same loop deletes every row that points at the user: the invoices, which must be kept for years, and the recent sign-in records kept for security.",
     "<code>deletingClosesTheAccountAtOnceAndBooksTheErasureWithin90Days</code> fails: the sign-in from two days ago is gone; and the invoice the trap test expects to remain has been deleted."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate replaces the hand-written inventory: \"read the foreign keys to <code>users</code> from the database, and no table is ever forgotten\". Read the file and list every problem before opening the findings.</p>
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
<p class="note">The flawed version looks more thorough than a hand-written list, and it does clean every table that knows the user id. The search of every column is what shows the difference.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
