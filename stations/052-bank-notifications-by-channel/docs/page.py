"""Station 052 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 52,
    "stack": "Spring Boot 4.1.1 · Java 25 · interfaces and constructor injection of List&lt;Channel&gt; · @MockitoSpyBean · Clock with @TestBean · RFC 9457 problem details",
    "simulation": "Customers and messages are demo data, not Tijori's. No SMS, email or push is sent: each channel records the message in an in-memory outbox (a record is created). Which channel each notice must use is a demo rule, not a regulator's.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tijori/notifications/"
T = "src/test/java/com/tijori/notifications/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Single responsibility", "A class has one reason to change.", "The SMS team edits SMS wording without touching email.", "<code>SmsChannel</code>, <code>EmailChannel</code>, <code>PushChannel</code>"),
    ("Interface", "A promise of what a class can do, without saying how.", "\"Can deliver a notice\".", "<code>Channel</code>"),
    ("Dependency inversion", "The main logic depends on the promise, not on each concrete class.", "The bank's rules call \"a channel\", not \"the SMS gateway\".", "<code>NotificationService(List&lt;Channel&gt;)</code>"),
    ("Failure isolation", "One part failing does not stop the others.", "The email server is down; the SMS still goes.", "<code>try</code> per channel"),
    ("GSM-7", "The alphabet an ordinary 160-character SMS uses.", "\"Rs\" fits; \"₹\" does not.", "<code>SmsChannel</code>"),
    ("Overkill", "Structure that costs more than it saves.", "A factory of factories for three channels.", "Two-method interface, nothing more"),
]
STORY = [
    ("900 lines, three channels", "Tijori's NotificationService wrote and sent SMS, email and push in one class. Every change was made in the same file."),
    ("Two email changes broke SMS", "In March the email redesign lower-cased the address (customers without email now crashed before their SMS) and changed \"Rs\" to \"₹\" in the shared amount format (SMS lost its 160-character limit)."),
    ("The fix", "One small class per channel, each with its own wording and limits, behind a two-method interface; the service only decides which channels to use, and one channel's failure cannot stop another."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">When three things change for different reasons, keep them in three places, so a change to one cannot break the others.</p>

<h2>What are we building?</h2>
<p>Internal systems post a notice (<code>POST /notifications</code>): a debit, a new-device login, a statement. The service decides which channels it goes to and answers what happened on each. Customers set which channels they want (<code>PUT /customers/{id}/notification-preferences</code>).</p>

<h2>An everyday analogy</h2>
<p>A bank branch with one clerk who writes every letter, SMS and phone call. Teach them a new letter format and they start writing SMS like letters. A branch with a letter desk, an SMS desk and a phone desk, and a manager who only says "send this to the SMS desk and the letter desk", can retrain one desk without the others noticing.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>A notice arrives</strong>: debit of ₹1,499 for Asha at BigBasket.</li>
<li><strong>The service asks the rule</strong> for that type and Asha's preferences: which channels?</li>
<li><strong>Each chosen channel</strong> writes its own text and records it; a channel with no address says UNREACHABLE.</li>
<li><strong>A channel that throws</strong> is marked FAILED; the others are unaffected.</li>
</ol>

<details class="qa check"><summary>Check yourself: why does the SMS say "Rs" while the email says "₹"?</summary><p>"₹" is not in GSM-7. One such character turns the whole SMS into UCS-2, where one part holds 70 characters instead of 160, so the alert costs two or three parts. Email has no such limit. Only the SMS class needs to know this.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real providers.</strong> Messages are recorded, not sent.</li>
<li><strong>No retries or queue.</strong> Retrying failed channels is challenge 2.</li>
<li><strong>No login.</strong> In a bank only internal systems may post notices.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tijori</strong> (a fictional digital bank) sends alerts by SMS, email and push from one large class. Each change for one channel risked the others, and in March two of them stopped debit alerts.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a ₹1,499 debit for Asha, <b>then</b> SMS, email and push are SENT, each in its own words; the SMS is GSM-7 and at most 160 characters.</li>
<li><b>Given</b> the same for Rohan (no email, no app), <b>then</b> the SMS is SENT, email UNREACHABLE, push SKIPPED.</li>
<li><b>Given</b> the email provider throws, <b>then</b> email is FAILED and SMS and push are SENT.</li>
<li><b>Given</b> Asha turns off email and push, <b>then</b> a statement notice goes by SMS only, a debit by SMS, and a new-device login still to all three.</li>
<li><b>Given</b> ₹1,23,45,678.90, <b>then</b> the SMS shows Indian grouping.</li>
<li><b>Given</b> a malformed body, <code>400</code>; a debit without amount or an unknown customer, <code>422</code>; preferences of an unknown customer, <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>One class per channel; the service depends only on the <code>Channel</code> interface.</li>
<li>One channel's failure never stops another.</li>
<li>Money in integer paise, shown in Indian grouping.</li>
<li>Addresses are masked in responses.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Split a class by its reasons to change.</li>
<li>Depend on a small interface and let Spring inject every implementation.</li>
<li>Isolate failures between independent parts.</li>
<li>Tell useful structure from overkill.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/notifications</code>", "A notice: <code>customerId</code>, <code>type</code> (<code>DEBIT_ALERT</code>, <code>NEW_DEVICE_LOGIN</code>, <code>STATEMENT_READY</code>), <code>amountPaise</code> (debits), <code>merchant</code> (optional, up to 24 characters). Answers one delivery per channel."],
    ["<code>PUT</code>", "<code>/customers/{id}/notification-preferences</code>", "Set <code>sms</code>, <code>email</code> and <code>push</code>, all three required."]]) + """
<h2>Delivery statuses</h2>
""" + table(["Status", "Meaning"], [
    ["<code>SENT</code>", "The channel recorded the message (simulated sending)."],
    ["<code>SKIPPED</code>", "The rule for this type and the customer's preferences do not use this channel."],
    ["<code>UNREACHABLE</code>", "No address on this channel: no email on file, no app."],
    ["<code>FAILED</code>", "The channel threw; the others were still tried."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Notice handled, whatever each channel's outcome"],
    ['<span class="pill ok">200</span>', "Preferences saved"],
    ['<span class="pill warn">400</span>', "Malformed body: missing customer, unknown type, amount 0 or with decimals, merchant too long"],
    ['<span class="pill warn">404</span>', "No such customer (preferences)"],
    ['<span class="pill warn">422</span>', "Unknown customer in the body; a debit alert without an amount"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-a-debit-alert-for-asha", "Case 1: a ₹1,499 debit for Asha", "<b>Why:</b> three channels, three wordings; \"Rs\" in the SMS, \"₹\" elsewhere."),
    ("02-a-debit-alert-for-rohan", "Case 2: the same for Rohan", "<b>Why:</b> no email: UNREACHABLE, and the SMS still goes. This is the case the old class crashed on."),
    ("03-asha-turns-off-email-and-push", "Case 3: Asha keeps SMS only", "<b>Why:</b> <code>200</code>."),
    ("04-her-statement-notice", "Case 4: her statement notice", "<b>Why:</b> statements follow preferences: SMS only."),
    ("05-a-debit-in-crores", "Case 5: a debit of ₹1,23,45,678.90", "<b>Why:</b> Indian grouping; still by SMS, whatever the preference."),
    ("06-a-debit-alert-without-amount", "Case 6: a debit alert with no amount", "<b>Why:</b> <code>422</code>."),
    ("07-an-unknown-type", "Case 7: type LOAN_OFFER", "<b>Why:</b> not a notice this service sends: <code>400</code>."),
    ("08-preferences-of-customer-99", "Case 8: preferences of customer 99", "<b>Why:</b> <code>404</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A debit for a customer with every channel", "Three deliveries, each in its own words", "<code>aDebitAlertGoesToEveryChannelInItsOwnWords</code>"],
    ["Preferences off, by type", "Statement by preference; debit always SMS; login everywhere", "<code>preferencesDecideExceptWhereTheRulesSayOtherwise</code>"],
    ["Lakhs and crores", "Indian grouping", "<code>lakhsAndCroresAreGroupedTheIndianWay</code>, <code>rupeesAreGroupedInThreeThenTwos</code>"],
    ["Email provider throws", "Email FAILED, SMS and push SENT", "<code>anEmailOutageLeavesSmsAndPushWorking</code>"],
    ["Malformed bodies", "<code>400</code>, nothing recorded", "<code>brokenRequestsAre400</code>"],
    ["Debit without amount; unknown customer", "<code>422</code>", "<code>impossibleNoticesAre422</code>"],
    ["Preferences of an unknown customer", "<code>404</code>", "<code>unknownCustomersPreferencesAre404</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">One class doing SMS, email and push, so one change breaks all three.</p>
<p>The old class is kept in the tests as <code>OldNotificationService</code>, with its two March changes. Both were made for email. The first lower-cases the email address before anything is sent: for Rohan, who has no email, it throws, and his debit alert never goes out by any channel. The second changed the shared amount format from "Rs" to "₹": the SMS now contains a character outside GSM-7 and is over 70 characters, so it is sent in parts. Through the fixed service, Rohan's SMS is SENT and Asha's SMS is GSM-7 within 160 characters.</p>
<p>While building, each part was undone once. Removing the per-channel <code>try</code> turned 1 test red (the email outage); "₹" in the SMS, 3; ignoring preferences, 1; western grouping, 2. Removing the email channel's "no address" check turned 1 red, and showed isolation working: the email channel threw, was marked FAILED instead of UNREACHABLE, and the SMS still went.</p>
</div>
""" + code(read(T + "OneClassForAllChannelsTrapTest.java"), "java") + code(read(T + "OldNotificationService.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "NotificationController.java", dwn("Validates the body, finds the customer, builds the channel-neutral notice.", "HTTP only.", "Channel details in the controller.")),
    (J + "NotificationService.java", dwn("Picks channels by the type's rule and the preferences; asks each to deliver; isolates failures.",
        "Knows no wording and no provider: only the <code>Channel</code> interface.", "One channel's crash stopping the rest.",
        "<ul><li>Spring injects every <code>Channel</code> bean as a list: a new channel is a new class, not an edit here.</li><li>A <code>RuntimeException</code> from one channel becomes FAILED for that channel only, and is logged.</li></ul>")),
    (J + "Channel.java", dwn("Two methods: a name and <code>deliver</code>.", "Small enough that every channel can honour it fully.", "A wide interface half of whose methods each channel fakes.")),
    (J + "SmsChannel.java", dwn("SMS wording; GSM-7, 160 characters; masked phone.", "The only place that knows SMS limits.", "\"₹\" in an SMS.")),
    (J + "EmailChannel.java", "<p>Email subject and body; lower-cases the address only when there is one.</p>"),
    (J + "PushChannel.java", "<p>A short lock-screen line, with no account digits.</p>"),
    (J + "Model.java", "<p>The shared plain types; the per-type channel rule lives on <code>NotificationType</code>.</p>"),
    (J + "Rupees.java", "<p>Indian grouping for paise, written by hand because <code>DecimalFormat</code> supports only one group size.</p>"),
    (J + "Customers.java", "<p>Demo customers and their preferences, in memory.</p>"),
    (J + "Outbox.java", "<p>Where simulated sending records each message.</p>"),
    (J + "NotificationsApplication.java", "<p>Entry point; a <code>Clock</code> in India time for message dates.</p>"),
]
tree = """stations/052-bank-notifications-by-channel/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tijori/notifications/
│   ├── NotificationController.java   ├── NotificationService.java   ├── Channel.java
│   ├── SmsChannel.java   ├── EmailChannel.java   ├── PushChannel.java
│   ├── Model.java   ├── Rupees.java   ├── Customers.java   ├── Outbox.java   └── NotificationsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/tijori/notifications/   (see Tests)
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
<p>Change "Tijori: Rs " to "Tijori: ₹" in <code>SmsChannel</code> and run the tests:</p>
""" + code("""./mvnw test -Dtest=OneClassForAllChannelsTrapTest""", "bash") + """
<p>The GSM-7 test fails, and only for SMS: email and push are separate classes and do not change. Put it back.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["An SMS billed as two or three parts", "A character outside GSM-7 (₹, curly quotes, emoji) makes it UCS-2: 70 characters a part.", "Keep SMS text in GSM-7."],
    ["<code>12,345,678.00</code> for an Indian amount", "<code>DecimalFormat</code> has one grouping size.", "Group the last three digits, then twos (<code>Rupees</code>)."],
    ["One provider outage stops all alerts", "Channels called in a row without isolation.", "Catch per channel; record FAILED; carry on."],
    ["<code>No qualifying bean of type Channel</code>", "A channel class without <code>@Component</code>, or outside the scanned package.", "Annotate it in this package."],
    ["Channel order changes in the response", "Spring's list order is not a contract.", "Sort deliveries; tests look channels up by name."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then each channel.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>NotificationContractTest</code> ({cnt('NotificationContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>OneClassForAllChannelsTrapTest</code> ({cnt('OneClassForAllChannelsTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station's concepts", "A channel failing alone; money formatting alone", f"<code>ChannelIsolationTest</code> ({cnt('ChannelIsolationTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "OneClassForAllChannelsTrapTest.java", "<p>Written first: both March changes in the old class, then the fixed service.</p>"),
    (T + "NotificationContractTest.java", "<p>Wording per channel, preferences by type, Indian grouping, and every refusal.</p>"),
    (T + "ChannelIsolationTest.java", "<p>The email channel made to throw with <code>@MockitoSpyBean</code>; rupee grouping edge values.</p>"),
    (T + "OldNotificationService.java", "<p>The old class, kept only in tests.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: a fixed Clock, an empty outbox and default preferences before each test.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tijori/notifications/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=WhatsAppChallengeTest</code>.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "A WhatsApp channel", "Beginner-friendly", 20,
    "Add WHATSAPP: to the customer's phone, opt-in (<code>\"whatsapp\": true</code> in the preferences; absent means false). The notification service should not change.",
    "the test in <code>WhatsAppChallengeTest</code> passes.",
    ["One new <code>@Component</code> implementing <code>Channel</code>.",
     "Adding the enum value makes the compiler point at every <code>switch</code> that must decide about it."],
    "challenge/WhatsAppChallengeTest.java", ["challenge/solution/WhatsAppChannel.java", "challenge/solution/Model.java", "challenge/solution/NotificationController.java"]) + challenge(2, "Retry what failed", "Go deeper", 30,
    "Add <code>POST /notifications/{id}/retry</code>: deliver again only the channels that FAILED. A customer must never get a second SMS because email was down. Nothing failed: <code>409</code>; unknown id: <code>404</code>.",
    "the test in <code>RetryChallengeTest</code> passes.",
    ["Keep each notification's customer, notice and deliveries.",
     "Replace only FAILED deliveries; keep the others as they were."],
    "challenge/RetryChallengeTest.java", ["challenge/solution/NotificationService.java", "challenge/solution/NotificationController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>When is this overkill?</h2>
<p>Tijori's HR tool sends one email when a payslip is ready, and nothing else. Would you write a <code>Channel</code> interface and an email class for it, or one method? List the signs that would make you split it later, and what splitting would cost then.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test with the old class and its two March changes.</li>
<li>List each reason to change: SMS limits, email layout, push wording, who-gets-what rules. One home each.</li>
<li>Write the smallest interface the service needs from a channel, and one class per channel.</li>
<li>Isolate failures, and test one channel failing alone.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["One class per channel behind a two-method interface", "A few small files.", '<span class="pill ok">Chosen</span>'],
    ["One service for all channels", "Every change touches every channel.", '<span class="pill bad">The trap</span>'],
    ["Abstract base class with template methods", "Shared code nobody can change alone; subclasses tied together.", '<span class="pill warn">Overkill here</span>'],
    ["A channel factory or registry", "Spring already gives us every <code>Channel</code> bean as a list.", '<span class="pill warn">Overkill here</span>'],
    ["A queue per channel", "Real isolation and retries; another system to run.", '<span class="pill warn">At scale</span>']]) + """
<h2>Database design</h2>
<p>None in this station. A real service would keep a <code>notifications</code> table and a <code>deliveries</code> table (one row per channel and attempt), which is what challenge 2's retry needs to survive a restart.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Providers fail</dt><dd>SMS gateways and email providers time out. Give each call a timeout, record the outcome per channel, and alert on a rising FAILED rate.</dd>
<dt>SMS rules in India</dt><dd>Commercial SMS is sent through registered sender IDs and templates under TRAI's rules. Text changes may need a new template; keep SMS wording in one place.</dd>
<dt>Masking</dt><dd>Responses and logs show masked addresses; full numbers stay with the provider call.</dd>
<dt>Preferences and law</dt><dd>Which alerts a customer may turn off is a compliance decision. Here it is a demo rule; in a bank, the compliance team writes it down.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What does the single responsibility principle mean in practice?", "A class should have one reason to change. SMS limits, email layout and the who-gets-what rule change for different reasons, at different times, by different people, so they live in different classes."),
    ("What is dependency inversion here?", "NotificationService depends on the Channel interface; the SMS and email classes depend on it too. Neither side depends on the other's details, so either can change alone."),
    ("How does Spring help?", "Injecting List<Channel> gives every Channel bean. Adding a channel is one new class; the service does not change."),
    ("Why catch exceptions per channel?", "Channels are independent. Without it, the first failure stops every later channel: an email outage would stop debit alerts by SMS."),
    ("When is an interface overkill?", "When there is one implementation, it is unlikely to grow, and tests do not need a substitute. Extract it when the second implementation or a real test need arrives."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You broke one channel and saw only its tests fail."],
    ["Design", "One class per channel, one small interface.", "You can say what you did not add, and why."],
    ["Resilience", "One failure does not stop the others.", "You know what a queue would add."],
    ["Details", "GSM-7 and Indian grouping right.", "You can explain UCS-2 and SMS parts."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any class that grows:</p>
<ul class="rules">
<li>How many different people or reasons would change this class?</li>
<li>Can one part throw and stop parts that do not depend on it?</li>
<li>Is an abstraction here because of a second implementation or a test, or "for later"?</li>
<li>Would a new variant be a new class, or an edit to a long <code>if</code>?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
