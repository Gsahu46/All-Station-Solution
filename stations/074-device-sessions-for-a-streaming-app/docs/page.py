"""Station 074 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 74,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Security 7 resource server · HS256 access tokens · rotating refresh tokens · JdbcClient · PostgreSQL 17 · Testcontainers",
    "simulation": "Members and devices are demo data, not Streamo's. No video plays: \"playback\" is only a scope in the token. The signing key in application.yaml is a demo key.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/streamo/devices/"
T = "src/test/java/com/streamo/devices/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Access token", "A signed token that opens the API for 10 minutes.", "A day pass to a gym.", "<code>accessToken</code>, a JWT"),
    ("Refresh token", "A long random secret the app trades for a new access token, without the password.", "The membership card you show to get today's day pass.", "<code>refreshToken</code>, 30 days"),
    ("Rotation", "Every refresh hands back a new refresh token; the old one is used up.", "A card that is swapped for a new one at every visit.", "<code>refresh_tokens.used_at</code>"),
    ("Reuse detection", "A used-up refresh token shown again means two people have it: end the device.", "Two people with the same old card: both are stopped at the desk.", "<code>revoked_reason = 'reuse'</code>"),
    ("Device session", "One signed-in device: what the device list shows and what \"remove\" ends.", "One key on the key ring.", "<code>device_sessions</code>"),
    ("Hash", "A one-way fingerprint: the table holds it, never the token.", "A fingerprint, not the finger.", "SHA-256 in <code>token_hash</code>"),
]
STORY = [
    ("A token on a shared laptop", "Streamo's apps got a refresh token at sign-in that lasted a year and never changed. A copy taken from a shared laptop kept working."),
    ("The button that did nothing", "The owner pressed \"log out of all devices\". It refreshed her screen; the copied token kept working for months."),
    ("The fix", "Refresh tokens are swapped at every use and stored only as hashes. A used one shown again ends that device for everyone holding it. Each device can be removed, and its access token stops at once."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A secret that never changes can be copied once and used forever. Make every copy go stale.</p>

<h2>What are we building?</h2>
<p>Sign-in per device, <code>POST /auth/refresh</code> that swaps the refresh token every time, <code>POST /auth/logout</code> for this device, and a device list where each device can be removed.</p>

<h2>An everyday analogy</h2>
<p>A hotel key card that the desk re-codes every morning. Last night's card stops working. If someone shows up with last night's card, the desk knows a copy exists and cancels that room's cards, and the guest comes down for a new one.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Sign in</strong> on a device: a 10-minute access token and a 30-day refresh token. The table stores only the refresh token's hash.</li>
<li><strong>Refresh</strong>: the refresh token is used up in one database statement and a new one comes back.</li>
<li><strong>Reuse</strong>: a used-up token shown again ends the device: the thief's copy and the owner's new token both stop.</li>
<li><strong>Remove</strong> a device from the list: its refresh token stops, and its access token is refused on the next request.</li>
</ol>

<details class="qa check"><summary>Check yourself: a thief copies the refresh token and uses it before the owner does. Who is caught?</summary><p>Both. The thief gets a new pair; then the owner's app sends the old token, which is now used up. That ends the device, so the thief's new token dies too, and the owner simply signs in again. The trap test <code>theThiefRefreshingFirstIsCaughtWhenTheOwnerRefreshes</code> shows it.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No playback.</strong> \"playback\" is only a scope; nothing streams.</li>
<li><strong>No sign-in with Google or passkeys.</strong> Those are stations 075 and 076.</li>
<li><strong>Tokens are not tied to the device's hardware.</strong> A copied token works until it is used twice or removed (see Practice, challenge 3).</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Streamo</strong> (a fictional streaming app): a stolen refresh token kept working for months, and \"log out of all devices\" did nothing.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo data: members anika and rohan. Demo rules: access tokens last 10 minutes, refresh tokens 30 days.</p>
<ol class="gwt">
<li><b>Given</b> a right email and password on a device, <b>then</b> <code>200</code> with an access token, a refresh token and the device id.</li>
<li><b>Given</b> a valid refresh token, <b>then</b> <code>200</code> with a new pair, and the old refresh token is used up.</li>
<li><b>Given</b> a used-up refresh token, <b>then</b> <code>401</code>, and that device is signed out for everyone.</li>
<li><b>Given</b> a device removed from the list or logged out, <b>then</b> its access and refresh tokens are refused at once.</li>
<li><b>Given</b> another member's device id, <b>then</b> <code>404</code>, the same as an unknown id, and nothing changes.</li>
<li><b>Given</b> a TV's token, <b>then</b> the device list is <code>403</code>: a TV in a living room may play, not manage the account.</li>
<li><b>Given</b> ten refreshes with one token at the same moment, <b>then</b> exactly one gets a new pair.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Refresh tokens are 32 random bytes; only their SHA-256 is stored.</li>
<li>At most one unused refresh token per device: the database enforces it.</li>
<li>Unknown, expired, used and signed-out refresh tokens all get the same answer.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Pair short access tokens with rotating refresh tokens.</li>
<li>Detect reuse and end the device session.</li>
<li>Make revocation immediate, and say what it costs.</li>
<li>Put ownership into the query, and answer 404 for other people's things.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/auth/login</code>", "<code>{email, password, deviceName, deviceType}</code> (phone, tv or web); a new device session and its token pair."],
    ["<code>POST</code>", "<code>/auth/refresh</code>", "<code>{refreshToken}</code>; a new pair, the old refresh token used up."],
    ["<code>POST</code>", "<code>/auth/logout</code>", "Bearer token; signs out this device only. <code>204</code>."],
    ["<code>GET</code>", "<code>/me/devices</code>", "This member's signed-in devices, oldest first; <code>current</code> marks the one asking. Scope <code>devices</code>."],
    ["<code>DELETE</code>", "<code>/me/devices/{id}</code>", "Signs out one device. Scope <code>devices</code>. <code>204</code>."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span> / <span class="pill ok">204</span>', "Tokens issued, list returned / device signed out"],
    ['<span class="pill warn">400</span>', "A field missing or too long, an unknown device type, a refresh token of the wrong shape, a device id that is not a UUID"],
    ['<span class="pill warn">401</span>', "Wrong login; a refresh token that is unknown, expired, used or signed out; no access token, or one that fails a check or whose device is signed out"],
    ['<span class="pill warn">403</span>', "A TV's token on the device endpoints"],
    ['<span class="pill warn">404</span>', "A device id that is unknown or another member's"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code>, connection and standard security headers are left out. Each real token is replaced by a name, so you can follow which one was sent.</p>
""" + examples([
    ("01-login-on-a-phone", "Case 1: anika signs in on her phone", "<b>Why:</b> a pair for this device, and its id."),
    ("02-login-on-a-tv", "Case 2: and on the living-room TV", "<b>Why:</b> a second device session."),
    ("03-refresh", "Case 3: the phone refreshes", "<b>Why:</b> refresh token 1 is used up; token 2 replaces it. The access token is the same text as in case 1: same member, device, scope and second, and signing the same claims with the same key gives the same token."),
    ("04-the-device-list", "Case 4: the device list from the phone", "<b>Why:</b> both devices; the phone is <code>current</code>."),
    ("05-the-tv-asks-for-the-list", "Case 5: the TV asks for the list", "<b>Why:</b> <code>403</code>: its token has <code>playback</code> only."),
    ("06-remove-the-tv", "Case 6: the phone removes the TV", "<b>Why:</b> <code>204</code>."),
    ("07-the-tv-right-after", "Case 7: the TV's access token, right after", "<b>Why:</b> <code>401</code> at once, not in 10 minutes."),
    ("08-another-members-device", "Case 8: rohan tries to remove anika's phone", "<b>Why:</b> <code>404</code>, as for an id that does not exist; the phone stays signed in."),
    ("09-the-used-refresh-token-again", "Case 9: refresh token 1 again, as a thief would", "<b>Why:</b> used up: <code>401</code>, and the phone's session ends."),
    ("10-the-phone-after-reuse", "Case 10: the phone's own new token", "<b>Why:</b> also <code>401</code>: anika signs in again, and the thief's copy is dead for good."),
]) + """
<h2>What the database holds afterwards</h2>
<p class="muted">From <code>psql</code> in <code>docs/capture.sh</code>, after the requests above.</p>
""" + code(read("docs/captures/sessions.txt").rstrip(), "text") + code(read("docs/captures/tokens.txt").rstrip(), "text") + """
<p>The TV was removed (case 6) and the phone ended by reuse (case 9); Rohan's phone is untouched (case 8). Only hashes are stored (cut to 16 characters here). Both of the phone's tokens show as used: token 2 was used up by the attempt in case 10, although the device had already ended, so it got no new pair.</p>"""

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Login", "A pair for this device: 600-second access token, 43-character refresh token", "<code>loginGivesAShortAccessTokenAndARefreshTokenForThisDevice</code>"],
    ["Refresh", "A new pair; one unused refresh token left; the chain goes on", "<code>refreshGivesANewPairAndTheOldRefreshTokenIsUsedUp</code>"],
    ["The device list", "Active devices only, this one marked", "<code>theDeviceListShowsOnlyActiveDevicesAndMarksThisOne</code>"],
    ["Logout", "This device only", "<code>logoutEndsThisDeviceOnly</code>"],
    ["Wrong password, unknown email, bad body", "Identical <code>401</code>s; <code>400</code>", "<code>wrongLoginsAre401AndBadBodiesAre400</code>"],
    ["Unknown device, not a UUID", "<code>404</code>; <code>400</code>", "<code>anUnknownDeviceIs404AndABadIdIs400</code>"],
    ["No access token", "<code>401</code> with a Bearer challenge", "<code>noTokenIs401</code>"],
    ["A TV's token on the device endpoints", "<code>403</code>", "<code>aTvMayPlayButNotManageDevices</code>"],
    ["Another member's device", "<code>404</code>; that device stays signed in", "<code>anotherMembersDeviceIs404AndStaysSignedIn</code>"],
    ["10:20 and 10:31 old access token; 30-day-old refresh token", "Accepted, then <code>401</code>; <code>401</code>", "<code>accessTokensEndAfter10MinutesAndRefreshTokensAfter30Days</code>"],
    ["Ten refreshes with one token at once", "Exactly one <code>200</code>; the device is ended for reuse", "<code>tenParallelRefreshesWithOneTokenGiveOnePairAndEndTheDevice</code>"],
    ["Odd refresh tokens and headers", "<code>400</code> or <code>401</code>, never an error", "<code>oddRefreshTokensAre400Or401NeverAnError</code>"],
    ["Rules written by plain SQL", "Refused by named constraints", "<code>refreshTokenRulesHoldWithoutJava</code>, <code>deviceAndMemberRulesHoldWithoutJava</code>"],
    ["A rotation that fails half-way", "Rolled back: the old token still works", "<code>aRotationThatFailsHalfWayLeavesTheOldTokenUsable</code>"],
    ["A clock that moves between two reads", "Still exactly 30 days stored", "<code>aClockThatMovesBetweenReadsStillStoresA30DayToken</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Refresh tokens that never rotate, so a stolen one works for months.</p>
<ul>
<li><strong>The old store.</strong> One token per sign-in, kept as it is, never replaced. The test copies it, presses the old \"log out of all devices\", and the copy still says \"anika\". The table holds the token itself.</li>
<li><strong>Owner first.</strong> On the real API, anika's app rotates; the thief's copy is now used up. Showing it ends the device: <code>401</code> for the thief and for anika's new token, and <code>revoked_reason</code> is <code>reuse</code>.</li>
<li><strong>Thief first.</strong> The thief rotates first and gets a pair. Then anika's app sends the old token: used up, so the device ends and the thief's new token dies too.</li>
<li><strong>Remove means now.</strong> The laptop removes the phone; one second later the phone's access token is <code>401</code>, not 10 minutes later.</li>
</ul>
<p>While building, each part was undone once: a refresh token usable again (no <code>used_at</code> check) turned 3 tests red; no device end on reuse 3; no active-session check on access tokens 2; no member in the remove query 1; a TV given the devices scope 1; refresh without a transaction 2 (in the parallel test no refresh won at all: see Code).</p>
</div>
""" + code(read(T + "NeverRotatingTokenTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SecurityConfig.java", dwn("Who may call what.",
        "Login and refresh open (they check their own secrets); logout for any valid token; devices need scope <code>devices</code>; everything else refused; no session.",
        "A TV in a living room managing the account, or a new endpoint open by default.",
        "<p><code>/error</code> is open: Spring forwards a server error there, and under <code>denyAll()</code> it came back as a <code>401</code> \"Sign-in required\" that hid the real <code>500</code>. Found while building.</p><p>CSRF is off because tokens travel in a header and a JSON body, never in a cookie a browser adds by itself. A web app that kept the refresh token in a cookie would need CSRF protection back.</p>")),
    (J + "JwtConfig.java", dwn("The access-token checks, including \"is this device still signed in?\".",
        "Signature (HS256 only), expiry with 30 seconds of allowance, issuer, audience, and one indexed lookup of the device session.",
        "A removed or logged-out device keeping access for the rest of its token's 10 minutes.",
        "<p>The lookup is a trade: one primary-key query per request buys immediate sign-out. Without it, \"remove\" works only for refresh tokens, and access tokens live on until they expire.</p>")),
    (J + "DeviceController.java", dwn("The five endpoints and their input checks.",
        "One <code>401</code> for every failed login and every failed refresh; a refresh token must have the shape of ours; another member's device is a <code>404</code>.",
        "Answers that tell an attacker which tokens or devices exist.")),
    (J + "Sessions.java", dwn("Sign-in, rotation, reuse detection, the device list.",
        "The refresh token is used up by one <code>UPDATE ... WHERE used_at IS NULL ... RETURNING</code>: of parallel calls, exactly one gets the row. A used token shown again ends the device. The whole rotation is one transaction.",
        "Tokens that work twice, and a phone signed out by its own retry after a half-done rotation.",
        "<ul><li>The first run against the real app failed every sign-in: <code>created_at</code> and <code>expires_at</code> came from two clock reads, a few microseconds apart, so the token was 30 days and 1 microsecond long and <code>refresh_tokens_expiry</code> refused it. The tests had a clock that stood still. Now the clock is read once, and the test clock can move on every read. Found while building.</li><li>Without <code>@Transactional</code> on <code>refresh</code>, the parallel test found no winner at all: the first statement committed alone, a losing call then saw a used token and ended the device before the winner had finished. Found while building.</li><li>Ten parallel refreshes with one token end the device. That is the safe side of a race, and a real cost for a phone that retries after a timeout: a short grace window is the usual softening (not built here).</li><li>An unknown email still pays for one bcrypt check, so it answers as slowly as a wrong password. No test measures the timing.</li></ul>")),
    (J + "TokenService.java", "<p>The 10-minute access token: <code>sub</code> the member, <code>sid</code> the device session, <code>scope</code> from the device type.</p>"),
    (J + "ProblemResponses.java", "<p>401 (with <code>WWW-Authenticate: Bearer</code>) and 403 in the same problem JSON as every other error.</p>"),
    (M + "V1__members_devices_tokens.sql", dwn("Members, device sessions and refresh tokens, with their rules.",
        "Only hashes; at most 30 days; at most one unused refresh token per device; a revoked device always has a reason.",
        "A script storing tokens in the clear, or two live tokens on one device.")),
    (M + "V2__demo_members.sql", "<p>Two demo members with bcrypt hashes made by pgcrypto.</p>"),
    ("src/main/resources/application.yaml", "<p>Issuer, audience, lifetimes, allowance, and a demo key that real deployments take from a secret store.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "DevicesApplication.java", "<p>Entry point, and the <code>Clock</code> every time check uses.</p>"),
]
tree = """stations/074-device-sessions-for-a-streaming-app/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/streamo/devices/
│   ├── SecurityConfig.java   ├── JwtConfig.java   ├── DeviceController.java
│   ├── Sessions.java   ├── TokenService.java   ├── ProblemResponses.java
│   └── DevicesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__members_devices_tokens.sql, V2__demo_members.sql
├── src/test/java/com/streamo/devices/   (see Tests)
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
<p>Sign in, refresh twice with the same refresh token, and look at the device afterwards:</p>
""" + code("""R=$(curl -s -X POST http://localhost:8080/auth/login -H 'Content-Type: application/json' \\
  -d '{"email": "rohan@example.com", "password": "rohan-demo-pass", "deviceName": "My laptop", "deviceType": "web"}' \\
  | sed 's/.*"refreshToken":"\\([^"]*\\)".*/\\1/')
curl -s -o /dev/null -w '%{http_code}\\n' -X POST http://localhost:8080/auth/refresh -H 'Content-Type: application/json' -d "{\\"refreshToken\\": \\"$R\\"}"
curl -s -o /dev/null -w '%{http_code}\\n' -X POST http://localhost:8080/auth/refresh -H 'Content-Type: application/json' -d "{\\"refreshToken\\": \\"$R\\"}"
docker compose exec postgres psql -U streamo -d streamo -c "SELECT device_name, revoked_reason FROM device_sessions\"""", "bash") + """
<p>The first refresh prints 200, the second 401, and the laptop's row says <code>reuse</code>.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["A removed device keeps working for minutes", "Access tokens checked only by signature and expiry.", "Check the device session on each request, as <code>JwtConfig</code> does, or accept the delay."],
    ["Phones signed out after a timeout and retry", "The retry sent the already-used refresh token.", "Expected with strict reuse detection; a short grace window or an idempotent retry softens it."],
    ["Every sign-in fails with <code>refresh_tokens_expiry</code>", "Creation and expiry times from two clock reads.", "Read the clock once. Found while building this station."],
    ["A <code>401</code> \"Sign-in required\" on a public endpoint", "A server error forwarded to <code>/error</code>, which the chain refused.", "Permit <code>/error</code>, then read the real error in the log."],
    ["<code>refresh_tokens_one_live_per_session</code> violated", "A new refresh token inserted before the old one was used up.", "Mark the old one used first, in the same transaction."],
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>DeviceContractTest</code> ({cnt('DeviceContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>NeverRotatingTokenTrapTest</code> ({cnt('NeverRotatingTokenTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>DeviceDatabaseTest</code> ({cnt('DeviceDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, one user accessing another user's data, malicious input", f"<code>DeviceSecurityTest</code> ({cnt('DeviceSecurityTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">The parallel test runs ten refreshes on virtual threads released by one latch, against the real PostgreSQL. The rollback test makes the database refuse new tokens with a trigger, so the failure happens inside the real transaction.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Spring Security 7.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "NeverRotatingTokenTrapTest.java", "<p>Written first: the old store keeps a stolen token alive; the real API ends the device on reuse, whoever came first; remove means now; only hashes are stored.</p>"),
    (T + "DeviceSecurityTest.java", "<p>401, 403 for a TV, another member's device, expiry, ten parallel refreshes, odd input.</p>"),
    (T + "DeviceDatabaseTest.java", "<p>Every named constraint with plain SQL, and a rotation that fails half-way.</p>"),
    (T + "DeviceContractTest.java", "<p>Login, refresh, the device list, logout, wrong input, through HTTP.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the test clock, a test key, no devices before each test, request helpers.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/streamo/devices/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=SignOutOtherDevicesChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Sign out every other device", "Beginner-friendly", 20,
    "The button that did nothing: <code>DELETE /me/devices</code> signs out all of this member's other devices at once (<code>204</code>) and keeps this one. A TV may not use it.",
    "both tests in <code>SignOutOtherDevicesChallengeTest</code> pass.",
    ["One <code>UPDATE</code> with <code>member_id = ? AND id &lt;&gt; ?</code>: the current device is the token's <code>sid</code>.",
     "The rule <code>/me/devices</code> already needs the <code>devices</code> scope."],
    "challenge/SignOutOtherDevicesChallengeTest.java", ["challenge/solution/DeviceController.java", "challenge/solution/Sessions.java"]) + challenge(2, "At most five devices", "Go deeper", 35,
    "Demo rule: at most 5 signed-in devices per member. Signing in on a sixth signs out the one used longest ago, with <code>revoked_reason = 'limit'</code>.",
    "the test in <code>DeviceLimitChallengeTest</code> passes.",
    ["The database refuses the new reason until a V3 migration replaces <code>device_sessions_revoked_reason</code>.",
     "<code>ORDER BY last_used_at DESC OFFSET 4</code> finds the devices to sign out.",
     "Two sign-ins at the same moment could both count four: lock the member row first (<code>SELECT ... FOR UPDATE</code>)."],
    "challenge/DeviceLimitChallengeTest.java", ["challenge/solution/V3__device_limit.sql", "challenge/solution/Sessions.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Retries, and tokens tied to the device</h2>
<p>A phone on a train sends a refresh, the answer is lost, and it retries with the same token: today it is signed out. Design a grace window (how long, what the retry gets back, and why a thief inside the window is still caught later). Then read about DPoP (RFC 9449, Proposed Standard): tokens bound to a key that never leaves the device. What would a stolen copy be worth then?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: a stolen, never-changing token outlives \"log out of all devices\".</li>
<li>Store device sessions and the hashes of their refresh tokens, with the rules as constraints.</li>
<li>Rotate in one transaction: use up the old token with a conditional <code>UPDATE</code>, insert the new one.</li>
<li>End the device on reuse; check the device on every access token.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Rotation with reuse detection, device check on every request", "One lookup per request; a retry after a lost answer signs the device out.", '<span class="pill ok">Chosen</span>'],
    ["One long refresh token, never rotated", "A copy works until it expires.", '<span class="pill bad">The trap</span>'],
    ["Rotation, no device check on access tokens", "No lookup; a removed device keeps access for up to 10 minutes.", '<span class="pill warn">Valid with very short access tokens</span>'],
    ["Rotation with a grace window for retries", "Fewer accidental sign-outs; a thief inside the window gets in once.", '<span class="pill warn">Common in practice</span>'],
    ["Sender-constrained tokens (DPoP, mTLS)", "Keys on each device and proofs on each request.", '<span class="pill warn">Strongest; more moving parts</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>refresh_tokens_hash_shape</code>", "CHECK: 64 hex characters", "Only SHA-256 hashes, never the token."],
    ["<code>refresh_tokens_expiry</code>", "CHECK: after creation, at most 30 days later", "No forever tokens from any writer."],
    ["<code>refresh_tokens_one_live_per_session</code>", "Partial UNIQUE index on <code>session_id</code> where unused", "Rotation as a rule: one live token per device."],
    ["<code>device_sessions_revoked_with_reason</code>, <code>_revoked_reason</code>", "CHECKs", "Every sign-out says why: logout, removed or reuse."],
    ["<code>device_sessions_type</code>, <code>_name_length</code>", "CHECKs", "Only phone, tv and web; a name the list can show."]]) + """
<p><strong>Transaction boundary:</strong> one refresh is one transaction: use up the old token, touch the device, insert the new token. A failure anywhere leaves the old token unused, so the retry works.</p>
""" + code(read(M + "V1__members_devices_tokens.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Old rows</dt><dd>Used and expired refresh tokens pile up. Keep used ones while their session could still be attacked (here at most 30 days), then delete them in a scheduled job.</dd>
<dt>Where apps keep the token</dt><dd>Mobile apps: the platform's keychain or keystore. Browsers: an <code>HttpOnly</code>, <code>Secure</code>, <code>SameSite</code> cookie on the refresh path only, and then CSRF protection on that path.</dd>
<dt>Telling the member</dt><dd>A reuse is a sign of theft: tell the member which device was signed out, and suggest a password change.</dd>
<dt>Logs</dt><dd>Never log tokens or request bodies of the auth endpoints.</dd>
<dt>Standards</dt><dd>The OAuth 2.0 Security Best Current Practice (RFC 9700, BCP 240) asks for refresh tokens that are rotated or bound to the client; refresh tokens themselves are in RFC 6749 (Proposed Standard).</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why have two tokens?", "The access token is checked on every request without the database (or with one cheap lookup) and lives minutes. The refresh token is checked only on refresh, can be stored and revoked, and lives weeks."),
    ("What is refresh token rotation?", "Each refresh hands back a new refresh token and marks the old one used. A stolen copy goes stale at the owner's next refresh."),
    ("What do you do when a used refresh token comes back?", "Assume two holders and end the whole device session: the attacker's copy and the owner's latest token both stop; the owner signs in again."),
    ("Why store only a hash of refresh tokens?", "A leaked table or backup then opens nothing. A fast hash such as SHA-256 is enough here because the token is 256 random bits, not a guessable password."),
    ("How do you make logout immediate with JWTs?", "Check something server-side on each request, such as the device session or a revoke list, or keep access tokens so short that the delay is acceptable."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Rotation", "A new refresh token at every refresh.", "Reuse ends the device; parallel refreshes have exactly one winner."],
    ["Revocation", "Remove and logout stop refresh tokens.", "Access tokens stop at once too, and you can say what that costs."],
    ["Data", "Only hashes stored.", "Rotation enforced by a partial unique index."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("The refresh token is never replaced",
     "\"So a retry never signs a phone out\" brings the original incident back: the same refresh token works for 30 days, a copy is never noticed, and two holders can refresh forever.",
     "<code>refreshGivesANewPairAndTheOldRefreshTokenIsUsedUp</code>, <code>aStolenRefreshTokenUsedAfterTheOwnerEndsTheWholeDevice</code>, <code>theThiefRefreshingFirstIsCaughtWhenTheOwnerRefreshes</code> and <code>tenParallelRefreshesWithOneTokenGiveOnePairAndEndTheDevice</code> fail; <code>aRotationThatFailsHalfWayLeavesTheOldTokenUsable</code> fails too, because there is no rotation to fail."),
    ("No device check on access tokens",
     "\"No database call on every request\" saves one primary-key lookup, and a removed device keeps its access for up to 10 more minutes.",
     "<code>removingADeviceStopsItsAccessTokenAtOnce</code> fails."),
    ("Remove by id only",
     "\"UUIDs cannot be guessed\" is not access control: ids appear in logs, screenshots and support tickets. Any member could sign out anyone's device.",
     "<code>anotherMembersDeviceIs404AndStaysSignedIn</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate fixes \"members on trains keep getting signed out\": the refresh token now stays the same for its 30 days, so a retry is harmless. They also drop the per-request device lookup (\"tokens are signed, the database is busy\"), and simplify device removal because \"UUIDs cannot be guessed\". Read the two files and list every problem before opening the findings.</p>
<p class="path">review/Sessions.java</p>
""" + code(read("review/Sessions.java"), "java") + """
<p class="path">review/JwtConfig.java</p>
""" + code(read("review/JwtConfig.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the two flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">The complaint was real: strict rotation does sign out a phone that retries. The fix for that is a short grace window, not a token that never changes.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
