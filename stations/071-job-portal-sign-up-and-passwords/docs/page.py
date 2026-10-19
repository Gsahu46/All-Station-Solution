"""Station 071 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 71,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Security 7 SecurityFilterChain · BCrypt via DelegatingPasswordEncoder · CORS · JdbcClient · PostgreSQL 17 · Testcontainers",
    "simulation": "Candidates and their passwords are demo data, not Hireloop's. No email is sent and no real account exists.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/hireloop/candidates/"
T = "src/test/java/com/hireloop/candidates/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Hash", "A one-way fingerprint of a password: easy to compute, impossible to reverse.", "A fingerprint identifies a person but is not the person.", "<code>password_hash</code>"),
    ("Fast hash", "MD5 or SHA-256: billions of guesses per second on a graphics card.", "A lock that can be tried a billion times a second.", "the old MD5 hashes"),
    ("Salt", "Random text mixed in, so the same password gives a different hash each time.", "Two people with the same PIN, but different locks.", "inside every bcrypt hash"),
    ("Work factor", "How slow the hash is on purpose; raised as computers get faster.", "A lock that takes a second to try, every time.", "bcrypt cost 10"),
    ("Filter chain", "The checks every request passes before a controller sees it.", "Security at a building's entrance.", "<code>SecurityFilterChain</code>"),
    ("CORS", "Which other websites a browser lets call this API.", "A guest list at the door, for browsers.", "<code>corsConfigurationSource</code>"),
]
STORY = [
    ("The leak", "A copy of Hireloop's candidate table got out. Passwords were stored as MD5 hashes."),
    ("Cracked in a coffee break", "MD5 is fast. An attacker hashes a list of common passwords and compares: every match is an account. Two people with the same password even had the same hash. 80,000 accounts were exposed."),
    ("The fix", "Store bcrypt hashes: salted, and slow on purpose. Old MD5 hashes are replaced with bcrypt the next time each candidate signs in."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Assume the password table will leak one day. Store it so the leak is useless.</p>

<h2>What are we building?</h2>
<p><code>POST /candidates/signup</code> creates an account with a bcrypt-hashed password; <code>GET /candidates/me</code> returns the signed-in candidate's own profile.</p>

<h2>An everyday analogy</h2>
<p>A bank does not keep your PIN on a card in the drawer. It keeps something that can check a PIN but cannot give it back, and makes each check take time, so trying a million PINs is hopeless.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Sign-up</strong>: check the email and a long-enough password, lower-case the email.</li>
<li><strong>Hash</strong> the password with bcrypt: a new salt each time, a deliberate cost.</li>
<li><strong>Store</strong> only the hash; the database refuses anything that is not one.</li>
<li><strong>Sign-in</strong>: Spring Security hashes what was sent the same way and compares; an old MD5 hash is replaced with bcrypt on success.</li>
</ol>

<details class="qa check"><summary>Check yourself: two candidates choose the same password. Do their stored hashes match?</summary><p>With the old MD5: yes, so one cracked password exposes both. With bcrypt: no, each hash has its own salt. The trap test shows the first; the stored hashes in the captures show the second.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No password reset.</strong> That is station 072.</li>
<li><strong>No tokens or sessions.</strong> Credentials come with each request; tokens are station 073.</li>
<li><strong>No email verification.</strong> A real sign-up would confirm the email address.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Hireloop</strong> (a fictional job portal) stored passwords with MD5. A leak exposed 80,000 accounts.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo data: two accounts imported from the old system, still with MD5 hashes.</p>
<ol class="gwt">
<li><b>Given</b> a valid sign-up, <b>then</b> <code>201</code>, a bcrypt hash stored, and no password or hash in any response.</li>
<li><b>Given</b> the same email in other capitals, <b>then</b> <code>409</code>.</li>
<li><b>Given</b> a password under 12 characters, over 64, or over 72 bytes, <b>then</b> <code>400</code>.</li>
<li><b>Given</b> no credentials, a wrong password or an unknown email, <b>then</b> the same <code>401</code>.</li>
<li><b>Given</b> a legacy account's correct password, <b>then</b> <code>200</code>, and its hash is now bcrypt.</li>
<li><b>Given</b> a browser on another website, <b>then</b> the CORS preflight is refused (<code>403</code>).</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>New passwords are hashed with bcrypt (cost 10); old MD5 hashes are only ever verified, then replaced.</li>
<li>The database refuses plain text, bare digests and weak bcrypt costs.</li>
<li>Responses never say whether an email has an account.</li>
<li>Only Hireloop's web app may call the API from a browser.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Configure a <code>SecurityFilterChain</code> for a stateless API.</li>
<li>Hash with bcrypt through a <code>PasswordEncoder</code>, and migrate old hashes.</li>
<li>Explain why CSRF does not apply here and what CORS does.</li>
<li>Back the rules with database constraints.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/candidates/signup</code>", "<code>{email, fullName, password}</code>; open to everyone; <code>201</code> with <code>{id, email, fullName}</code>."],
    ["<code>GET</code>", "<code>/candidates/me</code>", "The signed-in candidate (HTTP Basic: email and password)."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span> / <span class="pill ok">201</span>', "Profile / account created"],
    ['<span class="pill warn">400</span>', "Not an email; password under 12 or over 64 characters, or over 72 bytes; a field missing"],
    ['<span class="pill warn">401</span>', "No credentials, or credentials that do not match an account (one answer for both)"],
    ['<span class="pill warn">403</span>', "A browser preflight from a website other than Hireloop's"],
    ['<span class="pill warn">409</span>', "An account with that email exists"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-sign-up", "Case 1: sign-up", "<b>Why:</b> the email is lower-cased; nothing about the password comes back."),
    ("02-my-profile", "Case 2: the profile, signed in", "<b>Why:</b> \"me\" comes from the credentials."),
    ("03-a-wrong-password", "Case 3: a wrong password", "<b>Why:</b> <code>401</code>."),
    ("04-an-email-with-no-account", "Case 4: an email with no account", "<b>Why:</b> exactly the same <code>401</code> as case 3."),
    ("05-the-same-email-again", "Case 5: the same email again", "<b>Why:</b> <code>409</code>, pointing to sign-in or reset."),
    ("06-a-legacy-account-signs-in", "Case 6: an imported account signs in", "<b>Why:</b> its MD5 hash checks out once, and is replaced (below)."),
    ("07-a-browser-on-another-site", "Case 7: a preflight from another website", "<b>Why:</b> CORS refuses it."),
]) + """
<h2>The stored hashes, before and after</h2>
<p class="muted">From <code>psql</code> in <code>docs/capture.sh</code>: before the requests (<code>hashes-before.txt</code>) and after (<code>hashes-after.txt</code>).</p>
""" + code(read("docs/captures/hashes-before.txt").rstrip(), "text") + code(read("docs/captures/hashes-after.txt").rstrip(), "text") + """
<p>Priya's MD5 hash became bcrypt at her sign-in (case 6); Arjun has not signed in, so his is still MD5. Nisha's hash shows the parts of bcrypt: <code>$2a$</code> the version, <code>10</code> the cost, then 22 characters of salt and the hash.</p>"""

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Sign up, then read the profile", "<code>201</code>, then own profile", "<code>signUpThenReadOwnProfile</code>"],
    ["What is stored", "A bcrypt hash, never the password", "<code>theStoredHashIsBcryptNeverThePassword</code>"],
    ["The same email, other capitals", "<code>409</code>", "<code>aDuplicateEmailIs409AnyCase</code>"],
    ["Too short, too long, too many bytes, missing fields", "<code>400</code>", "<code>badSignupsAre400</code>"],
    ["Unknown email against wrong password", "Identical <code>401</code>s", "<code>anUnknownEmailAndAWrongPasswordLookTheSame</code>"],
    ["Another candidate's profile", "Not reachable: \"me\" is the signed-in identity", "<code>oneCandidateOnlyEverSeesTheirOwnProfile</code>"],
    ["A browser on another site", "Preflight refused", "<code>theApiIsReachableOnlyFromHireloopsOwnWebApp</code>"],
    ["SQL-looking input, control characters", "<code>400</code> or <code>401</code>, never run", "<code>oddInputIsRejectedNotExecuted</code>"],
    ["Plain text, bare digest, {noop}, weak cost, upper-case email written directly", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Fast hashes like MD5 or SHA-256 without a work factor.</p>
<ul>
<li><strong>Cracked from a list.</strong> The test takes Priya's leaked MD5 hash and hashes 25 common passwords: one of them matches. Real attackers use lists of millions, and a fast hash lets them try all of them per account in moments.</li>
<li><strong>The same leak with bcrypt.</strong> The bcrypt hash of the same password contains no MD5 to compare; every guess costs the full, deliberate work of bcrypt, with that hash's own salt.</li>
<li><strong>Old accounts move over by themselves.</strong> The imported MD5 hash is checked once at sign-in; Spring then calls <code>updatePassword</code> and the row holds bcrypt.</li>
</ul>
<p>While building, each fix was undone once: no MD5 verifier turned 2 tests red (sign-in on a legacy row failed with an error instead of a <code>401</code>, so even \"unknown and wrong look the same\" broke); no upgrade service 1; no byte check 1; no lower-casing of emails 2; no hash-shape CHECK 1; the CORS bean under another name 1.</p>
</div>
""" + code(read(T + "FastHashTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SecurityConfig.java", dwn("The filter chain, CORS and the password encoder.",
        "Sign-up open, all else authenticated; stateless Basic; bcrypt for new hashes, MD5 only to verify old ones.",
        "Every endpoint open, or plain-text and MD5 hashes accepted forever.",
        "<ul><li>CSRF is off because nothing here uses cookies or sessions: a browser never attaches these credentials on its own. With cookie sessions, CSRF protection must stay on.</li><li>The CORS bean must be called <code>corsConfigurationSource</code>; under another name it is ignored. Found while building this station.</li><li>Spring's default encoder list also accepts <code>{noop}</code> (plain text); this list holds only bcrypt and MD5.</li></ul>")),
    (J + "CandidateAccounts.java", dwn("Finds a candidate by email for Spring Security, and stores re-hashed passwords.",
        "As a <code>UserDetailsPasswordService</code>, Spring hands it the new bcrypt hash after an old hash checks out.",
        "Legacy MD5 hashes staying in the table for years.")),
    (J + "CandidateController.java", dwn("Sign-up and \"me\".",
        "Lower-cased emails, a 72-byte check for bcrypt, the hash made by the encoder; \"me\" from the verified identity.",
        "Duplicate accounts by capital letters, or a profile chosen by an id in the URL.")),
    (J + "ProblemResponses.java", "<p>401 and 403 in the same problem JSON as every other error.</p>"),
    (M + "V1__candidates.sql", dwn("The table, with a CHECK on the hash's shape.",
        "Plain text, bare digests, <code>{noop}</code> and cheap bcrypt costs are refused for every writer.",
        "A script or a hurried fix storing passwords in the clear.")),
    (M + "V2__legacy_candidates.sql", "<p>Two accounts imported with the old MD5 hashes.</p>"),
    ("src/main/resources/application.yaml", "<p>The one allowed browser origin.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "CandidatesApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/071-job-portal-sign-up-and-passwords/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/hireloop/candidates/
│   ├── SecurityConfig.java   ├── CandidateAccounts.java   ├── CandidateController.java
│   ├── ProblemResponses.java   └── CandidatesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__candidates.sql, V2__legacy_candidates.sql
├── src/test/java/com/hireloop/candidates/   (see Tests)
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
<p>Sign up, sign in, and look at what was stored:</p>
""" + code("""curl -X POST http://localhost:8080/candidates/signup -H 'Content-Type: application/json' \\
  -d '{"email": "you@example.com", "fullName": "You", "password": "a-long-passphrase"}'
curl -u 'you@example.com:a-long-passphrase' http://localhost:8080/candidates/me
docker compose exec postgres psql -U hireloop -d hireloop -c "SELECT email, password_hash FROM candidates\"""", "bash") + """
<p>Sign up twice with the same password under two emails: the two hashes differ.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Every origin passes CORS", "The <code>CorsConfigurationSource</code> bean has another name.", "Name it <code>corsConfigurationSource</code>. Found while building this station."],
    ["<code>There is no PasswordEncoder mapped for the id \"…\"</code>", "A stored hash with a prefix the encoder does not know.", "Add a verifier for it, or reset those accounts."],
    ["<code>password cannot be more than 72 bytes</code>", "bcrypt's input limit, enforced by Spring Security.", "Check the byte length first and answer <code>400</code>, as the controller does."],
    ["<code>candidates_password_hash_shape</code> violated", "Something tried to store a password that is not a bcrypt hash.", "Always store <code>passwordEncoder.encode(…)</code>."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>CandidateContractTest</code> ({cnt('CandidateContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>FastHashTrapTest</code> ({cnt('FastHashTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>CandidateDatabaseTest</code> ({cnt('CandidateDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, one user accessing another user's data, malicious input", f"<code>CandidateSecurityTest</code> ({cnt('CandidateSecurityTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">\"Not found\" here is the unknown email, answered like a wrong password on purpose. \"Another user's data\": there is no endpoint that takes an id, so the test shows one candidate's credentials can only ever reach their own profile.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Spring Security 7.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "FastHashTrapTest.java", "<p>Written first: an MD5 leak cracked from a short list, the same with bcrypt, and the upgrade at sign-in.</p>"),
    (T + "CandidateSecurityTest.java", "<p>401s that look alike, own profile only, CORS, odd input.</p>"),
    (T + "CandidateDatabaseTest.java", "<p>The hash-shape CHECK and the email rules with plain SQL, and a rolled-back insert.</p>"),
    (T + "CandidateContractTest.java", "<p>Sign-up and profile through HTTP.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the legacy accounts restored after each test.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/hireloop/candidates/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=ChangePasswordChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Change the password", "Beginner-friendly", 25,
    "Add <code>PUT /candidates/me/password</code> <code>{currentPassword, newPassword}</code>: <code>204</code>; the current password must be right (<code>422</code>), the new one follows the sign-up rules (<code>400</code>).",
    "both tests in <code>ChangePasswordChallengeTest</code> pass.",
    ["Check the current password with <code>passwordEncoder.matches</code> against the stored hash.", "Store <code>passwordEncoder.encode(newPassword)</code>, never the text."],
    "challenge/ChangePasswordChallengeTest.java", ["challenge/solution/CandidateController.java", "challenge/solution/CandidateAccounts.java"]) + challenge(2, "Lock after five wrong passwords", "Go deeper", 35,
    "After 5 wrong passwords in a row, lock the account for 15 minutes; the right password then gets the same <code>401</code>. A good sign-in resets the count.",
    "both tests in <code>LockoutChallengeTest</code> pass.",
    ["Spring Security publishes <code>AuthenticationFailureBadCredentialsEvent</code> and <code>AuthenticationSuccessEvent</code>; listen with <code>@EventListener</code>.",
     "Two columns in a new migration: a counter and <code>locked_until</code>.", "Return <code>accountLocked(true)</code> from <code>loadUserByUsername</code> while locked."],
    "challenge/LockoutChallengeTest.java", ["challenge/solution/V3__lockout.sql", "challenge/solution/CandidateAccounts.java", "challenge/solution/CandidateController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Refusing passwords that have already leaked</h2>
<p>Long passwords can still be leaked ones. Design a check against a breached-password list at sign-up without sending the password anywhere: hash it, send only the first five characters of the hash to a range API, and compare the returned suffixes locally (k-anonymity). Where does the check run, what happens if the service is down, and when would you move from bcrypt to argon2?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: crack an MD5 leak from a list.</li>
<li>Pick bcrypt behind <code>DelegatingPasswordEncoder</code>, with MD5 only to verify old hashes.</li>
<li>Let Spring upgrade old hashes at sign-in through <code>UserDetailsPasswordService</code>.</li>
<li>Configure the filter chain, CORS, and the database CHECK on hash shapes.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["bcrypt via DelegatingPasswordEncoder, upgrade at sign-in", "A slow hash per sign-in (by design).", '<span class="pill ok">Chosen</span>'],
    ["MD5 or SHA-256, salted or not", "Billions of guesses per second.", '<span class="pill bad">The trap</span>'],
    ["argon2id", "Memory-hard, the current first choice in OWASP guidance; needs Bouncy Castle here.", '<span class="pill warn">Better, more setup</span>'],
    ["Re-hash every MD5 hash at once: bcrypt(md5)", "No waiting for sign-ins; a nested scheme forever.", '<span class="pill warn">Valid for a fast cut-over</span>'],
    ["Force a reset for every legacy account", "Clean; annoys every user.", '<span class="pill warn">After a known breach</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>candidates_password_hash_shape</code>", "CHECK: bcrypt with cost 10–31, or a tagged legacy MD5 digest", "No plain text, bare digests or <code>{noop}</code> from any writer."],
    ["<code>candidates_email_lower</code>, <code>candidates_email_unique</code>", "CHECK and UNIQUE", "One account per email, whatever the capitals."]]) + """
""" + code(read(M + "V1__candidates.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>After a breach</dt><dd>Hashing better does not undo a leak that happened. Tell users, force resets for leaked accounts, and watch for credential stuffing.</dd>
<dt>Cost of bcrypt</dt><dd>Each sign-in costs real CPU. Rate-limit sign-in attempts, and measure the cost on production hardware before raising it.</dd>
<dt>Basic over HTTPS only</dt><dd>HTTP Basic sends the password with every request: only ever over TLS. Station 073 replaces it with tokens.</dd>
<dt>Logs</dt><dd>Never log request bodies of sign-up or password endpoints.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why not store passwords with SHA-256?", "It is designed to be fast; an attacker with the hashes can try billions of guesses per second. Password hashes must be salted and deliberately slow: bcrypt, scrypt, argon2."),
    ("What is a salt for?", "It makes each hash unique, so equal passwords do not share hashes and precomputed tables are useless."),
    ("How do you migrate old hashes?", "Keep a verifier for the old format, and re-hash with the new algorithm when the user next signs in; Spring's DelegatingPasswordEncoder and UserDetailsPasswordService do exactly this."),
    ("Does this API need CSRF protection?", "Not while credentials come only in the Authorization header: browsers never add it on their own. With cookie sessions, yes."),
    ("What does CORS protect?", "It tells browsers which other websites may read responses from this API; it does not stop curl or servers, so it is not authentication."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Hashing", "bcrypt with a salt and a cost.", "Migrating old hashes at sign-in."],
    ["Spring Security", "A filter chain with open and closed paths.", "Why CSRF is off here and when it must be on."],
    ["Privacy", "No account enumeration at sign-in.", "Also at sign-up (station 072)."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("SHA-256 instead of bcrypt",
     "\"Modern and fast\" is exactly the problem: one fast, unsalted hash per password. The database's hash-shape CHECK refuses it, so every sign-up becomes a 500; without the CHECK the weak hashes would have been stored quietly.",
     "<code>signUpThenReadOwnProfile</code>, <code>theStoredHashIsBcryptNeverThePassword</code>, <code>oneCandidateOnlyEverSeesTheirOwnProfile</code> (its sign-ups fail) and <code>theSameLeakOfBcryptHashesRevealsNothing</code> fail."),
    ("No verifier for the imported MD5 hashes",
     "Replacing the encoder drops the MD5 verifier: the legacy accounts can never sign in or be upgraded.",
     "<code>aLegacyMd5AccountIsUpgradedToBcryptOnFirstSignIn</code> fails."),
    ("Six-character passwords",
     "Short passwords are the first a list tries.",
     "<code>badSignupsAre400</code> fails."),
    ("Emails kept as typed",
     "<code>Sam@</code> and <code>sam@</code> become two accounts, and the database's lower-case CHECK turns the sign-up into a 500.",
     "<code>aDuplicateEmailIs409AnyCase</code> fails."),
    ("CORS for every origin",
     "\"*\" lets any website's scripts call the API from a visitor's browser.",
     "<code>theApiIsReachableOnlyFromHireloopsOwnWebApp</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate speeds up sign-in: \"SHA-256 is modern and much faster than bcrypt\". They also relax the password minimum to six characters, keep emails exactly as typed, and open CORS to \"*\" for preview builds. Read the two files and list every problem before opening the findings.</p>
<p class="path">review/SecurityConfig.java</p>
""" + code(read("review/SecurityConfig.java"), "java") + """
<p class="path">review/CandidateController.java</p>
""" + code(read("review/CandidateController.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the two flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">The database caught the weakest hash before it was stored. Without that CHECK, this pull request would have passed sign-up tests and quietly stored fast hashes.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
