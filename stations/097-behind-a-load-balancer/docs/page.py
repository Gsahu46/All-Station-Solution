"""Station 097 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 97,
    "stack": "Spring Boot 4.1.1 · Java 25 · Tomcat RemoteIpValve (server.forward-headers-strategy=native) · X-Forwarded-For / -Proto / -Host · trusted proxies · Tomcat timeouts · Spring Security 7 · stateless sessions",
    "simulation": "Uploads are simulated storage: each one is read to the end, counted and hashed, and the bytes are not kept. The load balancer in the captures is a small Python script (docs/test-balancer.py); the addresses are documentation ranges.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows). The tests use the loopback addresses 127.0.0.1 (the load balancer) and 127.0.0.2 (a client), which Linux and Windows route by default; on macOS add 127.0.0.2 first (<code>sudo ifconfig lo0 alias 127.0.0.2</code>).",
}
J = "src/main/java/com/mapwise/edge/"
T = "src/test/java/com/mapwise/edge/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Load balancer", "A server in front of yours that spreads requests over several copies of your app.", "A receptionist sending visitors to free counters.", "10.0.0.0/24"),
    ("X-Forwarded-For", "A header where proxies write the address of whoever sent them the request.", "A note \"from: Mrs Rao\" on a parcel the receptionist hands on.", "<code>203.0.113.9, 198.51.100.7</code>"),
    ("X-Forwarded-Proto / -Host", "Whether the client used https, and which name it typed.", "\"She came in by the front door, asking for Mapwise\".", "<code>https</code>, <code>maps.mapwise.example</code>"),
    ("Trusted proxy", "A machine whose X-Forwarded-* headers you believe: your balancer, nobody else.", "Believing the receptionist's note, not a note the visitor wrote.", "<code>internal-proxies</code>"),
    ("Timeout", "How long one side waits for the other before giving up.", "How long a counter waits for a visitor who stepped away.", "20 s, 75 s, 60 s"),
    ("Sticky session", "The balancer sending a user always to the same server because that server remembers them.", "Always the same counter, because only that clerk has your file.", "Not needed here"),
]
STORY = [
    ("One address for everyone", "Mapwise put a load balancer in front of the API. Now every request seemed to come from the balancer's address, links pointed to <code>http://10.0.0.17:8080/</code>, and big uploads timed out."),
    ("A quick fix, a new hole", "A teammate read the client's address from X-Forwarded-For. But anyone can send that header: a user at home wrote the office's address into it and opened the admin page."),
    ("The fix", "Tomcat rewrites the address, scheme and host from X-Forwarded-*, only for requests that really come from the balancer, and only from the balancer's own entry. Every hop has a timeout, and the app keeps no session."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A header is only as trustworthy as whoever wrote it. Believe X-Forwarded-For from your balancer, never from the client.</p>

<h2>What are we building?</h2>
<p>An API that knows the real client, the real scheme and the public host name behind a load balancer, without letting any client choose them.</p>

<h2>An everyday analogy</h2>
<p>A receptionist writes \"from: Mrs Rao, front door\" on each visitor's slip. The clerk believes slips the receptionist wrote, and ignores the ones visitors wrote themselves.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>The balancer adds</strong> the client's address to the end of X-Forwarded-For, and the scheme and host it was asked for.</li>
<li><strong>Tomcat checks</strong> who is talking: the balancer's address, or someone else? Anyone else: the headers are ignored.</li>
<li><strong>Tomcat reads from the right</strong>: the last entry is the one the balancer wrote; anything before it the client could have written.</li>
<li><strong>The app uses</strong> the request as rewritten: the real client for the office check, https and the public name for links.</li>
</ol>

<details class="qa check"><summary>Check yourself: the balancer receives <code>X-Forwarded-For: 203.0.113.9</code> from a client at 198.51.100.7. What does it send on, and which address is the client?</summary><p><code>203.0.113.9, 198.51.100.7</code>. The client is 198.51.100.7: the balancer wrote that one. The first entry is whatever the client typed.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real balancer.</strong> Tests send its headers from 127.0.0.1; the captures use a Python one.</li>
<li><strong>No TLS here.</strong> The balancer ends https; the app speaks http behind it.</li>
<li><strong>No real storage.</strong> Uploads are counted and hashed, not kept.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Mapwise</strong> (a fictional maps company): behind the load balancer every request seems to come from one IP, redirects point to <code>http://</code>, and uploads time out at 60 seconds.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo rules: the balancer is 10.0.0.0/24; the office is 203.0.113.0/24; uploads at most 10 MiB. Users asha and vikram, admin ops; password: the name plus <code>-demo-pass</code>.</p>
<ol class="gwt">
<li><b>Given</b> a request through the balancer, <b>then</b> the app sees the client's address, <code>https</code>, the public host and port 443.</li>
<li><b>Given</b> a client that writes its own X-Forwarded-For, <b>then</b> it is ignored (direct) or only the balancer's entry counts (through it).</li>
<li><b>Given</b> an upload, <b>then</b> <code>201</code> with <code>Location: https://maps.mapwise.example/uploads/{id}</code>; over the limit <code>413</code>.</li>
<li><b>Given</b> a client that stops sending in the middle of an upload, <b>then</b> the app answers <code>408</code> after its read timeout and stores nothing.</li>
<li><b>Given</b> <code>/admin/uploads</code>, <b>then</b> only an admin from the office: anyone else <code>403</code>, no sign-in <code>401</code>; another user's upload <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Only the balancer's addresses are trusted, not Spring Boot's default list.</li>
<li>No HTTP session: any copy of the app can answer any request.</li>
<li>Every hop has a timeout, and the app's keep-alive outlasts the balancer's idle timeout.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Configure forwarded headers in Tomcat with an explicit list of trusted proxies.</li>
<li>Explain why X-Forwarded-For is read from the right.</li>
<li>Build absolute links from the request, so they are right behind any proxy.</li>
<li>Set timeouts at each hop and say which one must be longer.</li>
<li>Test proxy behaviour on a real port from two different client addresses.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/whoami</code>", "What the app believes about this request (public)."],
    ["<code>POST</code>", "<code>/uploads</code>", "Upload a file as the raw body; <code>201</code> with its Location."],
    ["<code>GET</code>", "<code>/uploads/{id}</code>", "Your own upload."],
    ["<code>GET</code>", "<code>/admin/uploads</code>", "Every upload: admins, from the office network only."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "whoami; your upload; the admin list"],
    ['<span class="pill ok">201</span>', "Upload stored"],
    ['<span class="pill warn">401</span>', "No sign-in, or a wrong password"],
    ['<span class="pill warn">403</span>', "The admin list: not an admin, or not from the office"],
    ['<span class="pill warn">404</span>', "No such upload, or another user's"],
    ['<span class="pill warn">408</span>', "The client stopped sending before the upload was complete (answered by Tomcat)"],
    ['<span class="pill warn">413</span>', "Over 10 MiB"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from 127.0.0.2 on """ + read("docs/captures/date.txt").strip() + """, in this order. Port 8080 is the app as configured (its balancer is 10.0.0.0/24, so curl is just a client). Port 8081 is <code>docs/test-balancer.py</code>, a small Python balancer, in front of a second copy of the app that trusts it. <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-straight-to-the-app", "Case 1: straight to the app", "<b>Why:</b> the client is who connected: 127.0.0.2, plain http."),
    ("02-straight-with-a-made-up-header", "Case 2: straight, with a made-up X-Forwarded-For", "<b>Why:</b> ignored: 127.0.0.2 is not the balancer."),
    ("03-ops-pretends-to-be-in-the-office", "Case 3: the admin pretends to be in the office", "<b>Why:</b> <code>403</code>: the office check sees 127.0.0.2."),
    ("04-through-the-balancer", "Case 4: through the balancer", "<b>Why:</b> the balancer's entry is the client; https, the public name, port 443. Spring Security now knows the request is https and adds <code>Strict-Transport-Security</code>; the <code>Server</code> header is the Python balancer's."),
    ("05-through-the-balancer-with-a-made-up-header", "Case 5: through the balancer, with a made-up header", "<b>Why:</b> the balancer appended 127.0.0.2 after the made-up 203.0.113.9; Tomcat reads from the right and takes 127.0.0.2."),
    ("06-asha-uploads", "Case 6: Asha uploads", "<b>Why:</b> <code>201</code>; the Location is the public https address, not the app's own."),
    ("07-ops-from-outside-the-office", "Case 7: the admin, through the balancer, from outside the office", "<b>Why:</b> <code>403</code>."),
    ("08-no-sign-in", "Case 8: no sign-in", "<b>Why:</b> <code>401</code>."),
    ("09-vikram-reads-ashas-upload", "Case 9: Vikram reads Asha's upload", "<b>Why:</b> <code>404</code>, the same as one that does not exist."),
]) + """
<h2>A stalled upload</h2>
<p class="muted">From <code>docs/capture.sh</code>, against port 8080 and its 20 s read timeout:</p>
""" + code(read("docs/captures/stalled-upload.txt").strip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["The old way, straight or through the balancer", "The office address the client wrote", "<code>theOldWayBelievesWhateverTheClientWrites</code>"],
    ["The API, straight or through the balancer", "127.0.0.2; the balancer's entry; <code>403</code>", "<code>theApiTrustsTheHeaderOnlyFromTheBalancerAndOnlyItsLastEntry</code>"],
    ["Boot's default trusted list, a machine that is not the balancer", "Believed: <code>200</code> on /admin", "<code>withBootsDefaultListAMachineInsideTheNetworkCanBeTheOffice</code>"],
    ["A direct request", "Taken as it is", "<code>aDirectRequestIsTakenAsItIs</code>"],
    ["Through the balancer", "Client, https, public host, port 443", "<code>throughTheBalancerTheAppSeesTheClientHttpsAndThePublicName</code>"],
    ["An upload; one byte over the limit; an unknown id", "<code>201</code> with an https Location; <code>413</code>; <code>404</code>", "<code>anUploadIsCountedAndItsLocationIsThePublicHttpsAddress</code>"],
    ["An upload that stops half way", "<code>408</code> after the read timeout; nothing stored", "<code>aStalledUploadIsCutOffAndNothingIsStored</code>"],
    ["Any signed-in request", "No session cookie", "<code>noSessionCookieSoNoStickySessionsAreNeeded</code>"],
    ["No sign-in, a wrong password", "<code>401</code>", "<code>withoutASignInUploadsAre401</code>"],
    ["Admin from home; a user from the office", "<code>403</code>", "<code>theAdminListIsForAdminsInTheOfficeOnly</code>"],
    ["Another user's upload", "<code>404</code>", "<code>aUserCannotReadAnotherUsersUpload</code>"],
    ["Not an address, a look-alike name, a made-up protocol, two headers, 50 fake hops", "Never the office, never https, the balancer's entry", "<code>maliciousForwardedHeadersGiveNothingAway</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Trusting X-Forwarded-For from anyone, so clients can spoof their IP.</p>
<ul>
<li><strong>The old way.</strong> \"The first address in X-Forwarded-For is the client\": for a client that wrote <code>203.0.113.9</code> itself, straight to the app or through the balancer, that is the office.</li>
<li><strong>The API.</strong> The same requests: straight to the app the header is ignored (the client is 127.0.0.2, <code>403</code>); through the balancer the last entry, the one the balancer wrote, is the client.</li>
<li><strong>The second half.</strong> Forward headers on, but Spring Boot's default list of trusted proxies: every private and loopback range. A machine that is not the balancer, at 127.0.0.2, is trusted, and its made-up office address opens <code>/admin</code>.</li>
</ul>
<p>While building, each part was undone once: forward headers off turned 6 tests red; no office check 3; no admin check 2; any user's upload 1; a fixed <code>http://localhost:8080</code> link 1; no upload limit 1; sessions on 1. Removing the header names (<code>remote-ip-header</code>, <code>protocol-header</code>, <code>host-header</code>) turned nothing red: they were Boot's defaults, so they were deleted. A catch that turned a stalled read into our own <code>408</code> never ran (Tomcat answers 408 itself), so it was deleted too.</p>
</div>
""" + code(read(T + "SpoofedClientIpTrapTest.java"), "java") + code(read(T + "DefaultTrustedProxiesTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    ("src/main/resources/application.yaml", dwn("Where the forwarded headers are trusted, and the timeouts.",
        "<code>forward-headers-strategy: native</code>, <code>internal-proxies</code> set to the balancer's subnet only, a 20 s read timeout and a 75 s keep-alive.",
        "Any machine inside the network choosing its client address; the balancer reusing a connection the app has just closed.",
        "<ul><li>Spring Boot 4.1.1's default <code>internal-proxies</code> is every private and loopback range (from Boot's own configuration metadata): convenient, and wrong for most networks.</li><li>The header names are Boot's defaults; nothing else needs setting.</li></ul>")),
    (J + "SecurityConfig.java", dwn("Who may do what.", "HTTP Basic, no session; /admin only for admins whose <code>getRemoteAddr()</code> is in the office network.", "A client reaching /admin by writing a header.")),
    (J + "WhoAmIController.java", "<p>What the request looks like after Tomcat rewrote it.</p>"),
    (J + "UploadController.java", dwn("Uploads.", "Builds the Location from the request (<code>ServletUriComponentsBuilder</code>), so it carries https and the public host.", "Links that point at the app's internal address.")),
    (J + "Uploads.java", dwn("Reading an upload.", "8 KB at a time, counted and hashed, stopped at the limit.", "Memory that grows with the file; a stalled client holding a thread.")),
    (J + "ProblemResponses.java", "<p><code>401</code> and <code>403</code> in the problem shape.</p>"),
    (J + "EdgeApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/097-behind-a-load-balancer/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/mapwise/edge/
│   ├── SecurityConfig.java   ├── WhoAmIController.java   ├── UploadController.java
│   └── Uploads.java   ├── ProblemResponses.java   └── EdgeApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/mapwise/edge/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, the Python balancer, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Python 3", "Only for the test balancer in Try it yourself", "<code>python3 --version</code>"],
    ["macOS only", "The address 127.0.0.2 on the loopback interface, for the tests", "<code>sudo ifconfig lo0 alias 127.0.0.2</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. <code>HttpClient.Builder.localAddress</code>, which the tests use, is in Java 19 and later.</p>
<h2>Try it yourself</h2>
<p>Run a copy of the app that trusts this machine as its balancer, and the Python balancer in front of it:</p>
""" + code("""./mvnw spring-boot:run -Dspring-boot.run.arguments='--server.port=8082 --server.tomcat.remoteip.internal-proxies=127.0.0.1/32'
python3 docs/test-balancer.py 8081 8082
curl -H 'X-Forwarded-For: 203.0.113.9' http://localhost:8081/whoami""", "bash") + """
<p>The answer shows <code>127.0.0.1</code> (curl's address, appended by the balancer), <code>https</code> and <code>maps.mapwise.example</code>: your made-up address is not the client.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Every client has the balancer's address", "Forward headers are off, or the balancer is not in <code>internal-proxies</code>.", "<code>forward-headers-strategy: native</code> and the balancer's addresses."],
    ["Links start with <code>http://</code> behind an https balancer", "The balancer does not send X-Forwarded-Proto, or it is not trusted.", "Send it; trust the balancer."],
    ["Random 502s from the balancer", "The app closes idle connections before the balancer does.", "App keep-alive longer than the balancer's idle timeout."],
    ["Tests fail to bind 127.0.0.2 (macOS)", "macOS routes only 127.0.0.1 by default.", "<code>sudo ifconfig lo0 alias 127.0.0.2</code>"]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">Configuration first: most of this station is in it. Then the code, in the order a request travels.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>ProxyContractTest</code> ({cnt('ProxyContractTest')}), <code>TimeoutAndSessionTest</code> ({cnt('TimeoutAndSessionTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>SpoofedClientIpTrapTest</code> ({cnt('SpoofedClientIpTrapTest')}), <code>DefaultTrustedProxiesTrapTest</code> ({cnt('DefaultTrustedProxiesTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, one user accessing another user's data, malicious input", f"<code>ProxySecurityTest</code> ({cnt('ProxySecurityTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">These tests need a real server: the valve that reads X-Forwarded-* runs inside Tomcat, and MockMvc has no Tomcat. Each request is sent from a chosen address with <code>HttpClient.Builder.localAddress</code>: 127.0.0.1 plays the balancer, 127.0.0.2 a client. The tests use a 1 s read timeout and a 1 MiB upload limit so they run quickly.</p>
<p class="muted">Found while building: one byte over 10 MiB, the Java client saw the connection close instead of the <code>413</code>. Tomcat answers and then reads at most 2 MB more of the body before closing; a client still sending 10 MB sees the close first. With a 1 MiB limit in the tests the rest fits, and the <code>413</code> arrives.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "SpoofedClientIpTrapTest.java", "<p>Written first: the old way against the API.</p>"),
    (T + "DefaultTrustedProxiesTrapTest.java", "<p>Boot's default trusted list, shown letting a non-balancer in.</p>"),
    (T + "ProxyContractTest.java", "<p>Direct and through the balancer; uploads and their Location.</p>"),
    (T + "TimeoutAndSessionTest.java", "<p>A stalled upload on a raw socket; no session cookie.</p>"),
    (T + "ProxySecurityTest.java", "<p>401, 403, another user's upload, malicious headers.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: a real port, requests from a chosen address, the balancer's headers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/mapwise/edge/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=RequestIdChallengeTest</code>.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "One id across hops", "Beginner-friendly", 25,
    "Every answer carries <code>X-Request-Id</code>, so one request can be found in the balancer's log and the app's. Keep the balancer's id; replace one a client sent itself (it could reuse another request's id to muddle the logs); make one when there is none. Errors too.",
    "both tests in <code>RequestIdChallengeTest</code> pass.",
    ["Tomcat's valve marks requests that came through a trusted proxy: the request attribute <code>org.apache.tomcat.request.forwarded</code>.",
     "A filter that runs before Spring Security, so <code>401</code>s get an id too.",
     "The id goes into logs: allow only a short, safe set of characters."],
    "challenge/RequestIdChallengeTest.java", ["challenge/solution/RequestIdFilter.java"]) + challenge(2, "Three uploads a minute per client", "Go deeper", 35,
    "At most 3 uploads a minute from one client address (a demo rule), <code>429</code> with <code>Retry-After</code> after that. It only works because the address is real: with the old way, a client would write a new X-Forwarded-For each time.",
    "both tests in <code>UploadsPerClientChallengeTest</code> pass.",
    ["Key the window by <code>getRemoteAddr()</code>: after the valve, that is the client.",
     "A deque of times per address, trimmed to the last minute, under a lock per address."],
    "challenge/UploadsPerClientChallengeTest.java", ["challenge/solution/UploadLimiter.java", "challenge/solution/UploadController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>An upload longer than any timeout</h2>
<p>Field teams upload 2 GB survey videos over slow mobile networks: 20 minutes or more, through a balancer that cuts connections after 60 s of silence and a CDN with its own limits. Design it so no hop's timeout matters: the API hands out a short-lived signed URL, the phone uploads straight to object storage in parts it can resume, and storage tells the API when it is done. Which timeouts are left, and who owns each?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap tests: the old way, and Boot's default trusted list.</li>
<li>Turn on forward headers in Tomcat with the balancer's addresses only.</li>
<li>Build links from the request; check the office against <code>getRemoteAddr()</code>.</li>
<li>Set the timeouts and prove the read timeout with a stalled upload.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Tomcat's valve with an explicit list of trusted proxies", "One list to keep up to date when the balancer moves.", '<span class="pill ok">Chosen</span>'],
    ["Read X-Forwarded-For yourself, first entry", "Any client chooses its address.", '<span class="pill bad">The trap</span>'],
    ["The valve with Boot's default list", "Every private address is trusted: any machine inside can spoof.", '<span class="pill bad">The trap, second half</span>'],
    ["Spring's <code>ForwardedHeaderFilter</code> (strategy <code>framework</code>)", "Trusts the headers from anyone; only safe if the app cannot be reached except through the balancer.", '<span class="pill warn">Only with a closed network</span>'],
    ["The RFC 7239 <code>Forwarded</code> header", "One standard header instead of three; not every balancer sends it.", '<span class="pill warn">If your balancer does</span>'],
    ["Sticky sessions", "Uneven load; users lose their state when a server goes.", '<span class="pill bad">Avoid: stay stateless</span>']]) + """
<h2>Database design</h2>
<p>No database: uploads are kept in memory, which is exactly what would force sticky sessions with several copies of the app. In production their records go to a database and their bytes to object storage, so any copy can answer.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Timeouts at every hop</dt><dd>Client to balancer: the balancer's idle timeout (60 s is a common default). Balancer to app: the app's keep-alive must be longer than that, or the balancer reuses a connection the app just closed (a 502). The app's read timeout frees threads from stalled clients. App to anything it calls: a connect and a read timeout on every client, shorter than the request's own.</dd>
<dt>Close the side door</dt><dd>If the app can be reached without the balancer, every header check matters more. Put it in a private network or security group that only the balancer can reach.</dd>
<dt>Several layers</dt><dd>CDN, then balancer, then app: each layer appends; trust them all in <code>internal-proxies</code> or <code>trusted-proxies</code>, and nothing else.</dd>
<dt>Long uploads</dt><dd>Raise the balancer's idle timeout only for upload paths, or upload straight to object storage (challenge 3).</dd>
<dt>Logs</dt><dd>Log the rewritten client address, and the request id the balancer sends (challenge 1).</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("How does your app learn the client's IP behind a load balancer?", "From X-Forwarded-For, but only when the request comes from the balancer, and from the entry the balancer appended: read it from the right, skipping trusted proxies."),
    ("Why not the first entry?", "The client can send the header with anything in it; the balancer appends to it. The first entry is whatever the client wrote."),
    ("Why do links say http:// behind an https balancer?", "The app sees plain http from the balancer. Trust X-Forwarded-Proto from it, and build links from the request."),
    ("Which timeout must be longer, the balancer's or the app's?", "The app's keep-alive must outlast the balancer's idle timeout, or the balancer sends requests down connections the app has closed."),
    ("Why avoid sticky sessions?", "They tie a user to one server: uneven load, and lost state when it restarts. Keep state in a database or token instead."),
    ("How do you test this?", "On a real port, sending requests from two local addresses: one plays the balancer."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Trust", "Forward headers on.", "Only the balancer trusted; you can say why Boot's default is risky."],
    ["Links", "https links.", "Links built from the request, never from a Host header or a constant."],
    ["Timeouts", "A read timeout.", "Every hop's timeout, and which must be longer."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("The office check believes the client",
     "\"Behind the balancer getRemoteAddr() is the balancer\": not with forward headers on, it is the client. And the first entry of X-Forwarded-For is whatever the client wrote: a client at home sends <code>203.0.113.9</code> and is in the office. Straight to the app it works the same way.",
     "<code>theApiTrustsTheHeaderOnlyFromTheBalancerAndOnlyItsLastEntry</code> fails: the admin list answers <code>200</code> to a made-up header."),
    ("Links from the Host header",
     "<code>\"http://\" + Host</code> is the address the balancer used to reach the app, with http: <code>http://127.0.0.1:PORT/uploads/1</code> in the tests, <code>http://10.0.0.17:8080/...</code> in production. Clients that follow it go around the balancer, or fail. <code>ServletUriComponentsBuilder</code> uses the rewritten scheme, host and port.",
     "<code>anUploadIsCountedAndItsLocationIsThePublicHttpsAddress</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate \"fixes the balancer issues in code\": the office check reads the client from X-Forwarded-For, \"because behind the balancer getRemoteAddr() is the balancer\", and the upload's Location is built from the Host header the client used. Read both files and list every problem before opening the findings.</p>
<p class="path">review/SecurityConfig.java</p>
""" + code(read("review/SecurityConfig.java"), "java") + """
<p class="path">review/UploadController.java</p>
""" + code(read("review/UploadController.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">Every honest request works on the flawed version. Its problems need a client who writes a header, and a client who follows a link: both happen on the first day in production.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
