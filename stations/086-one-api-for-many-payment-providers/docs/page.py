"""Station 086 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 86,
    "stack": "Spring Boot 4.1.1 · Java 25 · adapter pattern · provider selection by configuration · JdbcClient · PostgreSQL 17 · Testcontainers",
    "simulation": "Both payment providers, sim-alpha and sim-beta, are simulations inside the app, not real companies: a charge or refund is an entry in memory and nothing is charged. Their formats and error codes are made up to differ the way real providers do. The orders are demo data.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/paysetu/payments/"
T = "src/test/java/com/paysetu/payments/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Payment provider", "The company that actually takes the card or UPI payment for you.", "The bank behind a card machine.", "<code>sim-alpha</code>, <code>sim-beta</code> (simulated)"),
    ("Adapter", "A small class that translates between your code and one provider's own way of talking.", "A travel plug adapter.", "<code>AlphaProvider</code>, <code>BetaProvider</code>"),
    ("Failover", "Trying a second provider when the first one does not work.", "Calling a second taxi company.", "<code>paysetu.fallback</code>"),
    ("Timeout", "No answer in time. The request may or may not have been done.", "A courier who does not call back: was it delivered?", "<code>PaymentProvider.Unknown</code>"),
    ("Status check", "Asking the provider what happened to a payment, by your own reference.", "Phoning the courier with the tracking number.", "<code>lookup</code>"),
    ("Decline", "The provider's answer \"no\": not enough money, card blocked.", "The card machine saying \"declined\".", "<code>402</code>"),
]
STORY = [
    ("Four months to switch", "Paysetu wanted a second payment provider. Provider calls, rupee formats and error codes were spread across checkout, refunds and reports: switching took four months."),
    ("The quick failover", "The next version tried provider B whenever provider A \"failed\". One evening A was slow: it took the money, but its answer timed out. The code took that as a failure and charged B as well. Customers paid twice."),
    ("The fix", "Everything provider-specific moves into one adapter per provider, chosen by configuration. A timeout is not a failure: ask A what happened first, and try B only when A says it never charged."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">\"No answer\" is not \"no\". After a timeout, find out what happened before you try anyone else.</p>

<h2>What are we building?</h2>
<p>One payments API in front of two simulated providers, with one adapter each, picked by configuration, and refunds that always go back to the provider that took the money.</p>

<h2>An everyday analogy</h2>
<p>You send a parcel with courier A and the tracking page does not load. Sending a second parcel with courier B means the friend may get two. You check with A first: delivered, lost, or never picked up. Only \"never picked up\" makes B a safe choice.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Record</strong> the payment (one per order) before calling anyone.</li>
<li><strong>Charge</strong> through the primary provider's adapter.</li>
<li><strong>If it never arrived</strong> (connection refused), try the fallback. <strong>If it timed out</strong>, ask the primary what happened.</li>
<li><strong>Record the answer</strong>: succeeded, declined, or unknown if nobody can tell yet; never charge a second provider then.</li>
</ol>

<details class="qa check"><summary>Check yourself: sim-alpha says \"declined: insufficient funds\". Should the API try sim-beta?</summary><p>No. A decline is an answer about the customer's money, not a provider problem. Trying elsewhere would surprise the customer and the bank: <code>aDeclineIsAnAnswerNotAFailover</code>.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real providers.</strong> Both are simulations in the app, with made-up formats; nothing is charged.</li>
<li><strong>No webhooks.</strong> Real providers also report results later by calling you; challenge 3 is about that.</li>
<li><strong>No refund keys.</strong> A retried refund is a second refund here, capped by the amount; station 085 shows idempotency keys.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Paysetu</strong> (a fictional payments company): switching provider took four months because provider code was everywhere, and the first failover charged customers twice.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo rules of the simulations: an amount ending in 51 paise is declined for funds, ending in 05 declined by the card side; with sim-alpha, ending in 97 it charges and then times out, ending in 98 it refuses the connection. Payments ₹1 to ₹1,00,000.</p>
<ol class="gwt">
<li><b>Given</b> a healthy primary, <b>then</b> <code>201</code>, and the payment names the provider and its reference.</li>
<li><b>Given</b> a decline, <b>then</b> <code>402</code> with our reason, and no other provider is tried.</li>
<li><b>Given</b> a primary that cannot be reached, <b>then</b> the fallback takes the payment; neither reachable, <code>503</code>.</li>
<li><b>Given</b> a timeout, <b>then</b> the primary is asked first; if it cannot say, <code>202</code> \"unknown\" and no other provider is tried.</li>
<li><b>Given</b> the same order again, <b>then</b> the same answer and no new charge; another amount, <code>409</code>.</li>
<li><b>Given</b> a refund, <b>then</b> it goes to the provider that took the payment, never more than is left.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Nothing outside the adapters knows a provider's formats, states or codes.</li>
<li>The provider is chosen by configuration; a wrong name stops the app at start.</li>
<li>The database allows one payment per order and never more refunded than paid.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Hide each provider behind an adapter with one interface.</li>
<li>Select implementations by configuration.</li>
<li>Map each provider's errors to your own, and tell \"not sent\" from \"unknown\".</li>
<li>Check the status before failing over after a timeout.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/payments</code>", "<code>{orderId, amountPaise}</code>: take a payment. Safe to repeat with the same order."],
    ["<code>POST</code>", "<code>/payments/{id}/refunds</code>", "<code>{amountPaise}</code>: refund part or all, through the provider that took it."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Payment succeeded (also on a retry); refund done"],
    ['<span class="pill warn">202</span>', "Unknown: a provider may have charged and could not say; nothing else was tried"],
    ['<span class="pill warn">400</span>', "Order id not 3 to 40 letters, digits or dashes; amount missing, a fraction or out of range"],
    ['<span class="pill warn">402</span>', "Declined, with <code>declineReason</code>"],
    ['<span class="pill warn">404</span>', "No such payment"],
    ['<span class="pill warn">409</span>', "The order was sent with another amount; a refund larger than what is left, or of a payment that did not succeed"],
    ['<span class="pill warn">503</span>', "No provider could be reached (nothing charged); a refund's provider could not be reached (nothing refunded)"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. JSON bodies are indented for reading; <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-a-payment", "Case 1: a payment", "<b>Why:</b> sim-alpha is primary and healthy."),
    ("02-the-same-order-again", "Case 2: the same order again, in lower case", "<b>Why:</b> the same payment, the same answer; sim-alpha is not called."),
    ("03-the-same-order-another-amount", "Case 3: the same order, another amount", "<b>Why:</b> <code>409</code>: probably a bug in the caller."),
    ("04-a-decline", "Case 4: a decline (amount ending in 51 paise)", "<b>Why:</b> sim-alpha's <code>INSUFFICIENT_BALANCE</code> becomes our <code>INSUFFICIENT_FUNDS</code>, with <code>402</code>; sim-beta is not tried."),
    ("05-sim-alpha-charges-then-times-out", "Case 5: sim-alpha charges, then its answer times out (amount ending in 97)", "<b>Why:</b> the API asked sim-alpha, found the charge, and recorded it. sim-beta was not called."),
    ("06-sim-alpha-refuses-the-connection", "Case 6: sim-alpha refuses the connection (amount ending in 98)", "<b>Why:</b> it certainly never charged, so sim-beta took the payment."),
    ("07-refund-part-of-the-first", "Case 7: refund ₹1,000 of the first payment", "<b>Why:</b> through sim-alpha, which took it."),
    ("08-refund-the-sim-beta-payment", "Case 8: refund the payment sim-beta took", "<b>Why:</b> through sim-beta, although sim-alpha is primary."),
    ("09-refund-more-than-is-left", "Case 9: refund more than is left", "<b>Why:</b> <code>409</code>, saying how much is left."),
    ("10-refund-a-declined-payment", "Case 10: refund a declined payment", "<b>Why:</b> <code>409</code>."),
    ("11-an-order-id-with-a-space", "Case 11: an order id with a space", "<b>Why:</b> <code>400</code>."),
]) + """
<h2>The payments and refunds afterwards</h2>
""" + code(read("docs/captures/payments.txt").rstrip(), "text") + code(read("docs/captures/refunds.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A healthy primary", "<code>201</code>, sim-alpha's reference", "<code>aPaymentGoesToThePrimaryProvider</code>"],
    ["A decline", "<code>402</code>, our reason, no failover", "<code>aDeclineIsAnAnswerNotAFailover</code>"],
    ["Primary unreachable; both unreachable", "The fallback takes it; <code>503</code>", "<code>anUnreachablePrimaryFailsOverAndBothDownIs503</code>"],
    ["Charged, then a timeout", "Asked first: the charge is found, sim-beta not called", "<code>afterATimeoutTheApiAsksFirstAndFindsTheCharge</code>"],
    ["A timeout and the status check down", "<code>202</code> unknown, sim-beta not called", "<code>whenTheStatusCheckCannotSayEitherNoOtherProviderIsTried</code>"],
    ["A timeout before charging", "sim-alpha says no such charge: sim-beta takes it", "<code>whenTheProviderSaysItNeverChargedTheFallbackIsTried</code>"],
    ["The same order again", "The same body, one charge", "<code>theSameOrderTwiceIsOnePaymentAndOneCharge</code>"],
    ["Five at the same moment", "One payment, one charge", "<code>fiveRetriesAtTheSameMomentAreOneCharge</code>"],
    ["An unknown payment retried", "Still unknown; nothing sent again", "<code>anUnknownPaymentRetriedIsNotSentAgain</code>"],
    ["A refund of a sim-beta payment", "Goes to sim-beta, though sim-alpha is primary", "<code>aRefundGoesToTheProviderThatTookThePayment</code>"],
    ["Two refunds at once that cannot both fit", "<code>201</code> and <code>409</code>", "<code>twoRefundsAtOnceCannotBothFit</code>"],
    ["A refund the provider never got", "<code>503</code>, the amount freed", "<code>aRefundTheProviderNeverGotGivesTheAmountBack</code>"],
    ["Each provider's codes", "The same reasons", "<code>bothProvidersErrorsMapToTheSameReasons</code>"],
    ["A wrong provider name in configuration", "The app does not start", "<code>providersArePickedByNameAndAWrongNameStopsTheStart</code>"],
    ["Rules written by plain SQL", "Refused by named constraints", "<code>paymentRulesHoldWithoutJava</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Failing over to a second provider after a timeout when the first may already have charged.</p>
<ul>
<li><strong>The old code.</strong> The test runs its logic against the two simulations: sim-alpha charges and then times out, the old code calls that a failure and charges sim-beta. Both have a charge for one order.</li>
<li><strong>The API.</strong> The same timeout: the API asks sim-alpha about its reference, finds the charge and records it. sim-beta is never called. If sim-alpha cannot say, the payment stays unknown.</li>
</ul>
<p>While building, each part was undone once: no status check after a timeout turned 4 tests red; a timeout moving on to the next provider 2; a decline moving on 3; refunds through the current primary 1; no row lock on refunds 1; no handling of the same order sent at once 1; a failed refund not giving the amount back 1; another amount for the same order accepted 1; sim-alpha's funds code mapped wrong 3; sim-beta's code 62 forgotten 1; rupees sent without paise 8. The refund lock and the same-order race first turned no test red: see Tests.</p>
</div>
""" + code(read(T + "FailoverAfterTimeoutTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "PaymentController.java", dwn("The two endpoints.", "Checks the order id and amount, upper-cases the order id with <code>Locale.ROOT</code>, and answers with a status that follows the payment's state.", "A retry getting a different answer from the first try.")),
    (J + "Payments.java", dwn("Payments and refunds, without knowing any provider.",
        "Writes the payment before calling anyone; tries providers in order; after a timeout asks first; records the answer. Refunds reserve the amount under a row lock, call the provider that took the payment with no transaction open, then record the result.",
        "Double charges after a timeout, refunds sent to the wrong provider, refunds over the amount.",
        "<ul><li><code>NotSent</code> and <code>Unknown</code> are different exceptions on purpose: only the first allows another provider.</li><li>A decline ends the attempt: it is the customer's answer, not the provider's failure.</li><li>The limit, in a <code>shortcut:</code> comment: one status check straight after the timeout. A provider still processing could say \"no such charge\" too early; real integrations wait and ask again, or wait for the provider's webhook.</li></ul>")),
    (J + "PaymentProvider.java", dwn("The one interface every adapter implements.", "Charge, look up, refund; our outcomes and our two exceptions.", "Provider types leaking into checkout code.")),
    (J + "Providers.java", dwn("Picks adapters by name from configuration.", "Spring hands it every adapter; the names in <code>application.yaml</code> choose primary and fallback.", "A code change and a release to switch provider.", "<p>A wrong name fails the start with the known names in the message, not the first payment.</p>")),
    (J + "AlphaProvider.java", dwn("The sim-alpha adapter.", "Paise to rupee text (<code>BigDecimal</code>, exact), its states and word codes to our outcomes, its exceptions to ours.", "sim-alpha's format anywhere else.")),
    (J + "BetaProvider.java", dwn("The sim-beta adapter.", "Two-digit response codes to our outcomes; codes we do not know become <code>DECLINED_BY_PROVIDER</code>.", "A new code from the provider crashing checkout.")),
    (J + "AlphaApi.java", "<p>The simulated sim-alpha, shaped like an SDK. Tests set its faults; demo amounts trigger them for the captures. Nothing is charged.</p>"),
    (J + "BetaApi.java", "<p>The simulated sim-beta. Nothing is charged.</p>"),
    (M + "V1__payments_and_refunds.sql", dwn("Payments and refunds.", "One payment per order; refunds never more than the amount, and only on succeeded payments; known providers and states.", "A second payment for an order, or an over-refund, from any writer.")),
    ("src/main/resources/application.yaml", "<p>Which provider is primary and which is the fallback; fractions refused for paise.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "PaymentsApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/086-one-api-for-many-payment-providers/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/paysetu/payments/
│   ├── PaymentController.java   ├── Payments.java   ├── PaymentProvider.java   ├── Providers.java
│   ├── AlphaProvider.java   ├── BetaProvider.java   (adapters)
│   └── AlphaApi.java   ├── BetaApi.java   (the simulated providers)   └── PaymentsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__payments_and_refunds.sql
├── src/test/java/com/paysetu/payments/   (see Tests)
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
<p>Make sim-beta the primary with no fallback, by configuration only, and pay:</p>
""" + code("""./mvnw spring-boot:run -Dspring-boot.run.arguments="--paysetu.primary=sim-beta --paysetu.fallback="
curl -s -X POST http://localhost:8080/payments -H 'Content-Type: application/json' -d '{"orderId": "TRY-1", "amountPaise": 10000}'""", "bash") + """
<p>The answer says <code>"provider":"sim-beta"</code> and a reference like <code>T5001</code>. Start it with <code>--paysetu.primary=sim-omega</code> instead: the app stops at start with <code>No payment provider named sim-omega; known: [sim-alpha, sim-beta]</code>.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["The app stops at start: <code>No payment provider named ...</code>", "A name in <code>paysetu.primary</code> or <code>paysetu.fallback</code> has no adapter.", "Use a known name, or add the adapter (challenge 2)."],
    ["A payment stays <code>unknown</code>", "The provider timed out and its status check did not answer either.", "Ask again later (challenge 1); never charge another provider for it."],
    ["<code>Could not find a valid Docker environment</code>", "Docker is not running.", "Start Docker Desktop or the Docker service."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the adapters and the database behind it.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>PaymentContractTest</code> ({cnt('PaymentContractTest')}), <code>RefundTest</code> ({cnt('RefundTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>FailoverAfterTimeoutTrapTest</code> ({cnt('FailoverAfterTimeoutTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>PaymentDatabaseTest</code> ({cnt('PaymentDatabaseTest')}), <code>RefundConcurrencyTest</code> ({cnt('RefundConcurrencyTest')})", '<span class="pill ok">pass</span>'],
    ["Idempotency", "A replay test: the same request twice gives one effect", f"<code>PaymentReplayTest</code> ({cnt('PaymentReplayTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Adapters and selection by configuration", f"<code>ProviderAdapterTest</code> ({cnt('ProviderAdapterTest')}), <code>PrimaryFromConfigTest</code> ({cnt('PrimaryFromConfigTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">Two mutations changed no test at first. Without the row lock on refunds, the database's CHECK still refused the second refund, with an error instead of a <code>409</code>; <code>RefundConcurrencyTest</code> now sends two refunds at once with a 200 ms reservation (a trigger). Without handling the same order sent at once, the five parallel retries passed in one run and failed in another; a 200 ms insert (a trigger) now makes all five look before the first is written, and the mutation fails every time. Found while building.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "FailoverAfterTimeoutTrapTest.java", "<p>Written first: the old failover charging twice, and the API asking first.</p>"),
    (T + "PaymentContractTest.java", "<p>Payments through HTTP: success, decline, failover, bad requests.</p>"),
    (T + "PaymentReplayTest.java", "<p>The same order again, declined or unknown; five at once.</p>"),
    (T + "RefundTest.java", "<p>Part refunds, the right provider, a provider that cannot be reached.</p>"),
    (T + "RefundConcurrencyTest.java", "<p>Two refunds at once that cannot both fit.</p>"),
    (T + "ProviderAdapterTest.java", "<p>The adapters and the factory alone, without Spring.</p>"),
    (T + "PrimaryFromConfigTest.java", "<p>sim-beta as primary by a property alone.</p>"),
    (T + "PaymentDatabaseTest.java", "<p>Named constraints with plain SQL; a refund that cannot be recorded calls no provider.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: both simulations reset and no payments before each test.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/paysetu/payments/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=StatusCheckChallengeTest</code> (Docker must be running). The sim-gamma test does not compile until <code>GammaApi</code> exists.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Settle unknown payments", "Beginner-friendly", 25,
    "<code>POST /payments/{id}/status-check</code> asks the provider that took an <code>unknown</code> payment: charged becomes <code>succeeded</code>, declined <code>declined</code>, never seen <code>failed</code>. If it still cannot say, nothing changes. Other payments are returned as they are.",
    "the three tests in <code>StatusCheckChallengeTest</code> pass.",
    ["Use <code>providers.named(payment.provider())</code>, never the current primary.",
     "It never charges: a payment that never happened becomes <code>failed</code>, and the customer pays again with a new order."],
    "challenge/StatusCheckChallengeTest.java", ["challenge/solution/Payments.java", "challenge/solution/PaymentController.java"]) + challenge(2, "A third provider", "Go deeper", 30,
    "Add the simulated sim-gamma (<code>GammaApi</code>, yes/no answers with a reason word) and its adapter, then make it primary by configuration. <code>Payments</code> does not change.",
    "both tests in <code>ThirdProviderChallengeTest</code> pass.",
    ["An adapter is a <code>@Component</code> implementing <code>PaymentProvider</code>; <code>Providers</code> finds it by name.",
     "The database only allows known provider names: a V3 migration replaces <code>payments_known_provider</code>."],
    "challenge/ThirdProviderChallengeTest.java", ["challenge/solution/GammaApi.java", "challenge/solution/GammaProvider.java", "challenge/solution/V3__provider_sim_gamma.sql"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Routing and webhooks</h2>
<p>Paysetu wants UPI through one provider and cards through another, and to move traffic away from a provider whose success rate drops. Design the routing rule and where it lives. Then add webhooks: each provider calls Paysetu when a payment settles. How do you verify the call is genuine, match it to a payment, and settle an <code>unknown</code> payment from it, safely if it arrives twice?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old failover against two simulations.</li>
<li>Define <code>PaymentProvider</code> with our outcomes and two exceptions: not sent, unknown.</li>
<li>Write one adapter per provider, and the factory that reads the configuration.</li>
<li>Write the payment flow: record, try in order, ask after a timeout, record the answer. Then refunds to the provider that took the payment.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Adapters behind one interface, chosen by configuration; ask after a timeout", "One class per provider; payments can stay unknown for a while.", '<span class="pill ok">Chosen</span>'],
    ["Fail over on any error", "Double charges after timeouts.", '<span class="pill bad">The trap</span>'],
    ["Provider SDK calls in the payment code", "Every switch touches everything.", '<span class="pill bad">The old code</span>'],
    ["A payment orchestration service bought in", "Less code; another provider to depend on, and its own failure modes.", '<span class="pill warn">At larger scale</span>'],
    ["Wait for the webhook instead of asking", "No polling; the payment waits until the webhook arrives, and webhooks can be late or lost.", '<span class="pill warn">Use both</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>payments_order_once</code>", "UNIQUE", "One payment per order, for every writer and every retry."],
    ["<code>payments_refunds_within_amount</code>, <code>payments_refunds_only_when_paid</code>", "CHECKs", "Never more refunded than paid; nothing refunded on a payment that did not succeed."],
    ["<code>payments_succeeded_has_ref</code>, <code>payments_declined_has_reason</code>", "CHECKs", "A succeeded payment can be found at its provider; a decline says why."],
    ["<code>payments_known_provider</code>, <code>payments_status</code>", "CHECKs", "Only names and states the code knows."]]) + """
<p><strong>Transaction boundaries:</strong> the payment row is written and committed before any provider is called. No transaction is open during a provider call. A refund reserves its amount in one short transaction and records the result in another.</p>
""" + code(read(M + "V1__payments_and_refunds.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Unknown payments</dt><dd>Count them and settle them: a job that asks the provider again (challenge 1), and the provider's webhooks. An unknown payment should never be charged again elsewhere.</dd>
<dt>Your reference</dt><dd>Send the provider your own reference (here <code>pay_&lt;id&gt;</code>) and use the provider's idempotency feature where it has one, so a status check can find the charge and a resend does not charge twice.</dd>
<dt>Timeouts</dt><dd>Set connect and read timeouts on every provider client. A connect timeout means \"not sent\"; a read timeout means \"unknown\".</dd>
<dt>Reconciliation</dt><dd>Compare each provider's settlement report with your payments every day; that is where the last mismatches show up.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is the adapter pattern here?", "One interface for what payments need (charge, look up, refund), and one class per provider that translates to that provider's API, formats and errors. The rest of the code only sees the interface."),
    ("How is the provider chosen?", "By configuration: Spring hands all adapters to a factory, which picks by name. A wrong name fails the start, not the first payment."),
    ("When is failover safe?", "When the first provider certainly did not charge: the connection was refused, or the provider says it has no such charge. After a timeout, ask first."),
    ("Why not fail over on a decline?", "A decline is the bank's answer about the customer's money. Another provider would ask the same bank, or charge a different way the customer did not choose."),
    ("Where do refunds go?", "To the provider that took the payment, stored on the payment. The current primary may never have seen it."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Adapters", "One class per provider.", "Nothing outside the adapters names a provider's formats or codes."],
    ["Failover", "Tries the fallback when the primary is down.", "Never after a timeout without asking; never after a decline."],
    ["Refunds", "Refunds work.", "To the provider that took the payment, capped, under a lock, with no transaction open during the call."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("Failing over on a timeout",
     "\"Any trouble with one provider, and the next one takes the payment\" treats \"no answer\" as \"no\". When sim-alpha charged and then timed out, sim-beta charges again: the customer pays twice. When sim-alpha's status check is down too, the payment should stay unknown; here it goes to sim-beta.",
     "<code>afterATimeoutTheApiAsksFirstAndFindsTheCharge</code>, <code>whenTheStatusCheckCannotSayEitherNoOtherProviderIsTried</code>, <code>anUnknownPaymentRetriedIsNotSentAgain</code> and <code>theSimulationsDemoAmountsTriggerItsFaults</code> fail."),
    ("Refunds through the current primary",
     "\"Refunds go through our main provider\" works only while every payment was taken by it. A payment sim-beta took during an outage is refunded at sim-alpha, which has never seen that charge.",
     "<code>aRefundGoesToTheProviderThatTookThePayment</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate makes payments \"more resilient\": any exception from a provider, timeouts included, moves on to the next provider, and the status check is gone as \"one more call that can fail\". Refunds now always use the primary provider, \"our main one\". Read the file and list every problem before opening the findings.</p>
<p class="path">review/Payments.java</p>
""" + code(read("review/Payments.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">On a normal day the flawed version works: every payment succeeds at sim-alpha and every refund goes there. Both flaws need a bad evening, a slow provider or an outage, to show.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
