"""Station 087 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 87,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Security 7 (HTTP Basic) · card-on-file tokens (simulated network) · JdbcClient · PostgreSQL 17 · Testcontainers",
    "simulation": "The card network's token service is a simulation inside the app (SimNetwork): its \"vault\" is a map that stands for the network's side, and nothing is charged. The cards are standard test numbers that belong to nobody; the customers are demo data.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/paysetu/cards/"
T = "src/test/java/com/paysetu/cards/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Card number (PAN)", "The 13 to 19 digits on the card. Whoever has it, with the expiry, can often pay.", "The key to a house.", "sent once to the network, never kept"),
    ("Token", "A stand-in for the card that only works for one merchant, through the network.", "A hotel key card that opens one room.", "<code>tkn_</code> + 20 letters"),
    ("Card network", "Visa, Mastercard, RuPay: they run the card system and its token service.", "The company that makes the hotel's lock system.", "<code>SimNetwork</code> (simulated)"),
    ("Cryptogram", "A one-time value the network gives for each payment with a token.", "A one-time password.", "<code>cryptogram</code>"),
    ("Consent", "The customer saying yes to saving the card, each time.", "Ticking \"save this card\".", "<code>consent: true</code>"),
    ("PCI DSS scope", "Every system that touches card numbers must meet the card industry's security standard.", "Every room the key passes through needs a lock.", "kept small by never holding the number"),
]
STORY = [
    ("One-click checkout", "A shop on Paysetu kept customers' card numbers for one-click checkout. A developer added a column \"just for retries\", so a failed payment could be sent again."),
    ("The breach", "An attacker copied a database backup. Thousands of card numbers with expiry dates were in it. RBI's card-on-file rules, in force since 1 October 2022, allow only card issuers and networks to store card data at all."),
    ("The fix", "The card number goes once to the card network's token service, which keeps it and returns a token. The shop keeps the token, the last four digits and the expiry. Payments and retries use the token."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">The safest card number is the one you never had. Keep a token; let the network keep the card.</p>

<h2>What are we building?</h2>
<p>Save a card as a network token (with the customer's consent), list saved cards, and pay with one. No card number is kept anywhere in our tables or logs.</p>

<h2>An everyday analogy</h2>
<p>A hotel does not keep a copy of your house key. It gives you a key card that opens one room, for a while, and can be switched off. Losing it is a nuisance, not a disaster.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Check</strong> the number's shape and check digit, and that the customer said yes.</li>
<li><strong>Send</strong> it to the network's token service; get a token, the network and the last four digits back.</li>
<li><strong>Keep</strong> only the token and what the customer needs to recognise the card. Forget the number.</li>
<li><strong>Pay</strong> with the token and a fresh one-time cryptogram from the network.</li>
</ol>

<details class="qa check"><summary>Check yourself: a payment is declined and the customer taps \"try again\". Do you need the card number?</summary><p>No. The retry asks the network for a new cryptogram for the same token: <code>afterSavingPayingAndRetryingTheCardNumberIsNowhereInOurDatabaseOrLog</code>. \"Just for retries\" was never a reason to keep it.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>Not a real network.</strong> The token service is simulated; real ones are reached through a payment aggregator, with their own APIs.</li>
<li><strong>Not a checkout page.</strong> In real life the number is often typed into the aggregator's own form, so it never reaches the merchant at all (challenge 3).</li>
<li><strong>Not legal advice.</strong> The rules are summarised; read RBI's circulars and your aggregator's terms.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Paysetu</strong> (a fictional payments company): a merchant's breach exposed card numbers kept for one-click checkout, which RBI's rules do not allow merchants to store.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo customers: asha (customer 1) and rohan (customer 2), password <code>name-demo-pass</code>. Demo rules of the simulation: cards starting 4 are VISA, 5 MASTERCARD, 6 RUPAY; an amount ending in 51 paise is declined.</p>
<ol class="gwt">
<li><b>Given</b> a valid card and consent, <b>then</b> <code>201</code> with the network, last four digits and expiry; no number, no token in the answer.</li>
<li><b>Given</b> a wrong check digit, a wrong length or no consent, <b>then</b> <code>400</code>, and the number is not repeated in the answer or the log.</li>
<li><b>Given</b> an expired or unsupported card, <b>then</b> <code>422</code>.</li>
<li><b>Given</b> a payment with a saved card, <b>then</b> the token pays; a retry of the same order gets the same payment.</li>
<li><b>Given</b> another customer's cards, <b>then</b> <code>403</code> for their path, <code>404</code> for their card id; no sign-in, <code>401</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>No card number in any table, log line, error message or object's printout.</li>
<li>The database refuses a card number in the token and last-four columns.</li>
<li>The customer id comes from the sign-in, never from the request alone.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Explain card-on-file tokenisation and why it shrinks what a breach can take.</li>
<li>Keep sensitive input out of fields, columns, logs and error messages.</li>
<li>Handle a token's life: create, use with a cryptogram, expire, delete.</li>
<li>Test that sensitive data is absent, with a test that can fail.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/customers/{id}/saved-cards</code>", "<code>{cardNumber, expiryMonth, expiryYear, consent}</code>: save a card as a token."],
    ["<code>GET</code>", "<code>/customers/{id}/saved-cards</code>", "The customer's saved cards: network, last four, expiry."],
    ["<code>POST</code>", "<code>/payments</code>", "<code>{orderId, savedCardId, amountPaise}</code>: pay with a saved card. Safe to repeat with the same order."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span> / <span class="pill ok">201</span>', "Listed / saved, or paid (also on a retry)"],
    ['<span class="pill warn">400</span>', "Card number of the wrong shape, length or check digit; no consent; a bad order id or amount"],
    ['<span class="pill warn">401</span>', "No sign-in, or a wrong password"],
    ['<span class="pill warn">402</span>', "Declined"],
    ['<span class="pill warn">403</span>', "Another customer's saved cards"],
    ['<span class="pill warn">404</span>', "No such saved card for this customer (also someone else's)"],
    ['<span class="pill warn">409</span>', "The order id belongs to another customer"],
    ['<span class="pill warn">422</span>', "The network refuses the card (expired, unsupported), or the saved card has expired"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. JSON bodies are indented for reading; <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-asha-saves-a-card", "Case 1: Asha saves a card", "<b>Why:</b> spaces are allowed; the answer has no number and no token."),
    ("02-asha-lists-her-cards", "Case 2: Asha lists her cards", "<b>Why:</b> what she needs to recognise it."),
    ("03-rohan-lists-ashas-cards", "Case 3: Rohan asks for Asha's cards", "<b>Why:</b> <code>403</code>, before anything is read."),
    ("04-no-sign-in", "Case 4: no sign-in", "<b>Why:</b> <code>401</code>."),
    ("05-a-wrong-check-digit", "Case 5: a mistyped number", "<b>Why:</b> the check digit catches it; the number is not repeated."),
    ("06-no-consent", "Case 6: consent false", "<b>Why:</b> <code>400</code>; nothing is sent to the network."),
    ("07-asha-pays-with-her-saved-card", "Case 7: Asha pays with her saved card", "<b>Why:</b> the token and a fresh cryptogram."),
    ("08-the-same-order-again", "Case 8: the same order again", "<b>Why:</b> the same payment."),
    ("09-rohan-pays-with-ashas-card", "Case 9: Rohan tries Asha's card id", "<b>Why:</b> <code>404</code>: not his, and not confirmed to exist."),
    ("10-a-decline", "Case 10: a decline (amount ending in 51 paise)", "<b>Why:</b> <code>402</code>."),
]) + """
<h2>What is stored</h2>
""" + code(read("docs/captures/saved-cards.txt").rstrip(), "text") + code(read("docs/captures/payments.txt").rstrip(), "text") + """
<p class="muted">Searched by <code>docs/capture.sh</code> with <code>pg_dump --data-only | grep -c</code>, after the captures above:</p>
""" + code(read("docs/captures/dump-search.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Save VISA, MASTERCARD, RUPAY; list", "Network, last four, expiry; own cards only", "<code>aSavedCardShowsOnlyWhatTheCustomerNeedsToRecogniseIt</code>"],
    ["Wrong check digit, too short, dashes, month 13, no consent", "<code>400</code>", "<code>badCardsAre400AndRefusedOnesAre422</code>"],
    ["Expired or unsupported card", "<code>422</code> from the network", "<code>badCardsAre400AndRefusedOnesAre422</code>"],
    ["Pay; a decline", "<code>201</code>; <code>402</code>", "<code>aPaymentWithASavedCardUsesItsToken</code>"],
    ["The same order twice", "One payment, the same body", "<code>theSameOrderTwiceIsOnePayment</code>"],
    ["A retry after the card expired", "The first answer, not a <code>422</code>", "<code>aRetryAfterTheCardExpiredStillGetsTheFirstAnswer</code>"],
    ["The last minute of the expiry month, in IST", "Still valid; one second later <code>422</code>", "<code>anExpiredSavedCardIs422</code>"],
    ["No sign-in, wrong password", "<code>401</code>", "<code>withoutAValidSignInEverythingIs401</code>"],
    ["Another customer's path; their card id", "<code>403</code>; <code>404</code>", "<code>oneCustomerCannotSeeOrAddToAnothersCards</code>"],
    ["Another customer's order id", "<code>409</code>, never their payment", "<code>anOrderIdBelongsToOneCustomer</code>"],
    ["Injection-shaped and 5,000-digit input", "<code>400</code> before anything runs", "<code>maliciousInputIsRefusedBeforeAnythingRuns</code>"],
    ["A card number written by plain SQL", "Refused by the shape constraints", "<code>aCardNumberCannotBeStoredAsATokenOrALast4</code>"],
    ["The saved card cannot be recorded", "The token is deleted at the network", "<code>aCardThatCannotBeRecordedLeavesNoTokenAtTheNetwork</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Keeping the card number \"just for retries\", which breaks RBI's rules and pulls every system into PCI scope.</p>
<ul>
<li><strong>The search can find it.</strong> The test searches every text column of every table for the digits. On a table shaped like the old design it finds <code>old_saved_cards.card_number</code>: the search is able to fail.</li>
<li><strong>Nowhere now.</strong> After saving a card, a declined payment, a retry, a save without consent and a mistyped number, the same search finds nothing, and the application's log does not contain the number. The network's vault does: that is the network's side.</li>
<li><strong>Printing the request.</strong> A Java record's default <code>toString</code> prints every field, so one log line or a debugger shows the number. The request masks it.</li>
</ul>
<p>While building, each part was undone once: no check digit turned 2 tests red; no length check 1; the number in the error message 1; the number stored as the token 8; no owner check on the path 1; any customer's card id 1; another customer's order id answered 1; no expiry check 1; the expiry month in UTC 1; the token left at the network when saving failed 1; no consent 1; the default <code>toString</code> 1; no replay check before the card checks 1.</p>
</div>
""" + code(read(T + "CardNumberStorageTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SecurityConfig.java", dwn("Who may call what.", "HTTP Basic with demo customers; saved cards and payments need the CUSTOMER role; everything else is refused.", "Anyone reading anyone's saved cards.")),
    (J + "CardController.java", dwn("The three endpoints.",
        "Checks the number's shape, the expiry and consent; makes sure the path's customer is the signed-in one; masks the number in <code>toString</code>.",
        "A card number in a log line, and one customer's cards in another's app.",
        "<ul><li>Someone else's customer id is <code>403</code>; someone else's card id in a payment is <code>404</code>, so it does not confirm that the card exists.</li><li>The record overrides <code>toString</code>: by default it prints every field.</li></ul>")),
    (J + "Cards.java", dwn("Saving, listing and paying.",
        "The number is a parameter that goes to the network and nowhere else; the payment row is written before the network is called; expiry is checked by the month in IST.",
        "Card numbers in the database, double charges on a double tap.",
        "<ul><li>If the saved card cannot be recorded, the token is deleted at the network, so nothing usable is left behind.</li><li>A retry of an order is answered before the card checks: the payment happened, whatever the card's state is now.</li></ul>")),
    (J + "Customers.java", "<p>The customer id of the signed-in user, from the database.</p>"),
    (J + "SimNetwork.java", "<p>The simulated network's token service: provisions tokens, issues one-time cryptograms, authorises. Its vault stands for the network's side. Nothing is charged.</p>"),
    (J + "ProblemResponses.java", "<p><code>401</code> and <code>403</code> in the same problem shape as other errors.</p>"),
    (M + "V1__customers_saved_cards_payments.sql", dwn("Customers, saved cards and payments.",
        "Shape rules on the token and the last four digits make a card number impossible to store in them.",
        "A \"temporary\" column or a script putting the number back.")),
    (M + "V2__demo_customers.sql", "<p>Two customers.</p>"),
    ("src/main/resources/application.yaml", "<p>Database connection; fractions refused for whole-number fields.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "CardsApplication.java", "<p>Entry point, and the <code>Clock</code> expiry is checked against.</p>"),
]
tree = """stations/087-saving-cards-with-network-tokens/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/paysetu/cards/
│   ├── SecurityConfig.java   ├── CardController.java   ├── Cards.java   ├── Customers.java
│   └── SimNetwork.java   ├── ProblemResponses.java   └── CardsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__customers_saved_cards_payments.sql, V2__demo_customers.sql
├── src/test/java/com/paysetu/cards/   (see Tests)
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
<p>Save a card, then search a full dump of the database for its number:</p>
""" + code("""curl -s -u asha:asha-demo-pass -X POST http://localhost:8080/customers/1/saved-cards -H 'Content-Type: application/json' -d '{"cardNumber": "4111 1111 1111 1111", "expiryMonth": 12, "expiryYear": 2028, "consent": true}'
docker compose exec -T postgres pg_dump -U paysetu -d paysetu --data-only | grep -c 4111111111111111""", "bash") + """
<p>The count is <code>0</code>, as in <code>docs/captures/dump-search.txt</code>. The search over every text column in <code>CardNumberStorageTrapTest</code> does the same inside the tests.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["A card number in a log line", "Something printed the request: a record's default <code>toString</code> shows every field.", "Mask it in <code>toString</code>, and never log request bodies with card data."],
    ["<code>401</code> with the right password", "The user is not one of the demo users.", "Use asha or rohan with <code>name-demo-pass</code>."],
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>SavedCardContractTest</code> ({cnt('SavedCardContractTest')}), <code>TokenPaymentTest</code> ({cnt('TokenPaymentTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>CardNumberStorageTrapTest</code> ({cnt('CardNumberStorageTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>CardDatabaseTest</code> ({cnt('CardDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, one user accessing another user's data, malicious input", f"<code>CardSecurityTest</code> ({cnt('CardSecurityTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">Two tests were corrected while building. The \"too short\" card number first failed its check digit, so removing the length check changed nothing; it is now a short number with a valid check digit. Removing the replay check before the card checks changed nothing either, because the unique order id returned the same payment; a retry after the card expired now shows the difference.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "CardNumberStorageTrapTest.java", "<p>Written first: the search over every text column, and the log.</p>"),
    (T + "SavedCardContractTest.java", "<p>Saving and listing through HTTP; bad and refused cards.</p>"),
    (T + "TokenPaymentTest.java", "<p>Paying with a token, retries, expiry at the IST month boundary.</p>"),
    (T + "CardSecurityTest.java", "<p>401, 403, other customers' cards and orders, malicious input.</p>"),
    (T + "CardDatabaseTest.java", "<p>Shape rules and named constraints with plain SQL; a card that cannot be recorded.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the test clock, the network simulation and customers before each test, request helpers, test card numbers.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/paysetu/cards/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=DeleteSavedCardChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Delete a saved card", "Beginner-friendly", 25,
    "<code>DELETE /customers/{id}/saved-cards/{cardId}</code>: the token is deleted at the network, the card leaves the list and cannot pay. Deleting it again is still <code>204</code>; another customer's path <code>403</code>; an unknown card <code>404</code>.",
    "both tests in <code>DeleteSavedCardChallengeTest</code> pass.",
    ["The security rules match paths: <code>/customers/*/saved-cards/*</code> needs adding.",
     "Mark the row deleted rather than removing it: payments still point at it."],
    "challenge/DeleteSavedCardChallengeTest.java", ["challenge/solution/Cards.java", "challenge/solution/CardController.java", "challenge/solution/SecurityConfig.java"]) + challenge(2, "Events from the network", "Go deeper", 35,
    "<code>POST /network/token-events</code>, signed in as the network (<code>sim-network</code>): <code>UPDATED</code> with a new expiry when the bank re-issues the card (the token stays, and payments work again), <code>SUSPENDED</code> and <code>RESUMED</code>. Customers get <code>403</code>.",
    "the three tests in <code>TokenEventsChallengeTest</code> pass.",
    ["A new role, <code>NETWORK</code>, and a user for it.",
     "A V3 migration lets <code>saved_cards_status</code> hold <code>suspended</code>; a suspended card answers <code>422</code>, not <code>404</code>."],
    "challenge/TokenEventsChallengeTest.java", ["challenge/solution/Cards.java", "challenge/solution/CardController.java", "challenge/solution/SecurityConfig.java", "challenge/solution/V3__suspended_tokens.sql"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Never even seeing the number</h2>
<p>Here the card number still passes through Paysetu's API on its way to the network. Redesign checkout so it never does: the customer types it into the aggregator's own form or SDK, and Paysetu only receives a token. What changes for PCI DSS scope, for logs and for support? And for guest checkout without saving: what may be kept, and for how long?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: a search over every text column, shown to find a number in an old-design table.</li>
<li>Save: check shape, check digit and consent; send to the network; keep the token and display data only.</li>
<li>Pay: write the payment row, get a cryptogram, authorise, record.</li>
<li>Lock down who sees what, and make the database refuse a number in the card columns.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Network tokens; keep token, last four, expiry", "Depends on the network and aggregator for every payment.", '<span class="pill ok">Chosen</span>'],
    ["Keep the card number \"just for retries\"", "Breaks RBI's rules; a breach takes the cards; every system in PCI scope.", '<span class="pill bad">The trap</span>'],
    ["Keep it encrypted", "Still card data stored by the merchant; the key is one more secret to lose.", '<span class="pill bad">Not allowed for merchants</span>'],
    ["Aggregator's hosted form or SDK", "The number never reaches Paysetu; less control over the page.", '<span class="pill ok">Better still (challenge 3)</span>'],
    ["Ask for the card every time", "Safe, but no one-click checkout.", '<span class="pill warn">Fine for guests</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>saved_cards_token_shape</code>, <code>saved_cards_last4_shape</code>", "CHECKs", "A card number cannot be written into these columns by any writer."],
    ["<code>saved_cards_token_unique</code>", "UNIQUE", "One saved card per token."],
    ["<code>payments_order_once</code>", "UNIQUE", "One payment per order, written before the network is called."],
    ["<code>payments_succeeded_has_ref</code>", "CHECK", "A succeeded payment can be found at the network."]]) + """
<p><strong>Transaction boundaries:</strong> no transaction is open while the network is called. A saved card is one insert after the token exists; if it fails, the token is deleted at the network.</p>
""" + code(read(M + "V1__customers_saved_cards_payments.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Rules</dt><dd>RBI's card-on-file tokenisation rules, in force since 1 October 2022, allow only card issuers and networks to store card data; merchants keep tokens, with the customer's consent. Read the circulars themselves and your aggregator's terms.</dd>
<dt>Logs and tools</dt><dd>Request logging, error trackers, APM and support tools copy bodies by default in many setups. Mask card fields before anything leaves the process.</dd>
<dt>Token life</dt><dd>Networks tell you when a card is re-issued or a token suspended (challenge 2); a token outlives the plastic card, which is part of why checkout keeps working.</dd>
<dt>Scope</dt><dd>Every system the number passes through is in PCI DSS scope. Fewer systems, smaller audits, smaller breaches.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is a network token?", "A stand-in for a card number, issued by the card network for one merchant. It is useless elsewhere, can be suspended or deleted, and survives a card re-issue."),
    ("Why not keep the card number encrypted?", "In India, RBI's rules do not allow merchants to store card data at all. Elsewhere it keeps you in PCI scope, and a breach of the key exposes everything."),
    ("How do you retry a declined payment without the card number?", "With the token: ask the network for a new one-time cryptogram and send the payment again."),
    ("How do you prove card numbers are not stored or logged?", "Search every text column and the captured log for the digits in a test, and show the search finds them in a table built the old way."),
    ("Why 404 for someone else's card id but 403 for their path?", "The path names the customer, which the caller already knows. A card id they do not own should not be confirmed to exist."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Card data", "No card number column.", "Not in logs, errors, toString or any table, proven by a search that can fail."],
    ["Access", "401 and 403.", "404 for others' card ids; the customer from the sign-in only."],
    ["Lifecycle", "Save and pay.", "Expiry in IST, retries with tokens, tokens cleaned up when saving fails."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("Logging the request",
     "\"Support needs this to debug failed saves\": the log line prints the request record, and without the masking <code>toString</code> that is the full card number, in every log store and backup it reaches.",
     "<code>afterSavingPayingAndRetryingTheCardNumberIsNowhereInOurDatabaseOrLog</code> and <code>theRequestNeverPrintsTheCardNumber</code> fail."),
    ("No owner check on listing",
     "\"Read-only, and it shows only the last 4 digits\": any signed-in customer can list anyone's saved cards by changing the id in the path, and the card ids they learn are what payments ask for.",
     "<code>oneCustomerCannotSeeOrAddToAnothersCards</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate helps support: a log line when a card is saved, and the masking <code>toString</code> removed as \"noise\". They also drop the owner check from listing cards, since it is read-only and shows only the last four digits. Read the file and list every problem before opening the findings.</p>
<p class="path">review/CardController.java</p>
""" + code(read("review/CardController.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">The database is clean in the flawed version: the card number leaks through the log, which no database constraint can see. Only a test that reads the log catches it.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
