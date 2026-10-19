"""Station 072 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 72,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Security 7 · SecureRandom tokens, stored as SHA-256 · single-use UPDATE … RETURNING · JdbcClient · PostgreSQL 17 · Testcontainers",
    "simulation": "Email is simulated: a row is written to an outbox table and nothing is sent. Candidates are demo data, not Hireloop's.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/hireloop/resets/"
T = "src/test/java/com/hireloop/resets/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Reset link", "A one-time key, sent by email, that lets its holder choose a new password.", "A spare key left with a neighbour, for one use.", "<code>…/reset-password?token=…</code>"),
    ("Single use", "The link stops working once it has been used.", "A ticket torn at the gate.", "<code>used_at</code>"),
    ("Expiry", "The link stops working after a while, used or not.", "A parking ticket valid for 30 minutes.", "<code>expires_at</code>, 30 minutes"),
    ("Account enumeration", "Finding out which emails have accounts from how a form replies.", "A receptionist who says \"no such guest\" or \"I'll ring their room\".", "one reply for every email"),
    ("Token hash", "Only a fingerprint of the link is stored, so a copy of the table opens nothing.", "The hotel keeps a key's serial number, not a spare key.", "<code>token_hash</code>"),
    ("Outbox", "Emails written as rows for a sender to pick up; here nobody sends them.", "A post tray.", "<code>outbox_emails</code>"),
]
STORY = [
    ("Forgot my password", "A candidate asks for a reset link. The old system stored the link's token as plain text, with no expiry, and never marked it used."),
    ("Keys left lying around", "Old emails in an inbox stayed keys to the account for ever, and anyone who read the reset table could take over any account. The form also said \"No account found with this email\", so attackers could test which emails were registered."),
    ("The fix", "One reply for every email. Links are 256 random bits, kept only as a hash, valid for 30 minutes, usable once, and all cancelled when the password changes."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A reset link is a password. Treat it like one: short-lived, single-use, and never stored in the clear.</p>

<h2>What are we building?</h2>
<p><code>POST /password-resets</code> sends a link (if the account exists, and never says whether it does); <code>POST /password-resets/{token}/complete</code> uses the link once to set a new password.</p>

<h2>An everyday analogy</h2>
<p>A hotel front desk that hands out a one-time key card, valid for half an hour, only to the guest's registered email, and answers \"if you are staying with us, we have sent it\" to anyone who asks.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Request</strong>: if an active account has the email, make a random token, store only its hash, and write an email with the link.</li>
<li><strong>Reply</strong> the same way in every case.</li>
<li><strong>Use the link</strong>: one database statement checks it is unused and unexpired and marks it used.</li>
<li><strong>Set the password</strong> and cancel every other open link of the account.</li>
</ol>

<details class="qa check"><summary>Check yourself: why is a plain SHA-256 fine for reset tokens but not for passwords?</summary><p>A token is 256 random bits made by the server: there is no list of likely tokens to try, so a fast hash loses nothing. Passwords are chosen by people, and lists of likely ones exist, so they need a slow, salted hash (station 071).</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No email is sent.</strong> The outbox row is the simulated email.</li>
<li><strong>No sign-in sessions.</strong> Ending other sessions after a reset is Practice 3, on paper.</li>
<li><strong>No CAPTCHA.</strong> A per-account limit stops flooding one inbox; abuse from many sources needs more.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Hireloop</strong> (a fictional job portal): reset links never expire, can be used twice, and the form tells attackers which emails have accounts.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo data: Priya and Arjun are active, Kiran is suspended. Tests control the clock.</p>
<ol class="gwt">
<li><b>Given</b> any email, known or not, <b>then</b> <code>202</code> with the same message; only an active account gets an email.</li>
<li><b>Given</b> the link and a new password, <b>then</b> <code>204</code>; the old password stops working, the new one works.</li>
<li><b>Given</b> the same link again, or after 30 minutes, or a link nobody issued, <b>then</b> the same <code>400</code>.</li>
<li><b>Given</b> two open links and one used, <b>then</b> the other no longer works.</li>
<li><b>Given</b> ten requests for one email, <b>then</b> at most three links are sent.</li>
<li><b>Given</b> one link sent ten times at the same moment, <b>then</b> exactly one succeeds.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Tokens come from <code>SecureRandom</code> (256 bits); only their SHA-256 is stored.</li>
<li>A link is valid for 30 minutes and once; the database refuses longer windows.</li>
<li>No reply, status or timing difference that depends on whether an account exists, as far as the code can control.</li>
<li>A password change cancels every open link of the account.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Design single-use, expiring tokens, and store them safely.</li>
<li>Avoid account enumeration in replies.</li>
<li>Make \"use once\" safe under concurrency with one conditional update.</li>
<li>Test time-based rules with a controllable clock.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/password-resets</code>", "<code>{email}</code>; always <code>202</code> with one message."],
    ["<code>POST</code>", "<code>/password-resets/{token}/complete</code>", "<code>{newPassword}</code>; <code>204</code> once per link."],
    ["<code>GET</code>", "<code>/candidates/me</code>", "The signed-in candidate (HTTP Basic), to see the new password work."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">202</span>', "Every reset request with a well-formed email"],
    ['<span class="pill ok">204</span>', "The new password is set"],
    ['<span class="pill warn">400</span>', "Not an email; a new password under 12 or over 64 characters or 72 bytes; a link that is unknown, used or expired (one message)"],
    ['<span class="pill warn">401</span> / <span class="pill warn">403</span>', "Profile without valid credentials / for a suspended account"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. The token is replaced by a placeholder in every capture: a real one is a key to an account. JSON bodies are indented for reading; <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-reset-for-a-known-email", "Case 1: a known email", "<b>Why:</b> <code>202</code> and a link in the outbox."),
    ("02-reset-for-an-unknown-email", "Case 2: an unknown email", "<b>Why:</b> exactly the same reply; no email."),
    ("03-choose-a-new-password", "Case 3: the link from the email", "<b>Why:</b> <code>204</code>: the password is changed."),
    ("04-the-same-link-again", "Case 4: the same link again", "<b>Why:</b> used: the one \"invalid or expired\" message."),
    ("05-signed-in-with-the-new-password", "Case 5: the new password", "<b>Why:</b> it works."),
    ("06-a-suspended-account", "Case 6: a suspended account", "<b>Why:</b> <code>403</code>."),
]) + """
<h2>What was stored</h2>
<p class="muted">From <code>psql</code> in <code>docs/capture.sh</code>: the outbox (with the token masked), and the reset row before and after it was used.</p>
""" + code(read("docs/captures/outbox.txt").rstrip(), "text") + code(read("docs/captures/resets-before.txt").rstrip(), "text") + code(read("docs/captures/resets-after.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["The whole reset", "Old password out, new one in", "<code>theWholeResetFromRequestToNewPassword</code>"],
    ["An unknown email", "Same reply, no email", "<code>anUnknownEmailGetsTheSameReplyAndNoEmail</code>"],
    ["A link nobody issued", "<code>400</code>", "<code>anUnknownLinkIs400</code>"],
    ["Bad email, short or too-long password", "<code>400</code>, and the link still works", "<code>badRequestsAre400</code>"],
    ["Suspended account", "<code>403</code> on the profile, no link", "<code>aSuspendedAccountIs403AndGetsNoLink</code>"],
    ["A link for one account", "Changes only that account", "<code>aLinkChangesOnlyTheAccountItWasSentFor</code>"],
    ["Two open links, one used", "The other is cancelled", "<code>aNewPasswordCancelsEveryOtherOpenLink</code>"],
    ["Ten requests", "Three links", "<code>floodingTheFormSendsAtMostThreeLinks</code>"],
    ["Quotes, a 500-character token, path tricks", "The same <code>400</code>", "<code>oddTokensAreJustUnknownLinks</code>"],
    ["One link, ten requests at once", "Exactly one <code>204</code>", "<code>oneLinkUsedTwiceAtTheSameMomentWorksOnce</code>"],
    ["Plain tokens, month-long links, late use written directly", "Refused by named constraints", "<code>ResetDatabaseTest</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Reusable, non-expiring tokens and different replies for known and unknown emails.</p>
<p>The old reset is kept in the test as plain SQL against an <code>old_reset_tokens</code> table:</p>
<ul>
<li><strong>Two replies.</strong> \"We have sent you a reset link\" or \"No account found with this email\": anyone can test a list of emails. The new replies are byte for byte the same.</li>
<li><strong>A key for ever.</strong> The old token sits in its table as text, and 31 days later it still works. The new link fails after 30 minutes and after one use, and the table holds only its SHA-256.</li>
</ul>
<p>While building, each fix was undone once: a different reply for unknown emails turned 3 tests red; a reusable link 2 (including the parallel test); no expiry check 1; keeping the other open links 1; no flood limit 1; storing the token itself instead of its hash 9, because the database's shape CHECK then refused every link.</p>
</div>
""" + code(read(T + "ReusableTokenTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "ResetController.java", dwn("The two reset steps and the profile.",
        "One constant reply for every request; the new password's length and bytes checked.",
        "A friendly \"no such account\" that answers attackers too.")),
    (J + "PasswordResets.java", dwn("Makes, stores and uses reset links.",
        "<code>SecureRandom</code> tokens, only their hash stored, one conditional <code>UPDATE … RETURNING</code> to use a link, every other link cancelled.",
        "Links that work twice, work for ever, or open accounts for whoever reads the table.",
        "<ul><li>The unknown-email path returns early: no email and no error. Its timing is close to, not equal to, the known path; a constant-time design would hand both to a queue.</li><li>Unknown, used and expired links share one message.</li></ul>")),
    (J + "SecurityConfig.java", dwn("Both reset steps open, the profile for active candidates, everything else denied.",
        "The reset is for people who cannot sign in.",
        "A new endpoint quietly open: with <code>denyAll</code> last, a forgotten rule fails closed.")),
    (J + "CandidateAccounts.java", "<p>Sign-in by email; suspended accounts get a role that the profile refuses.</p>"),
    (J + "ProblemResponses.java", "<p>401 and 403 as problem JSON.</p>"),
    (M + "V1__candidates_and_resets.sql", dwn("Candidates, reset links and the outbox, with named constraints.",
        "The database refuses plain tokens, links longer than an hour, and use after expiry.",
        "Rules that only the Java code knows.")),
    (M + "V2__demo_candidates.sql", "<p>Three candidates, with bcrypt hashes made by pgcrypto.</p>"),
    ("src/main/resources/application.yaml", "<p>The link address and its 30 minutes.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "ResetsApplication.java", "<p>Entry point and the clock.</p>"),
]
tree = """stations/072-password-reset-by-email/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/hireloop/resets/
│   ├── ResetController.java   ├── PasswordResets.java   ├── SecurityConfig.java
│   ├── CandidateAccounts.java   ├── ProblemResponses.java   └── ResetsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__candidates_and_resets.sql, V2__demo_candidates.sql
├── src/test/java/com/hireloop/resets/   (see Tests)
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
<p>Ask for a link, read the simulated email, and use the link:</p>
""" + code("""curl -X POST http://localhost:8080/password-resets -H 'Content-Type: application/json' -d '{"email": "arjun@example.com"}'
docker compose exec postgres psql -U hireloop -d hireloop -c "SELECT body FROM outbox_emails ORDER BY id DESC LIMIT 1"
curl -X POST "http://localhost:8080/password-resets/<token>/complete" -H 'Content-Type: application/json' -d '{"newPassword": "arjun-new-long-password"}'""", "bash") + """
<p>Run the last command twice: the second answer is the same as for a made-up token.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>403</code> on a new endpoint", "The filter chain ends in <code>denyAll</code>: unlisted paths are refused.", "Add a rule for the path. Found while building this station's Practice."],
    ["<code>password_resets_used_in_time</code> violated", "A link marked used after its expiry.", "Use it with the conditional <code>UPDATE</code>, which checks expiry in the same statement."],
    ["The link works in tests but not by hand", "The tests' clock is fixed; the app's is real.", "Use the link within 30 minutes."],
    ["Links in logs or analytics", "Reset URLs logged by a proxy or a page tracker.", "Keep the token out of logs; use it as soon as the page opens."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>ResetContractTest</code> ({cnt('ResetContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>ReusableTokenTrapTest</code> ({cnt('ReusableTokenTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>ResetDatabaseTest</code> ({cnt('ResetDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, one user accessing another user's data, malicious input", f"<code>ResetSecurityTest</code> ({cnt('ResetSecurityTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">Time-based rules use a test clock that the tests move forward: \"31 minutes later\" takes no time to test. The parallel test sends one link ten times on virtual threads released by one latch.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Spring Security 7.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "ReusableTokenTrapTest.java", "<p>Written first: the old two replies and the eternal token, then the new link's limits.</p>"),
    (T + "ResetSecurityTest.java", "<p>401, 403, one account only, cancelled links, flooding, odd tokens, and a parallel use.</p>"),
    (T + "ResetDatabaseTest.java", "<p>The reset table's constraints with plain SQL, and a rolled-back half reset.</p>"),
    (T + "ResetContractTest.java", "<p>The flow through HTTP.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the movable clock, demo candidates, and reading the link from the outbox.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/hireloop/resets/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=ChangedNoticeChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Tell the owner", "Beginner-friendly", 15,
    "After a reset, write a second email: \"Your Hireloop password was changed\", with no link in it.",
    "the test in <code>ChangedNoticeChallengeTest</code> passes.",
    ["Write it in the same transaction as the change, so a failed change sends no notice."],
    "challenge/ChangedNoticeChallengeTest.java", ["challenge/solution/PasswordResets.java"]) + challenge(2, "Every password change cancels links", "Go deeper", 30,
    "Add <code>PUT /candidates/me/password</code> <code>{currentPassword, newPassword}</code> for signed-in candidates. It must also cancel open reset links.",
    "both tests in <code>ChangePasswordCancelsLinksChallengeTest</code> pass.",
    ["Move \"set the password, cancel links, notify\" into one method both paths call.",
     "Found while building: the new path got <code>403</code> until the filter chain listed it, because the chain ends in <code>denyAll</code>."],
    "challenge/ChangePasswordCancelsLinksChallengeTest.java", ["challenge/solution/SecurityConfig.java", "challenge/solution/ResetController.java", "challenge/solution/PasswordResets.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>What else should a reset end?</h2>
<p>With sessions or tokens (stations 073 and 074), an attacker who already signed in keeps that session after the owner resets the password. Design how a reset ends every other session: a <code>password_changed_at</code> compared with each token's issue time, a per-account token version, or deleting refresh tokens. Which works for tokens that are checked without a database?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old replies and the eternal, plain-text token.</li>
<li>Make tokens random and long, keep only their hash, and give them an expiry.</li>
<li>Use a link with one conditional <code>UPDATE … RETURNING</code>, so \"once\" holds under concurrency.</li>
<li>Answer every request the same way, and limit links per account.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Random token, hash stored, 30 minutes, single use", "A table and a cleanup job for old rows.", '<span class="pill ok">Chosen</span>'],
    ["Token stored as text, no expiry", "Old emails and table copies are keys.", '<span class="pill bad">The trap</span>'],
    ["A signed token (HMAC or JWT) with an expiry, no table", "No storage; cannot be made single-use without storing something.", '<span class="pill warn">Not single-use</span>'],
    ["A 6-digit code instead of a link", "Easy to type; must be rate-limited hard, 10<sup>6</sup> guesses is small.", '<span class="pill warn">With strict attempt limits</span>'],
    ["Check-then-update in two statements", "Two parallel uses can both pass.", '<span class="pill bad">Race</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>password_resets_token_hash_shape</code>, <code>_unique</code>", "64 hex characters, unique", "Only hashes, never tokens."],
    ["<code>password_resets_expiry</code>", "Expires after creation, at most 1 hour later", "No month-long links from any writer."],
    ["<code>password_resets_used_in_time</code>", "Used only before expiry", "No late use slipping in."],
    ["<code>candidates_password_hash_shape</code>", "bcrypt only", "A reset can never store a plain password."]]) + """
<p><strong>Transaction boundary:</strong> using the link, changing the password and cancelling other links commit together.</p>
""" + code(read(M + "V1__candidates_and_resets.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Email is not instant</dt><dd>30 minutes is a demo rule; measure how long your email provider takes before you shorten it.</dd>
<dt>Referrer leaks</dt><dd>The reset page should send no <code>Referer</code> with the token (a <code>Referrer-Policy: no-referrer</code> header) and load no third-party scripts.</dd>
<dt>Old rows</dt><dd>Delete used and expired rows on a schedule; they are useless and still personal data.</dd>
<dt>Abuse</dt><dd>The per-account limit protects one inbox; limits per IP address and a CAPTCHA protect the service from mass requests.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What makes a reset token safe?", "Enough randomness (128+ bits from a secure generator), a short expiry, single use, and storing only its hash."),
    ("Why store a hash of the token?", "A copy of the table, from a backup or a leak, then opens nothing; the email holds the only usable copy."),
    ("How do you avoid account enumeration in a reset form?", "Give the same reply, status and roughly the same timing for every email; send the email only if the account exists."),
    ("How do you make a token single-use under concurrency?", "Check and mark it in one conditional statement: UPDATE … WHERE unused AND unexpired RETURNING; only one request can get a row back."),
    ("What should happen after a reset?", "Cancel other reset links, notify the owner, and end other sessions or tokens."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Tokens", "Random, hashed, expiring, single-use.", "Why a fast hash is fine here."],
    ["Privacy", "One reply for every email.", "The timing that still differs."],
    ["Concurrency", "One conditional UPDATE.", "Why check-then-update races."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("\"No account with this email\"",
     "A friendly 404 for unknown emails turns the form into a list checker for attackers.",
     "<code>anUnknownEmailGetsTheSameReplyAndNoEmail</code>, <code>theOldFormToldAttackersWhichEmailsHaveAccounts</code> and <code>aSuspendedAccountIs403AndGetsNoLink</code> fail."),
    ("The link is never marked used",
     "\"In case the first attempt fails\" means anyone with the email can reset again for the next 30 minutes, and ten parallel uses all succeed.",
     "<code>aNewLinkWorksOnceAndOnlyFor30Minutes</code> and <code>oneLinkUsedTwiceAtTheSameMomentWorksOnce</code> fail."),
    ("Other open links stay valid",
     "An older email in a stolen inbox still resets the password after the owner has reset it.",
     "<code>aNewPasswordCancelsEveryOtherOpenLink</code> fails."),
    ("No limit on links",
     "Removing the open-link check lets anyone flood a person's inbox with resets.",
     "<code>floodingTheFormSendsAtMostThreeLinks</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate makes resets \"friendlier\": tell people when they mistype their email, keep the link working \"in case the first attempt fails\", and drop the open-link count \"to simplify\". Read the file and list every problem before opening the findings.</p>
<p class="path">review/PasswordResets.java</p>
""" + code(read("review/PasswordResets.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">Every change looks like kindness to users; each one is kindness to attackers too.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
