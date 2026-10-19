"""Station 075 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 75,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Security 7 oauth2Login · OpenID Connect · authorization code flow with PKCE · Nimbus JOSE",
    "simulation": "Google is simulated in the tests: a local server with its own signing key plays Google's discovery, key and token endpoints. The running app is set up for the real Google with a demo client id that Google does not know, so a real sign-in stops at Google's page. Taskloom accounts are demo data in memory.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No database and no Docker. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows). A real Google sign-in needs your own Google Cloud client id and secret.",
}
J = "src/main/java/com/taskloom/signin/"
T = "src/test/java/com/taskloom/signin/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("OAuth 2.0", "A way for an app to get a token from another service without seeing your password there.", "A hotel giving a cleaner a key card for one floor.", "Google's authorization server"),
    ("OpenID Connect", "OAuth 2.0 plus an ID token that says who signed in.", "The receptionist's signed note: this guest is Asha.", "scope <code>openid</code>"),
    ("ID token", "A signed JWT from Google: who (sub, email), for which app (aud), from whom (iss), until when (exp).", "A visitor badge printed for one building.", "checked by Spring Security"),
    ("Authorization code", "A one-time code Google sends back through the browser; the server swaps it for tokens directly with Google.", "A cloakroom ticket, exchanged at the counter.", "<code>/login/oauth2/code/google</code>"),
    ("PKCE", "A secret made per sign-in: its hash goes to Google first, the secret itself with the code later. A stolen code alone is useless.", "Half of a torn ticket, matched at the end.", "<code>code_challenge</code>, <code>code_verifier</code>"),
    ("State and nonce", "Random values that tie Google's answer to this browser's own sign-in, and the ID token to this request.", "A reference number you check on the reply.", "<code>state</code>, <code>nonce</code>"),
]
STORY = [
    ("Teams want Google", "Taskloom's customers already have Google accounts and asked to use them instead of yet another password."),
    ("A home-made flow", "The first version took an ID token from the browser, decoded it and used the email in it. A token that Google had issued to some other app, for the same person, signed them in to Taskloom too."),
    ("The fix", "The standard code flow, run by Spring Security: the token comes straight from Google to the server, and its signature, issuer, audience, expiry and nonce are all checked before anyone is signed in."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A real Google signature only says Google wrote it. Whether it was written for you is in the audience.</p>

<h2>What are we building?</h2>
<p><code>GET /oauth2/authorization/google</code> sends the browser to Google; Google sends it back with a code; Taskloom checks everything and signs the person in to their Taskloom account. <code>GET /me</code> shows that account.</p>

<h2>An everyday analogy</h2>
<p>A visitor badge from the front desk works only in the building it was printed for, only today, and only if the desk's stamp is real. A badge from the building next door, with the same name on it, does not open this door.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Start</strong>: Taskloom redirects to Google with its client id, a state, a nonce and a PKCE challenge.</li>
<li><strong>Consent</strong>: the person signs in at Google; Google redirects back with a one-time code and the same state.</li>
<li><strong>Swap</strong>: Taskloom's server sends the code and the PKCE secret to Google, and receives the ID token directly.</li>
<li><strong>Check, then link</strong>: signature, issuer, audience, expiry, nonce; then the Taskloom account for that Google id.</li>
</ol>

<details class="qa check"><summary>Check yourself: the ID token is really signed by Google and really says asha. Why can it still be refused?</summary><p>Because it may have been issued to a different app (its audience is that app's client id). Any app Asha signs in to receives such a token; if Taskloom accepted it, every one of those apps could sign in to Taskloom as Asha. The trap test <code>aGoogleTokenMeantForAnotherAppIsRefused</code> shows it.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real Google in the tests.</strong> A local stand-in plays Google, with its own key; the checks are Spring's real ones.</li>
<li><strong>No passwords.</strong> Taskloom never sees one. Passkeys are station 076.</li>
<li><strong>No token for calling Google APIs.</strong> Only sign-in: the access token Google returns is not used.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Taskloom</strong> (a fictional team task tool) wants Google sign-in; its home-made flow accepted ID tokens meant for other apps.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo data: asha is already linked to her Google account; meera and kabir are invited. Tests invite their own people.</p>
<ol class="gwt">
<li><b>Given</b> a start, <b>then</b> a redirect to Google with this app's client id, <code>openid email profile</code>, a state, a nonce and an S256 PKCE challenge.</li>
<li><b>Given</b> Google's answer with an ID token for this app, <b>then</b> the person is signed in and <code>GET /me</code> shows their Taskloom account.</li>
<li><b>Given</b> an ID token for another app, from another issuer, with a bad signature, expired, or with another nonce, <b>then</b> <code>401</code> and no sign-in.</li>
<li><b>Given</b> a callback with a state this browser did not start, <b>then</b> <code>401</code>, and Google is never asked for tokens.</li>
<li><b>Given</b> a Google account with no Taskloom account, <b>then</b> <code>403</code>.</li>
<li><b>Given</b> an invited email that Google has not verified, <b>then</b> it is not linked.</li>
<li><b>Given</b> a sign-out without the CSRF token, <b>then</b> <code>403</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Accounts are linked by Google's <code>sub</code>, which never changes; the email is used only once, to accept an invitation, and only when verified.</li>
<li>Failed sign-ins do not say which check failed.</li>
<li>The client secret never reaches the browser.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Explain the authorization code flow with PKCE, state and nonce.</li>
<li>Name every check on an ID token, and what each one stops.</li>
<li>Configure <code>oauth2Login</code> and link Google identities to local accounts.</li>
<li>Explain why CSRF protection is back on here, unlike stations 071 to 074.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/oauth2/authorization/google</code>", "Starts sign-in: <code>302</code> to Google. Handled by Spring Security."],
    ["<code>GET</code>", "<code>/login/oauth2/code/google</code>", "Google's redirect back with <code>code</code> and <code>state</code>. Handled by Spring Security: <code>302</code> to <code>/me</code>, or a problem."],
    ["<code>GET</code>", "<code>/me</code>", "The signed-in person's Taskloom account."],
    ["<code>POST</code>", "<code>/logout</code>", "Signs out; needs the CSRF token. <code>204</code>."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span> / <span class="pill ok">204</span>', "Account shown / signed out"],
    ['<span class="pill ok">302</span>', "To Google at the start; to <code>/me</code> after a good sign-in"],
    ['<span class="pill warn">401</span>', "Not signed in; or the sign-in failed any check (state, token, signature, issuer, audience, expiry, nonce), or was cancelled at Google"],
    ['<span class="pill warn">403</span>', "Signed in at Google, but no Taskloom account for it; a sign-out without the CSRF token"],
    ['<span class="pill warn">404</span>', "A sign-in provider other than Google"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. These stop at the redirect or are refused before Google would be asked, so they need no network. The full sign-in, with Google's answer, runs in the tests against the stand-in. <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-start-sign-in", "Case 1: start sign-in", "<b>Why:</b> to Google, with state, nonce and a PKCE challenge, all new for this sign-in. The session cookie remembers them for the way back."),
    ("02-me-without-signing-in", "Case 2: <code>/me</code> without signing in", "<b>Why:</b> <code>401</code> and where to start. (Spring also keeps this request in a session, to return to it after sign-in.)"),
    ("03-an-unknown-provider", "Case 3: a provider that is not set up", "<b>Why:</b> <code>404</code>. Spring's default here is a <code>500</code>."),
    ("04-a-callback-this-browser-never-started", "Case 4: a callback this browser never started", "<b>Why:</b> no matching state in its session: <code>401</code>, and Google is not asked."),
    ("05-sign-out-without-the-csrf-token", "Case 5: sign-out without the CSRF token", "<b>Why:</b> <code>403</code>: a form on another website could send this request with the cookie."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Start", "Redirect with this app's id, scopes, redirect URI, state, nonce, challenge", "<code>startingSignInRedirectsToGoogleForThisApp</code>"],
    ["A linked member signs in", "<code>/me</code> shows their account; a parameter chooses nothing", "<code>aLinkedMemberSignsInAndSeesTheirAccount</code>"],
    ["First sign-in of an invited email, later a changed Google email", "Linked by email once, then by Google id", "<code>anInvitedEmailIsLinkedAtFirstSignInAndTheGoogleIdAfterThat</code>"],
    ["A Google account with no Taskloom account", "<code>403</code>, not signed in", "<code>aGoogleAccountWithNoTaskloomAccountIs403AndANewSignInIsNotStarted</code>"],
    ["Not signed in; another provider", "<code>401</code>; <code>404</code>", "<code>meWithoutSigningInIs401AndAnUnknownProviderIs404</code>"],
    ["PKCE, state and nonce", "S256; new for every sign-in; the verifier matches the challenge", "<code>everySignInGetsItsOwnPkceChallengeStateAndNonce</code>, <code>theVerifierSentToGoogleMatchesTheChallengeInTheRedirect</code>"],
    ["Another browser's state", "<code>401</code>, Google never asked", "<code>aCallbackWithAnotherBrowsersStateIsRefusedBeforeGoogleIsAsked</code>"],
    ["Another nonce", "<code>401</code>", "<code>anIdTokenWithAnotherNonceIsRefused</code>"],
    ["An unverified invited email", "Not linked; the invitation stays", "<code>anUnverifiedEmailNeverLinksAnInvitation</code>"],
    ["A second Google account with a linked member's email", "<code>403</code>: someone else", "<code>anotherGoogleAccountWithALinkedMembersEmailDoesNotBecomeThatMember</code>"],
    ["Sign-in", "A new session id", "<code>theSessionIdChangesAtSignIn</code>"],
    ["Sign-out without and with the CSRF token", "<code>403</code>; <code>204</code>", "<code>signingOutNeedsTheCsrfTokenBecauseTheCookieTravelsByItself</code>"],
    ["Cancelled consent, SQL-looking state, 5,000 characters, an unknown code", "<code>401</code>, never an error", "<code>oddCallbacksAre401NeverAnError</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Accepting any ID token without checking issuer and audience.</p>
<p>Each test makes one ID token, shows that the old decode-only check signs in as asha, then lets the stand-in Google hand out exactly that token in a real sign-in:</p>
<ul>
<li><strong>For another app.</strong> Signed by Google, about asha, but its audience is a photo app's client id: <code>401</code>.</li>
<li><strong>From another issuer.</strong> Same signature key, issuer <code>https://accounts.evil.example</code>: <code>401</code>.</li>
<li><strong>Someone else's key.</strong> Even with Google's key id in the header: <code>401</code>.</li>
<li><strong>Expired.</strong> Last week's token: <code>401</code>.</li>
<li><strong>The control.</strong> The same claims, right in every way: signed in.</li>
</ul>
<p>While building, each part was undone once: no <code>email_verified</code> check turned 1 test red; CSRF off 1; no new session id at sign-in 1; no <code>403</code> for unknown accounts 2; no handler for unknown providers 1; no lower-casing of emails 1. The explicit PKCE setting turned nothing red and was removed: see Code.</p>
</div>
""" + code(read(T + "UncheckedIdTokenTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SecurityConfig.java", dwn("oauth2Login, the account step, logout and the error answers.",
        "Spring runs the redirect and the callback; after Spring's ID token checks, the account step links or refuses; <code>/me</code> needs a sign-in; everything else refused.",
        "A Google account becoming a Taskloom member just by existing, or a sign-out any website can trigger.",
        "<ul><li>CSRF protection stays on: the sign-in now lives in a session cookie, which the browser sends with any request to this site, including one made by another site's form.</li><li>PKCE: Spring Security 7 sends a challenge for confidential clients too. The explicit <code>withPkce()</code> customizer turned no test red when removed, so it is gone. Found while building.</li><li>An unknown provider (<code>/oauth2/authorization/github</code>) is a <code>500</code> by default; an <code>ObjectPostProcessor</code> sets the redirect filter's failure handler to a <code>404</code>. Found while building.</li></ul>")),
    (J + "Accounts.java", dwn("Taskloom accounts and their link to a Google id.",
        "Linked by <code>sub</code>; an invitation is accepted only for a verified email; emails compared lower-case.",
        "Account takeover: someone creating a Google account with a member's address, unverified, or a second Google account that shows the same address.",
        "<p>Simulated in memory. <code>shortcut: lost on restart, one pod only; a real app keeps both maps in its database.</code></p>")),
    (J + "TaskloomUser.java", "<p>The signed-in principal: Google's checked identity plus the linked Taskloom account.</p>"),
    (J + "MeController.java", "<p><code>/me</code> from the principal; nothing in the request chooses the account.</p>"),
    (J + "ProblemResponses.java", "<p>One problem shape for 401, 403 and 404. A failed sign-in never says which check failed.</p>"),
    ("src/main/resources/application.yaml", "<p>The Google client registration. Spring Boot knows Google's endpoints and issuer; the values here are demo values.</p>"),
    (J + "SignInApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/075-sign-in-with-google/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/taskloom/signin/
│   ├── SecurityConfig.java   ├── Accounts.java   ├── TaskloomUser.java
│   ├── MeController.java   ├── ProblemResponses.java   └── SignInApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/taskloom/signin/   FakeGoogle.java and the tests
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Docker", "Not needed", ""],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""],
    ["For a real Google sign-in", "Your own OAuth client in Google Cloud, with redirect URI <code>http://localhost:8080/login/oauth2/code/google</code>", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""./mvnw spring-boot:run      # the app on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests, against the stand-in Google""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>See where sign-in sends a browser, without following it:</p>
""" + code("""curl -s -o /dev/null -w '%{redirect_url}\\n' http://localhost:8080/oauth2/authorization/google""", "bash") + """
<p>Run it twice: <code>state</code>, <code>nonce</code> and <code>code_challenge</code> change every time. With your own client id and secret in <code>application.yaml</code> (or as environment variables), open <code>http://localhost:8080/oauth2/authorization/google</code> in a browser: after Google, the sign-in ends in <code>403</code> until your Google email is in the invitation list in <code>Accounts.java</code>. (Not run while building this station: it needs your own Google client.)</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>redirect_uri_mismatch</code> at Google", "The redirect URI in Google Cloud differs from Spring's.", "Register exactly <code>{baseUrl}/login/oauth2/code/google</code>."],
    ["<code>500</code> on <code>/oauth2/authorization/xyz</code>", "Spring's default for an unknown registration id.", "Set the redirect filter's failure handler, as <code>SecurityConfig</code> does."],
    ["<code>403</code> on <code>POST /logout</code>", "No CSRF token: protection is on, because the sign-in is a cookie.", "Send the token (a form field or the <code>X-CSRF-TOKEN</code> header)."],
    ["<code>invalid_id_token</code> in the log", "A claim check failed: issuer, audience, expiry or nonce.", "Fix the configuration (issuer, client id), never the validator."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>SignInContractTest</code> ({cnt('SignInContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>UncheckedIdTokenTrapTest</code> ({cnt('UncheckedIdTokenTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, one user accessing another user's data, malicious input", f"<code>SignInSecurityTest</code> ({cnt('SignInSecurityTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">\"Another user's data\" here is account takeover: a second Google account with a member's email, or an unverified one, never becomes that member. How the stand-in works: <code>FakeGoogle</code> is a JDK HTTP server on a local port with discovery, its public key and a token endpoint; the app finds it through <code>issuer-uri</code>, so the token request and every check run for real.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Spring Security 7.1. No Docker. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "UncheckedIdTokenTrapTest.java", "<p>Written first: four ID tokens the old check believed, each refused by the real sign-in, and the control.</p>"),
    (T + "SignInSecurityTest.java", "<p>PKCE, state, nonce, account takeover, session fixation, CSRF, odd callbacks.</p>"),
    (T + "SignInContractTest.java", "<p>The redirect, sign-in and linking, <code>/me</code>, 401, 403, 404.</p>"),
    (T + "FakeGoogle.java", "<p>The stand-in for Google: discovery, keys, token endpoint, on a local port.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the app pointed at the stand-in; helpers that walk through a whole sign-in.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/taskloom/signin/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=WorkspaceDomainChallengeTest</code>.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Company accounts only, for Globex", "Beginner-friendly", 25,
    "Globex accepts only its own Google Workspace accounts: linking a Globex invitation needs the ID token's <code>hd</code> (hosted domain) claim to be <code>globex.example</code>. A personal Google account gets <code>403</code> and the invitation stays.",
    "the test in <code>WorkspaceDomainChallengeTest</code> passes.",
    ["<code>user.getClaimAsString(\"hd\")</code> in the account step; pass it to <code>Accounts.forGoogle</code>.",
     "Check before removing the invitation, so a refused sign-in leaves it for the right account."],
    "challenge/WorkspaceDomainChallengeTest.java", ["challenge/solution/Accounts.java", "challenge/solution/SecurityConfig.java"]) + challenge(2, "Members list for admins", "Go deeper", 30,
    "<code>GET /workspace/members</code>: the names of the signed-in members of the caller's own workspace, for workspace admins only (demo rule: asha administers Acme). Others get <code>403</code>.",
    "both tests in <code>WorkspaceAdminChallengeTest</code> pass.",
    ["Give the principal <code>ROLE_ADMIN</code> when the account is an admin, and add a <code>hasRole(\"ADMIN\")</code> rule.",
     "The workspace comes from the signed-in account, never from the request."],
    "challenge/WorkspaceAdminChallengeTest.java", ["challenge/solution/TaskloomUser.java", "challenge/solution/MeController.java", "challenge/solution/Accounts.java", "challenge/solution/SecurityConfig.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>A mobile app, and signing out everywhere</h2>
<p>Taskloom's phone app cannot keep a client secret: anything shipped in an app can be read. Design its sign-in as a public client (PKCE only, the system browser, a custom redirect URI). Then: when a company disables an employee in Google Workspace, how does Taskloom find out? Compare short Taskloom sessions with OpenID Connect back-channel logout.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: tokens the decode-only check believed.</li>
<li>Build a stand-in Google for the tests, so every step is real HTTP and real validation.</li>
<li>Configure <code>oauth2Login</code>; let Spring run the flow and the ID token checks.</li>
<li>Add the account step: link by <code>sub</code>, accept invitations for verified emails only.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Code flow with PKCE via Spring's oauth2Login; session cookie", "A session per user; CSRF protection needed.", '<span class="pill ok">Chosen</span>'],
    ["Decode an ID token sent by the browser", "Any token for any app signs people in.", '<span class="pill bad">The trap</span>'],
    ["Verify an ID token sent by the browser (signature, iss, aud, exp)", "Fine for a mobile app with Google's SDK; no nonce tied to this server's request.", '<span class="pill warn">Valid with every check</span>'],
    ["Link accounts by email", "Simple; emails change and can be reused.", '<span class="pill bad">Takeover risk</span>'],
    ["A broker (Keycloak, Auth0, Cognito) in front of Google", "One more system; many providers and enterprise SSO for free.", '<span class="pill warn">When more providers come</span>']]) + """
<h2>Database design</h2>
<p>No database in this station: accounts and links are demo data in memory. In a real app: a <code>google_links</code> table with <code>sub</code> as a unique key and the account id, and invitations with a unique lower-case email. The link is the thing that must never be guessed from an email.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>The client secret</dt><dd>From a secret store, never the repository (the one here is a demo value). Register the exact redirect URIs only.</dd>
<dt>Cookies</dt><dd>Captures show the session cookie with <code>HttpOnly</code> only, because the demo runs on plain HTTP. In production: HTTPS, <code>server.servlet.session.cookie.secure=true</code> and a <code>SameSite</code> setting.</dd>
<dt>Several pods</dt><dd>The sign-in in progress (state, nonce, PKCE verifier) and the session live in one pod's memory. Use sticky sessions or Spring Session with a shared store.</dd>
<dt>Logs</dt><dd>Never log codes, tokens or the client secret.</dd>
<dt>Standards</dt><dd>OAuth 2.0 is RFC 6749 and PKCE RFC 7636 (both Proposed Standards); OpenID Connect Core 1.0 is an OpenID Foundation final specification; the OAuth 2.0 Security Best Current Practice is RFC 9700 (BCP 240).</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is the difference between OAuth 2.0 and OpenID Connect?", "OAuth 2.0 gives an app an access token to call an API. OpenID Connect adds an ID token that says who signed in, and rules for checking it. Sign-in needs OpenID Connect."),
    ("Which checks does an ID token need?", "Signature with the provider's published key, issuer equal to the provider, audience containing this app's client id, not expired, and the nonce this app sent."),
    ("Why PKCE if the server has a client secret?", "It ties the code to the sign-in that asked for it: a code stolen from a redirect cannot be swapped by anyone who does not hold the verifier. Current guidance asks for it for every client."),
    ("What do state and nonce protect?", "State ties Google's redirect to this browser's own sign-in (no one can make you finish theirs). Nonce ties the ID token to this request (no replay of an old token)."),
    ("Why link by sub and not by email?", "sub is Google's permanent id for the account. Emails change, can be unverified, and an address can later belong to someone else."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Flow", "Code flow through Spring's oauth2Login.", "You can say what state, nonce and PKCE each stop."],
    ["Tokens", "All five ID token checks.", "A test for each, through a stand-in provider."],
    ["Accounts", "Linked by sub.", "No takeover through unverified or reused emails."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("The ID token validator checks only the expiry",
     "\"Issuer mismatch on staging\" was a configuration problem; replacing the validator removes the issuer and audience checks for everyone. Any app's Google token for a person now signs them in here: the original incident.",
     "<code>aGoogleTokenMeantForAnotherAppIsRefused</code> and <code>aTokenFromAnotherIssuerIsRefused</code> fail."),
    ("CSRF protection turned off",
     "The sign-in is a session cookie now: any website can make a visitor's browser post to Taskloom with it.",
     "<code>signingOutNeedsTheCsrfTokenBecauseTheCookieTravelsByItself</code> fails."),
    ("Accounts found by email, verified or not",
     "\"People who switch Google accounts\" can also be people who create one with someone else's address. Any Google account showing a member's email becomes that member, and unverified emails accept invitations.",
     "<code>anotherGoogleAccountWithALinkedMembersEmailDoesNotBecomeThatMember</code> and <code>anUnverifiedEmailNeverLinksAnInvitation</code> fail."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate fixes three tickets at once: staging sign-ins failing with <code>invalid_id_token</code> (\"the signature is what matters\"), the web app getting <code>403</code> on sign-out, and members who switched Google accounts losing their Taskloom account. Read the two files and list every problem before opening the findings.</p>
<p class="path">review/SecurityConfig.java</p>
""" + code(read("review/SecurityConfig.java"), "java") + """
<p class="path">review/Accounts.java</p>
""" + code(read("review/Accounts.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the two flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">Each ticket was real. The expired-token, forged-key and nonce tests still pass on the flawed version: the signature and expiry are still checked, which is exactly why the missing audience check is easy to miss.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
