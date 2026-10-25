"""Station 108 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 108,
    "stack": "Spring Boot 4.1.1 · Java 25 · JdbcClient · transactional outbox with FOR UPDATE SKIP LOCKED · @Scheduled relay · RestClient · PostgreSQL 17 · Testcontainers",
    "simulation": "The wallet is simulated: a reward is a credit request to a small server (no money moves). The order and sign-up services are simulated by the tests and by curl. Customers, phones and devices are made up.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). Python 3 runs the simulated wallet in Try it yourself. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/basketo/referrals/"
T = "src/test/java/com/basketo/referrals/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Referral", "A customer invites someone new with their code; when it works out, they get a reward.", "\"Bring a friend\" at a gym.", "<code>POST /referrals</code>"),
    ("Qualifying event", "The moment that proves the referral was real: here, the new customer's first delivered order.", "The friend actually paying for a month.", "a delivered order of ₹500 or more"),
    ("Idempotent grant", "The same event twice gives one reward, not two.", "A stamp card stamped once per visit, however often you show it.", "one reward per referral and per order"),
    ("Device check", "One new account per phone handset, whatever SIM is in it.", "One free trial per household.", "<code>referrals_one_per_device</code>"),
    ("Transactional outbox", "Write \"send this\" in the same transaction as the change, and send it afterwards.", "An outgoing-mail tray: the letter is in the tray before the clerk goes home.", "<code>wallet_outbox</code>"),
    ("Dead letter", "A message given up on, kept for a person instead of retried for ever.", "The returned-mail shelf.", "<code>DEAD</code>"),
]
STORY = [
    ("₹100 for every friend", "Basketo pays ₹100 when a customer's code brings in someone new."),
    ("Sixty friends, one phone", "One person signed up sixty times on one phone with new SIM cards and his own code. The reward was paid at sign-up and only the phone number was checked: ₹6,000, and not one order."),
    ("The fix", "A referral is only recorded at sign-up; the reward comes with the new customer's first delivered order. One referral per device, one reward per referral and per order, in the database. The wallet credit leaves through an outbox, retried and never paid twice."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Pay for the outcome you want, not for the step that is easy to fake, and make paying twice impossible.</p>

<h2>What are we building?</h2>
<p>Referrals recorded at sign-up, rewarded once after a real delivered order, and credited to the referrer's wallet reliably.</p>

<h2>An everyday analogy</h2>
<p>A gym gives a free month to members who bring a friend, once the friend has paid their first month, once per friend, and only one trial per household.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Sign-up</strong>: the code, the phone and the device are checked; a pending referral is recorded.</li>
<li><strong>Delivered order</strong>: the order service reports it, perhaps more than once.</li>
<li><strong>Reward once</strong>: the first delivered order of ₹500 or more creates the reward and a wallet message, together.</li>
<li><strong>Send</strong>: a background relay sends the credit, retries when the wallet is busy, and parks it when it cannot.</li>
</ol>

<details class="qa check"><summary>Check yourself: why not credit the wallet in the same request?</summary><p>If the wallet is slow, the order service waits and retries; if the wallet succeeds and our commit then fails, money is credited with no record. The outbox makes the reward and the message one decision, and the sending a separate, repeatable step.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real wallet.</strong> A simulated one; no money moves.</li>
<li><strong>No sign-up or order system.</strong> Their calls are simulated.</li>
<li><strong>No fraud model.</strong> Device and phone checks only; rings of real people are challenge 3.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Basketo</strong> (a fictional grocery delivery app): referral rewards were farmed with new SIM cards. Rewards must follow real orders and be paid once.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo rules: ₹100 reward; first delivered order of at least ₹500; one referral per device; the wallet credit tried 5 times, 1, 2, 4 and 8 s apart.</p>
<ol class="gwt">
<li><b>Given</b> a valid code, a new phone and a new device, <b>then</b> <code>201</code>: a customer and a pending referral, nothing paid.</li>
<li><b>Given</b> an unknown code, a known phone, the code's own phone or device, or a device already used, <b>then</b> <code>404</code>, <code>409</code>, <code>422</code>, and no customer.</li>
<li><b>Given</b> a delivered order of ₹500 or more by a referred customer, <b>then</b> <code>201</code> and one reward; the same event again, or any later order, <code>200</code> with the same reward.</li>
<li><b>Given</b> an order that is not delivered, or is below ₹500, or a customer nobody referred, <b>then</b> no reward.</li>
<li><b>Given</b> a busy wallet, <b>then</b> the credit is retried with the same Idempotency-Key; a refused one, or one that never gets through, is <code>DEAD</code> for a person.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>One referral per referee and per device, one reward per referral and per order: named UNIQUE constraints.</li>
<li>The reward and its wallet message in one transaction.</li>
<li>No transaction open during a wallet call.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Reward after a qualifying event, not before.</li>
<li>Make a grant idempotent with keys and constraints.</li>
<li>Build a transactional outbox with retries, backoff and a dead state.</li>
<li>Test duplicate delivery, retries and dead letters against a real database.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Caller", "Purpose"], [
    ["<code>POST</code>", "<code>/referrals</code>", "sign-up service", "<code>{referralCode, name, phone, deviceId}</code>: a new customer with a pending referral."],
    ["<code>POST</code>", "<code>/orders/{id}/referral-reward</code>", "order service", "<code>{customerId, totalPaise, status}</code>: an order event, delivered at least once."],
    ["<code>GET</code>", "<code>/rewards/{id}</code>", "support", "The reward and its wallet delivery: status, attempts, last error."]]) + """
<h2>Answers</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "A customer signed up; a reward granted"],
    ['<span class="pill ok">200</span>', "An order event with no new reward: <code>ALREADY_REWARDED</code> (the same reward), <code>NOT_REFERRED</code>, <code>BELOW_MINIMUM</code>"],
    ['<span class="pill warn">400</span>', "Bad phone, device id or body"],
    ['<span class="pill warn">404</span>', "No such code or reward"],
    ['<span class="pill warn">409</span>', "The phone already has an account"],
    ['<span class="pill warn">422</span>', "Own code or device; a device already used; an order that is not delivered"],
    ['<span class="pill warn">401</span> / <span class="pill warn">403</span>', "Not signed in / another service's door"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against <code>docs/test-wallet.py</code>, a simulated wallet that credits once per Idempotency-Key. <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-a-new-customer-signs-up", "Case 1: Neel signs up with Priya's code", "<b>Why:</b> <code>201</code>, pending; the phone stored as +91 and ten digits."),
    ("02-the-same-phone-with-a-new-sim", "Case 2: the same handset, a new SIM", "<b>Why:</b> <code>422</code>: one referral per device."),
    ("03-priyas-own-number", "Case 3: Priya's own number", "<b>Why:</b> <code>422</code>: her own code."),
    ("04-a-number-that-has-an-account", "Case 4: Karan's number", "<b>Why:</b> <code>409</code>: not a new customer."),
    ("05-a-code-nobody-has", "Case 5: a made-up code", "<b>Why:</b> <code>404</code>."),
    ("06-the-first-order-is-placed", "Case 6: Neel places an order", "<b>Why:</b> <code>422</code>: placing is not the qualifying event."),
    ("07-a-delivered-order-below-500", "Case 7: a ₹450 order is delivered", "<b>Why:</b> below ₹500: no reward, the referral stays open."),
    ("08-a-delivered-order-of-650", "Case 8: a ₹650 order is delivered", "<b>Why:</b> <code>201</code>, ₹100 to Priya. The wallet will be busy once."),
    ("09-the-same-event-again", "Case 9: the order service sends the same event again", "<b>Why:</b> <code>200</code>, the same reward."),
    ("10-the-reward-after-a-retry", "Case 10: the reward, a moment later", "<b>Why:</b> <code>SENT</code> after 2 attempts."),
    ("11-a-credit-the-wallet-refused", "Case 11: another reward, refused by the wallet", "<b>Why:</b> <code>DEAD</code> after 1 attempt, with the reason, for a person."),
]) + """
<h2>What the wallet received</h2>
""" + code(read("docs/captures/wallet.txt").strip(), "text") + """
<p class="muted">A hand-written INSERT in <code>psql</code> that reuses Neel's device:</p>
""" + code(read("docs/captures/db-guard.txt").strip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["The old way: 60 new SIMs", "₹6,000 paid at sign-up", "<code>theOldWayPaysAtSignUpForEveryNewPhoneNumber</code>"],
    ["The API: 60 sign-ups at once, one device", "1 referral, 59 <code>422</code>, nothing paid until a delivered order", "<code>theApiTakesOneReferralPerDeviceAndPaysOnlyForADeliveredOrder</code>"],
    ["A sign-up", "<code>201</code>, pending, phone normalised", "<code>aNewCustomerSignsUpWithACodeAndNothingIsPaidYet</code>"],
    ["Unknown code, known phone, own phone, used device, bad input", "<code>404</code>, <code>409</code>, <code>422</code>, <code>422</code>, <code>400</code>; no customer", "<code>codesPhonesAndDevicesThatAreNotNewAreRefused</code>"],
    ["Placed, below ₹500, not referred, delivered", "<code>422</code>, no reward, no reward, <code>201</code>", "<code>onlyADeliveredFirstOrderOfAtLeastFiveHundredRupeesIsRewarded</code>"],
    ["Bad events, unknown reward, wrong service", "<code>400</code>, <code>404</code>, <code>401</code>/<code>403</code>", "<code>badEventsAre400UnknownRewards404AndEachServiceHasItsOwnDoor</code>"],
    ["The same event twice", "One reward, one wallet message, credited once", "<code>theSameEventTwiceGivesOneReward</code>"],
    ["A second delivered order", "The same reward", "<code>aSecondDeliveredOrderOfTheSameCustomerIsNotASecondReward</code>"],
    ["Twenty copies at once", "One <code>201</code>, nineteen <code>200</code>", "<code>twentyCopiesAtTheSameMomentGiveOneReward</code>"],
    ["A busy wallet", "Retried with the same key; sent", "<code>aBusyWalletIsTriedAgainWithTheSameKeyUntilItAnswers</code>"],
    ["A wallet that never answers well", "<code>DEAD</code> after 3 tries; nothing more sent", "<code>aWalletThatNeverAnswersWellParksTheCreditAsDead</code>"],
    ["A refused credit", "<code>DEAD</code> at once", "<code>aRefusedCreditIsDeadAtOnce</code>"],
    ["Applied but answered too late", "Sent again with the same key; paid once", "<code>aCreditAppliedButAnsweredTooLateIsSentAgainAndPaidOnce</code>"],
    ["Plain SQL against the rules", "Refused by named constraints", "<code>theRulesAreNamedConstraintsInTheDatabase</code>"],
    ["A referral that cannot be recorded", "No customer left behind", "<code>aSignUpThatCannotRecordItsReferralLeavesNoCustomerBehind</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Rewarding at sign-up instead of after a real order, with no idempotency.</p>
<ul>
<li><strong>The old way</strong> (on its own old tables): each sign-up with a code pays the referrer, and only the phone number must be new. Sixty SIM cards in one handset: sixty rewards, ₹6,000, no orders.</li>
<li><strong>The API.</strong> Sixty sign-ups at once from that handset: the first is accepted (nothing can tell it apart), the other fifty-nine are refused by the device rule, and nothing is paid until that one customer's ₹600 order is delivered.</li>
</ul>
<p>While building, each part was undone once: no device check in Java turned 1 test red (the constraint still refused the concurrent ones, the Java check gives the clear message for an existing account); no device constraint 3; no own-code check 1; no row lock 1; no minimum 1; no outbox row 8; a new key per attempt 2; no retries 3; refused credits retried 1; phones not normalised 2; any order status rewarded 1. One check was taken out as redundant: looking the reward up by order before the referral (the referral's status already answers it).</p>
</div>
""" + code(read(T + "ReferralAbuseTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "ReferralController.java", dwn("The endpoints.", "Validates input, normalises the phone, and turns only DELIVERED into a reward attempt.", "A reward for a placed, cancelled or returned order.")),
    (J + "Referrals.java", dwn("The rules.", "Sign-up checks and a pending referral; on a delivered order, the referral locked, then one reward and one wallet message together.", "Rewards at sign-up; two rewards for one event.",
        "<ul><li>The device check in Java gives a clear message; the UNIQUE constraint is what holds when sixty sign-ups arrive at once: the trap test sends them together.</li></ul>")),
    (J + "WalletRelay.java", dwn("The outbox relay.", "Claims due messages for a minute, sends with an Idempotency-Key, retries with doubling waits, parks as DEAD.", "A lost credit; a credit paid twice; a transaction held while the wallet thinks.",
        "<ul><li>The key only helps if the wallet honours it: agree it with the wallet team. The simulated one does.</li><li>Shortcut: the relay polls every second; at scale, a notification (LISTEN/NOTIFY or a message broker) wakes it instead.</li></ul>")),
    (J + "Phones.java", "<p>Indian mobile numbers in one form, so formatting cannot make an old number look new.</p>"),
    (J + "SecurityConfig.java", "<p>One sign-in per calling service; each has its own door.</p>"),
    (M + "V1__referrals_and_rewards.sql", dwn("The tables.", "Named UNIQUE and CHECK constraints for every rule above, and the outbox.", "Any writer breaking the rules.")),
    (M + "V2__demo_customers.sql", "<p>Priya and Karan.</p>"),
    ("src/main/resources/application.yaml", "<p>Reward, minimum, wallet address, retries.</p>"),
]
tree = """stations/108-referral-rewards-without-abuse/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/basketo/referrals/
│   ├── ReferralController.java   ├── Referrals.java   ├── WalletRelay.java   ├── Phones.java
│   └── SecurityConfig.java, ProblemResponses.java, ReferralsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__referrals_and_rewards.sql, V2__demo_customers.sql
├── src/test/java/com/basketo/referrals/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, simulated wallet, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Docker", "Docker Desktop (Windows, macOS) or Docker Engine (Linux), running", "<code>docker info</code>"],
    ["Python 3", "Only for the simulated wallet", "<code>python3 --version</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""docker compose up -d --wait          # PostgreSQL 17 on localhost:5432
python3 docs/test-wallet.py 9095 &   # the simulated wallet
./mvnw spring-boot:run               # the API on http://localhost:8080
./mvnw test                          # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d --wait
Start-Process python -ArgumentList 'docs/test-wallet.py','9095'
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Stop the simulated wallet, deliver an order, and watch the credit wait and retry; start the wallet again and it goes through:</p>
""" + code("""curl -u orders:orders-demo-pass -H 'Content-Type: application/json' \\
  -d '{"customerId":3,"totalPaise":65000,"status":"DELIVERED"}' localhost:8080/orders/40010/referral-reward
curl -u support:support-demo-pass localhost:8080/rewards/1   # attempts and last_error grow until the wallet is back""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["A reward stays <code>PENDING</code>", "The wallet is down or slow; the relay is waiting between tries.", "Check <code>last_error</code>; it goes out once the wallet answers."],
    ["A reward is <code>DEAD</code>", "The wallet refused it, or it never got through in 5 tries.", "Fix the cause; resending is challenge 2."],
    ["<code>422</code> for a genuine new customer", "Their handset was used for a referral before (a second-hand phone).", "Expected with this rule; support can sign them up without a code."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the relay and the database.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>ReferralContractTest</code> ({cnt('ReferralContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>ReferralAbuseTrapTest</code> ({cnt('ReferralAbuseTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>ReferralDatabaseTest</code> ({cnt('ReferralDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Messaging", "Duplicate delivery, retry and dead letter", f"<code>WalletMessagingTest</code> ({cnt('WalletMessagingTest')})", '<span class="pill ok">pass</span>'],
    ["Idempotency", "The same request twice gives one effect", f"<code>ReferralRewardReplayTest</code> ({cnt('ReferralRewardReplayTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">PostgreSQL 17 in Docker; a simulated wallet that credits once per key and answers as each test plans; the relay polls every 100 ms and retries 50 ms then 100 ms apart, so a dead letter is reached in under a second.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "ReferralAbuseTrapTest.java", "<p>Written first: sixty SIMs, the old way and the API.</p>"),
    (T + "ReferralContractTest.java", "<p>Sign-ups, order events, answers, doors.</p>"),
    (T + "ReferralRewardReplayTest.java", "<p>The same event again; twenty at once.</p>"),
    (T + "WalletMessagingTest.java", "<p>Retries, dead letters, a late answer.</p>"),
    (T + "ReferralDatabaseTest.java", "<p>Named constraints with plain SQL; a rollback.</p>"),
    (T + "TestWallet.java", "<p>The simulated wallet.</p>"),
    (T + "ApiTest.java", "<p>Shared setup.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/basketo/referrals/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=MonthlyLimitChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "A monthly limit", "Beginner-friendly", 25,
    "At most <code>basketo.referrals.max-rewards-per-month</code> rewards per referrer per calendar month, India time (2 in the test). Past it, the outcome is <code>MONTHLY_LIMIT</code>, nothing is paid, and the referral stays open for next month.",
    "both tests in <code>MonthlyLimitChallengeTest</code> pass.",
    ["Count the referrer's rewards since the start of this month in Asia/Kolkata.",
     "The referral row is already locked; lock the referrer's row too if two of their referrals can finish at once."],
    "challenge/MonthlyLimitChallengeTest.java", ["challenge/solution/Referrals.java"]) + challenge(2, "Send a dead credit again", "Go deeper", 30,
    "Support fixes the cause of a <code>DEAD</code> credit and asks for it to be sent again: <code>POST /rewards/{id}/delivery-retry</code> (support only) answers <code>202</code> and puts it back in the outbox with fresh attempts and the same key; a credit that is not dead is <code>409</code>; an unknown one <code>404</code>.",
    "both tests in <code>RetryDeadCreditChallengeTest</code> pass.",
    ["One conditional UPDATE: <code>... WHERE reward_id = ? AND status = 'DEAD'</code>.",
     "Keep the Idempotency-Key: the wallet may have applied it after all."],
    "challenge/RetryDeadCreditChallengeTest.java", ["challenge/solution/Referrals.java", "challenge/solution/ReferralController.java", "challenge/solution/SecurityConfig.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>A ring of real people</h2>
<p>Ten friends each sign up on their own phones with each other's codes, place one ₹500 order, return it after the reward, and move on. Every rule here passes. Which signals would you add (returns, payment cards, delivery addresses), when would a reward wait for a return window, and who reviews the rest without punishing honest referrers?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: sixty sign-ups from one device.</li>
<li>Move the reward to the delivered order; record only a referral at sign-up.</li>
<li>Constraints for each \"once\"; a row lock for the decision.</li>
<li>An outbox and a relay for the wallet; retries, backoff, dead.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Outbox table + relay", "A table and a background job.", '<span class="pill ok">Chosen</span>'],
    ["Call the wallet inside the transaction", "A slow wallet holds the transaction; a commit failure after a credit loses the record.", '<span class="pill bad">Avoid</span>'],
    ["Call the wallet after commit, no outbox", "A crash between commit and call loses the credit.", '<span class="pill bad">Avoid</span>'],
    ["A message broker", "Another system to run; still needs an outbox to publish reliably.", '<span class="pill warn">At scale</span>'],
    ["Reward at sign-up", "Pays for the step that is easy to fake.", '<span class="pill bad">The trap</span>']]) + """
<h2>Database design</h2>
""" + table(["Constraint", "Rule", "Why"], [
    ["<code>referrals_one_per_referee</code>, <code>referrals_one_per_device</code>", "UNIQUE", "One referral per new customer, and per handset."],
    ["<code>referrals_not_self</code>", "referrer ≠ referee", "No referring yourself, even by SQL."],
    ["<code>rewards_one_per_referral</code>, <code>rewards_one_per_order</code>", "UNIQUE", "One reward, whatever arrives twice."],
    ["<code>customers_phone_unique</code>", "UNIQUE on the normalised number", "One account per number."],
    ["<code>wallet_outbox_one_per_reward</code>, <code>wallet_outbox_status</code>", "UNIQUE; known states", "One credit per reward."]]) + """
<p><strong>Transaction boundaries:</strong> a sign-up creates the customer and the referral together; a delivered order locks the referral and writes the reward, the referral's new status and the outbox row together; the relay claims rows in one short transaction, calls the wallet with none open, and records the result in another.</p>
""" + code(read(M + "V1__referrals_and_rewards.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["14. Operations: metric, alert, rollback, runbook, failure drill", "15. Real-world considerations"],
               "What changes when this runs for real.") + """
<h2>Real-world considerations</h2>
<dl class="facts">
<dt>Watching the outbox</dt><dd>Alert on any <code>DEAD</code> row, and on the oldest <code>PENDING</code> row passing a few minutes: both mean customers waiting for money they were promised.</dd>
<dt>Device ids</dt><dd>An app-generated id survives SIM changes but not a reinstall on some phones; combine it with other signals rather than trusting it alone.</dd>
<dt>Returns</dt><dd>A reward for an order later returned is the next loophole: hold rewards until the return window closes (challenge 3).</dd>
<dt>Cleaning up</dt><dd>Sent outbox rows can be deleted after a few weeks; keep rewards for accounting.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("When should a referral reward be paid?", "After the event that shows the referral was real (a delivered first order), not at sign-up."),
    ("How do you make a reward grant idempotent?", "Key it on what must be unique (one per referral, one per order) with database constraints, and lock the row while deciding."),
    ("What is a transactional outbox?", "Writing the message to send in the same transaction as the change, then sending it from that table, so neither is lost without the other."),
    ("How do retries avoid paying twice?", "The same idempotency key on every attempt, and a receiver that honours it."),
    ("What is a dead letter?", "A message that will not succeed by retrying (refused, or out of attempts), parked with its reason for a person."),
    ("Why not hold a transaction while calling the wallet?", "It holds a database connection and locks for as long as the wallet takes."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Abuse", "Reward after an order.", "Every \"once\" is a constraint, and you can name what still gets through."],
    ["Delivery", "The credit is sent.", "Outbox, retries with backoff, dead letters, idempotency keys, no transaction during calls."],
    ["Tests", "Happy path.", "Duplicates, concurrency, retries, dead letters and late answers, against a real database."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("No lock on the referral",
     "\"The unique constraint already stops a second reward\": it stops the second row, as an error. Two deliveries of the same event at once both read the referral as pending; one wins, the other gets a 500, and the order service retries something that had already succeeded.",
     "<code>twentyCopiesAtTheSameMomentGiveOneReward</code> fails: 500s for copies that should be 200s."),
    ("The wallet called inside the transaction",
     "\"Why a table and a scheduler? Call the wallet when the reward is made\": while the wallet thinks, the transaction and its locks are held; when it is down, the reward is rolled back and the order service is told to retry; and when the wallet succeeds but the commit fails, the money is credited with no reward on record.",
     "All four <code>WalletMessagingTest</code> tests fail, and <code>theSameEventTwiceGivesOneReward</code>, <code>onlyADeliveredFirstOrderOfAtLeastFiveHundredRupeesIsRewarded</code> and <code>theApiTakesOneReferralPerDeviceAndPaysOnlyForADeliveredOrder</code> with them: a busy wallet fails the reward itself, and there is no delivery record to look at."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate \"simplifies\" the reward: \"the constraint is enough without a lock, and the outbox is a lot of machinery for one HTTP call\". Read the file and list every problem before opening the findings.</p>
<p class="path">review/Referrals.java</p>
""" + code(read("review/Referrals.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">With a healthy wallet and one event at a time, the flawed version pays the right people the right amount.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
