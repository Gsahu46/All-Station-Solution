"""Station 085 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 85,
    "label": "SAMPLE OF THE FULL STATION FORMAT",
    "page_title": "Station 085 · Idempotent UPI Payments",
    "show_blueprint": True,
    "stack": "Spring Boot 4.1.1 · Java 25 · PostgreSQL 17 · Flyway · Testcontainers 2",
    "simulation": "Payments are rows in this app's own database, marked <code>SUCCESS</code>. Nothing calls a bank or the UPI network, and no real money moves.",
}
J = "src/main/java/com/paysetu/payments/"
T = "src/test/java/com/paysetu/payments/"


# ---------- Tab 1: Understand ----------
TERMS = [
    ("Idempotency", "Doing the same thing twice has the same effect as doing it once.", "Pressing a lift button five times still calls the lift once.", "Sending the same payment twice charges Asha once."),
    ("Idempotency key", "A unique reference the app creates for one payment and repeats on every retry of it.", "The token number you write on your order slip.", "The header <code>Idempotency-Key: 7f3c9a2e-…</code>"),
    ("Retry", "Sending the same request again because no answer came back.", "Re-dialling when a call drops.", "The app resends the payment after a 10-second timeout."),
    ("Replay", "The server returns the saved answer from the first time instead of doing the work again.", "The counter shows you the bill for your first order.", "Response header <code>Idempotent-Replayed: true</code>"),
    ("Request fingerprint", "A short code calculated from the payment details, used to check that a retry is really the same payment.", "Checking that the order on your slip matches the order in the book.", "SHA-256 of payer, payee, amount and note."),
    ("HTTP 422", "\"I understood your request, but I cannot accept it.\"", "Token 42 comes back with a different order.", "Same key, but a different amount."),
    ("Transaction", "A group of database changes that all succeed together or all fail together.", "A bank transfer: the amount leaves one account and reaches the other, or neither happens.", "The key, the payment and the saved response are stored together."),
    ("Unique constraint", "A database rule that no two rows may have the same value.", "An app that lets only one account use a mobile number.", "<code>(payer, key)</code> can exist once, so the database itself blocks a second claim."),
    ("Concurrency", "Two or more requests being handled at the same moment.", "Two people booking the last train seat in the same second.", "A retry arrives while the first request is still running."),
    ("Paise", "One hundredth of a rupee. Whole numbers avoid rounding errors.", "₹125.50 is 12550 paise.", "<code>\"amountPaise\": 12550</code>"),
]
STORY = [
    ("Asha pays Ravi", "Asha taps <em>Pay ₹125.50</em>. The server records the payment, but the internet is slow and the confirmation never reaches her phone."),
    ("The app tries again", "Asha's app thinks the payment failed and sends it again. If the server treats this as a new payment, Asha is charged twice."),
    ("The server recognises the retry", "With this station's API, the server sees the same payment reference, returns the saved result from the first time, and creates nothing new."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms, for reference"],
    "Level 1, about 5 minutes. Plain language: no code, no database detail.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A timeout does not mean the payment failed. It means the phone does not know. The server has to make a retry safe.</p>

<h2>What are we building?</h2>
<p>A Spring Boot API with two endpoints. One creates a payment; the other reads it back. Retrying the same payment never charges twice, even when the retries arrive at the same moment.</p>

<h2>An everyday analogy</h2>
<p>You order food at a counter and write a token number, say 42, on your order slip. If you come back with token 42 and the same order, the counter hands you the bill for your first order instead of cooking again. If you come back with token 42 and a <em>different</em> order, the counter refuses: one token, one order. The token is the idempotency key.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>The app creates a key</strong> for this payment and sends it with the request. It sends the <em>same</em> key on every retry of this payment.</li>
<li><strong>The server checks the key</strong>: has this payer used it before?</li>
<li><strong>The server decides.</strong> A new key: create the payment and save its result. A known key with the same details: return the saved result. A known key with different details: refuse.</li>
<li><strong>The server saves safely.</strong> The payment, the key and the saved result are stored together, all or nothing. Then the app gets its answer.</li>
</ol>

<p class="limit"><b>One limit to remember:</b> the protection lasts only as long as the server keeps the key. The rule here is to keep keys for 24 hours and then delete them (you build that cleanup in Practice). A retry after its key is deleted is treated as a new payment, so apps must stop retrying long before then.</p>

<details class="qa check"><summary>Check yourself: Asha's first request succeeded, but the reply never reached her phone. The app retries with the same key. What should the server do?</summary><p>Return the saved result of the first payment and create nothing new. The original payment record has already been created; the retry only needs the result it missed, not another payment record. If the app sent a <em>new</em> key instead, the server could not know it was a retry. That is why the app must reuse the key for every retry of the same payment.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>A simulation, not real money.</strong> Payments are rows in this app's own database, marked <code>SUCCESS</code> at once. Nothing calls a bank or the UPI network. Real payments have pending states, failures, bank callbacks and reconciliation; those come in stations 132 and 193.</li>
<li><strong>No login.</strong> The payer is read from the request body to keep the station small. In production, identity comes from the signed-in user, never from the body, and <code>GET /payments/{id}</code> must check that the user may see that payment. Knowing a payment's id is not permission. An idempotency key is not authentication.</li>
<li><strong>The ₹1,00,000 maximum is a demo rule</strong> for this station, not an official UPI limit.</li>
<li><strong>Deleting old keys</strong> is left for you: Practice challenge 1.</li>
</ul>

<h2>Key terms</h2>
<p class="muted">For reference while you read the other tabs.</p>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build: precise enough to write the tests from.") + """
<h2>Business problem</h2>
<p><strong>Paysetu</strong> (a fictional UPI-style payments app) lets people pay each other from their phones. On a weak 4G signal, Asha taps <em>Pay ₹125.50 to ravi@oksbi</em>. The server charges her, but the reply never reaches the phone. After 10 seconds the app shows "Something went wrong", and its retry logic sends the same payment again. The server treats it as a new payment and charges Asha a second time.</p>
<p>In a real payments app, Asha's money would be stuck until a refund went through, which takes days. (This station records payments only; see the simulation note at the top.) Support gets a "charged twice" ticket, and Paysetu loses her trust. The client cannot tell a timeout that happened <em>before</em> the charge from one that happened <em>after</em> it, so retries cannot be avoided. The server has to make them safe.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a new <code>Idempotency-Key</code>, <b>when</b> the app sends a valid payment, <b>then</b> one payment is created and the API returns <code>201</code> with <code>Location</code> and <code>Idempotent-Replayed: false</code>.</li>
<li><b>Given</b> a key already used with the same body, <b>when</b> the app retries, <b>then</b> no new payment is created and the API returns the original status, the original response body and the same <code>Location</code>, with <code>Idempotent-Replayed: true</code>.</li>
<li><b>Given</b> a key already used with a different body, <b>when</b> the app sends it, <b>then</b> the API returns <code>422</code> and charges nothing.</li>
<li><b>Given</b> 20 identical requests that arrive at the same moment, <b>then</b> exactly one payment exists and all 20 responses carry the same <code>paymentId</code>.</li>
<li><b>Given</b> no <code>Idempotency-Key</code> header, <b>then</b> the API returns <code>400</code> and charges nothing.</li>
<li><b>Given</b> the server fails after saving the payment but before saving the response, <b>then</b> nothing is kept, and a retry with the same key succeeds once.</li>
<li><b>Given</b> two different payers who happen to send the same key string, <b>then</b> each gets their own payment.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li><code>POST /payments</code> requires an <code>Idempotency-Key</code> header: 8–64 characters from <code>A–Z a–z 0–9 - _</code>. The client creates one key per payment (a UUID works) and sends the same key on every retry of that payment.</li>
<li>Keys are scoped to the payer: <code>(payerVpa, key)</code> is unique, not the key alone.</li>
<li>A key is bound to its request. The fingerprint is a SHA-256 of payer, payee, amount and note. VPAs are compared in lower case using a fixed locale. A missing note and an empty note are the same; any other note text is part of the payment. JSON spacing and field order do not change it.</li>
<li>A key belongs to one logical payment. The client reuses it only to resend <em>that</em> payment, never for a different one. The retry rules are in the API contract tab.</li>
<li>Amounts are whole paise (<code>12550</code> = ₹125.50), from 1 up to 10,000,000 (₹1,00,000, a demo rule for this station). Never a decimal.</li>
<li>Payer and payee must be different, in any letter case.</li>
<li>The database enforces the amount range, different parties and a complete stored response too, so a bug or a script that skips Java validation still cannot break them.</li>
<li>Every error is an RFC 9457 <code>application/problem+json</code> body. Validation errors list each field.</li>
<li>Requests that fail validation do not use up the key.</li>
<li><code>GET /payments/{id}</code> returns the payment, or <code>404</code>.</li>
<li>Keys are kept for at least 24 hours, which is longer than any client retries. The cleanup job is out of scope; the index for it is provided.</li>
</ul>

<h2>Learning objectives</h2>
<p>After this station you can:</p>
<ul>
<li>Explain why a timeout is ambiguous, and why that makes retries unavoidable.</li>
<li>Design the idempotency flow: claim the key, do the work, store the response, replay it.</li>
<li>Use a database unique constraint as the lock, instead of check-then-insert.</li>
<li>Bind a key to a request fingerprint and reject reuse with <code>422</code>.</li>
<li>Keep the key, the payment and the stored response in one transaction.</li>
<li>Explain why Java validation and database constraints are partners, not alternatives.</li>
<li>Prove the rule holds with a real concurrent test against real PostgreSQL.</li>
</ul>
"""

# ---------- Tab 2: API contract ----------
cap = ST / "docs" / "captures"
B = '{"payerVpa":"asha@okpaysetu","payeeVpa":"ravi@oksbi","amountPaise":12550,"note":"Dinner split"}'
K = "7f3c9a2e-5b1d-4e8a-9c6f-2d4b8e1a0c37"


def post(body, key=K):
    hdr = f"Idempotency-Key: {key}\n" if key else ""
    return f"POST /payments HTTP/1.1\n{hdr}Content-Type: application/json\n\n{pretty(body)}"


def get_line(name):
    """The GET request as it was actually sent, taken from the capture's first line ("$ curl http://host:port/path")."""
    path = re.search(r"localhost:\d+(/\S*)", read(f"docs/captures/{name}.txt").splitlines()[0])[1]
    return f"GET {path} HTTP/1.1"


def pretty(text):
    try:
        return json.dumps(json.loads(text), indent=2, ensure_ascii=False)
    except ValueError:
        return text


def response(name):
    raw = (cap / f"{name}.txt").read_text().split("\n\n", 1)[1].strip()
    head, _, body = raw.partition("\n\n")
    return head.strip() + "\n\n" + pretty(body.strip())


examples = [
    ("01-create", "Case 1: a new payment", "<b>Why:</b> the key is new, so the server creates the payment. <code>201 Created</code>, and <code>Location</code> points to the new payment.", post(B)),
    ("02-retry-same-key", "Case 2: same key, same details", "<b>Why:</b> the server recognises a retry. It returns the saved first response: same <code>paymentId</code>, same <code>createdAt</code>. <code>Idempotent-Replayed: true</code> says it is a replay. No new payment.", post(B)),
    ("03-same-key-different-amount", "Case 3: same key, different amount", "<b>Why:</b> the amount changed from ₹125.50 to ₹999. One key must not stand for two different payments, so the server refuses with <code>422</code> and charges nothing. A genuinely new payment needs a new key.", post(B.replace("12550", "99900"))),
    ("04-missing-key", "Case 4: no key", "<b>Why:</b> without a key the server cannot tell a retry from a new payment, so it refuses with <code>400</code> before touching the database.", post(B, key=None)),
    ("05-invalid-fields", "Case 5: invalid details", "<b>Why:</b> the payer VPA has no <code>@bank</code> part and the amount is 0. <code>400</code> with one message per field, so the app can show each error next to its input. The key is not used up.", post('{"payerVpa":"asha","payeeVpa":"ravi@oksbi","amountPaise":0}', key="0b8e4f6a-1c2d-4e3f-8a9b-7c6d5e4f3a2b")),
    ("06-get", "Case 6: read a payment", "<b>Why:</b> the same data as the create response, read back from the database.", get_line("06-get")),
    ("07-get-unknown", "Case 7: unknown payment", "<b>Why:</b> no payment has this id, so <code>404</code> with a problem body.", get_line("07-get-unknown")),
]
ex_html = "".join(
    f'<section class="example"><h3>{t}</h3>{f"<p>{d}</p>" if d else ""}<div class="pair">'
    f'<div><p class="eyebrow">Request</p>{code(req, "http")}</div>'
    f'<div><p class="eyebrow">Response</p>{code(response(n), "http")}</div></div></section>'
    for n, t, d, req in examples)

api = belongs(["5. API contract: methods, URLs, bodies, headers, status codes, error bodies",
               "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/payments</code>", "Pay another VPA. Requires <code>Idempotency-Key</code>."],
    ["<code>GET</code>", "<code>/payments/{id}</code>", "Read one payment."]]) + """
<h2>Request body for <code>POST /payments</code></h2>
""" + table(["Field", "Type", "Rule"], [
    ["<code>payerVpa</code>", "string", "Required. <code>name@bank</code>, at most 255 characters."],
    ["<code>payeeVpa</code>", "string", "Required. Same format. Must differ from the payer."],
    ["<code>amountPaise</code>", "integer", "Required. 1 to 10,000,000 (₹0.01 to ₹1,00,000; the maximum is a demo rule)."],
    ["<code>note</code>", "string", "Optional. At most 80 characters."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When", "Body", "Safe to retry with the same key?"], [
    ['<span class="pill ok">201</span>', "New payment created", "Payment, <code>Idempotent-Replayed: false</code>", "Yes, you get a replay"],
    ['<span class="pill ok">201</span>', "Replay of an earlier success", "The original status, body (byte for byte) and <code>Location</code>; <code>Idempotent-Replayed: true</code>", "Yes"],
    ['<span class="pill warn">400</span>', "Missing or malformed key, invalid fields, broken JSON", "Problem with <code>errors</code> per field", "Only after fixing the request"],
    ['<span class="pill warn">422</span>', "Key already used with a different body", "Problem: <em>Idempotency key reused</em>", "No. Use a new key for a new payment"],
    ['<span class="pill warn">404</span>', "<code>GET</code> for an unknown id", "Problem: <em>Payment not found</em>", "n/a"],
    ['<span class="pill bad">500</span>', "Unexpected failure", "Problem", "Yes, with the same key. See the note below"]]) + """
<div class="rulebox"><p class="eyebrow">Retry rules for the client</p>
<p>A key is not just a request id. It is bound to one logical payment: its payer, payee, amount and note.</p>""" + table(["What happened", "Outcome", "What the client does"], [
    ["Timeout, dropped connection, <code>5xx</code>", "Unknown: the payment may or may not exist", "Resend the <strong>same</strong> request with the <strong>same</strong> key. If the original committed, you get its saved result; if it rolled back, it runs fresh."],
    ["<code>400</code> invalid request", "Nothing was stored; the key was not used", "Fix the request and send it. Reusing the same key is fine, because it was never bound."],
    ["<code>422</code> key reused", "The key is already bound to a different payment", "Do not use this key for the new payment. Create a new key."],
    ["<code>201</code>", "Done", "Keep the key only for resending this same payment."],
    ["More than 24 hours since the first attempt", "The key may have been deleted", "Stop retrying. A retry now could create a second payment."]]) + """
</div>
<p class="note"><strong>What "the same response" means here.</strong> A replay returns the original HTTP status, the original response body (byte for byte) and the same <code>Location</code>. One header differs on purpose: <code>Idempotent-Replayed</code> is <code>false</code> the first time and <code>true</code> on a replay. That is why a replay is <code>201</code> and not <code>200</code>: the app needs no special code for retries, and the header is there for logs and debugging.</p>
<p class="note">Where <code>400</code> and <code>422</code> come from: they match what the IETF <em>Idempotency-Key</em> header draft recommends. That draft (draft-07, October 2025) has expired and is not a published standard, so read them as this API's deliberate design choices. Check the current status yourself on the <a href="https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/">IETF Datatracker</a>; checking a standard's status is part of the job.</p>
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + ex_html

# ---------- Tab 3: Edge cases and trap ----------
edges = table(["Case", "What the API does", "Proved by"], [
    ["Retry after a timeout, same body", "Replays the stored response. One payment.", "<code>sameKeyAndBodyReplaysTheFirstResponseExactly</code>"],
    ["20 identical requests at the same moment", "One payment. All 20 get the same <code>paymentId</code>.", "<code>twentyParallelRetriesWithTheSameKeyCreateOnePayment</code>"],
    ["20 different keys at the same moment", "20 payments. No false de-duplication.", "<code>twentyParallelPaymentsWithDifferentKeysAllGoThrough</code>"],
    ["Same key, different amount", "<code>422</code>, nothing charged.", "<code>sameKeyWithADifferentAmountIs422AndChargesNothingMore</code>"],
    ["Same key string, different payer", "Independent payments.", "<code>keysAreScopedPerPayerSoTwoCustomersCanPickTheSameKey</code>"],
    ["Same key, different payee", "<code>422</code>, nothing charged.", "<code>sameKeyWithADifferentPayeeIs422</code>"],
    ["Same content, JSON reordered or re-spaced", "Treated as the same request: replay.", "<code>sameContentWithDifferentJsonFormattingIsStillAReplay</code>"],
    ["Note left out, then sent as <code>\"\"</code>", "Same payment: replay. A written note, even a space, is a different payment.", "<code>omittedNoteThenEmptyNoteIsAReplay</code>, <code>anyWrittenNoteIsPartOfThePayment</code>"],
    ["VPA in different letter case", "Same payer, same payment: replay.", "<code>mixedCaseVpaIsTheSamePayerAndTheSamePayment</code>"],
    ["Server running with a Turkish locale", "Fingerprint unchanged (<code>Locale.ROOT</code>). Without it, <code>I</code> becomes a dotless <code>ı</code> and retries stop matching.", "<code>aTurkishServerLocaleDoesNotChangeTheFingerprint</code>"],
    ["Request fails validation", "<code>400</code>; the key stays free for the corrected request.", "<code>aFailedValidationDoesNotUseUpTheKey</code>"],
    ["Crash after the payment insert", "Everything rolls back; the retry succeeds once.", "<code>aFailureAfterThePaymentInsertRollsBackTheKeyAndThePayment</code>"],
    ["Amount 0 or above the maximum slips past Java validation", "The database <code>CHECK</code> still rejects it.", "<code>databaseRejectsAmountsOutsideTheRangeEvenWithoutJavaValidation</code>"],
    ["Paying yourself, written in a different case, slips past Java", "The database <code>CHECK</code> still rejects it.", "<code>databaseRejectsPayingYourselfInAnyLetterCase</code>"],
    ["A stored response saved half-filled", "The database rejects it; a replay always finds a complete response.", "<code>databaseRejectsAHalfFilledStoredResponse</code>"],
    ["Missing or short key", "<code>400</code>", "<code>missingIdempotencyKeyIs400</code>, <code>malformedIdempotencyKeyIs400</code>"],
    ["Amount above ₹1,00,000; paying yourself; broken JSON", "<code>400</code> with field messages", "<code>PaymentContractTest</code>"],
    ["Unknown payment id", "<code>404</code> problem", "<code>unknownPaymentIs404Problem</code>"],
    ["Retry after the key was cleaned up", "Charged again. Retention must be longer than any client retry window.", "Design rule (no cleanup job in this station)"],
])

trap_test = read(T + "RetryWithoutKeyTrapTest.java")
trap = belongs(["6. Edge cases and failure cases", "7. The trap: the plausible-but-wrong approach, shown failing with a test"],
               "Every edge case points at the test that proves it. The trap is the first test written.") + """
<h2>Edge cases and failure cases</h2>
""" + edges + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Retrying a timed-out payment without an idempotency key, which charges the customer twice.</p>
<p>The "before" code charges on every <code>POST</code>. It looks fine in a demo, where the network never drops a reply. The first test in this station reproduces the bug. It passes because it asserts the bug: two attempts, two charges. The second test runs the fixed API and gets one charge.</p>
</div>
""" + code(trap_test, "java") + """
<h3>The subtler trap</h3>
<p>Adding a key is not enough. The obvious way to use it (look up the key, charge if absent, then save the key) still double-charges when retries overlap. Against the flawed version in the <a href="#review" data-goto="review">Review</a> tab, 20 parallel retries with one key produced these results in 5 runs:</p>
""" + table(["Run", "Payments charged", "Responses"], [
    ["1", '<span class="pill bad">19</span>', "2 × 201, 18 × 500"],
    ["2", '<span class="pill bad">9</span>', "12 × 201, 8 × 500"],
    ["3", '<span class="pill bad">2</span>', "19 × 201, 1 × 500"],
    ["4", '<span class="pill bad">5</span>', "16 × 201, 4 × 500"],
    ["5", '<span class="pill bad">4</span>', "17 × 201, 3 × 500"]], "narrow") + """
<p>The correct answer is 1 every time. The fixed code gets 1 every time, which <code>PaymentConcurrencyTest</code> checks.</p>
"""

# ---------- Tab 4: Design ----------
design = belongs(["8. Implementation approach: numbered steps before any code", "9. Design alternatives and trade-offs",
                  "12. Database design: tables, constraints, indexes, migration, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li><strong>Validate</strong> the header and body. A bad request gets <code>400</code> before the database is touched, so it does not use up the key.</li>
<li><strong>Fingerprint</strong> the request: SHA-256 of payer, payee, amount and note.</li>
<li><strong>Begin</strong> one transaction.</li>
<li><strong>Claim</strong> the key: <code>INSERT … ON CONFLICT DO NOTHING</code>. One row inserted means this request owns the key. If another transaction is inserting the same key, PostgreSQL makes this insert wait until that transaction ends.</li>
<li><strong>If not claimed</strong>, read the stored row. If the fingerprint differs, return <code>422</code>. Otherwise return the stored status and body with <code>Idempotent-Replayed: true</code>.</li>
<li><strong>Charge</strong>: insert the payment.</li>
<li><strong>Store the response</strong>: serialise it once and save it on the key row with the payment id.</li>
<li><strong>Commit.</strong> The key, the payment and the response become visible together, or not at all.</li>
<li><strong>Return</strong> the stored status and body as-is, with the same <code>Location</code>. Only <code>Idempotent-Replayed</code> tells a replay apart.</li>
</ol>

<h2>Two retries at the same moment</h2>
<pre class="mermaid">
sequenceDiagram
    autonumber
    participant A as Phone, attempt 1
    participant B as Phone, retry
    participant API as Payments API
    participant DB as PostgreSQL
    A->>API: POST /payments (key K)
    API->>DB: INSERT key K ON CONFLICT DO NOTHING
    DB-->>API: 1 row: A owns K
    B->>API: POST /payments (key K)
    API->>DB: INSERT key K ON CONFLICT DO NOTHING
    Note over DB: B waits: A's insert of K is not committed yet
    API->>DB: INSERT payment, UPDATE key K with response
    API->>DB: COMMIT (A)
    API-->>A: 201 (reply lost on the network)
    DB-->>API: 0 rows: K already exists
    API->>DB: SELECT key K
    DB-->>API: same fingerprint, stored 201 body
    API-->>B: 201, same body, Idempotent-Replayed: true
</pre>

<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["<strong>Unique constraint claims the key</strong>, all in one transaction", "A waiting retry holds a DB connection until the first finishes. Works only when the effect is in the same database.", '<span class="pill ok">Chosen</span>'],
    ["Check-then-insert: <code>SELECT</code> the key, charge, then <code>INSERT</code> the key", "Two requests both see \"no key\" and both charge. Measured above: up to 19 charges.", '<span class="pill bad">Wrong</span>'],
    ["<code>SELECT … FOR UPDATE</code>", "You cannot lock a row that does not exist yet, which is exactly the first-request case.", '<span class="pill bad">Wrong</span>'],
    ["Redis <code>SET NX</code> with a TTL", "Fast, with expiry built in. But the key and the payment live in two stores with no shared transaction; a crash between them leaves them out of step.", '<span class="pill warn">When the effect is elsewhere</span>'],
    ["PostgreSQL advisory lock on a hash of the key", "Works, but a hash can collide and the rule is invisible in the schema. A constraint documents itself.", '<span class="pill warn">Possible</span>'],
    ["Two-phase key: commit <code>IN_PROGRESS</code>, call the bank, then mark <code>COMPLETED</code>; a concurrent retry gets <code>409</code>", "Needed when the charge is an external call that cannot sit inside your database transaction, as with a real bank or PSP. Costs a recovery job for keys stuck in progress.", '<span class="pill warn">Later stations</span>'],
    ["De-duplicate by business fields (same payer, payee and amount within 5 minutes)", "Blocks real repeat payments, such as two ₹20 chai payments to the same stall.", '<span class="pill bad">Wrong</span>'],
    ["Server-issued intent: the client first creates a payment intent or order, then confirms it", "Also correct, and common at large PSPs. Costs one extra round trip and a new resource to manage.", '<span class="pill warn">Valid alternative</span>']]) + """
<p class="note">One deliberate difference from Stripe's API v1: Stripe stores and replays even a <code>500</code> response, because its side effects may already have happened. Here, a <code>500</code> raised inside <code>pay()</code> rolls the transaction back, so a same-key retry runs fresh. A failure the client sees <em>after</em> the commit (a lost reply, a proxy error) is answered by a replay. Both cases are safe only because the key, the payment and the response share one transaction.</p>

<h2>Database design</h2>
""" + table(["Table", "Key and constraints", "Why"], [
    ["<code>payments</code>", "PK <code>id</code> (UUID). <code>payments_amount_range</code>: 1 to 10,000,000 paise. <code>payments_different_parties</code>: payer ≠ payee, any case. <code>BIGINT</code> paise.", "The effect. The same rules as <code>PaymentRequest</code>, enforced again: Java gives friendly messages, the database guarantees them even when Java is bypassed."],
    ["<code>idempotency_keys</code>", "PK <code>(payer_vpa, idem_key)</code>. FK <code>payment_id → payments.id</code>. <code>idempotency_keys_result_complete</code>: the three result columns are all empty or all filled. Index on <code>created_at</code>.", "The PK is the lock and the per-payer scope. The result columns are empty only inside the claiming transaction, which no one else can see, and the check stops a half-saved response. The index serves the cleanup job in Practice."]]) + """
<p><strong>Transaction boundary:</strong> <code>PaymentService.pay</code> is <code>@Transactional</code> at PostgreSQL's default <code>READ COMMITTED</code>. That level is enough: after the waiting insert returns 0 rows, the next <code>SELECT</code> takes a fresh snapshot and sees the committed row.</p>
""" + code(read("src/main/resources/db/migration/V1__payments_and_idempotency_keys.sql"), "sql")

# ---------- Tab 5: Code ----------
code_files = [  # in the order a request travels: in at the controller, out to the database
    (J + "PaymentController.java", dwn("Receives <code>POST /payments</code> and <code>GET /payments/{id}</code>, checks the header format, and returns the stored response with <code>Location</code> and <code>Idempotent-Replayed</code>.",
        "Keeps HTTP details (headers, status codes) out of the business logic.",
        "No endpoint. Put this logic in the service instead and it becomes hard to test without HTTP.",
        "<ul><li>Returns <code>ResponseEntity&lt;String&gt;</code> because the body is already JSON from the store. A replay has the original status, body and <code>Location</code>; only <code>Idempotent-Replayed</code> differs.</li></ul>")),
    (J + "PaymentRequest.java", dwn("Holds the request fields with their validation rules, and computes the fingerprint.",
        "One place defines what a valid payment is and what makes two requests \"the same payment\".",
        "Bad input reaches the database, and a retry with different formatting would not be recognised.",
        "<ul><li><code>normalise()</code> lower-cases VPAs with <code>Locale.ROOT</code>; every VPA comparison goes through it.</li><li>A missing note and an empty note give the same fingerprint, by design.</li></ul>")),
    (J + "PaymentService.java", dwn("Runs the whole flow in one transaction: claim the key, compare the fingerprint, create the payment, store the response.",
        "The transaction is what makes the key, the payment and the response appear together or not at all.",
        "Split this across separate calls and a crash between them leaves a payment with no key, which a retry charges again (see the Review tab).",
        "<ul><li><code>claim</code> returning <code>false</code> means another request owns this key (we may have waited for it to commit).</li></ul>")),
    (J + "IdempotencyKeyRepository.java", dwn("Claims a key with <code>INSERT … ON CONFLICT DO NOTHING</code>, saves the response, and reads a stored one back.",
        "The database's unique key decides which of two simultaneous requests wins. No Java lock can do that across several servers.",
        "Back to check-then-insert, which charged up to 19 times for one key in the Edge cases tab.")),
    (J + "PaymentRepository.java", dwn("Inserts and reads payments with plain SQL.",
        "Every statement is visible, which helps while learning.",
        "No payments. Use JPA instead and the SQL is hidden, which suits later stations.",
        "<ul><li>Times are truncated to microseconds, so the response matches what PostgreSQL stores and later returns.</li></ul>")),
    (J + "Payment.java", dwn("One record that is both the stored payment and the response body.", "A separate response class would add nothing yet.", "Nowhere to hold a payment.")),
    (J + "ApiErrors.java", dwn("Adds an <code>errors</code> map (field → message) to validation errors.",
        "Spring already returns RFC 9457 problem bodies; the app needs to know which field is wrong.",
        "Clients get \"invalid request\" with no hint which field to fix.",
        "<ul><li>Because the header has a constraint, body errors arrive as <code>HandlerMethodValidationException</code>. Handling only <code>MethodArgumentNotValidException</code> was a real bug the contract tests caught while this station was built.</li></ul>")),
    ("src/main/resources/db/migration/V1__payments_and_idempotency_keys.sql", dwn("Creates both tables with their constraints when the app starts (Flyway).",
        "The schema is versioned with the code. Later changes are new files (<code>V2__…</code>), never edits to a released one.",
        "Someone creates tables by hand, and the constraints that protect the payment records are missing.")),
    (J + "PaymentsApplication.java", "<p>Standard Spring Boot entry point.</p>"),
    ("src/main/resources/application.yaml", "<p>Local database settings. Tests replace them with their own container automatically.</p>"),
    ("pom.xml", "<p>Spring Boot 4.1.1, Java 25. Only the starters this station uses. Test side: Testcontainers 2 for a real PostgreSQL, and <code>RestTestClient</code> for real HTTP calls.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app locally. Tests do not need it; they start their own container.</p>"),
]
tree = """stations/085-idempotent-upi-payments/
├── README.md                      (this page, as Markdown)
├── pom.xml, mvnw, mvnw.cmd        (Maven wrapper: no Maven install needed)
├── compose.yaml                   (PostgreSQL 17 for running locally)
├── src/main/java/com/paysetu/payments/
│   ├── PaymentController.java     ├── PaymentRepository.java
│   ├── PaymentRequest.java        ├── IdempotencyKeyRepository.java
│   ├── PaymentService.java        ├── Payment.java
│   ├── ApiErrors.java             └── PaymentsApplication.java
├── src/main/resources/            (application.yaml, db/migration/V1__….sql)
├── src/test/java/…                (8 test files, see Tests)
├── challenge/                     (Practice tests; solutions ship in a separate pack)
├── review/PaymentService.java     (flawed version, see Review)
└── docs/                          (payment.json for curl, captures, saved test runs)"""

setup = table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Docker", "Docker Desktop (Windows, macOS) or Docker Engine (Linux), running", "<code>docker info</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper (<code>mvnw</code>)", ""],
    ["curl", "Built into Windows 10+, macOS and Linux", "<code>curl --version</code>"]])

trouble = table(["You see", "Cause", "Fix"], [
    ["<code>Could not find a valid Docker environment</code>", "Docker is not running. Testcontainers needs it for the tests.", "Start Docker Desktop, wait until it says running, then run the tests again."],
    ["<code>release version 25 not supported</code>", "Maven is using an older JDK.", "Point <code>JAVA_HOME</code> at JDK 25, or use the JDK 21 command below."],
    ["<code>Connection to localhost:5432 refused</code>", "The app started before PostgreSQL, or compose is not up.", "Run <code>docker compose up -d</code>, wait a few seconds, start the app again."],
    ["<code>port 5432 is already allocated</code>", "A local PostgreSQL already uses the port.", "Stop it, or change <code>\"5432:5432\"</code> to <code>\"5433:5432\"</code> in <code>compose.yaml</code> and the URL in <code>application.yaml</code>."],
    ["<code>'./mvnw' is not recognized</code> on Windows", "PowerShell needs the <code>.cmd</code> file.", "Use <code>.\\mvnw.cmd</code> instead of <code>./mvnw</code>."]])

codetab = belongs(["Set up and run: what to install, the commands for Windows and macOS/Linux, troubleshooting",
                   "Try it yourself: send the requests and count the rows",
                   "10. Complete working code, in the order a request travels", "11. Code explanation: for each class, what it does, why it exists, what breaks without it"],
                  "Level 2. Every command here was run on 11 Oct 2026 and gave the results shown.") + """
<h2>Set up and run</h2>
""" + setup + """
<p><strong>macOS / Linux</strong></p>
""" + code("""docker compose up -d        # PostgreSQL 17 on localhost:5432
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21 instead of 25, add <code>-Djava.version=21</code>, for example <code>./mvnw -Djava.version=21 test</code>. All """ + str(N_TESTS) + """ tests passed this way on JDK 21.0.12. Nothing in this station needs a Java 25 feature.</p>

<h2>Try it yourself</h2>
<p>With the app running, open a second terminal in the project folder. The request body is in <code>docs/payment.json</code>, so the same commands work in PowerShell and in bash.</p>
""" + code("""# 1. Pay once: expect HTTP 201 and Idempotent-Replayed: false
curl -i -X POST http://localhost:8080/payments -H "Idempotency-Key: try-it-0001" -H "Content-Type: application/json" -d "@docs/payment.json"

# 2. Retry with the same key: expect HTTP 201 and Idempotent-Replayed: true
curl -i -X POST http://localhost:8080/payments -H "Idempotency-Key: try-it-0001" -H "Content-Type: application/json" -d "@docs/payment.json"

# 3. Same key, different amount: expect HTTP 422
curl -i -X POST http://localhost:8080/payments -H "Idempotency-Key: try-it-0001" -H "Content-Type: application/json" -d "@docs/payment-changed-amount.json"

# 4. Count payments in the database: expect 1
docker compose exec postgres psql -U paysetu -d paysetu -c "SELECT count(*) AS payments FROM payments\"""", "bash") + """
<p>Three requests, one payment. Now try request 1 with a new key such as <code>try-it-0002</code>, count again, and explain the result to yourself. In PowerShell, write <code>curl.exe</code> instead of <code>curl</code> if <code>curl</code> opens a different command.</p>

<h2>Troubleshooting</h2>
""" + trouble + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">Files are listed in the order a request travels: in at the controller, through the service, out to the database.</p>
""" + filebrowser("code", code_files)

# ---------- Tab 6: Tests ----------
test_files = [
    (T + "RetryWithoutKeyTrapTest.java", "<p>Written first. Reproduces the double charge, then shows the fix.</p>"),
    (T + "PaymentRequestTest.java", "<p>Plain unit tests for the fingerprint rules: letter case, a Turkish server locale, missing versus empty note, every field. No Spring, so they run in milliseconds.</p>"),
    (T + "PaymentContractTest.java", "<p>The HTTP contract: valid, invalid, not found, missing and malformed key, broken JSON.</p>"),
    (T + "IdempotencyReplayTest.java", "<p>Replays; key reuse with a different amount or payee; JSON formatting; missing versus empty note; letter case; per-payer scope; validation failures not using up the key.</p>"),
    (T + "PaymentConcurrencyTest.java", "<p>20 real HTTP requests released together on virtual threads. One test proves one payment per key; the other proves different keys are not merged.</p>"),
    (T + "PaymentDatabaseTest.java", "<p>Amount range, different parties and a complete stored response hold without Java validation. A crash injected after the payment insert rolls back the key and the payment.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app on a random port, real HTTP, tables emptied before each test.</p>"),
    (T + "PostgresTestConfig.java", "<p>A real PostgreSQL 17 in Docker via Testcontainers. Spring wires it in with <code>@ServiceConnection</code>.</p>"),
]
SP = STATION_RUN[0]
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)


def cnt(*classes):
    return sum(SP[c][1] for c in classes)
tests = belongs(["13. Testing: each required test named, with what it proves",
                 "The test that reproduces the failure before the fix",
                 "Real run output"],
                "Required tests come from the station's types. The validator fails a station that is missing any of them.") + """
<h2>Required tests for this station</h2>
<p>Station types: <span class="chip">Database</span> <span class="chip">Concurrency</span> <span class="chip">Idempotency</span></p>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>PaymentContractTest</code> ({cnt('PaymentContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>RetryWithoutKeyTrapTest</code> ({cnt('RetryWithoutKeyTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>PaymentDatabaseTest</code> ({cnt('PaymentDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Concurrency", "A real concurrency test that proves the invariant holds", f"<code>PaymentConcurrencyTest</code> ({cnt('PaymentConcurrencyTest')})", '<span class="pill ok">pass</span>'],
    ["Idempotency", "Replay: the same request twice gives one effect", f"<code>IdempotencyReplayTest</code> ({cnt('IdempotencyReplayTest')}), <code>PaymentRequestTest</code> ({cnt('PaymentRequestTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Docker via Testcontainers 2.0.5. Run on 11 Oct 2026. Nothing skipped, and no in-memory database. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", test_files)

# ---------- Tab 7: Production ----------
prod = belongs(["15. Real-world considerations: security, performance, reliability, scale, cost, maintainability",
                "14. Operations: metric, alert, rollback, runbook, failure drill (Production Scale stations only)"],
               "This is a Working Systems station, so the full Operations section is not required. This tab shows the signals to know; the runbook and failure drill start at Production Scale.") + """
<h2>Real-world considerations</h2>
<dl class="facts">
<dt>Security</dt><dd>Keys are scoped per payer. With a global scope, anyone who reuses another person's key would receive that person's payment details. In production the payer comes from the authenticated token, never from the request body. <code>GET /payments/{id}</code> must also check that the signed-in user is the payer or the payee; a UUID is hard to guess, but knowing it is not permission. Answer <code>404</code> rather than <code>403</code>, so the API does not confirm the payment exists. A VPA is personal data under India's DPDP rules, so mask it in logs. All of this is taught in the Security stations.</dd>
<dt>Performance</dt><dd>Each payment costs one extra insert and one update. Retries of the same key queue behind each other and hold a database connection while they wait, so a retry storm can drain the pool. Size the pool and keep client retries spaced out with backoff.</dd>
<dt>Reliability</dt><dd>Retrying with the same key is safe <em>while the key is retained</em> (24 hours here): a replay if the original committed, a fresh run if it rolled back, or a <code>422</code> if the details changed. After cleanup the server has forgotten the key, and the same request creates a new payment. So the retention window must be longer than the longest client retry, and clients must give up before it ends (Practice challenge 1 shows this with a test). Real UPI payments are asynchronous (pending, then success or failure from the bank). This station simplifies to an immediate success; bank callbacks come in station 132.</dd>
<dt>Scale</dt><dd><code>idempotency_keys</code> grows by one row per payment. A daily cleanup of rows older than the retention window keeps it bounded (Practice challenge 1). Partitioning by day so old days can be dropped is <em>not</em> a drop-in change: PostgreSQL requires a primary key on a partitioned table to include the partition column, and <code>(payer_vpa, idem_key)</code> does not. Practice challenge 4 works through the trade-offs.</dd>
<dt>Cost</dt><dd>About 200 bytes of stored response per payment, for 24 hours. Small next to the cost of one refund ticket.</dd>
<dt>Maintainability</dt><dd>The flow lives in one service method. Pull it out into a shared filter or aspect only when a third endpoint needs it, not before.</dd>
</dl>
<h2>Signals to know</h2>
""" + table(["Signal", "What it tells you"], [
    ["Replay rate: responses with <code>Idempotent-Replayed: true</code> as a share of all", "A jump means the network or a client is retrying more than usual."],
    ["Rate of <code>422</code> key-reused responses", "Almost always a client bug: one key used for two different payments."],
    ["p99 latency of <code>POST /payments</code>", "Lock waits from same-key retries show up here first."],
    ["Rows in <code>idempotency_keys</code> older than 24 hours", "Cleanup is not running."]])

# ---------- Tab 8: Interview ----------
qa = [
    ("What does idempotent mean, and is POST idempotent?", "An operation is idempotent if doing it twice has the same effect as doing it once. HTTP defines GET, PUT and DELETE (among others) as idempotent, but not POST. A payment POST becomes idempotent only when the server makes it so, here with a client-supplied key."),
    ("Why can't the app check whether the payment went through before retrying?", "The check can time out too, and it races with the original request, which may still be in progress. Only the server, which sees both requests, can decide safely. The key gives it the information to do that."),
    ("Why a unique constraint and not SELECT, then INSERT?", "Two requests can both run the SELECT before either inserts, so both see \"no key\" and both charge. A unique constraint makes the database pick exactly one winner, atomically. In PostgreSQL the loser's insert waits for the winner to commit, then reports a conflict."),
    ("Same key, different amount: what do you return, and why?", "422 Unprocessable Content. The (now expired) IETF Idempotency-Key draft suggested the same, but it is our design choice, not a standard requirement. Returning the old payment would make the client think the new amount was paid. Charging would break the key's promise. The client must use a new key for a new payment."),
    ("Two requests with the same key arrive together. Walk through your design.", "Both try the insert. One gets the row; the other waits on the unique index. The first inserts the payment, stores the response and commits. The waiting insert then returns 0 rows; a fresh SELECT under READ COMMITTED sees the stored response, compares the fingerprint, and replays it."),
    ("What changes if the charge is an HTTP call to a bank?", "You cannot hold a database transaction open across a slow external call, and you cannot roll the call back. Commit the key as IN_PROGRESS first, call the bank with your own idempotency reference, then mark it COMPLETED with the response. A concurrent retry gets 409 Conflict, and a recovery job resolves keys stuck in progress by asking the bank for the status."),
    ("A client got a 500 from a payment API. Should it retry, and with which key?", "Yes, with the same key. If the server's transaction rolled back, the retry runs as a fresh payment. If it committed and only the reply was lost or mangled by a proxy, the retry gets the saved response. A new key is the mistake that charges twice. One limit: this holds only while the server still keeps the key (24 hours here); a retry after cleanup is a new payment."),
    ("How long do you keep keys?", "Longer than any client will retry. Stripe's docs, for example, say keys can be pruned once they are at least 24 hours old. After pruning, the same key is treated as a new request, so a very late retry would charge again."),
    ("Redis or PostgreSQL for the keys?", "If the effect is a row in PostgreSQL, keep the key there and use one transaction; correctness comes for free. Redis fits when the effect is somewhere else and you want built-in expiry, but then you must handle a crash between \"key saved\" and \"effect done\"."),
    ("Why amounts in paise as integers?", "Binary floating point cannot represent most decimal amounts exactly, so sums drift. Whole paise in a BIGINT are exact, and the API states the unit in the field name."),
]
interview = belongs(["16. Interview takeaways: questions to answer out loud, with strong answers", "17. Self-check rubric"],
                    "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
<p class="muted">Say your answer out loud, then open the strong answer.</p>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can say why each test would fail without the fix."],
    ["Robustness", "Every edge case in the table is handled.", "You found a case the table does not list, and added a test."],
    ["Design", "One transaction; the unique constraint is the lock.", "You can argue when the two-phase design is needed instead."],
    ["Tests", "Real PostgreSQL and real parallel requests.", "You broke the code on purpose and watched the right test go red."],
    ["Explanation", "You can explain the flow in two minutes.", "You can draw the sequence diagram from memory."]])

# ---------- Tab 9: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("No transaction", "The payment insert commits on its own. When the key insert then fails (a parallel retry got there first), the customer is already charged and the client gets a 500.", "<code>twentyParallelRetriesWithTheSameKeyCreateOnePayment</code>: 500 instead of 201. The probe counted 2 to 19 charges for one key."),
    ("Check-then-act race", "Two retries both run the SELECT, both see no key, and both charge. A single-threaded test never sees this.", "Same concurrency test. The simple \"send twice\" trap test still passes, which is how this got approved."),
    ("Key not scoped to the payer", "The lookup uses only <code>idem_key</code>. If Meera's app picks the same key string as Asha's, Meera receives Asha's payment details, and Meera's payment never happens.", "<code>keysAreScopedPerPayerSoTwoCustomersCanPickTheSameKey</code>: replay header was true, expected false."),
    ("Fingerprint saved but never compared", "Same key, new amount returns the old payment as 201. The client believes ₹999 was paid when only ₹125.50 was.", "<code>sameKeyWithADifferentAmountIs422AndChargesNothingMore</code> and <code>sameKeyWithADifferentPayeeIs422</code>: got 201, expected 422."),
    ("A crash leaves a charge without a key", "If the process dies between the two inserts, the payment exists but the key does not, so the retry charges again.", "<code>aFailureAfterThePaymentInsertRollsBackTheKeyAndThePayment</code> fails: it injects its crash in the step this version skips, so the crash never happens. With no transaction there is nothing to roll back anyway."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate's version was approved and shipped. It passes the "send twice, get one payment" test. Read it and list every problem before opening the findings.</p>
""" + code(read("review/PaymentService.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed <code>PaymentService</code> copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">The lesson: the tests a reviewer usually sees (contract and a simple retry) all pass. Only the concurrency, scope and key-reuse tests catch these bugs, which is why each station type requires its own tests.</p>
"""

# ---------- Tab 10: Practice ----------
CH = "challenge/"
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
def challenge(n, title, level, minutes, task, done, hints, test, solutions):
    sol = "".join(f'<p class="path">{e(f)}</p><div class="src">{code(read(f), "java")}</div>' for f in solutions)
    hint = "".join(f"<li>{h}</li>" for h in hints)
    return (f'<section class="challenge"><p class="eyebrow">Challenge {n} · {level} · about {minutes} minutes</p><h2>{title}</h2>'
            f'<p>{task}</p><p><b>Done when:</b> {done}</p>'
            f'<details class="qa"><summary>Hints</summary><ul>{hint}</ul></details>'
            f'<p class="path">{e(test)}</p>{code(read(test), "java")}'
            f'<details class="qa solution"><summary>Solution (open after trying)</summary>{sol}</details></section>')

practice = belongs(["19. Practice challenges: tasks the learner builds, each with a ready test in <code>challenge/</code> and a solution to open after trying",
                    "One design-on-paper task with no code"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Download the starter project; the solutions are a separate pack, and on this page they open only when you click. Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/paysetu/payments/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=KeyCleanupChallengeTest</code></li>
<li>Write the code until it passes. Then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests still pass.</li>
</ol>
<p class="muted">Checked on 11 Oct 2026 (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Old keys expire after 24 hours", "Beginner-friendly", 45,
    "Right now <code>idempotency_keys</code> grows forever. Add a Spring bean <code>IdempotencyKeyCleanup</code> with a method <code>int deleteKeysOlderThan(Duration age)</code> that deletes old keys and returns how many it deleted. Then run it every night.",
    "both tests in <code>KeyCleanupChallengeTest</code> pass. The second test shows why retention must be longer than any client retry: after cleanup, the same key creates a new payment.",
    ["The table already has an index on <code>created_at</code>; your <code>DELETE</code> should use it.",
     "Delete keys, never payments. A payment is a financial record.",
     "<code>@Scheduled(cron = …)</code> runs a method on a timetable. It needs <code>@EnableScheduling</code> somewhere."],
    CH + "KeyCleanupChallengeTest.java", [CH + "solution/IdempotencyKeyCleanup.java"]) + challenge(2, "Count replays and key reuse", "Go deeper", 30,
    "On-call engineers need to see retries. Count two events with Micrometer: <code>paysetu.payments.replayed</code> when a saved response is returned, and <code>paysetu.payments.key_reused</code> when a key comes back with different details.",
    "<code>ReplayMetricsChallengeTest</code> passes and the other tests still pass.",
    ["Add <code>spring-boot-starter-actuator</code> to <code>pom.xml</code>; it provides a <code>MeterRegistry</code> bean.",
     "Create both counters once, in the constructor, not on every request.",
     "Increment only on the replay and 422 paths, not on the first payment."],
    CH + "ReplayMetricsChallengeTest.java", [CH + "solution/PaymentService.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · Go deeper · design on paper, no code</p>
<h2>The charge becomes a call to a bank</h2>
<p>The payment is no longer a row in your database. It is an HTTP call to a bank that takes 2 to 8 seconds and cannot be rolled back. Redesign the flow on paper and answer:</p>
<ol>
<li>Where does your database transaction start and end now? Why can it not stay open during the bank call?</li>
<li>What does a second request with the same key see while the first is still waiting for the bank? Which status code do you return?</li>
<li>The bank says yes, then your server crashes before saving the result. What happens on the retry, and how do you find out what the bank did?</li>
</ol>
<p>Compare your answer with the interview question about a bank call and the two-phase row in the Design tab's alternatives.</p>
</section>
<section class="challenge"><p class="eyebrow">Challenge 4 · Go deeper · design on paper, no code</p>
<h2>Keep the keys table small at 50 million payments a day</h2>
<p>Daily <code>DELETE</code>s of millions of rows are slow and bloat the table. Dropping a whole day's partition is instant. But PostgreSQL requires a primary key on a partitioned table to include the partition column, and <code>(payer_vpa, idem_key)</code> does not include <code>created_at</code>.</p>
<ol>
<li>If you partition by day and change the key to <code>(payer_vpa, idem_key, created_at)</code>, what can now go wrong when a retry arrives just after midnight?</li>
<li>What do you gain and lose by hash-partitioning on <code>payer_vpa</code> instead?</li>
<li>Would you keep deleting in batches, accept the bloat, or move keys to a store with built-in expiry? Which number would make you change your mind?</li>
</ol>
<p class="muted">Background: the PostgreSQL documentation on table partitioning, "Limitations" section.</p>
</section>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
