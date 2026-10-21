"""Station 076 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 76,
    "stack": "Spring Boot 4.1.1 · Java 25 · WebAuthn with webauthn4j 0.31.9 · TOTP (RFC 6238) · Spring Security 7 resource server · JdbcClient · PostgreSQL 17 · Testcontainers",
    "simulation": "Customers and balances are demo rows in a table, not Tijori's; no bank is involved. In the tests, webauthn4j's emulator plays the phone's authenticator and browser, with real keys and real signatures. The TOTP secret is RFC 6238's published test secret, demo only.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows). A real passkey in a browser needs HTTPS on the configured origin.",
}
J = "src/main/java/com/tijori/passkeys/"
T = "src/test/java/com/tijori/passkeys/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Passkey", "A key pair made by the phone for one website. The private key never leaves the phone; the site keeps the public key.", "A house key cut for one door only.", "<code>passkeys</code> table"),
    ("Relying party (RP) id", "The website domain a passkey belongs to. The phone will not use it for another domain.", "The address engraved on the key.", "<code>tijori.example</code>"),
    ("Challenge", "Random bytes the server sends for one sign-in; the phone signs them.", "A one-time password the guard says out loud.", "<code>webauthn_challenges</code>"),
    ("Origin", "The exact web address of the page that asked the phone, written into what it signs.", "The return address on a letter.", "<code>https://app.tijori.example</code>"),
    ("User verification", "The phone checked a fingerprint, face or PIN before signing.", "The guard checks the face matches the badge.", "<code>userVerification: required</code>"),
    ("TOTP", "A six-digit code from an app, made from a shared secret and the time, new every 30 seconds.", "A safe whose code changes every half minute.", "<code>POST /2fa/totp</code>"),
]
STORY = [
    ("Phished and SIM-swapped", "Fake Tijori pages collected passwords, and attackers moved customers' numbers to new SIM cards to receive their SMS codes. Fourteen accounts were drained."),
    ("Passkeys, half done", "The first passkey code only checked the signature. A sign-in recorded once could be sent again, and an answer made for a look-alike page was accepted."),
    ("The fix", "Every sign-in signs a fresh challenge from Tijori, on Tijori's page, for Tijori's domain, with the customer's fingerprint or face. The server checks all of it. The fallback is a password with an authenticator-app code, never SMS."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A signature only proves the key signed something. What it signed, and for whom, is the server's to check.</p>

<h2>What are we building?</h2>
<p>Passkey registration and sign-in (two ceremonies, each with options and an answer), a password-plus-code fallback, and an account page.</p>

<h2>An everyday analogy</h2>
<p>A notary stamps a letter only after reading today's date and the addressee aloud. A stamped letter dated last week, or addressed to the shop next door, is worth nothing here, however real the stamp.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Options</strong>: Tijori sends a fresh challenge and its domain.</li>
<li><strong>Phone</strong>: the customer touches the sensor; the phone signs the challenge together with the page's origin and the domain.</li>
<li><strong>Check</strong>: Tijori uses up the challenge, then checks origin, domain, fingerprint flag, signature and counter.</li>
<li><strong>Token</strong>: a 10-minute access token that records how the customer signed in.</li>
</ol>

<details class="qa check"><summary>Check yourself: why can a fake page not simply pass the customer's passkey answer on to Tijori?</summary><p>The answer names the page that asked it, inside the signed data. Tijori accepts only its own origin, so an answer made on <code>tijori-login.example</code> is refused, as <code>aSignInAnsweredForAPhishingPageIsRefused</code> shows. (Real browsers also refuse to use a Tijori passkey on another domain at all.)</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real phone in the tests.</strong> webauthn4j's emulator plays it, with real keys.</li>
<li><strong>No attestation checks.</strong> Tijori does not ask which model of authenticator made the key (<code>attestation: none</code>).</li>
<li><strong>No account recovery.</strong> Losing every passkey and the code app is a support process (Practice, challenge 3).</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tijori</strong> (a fictional bank) lost 14 accounts to phished passwords and SIM-swapped SMS codes; customers want to sign in with a fingerprint or face.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo data: customers zoya and dev, with passwords and the same demo TOTP secret.</p>
<ol class="gwt">
<li><b>Given</b> the right password and the current code, <b>then</b> <code>200</code> with a token; the same code again is <code>401</code>.</li>
<li><b>Given</b> a sign-in from the last 5 minutes, <b>then</b> a passkey can be registered; with an older token, <code>403</code>.</li>
<li><b>Given</b> a registered passkey and a fresh challenge on Tijori's page, <b>then</b> sign-in works without a password.</li>
<li><b>Given</b> a sign-in answer sent twice, made for another page, or made for another domain, <b>then</b> it is refused.</li>
<li><b>Given</b> a passkey answer claiming another customer, or a registration on another customer's challenge, <b>then</b> refused.</li>
<li><b>Given</b> ten sign-ins with one code at once, <b>then</b> exactly one token.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>The challenge, origin and RP id come from the server, never from the request.</li>
<li>Challenges are single-use and last 5 minutes; the database enforces their shape and lifetime.</li>
<li>No SMS anywhere. A password is never enough on its own.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Run both WebAuthn ceremonies and name every server-side check.</li>
<li>Explain what makes passkeys resistant to phishing, and what the server still has to do.</li>
<li>Implement TOTP with single use and a small time window.</li>
<li>Test with an authenticator emulator instead of a phone.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/2fa/totp</code>", "The fallback: <code>{email, password, code}</code>. A token with <code>signedInWith</code> <code>pwd otp mfa</code>."],
    ["<code>POST</code>", "<code>/webauthn/registration/options</code>", "Needs a token from the last 5 minutes. The options for <code>navigator.credentials.create()</code>."],
    ["<code>POST</code>", "<code>/webauthn/registration</code>", "<code>{label, credential}</code>: the browser's answer. <code>201</code>."],
    ["<code>POST</code>", "<code>/webauthn/authentication/options</code>", "Open. The options for <code>navigator.credentials.get()</code>. (Not in the roadmap's list: a sign-in needs its challenge from somewhere.)"],
    ["<code>POST</code>", "<code>/webauthn/authentication</code>", "The browser's answer. A token with <code>signedInWith</code> <code>hwk user</code>."],
    ["<code>GET</code>", "<code>/accounts/me</code>", "Name and balance (in paise) of the signed-in customer."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span> / <span class="pill ok">201</span>', "Signed in, options given / passkey registered"],
    ['<span class="pill warn">400</span>', "A body of the wrong shape; a registration answer that fails a check"],
    ['<span class="pill warn">401</span>', "Wrong email, password or code (one answer); a sign-in answer that fails any check; no token"],
    ['<span class="pill warn">403</span>', "Adding a passkey with a sign-in older than 5 minutes"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. curl has no authenticator, so the two passkey ceremonies themselves run in the tests, with webauthn4j's emulator; here are the code sign-in, both option documents, and what is refused. <code>Date</code>, connection and standard security headers are left out; the token and the code are shown by name.</p>
""" + examples([
    ("01-password-and-code", "Case 1: password and the current code", "<b>Why:</b> both factors in one request; the token records them."),
    ("02-the-same-code-again", "Case 2: the same code again", "<b>Why:</b> a code works once: <code>401</code>, the same answer as a wrong code."),
    ("03-the-account", "Case 3: the account", "<b>Why:</b> the token's customer; the balance is in paise."),
    ("04-registration-options", "Case 4: options to add a passkey", "<b>Why:</b> a fresh challenge, Tijori's domain, a random user id (not the email), a passkey that stays on the device, a fingerprint or face required."),
    ("05-sign-in-options", "Case 5: options to sign in", "<b>Why:</b> no user named: the passkey says whose it is."),
    ("06-a-made-up-passkey-answer", "Case 6: a made-up passkey answers case 5's challenge, from another page", "<b>Why:</b> <code>401</code>, and the challenge is now used up (below)."),
    ("07-registration-without-a-token", "Case 7: adding a passkey without signing in", "<b>Why:</b> <code>401</code>."),
]) + """
<h2>What the database holds afterwards</h2>
<p class="muted">From <code>psql</code> in <code>docs/capture.sh</code>.</p>
""" + code(read("docs/captures/challenges.txt").rstrip(), "text") + code(read("docs/captures/customers.txt").rstrip(), "text") + """
<p>The sign-in challenge was used up by the made-up answer in case 6, so it can never be answered again. The registration challenge from case 4 is still open; it expires 5 minutes after it was made. Zoya's used code is recorded as a time step, not as the code.</p>"""

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Password and code", "A token that opens the account", "<code>passwordAndCodeGiveATokenThatOpensTheAccount</code>"],
    ["Registration options", "Tijori's domain, a random user id, passkey and fingerprint required", "<code>registrationOptionsNameThisSiteAndAskForAPasskeyWithUserVerification</code>"],
    ["Register, then sign in", "No password needed", "<code>aRegisteredPasskeySignsInWithoutAPassword</code>"],
    ["Wrong password, wrong code, unknown email", "The same <code>401</code>", "<code>wrongPasswordWrongCodeOrUnknownEmailAreTheSame401</code>"],
    ["Bad bodies", "<code>400</code>", "<code>badBodiesAre400</code>"],
    ["No token", "<code>401</code>", "<code>noTokenIs401</code>"],
    ["A sign-in older than 5 minutes adds a passkey", "<code>403</code>", "<code>addingAPasskeyNeedsASignInFromTheLastFiveMinutes</code>"],
    ["A registration on another customer's challenge", "<code>400</code>, nothing stored", "<code>aChallengeIssuedToAnotherCustomerCannotAddAPasskeyHere</code>"],
    ["A passkey answer claiming another customer", "<code>401</code>", "<code>aPasskeyCannotSayItBelongsToAnotherCustomer</code>"],
    ["A challenge after 5 minutes", "<code>401</code>", "<code>aChallengeExpiresAfterFiveMinutes</code>"],
    ["A counter lower than the stored one", "<code>401</code>: it looks like a copied key", "<code>aCounterThatGoesBackwardsLooksLikeACloneAndIsRefused</code>"],
    ["A code twice; one step late; two steps late", "<code>401</code>; accepted; <code>401</code>", "<code>aCodeWorksOnceAndOnlyNearItsTime</code>"],
    ["Ten sign-ins with one code at once", "Exactly one token", "<code>tenParallelSignInsWithOneCodeGiveOneToken</code>"],
    ["Odd answers", "<code>400</code> or <code>401</code>, never an error", "<code>oddAnswersAre400Or401NeverAnError</code>"],
    ["Rules written by plain SQL", "Refused by named constraints", "<code>challengeRulesHoldWithoutJava</code>, <code>passkeyAndCustomerRulesHoldWithoutJava</code>"],
    ["A save that fails; a check that fails", "Rolled back, retry works; the challenge is used up", "<code>aSaveThatFailsRollsBackAndTheSameAnswerCanBeSentAgain</code>, <code>aFailedCheckUsesUpTheChallenge</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Not checking the challenge, origin and relying-party id, so a phishing site can replay a sign-in.</p>
<p>The old code checked only that the signature matched the stored public key. Each test makes one answer it accepted:</p>
<ul>
<li><strong>Replayed.</strong> A real sign-in, sent again a minute later: the signature is still valid. The API refuses it, because its challenge was used up. The test device keeps its counter at 0, as synced passkeys commonly do, so only the challenge stops this.</li>
<li><strong>Answered for a phishing page.</strong> <code>tijori-login.example</code> fetches a real challenge and gets the passkey to answer it on its own page: valid signature, wrong origin. Refused.</li>
<li><strong>Made for another site.</strong> A look-alike page asks for a passkey for its own domain and hands it to Tijori. The old code stored any key it could parse. Refused.</li>
<li><strong>The control.</strong> A fresh challenge on Tijori's page signs in.</li>
</ul>
<p>While building, each check was undone once: the sign-in challenge taken from the request turned 3 tests red; any origin 1; no userHandle comparison 1; no owner check on the registration challenge 1; registration without its transaction 1, or rolling back on every failure 1; no recent sign-in check 1; a reusable code 2; no one-step window 1; the counter not stored 1. Not requiring user verification turned nothing red: the emulator always reports it.</p>
</div>
""" + code(read(T + "UncheckedCeremonyTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SecurityConfig.java", dwn("Who may call what.",
        "The sign-in ceremonies and the code sign-in are open (they are the proof); adding a passkey and the account need a token; everything else refused.",
        "A passkey added by someone who is not signed in, or a new endpoint open by default.")),
    (J + "SignInController.java", dwn("The five sign-in endpoints.",
        "Password and code together, never apart; adding a passkey needs a sign-in from the last 5 minutes; one answer for every failed ceremony.",
        "A stolen token planting the attacker's own passkey, or errors that tell which check failed.")),
    (J + "Passkeys.java", dwn("Both WebAuthn ceremonies.",
        "The challenge is ours and used up in one conditional <code>UPDATE</code>; then webauthn4j checks it with our origin and our RP id, user verification, the signature and the counter; the server compares <code>userHandle</code> itself.",
        "Replays, answers made for other pages or other sites, and one customer's passkey speaking for another.",
        "<ul><li>The signature covers the authenticator data and a hash of clientDataJSON, not <code>userHandle</code>: a changed <code>userHandle</code> keeps the signature valid. Found while building.</li><li>Synced passkeys commonly report a counter of 0, so the counter cannot be relied on to stop replays: the challenge does. Found while building, when the replay test first stayed green.</li><li>Both ceremonies are transactions with <code>noRollbackFor = CeremonyFailed</code>: a failed check still uses up its challenge, a failed save does not.</li></ul>")),
    (J + "CodeSignIn.java", dwn("The fallback: password and an authenticator-app code.",
        "RFC 6238 codes for the current and the previous 30 seconds, compared in constant time, each accepted once (<code>totp_last_step</code> moves forward in one conditional UPDATE).",
        "A code read over a shoulder being used again, or two requests with one code both getting in.",
        "<p>No attempt limit yet: a six-digit code has a million values. Challenge 2 adds one.</p>")),
    (J + "Totp.java", "<p>The code itself: HMAC-SHA1 over the step number, dynamic truncation, six digits.</p>"),
    (J + "TokenService.java", "<p>10-minute tokens; <code>amr</code> (RFC 8176 values) records how the customer signed in.</p>"),
    (J + "JwtConfig.java", "<p>The token checks, as in station 073.</p>"),
    (J + "AccountController.java", "<p>The account from the token's subject.</p>"),
    (J + "ProblemResponses.java", "<p>401 and 403 in the same problem JSON as every other error.</p>"),
    (M + "V1__customers_passkeys_challenges.sql", dwn("Customers, passkeys and challenges, with their rules.",
        "32-byte challenges for 5 minutes at most; a registration challenge always belongs to a customer; a counter within 32 bits; a random 32-byte user id.",
        "A script storing eternal challenges, or a passkey whose owner could be guessed from its user id.")),
    (M + "V2__demo_customers.sql", "<p>Two demo customers, bcrypt hashes made by pgcrypto, and RFC 6238's public test secret.</p>"),
    ("src/main/resources/application.yaml", "<p>The RP id, the one allowed origin, lifetimes, and a demo signing key.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "PasskeysApplication.java", "<p>Entry point, and the <code>Clock</code> every time check uses.</p>"),
]
tree = """stations/076-passkey-sign-in-with-webauthn/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/tijori/passkeys/
│   ├── SecurityConfig.java   ├── SignInController.java   ├── Passkeys.java
│   ├── CodeSignIn.java   ├── Totp.java   ├── TokenService.java   ├── JwtConfig.java
│   ├── AccountController.java   ├── ProblemResponses.java   └── PasskeysApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__customers_passkeys_challenges.sql, V2__demo_customers.sql
├── src/test/java/com/tijori/passkeys/   Device.java (the emulated phone) and the tests
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
<p>Make the current code from the demo secret and sign in with it, twice:</p>
""" + code("""CODE=$(python3 -c 'import hmac,hashlib,struct,time; h=hmac.new(b"12345678901234567890",struct.pack(">Q",int(time.time())//30),hashlib.sha1).digest(); o=h[-1]&15; print("%06d"%((int.from_bytes(h[o:o+4],"big")&0x7fffffff)%1000000))')
for i in 1 2; do curl -s -o /dev/null -w '%{http_code}\\n' -X POST http://localhost:8080/2fa/totp -H 'Content-Type: application/json' \\
  -d "{\\"email\\": \\"dev@example.com\\", \\"password\\": \\"dev-demo-pass\\", \\"code\\": \\"$CODE\\"}"; done""", "bash") + """
<p>The first prints 200, the second 401. Any authenticator app set up with the base32 secret <code>GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ</code> shows the same codes. A real passkey needs a browser on HTTPS at the configured origin; to see the ceremonies, run <code>./mvnw test -Dtest=PasskeyContractTest</code>.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Every passkey sign-in is <code>401</code>, the log says <code>BadOriginException</code>", "The page's origin differs from <code>tijori.webauthn.origin</code> (port, http against https, another subdomain).", "Configure the exact origin; list every real one, never all."],
    ["<code>BadRpIdException</code>", "The passkey was made for another RP id.", "The RP id is the registrable domain the passkeys were created for; changing it later orphans them."],
    ["Codes are always wrong", "The server clock is off by more than 30 seconds.", "Keep server clocks in sync (NTP)."],
    ["<code>MaliciousCounterValueException</code>", "The counter went backwards: a copied key, or a restored backup of the table.", "Treat it as a warning about that passkey; ask the customer."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>PasskeyContractTest</code> ({cnt('PasskeyContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>UncheckedCeremonyTrapTest</code> ({cnt('UncheckedCeremonyTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>PasskeyDatabaseTest</code> ({cnt('PasskeyDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, one user accessing another user's data, malicious input", f"<code>PasskeySecurityTest</code> ({cnt('PasskeySecurityTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">\"Not found\" here is the unknown email and the unknown passkey, both answered like a wrong one on purpose. \"Another user's data\": a passkey claiming another customer, and a registration on another customer's challenge. <code>Device</code> wraps webauthn4j's emulator: a <code>NoneAttestationAuthenticator</code> behind a <code>ClientPlatform</code> at an origin, turning the server's options into the JSON a browser sends.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, webauthn4j 0.31.9, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "UncheckedCeremonyTrapTest.java", "<p>Written first: three answers the signature-only check accepted, each refused by the API, and the control.</p>"),
    (T + "PasskeySecurityTest.java", "<p>401, 403, other customers, expiry, a copied key, codes once and near their time, ten parallel sign-ins, odd answers.</p>"),
    (T + "PasskeyDatabaseTest.java", "<p>Every named constraint with plain SQL; a save that fails rolls back, a check that fails uses the challenge up.</p>"),
    (T + "PasskeyContractTest.java", "<p>Code sign-in, both ceremonies, wrong answers, bad bodies.</p>"),
    (T + "Device.java", "<p>The emulated phone: authenticator and browser, at an origin.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the test clock, a test key, a clean slate before each test, ceremony helpers.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tijori/passkeys/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=ManagePasskeysChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "List and remove passkeys", "Beginner-friendly", 25,
    "<code>GET /webauthn/passkeys</code> lists the customer's own passkeys (id, label); <code>DELETE /webauthn/passkeys/{id}</code> removes one (<code>204</code>), after which it cannot sign in. Another customer's passkey is <code>404</code> and stays.",
    "both tests in <code>ManagePasskeysChallengeTest</code> pass.",
    ["Put the customer in the <code>DELETE</code>'s <code>WHERE</code>: another customer's id then finds no row.",
     "The filter chain refuses new paths until they have a rule."],
    "challenge/ManagePasskeysChallengeTest.java", ["challenge/solution/PasskeyListController.java", "challenge/solution/SecurityConfig.java"]) + challenge(2, "Lock code sign-in after five wrong codes", "Go deeper", 40,
    "After 5 wrong codes in a row (with the right password), code sign-in is locked for 15 minutes; even the right code then gets the same <code>401</code>. A good sign-in resets the count.",
    "both tests in <code>CodeLockoutChallengeTest</code> pass.",
    ["Two columns in a V3 migration, with a CHECK on the count.",
     "Lock the customer row (<code>SELECT ... FOR UPDATE</code>) so parallel guesses are counted one by one.",
     "A code that was already used is a replay, not a guess: do not count it, or ten parallel requests lock the account."],
    "challenge/CodeLockoutChallengeTest.java", ["challenge/solution/V3__code_lockout.sql", "challenge/solution/CodeSignIn.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Lost phone, and the apps</h2>
<p>A customer loses the only phone with their passkey and their code app. Design recovery without SMS: what identity checks, what waiting period, and what the customer is told. Then: Tijori's Android app sends <code>android:apk-key-hash:...</code> as its origin. How do you accept it without accepting every origin?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: answers a signature-only check accepted, made with an emulated phone.</li>
<li>Store challenges in the database, single-use, with their purpose and owner.</li>
<li>Let webauthn4j check the answers against our challenge, our origin and our RP id.</li>
<li>Add the password-plus-code fallback, with single-use codes.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Own endpoints on webauthn4j, challenges in PostgreSQL", "More code than a built-in; every check visible.", '<span class="pill ok">Chosen</span>'],
    ["Check only the signature", "Replays and answers for other pages pass.", '<span class="pill bad">The trap</span>'],
    ["Spring Security's <code>webAuthn()</code> DSL", "Little code; its own endpoint names and session-based options.", '<span class="pill warn">Good for a web app with sessions</span>'],
    ["SMS codes as the fallback", "SIM swaps; the original incident.", '<span class="pill bad">Not here</span>'],
    ["Ask for attestation and trust only certain authenticators", "Metadata service, privacy prompts; for regulated keys.", '<span class="pill warn">When the authenticator model matters</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>webauthn_challenges_length</code>, <code>_expiry</code>", "CHECKs: 32 bytes, at most 5 minutes", "No guessable or eternal challenges from any writer."],
    ["<code>webauthn_challenges_registration_has_customer</code>", "CHECK", "A registration challenge always belongs to one customer."],
    ["<code>passkeys_sign_count_range</code>, <code>_credential_id_length</code>", "CHECKs", "What WebAuthn allows: a 32-bit counter, ids of 16 to 1023 bytes."],
    ["<code>customers_user_handle_length</code>, <code>_unique</code>", "CHECK and UNIQUE", "A random 32-byte id per customer, never the email."],
    ["<code>customers_totp_secret_length</code>", "CHECK: at least 20 bytes", "RFC 4226's minimum of 128 bits, recommended 160."]]) + """
<p><strong>Transaction boundary:</strong> one ceremony is one transaction. A failed check commits (the challenge stays used); a failed save rolls back (the same answer can be sent again).</p>
""" + code(read(M + "V1__customers_passkeys_challenges.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Origins</dt><dd>List every real origin (web, Android's <code>android:apk-key-hash:</code>, iOS uses the web origin through associated domains). Never accept any origin.</dd>
<dt>Old challenges</dt><dd>Delete used and expired challenges in a scheduled job.</dd>
<dt>TOTP secrets</dt><dd>Store them encrypted (they are not hashes: the server needs them), and show the QR code only once.</dd>
<dt>Logs</dt><dd>Log which check failed; never log codes, tokens or full credential JSON.</dd>
<dt>Standards</dt><dd>Web Authentication Level 2 is a W3C Recommendation (2021); Level 3, which adds the JSON forms used here, was still being finished at W3C when this was written: check its status before citing it; CTAP 2 is a FIDO Alliance specification; TOTP is RFC 6238 and HOTP RFC 4226 (both Informational); <code>amr</code> values are RFC 8176 (Proposed Standard).</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why are passkeys phishing-resistant?", "The browser gives a passkey only to pages of the domain it was made for, and the signed data names the page's origin. A look-alike domain cannot use it, and the server refuses answers for other origins."),
    ("What does the server check on a passkey sign-in?", "That the challenge is its own, unused and in time; the origin and RP id hash; the user-presence and user-verification flags; the signature with the stored public key; the counter; and that userHandle matches the passkey's owner."),
    ("Why store challenges server-side?", "So each is used once. A random challenge that the server does not remember can be answered again by anyone who recorded the answer."),
    ("What is the signature counter for?", "Cloned-key detection: a counter that does not increase suggests two copies of a key. Synced passkeys usually report 0, so it is a signal, not a replay defence."),
    ("Why TOTP and not SMS as the fallback?", "SMS can be redirected by a SIM swap or intercepted. TOTP lives in an app on the device. It can still be phished, which is why passkeys are the main way in."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Ceremonies", "Challenge, origin, RP id, signature checked.", "userHandle compared; counter kept; you know why 0 is common."],
    ["Fallback", "Password and code together.", "Codes single-use under parallel requests."],
    ["Data", "Challenges single-use.", "Each rule a named constraint; failed checks and failed saves behave differently."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("Any origin accepted",
     "\"The Android app and staging send other origins\" is solved by listing them. Accepting every origin accepts answers made for a phishing page.",
     "<code>aSignInAnsweredForAPhishingPageIsRefused</code> fails."),
    ("The sign-in challenge taken from the request",
     "\"Random and signed\" is true and beside the point: the server must know it issued the challenge and that it was not used. Without the lookup, a recorded sign-in works again, expired challenges work, and a malformed answer becomes a 500 because nothing checks it first.",
     "<code>aSignInCapturedOnceAndSentAgainIsRefused</code>, <code>aChallengeExpiresAfterFiveMinutes</code> and <code>oddAnswersAre400Or401NeverAnError</code> fail."),
    ("Any token may add a passkey",
     "A stolen 10-minute token is now enough to plant the attacker's own passkey, which then works for months.",
     "<code>addingAPasskeyNeedsASignInFromTheLastFiveMinutes</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate unblocks the Android app and staging (\"they send other origins\"), drops the challenge table lookup at sign-in (\"challenges are random 32 bytes and signed anyway\"), and removes the fresh sign-in needed to add a passkey (\"customers complained\"). Read the two files and list every problem before opening the findings.</p>
<p class="path">review/Passkeys.java</p>
""" + code(read("review/Passkeys.java"), "java") + """
<p class="path">review/SignInController.java</p>
""" + code(read("review/SignInController.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the two flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">The signature check still passes on every one of these answers. That is the whole trap: a valid signature over the wrong thing.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
