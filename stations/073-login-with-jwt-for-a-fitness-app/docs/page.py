"""Station 073 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 73,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Security 7 OAuth2 resource server · Nimbus JOSE (HS256) · JwtEncoder / JwtDecoder · stateless",
    "simulation": "Members, passwords and workouts are demo data held in the app, not FitNest's. The signing key in application.yaml is a demo key; no identity provider is involved.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No database and no Docker. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/fitnest/workouts/"
T = "src/test/java/com/fitnest/workouts/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Session", "The server remembers \"this browser is asha\" in its own memory.", "A cloakroom ticket that only one cloakroom knows.", "the old login"),
    ("JWT", "Three base64url parts: header, payload (claims), signature. Anyone can read it; only the key holder can sign it.", "A sealed, signed pass: readable through the window, but the seal shows tampering.", "<code>accessToken</code>"),
    ("Signature", "A code computed from the header, payload and a secret key. Change one letter and it no longer matches.", "A wax seal.", "HS256 with the shared key"),
    ("Claims", "What the token says: who (sub), from whom (iss), for which API (aud), until when (exp), what they may do (scope).", "The name, issuer and expiry date on a pass.", "<code>TokenService</code>"),
    ("Clock skew", "A small allowance because two servers' clocks never agree exactly.", "A bus pass still accepted a minute after midnight.", "60 seconds"),
    ("401 and 403", "401: we do not know who you are. 403: we know, and you may not do this.", "No ticket, against a ticket for another show.", "no token against no <code>workouts:read</code>"),
]
STORY = [
    ("Logged out by a deploy", "FitNest kept each login in the memory of the server that handled it. Every restart or deploy wiped it, and a member sent to another server was a stranger there."),
    ("A quick fix that was worse", "The first token version only base64-decoded the token to read the member's name. Anyone could write a token saying \"ravi\" and read Ravi's workouts."),
    ("The fix", "Signed tokens, checked on every request: the signature, the algorithm, the expiry with a small allowance, the issuer and the audience. Any server with the key can check them; none has to remember anything."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A token is only worth what the server checks. Reading it is not checking it.</p>

<h2>What are we building?</h2>
<p><code>POST /auth/login</code> swaps a username and password for a 15-minute signed token; <code>GET /workouts/me</code> returns the workouts of whoever the token is for.</p>

<h2>An everyday analogy</h2>
<p>A festival wristband printed with your name, the festival, the day, and a hologram. Any gate can check it without phoning the ticket office. A wristband you drew yourself has no hologram; yesterday's has the wrong day.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Login</strong>: the password is checked against a bcrypt hash (station 071).</li>
<li><strong>Issue</strong>: the server writes the claims and signs them with the shared key.</li>
<li><strong>Send</strong>: the app sends <code>Authorization: Bearer &lt;token&gt;</code> with every request, to any server.</li>
<li><strong>Check</strong>: that server verifies signature, algorithm, expiry, issuer and audience, then the scope. Only then does the controller see <code>sub</code>.</li>
</ol>

<details class="qa check"><summary>Check yourself: the payload is only base64. Can a member change their own token to say they are someone else?</summary><p>They can change the text, but the signature was computed over the original. The server recomputes it with the key, sees a mismatch and answers <code>401</code>. The security test does exactly this, and capture 4 shows the response.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No refresh tokens or device list.</strong> That is station 074.</li>
<li><strong>No outside identity provider.</strong> Sign-in with Google is station 075.</li>
<li><strong>No logout yet.</strong> A token stays valid until it expires; challenge 1 adds a revoke list.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>FitNest</strong> (a fictional fitness app) logs members out on every deploy because sessions live in one server's memory.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo data: members asha, ravi and meera may read workouts; newbie has not finished onboarding and may not.</p>
<ol class="gwt">
<li><b>Given</b> a right username and password, <b>then</b> <code>200</code> with a Bearer token valid for 900 seconds.</li>
<li><b>Given</b> a wrong password or an unknown username, <b>then</b> the same <code>401</code>.</li>
<li><b>Given</b> a valid token, <b>then</b> <code>GET /workouts/me</code> returns that member's workouts, and nothing in the request chooses another member.</li>
<li><b>Given</b> no token, a changed, forged, unsigned or expired token, or one from another issuer or for another API, <b>then</b> <code>401</code> with <code>WWW-Authenticate: Bearer</code>.</li>
<li><b>Given</b> a valid token without <code>workouts:read</code>, <b>then</b> <code>403</code>.</li>
<li><b>Given</b> a token 15 minutes and 30 seconds old, <b>then</b> still accepted (60-second allowance); at 16 minutes and 1 second, refused.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Tokens are HS256 only; the key is at least 256 bits and shared by every server.</li>
<li>Tokens carry iss, sub, aud, iat, exp and scope, and nothing secret: anyone holding one can read it.</li>
<li>No server-side session.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Explain the three parts of a JWT and what the signature protects.</li>
<li>Issue tokens with <code>JwtEncoder</code> and validate them with a resource server.</li>
<li>Set expiry and clock skew, and test them with a controllable clock.</li>
<li>Tell 401 from 403.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/auth/login</code>", "<code>{username, password}</code>; open to everyone; <code>200</code> with <code>{accessToken, tokenType, expiresIn}</code>."],
    ["<code>GET</code>", "<code>/workouts/me</code>", "The token subject's workouts. Needs <code>Authorization: Bearer</code> and scope <code>workouts:read</code>."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "Token issued / workouts returned"],
    ['<span class="pill warn">400</span>', "Username or password missing, empty or too long"],
    ['<span class="pill warn">401</span>', "Wrong login (one answer for unknown and wrong); no token, or a token that fails any check"],
    ['<span class="pill warn">403</span>', "A valid token without <code>workouts:read</code>"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code>, connection and standard security headers are left out. Real tokens are replaced by their shape: each one opened an account for 15 minutes.</p>
""" + examples([
    ("01-login", "Case 1: login", "<b>Why:</b> a Bearer token for 900 seconds."),
    ("02-my-workouts", "Case 2: the token opens the member's own workouts", "<b>Why:</b> \"me\" is the verified <code>sub</code>."),
    ("03-no-token", "Case 3: no token", "<b>Why:</b> <code>401</code>, and <code>WWW-Authenticate: Bearer</code> says what is expected."),
    ("04-payload-changed-to-ravi", "Case 4: asha's token with the payload changed to ravi", "<b>Why:</b> the signature no longer matches: <code>401</code>. The old base64-only check would have shown Ravi's workouts."),
    ("05-wrong-password", "Case 5: a wrong password", "<b>Why:</b> <code>401</code>, the same as for an unknown username."),
    ("06-signed-in-without-the-scope", "Case 6: a valid token for newbie, without the scope", "<b>Why:</b> <code>403</code>: known, but not allowed."),
]) + """
<h2>What the token says</h2>
<p class="muted">The payload of asha's token from case 1, base64url-decoded by <code>docs/capture.sh</code>. Anyone with the token can read this; that is why it holds no secrets.</p>
""" + code(read("docs/captures/payload.txt").rstrip(), "json") + """
<p><code>exp</code> minus <code>iat</code> is 900 seconds. <code>scope</code> holds only the member's own grant: see \"Found while building\" in the Code tab.</p>"""

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Login, then workouts", "Token, then own workouts", "<code>theTokenOpensTheMembersOwnWorkouts</code>"],
    ["What the token says", "iss, sub, scope <code>workouts:read</code> only, 900 seconds", "<code>thePayloadSaysWhoForWhichApiAndWhatTheyMayDo</code>"],
    ["A member with no workouts", "<code>200</code> with an empty list", "<code>aMemberWithNoWorkoutsGetsAnEmptyList</code>"],
    ["Wrong password, unknown user, bad body", "Identical <code>401</code>s; <code>400</code>", "<code>aWrongPasswordOrAnUnknownMemberIs401AndAMalformedLoginIs400</code>"],
    ["No token", "<code>401</code> with a Bearer challenge", "<code>noTokenIs401WithABearerChallenge</code>"],
    ["15:30 old, then 16:01 old", "Accepted, then <code>401</code>", "<code>aTokenExpiresAfter15MinutesWithOneMinuteForClockDifferences</code>"],
    ["Signed with the right key, wrong iss or aud", "<code>401</code>; all claims right is <code>200</code>", "<code>aTokenFromAnotherIssuerOrForAnotherApiIs401</code>"],
    ["Valid token, no scope", "<code>403</code>", "<code>aMemberWithoutTheScopeIs403</code>"],
    ["Payload changed to another member; <code>?member=ravi</code>", "<code>401</code>; the parameter is ignored", "<code>changingWhoTheTokenIsForBreaksItsSignature</code>"],
    ["Not a JWT, SQL-looking text, 5,000 characters, Basic credentials", "<code>401</code>, never an error", "<code>garbageInTheHeaderIs401NotAnError</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Reading the token without checking it, and tokens that live for weeks.</p>
<ul>
<li><strong>Sessions in memory.</strong> The test puts asha's session in one map and looks in a fresh one, as a restarted pod would: she is gone. A signed token checked on a second decoder with the same key still works.</li>
<li><strong>A forged key.</strong> A token signed with someone else's key says \"ravi\". The old base64-only read believes it; the API answers <code>401</code>.</li>
<li><strong>No signature at all.</strong> A token with <code>alg: none</code> and an empty signature. Believed by the old read; refused by the API, which accepts HS256 only.</li>
<li><strong>Expired.</strong> A month later the old read still says \"asha\"; the API answers <code>401</code>.</li>
</ul>
<p>While building, each check was removed once: no audience check turned 1 test red; no issuer check 1; no clock allowance 1; the validator on the machine's clock instead of the app's 6; a 30-day lifetime 4; any signed-in member allowed 1; the scope built from all of the sign-in's authorities 1. Two changes turned nothing red and are explained in the Code tab.</p>
</div>
""" + code(read(T + "UnverifiedTokenTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SecurityConfig.java", dwn("The filter chain, the demo members and the login's authentication manager.",
        "Login open; workouts need <code>SCOPE_workouts:read</code>; everything else refused; the resource server checks every bearer token; no session.",
        "An endpoint added later and open to everyone by default, or a valid token treated as permission for everything.",
        "<ul><li>CSRF is off because the token travels in a header the browser never adds on its own. If the token moved into a cookie, CSRF protection must come back.</li><li><code>denyAll()</code> at the end: a new path is refused until someone decides who may use it.</li><li>Changing STATELESS to IF_REQUIRED turned no test red: the bearer filter never puts the sign-in into a session. The line stays, to say what the API is.</li></ul>")),
    (J + "JwtConfig.java", dwn("The key, the encoder and the decoder with its five checks.",
        "Signature with the shared key and HS256 only; exp and nbf with 60 seconds of allowance, on the app's clock; issuer; audience.",
        "Forged, unsigned, expired or misdirected tokens being accepted.",
        "<ul><li>Removing <code>.macAlgorithm(HS256)</code> turned no test red: it is already the default for <code>withSecretKey</code>. It stays, so the choice is written down.</li><li>The timestamp validator uses the machine's clock unless given one: a second decoder in a test, built without it, refused a fresh token. Found while building.</li></ul>")),
    (J + "TokenService.java", dwn("Writes the claims and signs them.",
        "15-minute tokens with iss, sub, aud, iat, exp and the member's grants as scope.",
        "Tokens that live for weeks, or carry more than they should.",
        "<p>Spring Security 7 adds a <code>FACTOR_PASSWORD</code> authority to a password sign-in. Built from <code>authentication.getAuthorities()</code>, every token's scope said <code>workouts:read FACTOR_PASSWORD</code>. The scope now comes from the member's own grants. Found while building.</p>")),
    (J + "AuthController.java", dwn("Login and \"my workouts\".",
        "One <code>401</code> for every failed login; \"me\" is the verified token subject.",
        "A member chosen by a parameter, or login answers that reveal which usernames exist.")),
    (J + "ProblemResponses.java", "<p>401 (with <code>WWW-Authenticate: Bearer</code>) and 403 in the same problem JSON as every other error.</p>"),
    ("src/main/resources/application.yaml", "<p>Issuer, audience, lifetime, allowance, and a demo key that real deployments take from a secret store.</p>"),
    (J + "WorkoutsApplication.java", "<p>Entry point, and the <code>Clock</code> every time check uses.</p>"),
]
tree = """stations/073-login-with-jwt-for-a-fitness-app/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/fitnest/workouts/
│   ├── SecurityConfig.java   ├── JwtConfig.java   ├── TokenService.java
│   ├── AuthController.java   ├── ProblemResponses.java   └── WorkoutsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/fitnest/workouts/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Docker", "Not needed: no database in this station", ""],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Log in, keep the token, use it, then decode its payload and read the claims:</p>
""" + code("""TOKEN=$(curl -s -X POST http://localhost:8080/auth/login -H 'Content-Type: application/json' \\
  -d '{"username": "asha", "password": "asha-demo-pass"}' | sed 's/.*"accessToken":"\\([^"]*\\)".*/\\1/')
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/workouts/me
echo "$TOKEN" | cut -d. -f2 | tr '_-' '/+' | base64 -d 2>/dev/null; echo""", "bash") + """
<p>Restart the app and send the same token: it still works, because nothing was remembered. Change the key in <code>application.yaml</code> and restart: now it does not.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Every token is <code>401</code> right after login", "Servers with different keys, or a clock far off.", "Every pod needs the same key; keep clocks in sync (NTP)."],
    ["<code>Jwt expired at …</code> in a test, for a fresh token", "A decoder built without the app's clock.", "Call <code>setClock</code> on the timestamp validator. Found while building this station."],
    ["<code>FACTOR_PASSWORD</code> in a token's scope", "Spring Security 7 adds it to a password sign-in.", "Build the scope from the member's own grants."],
    ["<code>403</code> on a new endpoint", "<code>denyAll()</code> at the end of the chain.", "Add a rule for the path, on purpose."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>WorkoutContractTest</code> ({cnt('WorkoutContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>UnverifiedTokenTrapTest</code> ({cnt('UnverifiedTokenTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, one user accessing another user's data, malicious input", f"<code>WorkoutSecurityTest</code> ({cnt('WorkoutSecurityTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">\"Not found\" here is the unknown username, answered like a wrong password on purpose, and the member with no workouts. \"Another user's data\": the only way to ask for Ravi's workouts is to change the token, which breaks its signature, or add a parameter, which is ignored.</p>
<p class="muted">Time is controlled: the app's <code>Clock</code> is a test clock, so \"16 minutes later\" takes no time and never depends on the machine.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Spring Security 7.1. No Docker needed. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "UnverifiedTokenTrapTest.java", "<p>Written first: sessions lost on restart, then a forged, an unsigned and an expired token, believed by the old read and refused by the API.</p>"),
    (T + "WorkoutSecurityTest.java", "<p>401 with a challenge, expiry with allowance, issuer and audience, 403, a changed payload, garbage headers.</p>"),
    (T + "WorkoutContractTest.java", "<p>Login and workouts through HTTP, and what the token says.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the test clock, a test key, login helpers, and <code>forge</code> to build tokens the way an attacker would.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/fitnest/workouts/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=LogoutRevokesTokenChallengeTest</code>.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Logout that revokes one token", "Beginner-friendly", 30,
    "Add <code>POST /auth/logout</code> with the bearer token: <code>204</code>, and that token is <code>401</code> from then on, while a new login works.",
    "both tests in <code>LogoutRevokesTokenChallengeTest</code> pass.",
    ["Give every token an id: <code>.id(UUID.randomUUID().toString())</code> sets the <code>jti</code> claim.",
     "Keep revoked ids with their expiry, and forget them once the token would have expired anyway.",
     "Add a validator to the decoder that fails for a revoked id. <code>JwtClaimValidator</code> also fails when the claim is missing, so write a plain one."],
    "challenge/LogoutRevokesTokenChallengeTest.java", ["challenge/solution/RevokedTokens.java", "challenge/solution/JwtConfig.java", "challenge/solution/TokenService.java", "challenge/solution/AuthController.java", "challenge/solution/SecurityConfig.java"]) + challenge(2, "A coach reads their trainees' workouts", "Go deeper", 30,
    "Add coach kabir (scope <code>coach:read</code>) and <code>GET /workouts/{member}</code>: <code>200</code> for his trainees (demo rule: asha), <code>403</code> for anyone else, and <code>403</code> for members without the scope.",
    "both tests in <code>CoachReadsTraineesChallengeTest</code> pass.",
    ["The scope says \"is a coach\"; it does not say \"of whom\". Check the trainee list too.",
     "A rule for <code>/workouts/*</code> in the filter chain; <code>/workouts/me</code> keeps its own rule, which comes first."],
    "challenge/CoachReadsTraineesChallengeTest.java", ["challenge/solution/AuthController.java", "challenge/solution/SecurityConfig.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Refresh tokens and a new signing key</h2>
<p>Members should not log in every 15 minutes, and the key must be replaced one day without logging everyone out. Design a refresh token (where it is stored, how it is rotated and revoked) and a key change with a <code>kid</code> header, where for a while both keys verify and only the new one signs. When would you move from one shared key (HS256) to a private key that signs and public keys that verify (RS256 or ES256)?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: sessions lost on restart, then three tokens the base64-only read believes.</li>
<li>Issue tokens with Spring Security's <code>JwtEncoder</code> after a normal password check.</li>
<li>Validate with the OAuth2 resource server: one decoder with every check, on the app's clock.</li>
<li>Authorise by scope, and refuse every path not listed.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Signed 15-minute JWT, HS256, shared key", "No logout before expiry; every server holds the signing key.", '<span class="pill ok">Chosen</span>'],
    ["Base64-decode the token and trust it", "Anyone can write any member's name.", '<span class="pill bad">The trap</span>'],
    ["Sessions in each server's memory", "Lost on every restart; sticky routing needed.", '<span class="pill bad">The old problem</span>'],
    ["Sessions in a shared store (Spring Session with Valkey)", "Logout is easy; every request reads the store.", '<span class="pill warn">Valid, especially for browsers</span>'],
    ["RS256 or ES256: a private key signs, public keys verify", "Key pairs and a key set to publish; only the issuer can sign.", '<span class="pill warn">When other services verify</span>'],
    ["Opaque tokens with introspection", "A call to the issuer per request (or a cache); instant revoke.", '<span class="pill warn">When revocation must be instant</span>']]) + """
<h2>Database design</h2>
<p>No database in this station: the point is that the API keeps no login state. Members and workouts are demo data in the app. Stations 074 and 076 store sessions and passkeys in PostgreSQL, with their constraints.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>The key</dt><dd>Anyone with the HS256 key can sign tokens for any member. Keep it in a secret store, at least 256 bits, never in the repository (the one here is a demo key), and plan how to replace it.</dd>
<dt>Revocation</dt><dd>A stolen token works until it expires. Short lifetimes limit the damage; a revoke list (challenge 1) or refresh tokens (station 074) cover the rest.</dd>
<dt>Clocks</dt><dd>Expiry depends on every server's clock. Keep them in sync (NTP) and the allowance small.</dd>
<dt>Logs</dt><dd>Never log the <code>Authorization</code> header or tokens: each one is a key to an account until it expires.</dd>
<dt>Standards</dt><dd>JWT is RFC 7519 and JWS is RFC 7515 (both Proposed Standards); RFC 8725 (Best Current Practice, BCP 225) lists what to check; bearer tokens over HTTP are RFC 6750 (Proposed Standard).</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Is a JWT encrypted?", "Usually not. A signed JWT (JWS) is only base64url-encoded: anyone can read the claims. The signature stops changes, not reading. Put nothing secret in it."),
    ("What must a server check on every token?", "The signature with the expected key, an allowed algorithm (never \"none\"), exp and nbf with a small allowance, the issuer and the audience. Then the scopes for the endpoint."),
    ("401 or 403?", "401 when the caller is not authenticated (no token, or one that fails a check), with WWW-Authenticate. 403 when the token is valid but does not grant this."),
    ("How do you log out a JWT?", "You cannot change a token already issued. Keep lifetimes short, keep a revoke list of token ids until they expire, or use refresh tokens that can be revoked."),
    ("HS256 or RS256?", "HS256: one shared secret signs and verifies, fine when one team runs every server. RS256 or ES256: only the issuer holds the private key, and anyone can verify with the public key."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Validation", "Signature, algorithm and expiry checked.", "Issuer, audience and clock allowance too, tested with a controlled clock."],
    ["Authorization", "401 and 403 used correctly.", "Scopes kept to the member's own grants."],
    ["Operations", "The key is not in code.", "A plan to revoke tokens and replace the key."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("No issuer or audience check",
     "\"Our own tokens only\" is the assumption that breaks: a token signed with the same key for another FitNest API, or by another issuer sharing the key, is accepted here.",
     "<code>aTokenFromAnotherIssuerOrForAnotherApiIs401</code> fails."),
    ("30-day tokens",
     "Members hate logging in, but a stolen token now opens the account for a month, and there is no way to take it back.",
     "<code>loginGivesAShortLivedBearerToken</code>, <code>thePayloadSaysWhoForWhichApiAndWhatTheyMayDo</code>, <code>aTokenExpiresAfter15MinutesWithOneMinuteForClockDifferences</code> and <code>readingWithoutVerifyingTrustsAnExpiredToken</code> fail."),
    ("Any signed-in member reads workouts",
     "<code>authenticated()</code> instead of the scope: newbie, who may not read workouts yet, gets them. A valid token is identity, not permission.",
     "<code>aMemberWithoutTheScopeIs403</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate simplifies the token setup: \"we only accept our own tokens, so issuer and audience checks are noise\". Members complained about logging in, so tokens now last 30 days, and the workouts rule is now just \"signed in\". Read the three files and list every problem before opening the findings.</p>
<p class="path">review/JwtConfig.java</p>
""" + code(read("review/JwtConfig.java"), "java") + """
<p class="path">review/TokenService.java</p>
""" + code(read("review/TokenService.java"), "java") + """
<p class="path">review/SecurityConfig.java</p>
""" + code(read("review/SecurityConfig.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the three flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">Every flaw here still lets the normal login and workouts work. Only tests that try the wrong token, the old token and the wrong member catch them.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
