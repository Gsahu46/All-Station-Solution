"""Station 022 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 22,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · Spring Security 7 · Jackson 3 ValueSerializer · MockMvc",
    "simulation": "Two demo customers in memory. Every number is made up; the card numbers are the well-known test numbers. Sign-in is HTTP Basic with demo passwords.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tijori/profiles/"
T = "src/test/java/com/tijori/profiles/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Masking", "Showing only part of a number, enough to recognise it, never enough to use it.", "A receipt that prints XXXX XXXX XXXX 1111.", "<code>Sensitive.masked()</code>"),
    ("API response", "What the server actually sends. Logs, proxies and screenshots keep it.", "The parcel, not the label stuck on top.", "The JSON body"),
    ("Serializer", "The code that turns a Java object into JSON.", "A translator who always leaves certain words out.", "<code>MaskingSerializer</code>"),
    ("toString", "What Java prints when an object is logged.", "What gets read aloud when someone says \"what is in this?\"", "<code>Sensitive.toString()</code>"),
    ("401 / 403", "401: we do not know who you are. 403: we know, and you may not.", "No ticket; a ticket for another show.", "Wrong password; marketing role"),
    ("Enumeration", "Learning which ids exist by watching which answers differ.", "Trying door handles to see which flats are occupied.", "Another customer's profile is a plain 404"),
]
STORY = [
    ("Asha shares a screenshot with support", "The app shows XXXX XXXX 0123 for her Aadhaar. But the network log in the same bug report shows the full 12 digits: the API sent them; only the screen hid them."),
    ("The logs agree", "Every profile request logged by the gateway, and every crash report with the response attached, holds full card and Aadhaar numbers."),
    ("The fix", "Mask on the server, on the type itself: any field holding one of these values is masked in every response and every log line, with no switch to turn it off."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">If the screen hides it but the response carries it, it is not hidden.</p>

<h2>What are we building?</h2>
<p><code>GET /customers/{id}/profile</code> returns a customer's profile with every sensitive number masked, to the customer, and to support, with no exceptions.</p>

<h2>An everyday analogy</h2>
<p>A bank posts your new debit card in an envelope with a window that shows only your name. Holding the envelope up to the light must not reveal the card number either: the protection is in the envelope, not in how carefully people hold it.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Sign in</strong>: unknown callers get <code>401</code>, roles that may not read profiles <code>403</code>.</li>
<li><strong>Check ownership</strong>: a customer sees only their own profile; anything else is the same <code>404</code> as a missing one.</li>
<li><strong>Load the profile</strong>: sensitive values are held in a <code>Sensitive</code> type, never a plain string.</li>
<li><strong>Write JSON</strong>: the type's serializer writes the masked form. There is no other form to write.</li>
</ol>

<details class="qa check"><summary>Check yourself: support needs to confirm a caller's Aadhaar. Should support get the full number?</summary><p>No. Support can ask for the last four and compare, or (challenge 2) ask the server whether they match. Every person who can see a full number is another place it can leak from.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>Not encryption at rest.</strong> The numbers sit in memory in full; storing them safely is a separate concern.</li>
<li><strong>Not real sign-in.</strong> HTTP Basic with demo users.</li>
<li><strong>Not legal advice.</strong> Card and Aadhaar rules are summarised; check the current versions.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tijori</strong> (a fictional fintech app) masks card and Aadhaar numbers in its app's screens, but its profile API returns them in full. They appear in gateway logs, crash reports and the network tab of every bug report. Support tooling has a "show full" switch nobody remembers adding.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a customer reading their own profile, <b>then</b> Aadhaar shows as <code>XXXX XXXX 0123</code>, cards as <code>XXXX XXXX XXXX 1111</code>, account and mobile with only the last 4, email as <code>a***@example.com</code>.</li>
<li><b>Given</b> any response, <b>then</b> no full number from the data appears anywhere in it, and no run of five digits.</li>
<li><b>Given</b> support, <b>then</b> any profile, masked exactly the same; <code>?full=true</code> or any other parameter changes nothing.</li>
<li><b>Given</b> one customer asking for another's profile, <b>then</b> the same <code>404</code> as for an id that does not exist.</li>
<li><b>Given</b> no or wrong credentials, <b>then</b> <code>401</code>; a marketing user, <code>403</code>.</li>
<li><b>Given</b> a profile written to a log, <b>then</b> it is masked there too.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Sensitive values have their own type; its serializer and <code>toString</code> both mask.</li>
<li>Values shorter than 8 characters show no digits at all.</li>
<li>Error responses never repeat the requested id in their detail.</li>
<li>No CVV is stored: card rules forbid keeping it after authorisation.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Write a Jackson 3 <code>ValueSerializer</code> and attach it to a type.</li>
<li>Mask per field with rules that match each kind of number.</li>
<li>Prove masking with tests that search the whole response, for every role.</li>
<li>Answer 401, 403 and "not yours" without leaking which ids exist.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/customers/{id}/profile</code>", "The profile, masked. Customers: their own; support: any."]]) + """
<h2>Demo users</h2>
""" + table(["User", "Password", "Role", "Profiles"], [
    ["asha", "asha-demo-pass", "CUSTOMER", "c-1001 only"],
    ["ravi", "ravi-demo-pass", "CUSTOMER", "c-1002 only"],
    ["neha", "neha-demo-pass", "SUPPORT", "Any, masked"],
    ["kiran", "kiran-demo-pass", "MARKETING", "None (403)"]]) + """
<h2>Masking rules</h2>
""" + table(["Field", "Shown as"], [
    ["<code>aadhaar</code>", "<code>XXXX XXXX 0123</code>"],
    ["<code>cards[].number</code>", "<code>XXXX XXXX XXXX 1111</code> (network and expiry shown)"],
    ["<code>bankAccount</code>, <code>mobile</code>", "X for every digit but the last 4"],
    ["<code>email</code>", "First letter, <code>***</code>, the domain"]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "Your profile, or any profile for support"],
    ['<span class="pill warn">401</span>', "No credentials or a wrong password"],
    ['<span class="pill warn">403</span>', "A role that may not read profiles"],
    ['<span class="pill warn">404</span>', "No such profile, or not yours (the same answer)"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. <code>-u</code> is shown as the <code>Authorization</code> header curl sends. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-own-profile", "Case 1: Asha reads her own profile", "<b>Why:</b> every number masked by its own rule; name, network and expiry shown."),
    ("02-support-view", "Case 2: support reads Ravi's profile", "<b>Why:</b> support may read any profile, and sees exactly what the customer sees."),
    ("03-support-asks-for-full", "Case 3: support adds ?full=true", "<b>Why:</b> there is no unmasked form to switch to. The parameter is ignored."),
    ("04-someone-elses-profile", "Case 4: Asha asks for Ravi's profile", "<b>Why:</b> the same 404 as a missing id, so nobody can find out which ids exist."),
    ("05-no-credentials", "Case 5: no credentials", "<b>Why:</b> <code>401</code> with a <code>WWW-Authenticate</code> header."),
    ("06-marketing", "Case 6: a marketing user", "<b>Why:</b> signed in, but the role may not read profiles: <code>403</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Own profile", "Every field masked by its rule", "<code>aCustomerSeesTheirOwnProfileMaskedFieldByField</code>"],
    ["Unknown id (support)", "<code>404</code>", "<code>aProfileThatDoesNotExistIs404</code>"],
    ["No credentials; wrong password", "<code>401</code>", "<code>noCredentialsOrAWrongPasswordIs401</code>"],
    ["Marketing user", "<code>403</code>", "<code>marketingCannotReadProfilesAtAll</code>"],
    ["Asha asks for Ravi's profile", "<code>404</code>, identical to a missing id", "<code>aCustomerCannotReadAnotherCustomersProfileAndCannotTellItExists</code>"],
    ["Support, both profiles", "Masked, no full number", "<code>supportSeesAnyProfileButStillMasked</code>"],
    ["?full, ?unmasked, ?raw, ?debug, X-Debug", "Still masked", "<code>noParameterOrHeaderUnmasks</code>"],
    ["Script and SQL-looking ids", "<code>404</code> with a fixed detail", "<code>maliciousIdsAreNotFoundAndTheDetailNeverEchoesThem</code>"],
    ["Encoded slashes, a null byte", "<code>400</code> from the firewall", "<code>pathTricksAreStoppedByTheFirewallBeforeAnyController</code>"],
    ["Short or odd values", "No digits shown", "<code>tooShortOrOddValuesShowNothing</code>"],
    ["A card in a log line", "Masked", "<code>toStringIsMaskedSoLogsAreToo</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Masking in the UI only; the full number is still in the API response.</p>
<p>The first test serialises the old profile, plain strings, and finds the full Aadhaar and card numbers in the JSON and in its <code>toString</code>. The second searches the real response for every full number in the data, and for any run of five digits: none. The third shows a plain <code>JsonMapper</code>, not Spring's, masking too, because the rule is on the type.</p>
</div>
""" + code(read(T + "FullNumberTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SecurityConfig.java", dwn("HTTP Basic, four demo users, and which roles may read profiles.",
        "Role checks at the door; ownership checks in the controller, where the id is known.",
        "Every signed-in user reads every profile.")),
    (J + "ProfileController.java", dwn("Checks ownership and returns the profile.",
        "Someone else's profile is the same 404 as a missing one; there is no \"full\" switch.",
        "<code>?full=true</code> for support; a 403 that confirms the id exists.")),
    (J + "Sensitive.java", dwn("The type for numbers that must never leave in full, with its masking rules and serializer.",
        "<code>@JsonSerialize</code> on the type: every field, every mapper, every log line masks.",
        "The trap: plain strings, masked only on screen.",
        "<ul><li>One <code>switch</code> over <code>Kind</code> holds every rule.</li><li><code>toString()</code> is overridden, because logs print it.</li><li>Under 8 characters, no digits are shown at all.</li></ul>")),
    (J + "Customers.java", "<p>Two made-up customers, and which demo user is which customer. No CVV anywhere.</p>"),
    (J + "ProblemResponses.java", "<p>401 and 403 written as problem JSON, since they happen before any controller.</p>"),
    ("src/main/resources/application.yaml", "<p>Problem bodies for every error.</p>"),
    (J + "ProfilesApplication.java", "<p>Standard Spring Boot entry point.</p>"),
]
tree = """stations/022-masking-card-and-aadhaar-numbers-in-responses/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tijori/profiles/
│   ├── SecurityConfig.java   ├── ProfileController.java   ├── Sensitive.java
│   ├── Customers.java        ├── ProblemResponses.java    └── ProfilesApplication.java
├── src/test/java/com/tijori/profiles/   (see Tests)
├── review/                   The flawed version for the Review tab
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""],
    ["Docker", "Not needed for this station", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
""" + code("""# Your own profile, masked
curl -u asha:asha-demo-pass http://localhost:8080/customers/c-1001/profile

# Someone else's: 404
curl -i -u asha:asha-demo-pass http://localhost:8080/customers/c-1002/profile""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>401</code>", "Wrong user or password.", "Use a demo user from the API contract."],
    ["<code>404</code> for an id you can see in the data", "It is not your profile.", "Sign in as its owner, or as support."],
    ["<code>release version 25 not supported</code>", "Maven is using an older JDK.", "Point <code>JAVA_HOME</code> at JDK 25, or add <code>-Djava.version=21</code>."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>ProfileContractTest</code> ({cnt('ProfileContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>FullNumberTrapTest</code> ({cnt('FullNumberTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, one user reading another's data, malicious input", f"<code>ProfileSecurityTest</code> ({cnt('ProfileSecurityTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Each masking rule and toString", f"<code>MaskingTest</code> ({cnt('MaskingTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "FullNumberTrapTest.java", "<p>Written first: the old profile's full numbers, the real response searched for them, and a plain mapper masking.</p>"),
    (T + "ProfileSecurityTest.java", "<p>401, 403, someone else's profile, support, unmask attempts, malicious ids and the firewall.</p>"),
    (T + "ProfileContractTest.java", "<p>The masked profile field by field, and a missing profile.</p>"),
    (T + "MaskingTest.java", "<p>Each rule, odd values, and <code>toString</code>.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: MockMvc, sign-in as a demo user, and every full number in the data.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tijori/profiles/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=PanChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Add a PAN", "Beginner-friendly", 15,
    "Profiles gain a PAN (made up: ABCDE1234F for Asha). Show it as <code>XXXXXX234F</code>.",
    "the test in <code>PanChallengeTest</code> passes, and no response contains the full PAN.",
    ["One more <code>Kind</code>, one more <code>case</code>: the serializer and <code>toString</code> follow on their own.",
     "Add the field to <code>Profile</code> as <code>Sensitive</code>, never as a <code>String</code>."],
    "challenge/PanChallengeTest.java", ["challenge/solution/Sensitive.java", "challenge/solution/Customers.java"]) + challenge(2, "Verify without revealing", "Go deeper", 30,
    "Add <code>POST /customers/{id}/aadhaar-checks</code> with <code>{\"last4\": \"0123\"}</code>, for support only. It answers <code>{\"match\": true|false}</code> and never shows the number. Only exactly 4 digits are accepted.",
    "both tests in <code>VerifyWithoutRevealingChallengeTest</code> pass.",
    ["Compare inside <code>Sensitive</code>, so the raw value never leaves the type.",
     "<code>MessageDigest.isEqual</code> compares in the same time whether it matches or not.",
     "Restrict the path to SUPPORT in <code>SecurityConfig</code>."],
    "challenge/VerifyWithoutRevealingChallengeTest.java", ["challenge/solution/Sensitive.java", "challenge/solution/ProfileController.java", "challenge/solution/SecurityConfig.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Who may ever see a full number?</h2>
<p>The bank's card team says a dispute process needs the full card number once a year. Design it: who asks, who approves, what is logged, where the number is shown, and for how long. Would you build it into this API at all?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old profile's JSON and <code>toString</code> both carry the full numbers.</li>
<li>Introduce <code>Sensitive</code> with its rules, serializer and <code>toString</code>; test each rule.</li>
<li>Change every sensitive field to <code>Sensitive</code>; search the whole response in tests, for every role.</li>
<li>Add sign-in, roles and the ownership check, with answers that do not reveal which ids exist.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["A type with its own serializer and toString", "Wrapping values in a type.", '<span class="pill ok">Chosen</span>'],
    ["Masking in the UI", "The response still carries everything.", '<span class="pill bad">The trap</span>'],
    ["<code>@JsonSerialize</code> on each field", "Works until someone adds a field and forgets.", '<span class="pill warn">Fragile</span>'],
    ["A response DTO that copies masked strings", "Safe for responses; logs of the domain object still leak.", '<span class="pill warn">Half the job</span>'],
    ["A filter that regex-masks every response", "Guesses what is a number; misses some, breaks others.", '<span class="pill bad">Avoid</span>']]) + """
<h2>Database design</h2>
<p>None in this station. With a database: card numbers are not stored at all (a token from the card network instead), and Aadhaar numbers only where the law allows, encrypted, in a separate store. The profile table keeps the last 4 digits for display.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Cards</dt><dd>PCI DSS, the card industry's security standard, limits what may be displayed (at most the first few and the last four digits) and forbids keeping the CVV after authorisation. Most apps should never see a card number at all: card networks issue tokens.</dd>
<dt>Aadhaar</dt><dd>UIDAI's masked Aadhaar shows only the last four digits. Organisations that keep Aadhaar numbers face strict storage rules; check UIDAI's current regulations before storing any.</dd>
<dt>Logs</dt><dd>A masked <code>toString</code> protects the common case. Request and response body logging must still be off for these endpoints.</dd>
<dt>Tests</dt><dd>Search the whole response for every raw value, for every role. A test that checks one field misses the next one someone adds.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why is masking in the UI not enough?", "The UI is one reader of the response. Logs, proxies, browser network tabs, crash reports and other clients all see the raw response."),
    ("Where would you put masking in Spring?", "On the type: a value class whose JSON serializer writes the masked form and whose toString masks too. Then every field of that type is masked everywhere, by default."),
    ("How do you write a Jackson 3 serializer?", "Extend tools.jackson.databind.ValueSerializer<T> and override serialize(value, JsonGenerator, SerializationContext). Attach it with @JsonSerialize(using = ...) or a module."),
    ("401 or 403 or 404 for someone else's data?", "401 if we do not know who you are, 403 if your role may not do this at all, and 404 for a specific item that is not yours, so the response does not confirm it exists."),
    ("How do you test that masking holds?", "Search the whole body for every raw value in the test data, for each role and parameter, and check toString as well."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You found all four flaws in the Review tab before opening them."],
    ["Masking", "Every sensitive field masked by type.", "You can say why toString matters."],
    ["Access", "401, 403 and not-yours behave as specified.", "You can explain enumeration."],
    ["Explanation", "Why server-side masking.", "Who, if anyone, should see a full number."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("The Aadhaar mask keeps the first four digits", "\"Support can match it\" sounds helpful, but the masked Aadhaar standard shows the last four; the first four plus the last four that other systems show is two-thirds of the number.", "<code>aCustomerSeesTheirOwnProfileMaskedFieldByField</code>: got <code>XXXX XXXX 3456</code>; also <code>eachKindShowsOnlyWhatItMay</code> and <code>theRealResponseIsMaskedBeforeItLeavesTheServer</code>."),
    ("<code>toString()</code> removed \"for debugging\"", "The record's default <code>toString</code> prints the raw value, so every log line with a profile or card now holds the full number.", "<code>toStringIsMaskedSoLogsAreToo</code>, and <code>anyMapperMasksBecauseTheRuleIsOnTheType</code> fails with it."),
    ("Support gets <code>?full=true</code>", "A convenience for KYC calls that turns a support login into a full-number export, and puts those numbers into every log of that request.", "<code>noParameterOrHeaderUnmasks</code>: <code>[full]</code> returned the raw Aadhaar."),
    ("The ownership check is gone", "\"The app only shows your own id\": but anyone can call the API with any id. Asha reads Ravi's profile.", "<code>aCustomerCannotReadAnotherCustomersProfileAndCannotTellItExists</code>: got 200."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate made support's life easier: the Aadhaar mask "keeps the useful digits", <code>toString</code> is "readable again", support can ask for full numbers during KYC calls, and a "redundant" ownership check is gone. The happy-path tests pass. Read both files and list every problem before opening the findings.</p>
<p class="path">review/Sensitive.java</p>
""" + code(read("review/Sensitive.java"), "java") + """
<p class="path">review/ProfileController.java</p>
""" + code(read("review/ProfileController.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the two flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">Each change was made for a person: support, a developer debugging, a product shortcut. The tests catch them because they ask what a log, an attacker or another customer would see.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
