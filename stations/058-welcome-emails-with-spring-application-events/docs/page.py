"""Station 058 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 58,
    "stack": "Spring Boot 4.1.1 · Java 25 · ApplicationEventPublisher · @TransactionalEventListener(AFTER_COMMIT) · @Async on virtual threads · HtmlUtils · JdbcClient · PostgreSQL 17 · Flyway · Testcontainers · Awaitility",
    "simulation": "No email is sent and no CRM is called: the welcome email is recorded in an in-memory mailbox, and the CRM records the contact after a configurable delay. Sign-ups and invites are demo data, not Taskloom's.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/taskloom/welcome/"
T = "src/test/java/com/taskloom/welcome/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Application event", "A message one part of the app publishes and others listen to.", "A shop's bell that rings when a customer enters.", "<code>SignedUp</code>"),
    ("Plain listener", "Runs at once, inside the publishing call, before the transaction ends.", "Greeting the customer before they have paid.", "<code>@EventListener</code>"),
    ("After-commit listener", "Runs only once the transaction has committed.", "Sending the thank-you note after payment clears.", "<code>@TransactionalEventListener</code>"),
    ("Async", "Runs on another thread, so the caller does not wait.", "Posting a letter instead of delivering it yourself.", "<code>@Async</code>"),
    ("Retry and dead letter", "Try again a few times; then set the message aside for a person.", "Returned post kept at the counter.", "<code>DEAD</code> status"),
    ("Escaping", "Turning special characters into plain text so they cannot act as code.", "Writing \"&lt;b&gt;\" instead of making text bold.", "<code>HtmlUtils.htmlEscape</code>"),
]
STORY = [
    ("Sign-up did everything", "Taskloom's sign-up sent the welcome email, told the CRM and the analytics system, then answered. When the CRM was slow, sign-up was slow."),
    ("Events, too early", "The team switched to events, with plain listeners. They run inside publishEvent, before the commit. Sign-ups rolled back later, for a full team invite, had already been welcomed by email."),
    ("The fix", "Listeners that run after commit, on other threads; one welcome email per sign-up however often the event arrives; retries, then a dead-letter state; and a name escaped before it goes into HTML."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Side effects belong after the commit, and off the request's path.</p>

<h2>What are we building?</h2>
<p><code>POST /signups</code> saves a sign-up (optionally joining a team through an invite) and answers at once. After it commits, two things happen on their own: a welcome email and a CRM record. <code>GET /signups/{id}</code> shows where the welcome email is.</p>

<h2>An everyday analogy</h2>
<p>A hotel front desk. The receptionist checks you in and hands over the key. Only then does someone else send the welcome note and update the loyalty system. If check-in is cancelled halfway, nobody sends the note; if the loyalty system is slow, you still get your key.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>The service saves</strong> the sign-up and publishes <code>SignedUp</code>; nothing happens yet.</li>
<li><strong>It may still fail</strong> (a full invite): then everything rolls back, and the event is dropped.</li>
<li><strong>On commit</strong>, Spring hands the event to the after-commit listeners, each on its own thread.</li>
<li><strong>The email listener</strong> claims the email once, sends it, retries if the provider fails, and gives up to DEAD after three attempts.</li>
</ol>

<details class="qa check"><summary>Check yourself: the email listener runs after commit. Why must it still guard against duplicates?</summary><p>Events can arrive twice: a retry by a person, a re-published event, a second instance. Without the claim row, each one sends an email. With it, the database lets exactly one through.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real email or CRM.</strong> Both are simulated.</li>
<li><strong>No outbox.</strong> Events live in memory: a crash between commit and listener loses the email (see Production).</li>
<li><strong>No login.</strong> Sign-up is the start.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Taskloom</strong> (a fictional SaaS) welcomed people whose sign-up had failed, and made every sign-up wait for its slowest partner system.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> Asha signs up, <b>then</b> <code>201</code> with welcomeEmail PENDING, then one UTF-8 HTML welcome email, then SENT.</li>
<li><b>Given</b> Ravi signs up with a full invite, <b>then</b> <code>409</code>, no sign-up, and no email, ever.</li>
<li><b>Given</b> the CRM hangs, <b>then</b> the sign-up still answers in under 2 seconds and the email still goes.</li>
<li><b>Given</b> the same event five times at once, <b>then</b> one email.</li>
<li><b>Given</b> the provider fails twice, <b>then</b> the third attempt sends it; failing every time, the email is DEAD after 3 attempts, with the error.</li>
<li><b>Given</b> a name like <code>Zoë &lt;b&gt;&amp; co&lt;/b&gt;</code> or one with a line break, <b>then</b> it is text in the body and one line in the subject.</li>
<li><b>Given</b> a malformed body, <code>400</code>; a taken email, <code>409</code>; an unknown invite, <code>422</code>; an unknown sign-up, <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Side effects run after commit, never for a rolled-back sign-up.</li>
<li>Slow partners never slow the sign-up.</li>
<li>One welcome email per sign-up, guarded by the database.</li>
<li>Bounded retries, then a visible dead-letter state.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Publish and listen to application events.</li>
<li>Choose between <code>@EventListener</code> and <code>@TransactionalEventListener</code>.</li>
<li>Run listeners asynchronously, and test asynchronous code.</li>
<li>Make a side effect idempotent, retried, and dead-lettered; and write safe HTML email.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/signups</code>", "Sign up: <code>email</code>, <code>name</code>, optional <code>inviteCode</code> to join a team."],
    ["<code>GET</code>", "<code>/signups/{id}</code>", "The sign-up and its <code>welcomeEmail</code>: PENDING, SENDING, SENT or DEAD."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Signed up (the email follows after commit)"],
    ['<span class="pill ok">200</span>', "The sign-up"],
    ['<span class="pill warn">400</span>', "Malformed email, blank name, malformed invite code"],
    ['<span class="pill warn">404</span>', "No such sign-up"],
    ['<span class="pill warn">409</span>', "Email already signed up; invite has no seats left (nothing kept)"],
    ['<span class="pill warn">422</span>', "Unknown invite (nothing kept)"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against one fresh database (invite DESIGN-26 with seats, OPS-FULL without). JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-asha-signs-up", "Case 1: Asha signs up", "<b>Why:</b> <code>201</code> at once; the email is still PENDING."),
    ("02-a-moment-later", "Case 2: a second later", "<b>Why:</b> the after-commit listener has sent it: SENT."),
    ("03-ravi-with-a-full-invite", "Case 3: Ravi, invite OPS-FULL", "<b>Why:</b> the sign-up was saved and the event published, then the invite failed: rolled back, <code>409</code>, no email."),
    ("04-meera-with-a-design-team-invite", "Case 4: Meera, invite DESIGN-26", "<b>Why:</b> a seat taken, <code>201</code>."),
    ("05-asha-again", "Case 5: Asha@x.com again", "<b>Why:</b> <code>409</code>."),
    ("06-not-an-email", "Case 6: asha.x.com", "<b>Why:</b> <code>400</code>."),
    ("07-no-such-signup", "Case 7: sign-up 99", "<b>Why:</b> <code>404</code>."),
]) + """
<h2>What happened after each commit</h2>
<p class="muted">From the running app's log (<code>docs/captures/app-log.txt</code>) and the <code>sent_emails</code> table (<code>docs/captures/emails.txt</code>), after the requests above: two welcome emails, for Asha and Meera; none for Ravi, whose sign-up does not exist.</p>
""" + code(read("docs/captures/app-log.txt").rstrip(), "text") + code(read("docs/captures/emails.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A sign-up", "<code>201</code> PENDING, then one email, then SENT", "<code>aSignupIsAnsweredAtOnceAndWelcomedAfter</code>"],
    ["HTML and line breaks in the name", "Escaped in the body; one line in the subject", "<code>theNameIsTextInTheEmailNotHtmlOrHeaders</code>"],
    ["An invite with seats", "Seat taken, email sent", "<code>anInviteWithSeatsJoinsTheTeam</code>"],
    ["Full or unknown invite; taken email", "<code>409</code>, <code>422</code>, <code>409</code>; no email for any", "<code>aFullOrUnknownInviteOrATakenEmailIsRefusedAndNotWelcomed</code>"],
    ["Malformed; unknown", "<code>400</code>; <code>404</code>", "<code>malformedSignupsAre400</code>, <code>unknownSignupsAre404</code>"],
    ["A hanging CRM", "Sign-up and email unaffected", "<code>theSignupAndTheEmailDoNotWaitForTheCrm</code>"],
    ["The same event five times at once", "One email", "<code>theSameEventDeliveredFiveTimesAtOnceSendsOneEmail</code>"],
    ["Provider fails twice", "Retried; sent on attempt 3", "<code>aProviderThatFailsTwiceIsRetriedAndTheEmailGoesOnce</code>"],
    ["Provider never recovers", "DEAD after 3; a late duplicate does not resend", "<code>aProviderThatNeverRecoversLeavesTheEmailDeadForAPerson</code>"],
    ["Bad rows written directly; a rolled-back invite", "Refused by named constraints; nothing kept", "<code>SignupDatabaseTest</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Sending email in a plain listener before commit; failed sign-ups still get mail.</p>
<p>The old flow is kept in the tests as <code>OldSignupFlow</code>, with the same steps as today and a plain <code>@EventListener</code> that sends the welcome email. Ravi signs up with a full invite: the exception rolls the sign-up back, there is no account, and the mailbox holds one "Welcome to Taskloom" addressed to him. Through today's API the same request leaves no sign-up and, checked for half a second, no email.</p>
<p>While building, each part was undone once. A synchronous plain listener, the old shape, turned 2 tests red: the trap and the full-invite contract test. An <code>@Async</code> plain listener turned a different one red. It ran on another thread before the commit, when PostgreSQL could not yet see the new sign-up, so its claim failed on <code>sent_emails_signup_fk</code> and a valid sign-up got no email. A CRM listener without <code>@Async</code> turned 1 red (the hanging-CRM test). Without the claim, 2; with one attempt instead of three, 2; without escaping, 1.</p>
</div>
""" + code(read(T + "EmailBeforeCommitTrapTest.java"), "java") + code(read(T + "OldSignupFlow.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SignupController.java", dwn("Validates and normalises the sign-up; reads it back with its email status.", "HTTP only.", "Side effects started from the controller.")),
    (J + "SignupService.java", dwn("Saves the sign-up, publishes <code>SignedUp</code>, joins the team.", "Knows no email, CRM or analytics.", "A sign-up that waits for partners.")),
    (J + "Listeners.java", dwn("The welcome email and the CRM, each <code>@Async</code> and after commit.",
        "Rolled-back sign-ups cause nothing; slow partners slow nothing.", "Mail for sign-ups that do not exist.",
        "<ul><li><code>@TransactionalEventListener(phase = AFTER_COMMIT)</code> holds the event until the commit, and drops it on rollback.</li><li><code>@Async</code> hands it to Spring's executor (virtual threads here).</li></ul>")),
    (J + "WelcomeMailer.java", dwn("Claims, sends, retries, dead-letters.",
        "The database decides that one email goes out.", "Duplicates and silent losses.",
        "<ul><li>The claim is <code>INSERT ... ON CONFLICT DO NOTHING</code>: zero rows means someone already has it.</li><li>Waits grow with each attempt; after the last, DEAD with the error.</li></ul>")),
    (J + "WelcomeEmail.java", dwn("The HTML template, UTF-8.", "User input escaped in the body, line breaks removed from the subject.", "HTML or header injection through a name.")),
    (J + "Mailbox.java", "<p>The simulated provider: records each message.</p>"),
    (J + "MailGateway.java", "<p>The one-method interface the mailer depends on.</p>"),
    (J + "CrmClient.java", "<p>The simulated CRM, with a configurable delay.</p>"),
    (J + "SignedUp.java", "<p>The event.</p>"),
    (M + "V1__signups_invites_emails.sql", "<p>Sign-ups, invites and the email claim table, with named constraints.</p>"),
    (M + "V2__demo_invites.sql", "<p>One invite with seats, one full.</p>"),
    ("src/main/resources/application.yaml", "<p>Virtual threads for <code>@Async</code>; retry attempts and waits; the CRM's delay.</p>"),
    (J + "WelcomeApplication.java", "<p>Entry point; <code>@EnableAsync</code>.</p>"),
]
tree = """stations/058-welcome-emails-with-spring-application-events/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/taskloom/welcome/
│   ├── SignupController.java   ├── SignupService.java   ├── SignedUp.java   ├── Listeners.java
│   ├── WelcomeMailer.java   ├── WelcomeEmail.java   ├── MailGateway.java   ├── Mailbox.java
│   ├── CrmClient.java   └── WelcomeApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__signups_invites_emails.sql, V2__demo_invites.sql
├── src/test/java/com/taskloom/welcome/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
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
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Virtual threads need JDK 21 or later.</p>
<h2>Try it yourself</h2>
<p>Make the CRM slow and feel that sign-up does not care:</p>
""" + code("""./mvnw spring-boot:run -Dspring-boot.run.arguments=--taskloom.crm.delay-ms=3000
curl -w "\\n%{time_total}s\\n" -X POST localhost:8080/signups -H "Content-Type: application/json" -d '{"email":"you@x.com","name":"You"}'""", "bash") + """
<p>The answer comes back long before the CRM's three seconds. Then remove <code>@Async</code> from <code>registerInCrm</code> and try again.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Emails for sign-ups that failed", "A plain <code>@EventListener</code>: it runs before the commit.", "<code>@TransactionalEventListener(phase = AFTER_COMMIT)</code>."],
    ["An after-commit listener never runs", "The event was published outside a transaction.", "Publish inside one, or set <code>fallbackExecution = true</code> on purpose."],
    ["Sign-up slow when a partner is slow", "The listener runs on the request's thread.", "<code>@Async</code> and <code>@EnableAsync</code>."],
    ["Two welcome emails", "The event arrived twice and nothing claimed it.", "Claim the email in the database first."],
    ["A foreign key error in an async listener", "It ran before the commit and the new row was not visible yet.", "After-commit, not a plain listener."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then what happens after the commit.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>SignupContractTest</code> ({cnt('SignupContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>EmailBeforeCommitTrapTest</code> ({cnt('EmailBeforeCommitTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>SignupDatabaseTest</code> ({cnt('SignupDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Messaging", "Duplicate-delivery, retry and dead-letter tests", f"<code>WelcomeEmailMessagingTest</code> ({cnt('WelcomeEmailMessagingTest')})", '<span class="pill ok">pass</span>'],
    ["This station's concepts", "Async listeners: a hanging CRM", f"<code>SlowCrmTest</code> ({cnt('SlowCrmTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Testing asynchronous code</h2>
<p>Async results arrive later, so the tests wait for them with Awaitility, up to 5 seconds, instead of sleeping a fixed time. "Never" is checked by watching for half a second that nothing arrives. The hanging CRM is a Mockito mock that blocks on a latch, released by the test.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "EmailBeforeCommitTrapTest.java", "<p>Written first: the old plain listener and today's after-commit one, for the same failed sign-up.</p>"),
    (T + "SignupContractTest.java", "<p>Sign-ups, invites, the email that follows, escaping, and every refusal.</p>"),
    (T + "WelcomeEmailMessagingTest.java", "<p>Duplicate events, a provider that recovers, and one that never does.</p>"),
    (T + "SlowCrmTest.java", "<p>A CRM that hangs, mocked with a latch.</p>"),
    (T + "SignupDatabaseTest.java", "<p>Named constraints and a rolled-back sign-up.</p>"),
    (T + "OldSignupFlow.java", "<p>The old flow and its plain listener, kept only in tests.</p>"),
    (T + "ApiTest.java", "<p>Shared setup, Awaitility helpers, parallel calls.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/taskloom/welcome/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=AnalyticsChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in (Java files and one migration), all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "An analytics listener", "Beginner-friendly", 20,
    "Record every committed sign-up in a new <code>analytics_events</code> table, from a third after-commit listener, without changing <code>SignupService</code>.",
    "the test in <code>AnalyticsChallengeTest</code> passes.",
    ["A new method in <code>Listeners</code>, and a migration.",
     "The rolled-back sign-up in the test must leave no row."],
    "challenge/AnalyticsChallengeTest.java", ["challenge/solution/V3__analytics_events.sql", "challenge/solution/Listeners.java"]) + challenge(2, "Send a dead email again", "Go deeper", 25,
    "Add <code>POST /signups/{id}/welcome-email/retry</code>: a DEAD email goes back to SENDING and is retried as before. Not DEAD: <code>409</code>; unknown: <code>404</code>.",
    "the test in <code>ResendChallengeTest</code> passes.",
    ["Move DEAD to SENDING with a conditional UPDATE: zero rows means it was not dead.",
     "Reuse the delivery loop; only the claim differs."],
    "challenge/ResendChallengeTest.java", ["challenge/solution/WelcomeMailer.java", "challenge/solution/SignupController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Events in memory, or an outbox?</h2>
<p>If the app restarts a millisecond after a sign-up commits, the in-memory event is gone and the welcome email never goes. Sketch a transactional outbox: a table written in the sign-up's transaction, and a poller that sends. What does it cost, and which of this station's tests would change?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, mapping"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test with the old plain listener as a real bean.</li>
<li>Publish one event from the service; move each side effect into its own after-commit, async listener.</li>
<li>Make the email idempotent with a claim row; add bounded retries and a dead-letter state.</li>
<li>Escape user input in the template; test asynchronous outcomes by waiting for them.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["After-commit, async listeners with a claim row", "Events in memory: lost if the app dies after commit.", '<span class="pill ok">Chosen</span>'],
    ["Plain <code>@EventListener</code>", "Runs before commit: mail for failed sign-ups.", '<span class="pill bad">The trap</span>'],
    ["Calling email and CRM directly in the service", "Every partner's speed and failure becomes the sign-up's.", '<span class="pill bad">The old code</span>'],
    ["Transactional outbox + poller", "A table and a job; nothing lost on a crash.", '<span class="pill warn">The next step</span>'],
    ["A message broker (Kafka, RabbitMQ)", "Durable and shareable across services; another system to run.", '<span class="pill warn">Across services</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Constraints"], [
    ["<code>signups</code>", "<code>signups_email_unique</code> (on <code>lower(email)</code>), <code>signups_invite_fk</code>"],
    ["<code>invites</code>", "<code>invites_seats_within_total</code>"],
    ["<code>sent_emails</code>", "<code>sent_emails_once</code> (primary key: one per sign-up and kind), <code>sent_emails_signup_fk</code>, <code>sent_emails_status_known</code>, <code>sent_emails_attempts_range</code>, <code>sent_emails_dead_has_error</code>"]]) + """
""" + code(read(M + "V1__signups_invites_emails.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>The crash window</dt><dd>Between commit and listener the event lives only in memory. A restart there loses the email. A nightly query for sign-ups with no <code>sent_emails</code> row finds them; an outbox removes the window.</dd>
<dt>Watch the dead letters</dt><dd>DEAD emails need a person. Alert when their count grows, and give support a way to send again (challenge 2).</dd>
<dt>Shutdown</dt><dd>Async tasks still running at shutdown are cut off. Spring's executor can wait for them (<code>spring.task.execution.shutdown.await-termination</code>).</dd>
<dt>Email deliverability</dt><dd>A real provider needs a verified sending domain (SPF, DKIM, DMARC) and a plain-text part next to the HTML.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("@EventListener vs @TransactionalEventListener?", "@EventListener runs immediately, inside publishEvent, in the publisher's transaction. @TransactionalEventListener waits for a transaction phase, by default AFTER_COMMIT, and is skipped if the transaction rolls back."),
    ("Why make the listener @Async?", "So its work, and any slowness or failure in it, does not delay the request. The trade-off: errors no longer reach the caller, so they must be recorded somewhere."),
    ("How do you stop duplicate emails?", "Claim the email in the database before sending: a unique key on (sign-up, kind) and INSERT ... ON CONFLICT DO NOTHING. Only the caller that inserted the row sends."),
    ("What is a dead letter?", "A message that failed every allowed attempt, set aside with its error for a person, instead of being retried forever or dropped."),
    ("Why escape a name in an email?", "It is user input placed into HTML. Unescaped, \"<script>\" or \"<a href>\" becomes markup in the email; a line break in a subject header can add headers."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You swapped in a plain listener and explained both failures."],
    ["Events", "After-commit and async.", "You know the crash window and the outbox."],
    ["Delivery", "Once, retried, dead-lettered.", "Support can resend a dead email."],
    ["Email", "Escaped, UTF-8.", "Subject header injection covered."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any side effect:</p>
<ul class="rules">
<li>Can it happen for a transaction that later rolls back?</li>
<li>Does the request wait for it?</li>
<li>What happens if it runs twice, or fails every time?</li>
<li>Is user input escaped for where it ends up (HTML, headers, SQL)?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
