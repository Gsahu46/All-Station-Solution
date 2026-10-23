"""Station 094 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 94,
    "stack": "Spring Boot 4.1.1 · Java 25 · SSRF defences · Apache HttpClient 5 with a checking DNS resolver · timeouts and size limits · Spring Security 7",
    "simulation": "The members, the news site and the \"internal metadata service\" are demo data: in the tests two small local servers stand for a public site and a cloud metadata service, and a stand-in for DNS points names at them. The secret is a made-up string.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows). The tests use the loopback addresses 127.0.0.1 and 127.0.0.2, which Linux and Windows route by default; on macOS add 127.0.0.2 first (<code>sudo ifconfig lo0 alias 127.0.0.2</code>).",
}
J = "src/main/java/com/chaupal/previews/"
T = "src/test/java/com/chaupal/previews/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Link preview", "The title, text and picture shown when a link is pasted into a post.", "The cover of a book seen through a shop window.", "<code>POST /link-previews</code>"),
    ("SSRF", "Server-side request forgery: making a server fetch an address the attacker cannot reach themselves.", "Asking the receptionist to fetch a file from the manager's locked office.", "the metadata address"),
    ("Metadata service", "An address inside cloud machines (169.254.169.254) that hands out the machine's keys.", "The key cabinet behind the counter.", "<code>169.254.169.254</code>"),
    ("Private address", "An address only reachable inside a network: 10.x, 192.168.x, 127.0.0.1...", "A room number inside the building.", "<code>AddressPolicy</code>"),
    ("DNS rebinding", "A name that answers a safe address when checked and an internal one when used.", "A visitor whose badge says \"guest\" at the door and \"staff\" inside.", "<code>rebind.example</code>"),
    ("Timeout", "The longest the server waits for a page.", "Hanging up after three rings.", "2 s to connect, 3 s to answer"),
]
STORY = [
    ("A preview of the keys", "Chaupal shows a preview when a member pastes a link. An attacker pasted http://169.254.169.254/latest/meta-data/iam/security-credentials/. The server fetched it, from inside the cloud, and the preview showed the server's access keys."),
    ("A check that looked once", "The fix looked up the name, checked the address was public, and then fetched the URL. The fetch looked the name up again. The attacker's name answered a public address to the check and an internal one to the fetch."),
    ("The fix", "The server looks every name up once, itself, refuses it if any address is internal, and connects to exactly the addresses it checked, also after redirects. It waits at most 3 seconds and reads at most 512 KB."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A server that fetches URLs for users is a door into your network. Check where each connection really goes, at the moment it goes.</p>

<h2>What are we building?</h2>
<p>Link previews for members' draft posts, fetched only from the public internet, quickly and in small amounts.</p>

<h2>An everyday analogy</h2>
<p>A receptionist who fetches documents for visitors, but only from outside the building, reads the address on the envelope themselves at the moment they leave, and gives up if it takes too long.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Check the link</strong>: http or https, a host, no user name in it.</li>
<li><strong>Look the name up once</strong>: if any address is loopback, private, link-local or similar, refuse.</li>
<li><strong>Connect to those addresses</strong>, with short timeouts; redirects go through steps 1 and 2 again.</li>
<li><strong>Read a little</strong>: HTML only, the first 512 KB, then take the title, description and image link.</li>
</ol>

<details class="qa check"><summary>Check yourself: the link is http://news.example/... and news.example has two addresses, one public and one 10.0.0.5. Fetch or not?</summary><p>Refuse. The connection could go to either address, so one internal address is enough: <code>everyWayToNameAnInternalAddressIsRefused</code> (mixed.example).</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No image fetching.</strong> The image is only linked; fetching it is challenge 2, with the same checks.</li>
<li><strong>No cache.</strong> Previews are kept in memory per member.</li>
<li><strong>No HTML parser.</strong> A few regular expressions read the title and Open Graph tags.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Chaupal</strong> (a fictional community app): a \"preview this link\" feature let an attacker read the cloud metadata service through our server.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo users: members meera and dev, and a guest; password <code>name-demo-pass</code>. Demo rules: 2 s to connect, 3 s to answer, 3 redirects, 512 KB.</p>
<ol class="gwt">
<li><b>Given</b> a public web page, <b>then</b> <code>201</code> with its title, description and an absolute image link.</li>
<li><b>Given</b> any address that is loopback, private, link-local, \"this network\", carrier-grade NAT, multicast or IPv6 unique-local, by IP, by name, among several addresses, or after a redirect, <b>then</b> <code>422</code>, without connecting.</li>
<li><b>Given</b> a name that changes its answer, <b>then</b> the address checked is the address used.</li>
<li><b>Given</b> another scheme, no host or a user name in the link, <b>then</b> <code>400</code>.</li>
<li><b>Given</b> a slow page, <b>then</b> <code>504</code> within about 3 s; a huge page, only its first 512 KB.</li>
<li><b>Given</b> another member's preview, <b>then</b> <code>404</code>; a guest, <code>403</code>; no sign-in, <code>401</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>One lookup per connection, checked and used together.</li>
<li>Limits on time, size, redirects and type.</li>
<li>No fetch of the image by the server (until challenge 2 adds it with the same checks).</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Recognise SSRF and why cloud metadata makes it serious.</li>
<li>Block address ranges, not host names.</li>
<li>Defeat DNS rebinding by pinning the checked addresses.</li>
<li>Put timeouts and size limits on every outgoing request.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/link-previews</code>", "<code>{url}</code>: fetch the page safely and keep a preview for the member."],
    ["<code>GET</code>", "<code>/link-previews/{id}</code>", "The member's own preview."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span> / <span class="pill ok">201</span>', "The preview / created"],
    ['<span class="pill warn">400</span>', "Not a link; not http or https; no host; a user name in it"],
    ['<span class="pill warn">401</span> / <span class="pill warn">403</span>', "No sign-in / a guest"],
    ['<span class="pill warn">404</span>', "No such preview for this member"],
    ['<span class="pill warn">422</span>', "A blocked address; no such host; not HTML; not 200; too many or bad redirects"],
    ['<span class="pill warn">502</span> / <span class="pill warn">504</span>', "The page could not be fetched / took more than 3 s"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. The running app uses real DNS, and every address it could reach while capturing is private: these are refusals. Successful previews are shown by the tests, against the test sites. JSON bodies are indented for reading; <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-the-cloud-metadata-address", "Case 1: the cloud metadata address", "<b>Why:</b> 169.254.169.254 is link-local: <code>422</code>."),
    ("02-the-app-itself-on-localhost", "Case 2: the app itself, on localhost", "<b>Why:</b> loopback: <code>422</code>."),
    ("03-ipv6-loopback", "Case 3: [::1]", "<b>Why:</b> IPv6 loopback: <code>422</code>."),
    ("04-a-private-network-address", "Case 4: 10.0.0.5", "<b>Why:</b> a private network: <code>422</code>."),
    ("05-a-file-link", "Case 5: file:///etc/passwd", "<b>Why:</b> only http and https: <code>400</code>."),
    ("06-a-name-that-does-not-exist", "Case 6: nosuch.invalid", "<b>Why:</b> <code>.invalid</code> never resolves: <code>422</code>."),
    ("07-a-guest", "Case 7: a guest", "<b>Why:</b> <code>403</code>: previews are for members."),
    ("08-no-sign-in", "Case 8: no sign-in", "<b>Why:</b> <code>401</code>."),
]) + """
<p class="muted">Timed by <code>docs/capture.sh</code>: """ + read("docs/captures/refusal-time.txt").strip() + """ Refused at the lookup, before any connection could wait.</p>
"""

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A public page", "Title, description, absolute image link; readable by its member", "<code>aPublicPageGivesATitleDescriptionAndImageLink</code>"],
    ["A redirect to a public page", "Followed; relative links resolve against the final page", "<code>aSafeRedirectIsFollowed</code>"],
    ["An image, a 404, an unknown host, a redirect loop, not a link", "<code>422</code> or <code>400</code> with a plain reason", "<code>whatCannotBePreviewedIsSaidPlainly</code>"],
    ["Loopback, IPv6, mapped IPv4, 0.0.0.0, metadata, private, CGNAT, ULA, a mixed name, a redirect inside", "<code>422</code>", "<code>everyWayToNameAnInternalAddressIsRefused</code>"],
    ["file:, gopher:, ftp:, no host, user info, javascript:; a redirect to file:", "<code>400</code>; <code>422</code>", "<code>onlyHttpAndHttpsToAHost</code>"],
    ["Each address rule", "Blocked or open, one by one", "<code>theAddressRulesOneByOne</code>"],
    ["No sign-in, a guest, another member's preview", "<code>401</code>, <code>403</code>, <code>404</code>", "<code>signInRulesAndAnotherMembersPreview</code>"],
    ["A page that answers after 10 s", "<code>504</code> after about 3 s", "<code>aSlowPageTimesOut</code>"],
    ["A page that never ends", "The first 512 KB, in under 2 s", "<code>aHugePageIsReadOnlyAsFarAsAPreviewNeeds</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Fetching any URL the user sends, including internal addresses.</p>
<ul>
<li><strong>The old way.</strong> <code>openStream()</code> on the internal address returns the secret.</li>
<li><strong>Check, then fetch.</strong> The test looks up <code>rebind.example</code> (a public address: \"go ahead\"), then the fetch looks it up again and gets the internal one: the secret again.</li>
<li><strong>The API.</strong> <code>metadata.internal</code> is refused. <code>rebind.example</code> is looked up once, checked, and fetched from that same public address: the news page, and exactly one lookup.</li>
</ul>
<p>While building, each part was undone once: no address check turned 2 tests red; checking only the first address 1; no link-local 2; no carrier-grade NAT 2; no IPv6 unique-local 2; no scheme check 1; user info allowed 1; no size cap 1; no cancel after the cap 1; long timeouts 1; no type check 1; any member's preview 1.</p>
</div>
""" + code(read(T + "FetchAnyUrlTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SecurityConfig.java", dwn("Who may preview.", "HTTP Basic; members create and read; guests nothing.", "Anyone using the server as a fetcher.")),
    (J + "PreviewController.java", dwn("The endpoints.", "Parses the link, hands it to <code>Previews</code>.", "Links that are not links reaching the fetcher.")),
    (J + "Previews.java", dwn("Making and keeping previews.", "Fetches the page safely, reads the title and Open Graph tags, keeps the preview for its member.", "One member reading another's drafts.", "<p>The image link is returned, never fetched by the server.</p>")),
    (J + "SafeFetcher.java", dwn("Fetching safely.",
        "Apache HttpClient with our <code>DnsResolver</code>: each name resolved once and refused if any address is blocked, then connected to exactly those addresses. Timeouts, 3 redirects, HTML only, the first 512 KB.",
        "SSRF, DNS rebinding, redirects inside, and pages that never end.",
        "<ul><li>The resolver is the only place names become addresses, so the check and the connection cannot disagree.</li><li>When more than 512 KB is coming, the request is cancelled: otherwise the client reads the rest to reuse the connection, and an endless page timed out. Found while building.</li><li>A redirect to <code>file:</code> surfaces as a protocol error; it is answered <code>422</code>.</li></ul>")),
    (J + "AddressPolicy.java", dwn("Which addresses are internal.",
        "Loopback, private, link-local, any-local, 0/8, 100.64/10, multicast, fc00::/7. A list of exceptions exists for tests only.",
        "Missing a range an attacker can use.",
        "<p>No check for IPv6 addresses wrapping IPv4 ones: Java turns <code>::ffff:127.0.0.1</code> into 127.0.0.1 itself. A first version had the check; removing it changed no test. Found while building.</p>")),
    (J + "NameLookup.java", "<p>DNS as one method, so tests can point names at local servers and make one change its answer.</p>"),
    (J + "ProblemResponses.java", "<p><code>401</code> and <code>403</code> in the same problem shape as other errors.</p>"),
    ("src/main/resources/application.yaml", "<p>The exception list, empty.</p>"),
    (J + "PreviewsApplication.java", "<p>Entry point, and real DNS.</p>"),
]
tree = """stations/094-image-previews-without-ssrf/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/chaupal/previews/
│   ├── SecurityConfig.java   ├── PreviewController.java   ├── Previews.java
│   ├── SafeFetcher.java   ├── AddressPolicy.java   ├── NameLookup.java
│   └── ProblemResponses.java   └── PreviewsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/chaupal/previews/   (see Tests; TestSites.java runs the two test servers)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""],
    ["macOS only", "The address 127.0.0.2 on the loopback interface, for the tests", "<code>sudo ifconfig lo0 alias 127.0.0.2</code>"]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Ask for a preview of the app itself, as Meera:</p>
""" + code("""curl -u meera:meera-demo-pass -H 'Content-Type: application/json' -d '{"url": "http://localhost:8080/actuator"}' http://localhost:8080/link-previews""", "bash") + """
<p>It answers <code>422</code> \"This address cannot be previewed\", as in case 2. With internet access, a public news page gives <code>201</code> and its title.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Tests fail to bind 127.0.0.2 (macOS)", "macOS routes only 127.0.0.1 by default.", "<code>sudo ifconfig lo0 alias 127.0.0.2</code>"],
    ["A huge page times out instead of stopping", "The client reads the rest of the body to reuse the connection.", "Cancel the request after reading what you need, as <code>SafeFetcher</code> does."],
    ["Every preview is refused behind a corporate proxy", "The fetcher connects directly; a proxy changes where connections go.", "Then the proxy must enforce the same rules (challenge 3)."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>PreviewContractTest</code> ({cnt('PreviewContractTest')}), <code>FetchLimitsTest</code> ({cnt('FetchLimitsTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>FetchAnyUrlTrapTest</code> ({cnt('FetchAnyUrlTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, one user accessing another user's data, malicious input", f"<code>SsrfSecurityTest</code> ({cnt('SsrfSecurityTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">The tests need a \"public\" site and an \"internal\" one on the same machine: <code>TestSites</code> runs a news site on 127.0.0.2 and a metadata service on 127.0.0.1, on the same port, and a stand-in for DNS. Only 127.0.0.2 is on the test exception list; 127.0.0.1 stays blocked, like every private address.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Apache HttpClient 5.6.4. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "FetchAnyUrlTrapTest.java", "<p>Written first: the old fetch, check-then-fetch with rebinding, and the API.</p>"),
    (T + "SsrfSecurityTest.java", "<p>Every way to name an internal address, other schemes, each rule, sign-in.</p>"),
    (T + "PreviewContractTest.java", "<p>Previews of the test news site; what cannot be previewed.</p>"),
    (T + "FetchLimitsTest.java", "<p>A slow page and an endless one.</p>"),
    (T + "TestSites.java", "<p>The two test servers and the test DNS.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the test DNS as a bean, the exception for 127.0.0.2, request helpers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/chaupal/previews/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=AllowedDomainsChallengeTest</code>.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Only some sites", "Beginner-friendly", 20,
    "<code>chaupal.previews.allowed-domains</code>, when set, limits previews to those sites and their subdomains: <code>fakenews.example</code> is not <code>news.example</code>, and an IP address is no site. The address rules still apply.",
    "the test in <code>AllowedDomainsChallengeTest</code> passes.",
    ["Compare the lower-cased host with each domain, or with <code>\".\" + domain</code> at its end.",
     "An empty list means no domain limit."],
    "challenge/AllowedDomainsChallengeTest.java", ["challenge/solution/SafeFetcher.java"]) + challenge(2, "Images through the server", "Go deeper", 35,
    "<code>GET /link-previews/{id}/image</code> serves the preview's image, fetched by the server with the same checks as the page: only <code>image/*</code>, at most 1 MB. An <code>og:image</code> pointing inside is refused.",
    "both tests in <code>ImageProxyChallengeTest</code> pass.",
    ["Make the fetcher take the accepted type and the size limit.",
     "An image link is attacker-controlled exactly like the page link."],
    "challenge/ImageProxyChallengeTest.java", ["challenge/solution/SafeFetcher.java", "challenge/solution/Previews.java", "challenge/solution/PreviewController.java", "challenge/solution/SecurityConfig.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>An egress proxy</h2>
<p>Instead of checking addresses in the app, send every outgoing fetch through a separate egress proxy that can only reach the internet (no route to private networks, metadata blocked by the network itself). What does the app still check, what moves to the network, and what do you gain when a second team also needs to fetch URLs? Add the cloud provider's own protection (for example, metadata that requires a session token).</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test with a public and an internal test server.</li>
<li>Write the address policy and test each range.</li>
<li>Put the policy in the HTTP client's DNS resolver, so every connection, redirects included, is checked where it is made.</li>
<li>Add timeouts, the size cap, the type check and the member rules.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Check in the resolver, connect to the checked addresses", "A client that lets you plug in DNS (Apache HttpClient does).", '<span class="pill ok">Chosen</span>'],
    ["Fetch anything", "The metadata service, the admin panel, everything inside.", '<span class="pill bad">The trap</span>'],
    ["Check the address, then fetch by name", "DNS rebinding; redirects unchecked.", '<span class="pill bad">The first fix</span>'],
    ["A block-list of host names", "Endless ways to write an address: IPv6, decimal, other names.", '<span class="pill bad">Review finding</span>'],
    ["An egress proxy with network rules", "Infrastructure; protects every service at once.", '<span class="pill ok">Best, with app checks (challenge 3)</span>']]) + """
<h2>Database design</h2>
<p>This station has no database: previews are kept in memory per member (a <code>shortcut:</code> comment says so). A real service would cache previews by URL with an expiry, and never cache a refusal as a preview.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Defence in depth</dt><dd>Block metadata at the cloud level too (for example, metadata that requires a session token) and give the server no network route to private ranges.</dd>
<dt>More ranges</dt><dd>NAT64 prefixes (64:ff9b::/96) and your own public addresses can also reach inside: add them where they exist.</dd>
<dt>Abuse</dt><dd>Previews make your server fetch for others: rate-limit per member, and watch for scanning patterns (many hosts, many ports).</dd>
<dt>Logs</dt><dd>Log refusals with the member and the address: they are often the first sign of an attack.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is SSRF?", "Server-side request forgery: getting a server to make requests the attacker chooses, to places only the server can reach, such as internal services and cloud metadata."),
    ("Why is a host-name block-list not enough?", "An address can be written many ways (IPv6, decimal, other names pointing at it), and redirects lead elsewhere. Check the resolved addresses, at connect time."),
    ("What is DNS rebinding?", "A name that resolves to a safe address when checked and an internal one when used. Resolve once and connect to the checked address."),
    ("Which addresses do you block?", "Loopback, private ranges, link-local (with 169.254.169.254), any-local, 0/8, carrier-grade NAT, multicast, IPv6 unique-local, and anything else that routes inside."),
    ("What limits does a server-side fetch need?", "Timeouts for connect and read, a cap on size, few redirects, an expected content type, and a rate limit per user."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Addresses", "Loopback and metadata blocked.", "Every internal range, every spelling, every address of a name."],
    ["Rebinding", "Checked before fetching.", "Checked where the connection is made, redirects included."],
    ["Limits", "A timeout.", "Connect and read timeouts, a size cap that really stops reading, type and redirect limits."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("A block-list of host names",
     "\"The internal hosts an attacker would try\": localhost, 127.0.0.1, 169.254.169.254. But [::1], 0.0.0.0, 10.0.0.5, any name that points inside, and a public page that redirects to 127.0.0.1 all pass. An attacker only needs one spelling the list does not have.",
     "<code>everyWayToNameAnInternalAddressIsRefused</code> fails."),
    ("No check where the connection is made",
     "\"The URL was checked in fetch()\": the resolver now returns whatever DNS says, so a name pointing inside (metadata.internal) is fetched, and redirects are never checked at all.",
     "<code>theApiRefusesInternalAddressesAndIsNotFooledByRebinding</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate simplifies the fetcher: the URL's host is checked against a short list of internal hosts before fetching, and the resolver stops checking, \"since the URL was already checked\". Read the file and list every problem before opening the findings.</p>
<p class="path">review/SafeFetcher.java</p>
""" + code(read("review/SafeFetcher.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">The three addresses on the list are refused, and the obvious attack in a manual test fails. Only two tests fail, but each holds many attacks: one bypass is all it takes.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
