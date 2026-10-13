# Station 085 · Idempotent UPI-style payments

Working Systems · 0–2 years · Core · Payments · Types: Database, Concurrency, Idempotency

Spring Boot 4.1.1 · Java 25 · PostgreSQL 17 · Flyway · Testcontainers 2. Needs JDK 25 (or 21, see Set up & code) and Docker. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Payments are rows in this app's own database, marked `SUCCESS`. Nothing calls a bank or the UPI network, and no real money moves.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 31 tests.

# 1 · Understand

## The problem in real life

1.  **Asha pays Ravi**

    Asha taps *Pay ₹125.50*. The server records the payment, but the internet is slow and the confirmation never reaches her phone.

2.  **The app tries again**

    Asha's app thinks the payment failed and sends it again. If the server treats this as a new payment, Asha is charged twice.

3.  **The server recognises the retry**

    With this station's API, the server sees the same payment reference, returns the saved result from the first time, and creates nothing new.

A timeout does not mean the payment failed. It means the phone does not know. The server has to make a retry safe.

## What are we building?

A Spring Boot API with two endpoints. One creates a payment; the other reads it back. Retrying the same payment never charges twice, even when the retries arrive at the same moment.

## An everyday analogy

You order food at a counter and write a token number, say 42, on your order slip. If you come back with token 42 and the same order, the counter hands you the bill for your first order instead of cooking again. If you come back with token 42 and a *different* order, the counter refuses: one token, one order. The token is the idempotency key.

## How it works in 4 steps

1.  **The app creates a key** for this payment and sends it with the request. It sends the *same* key on every retry of this payment.
2.  **The server checks the key**: has this payer used it before?
3.  **The server decides.** A new key: create the payment and save its result. A known key with the same details: return the saved result. A known key with different details: refuse.
4.  **The server saves safely.** The payment, the key and the saved result are stored together, all or nothing. Then the app gets its answer.

**One limit to remember:** the protection lasts only as long as the server keeps the key. The rule here is to keep keys for 24 hours and then delete them (you build that cleanup in Practice). A retry after its key is deleted is treated as a new payment, so apps must stop retrying long before then.

Check yourself: Asha's first request succeeded, but the reply never reached her phone. The app retries with the same key. What should the server do?

Return the saved result of the first payment and create nothing new. The original payment record has already been created; the retry only needs the result it missed, not another payment record. If the app sent a *new* key instead, the server could not know it was a retry. That is why the app must reuse the key for every retry of the same payment.

## What this station is not

- **A simulation, not real money.** Payments are rows in this app's own database, marked `SUCCESS` at once. Nothing calls a bank or the UPI network. Real payments have pending states, failures, bank callbacks and reconciliation; those come in stations 132 and 193.
- **No login.** The payer is read from the request body to keep the station small. In production, identity comes from the signed-in user, never from the body, and `GET /payments/{id}` must check that the user may see that payment. Knowing a payment's id is not permission. An idempotency key is not authentication.
- **The ₹1,00,000 maximum is a demo rule** for this station, not an official UPI limit.
- **Deleting old keys** is left for you: Practice challenge 1.

## Key terms

For reference while you read the other tabs.

| Term                    | Simple meaning                                                                                           | Everyday example                                                                          | In this project                                                              |
|-------------------------|----------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| **Idempotency**         | Doing the same thing twice has the same effect as doing it once.                                         | Pressing a lift button five times still calls the lift once.                              | Sending the same payment twice charges Asha once.                            |
| **Idempotency key**     | A unique reference the app creates for one payment and repeats on every retry of it.                     | The token number you write on your order slip.                                            | The header `Idempotency-Key: 7f3c9a2e-…`                                     |
| **Retry**               | Sending the same request again because no answer came back.                                              | Re-dialling when a call drops.                                                            | The app resends the payment after a 10-second timeout.                       |
| **Replay**              | The server returns the saved answer from the first time instead of doing the work again.                 | The counter shows you the bill for your first order.                                      | Response header `Idempotent-Replayed: true`                                  |
| **Request fingerprint** | A short code calculated from the payment details, used to check that a retry is really the same payment. | Checking that the order on your slip matches the order in the book.                       | SHA-256 of payer, payee, amount and note.                                    |
| **HTTP 422**            | "I understood your request, but I cannot accept it."                                                     | Token 42 comes back with a different order.                                               | Same key, but a different amount.                                            |
| **Transaction**         | A group of database changes that all succeed together or all fail together.                              | A bank transfer: the amount leaves one account and reaches the other, or neither happens. | The key, the payment and the saved response are stored together.             |
| **Unique constraint**   | A database rule that no two rows may have the same value.                                                | An app that lets only one account use a mobile number.                                    | `(payer, key)` can exist once, so the database itself blocks a second claim. |
| **Concurrency**         | Two or more requests being handled at the same moment.                                                   | Two people booking the last train seat in the same second.                                | A retry arrives while the first request is still running.                    |
| **Paise**               | One hundredth of a rupee. Whole numbers avoid rounding errors.                                           | ₹125.50 is 12550 paise.                                                                   | `"amountPaise": 12550`                                                       |

# 2 · Build: Spec

## Business problem

**Paysetu** (a fictional UPI-style payments app) lets people pay each other from their phones. On a weak 4G signal, Asha taps *Pay ₹125.50 to ravi@oksbi*. The server charges her, but the reply never reaches the phone. After 10 seconds the app shows "Something went wrong", and its retry logic sends the same payment again. The server treats it as a new payment and charges Asha a second time.

In a real payments app, Asha's money would be stuck until a refund went through, which takes days. (This station records payments only; see the simulation note at the top.) Support gets a "charged twice" ticket, and Paysetu loses her trust. The client cannot tell a timeout that happened *before* the charge from one that happened *after* it, so retries cannot be avoided. The server has to make them safe.

## Acceptance criteria

1.  **Given** a new `Idempotency-Key`, **when** the app sends a valid payment, **then** one payment is created and the API returns `201` with `Location` and `Idempotent-Replayed: false`.
2.  **Given** a key already used with the same body, **when** the app retries, **then** no new payment is created and the API returns the original status, the original response body and the same `Location`, with `Idempotent-Replayed: true`.
3.  **Given** a key already used with a different body, **when** the app sends it, **then** the API returns `422` and charges nothing.
4.  **Given** 20 identical requests that arrive at the same moment, **then** exactly one payment exists and all 20 responses carry the same `paymentId`.
5.  **Given** no `Idempotency-Key` header, **then** the API returns `400` and charges nothing.
6.  **Given** the server fails after saving the payment but before saving the response, **then** nothing is kept, and a retry with the same key succeeds once.
7.  **Given** two different payers who happen to send the same key string, **then** each gets their own payment.

## Requirements

- `POST /payments` requires an `Idempotency-Key` header: 8–64 characters from `A–Z a–z 0–9 - _`. The client creates one key per payment (a UUID works) and sends the same key on every retry of that payment.
- Keys are scoped to the payer: `(payerVpa, key)` is unique, not the key alone.
- A key is bound to its request. The fingerprint is a SHA-256 of payer, payee, amount and note. VPAs are compared in lower case using a fixed locale. A missing note and an empty note are the same; any other note text is part of the payment. JSON spacing and field order do not change it.
- A key belongs to one logical payment. The client reuses it only to resend *that* payment, never for a different one. The retry rules are in the API contract tab.
- Amounts are whole paise (`12550` = ₹125.50), from 1 up to 10,000,000 (₹1,00,000, a demo rule for this station). Never a decimal.
- Payer and payee must be different, in any letter case.
- The database enforces the amount range, different parties and a complete stored response too, so a bug or a script that skips Java validation still cannot break them.
- Every error is an RFC 9457 `application/problem+json` body. Validation errors list each field.
- Requests that fail validation do not use up the key.
- `GET /payments/{id}` returns the payment, or `404`.
- Keys are kept for at least 24 hours, which is longer than any client retries. The cleanup job is out of scope; the index for it is provided.

## Learning objectives

After this station you can:

- Explain why a timeout is ambiguous, and why that makes retries unavoidable.
- Design the idempotency flow: claim the key, do the work, store the response, replay it.
- Use a database unique constraint as the lock, instead of check-then-insert.
- Bind a key to a request fingerprint and reject reuse with `422`.
- Keep the key, the payment and the stored response in one transaction.
- Explain why Java validation and database constraints are partners, not alternatives.
- Prove the rule holds with a real concurrent test against real PostgreSQL.

# 2 · Build: API contract

## Endpoints

| Method | Path             | Purpose                                      |
|--------|------------------|----------------------------------------------|
| `POST` | `/payments`      | Pay another VPA. Requires `Idempotency-Key`. |
| `GET`  | `/payments/{id}` | Read one payment.                            |

## Request body for `POST /payments`

| Field         | Type    | Rule                                                                        |
|---------------|---------|-----------------------------------------------------------------------------|
| `payerVpa`    | string  | Required. `name@bank`, at most 255 characters.                              |
| `payeeVpa`    | string  | Required. Same format. Must differ from the payer.                          |
| `amountPaise` | integer | Required. 1 to 10,000,000 (₹0.01 to ₹1,00,000; the maximum is a demo rule). |
| `note`        | string  | Optional. At most 80 characters.                                            |

## Status codes

| Status | When                                                  | Body                                                                                  | Safe to retry with the same key?           |
|--------|-------------------------------------------------------|---------------------------------------------------------------------------------------|--------------------------------------------|
| 201    | New payment created                                   | Payment, `Idempotent-Replayed: false`                                                 | Yes, you get a replay                      |
| 201    | Replay of an earlier success                          | The original status, body (byte for byte) and `Location`; `Idempotent-Replayed: true` | Yes                                        |
| 400    | Missing or malformed key, invalid fields, broken JSON | Problem with `errors` per field                                                       | Only after fixing the request              |
| 422    | Key already used with a different body                | Problem: *Idempotency key reused*                                                     | No. Use a new key for a new payment        |
| 404    | `GET` for an unknown id                               | Problem: *Payment not found*                                                          | n/a                                        |
| 500    | Unexpected failure                                    | Problem                                                                               | Yes, with the same key. See the note below |

Retry rules for the client

A key is not just a request id. It is bound to one logical payment: its payer, payee, amount and note.

| What happened                              | Outcome                                         | What the client does                                                                                                                      |
|--------------------------------------------|-------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| Timeout, dropped connection, `5xx`         | Unknown: the payment may or may not exist       | Resend the **same** request with the **same** key. If the original committed, you get its saved result; if it rolled back, it runs fresh. |
| `400` invalid request                      | Nothing was stored; the key was not used        | Fix the request and send it. Reusing the same key is fine, because it was never bound.                                                    |
| `422` key reused                           | The key is already bound to a different payment | Do not use this key for the new payment. Create a new key.                                                                                |
| `201`                                      | Done                                            | Keep the key only for resending this same payment.                                                                                        |
| More than 24 hours since the first attempt | The key may have been deleted                   | Stop retrying. A retry now could create a second payment.                                                                                 |

**What "the same response" means here.** A replay returns the original HTTP status, the original response body (byte for byte) and the same `Location`. One header differs on purpose: `Idempotent-Replayed` is `false` the first time and `true` on a replay. That is why a replay is `201` and not `200`: the app needs no special code for retries, and the header is there for logs and debugging.

Where `400` and `422` come from: they match what the IETF *Idempotency-Key* header draft recommends. That draft (draft-07, October 2025) has expired and is not a published standard, so read them as this API's deliberate design choices. Check the current status yourself on the [IETF Datatracker](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/); checking a standard's status is part of the job.

## Captured examples

Captured with curl from the running app on 11 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: a new payment

**Why:** the key is new, so the server creates the payment. `201 Created`, and `Location` points to the new payment.

Request

``` code
POST /payments HTTP/1.1
Idempotency-Key: 7f3c9a2e-5b1d-4e8a-9c6f-2d4b8e1a0c37
Content-Type: application/json

{
  "payerVpa": "asha@okpaysetu",
  "payeeVpa": "ravi@oksbi",
  "amountPaise": 12550,
  "note": "Dinner split"
}
```

Response

``` code
HTTP/1.1 201 
Location: /payments/cac03584-ce89-4936-901e-26a48da8105c
Idempotent-Replayed: false
Content-Type: application/json
Content-Length: 207

{
  "paymentId": "cac03584-ce89-4936-901e-26a48da8105c",
  "payerVpa": "asha@okpaysetu",
  "payeeVpa": "ravi@oksbi",
  "amountPaise": 12550,
  "note": "Dinner split",
  "status": "SUCCESS",
  "createdAt": "2026-10-11T07:16:26.550517Z"
}
```

### Case 2: same key, same details

**Why:** the server recognises a retry. It returns the saved first response: same `paymentId`, same `createdAt`. `Idempotent-Replayed: true` says it is a replay. No new payment.

Request

``` code
POST /payments HTTP/1.1
Idempotency-Key: 7f3c9a2e-5b1d-4e8a-9c6f-2d4b8e1a0c37
Content-Type: application/json

{
  "payerVpa": "asha@okpaysetu",
  "payeeVpa": "ravi@oksbi",
  "amountPaise": 12550,
  "note": "Dinner split"
}
```

Response

``` code
HTTP/1.1 201 
Location: /payments/cac03584-ce89-4936-901e-26a48da8105c
Idempotent-Replayed: true
Content-Type: application/json
Content-Length: 207

{
  "paymentId": "cac03584-ce89-4936-901e-26a48da8105c",
  "payerVpa": "asha@okpaysetu",
  "payeeVpa": "ravi@oksbi",
  "amountPaise": 12550,
  "note": "Dinner split",
  "status": "SUCCESS",
  "createdAt": "2026-10-11T07:16:26.550517Z"
}
```

### Case 3: same key, different amount

**Why:** the amount changed from ₹125.50 to ₹999. One key must not stand for two different payments, so the server refuses with `422` and charges nothing. A genuinely new payment needs a new key.

Request

``` code
POST /payments HTTP/1.1
Idempotency-Key: 7f3c9a2e-5b1d-4e8a-9c6f-2d4b8e1a0c37
Content-Type: application/json

{
  "payerVpa": "asha@okpaysetu",
  "payeeVpa": "ravi@oksbi",
  "amountPaise": 99900,
  "note": "Dinner split"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "Idempotency-Key 7f3c9a2e-5b1d-4e8a-9c6f-2d4b8e1a0c37 was already used with a different request body. Use a new key for a new payment.",
  "instance": "/payments",
  "status": 422,
  "title": "Idempotency key reused"
}
```

### Case 4: no key

**Why:** without a key the server cannot tell a retry from a new payment, so it refuses with `400` before touching the database.

Request

``` code
POST /payments HTTP/1.1
Content-Type: application/json

{
  "payerVpa": "asha@okpaysetu",
  "payeeVpa": "ravi@oksbi",
  "amountPaise": 12550,
  "note": "Dinner split"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Required header 'Idempotency-Key' is not present.",
  "instance": "/payments",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 5: invalid details

**Why:** the payer VPA has no `@bank` part and the amount is 0. `400` with one message per field, so the app can show each error next to its input. The key is not used up.

Request

``` code
POST /payments HTTP/1.1
Idempotency-Key: 0b8e4f6a-1c2d-4e3f-8a9b-7c6d5e4f3a2b
Content-Type: application/json

{
  "payerVpa": "asha",
  "payeeVpa": "ravi@oksbi",
  "amountPaise": 0
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "The payment request has invalid fields.",
  "instance": "/payments",
  "status": 400,
  "title": "Bad Request",
  "errors": {
    "amountPaise": "must be greater than 0",
    "payerVpa": "must look like name@bank"
  }
}
```

### Case 6: read a payment

**Why:** the same data as the create response, read back from the database.

Request

``` code
GET /payments/cac03584-ce89-4936-901e-26a48da8105c HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 207

{
  "paymentId": "cac03584-ce89-4936-901e-26a48da8105c",
  "payerVpa": "asha@okpaysetu",
  "payeeVpa": "ravi@oksbi",
  "amountPaise": 12550,
  "note": "Dinner split",
  "status": "SUCCESS",
  "createdAt": "2026-10-11T07:16:26.550517Z"
}
```

### Case 7: unknown payment

**Why:** no payment has this id, so `404` with a problem body.

Request

``` code
GET /payments/00000000-0000-0000-0000-000000000000 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No payment with id 00000000-0000-0000-0000-000000000000",
  "instance": "/payments/00000000-0000-0000-0000-000000000000",
  "status": 404,
  "title": "Payment not found"
}
```

# 2 · Build: Edge cases & trap

## Edge cases and failure cases

| Case                                                          | What the API does                                                                                       | Proved by                                                               |
|---------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| Retry after a timeout, same body                              | Replays the stored response. One payment.                                                               | `sameKeyAndBodyReplaysTheFirstResponseExactly`                          |
| 20 identical requests at the same moment                      | One payment. All 20 get the same `paymentId`.                                                           | `twentyParallelRetriesWithTheSameKeyCreateOnePayment`                   |
| 20 different keys at the same moment                          | 20 payments. No false de-duplication.                                                                   | `twentyParallelPaymentsWithDifferentKeysAllGoThrough`                   |
| Same key, different amount                                    | `422`, nothing charged.                                                                                 | `sameKeyWithADifferentAmountIs422AndChargesNothingMore`                 |
| Same key string, different payer                              | Independent payments.                                                                                   | `keysAreScopedPerPayerSoTwoCustomersCanPickTheSameKey`                  |
| Same key, different payee                                     | `422`, nothing charged.                                                                                 | `sameKeyWithADifferentPayeeIs422`                                       |
| Same content, JSON reordered or re-spaced                     | Treated as the same request: replay.                                                                    | `sameContentWithDifferentJsonFormattingIsStillAReplay`                  |
| Note left out, then sent as `""`                              | Same payment: replay. A written note, even a space, is a different payment.                             | `omittedNoteThenEmptyNoteIsAReplay`, `anyWrittenNoteIsPartOfThePayment` |
| VPA in different letter case                                  | Same payer, same payment: replay.                                                                       | `mixedCaseVpaIsTheSamePayerAndTheSamePayment`                           |
| Server running with a Turkish locale                          | Fingerprint unchanged (`Locale.ROOT`). Without it, `I` becomes a dotless `ı` and retries stop matching. | `aTurkishServerLocaleDoesNotChangeTheFingerprint`                       |
| Request fails validation                                      | `400`; the key stays free for the corrected request.                                                    | `aFailedValidationDoesNotUseUpTheKey`                                   |
| Crash after the payment insert                                | Everything rolls back; the retry succeeds once.                                                         | `aFailureAfterThePaymentInsertRollsBackTheKeyAndThePayment`             |
| Amount 0 or above the maximum slips past Java validation      | The database `CHECK` still rejects it.                                                                  | `databaseRejectsAmountsOutsideTheRangeEvenWithoutJavaValidation`        |
| Paying yourself, written in a different case, slips past Java | The database `CHECK` still rejects it.                                                                  | `databaseRejectsPayingYourselfInAnyLetterCase`                          |
| A stored response saved half-filled                           | The database rejects it; a replay always finds a complete response.                                     | `databaseRejectsAHalfFilledStoredResponse`                              |
| Missing or short key                                          | `400`                                                                                                   | `missingIdempotencyKeyIs400`, `malformedIdempotencyKeyIs400`            |
| Amount above ₹1,00,000; paying yourself; broken JSON          | `400` with field messages                                                                               | `PaymentContractTest`                                                   |
| Unknown payment id                                            | `404` problem                                                                                           | `unknownPaymentIs404Problem`                                            |
| Retry after the key was cleaned up                            | Charged again. Retention must be longer than any client retry window.                                   | Design rule (no cleanup job in this station)                            |

## The trap

Plausible but wrong

Retrying a timed-out payment without an idempotency key, which charges the customer twice.

The "before" code charges on every `POST`. It looks fine in a demo, where the network never drops a reply. The first test in this station reproduces the bug. It passes because it asserts the bug: two attempts, two charges. The second test runs the fixed API and gets one charge.

``` code
package com.paysetu.payments;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * The phone sends a payment, the network times out before the reply arrives, the app retries.
 */
@Import(RetryWithoutKeyTrapTest.NaivePaymentController.class)
class RetryWithoutKeyTrapTest extends ApiTest {

    /** The "before" code: every POST charges. Kept only in tests, to show the trap. */
    @RestController
    static class NaivePaymentController {
        private final PaymentRepository payments;

        NaivePaymentController(PaymentRepository payments) {
            this.payments = payments;
        }

        @PostMapping("/naive/payments")
        Payment pay(@RequestBody PaymentRequest req) {
            return payments.insert(req);
        }
    }

    @Test
    void retryWithoutAKeyChargesTheCustomerTwice() {
        for (int attempt = 1; attempt <= 2; attempt++) { // attempt 1 "timed out" on the phone, attempt 2 is the retry
            client.post().uri("/naive/payments").contentType(MediaType.APPLICATION_JSON).body(ASHA_PAYS_RAVI)
                    .exchange().expectStatus().isOk();
        }
        assertThat(paymentCount()).as("the bug: Asha paid Rs 125.50 twice").isEqualTo(2);
    }

    @Test
    void retryWithTheSameKeyChargesOnce() {
        pay("phone-retry-0001", ASHA_PAYS_RAVI).expectStatus().isCreated();
        pay("phone-retry-0001", ASHA_PAYS_RAVI).expectStatus().isCreated();
        assertThat(paymentCount()).as("the fix").isEqualTo(1);
    }
}
```

### The subtler trap

Adding a key is not enough. The obvious way to use it (look up the key, charge if absent, then save the key) still double-charges when retries overlap. Against the flawed version in the [Review](#review) tab, 20 parallel retries with one key produced these results in 5 runs:

| Run | Payments charged | Responses         |
|-----|------------------|-------------------|
| 1   | 19               | 2 × 201, 18 × 500 |
| 2   | 9                | 12 × 201, 8 × 500 |
| 3   | 2                | 19 × 201, 1 × 500 |
| 4   | 5                | 16 × 201, 4 × 500 |
| 5   | 4                | 17 × 201, 3 × 500 |

The correct answer is 1 every time. The fixed code gets 1 every time, which `PaymentConcurrencyTest` checks.

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                                           | Check with       |
|----------|-------------------------------------------------------------------|------------------|
| JDK      | 25 (recommended). JDK 21 also works, see below                    | `java -version`  |
| Docker   | Docker Desktop (Windows, macOS) or Docker Engine (Linux), running | `docker info`    |
| Maven    | Not needed: the project ships the Maven wrapper (`mvnw`)          |                  |
| curl     | Built into Windows 10+, macOS and Linux                           | `curl --version` |

**macOS / Linux**

``` code
docker compose up -d        # PostgreSQL 17 on localhost:5432
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 31 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21 instead of 25, add `-Djava.version=21`, for example `./mvnw -Djava.version=21 test`. All 31 tests passed this way on JDK 21.0.12. Nothing in this station needs a Java 25 feature.

## Try it yourself

With the app running, open a second terminal in the project folder. The request body is in `docs/payment.json`, so the same commands work in PowerShell and in bash.

``` code
# 1. Pay once: expect HTTP 201 and Idempotent-Replayed: false
curl -i -X POST http://localhost:8080/payments -H "Idempotency-Key: try-it-0001" -H "Content-Type: application/json" -d "@docs/payment.json"

# 2. Retry with the same key: expect HTTP 201 and Idempotent-Replayed: true
curl -i -X POST http://localhost:8080/payments -H "Idempotency-Key: try-it-0001" -H "Content-Type: application/json" -d "@docs/payment.json"

# 3. Same key, different amount: expect HTTP 422
curl -i -X POST http://localhost:8080/payments -H "Idempotency-Key: try-it-0001" -H "Content-Type: application/json" -d "@docs/payment-changed-amount.json"

# 4. Count payments in the database: expect 1
docker compose exec postgres psql -U paysetu -d paysetu -c "SELECT count(*) AS payments FROM payments"
```

Three requests, one payment. Now try request 1 with a new key such as `try-it-0002`, count again, and explain the result to yourself. In PowerShell, write `curl.exe` instead of `curl` if `curl` opens a different command.

## Troubleshooting

| You see                                     | Cause                                                         | Fix                                                                                                    |
|---------------------------------------------|---------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| `Could not find a valid Docker environment` | Docker is not running. Testcontainers needs it for the tests. | Start Docker Desktop, wait until it says running, then run the tests again.                            |
| `release version 25 not supported`          | Maven is using an older JDK.                                  | Point `JAVA_HOME` at JDK 25, or use the JDK 21 command below.                                          |
| `Connection to localhost:5432 refused`      | The app started before PostgreSQL, or compose is not up.      | Run `docker compose up -d`, wait a few seconds, start the app again.                                   |
| `port 5432 is already allocated`            | A local PostgreSQL already uses the port.                     | Stop it, or change `"5432:5432"` to `"5433:5432"` in `compose.yaml` and the URL in `application.yaml`. |
| `'./mvnw' is not recognized` on Windows     | PowerShell needs the `.cmd` file.                             | Use `.\mvnw.cmd` instead of `./mvnw`.                                                                  |

## Project layout

``` tree
stations/085-idempotent-upi-payments/
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
└── docs/                          (payment.json for curl, captures, saved test runs)
```

## Code walkthrough

Files are listed in the order a request travels: in at the controller, through the service, out to the database.

#### `src/main/java/com/paysetu/payments/PaymentController.java`

Does  
Receives `POST /payments` and `GET /payments/{id}`, checks the header format, and returns the stored response with `Location` and `Idempotent-Replayed`.

Why  
Keeps HTTP details (headers, status codes) out of the business logic.

Without it  
No endpoint. Put this logic in the service instead and it becomes hard to test without HTTP.

- Returns `ResponseEntity<String>` because the body is already JSON from the store. A replay has the original status, body and `Location`; only `Idempotent-Replayed` differs.

#### `src/main/java/com/paysetu/payments/PaymentRequest.java`

Does  
Holds the request fields with their validation rules, and computes the fingerprint.

Why  
One place defines what a valid payment is and what makes two requests "the same payment".

Without it  
Bad input reaches the database, and a retry with different formatting would not be recognised.

- `normalise()` lower-cases VPAs with `Locale.ROOT`; every VPA comparison goes through it.
- A missing note and an empty note give the same fingerprint, by design.

#### `src/main/java/com/paysetu/payments/PaymentService.java`

Does  
Runs the whole flow in one transaction: claim the key, compare the fingerprint, create the payment, store the response.

Why  
The transaction is what makes the key, the payment and the response appear together or not at all.

Without it  
Split this across separate calls and a crash between them leaves a payment with no key, which a retry charges again (see the Review tab).

- `claim` returning `false` means another request owns this key (we may have waited for it to commit).

#### `src/main/java/com/paysetu/payments/IdempotencyKeyRepository.java`

Does  
Claims a key with `INSERT … ON CONFLICT DO NOTHING`, saves the response, and reads a stored one back.

Why  
The database's unique key decides which of two simultaneous requests wins. No Java lock can do that across several servers.

Without it  
Back to check-then-insert, which charged up to 19 times for one key in the Edge cases tab.

#### `src/main/java/com/paysetu/payments/PaymentRepository.java`

Does  
Inserts and reads payments with plain SQL.

Why  
Every statement is visible, which helps while learning.

Without it  
No payments. Use JPA instead and the SQL is hidden, which suits later stations.

- Times are truncated to microseconds, so the response matches what PostgreSQL stores and later returns.

#### `src/main/java/com/paysetu/payments/Payment.java`

Does  
One record that is both the stored payment and the response body.

Why  
A separate response class would add nothing yet.

Without it  
Nowhere to hold a payment.

#### `src/main/java/com/paysetu/payments/ApiErrors.java`

Does  
Adds an `errors` map (field → message) to validation errors.

Why  
Spring already returns RFC 9457 problem bodies; the app needs to know which field is wrong.

Without it  
Clients get "invalid request" with no hint which field to fix.

- Because the header has a constraint, body errors arrive as `HandlerMethodValidationException`. Handling only `MethodArgumentNotValidException` was a real bug the contract tests caught while this station was built.

#### `src/main/resources/db/migration/V1__payments_and_idempotency_keys.sql`

Does  
Creates both tables with their constraints when the app starts (Flyway).

Why  
The schema is versioned with the code. Later changes are new files (`V2__…`), never edits to a released one.

Without it  
Someone creates tables by hand, and the constraints that protect the payment records are missing.

#### `src/main/java/com/paysetu/payments/PaymentsApplication.java`

Standard Spring Boot entry point.

#### `src/main/resources/application.yaml`

Local database settings. Tests replace them with their own container automatically.

#### `pom.xml`

Spring Boot 4.1.1, Java 25. Only the starters this station uses. Test side: Testcontainers 2 for a real PostgreSQL, and `RestTestClient` for real HTTP calls.

#### `compose.yaml`

PostgreSQL 17 for running the app locally. Tests do not need it; they start their own container.

# 2 · Build: Tests

## Required tests for this station

Station types: Database Concurrency Idempotency

| Required by   | Requirement                                             | Test class                                            | Result |
|---------------|---------------------------------------------------------|-------------------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                | `PaymentContractTest` (9)                             | pass   |
| Every station | Reproduce the failure before the fix                    | `RetryWithoutKeyTrapTest` (2)                         | pass   |
| Database      | Rollback and constraint tests against a real database   | `PaymentDatabaseTest` (5)                             | pass   |
| Concurrency   | A real concurrency test that proves the invariant holds | `PaymentConcurrencyTest` (2)                          | pass   |
| Idempotency   | Replay: the same request twice gives one effect         | `IdempotencyReplayTest` (8), `PaymentRequestTest` (5) | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Docker via Testcontainers 2.0.5. Run on 11 Oct 2026. Nothing skipped, and no in-memory database. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payments.PaymentConcurrencyTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payments.PaymentDatabaseTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payments.RetryWithoutKeyTrapTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payments.PaymentRequestTest
[INFO] Tests run: 9, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payments.PaymentContractTest
[INFO] Tests run: 8, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payments.IdempotencyReplayTest
[INFO] Tests run: 31, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/paysetu/payments/RetryWithoutKeyTrapTest.java`

Written first. Reproduces the double charge, then shows the fix.

#### `src/test/java/com/paysetu/payments/PaymentRequestTest.java`

Plain unit tests for the fingerprint rules: letter case, a Turkish server locale, missing versus empty note, every field. No Spring, so they run in milliseconds.

#### `src/test/java/com/paysetu/payments/PaymentContractTest.java`

The HTTP contract: valid, invalid, not found, missing and malformed key, broken JSON.

#### `src/test/java/com/paysetu/payments/IdempotencyReplayTest.java`

Replays; key reuse with a different amount or payee; JSON formatting; missing versus empty note; letter case; per-payer scope; validation failures not using up the key.

#### `src/test/java/com/paysetu/payments/PaymentConcurrencyTest.java`

20 real HTTP requests released together on virtual threads. One test proves one payment per key; the other proves different keys are not merged.

#### `src/test/java/com/paysetu/payments/PaymentDatabaseTest.java`

Amount range, different parties and a complete stored response hold without Java validation. A crash injected after the payment insert rolls back the key and the payment.

#### `src/test/java/com/paysetu/payments/ApiTest.java`

Shared setup: the whole app on a random port, real HTTP, tables emptied before each test.

#### `src/test/java/com/paysetu/payments/PostgresTestConfig.java`

A real PostgreSQL 17 in Docker via Testcontainers. Spring wires it in with `@ServiceConnection`.

# 2 · Build: Practice

## How to do a challenge

1.  Download the starter project; the solutions are a separate pack, and on this page they open only when you click. Copy the challenge test from `challenge/` into `src/test/java/com/paysetu/payments/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=KeyCleanupChallengeTest`
3.  Write the code until it passes. Then run `./mvnw test` to check the other 31 tests still pass.

Checked on 11 Oct 2026 (`docs/challenge-run.txt`): with the reference solutions copied in, all 34 tests pass (31 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 45 minutes

## Old keys expire after 24 hours

Right now `idempotency_keys` grows forever. Add a Spring bean `IdempotencyKeyCleanup` with a method `int deleteKeysOlderThan(Duration age)` that deletes old keys and returns how many it deleted. Then run it every night.

**Done when:** both tests in `KeyCleanupChallengeTest` pass. The second test shows why retention must be longer than any client retry: after cleanup, the same key creates a new payment.

Hints

- The table already has an index on `created_at`; your `DELETE` should use it.
- Delete keys, never payments. A payment is a financial record.
- `@Scheduled(cron = …)` runs a method on a timetable. It needs `@EnableScheduling` somewhere.

#### `challenge/KeyCleanupChallengeTest.java`

``` code
package com.paysetu.payments;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * CHALLENGE 1: keys must not live forever.
 * Copy this file into src/test/java/com/paysetu/payments/ and make it pass.
 * You need a Spring bean IdempotencyKeyCleanup with: int deleteKeysOlderThan(Duration age)
 */
class KeyCleanupChallengeTest extends ApiTest {

    @Autowired
    IdempotencyKeyCleanup cleanup;

    @Test
    void deletesOnlyKeysOlderThanTheRetentionWindow() {
        pay("old-key-000001", ASHA_PAYS_RAVI).expectStatus().isCreated();
        pay("new-key-000001", ASHA_PAYS_RAVI.replace("12550", "500")).expectStatus().isCreated();
        ageKey("old-key-000001", 25);

        int deleted = cleanup.deleteKeysOlderThan(Duration.ofHours(24));

        assertThat(deleted).isEqualTo(1);
        assertThat(jdbc.sql("SELECT idem_key FROM idempotency_keys").query(String.class).list())
                .containsExactly("new-key-000001");
        assertThat(paymentCount()).as("payments are records; only keys expire").isEqualTo(2);
    }

    @Test
    void aRetryAfterCleanupIsTreatedAsANewPayment() {
        pay("late-retry-0001", ASHA_PAYS_RAVI).expectStatus().isCreated();
        ageKey("late-retry-0001", 25);
        cleanup.deleteKeysOlderThan(Duration.ofHours(24));

        pay("late-retry-0001", ASHA_PAYS_RAVI)
                .expectStatus().isCreated()
                .expectHeader().valueEquals("Idempotent-Replayed", "false");
        // This is why retention must be longer than the longest client retry window.
        assertThat(paymentCount()).isEqualTo(2);
    }

    private void ageKey(String key, int hours) {
        jdbc.sql("UPDATE idempotency_keys SET created_at = now() - make_interval(hours => ?) WHERE idem_key = ?")
                .params(hours, key)
                .update();
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Count replays and key reuse

On-call engineers need to see retries. Count two events with Micrometer: `paysetu.payments.replayed` when a saved response is returned, and `paysetu.payments.key_reused` when a key comes back with different details.

**Done when:** `ReplayMetricsChallengeTest` passes and the other tests still pass.

Hints

- Add `spring-boot-starter-actuator` to `pom.xml`; it provides a `MeterRegistry` bean.
- Create both counters once, in the constructor, not on every request.
- Increment only on the replay and 422 paths, not on the first payment.

#### `challenge/ReplayMetricsChallengeTest.java`

``` code
package com.paysetu.payments;

import io.micrometer.core.instrument.MeterRegistry;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * CHALLENGE 2: make retries visible to the on-call engineer.
 * Copy this file into src/test/java/com/paysetu/payments/ and make it pass.
 * Count two things with Micrometer:
 *   paysetu.payments.replayed    - a stored response was returned
 *   paysetu.payments.key_reused  - a key came back with a different body (422)
 * Hint: add spring-boot-starter-actuator to pom.xml to get a MeterRegistry.
 */
class ReplayMetricsChallengeTest extends ApiTest {

    @Autowired
    MeterRegistry meters;

    @Test
    void countsReplaysAndKeyReuse() {
        double replayedBefore = count("paysetu.payments.replayed");
        double reusedBefore = count("paysetu.payments.key_reused");

        pay("metrics-key-001", ASHA_PAYS_RAVI).expectStatus().isCreated();
        pay("metrics-key-001", ASHA_PAYS_RAVI).expectStatus().isCreated();
        pay("metrics-key-001", ASHA_PAYS_RAVI.replace("12550", "99900")).expectStatus().isEqualTo(422);

        assertThat(count("paysetu.payments.replayed") - replayedBefore).isEqualTo(1);
        assertThat(count("paysetu.payments.key_reused") - reusedBefore).isEqualTo(1);
    }

    private double count(String name) {
        return meters.counter(name).count();
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · Go deeper · design on paper, no code

## The charge becomes a call to a bank

The payment is no longer a row in your database. It is an HTTP call to a bank that takes 2 to 8 seconds and cannot be rolled back. Redesign the flow on paper and answer:

1.  Where does your database transaction start and end now? Why can it not stay open during the bank call?
2.  What does a second request with the same key see while the first is still waiting for the bank? Which status code do you return?
3.  The bank says yes, then your server crashes before saving the result. What happens on the retry, and how do you find out what the bank did?

Compare your answer with the interview question about a bank call and the two-phase row in the Design tab's alternatives.

Challenge 4 · Go deeper · design on paper, no code

## Keep the keys table small at 50 million payments a day

Daily `DELETE`s of millions of rows are slow and bloat the table. Dropping a whole day's partition is instant. But PostgreSQL requires a primary key on a partitioned table to include the partition column, and `(payer_vpa, idem_key)` does not include `created_at`.

1.  If you partition by day and change the key to `(payer_vpa, idem_key, created_at)`, what can now go wrong when a retry arrives just after midnight?
2.  What do you gain and lose by hash-partitioning on `payer_vpa` instead?
3.  Would you keep deleting in batches, accept the bloat, or move keys to a store with built-in expiry? Which number would make you change your mind?

Background: the PostgreSQL documentation on table partitioning, "Limitations" section.

# 3 · Go deeper: Design

## Implementation approach

1.  **Validate** the header and body. A bad request gets `400` before the database is touched, so it does not use up the key.
2.  **Fingerprint** the request: SHA-256 of payer, payee, amount and note.
3.  **Begin** one transaction.
4.  **Claim** the key: `INSERT … ON CONFLICT DO NOTHING`. One row inserted means this request owns the key. If another transaction is inserting the same key, PostgreSQL makes this insert wait until that transaction ends.
5.  **If not claimed**, read the stored row. If the fingerprint differs, return `422`. Otherwise return the stored status and body with `Idempotent-Replayed: true`.
6.  **Charge**: insert the payment.
7.  **Store the response**: serialise it once and save it on the key row with the payment id.
8.  **Commit.** The key, the payment and the response become visible together, or not at all.
9.  **Return** the stored status and body as-is, with the same `Location`. Only `Idempotent-Replayed` tells a replay apart.

## Two retries at the same moment

``` mermaid
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
```

## Design alternatives and trade-offs

| Approach                                                                                                 | What it costs                                                                                                                                                             | Verdict                      |
|----------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------|
| **Unique constraint claims the key**, all in one transaction                                             | A waiting retry holds a DB connection until the first finishes. Works only when the effect is in the same database.                                                       | Chosen                       |
| Check-then-insert: `SELECT` the key, charge, then `INSERT` the key                                       | Two requests both see "no key" and both charge. Measured above: up to 19 charges.                                                                                         | Wrong                        |
| `SELECT … FOR UPDATE`                                                                                    | You cannot lock a row that does not exist yet, which is exactly the first-request case.                                                                                   | Wrong                        |
| Redis `SET NX` with a TTL                                                                                | Fast, with expiry built in. But the key and the payment live in two stores with no shared transaction; a crash between them leaves them out of step.                      | When the effect is elsewhere |
| PostgreSQL advisory lock on a hash of the key                                                            | Works, but a hash can collide and the rule is invisible in the schema. A constraint documents itself.                                                                     | Possible                     |
| Two-phase key: commit `IN_PROGRESS`, call the bank, then mark `COMPLETED`; a concurrent retry gets `409` | Needed when the charge is an external call that cannot sit inside your database transaction, as with a real bank or PSP. Costs a recovery job for keys stuck in progress. | Later stations               |
| De-duplicate by business fields (same payer, payee and amount within 5 minutes)                          | Blocks real repeat payments, such as two ₹20 chai payments to the same stall.                                                                                             | Wrong                        |
| Server-issued intent: the client first creates a payment intent or order, then confirms it               | Also correct, and common at large PSPs. Costs one extra round trip and a new resource to manage.                                                                          | Valid alternative            |

One deliberate difference from Stripe's API v1: Stripe stores and replays even a `500` response, because its side effects may already have happened. Here, a `500` raised inside `pay()` rolls the transaction back, so a same-key retry runs fresh. A failure the client sees *after* the commit (a lost reply, a proxy error) is answered by a replay. Both cases are safe only because the key, the payment and the response share one transaction.

## Database design

| Table              | Key and constraints                                                                                                                                                         | Why                                                                                                                                                                                                                                |
|--------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `payments`         | PK `id` (UUID). `payments_amount_range`: 1 to 10,000,000 paise. `payments_different_parties`: payer ≠ payee, any case. `BIGINT` paise.                                      | The effect. The same rules as `PaymentRequest`, enforced again: Java gives friendly messages, the database guarantees them even when Java is bypassed.                                                                             |
| `idempotency_keys` | PK `(payer_vpa, idem_key)`. FK `payment_id → payments.id`. `idempotency_keys_result_complete`: the three result columns are all empty or all filled. Index on `created_at`. | The PK is the lock and the per-payer scope. The result columns are empty only inside the claiming transaction, which no one else can see, and the check stops a half-saved response. The index serves the cleanup job in Practice. |

**Transaction boundary:** `PaymentService.pay` is `@Transactional` at PostgreSQL's default `READ COMMITTED`. That level is enough: after the waiting insert returns 0 rows, the next `SELECT` takes a fresh snapshot and sees the committed row.

``` code
-- The same business rules as PaymentRequest, enforced again by the database.
-- Java validation gives friendly messages; these constraints hold even when Java is bypassed
-- (a script, another service, a bug). They are partners, not alternatives.
CREATE TABLE payments (
    id           UUID         PRIMARY KEY,
    payer_vpa    VARCHAR(255) NOT NULL,
    payee_vpa    VARCHAR(255) NOT NULL,
    amount_paise BIGINT       NOT NULL,
    note         VARCHAR(80),
    status       VARCHAR(16)  NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL,
    CONSTRAINT payments_amount_range      CHECK (amount_paise BETWEEN 1 AND 10000000), -- Rs 0.01 to Rs 1,00,000 (demo rule)
    CONSTRAINT payments_different_parties CHECK (lower(payer_vpa) <> lower(payee_vpa))
);

-- One row per (payer, key). The primary key is the lock: a second insert of the
-- same pair waits for the first transaction, then sees its committed row.
CREATE TABLE idempotency_keys (
    payer_vpa       VARCHAR(255) NOT NULL,
    idem_key        VARCHAR(64)  NOT NULL,
    request_hash    CHAR(64)     NOT NULL,
    payment_id      UUID         REFERENCES payments (id),
    response_status SMALLINT,
    response_body   TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (payer_vpa, idem_key),
    -- The three result columns are empty while the claiming transaction runs, and all filled before it commits.
    -- Never half-filled: a replay must always find a complete stored response.
    CONSTRAINT idempotency_keys_result_complete CHECK (
        (payment_id IS NULL AND response_status IS NULL AND response_body IS NULL)
        OR (payment_id IS NOT NULL AND response_status IS NOT NULL AND response_body IS NOT NULL))
);

-- Lets a cleanup job delete keys older than the retention window without a full scan.
CREATE INDEX idx_idempotency_keys_created_at ON idempotency_keys (created_at);
```

# 3 · Go deeper: Production

## Real-world considerations

Security  
Keys are scoped per payer. With a global scope, anyone who reuses another person's key would receive that person's payment details. In production the payer comes from the authenticated token, never from the request body. `GET /payments/{id}` must also check that the signed-in user is the payer or the payee; a UUID is hard to guess, but knowing it is not permission. Answer `404` rather than `403`, so the API does not confirm the payment exists. A VPA is personal data under India's DPDP rules, so mask it in logs. All of this is taught in the Security stations.

Performance  
Each payment costs one extra insert and one update. Retries of the same key queue behind each other and hold a database connection while they wait, so a retry storm can drain the pool. Size the pool and keep client retries spaced out with backoff.

Reliability  
Retrying with the same key is safe *while the key is retained* (24 hours here): a replay if the original committed, a fresh run if it rolled back, or a `422` if the details changed. After cleanup the server has forgotten the key, and the same request creates a new payment. So the retention window must be longer than the longest client retry, and clients must give up before it ends (Practice challenge 1 shows this with a test). Real UPI payments are asynchronous (pending, then success or failure from the bank). This station simplifies to an immediate success; bank callbacks come in station 132.

Scale  
`idempotency_keys` grows by one row per payment. A daily cleanup of rows older than the retention window keeps it bounded (Practice challenge 1). Partitioning by day so old days can be dropped is *not* a drop-in change: PostgreSQL requires a primary key on a partitioned table to include the partition column, and `(payer_vpa, idem_key)` does not. Practice challenge 4 works through the trade-offs.

Cost  
About 200 bytes of stored response per payment, for 24 hours. Small next to the cost of one refund ticket.

Maintainability  
The flow lives in one service method. Pull it out into a shared filter or aspect only when a third endpoint needs it, not before.

## Signals to know

| Signal                                                                    | What it tells you                                                    |
|---------------------------------------------------------------------------|----------------------------------------------------------------------|
| Replay rate: responses with `Idempotent-Replayed: true` as a share of all | A jump means the network or a client is retrying more than usual.    |
| Rate of `422` key-reused responses                                        | Almost always a client bug: one key used for two different payments. |
| p99 latency of `POST /payments`                                           | Lock waits from same-key retries show up here first.                 |
| Rows in `idempotency_keys` older than 24 hours                            | Cleanup is not running.                                              |

# 3 · Go deeper: Interview

## Interview takeaways

Say your answer out loud, then open the strong answer.

What does idempotent mean, and is POST idempotent?

An operation is idempotent if doing it twice has the same effect as doing it once. HTTP defines GET, PUT and DELETE (among others) as idempotent, but not POST. A payment POST becomes idempotent only when the server makes it so, here with a client-supplied key.

Why can't the app check whether the payment went through before retrying?

The check can time out too, and it races with the original request, which may still be in progress. Only the server, which sees both requests, can decide safely. The key gives it the information to do that.

Why a unique constraint and not SELECT, then INSERT?

Two requests can both run the SELECT before either inserts, so both see "no key" and both charge. A unique constraint makes the database pick exactly one winner, atomically. In PostgreSQL the loser's insert waits for the winner to commit, then reports a conflict.

Same key, different amount: what do you return, and why?

422 Unprocessable Content. The (now expired) IETF Idempotency-Key draft suggested the same, but it is our design choice, not a standard requirement. Returning the old payment would make the client think the new amount was paid. Charging would break the key's promise. The client must use a new key for a new payment.

Two requests with the same key arrive together. Walk through your design.

Both try the insert. One gets the row; the other waits on the unique index. The first inserts the payment, stores the response and commits. The waiting insert then returns 0 rows; a fresh SELECT under READ COMMITTED sees the stored response, compares the fingerprint, and replays it.

What changes if the charge is an HTTP call to a bank?

You cannot hold a database transaction open across a slow external call, and you cannot roll the call back. Commit the key as IN_PROGRESS first, call the bank with your own idempotency reference, then mark it COMPLETED with the response. A concurrent retry gets 409 Conflict, and a recovery job resolves keys stuck in progress by asking the bank for the status.

A client got a 500 from a payment API. Should it retry, and with which key?

Yes, with the same key. If the server's transaction rolled back, the retry runs as a fresh payment. If it committed and only the reply was lost or mangled by a proxy, the retry gets the saved response. A new key is the mistake that charges twice. One limit: this holds only while the server still keeps the key (24 hours here); a retry after cleanup is a new payment.

How long do you keep keys?

Longer than any client will retry. Stripe's docs, for example, say keys can be pruned once they are at least 24 hours old. After pruning, the same key is treated as a new request, so a very late retry would charge again.

Redis or PostgreSQL for the keys?

If the effect is a row in PostgreSQL, keep the key there and use one transaction; correctness comes for free. Redis fits when the effect is somewhere else and you want built-in expiry, but then you must handle a crash between "key saved" and "effect done".

Why amounts in paise as integers?

Binary floating point cannot represent most decimal amounts exactly, so sums drift. Whole paise in a BIGINT are exact, and the API states the unit in the field name.

## Self-check rubric

| Area        | Meets the bar                                       | Above the bar                                                    |
|-------------|-----------------------------------------------------|------------------------------------------------------------------|
| Correctness | All 31 tests pass.                                  | You can say why each test would fail without the fix.            |
| Robustness  | Every edge case in the table is handled.            | You found a case the table does not list, and added a test.      |
| Design      | One transaction; the unique constraint is the lock. | You can argue when the two-phase design is needed instead.       |
| Tests       | Real PostgreSQL and real parallel requests.         | You broke the code on purpose and watched the right test go red. |
| Explanation | You can explain the flow in two minutes.            | You can draw the sequence diagram from memory.                   |

# 3 · Go deeper: Review

## The pull request

A teammate's version was approved and shipped. It passes the "send twice, get one payment" test. Read it and list every problem before opening the findings.

``` code
package com.paysetu.payments;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.web.ErrorResponseException;
import tools.jackson.databind.json.JsonMapper;

import java.util.UUID;

/**
 * REVIEW EXERCISE: this version was "approved" in a pull request and shipped.
 * It passes a simple "send twice, get one payment" test. Find what is wrong before reading the answers.
 * To see it fail: copy it over src/main/java/com/paysetu/payments/PaymentService.java and run mvn test.
 */
@Service
public class PaymentService {

    public record PaymentResult(UUID paymentId, int status, String body, boolean replayed) {
    }

    private record Earlier(UUID paymentId, String body) {
    }

    private final PaymentRepository payments;
    private final JdbcClient jdbc;
    private final JsonMapper json;

    PaymentService(PaymentRepository payments, JdbcClient jdbc, JsonMapper json) {
        this.payments = payments;
        this.jdbc = jdbc;
        this.json = json;
    }

    public PaymentResult pay(String idempotencyKey, PaymentRequest req) {
        // 1. Was this key used before?
        var earlier = jdbc.sql("SELECT payment_id, response_body FROM idempotency_keys WHERE idem_key = ?")
                .param(idempotencyKey)
                .query((rs, n) -> new Earlier(rs.getObject("payment_id", UUID.class), rs.getString("response_body")))
                .optional();
        if (earlier.isPresent()) {
            return new PaymentResult(earlier.get().paymentId(), 201, earlier.get().body(), true);
        }

        // 2. No: charge the customer.
        Payment payment = payments.insert(req);
        String body = json.writeValueAsString(payment);

        // 3. Remember the key for next time.
        jdbc.sql("""
                INSERT INTO idempotency_keys (payer_vpa, idem_key, request_hash, payment_id, response_status, response_body)
                VALUES (?, ?, ?, ?, 201, ?)
                """)
                .params(PaymentRequest.normalise(req.payerVpa()), idempotencyKey, req.fingerprint(), payment.paymentId(), body)
                .update();
        return new PaymentResult(payment.paymentId(), 201, body, false);
    }

    public Payment get(UUID id) {
        return payments.findById(id).orElseThrow(() -> {
            var problem = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No payment with id " + id);
            problem.setTitle("Payment not found");
            return new ErrorResponseException(HttpStatus.NOT_FOUND, problem, null);
        });
    }
}
```

## Findings

1No transaction

The payment insert commits on its own. When the key insert then fails (a parallel retry got there first), the customer is already charged and the client gets a 500.

**Test evidence:** `twentyParallelRetriesWithTheSameKeyCreateOnePayment`: 500 instead of 201. The probe counted 2 to 19 charges for one key.

2Check-then-act race

Two retries both run the SELECT, both see no key, and both charge. A single-threaded test never sees this.

**Test evidence:** Same concurrency test. The simple "send twice" trap test still passes, which is how this got approved.

3Key not scoped to the payer

The lookup uses only `idem_key`. If Meera's app picks the same key string as Asha's, Meera receives Asha's payment details, and Meera's payment never happens.

**Test evidence:** `keysAreScopedPerPayerSoTwoCustomersCanPickTheSameKey`: replay header was true, expected false.

4Fingerprint saved but never compared

Same key, new amount returns the old payment as 201. The client believes ₹999 was paid when only ₹125.50 was.

**Test evidence:** `sameKeyWithADifferentAmountIs422AndChargesNothingMore` and `sameKeyWithADifferentPayeeIs422`: got 201, expected 422.

5A crash leaves a charge without a key

If the process dies between the two inserts, the payment exists but the key does not, so the retry charges again.

**Test evidence:** `aFailureAfterThePaymentInsertRollsBackTheKeyAndThePayment` fails: it injects its crash in the step this version skips, so the crash never happens. With no transaction there is nothing to roll back anyway.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed `PaymentService` copied over the real one, then the full suite run.

| Test class                | Fixed version | Flawed version |
|---------------------------|---------------|----------------|
| `PaymentContractTest`     | 9 / 9         | 9 / 9          |
| `PaymentRequestTest`      | 5 / 5         | 5 / 5          |
| `RetryWithoutKeyTrapTest` | 2 / 2         | 2 / 2          |
| `IdempotencyReplayTest`   | 8 / 8         | 5 / 8          |
| `PaymentConcurrencyTest`  | 2 / 2         | 1 / 2          |
| `PaymentDatabaseTest`     | 5 / 5         | 4 / 5          |

The lesson: the tests a reviewer usually sees (contract and a simple retry) all pass. Only the concurrency, scope and key-reuse tests catch these bugs, which is why each station type requires its own tests.
