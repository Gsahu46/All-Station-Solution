"""Station 103 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 103,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring-WS 5 · JAXB classes generated from the WSDL · java.net.http client with timeouts",
    "simulation": "The insurer's SOAP service is simulated: a small server answers with SOAP envelopes written by hand (no policy is really issued). The customers and products are demo data.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker and no database: the tests start their own simulated insurer. Python 3 runs the simulated insurer in Try it yourself. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/bimaly/policies/"
T = "src/test/java/com/bimaly/policies/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("SOAP", "An older way for systems to talk: every message is an XML \"envelope\" sent by HTTP POST.", "A letter in a fixed government form.", "the insurer's IssuePolicy"),
    ("WSDL", "An XML file that describes a SOAP service: its operations, its messages and its address.", "The form's instruction booklet.", "<code>policy-issuance.wsdl</code>"),
    ("Generated client classes", "Java classes made from the WSDL at build time, so you never write the XML yourself.", "A pre-printed form you only fill in.", "<code>IssuePolicyRequest</code>, <code>PolicyFault</code>"),
    ("SOAP fault", "SOAP's error message: a code (whose mistake: Client or Server), a reason, and details.", "The form sent back with \"rejected: field 4\" stamped on it.", "422 or 502"),
    ("Timeout", "How long you wait for an answer before giving up.", "Hanging up after a minute on hold.", "connect 2 s, answer 8 s"),
    ("Circuit breaker", "After several failures in a row, stop calling for a while.", "Not redialling a number that is clearly down.", "challenge 2"),
]
STORY = [
    ("The insurer's old system", "Bimaly sells health and term insurance. Policies are issued only by the insurer's 15-year-old SOAP service. Nobody on the team had used SOAP."),
    ("A minute of waiting, then a 500", "The first client used the library's defaults. On a slow day the insurer took 40 seconds; customers waited, retried and stacked up. When the insurer said \"we do not sell that product\", the customer saw \"500 Internal Server Error\"."),
    ("The fix", "The client is generated from the WSDL, gives the insurer 8 seconds at most, and reads each fault: our mistake is a 422 with the insurer's reason, the insurer's failure is a 502, and no answer is a 504 that says the policy may or may not exist."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Every call to another system needs a time limit and an honest translation of its errors. Old systems need both most.</p>

<h2>What are we building?</h2>
<p>A JSON endpoint that issues a policy through the insurer's SOAP service, with time limits and clear errors.</p>

<h2>An everyday analogy</h2>
<p>A travel agent booking with an airline that only accepts paper forms by fax. The agent fills in the airline's form exactly, waits a fixed time for the reply, and tells the customer in plain words whether the airline refused (\"no seats in that class\") or its fax machine is broken.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Check</strong>: the request is validated before anything is sent; a bad request never reaches the insurer.</li>
<li><strong>Translate</strong>: generated classes turn it into the insurer's XML envelope.</li>
<li><strong>Send, with a limit</strong>: at most 2 s to connect and 8 s for the answer.</li>
<li><strong>Translate back</strong>: a policy is <code>201</code>; a refusal <code>422</code>; the insurer failing <code>502</code>; no answer <code>504</code>.</li>
</ol>

<details class="qa check"><summary>Check yourself: why not retry when the insurer does not answer?</summary><p>The insurer may have issued the policy and only the answer was lost. A retry could issue a second policy for the same person. The API says \"may or may not have been issued\" instead.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real insurer.</strong> A small simulated SOAP server answers.</li>
<li><strong>No database.</strong> The insurer keeps the policies; we only pass them on.</li>
<li><strong>No SOAP server of our own.</strong> We only call one.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Bimaly</strong> (a fictional insurance broker) issues policies through its insurer's SOAP service. Slow answers hold requests for a minute, and refusals reach customers as 500s.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo rules: 2 s to connect, 8 s for the whole answer (the insurer usually answers in 1 to 3 s, at worst 6 s); a name of at most 100 characters; a product code of 3 to 10 letters or digits.</p>
<ol class="gwt">
<li><b>Given</b> a valid request the insurer accepts, <b>then</b> <code>201</code> with the insurer's policy number and premium, and a <code>Location</code>.</li>
<li><b>Given</b> a request the insurer refuses (a Client fault), <b>then</b> <code>422</code> with the insurer's reason and code.</li>
<li><b>Given</b> the insurer's own failure (a Server fault) or no connection, <b>then</b> <code>502</code>.</li>
<li><b>Given</b> no answer within 8 s, <b>then</b> <code>504</code>, saying the policy may or may not have been issued.</li>
<li><b>Given</b> bad input, <b>then</b> <code>400</code>, and nothing is sent.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>The client is generated from the insurer's WSDL, not written by hand.</li>
<li>Every call has a connect timeout and an answer timeout.</li>
<li>IssuePolicy is never retried automatically: it is not idempotent.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Read a WSDL: operations, messages, faults, address.</li>
<li>Generate client classes from it with Maven.</li>
<li>Call a SOAP operation with Spring-WS and set real timeouts.</li>
<li>Map SOAP faults to honest HTTP errors.</li>
<li>Test against a simulated SOAP server, including slow and broken answers.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/policies</code>", "Issue a policy: <code>{customerName, dateOfBirth, productCode, sumInsuredPaise}</code>."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Issued by the insurer"],
    ['<span class="pill warn">400</span>', "Missing or bad fields; a date of birth not in the past"],
    ['<span class="pill warn">422</span>', "The insurer refused the request (its code in <code>insurerCode</code>)"],
    ['<span class="pill warn">502</span>', "The insurer's system failed, or could not be reached"],
    ['<span class="pill warn">504</span>', "No answer within 8 s; the policy may or may not exist"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against <code>docs/test-insurer.py</code>, a small simulated insurer. <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-a-term-policy", "Case 1: a term policy", "<b>Why:</b> <code>201</code>; the policy number comes from the insurer."),
    ("02-a-product-the-insurer-does-not-sell", "Case 2: a product the insurer does not sell", "<b>Why:</b> a Client fault: <code>422</code> with the insurer's own reason."),
    ("03-a-sum-above-the-limit", "Case 3: a sum above the insurer's limit", "<b>Why:</b> the insurer's rule, not ours: <code>422</code>."),
    ("04-a-date-of-birth-in-the-future", "Case 4: a date of birth in the future", "<b>Why:</b> <code>400</code>; nothing sent."),
    ("05-the-insurers-system-fails", "Case 5: the insurer's system fails", "<b>Why:</b> a Server fault: <code>502</code>, and no internal detail passed on."),
    ("06-the-insurer-hangs", "Case 6: the insurer hangs for 20 s", "<b>Why:</b> <code>504</code> after 8 s."),
]) + """
<p class="muted">How long case 6 took, measured by curl:</p>
""" + code(read("docs/captures/hang-timing.txt").strip(), "text") + """
<h2>On the wire</h2>
<p class="muted">What the simulated insurer received and sent back for cases 1 and 2. Note the <code>SOAPAction</code> header, and that SOAP 1.1 sends a fault with HTTP 500.</p>
""" + code(read("docs/captures/wire-issue.txt").strip(), "xml") + code(read("docs/captures/wire-fault.txt").strip(), "xml")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["The old client and a slow insurer", "60 s read timeout; still waiting after 2 s", "<code>theOldClientWaitsAsLongAsTheInsurerDoes</code>"],
    ["The old way and a refusal", "An exception escapes (a 500); the API answers <code>422</code>", "<code>theOldWayLetsAFaultEscapeAsAnErrorAndTheApiExplainsIt</code>"],
    ["A policy issued", "<code>201</code>, Location, SOAPAction sent", "<code>aPolicyIsIssuedThroughTheInsurersSoapService</code>"],
    ["A refusal", "<code>422</code> with the insurer's reason and code", "<code>theInsurersRefusalIs422WithItsReason</code>"],
    ["A Server fault; a slow insurer", "<code>502</code>; <code>504</code>", "<code>theInsurersOwnFailureIs502AndASlowInsurer504</code>"],
    ["Bad input", "<code>400</code>; the insurer gets nothing", "<code>badRequestsAre400AndNeverReachTheInsurer</code>"],
    ["No insurer listening", "<code>502</code>", "<code>anInsurerThatCannotBeReachedIs502</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">No timeout on a slow legacy service, and SOAP faults turned into 500s.</p>
<ul>
<li><strong>The old way.</strong> A <code>WebServiceTemplate</code> as it comes. Its default sender waits 60 s to connect and 60 s for an answer: the test reads the value and shows a request still waiting after 2 s. A refusal arrives as <code>SoapFaultClientException</code>; nothing catches it, so the customer gets a 500 with no reason.</li>
<li><strong>The API.</strong> Gives up after its limit (1 s in the tests) with <code>504</code>, and turns the same refusal into <code>422</code> \"The insurer refused the policy: Product CAR1 is not sold.\"</li>
</ul>
<p>While building, each part was undone once: no timeouts turned 2 tests red; no SOAPAction 1; every fault as <code>422</code> 1; the fault's detail ignored 2; every lost answer as <code>502</code> 2; the product code not upper-cased 1; no pattern on the product code 1.</p>
</div>
""" + code(read(T + "LegacySoapTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    ("src/main/resources/wsdl/policy-issuance.wsdl", dwn("The insurer's contract.", "One operation, IssuePolicy; its request, answer and fault; the address. SOAP 1.1, document/literal.", "Hand-written XML that drifts from what the insurer expects.",
        "<ul><li>Here a copy of the insurer's file, kept in the project so the build does not depend on their server.</li></ul>")),
    ("pom.xml", dwn("Generating the client.", "<code>jaxb-maven-plugin</code> reads the WSDL at build time and writes <code>com.bimaly.policies.insurer</code> into <code>target/</code>.", "Generated code checked in and forgotten when the WSDL changes.")),
    (J + "PolicyController.java", dwn("The endpoint and its errors.", "Validates, builds the generated request, and turns each outcome into one status with a plain sentence.", "A 500 for every problem on the insurer's side.")),
    (J + "InsurerClient.java", dwn("The SOAP call.", "Sends the SOAPAction; reads a fault's code (Client/Sender: our request; Server/Receiver: theirs) and its PolicyFault detail; tells a timeout from a lost connection.", "\"The insurer refused\" and \"the insurer is broken\" looking the same.",
        "<ul><li>A timeout is recognised by its cause (<code>HttpTimeoutException</code>), not by the words of its message.</li></ul>")),
    (J + "PoliciesApplication.java", dwn("The client's settings.", "<code>JdkHttpClientMessageSender</code>: connect 2 s, whole request 8 s.", "Spring-WS's default sender: 60 s and 60 s.",
        "<ul><li>Made inside a <code>@Bean</code> method, the sender must be given its <code>HttpClient</code>: it only builds one in <code>afterPropertiesSet</code>, which Spring calls for beans, and otherwise fails with \"HttpClient is not available\". Found while building.</li></ul>")),
    ("src/main/resources/application.yaml", "<p>The insurer's address and the two timeouts.</p>"),
]
tree = """stations/103-calling-a-legacy-soap-service/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/bimaly/policies/
│   ├── PolicyController.java   ├── InsurerClient.java   └── PoliciesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── wsdl/policy-issuance.wsdl
├── target/generated-sources/   com/bimaly/policies/insurer/ (made by the build)
├── src/test/java/com/bimaly/policies/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, simulated insurer, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Python 3", "Only for the simulated insurer in Try it yourself", "<code>python3 --version</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""python3 docs/test-insurer.py 9088 &   # the simulated insurer
./mvnw spring-boot:run      # generates the client from the WSDL; the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests; they start their own simulated insurer""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""Start-Process python -ArgumentList 'docs/test-insurer.py','9088'
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Make the insurer hang, then issue a policy:</p>
""" + code("""curl -d '{"delay":20}' http://127.0.0.1:9088/control
curl -i -H 'Content-Type: application/json' -d '{"customerName":"Asha Rao","dateOfBirth":"1990-06-30","productCode":"HEALTH5","sumInsuredPaise":50000000}' localhost:8080/policies""", "bash") + """
<p>The answer is <code>504</code> after 8 s. Then copy the Review tab's <code>PoliciesApplication.java</code> over the real one and try again: the request waits the full 20 s.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>cannot find symbol IssuePolicyRequest</code> in the IDE", "The classes are generated by the build.", "Run <code>./mvnw compile</code> once, and mark <code>target/generated-sources</code> as a source folder if the IDE does not."],
    ["<code>HttpClient is not available</code>", "A <code>JdkHttpClientMessageSender</code> made by hand, without an HttpClient.", "Pass one to its constructor, as in <code>PoliciesApplication</code>."],
    ["The insurer answers \"no operation\" or ignores the request", "No or wrong <code>SOAPAction</code> header.", "Send the action named in the WSDL's binding."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">The contract first, then in the order a request travels.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>PolicyContractTest</code> ({cnt('PolicyContractTest')}), <code>InsurerDownTest</code> ({cnt('InsurerDownTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>LegacySoapTrapTest</code> ({cnt('LegacySoapTrapTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">\"Not found\" here is the insurer's side: a product it does not sell (<code>422</code>) and an insurer that cannot be reached (<code>502</code>); there is no policy to look up in this station. The tests' simulated insurer answers with hand-written SOAP 1.1 envelopes, can be made slow or broken, and the API's limit is 1 s, so a hang is reached in a second.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "LegacySoapTrapTest.java", "<p>Written first: the client as it comes against the API, a slow insurer and a refusal.</p>"),
    (T + "PolicyContractTest.java", "<p>Issued, refused, failed, slow and bad requests.</p>"),
    (T + "InsurerDownTest.java", "<p>Nothing listening at the insurer's address.</p>"),
    (T + "TestInsurer.java", "<p>A simulated SOAP service: hand-written envelopes, a delay, a broken switch, the requests it received.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the insurer's address and the 1 s limit.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/bimaly/policies/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=MaskedSoapLogChallengeTest</code>.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Log the envelopes, not the customer", "Beginner-friendly", 25,
    "When the insurer refuses something, support wants to see the exact XML. Log every request, answer and fault envelope at DEBUG on the logger <code>com.bimaly.policies.SoapLog</code>, with the customer's name replaced by <code>***</code>.",
    "both tests in <code>MaskedSoapLogChallengeTest</code> pass.",
    ["A Spring-WS <code>ClientInterceptor</code> sees each message: <code>handleRequest</code>, <code>handleResponse</code>, <code>handleFault</code>.",
     "Write the message to a <code>ByteArrayOutputStream</code>, then mask the <code>customerName</code> element.",
     "Register it with <code>template.setInterceptors(...)</code>, and return <code>true</code> so the call goes on."],
    "challenge/MaskedSoapLogChallengeTest.java", ["challenge/solution/SoapLog.java", "challenge/solution/PoliciesApplication.java"]) + challenge(2, "Leave a struggling insurer alone", "Go deeper", 35,
    "When the insurer is down, every customer still waits for a timeout. After 3 failures in a row (Server faults or no answer), answer <code>503</code> \"The insurer is having trouble. Try again in a minute.\" without calling it, for <code>bimaly.insurer.cool-down</code> (1 s in the test). A refusal is an answer, so it does not count.",
    "both tests in <code>CircuitBreakerChallengeTest</code> pass.",
    ["Count failures in a row; reset the count on any answer, refusals included.",
     "Remember when the circuit opened; after the cool-down, let a call through.",
     "Many requests at once: an <code>AtomicInteger</code> and a <code>volatile</code> time are enough here."],
    "challenge/CircuitBreakerChallengeTest.java", ["challenge/solution/InsurerClient.java", "challenge/solution/PolicyController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>What happened to the 504?</h2>
<p>A customer got <code>504</code>: the policy may or may not have been issued. The insurer's WSDL has no \"look up by our reference\" operation, but its team says they could add one next quarter. Design what Bimaly does today and after: what reference you send with each IssuePolicy, where you record the attempt, who checks it and when, and what the customer is told meanwhile.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the client as it comes, against a slow and a refusing simulated insurer.</li>
<li>Generate the classes from the WSDL; call IssuePolicy with the SOAPAction.</li>
<li>Set both timeouts on the sender.</li>
<li>Map faults by code, with the insurer's detail, and lost answers by cause.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Generated classes + Spring-WS", "A build plugin; regenerate when the WSDL changes.", '<span class="pill ok">Chosen</span>'],
    ["Hand-written XML strings", "Easy to start; breaks silently on namespaces and escaping.", '<span class="pill bad">Avoid</span>'],
    ["JAX-WS (Jakarta XML Web Services) client", "Also generated from the WSDL; a second stack beside Spring.", '<span class="pill warn">Fine too</span>'],
    ["The library's default timeouts", "60 s per call, or none at all with some senders.", '<span class="pill bad">The trap</span>'],
    ["Retry IssuePolicy on a timeout", "A second policy for the same person.", '<span class="pill bad">Not without a lookup</span>']]) + """
<h2>Database design</h2>
<p>No database in this station: the insurer stores the policies, and Bimaly passes them on. Challenge 3 asks where a record of each attempt would belong.</p>
<p><strong>Transaction boundaries:</strong> none of our own. One SOAP call is one attempt at the insurer; it is never repeated automatically.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["14. Operations: metric, alert, rollback, runbook, failure drill", "15. Real-world considerations"],
               "What changes when this runs for real.") + """
<h2>Real-world considerations</h2>
<dl class="facts">
<dt>Timeouts from the insurer's figures</dt><dd>Ask the insurer for its usual and worst answer times; set the limit a little above the worst. Here: usually 1 to 3 s, at worst 6 s, limit 8 s (demo rules).</dd>
<dt>A changing WSDL</dt><dd>Keep the insurer's WSDL in the project and regenerate on purpose. A new optional field is harmless; a renamed one fails the build, which is where you want to find out.</dd>
<dt>Security</dt><dd>Real partners usually want HTTPS with client certificates, or WS-Security headers. Both are set on the message sender or as interceptors; neither is simulated here.</dd>
<dt>Logs</dt><dd>Envelopes carry personal data: log them masked (challenge 1), and never the full detail of a Server fault to the customer.</dd>
<dt>Watching it</dt><dd>Count outcomes (issued, refused, failed, timed out) and how long calls take. A rising timeout count is the first sign the insurer is struggling.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is a WSDL, and what do you do with it?", "The service's contract: operations, messages, faults and address. You generate client classes from it at build time."),
    ("What is the SOAPAction header?", "In SOAP 1.1, an HTTP header naming the operation. Many old servers route by it, so send the value the WSDL gives."),
    ("How do you map SOAP faults to HTTP?", "By the fault code: Client/Sender means our request was wrong (4xx, with the reason); Server/Receiver means theirs failed (502)."),
    ("What are Spring-WS's default timeouts?", "The default HttpURLConnection sender waits 60 s to connect and 60 s to read. Set your own on the sender."),
    ("Should you retry a timed-out call?", "Only if the operation is idempotent or you can look up what happened. Issuing a policy is neither here."),
    ("How do you test a SOAP client?", "Against a simulated SOAP server that sends real envelopes, including faults, delays and nothing at all."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["SOAP", "Generated classes; the call works.", "You can read the WSDL and the captured envelopes and explain every part."],
    ["Errors", "No 500s for the insurer's answers.", "Refusals, failures and timeouts each with an honest status and sentence."],
    ["Timeouts", "Set.", "Chosen from the insurer's figures, and proved by a test."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("The library's default timeouts",
     "\"Spring-WS's defaults are fine for a partner we trust\": the default sender waits 60 s to connect and 60 s for an answer. On a slow day each customer's request is held for up to two minutes, and the API's 8 s promise is gone.",
     "<code>theOldClientWaitsAsLongAsTheInsurerDoes</code> and <code>theInsurersOwnFailureIs502AndASlowInsurer504</code> fail."),
    ("Every fault is the insurer's problem",
     "\"A fault comes from the insurer, so it is the insurer's problem\": a Client fault says our request was wrong. Answering <code>502</code> \"try again later\" makes the customer retry a request that can never succeed, and hides the reason the insurer gave.",
     "<code>theInsurersRefusalIs422WithItsReason</code> and <code>theOldWayLetsAFaultEscapeAsAnErrorAndTheApiExplainsIt</code> fail."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate \"simplifies\" the client: \"the defaults are fine, and a fault means the insurer had a problem\". Read both files and list every problem before opening the findings.</p>
<p class="path">review/PoliciesApplication.java</p>
""" + code(read("review/PoliciesApplication.java"), "java") + """
<p class="path">review/InsurerClient.java</p>
""" + code(read("review/InsurerClient.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">On a good day, with a fast insurer and correct requests, the flawed version works. It fails on the slow day and on the first refusal.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
