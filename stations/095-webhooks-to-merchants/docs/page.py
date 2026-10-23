"""Station 095 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 95,
    "stack": "Spring Boot 4.1.1 · Java 25 · @Scheduled · transactional outbox · HMAC-SHA256 (Standard Webhooks format) · exponential backoff · FOR UPDATE SKIP LOCKED · java.net.http · Spring Security 7 · PostgreSQL 17 · Testcontainers · Awaitility",
    "simulation": "Payments are simulated: a test event records that a payment was captured; no payment exists and no money moves. The merchants and their servers are demo ones (a Python script in the captures, small Java servers in the tests).",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/paysetu/webhooks/"
T = "src/test/java/com/paysetu/webhooks/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Webhook", "An HTTP request we send to the merchant's server when something happens.", "A courier ringing your bell instead of you phoning to ask.", "<code>payment.captured</code>"),
    ("Outbox", "A table of messages still to send, written together with the change they announce.", "Letters in the out tray, written while the deal is signed.", "<code>deliveries</code>"),
    ("Signature", "A code only someone with the shared secret can make, sent with the request.", "A seal on an envelope.", "<code>webhook-signature: v1,...</code>"),
    ("HMAC-SHA256", "The way the signature is made: a hash of the message mixed with the secret.", "A seal stamped with a ring only two people own.", "<code>WebhookSignature.sign</code>"),
    ("Exponential backoff", "Waiting longer after each failure: 30 s, 1 min, 2 min, ...", "Calling a busy shop again later, and later still.", "<code>Dispatcher.backoff</code>"),
    ("Dead letter", "A message we stop trying, kept for a person to look at.", "A parcel back at the depot after eight failed doorsteps.", "<code>status FAILED</code>"),
]
STORY = [
    ("Down for five minutes", "Ravi's shop server restarts for an update. In those five minutes three customers pay. Paysetu posts each \"payment captured\" once, gets a 503, and moves on."),
    ("Orders that never ship", "Ravi's system never hears about the three payments, so the orders stay unpaid. The customers call; Ravi calls Paysetu. And because nothing was signed, a fake \"paid\" sent by anyone would have shipped goods for free."),
    ("The fix", "Each payment is written with a delivery for each of Ravi's servers, in one transaction. A dispatcher sends them signed, waits longer after each failure, logs every try, and after eight failures keeps the delivery as failed for a person to see."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A notification you send once is a notification you lose. Write it down first, sign it, retry it, and keep the record.</p>

<h2>What are we building?</h2>
<p>Merchants register a URL and get a secret. Every captured payment is delivered to each URL, signed, retried with growing waits, and listed in a delivery log the merchant can read.</p>

<h2>An everyday analogy</h2>
<p>A courier service: each parcel is booked before it leaves, sealed, tried again tomorrow and the day after when nobody is home, and after the last try it waits at the depot. The tracking page shows every doorstep visit.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Register</strong>: the merchant gives a URL and gets a signing secret, shown once.</li>
<li><strong>Record</strong>: a captured payment writes an event and one delivery per URL in one transaction.</li>
<li><strong>Send</strong>: every second a dispatcher takes what is due, signs it and posts it. 2xx means delivered.</li>
<li><strong>Retry or stop</strong>: after a failure it waits 30 s, then twice as long each time; the 8th failure is final.</li>
</ol>

<details class="qa check"><summary>Check yourself: the merchant's server took the request, saved the payment, then crashed before answering. What happens?</summary><p>We see no 2xx, so we retry, and the merchant gets the same payment twice. That is why every retry carries the same <code>webhook-id</code>: the merchant drops repeats by it. Webhooks are delivered at least once, not exactly once.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real payments.</strong> A test event stands in for a captured payment.</li>
<li><strong>No checks of where a URL points.</strong> A merchant could register an internal address; see Production.</li>
<li><strong>No ordering.</strong> A retry can arrive after a newer event.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Paysetu</strong> (a fictional payments company): merchants miss payment notifications when their server is down for five minutes, and cannot tell a real notification from a forged one.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo users: ravi (merchant 1) and meena (merchant 2); password: the name plus <code>-demo-pass</code>. Demo rules: first retry after 30 s, doubled each time, 8 attempts (about an hour); 5 s per attempt; signatures older than 5 minutes refused.</p>
<ol class="gwt">
<li><b>Given</b> a valid URL, <b>then</b> <code>201</code> with a <code>whsec_</code> secret, shown only here; the same URL again <code>409</code>.</li>
<li><b>Given</b> a captured payment, <b>then</b> <code>202</code> and, within a second, a POST to each URL with <code>webhook-id</code>, <code>webhook-timestamp</code> and a valid <code>webhook-signature</code>.</li>
<li><b>Given</b> the merchant down for five minutes, <b>then</b> the payment arrives on the first try after it is back (7.5 minutes in), with the same id.</li>
<li><b>Given</b> eight failures, <b>then</b> the delivery is <code>FAILED</code> and not tried again; the log shows all eight.</li>
<li><b>Given</b> the same payment reported twice, <b>then</b> one event and one delivery per URL; with another amount <code>409</code>.</li>
<li><b>Given</b> another merchant's id or delivery, <b>then</b> <code>403</code> or <code>404</code>; no sign-in <code>401</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Nothing is sent inside the request that records the payment.</li>
<li>Two servers running the dispatcher never send the same delivery at the same time.</li>
<li>The attempt limit, the states and the one-delivery-per-endpoint rule are also database constraints.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Write an event and its deliveries atomically (a transactional outbox) and send them from a <code>@Scheduled</code> job.</li>
<li>Sign requests with HMAC-SHA256 and verify them in constant time with a timestamp tolerance.</li>
<li>Retry with exponential backoff and stop with a dead letter.</li>
<li>Claim work from a table safely with <code>FOR UPDATE SKIP LOCKED</code> and a lease.</li>
<li>Test time-based behaviour with a clock you move, not with sleeps.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/merchants/{id}/webhook-endpoints</code>", "Register a URL; the answer has the signing secret."],
    ["<code>POST</code>", "<code>/merchants/{id}/test-events</code>", "Demo helper: record a captured payment (like a dashboard's \"send test webhook\")."],
    ["<code>GET</code>", "<code>/webhook-deliveries?status=PENDING|DELIVERED|FAILED</code>", "The merchant's deliveries, newest first (at most 100)."],
    ["<code>GET</code>", "<code>/webhook-deliveries/{id}</code>", "One delivery and every attempt."]]) + """
<h2>What the merchant receives</h2>
""" + table(["Header", "Value"], [
    ["<code>webhook-id</code>", "The event id: the same on every retry, so the merchant can drop repeats."],
    ["<code>webhook-timestamp</code>", "Seconds since 1970 when this attempt was signed."],
    ["<code>webhook-signature</code>", "<code>v1,</code> + Base64 of HMAC-SHA256(secret, <code>id.timestamp.body</code>)."]]) + """
<p class="muted">The format of <a href="https://www.standardwebhooks.com/">Standard Webhooks</a>, a community specification (not an IETF or W3C standard).</p>
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Endpoint registered"],
    ['<span class="pill ok">202</span>', "Payment recorded; deliveries will be sent"],
    ['<span class="pill ok">200</span>', "The same payment again (the first event), or a read"],
    ['<span class="pill warn">400</span>', "Not an http(s) URL with a host; a user name or #fragment; a bad payment ref or amount; an unknown status"],
    ['<span class="pill warn">401</span>', "No sign-in, or a wrong password"],
    ['<span class="pill warn">403</span>', "Another merchant's id in the path"],
    ['<span class="pill warn">404</span>', "No such delivery, or another merchant's"],
    ['<span class="pill warn">409</span>', "The URL is already registered; the payment was reported with another amount"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. Ravi's first server is <code>docs/test-merchant.py</code>, a Python script that checks every signature itself and answers 503 to its first request; nothing listens at his second URL. <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-ravi-registers-his-server", "Case 1: Ravi registers his server", "<b>Why:</b> <code>201</code>; the secret is shown this once."),
    ("02-a-second-server-that-is-off", "Case 2: a second URL", "<b>Why:</b> nothing listens there: its delivery will fail."),
    ("03-the-same-url-again", "Case 3: the same URL again", "<b>Why:</b> <code>409</code> (<code>endpoints_url_once_per_merchant</code>)."),
    ("04-not-a-web-address", "Case 4: a file path", "<b>Why:</b> <code>400</code>."),
    ("05-a-payment-is-captured", "Case 5: a payment is captured", "<b>Why:</b> <code>202</code>: one delivery per URL, sent by the dispatcher, not by this request."),
    ("06-reported-again", "Case 6: the same payment again", "<b>Why:</b> <code>200</code>, the same event: nothing new is sent."),
    ("07-again-with-another-amount", "Case 7: the same payment, another amount", "<b>Why:</b> <code>409</code>: that is a bug in the caller, not a repeat."),
    ("08-meena-on-ravis-merchant", "Case 8: Meena points Ravi's payments at her URL", "<b>Why:</b> <code>403</code>."),
    ("09-no-sign-in", "Case 9: no sign-in", "<b>Why:</b> <code>401</code>."),
    ("10-right-after", "Case 10: the log 3 s later", "<b>Why:</b> both deliveries tried once: 503 and no connection; the next tries are 30 s after the first."),
    ("11-delivered-after-the-retry", "Case 11: about 30 s later", "<b>Why:</b> the retry was answered 200."),
    ("12-the-delivery-log", "Case 12: one delivery and its attempts", "<b>Why:</b> what a merchant's support team reads."),
    ("13-the-server-that-is-off", "Case 13: the URL that is off", "<b>Why:</b> still pending, waiting longer each time."),
    ("14-meena-reads-ravis-delivery", "Case 14: Meena reads Ravi's delivery", "<b>Why:</b> <code>404</code>, the same as one that does not exist."),
    ("15-not-a-status", "Case 15: ?status=LOST", "<b>Why:</b> <code>400</code>."),
]) + """
<h2>What Ravi's server saw</h2>
<p class="muted">Printed by <code>docs/test-merchant.py</code>, which recomputes each HMAC in Python: an independent check of the Java signing.</p>
""" + code(read("docs/captures/merchant-server.txt").rstrip(), "text") + """
<h2>The attempts table afterwards</h2>
""" + code(read("docs/captures/attempts.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["The old way, merchant down", "One unsigned try, nothing to retry from", "<code>theOldWayLosesThePaymentWhileTheMerchantIsDown</code>"],
    ["The merchant down for five minutes", "Tries at 0, 30, 90, 210, 450 s; the fifth delivered; one id", "<code>theApiKeepsThePaymentUntilTheMerchantIsBack</code>"],
    ["Register; the same URL; bad URLs; another merchant, same URL", "<code>201</code>, <code>409</code>, <code>400</code>, <code>201</code>", "<code>anEndpointIsRegisteredWithASecretShownOnce</code>"],
    ["Headers, body and signature", "Exactly as specified; nothing sent inside the request", "<code>aPaymentIsSentSignedTheStandardWebhooksWay</code>"],
    ["Two URLs, one up, one down", "The log by status, every attempt", "<code>theDeliveryLogListsByStatusAndShowsEveryAttempt</code>"],
    ["Always 500", "Waits 30 s doubled; 8th failure final; never again", "<code>theWaitDoublesAfterEachFailureAndTheEighthFailureIsFinal</code>"],
    ["Too slow, a redirect, nobody listening", "A failed attempt each; the redirect not followed", "<code>aSlowMerchantARedirectOrNoServerIsAFailedAttempt</code>"],
    ["Two dispatcher rounds at once", "Each delivery sent once", "<code>twoServersDispatchingAtOnceSendEachDeliveryOnce</code>"],
    ["A delivery another round has locked", "Skipped, not waited for", "<code>aDeliveryAnotherRoundIsClaimingIsSkippedNotWaitedFor</code>"],
    ["The same payment twice; another amount", "One event, one send; <code>409</code>", "<code>theSamePaymentReportedTwiceIsOneEventAndOneDelivery</code>"],
    ["No sign-in, another merchant's id", "<code>401</code>, <code>403</code>, nothing stored", "<code>withoutASignInIt401sAndAnotherMerchantsWebhooksAre403</code>"],
    ["Another merchant's deliveries", "Not listed; <code>404</code>", "<code>aMerchantSeesOnlyTheirOwnDeliveries</code>"],
    ["file:, javascript:, user names, CRLF, SQL in refs", "<code>400</code>, nothing stored", "<code>maliciousInputIsRefused</code>"],
    ["Tampered, other secret, replayed later", "Verification fails", "<code>aForgedTamperedOrReplayedRequestFailsVerification</code>"],
    ["Rules written by plain SQL", "Refused by named constraints", "<code>deliveryRulesHoldWithoutJava</code>"],
    ["Deliveries cannot be written", "No event either", "<code>anEventWhoseDeliveriesCannotBeWrittenIsNotRecordedEither</code>"],
    ["The real schedule and clock", "Sent without anyone calling the dispatcher", "<code>theScheduledDispatcherSendsWithoutBeingAsked</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Fire-and-forget delivery with no signature, retry or delivery log.</p>
<ul>
<li><strong>The old way.</strong> The test posts the payment once with <code>sendAsync</code> and never reads the answer. The merchant answers 503; ten minutes later it is back, and nothing comes: there is no record to retry from. The request had no signature, so a forged one would look the same.</li>
<li><strong>The API.</strong> The merchant is down for the first five minutes. Tries at 0 s, 30 s, 90 s, 210 s and 450 s; the fifth is answered 200. Every try is signed afresh and carries the same id.</li>
</ul>
<p>While building, each part was undone once: a fixed 30 s wait turned 2 tests red; no attempt limit 1; no signature header 3; a new id on each try 2; following redirects 1; no per-attempt timeout 1; no timestamp check 1; no transaction around the event and its deliveries 1; any merchant's id 1; every merchant's deliveries listed 1; no amount check on repeats 1; user names allowed in URLs 1; payment refs not upper-cased 2. Removing <code>SKIP LOCKED</code> at first turned nothing red (see Tests); a test that holds a lock now catches it.</p>
</div>
""" + code(read(T + "FireAndForgetTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SecurityConfig.java", dwn("Who may do what.", "HTTP Basic; merchants only; each sign-in belongs to one merchant.", "Anyone registering a URL for someone else's payments.")),
    (J + "WebhookController.java", dwn("The four endpoints.",
        "Checks the path's merchant against the sign-in, validates bodies, answers <code>202</code> for new payments and <code>200</code> for repeats.",
        "A merchant reading or redirecting another merchant's payments.")),
    (J + "Webhooks.java", dwn("Endpoints, events and the log.",
        "URL checks; the secret; the event and its deliveries in one transaction; a repeat returns the first event.",
        "A payment recorded with nobody to tell, or told twice.",
        "<ul><li>The payload is stored as text: the exact bytes that are signed and sent, not JSON that could be re-encoded differently.</li><li>Payment refs are upper-cased with <code>Locale.ROOT</code>, so <code>pay-1001</code> is a repeat of <code>PAY-1001</code>.</li></ul>")),
    (J + "Dispatcher.java", dwn("Sending, retrying, giving up.",
        "Claims due deliveries in one statement, sends each on a virtual thread, records the attempt and the next one.",
        "A payment lost to a five-minute outage, or sent twice by two servers.",
        "<ul><li>The claim moves the next attempt past a lease (timeout + 30 s), so other rounds do not see it while we send. If this server dies mid-send, the lease runs out and another server tries again: at least once.</li><li>The update checks <code>attempts</code> is still what we claimed; if another round got there first, ours is rolled back.</li><li>Redirects are not followed: the merchant registered this URL.</li></ul>")),
    (J + "WebhookSignature.java", dwn("Signing, and the merchant's check.", "HMAC-SHA256 over id.timestamp.body; constant-time compare; 5-minute tolerance.", "Forged or replayed notifications.")),
    (J + "DispatchSchedule.java", "<p>Runs a round every second after the last one ends (fixed delay, so rounds never pile up). Tests switch it off.</p>"),
    (J + "ProblemResponses.java", "<p><code>401</code> and <code>403</code> in the same problem shape as other errors.</p>"),
    (M + "V1__webhooks.sql", dwn("Four tables.", "Endpoints, events, deliveries (the outbox) and attempts, with named constraints.", "States the code would never write, from any writer.")),
    ("src/main/resources/application.yaml", "<p>The demo rules: first retry, timeout, poll interval.</p>"),
    (J + "WebhooksApplication.java", "<p>Entry point, and the <code>Clock</code> every \"now\" comes from.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
]
tree = """stations/095-webhooks-to-merchants/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/paysetu/webhooks/
│   ├── SecurityConfig.java   ├── WebhookController.java   ├── Webhooks.java
│   ├── Dispatcher.java   ├── DispatchSchedule.java   ├── WebhookSignature.java
│   └── ProblemResponses.java   └── WebhooksApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__webhooks.sql
├── src/test/java/com/paysetu/webhooks/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, test merchant, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Docker", "Docker Desktop (Windows, macOS) or Docker Engine (Linux), running", "<code>docker info</code>"],
    ["Python 3", "Only for the test merchant in Try it yourself", "<code>python3 --version</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""docker compose up -d        # PostgreSQL 17 on localhost:5432
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature (virtual threads are in 21).</p>
<h2>Try it yourself</h2>
<p>Register a URL, start the test merchant with the secret you got, and record a payment:</p>
""" + code("""curl -u ravi:ravi-demo-pass -H 'Content-Type: application/json' -d '{"url":"http://127.0.0.1:9095/hooks/paysetu"}' http://localhost:8080/merchants/1/webhook-endpoints
python3 docs/test-merchant.py 9095 whsec_...the-secret...
curl -u ravi:ravi-demo-pass -H 'Content-Type: application/json' -d '{"paymentRef":"PAY-1001","amountPaise":49900}' http://localhost:8080/merchants/1/test-events""", "bash") + """
<p>The script answers 503 first: watch the retry arrive 30 seconds later, then read <code>GET /webhook-deliveries/1</code>. Stop the script and record another payment to watch the waits grow.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Every attempt says <code>could not connect</code>", "Nothing listens at the URL, or the app cannot reach it (from Docker, <code>127.0.0.1</code> is the container).", "Start the merchant; use an address the app can reach."],
    ["The merchant says the signature is wrong", "The body was parsed and re-serialised before checking, or the secret's <code>whsec_</code> prefix was not removed before Base64-decoding.", "Verify the raw bytes, with the decoded key."],
    ["\"timestamp within 5 minutes: NO\"", "The merchant's clock is off.", "Sync it with NTP."],
    ["<code>Could not find a valid Docker environment</code>", "Docker is not running.", "Start Docker Desktop or the Docker service."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the dispatcher and the database behind it.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>WebhookContractTest</code> ({cnt('WebhookContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>FireAndForgetTrapTest</code> ({cnt('FireAndForgetTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>WebhookDatabaseTest</code> ({cnt('WebhookDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, one user accessing another user's data, malicious input", f"<code>WebhookSecurityTest</code> ({cnt('WebhookSecurityTest')})", '<span class="pill ok">pass</span>'],
    ["Messaging", "Duplicate delivery, retry and dead letter", f"<code>RetryAndDeadLetterMessagingTest</code> ({cnt('RetryAndDeadLetterMessagingTest')}), <code>DuplicateDeliveryMessagingTest</code> ({cnt('DuplicateDeliveryMessagingTest')}), <code>ScheduledDeliveryTest</code> ({cnt('ScheduledDeliveryTest')})", '<span class="pill ok">pass</span>'],
    ["Idempotency", "Replay: the same request twice gives one effect", f"<code>PaymentReplayTest</code> ({cnt('PaymentReplayTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">An hour of retries runs in milliseconds: the app takes \"now\" from a <code>Clock</code>, the tests move a <code>TestClock</code> by hand and run dispatcher rounds themselves, with the schedule switched off. One test keeps the real schedule and clock, and waits for the delivery with Awaitility instead of a fixed sleep.</p>
<p class="muted">Found while building: with <code>FOR UPDATE SKIP LOCKED</code> removed, the two-rounds-at-once test still passed. The claim is one short statement, and the lease it writes already hides the rows from the next round, so the two rounds almost never meet inside it. A second test holds a lock on one delivery, as a round in the middle of its claim would, and checks that the dispatcher takes the other one at once instead of waiting: that one fails without <code>SKIP LOCKED</code>.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "FireAndForgetTrapTest.java", "<p>Written first: the old way against the API, with the merchant down for five minutes.</p>"),
    (T + "WebhookContractTest.java", "<p>Registering, the exact request a merchant receives, the delivery log.</p>"),
    (T + "RetryAndDeadLetterMessagingTest.java", "<p>Every wait, one second early and on time; the dead letter; timeouts, redirects, no server.</p>"),
    (T + "DuplicateDeliveryMessagingTest.java", "<p>Two rounds at once; a delivery locked by another round skipped.</p>"),
    (T + "PaymentReplayTest.java", "<p>The same payment reported twice: one event, one send; another amount 409.</p>"),
    (T + "WebhookSecurityTest.java", "<p>401, 403, another merchant's data, malicious input, forged and replayed signatures.</p>"),
    (T + "WebhookDatabaseTest.java", "<p>Named constraints with plain SQL; the event and its deliveries commit together.</p>"),
    (T + "ScheduledDeliveryTest.java", "<p>The real schedule and clock.</p>"),
    (T + "TestMerchant.java", "<p>A merchant's server: records what arrives, answers what the test says.</p>"),
    (T + "TestClock.java", "<p>A clock moved by hand.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: empty tables and the clock at 10:00 UTC before each test, the scheduler off.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/paysetu/webhooks/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=RetryDeadDeliveryChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Send a dead letter again", "Beginner-friendly", 25,
    "<code>POST /webhook-deliveries/{id}/retry</code>: a <code>FAILED</code> delivery goes back to <code>PENDING</code> with zero attempts, due now, and the old attempts stay in the log. Any other state is <code>409</code>; another merchant's delivery <code>404</code>.",
    "both tests in <code>RetryDeadDeliveryChallengeTest</code> pass.",
    ["One UPDATE with <code>WHERE status = 'FAILED'</code> and the merchant check; 0 rows means 404 or 409: read the row to tell which.",
     "The database already allows it: attempts 0 with a next attempt is a valid pending row.",
     "A new matcher in <code>SecurityConfig</code>: everything not listed is denied."],
    "challenge/RetryDeadDeliveryChallengeTest.java", ["challenge/solution/Webhooks.java", "challenge/solution/WebhookController.java", "challenge/solution/SecurityConfig.java"]) + challenge(2, "Rotate the secret", "Go deeper", 40,
    "<code>POST /merchants/{id}/webhook-endpoints/{endpointId}/secret</code> gives the endpoint a new secret (<code>201</code>). For 24 hours every request carries two signatures, new and old, separated by a space, so the merchant can switch over without rejecting a payment. After that, only the new one.",
    "both tests in <code>RotateSecretChallengeTest</code> pass.",
    ["A V2 migration: <code>previous_secret</code> and <code>previous_secret_until</code>, both set or both empty (a CHECK).",
     "The claim can return the old secret only while it is valid: <code>CASE WHEN previous_secret_until &gt; :now THEN previous_secret END</code>.",
     "<code>verify</code> already accepts any one of several signatures."],
    "challenge/RotateSecretChallengeTest.java", ["challenge/solution/V2__previous_secret.sql", "challenge/solution/Dispatcher.java", "challenge/solution/Webhooks.java", "challenge/solution/WebhookController.java", "challenge/solution/SecurityConfig.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>A merchant that is gone for a week</h2>
<p>One merchant's server has been off for a week. Every payment makes a delivery that fails eight times. Design what happens: when do you stop sending to that endpoint, how do you tell the merchant, and how do they get the missed payments once they are back (a retry per delivery, a \"replay since\" button, or a list endpoint they poll)? And a merchant that needs payment events in order: what would you change?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old way and the five-minute outage.</li>
<li>Write the tables and their constraints; the event and its deliveries in one transaction.</li>
<li>Write the signature and its check, with tests for tampering and replay.</li>
<li>Write the dispatcher: claim, send, record; then the backoff and the dead letter; then two rounds at once.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["An outbox table and a scheduled dispatcher", "A poll every second; at-least-once, so merchants must drop repeats.", '<span class="pill ok">Chosen</span>'],
    ["Post right after the payment, once", "Lost on any outage; no proof of what was sent.", '<span class="pill bad">The trap</span>'],
    ["Post inside the payment's transaction", "A slow merchant holds the payment's transaction and connection; a rollback after posting announces a payment that did not happen.", '<span class="pill bad">Avoid</span>'],
    ["A message broker (Kafka, RabbitMQ) with retry topics", "Another system to run; the outbox is still needed to publish atomically.", '<span class="pill warn">At larger scale</span>'],
    ["Fixed retry every 30 s, forever", "Hammers a merchant that is down; never tells anyone it failed.", '<span class="pill bad">Review finding</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>events_once_per_object</code>", "UNIQUE (merchant, type, payment ref)", "A payment reported twice is one event."],
    ["<code>deliveries_once_per_endpoint</code>", "UNIQUE (event, endpoint)", "Never two deliveries of one event to one URL."],
    ["<code>deliveries_attempts_range</code>", "CHECK 0..8", "The attempt limit, for any writer."],
    ["<code>deliveries_pending_has_next</code>, <code>deliveries_delivered_has_time</code>", "CHECKs", "Pending exactly when a next attempt is set; delivered exactly when a time is."],
    ["<code>deliveries_due</code>", "Partial index on next attempt, pending only", "The dispatcher's query reads only what is waiting."],
    ["<code>endpoints_url_http</code>, <code>endpoints_secret_format</code>", "CHECKs", "Only web URLs; only generated secrets."]]) + """
<p><strong>Transaction boundaries:</strong> the event and its deliveries commit together. The claim is one autocommitted statement. Each attempt and the delivery's new state commit together, after the HTTP call: no transaction is open while we wait for a merchant.</p>
""" + code(read(M + "V1__webhooks.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Where URLs point</dt><dd>A webhook URL is user input your server will call. Check the address it resolves to on every attempt (no private, loopback or metadata addresses), as an SSRF-safe fetcher does. Not done here: a demo rule.</dd>
<dt>Secrets</dt><dd>The secret must be readable to sign, so it cannot be hashed: encrypt it at rest with a key from a KMS. Here it is stored as is.</dd>
<dt>Jitter</dt><dd>After a big outage every delivery retries on the same schedule. Add a random part to each wait so they spread out.</dd>
<dt>Merchants who are gone</dt><dd>Disable an endpoint after days of failures and email the merchant (challenge 3).</dd>
<dt>Clean-up</dt><dd>Events, deliveries and attempts grow forever here. Keep them for a set time, then delete or archive.</dd>
<dt>Monitoring</dt><dd>Alert on the age of the oldest pending delivery and on the number of failures per merchant.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("How do you make sure a webhook is not lost?", "Write it to an outbox table in the same transaction as the change, and send it from a background job that retries until a 2xx or a limit."),
    ("Exactly once or at least once?", "At least once: a timeout after the merchant processed it means we send again. Send a stable id so the receiver can drop repeats."),
    ("How does the merchant know a webhook is from you?", "An HMAC-SHA256 signature over the id, a timestamp and the raw body, with a shared secret; compared in constant time."),
    ("Why sign the timestamp?", "So a captured request cannot be replayed later: the receiver refuses timestamps older than a few minutes."),
    ("Why exponential backoff?", "A merchant that is down gets fewer and fewer requests, and the retries still cover a long outage: 8 tries over about an hour here."),
    ("How do two servers avoid sending the same row?", "Claim rows with FOR UPDATE SKIP LOCKED and move them past a lease in the same statement."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Delivery", "Retries on failure.", "Outbox in one transaction, backoff, dead letter, at-least-once with a stable id."],
    ["Security", "Requests are signed.", "Timestamp in the signature, constant-time check, secrets per endpoint."],
    ["Testing", "A retry test.", "A clock you move, parallel rounds, and one test with the real schedule."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("Two servers send the same delivery",
     "\"The update after sending moves it on\": but between the SELECT and that update, the HTTP call takes as long as the merchant does. Another server's round, a second later, reads the same rows and sends them again. Every app with two instances sends duplicates. The claim must move the row on before sending, in the same statement that picks it (here: a lease, with SKIP LOCKED).",
     "<code>twoServersDispatchingAtOnceSendEachDeliveryOnce</code> and <code>aDeliveryAnotherRoundIsClaimingIsSkippedNotWaitedFor</code> fail."),
    ("Retrying every 30 seconds, forever",
     "\"So it arrives soon after they are back\": and a merchant that is down for a day gets 2,880 requests per payment, all at once when it comes back. The waits must grow. And \"never give up\" hides the problem: nobody is told the delivery failed. Worse, the database's limit of 8 attempts makes the ninth try's record fail: the row is unchanged and still due, so it is sent again on every round, every second.",
     "<code>theWaitDoublesAfterEachFailureAndTheEighthFailureIsFinal</code> and <code>theApiKeepsThePaymentUntilTheMerchantIsBack</code> fail."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate simplifies the dispatcher: a plain SELECT of what is due instead of the \"complicated\" UPDATE, \"since the update after sending moves it on anyway\", and a retry every 30 seconds until it works, \"because merchants want every payment\". Read the file and list every problem before opening the findings.</p>
<p class="path">review/Dispatcher.java</p>
""" + code(read("review/Dispatcher.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">With one server and a merchant that is up, the flawed dispatcher delivers every payment. Its problems need a second instance and an outage: both normal in production.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
