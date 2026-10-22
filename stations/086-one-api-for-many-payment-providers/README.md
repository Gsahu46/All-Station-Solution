# Station 086 · One API for many payment providers

Working Systems · 0–2 years · Core · Payments · Types: Database, Idempotency

Spring Boot 4.1.1 · Java 25 · adapter pattern · provider selection by configuration · JdbcClient · PostgreSQL 17 · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Both payment providers, sim-alpha and sim-beta, are simulations inside the app, not real companies: a charge or refund is an entry in memory and nothing is charged. Their formats and error codes are made up to differ the way real providers do. The orders are demo data.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 25 tests.

# 1 · Understand

## The problem in real life

1.  **Four months to switch**

    Paysetu wanted a second payment provider. Provider calls, rupee formats and error codes were spread across checkout, refunds and reports: switching took four months.

2.  **The quick failover**

    The next version tried provider B whenever provider A "failed". One evening A was slow: it took the money, but its answer timed out. The code took that as a failure and charged B as well. Customers paid twice.

3.  **The fix**

    Everything provider-specific moves into one adapter per provider, chosen by configuration. A timeout is not a failure: ask A what happened first, and try B only when A says it never charged.

"No answer" is not "no". After a timeout, find out what happened before you try anyone else.

## What are we building?

One payments API in front of two simulated providers, with one adapter each, picked by configuration, and refunds that always go back to the provider that took the money.

## An everyday analogy

You send a parcel with courier A and the tracking page does not load. Sending a second parcel with courier B means the friend may get two. You check with A first: delivered, lost, or never picked up. Only "never picked up" makes B a safe choice.

## How it works in 4 steps

1.  **Record** the payment (one per order) before calling anyone.
2.  **Charge** through the primary provider's adapter.
3.  **If it never arrived** (connection refused), try the fallback. **If it timed out**, ask the primary what happened.
4.  **Record the answer**: succeeded, declined, or unknown if nobody can tell yet; never charge a second provider then.

Check yourself: sim-alpha says "declined: insufficient funds". Should the API try sim-beta?

No. A decline is an answer about the customer's money, not a provider problem. Trying elsewhere would surprise the customer and the bank: `aDeclineIsAnAnswerNotAFailover`.

## What this station is not

- **No real providers.** Both are simulations in the app, with made-up formats; nothing is charged.
- **No webhooks.** Real providers also report results later by calling you; challenge 3 is about that.
- **No refund keys.** A retried refund is a second refund here, capped by the amount; station 085 shows idempotency keys.

## Key terms

| Term                 | Simple meaning                                                                         | Everyday example                                    | In this project                     |
|----------------------|----------------------------------------------------------------------------------------|-----------------------------------------------------|-------------------------------------|
| **Payment provider** | The company that actually takes the card or UPI payment for you.                       | The bank behind a card machine.                     | `sim-alpha`, `sim-beta` (simulated) |
| **Adapter**          | A small class that translates between your code and one provider's own way of talking. | A travel plug adapter.                              | `AlphaProvider`, `BetaProvider`     |
| **Failover**         | Trying a second provider when the first one does not work.                             | Calling a second taxi company.                      | `paysetu.fallback`                  |
| **Timeout**          | No answer in time. The request may or may not have been done.                          | A courier who does not call back: was it delivered? | `PaymentProvider.Unknown`           |
| **Status check**     | Asking the provider what happened to a payment, by your own reference.                 | Phoning the courier with the tracking number.       | `lookup`                            |
| **Decline**          | The provider's answer "no": not enough money, card blocked.                            | The card machine saying "declined".                 | `402`                               |

# 2 · Build: Spec

## Business problem

**Paysetu** (a fictional payments company): switching provider took four months because provider code was everywhere, and the first failover charged customers twice.

## Acceptance criteria

Demo rules of the simulations: an amount ending in 51 paise is declined for funds, ending in 05 declined by the card side; with sim-alpha, ending in 97 it charges and then times out, ending in 98 it refuses the connection. Payments ₹1 to ₹1,00,000.

1.  **Given** a healthy primary, **then** `201`, and the payment names the provider and its reference.
2.  **Given** a decline, **then** `402` with our reason, and no other provider is tried.
3.  **Given** a primary that cannot be reached, **then** the fallback takes the payment; neither reachable, `503`.
4.  **Given** a timeout, **then** the primary is asked first; if it cannot say, `202` "unknown" and no other provider is tried.
5.  **Given** the same order again, **then** the same answer and no new charge; another amount, `409`.
6.  **Given** a refund, **then** it goes to the provider that took the payment, never more than is left.

## Requirements

- Nothing outside the adapters knows a provider's formats, states or codes.
- The provider is chosen by configuration; a wrong name stops the app at start.
- The database allows one payment per order and never more refunded than paid.

## Learning objectives

- Hide each provider behind an adapter with one interface.
- Select implementations by configuration.
- Map each provider's errors to your own, and tell "not sent" from "unknown".
- Check the status before failing over after a timeout.

# 2 · Build: API contract

## Endpoints

| Method | Path                     | Purpose                                                                       |
|--------|--------------------------|-------------------------------------------------------------------------------|
| `POST` | `/payments`              | `{orderId, amountPaise}`: take a payment. Safe to repeat with the same order. |
| `POST` | `/payments/{id}/refunds` | `{amountPaise}`: refund part or all, through the provider that took it.       |

## Status codes

| Status | When                                                                                                            |
|--------|-----------------------------------------------------------------------------------------------------------------|
| 201    | Payment succeeded (also on a retry); refund done                                                                |
| 202    | Unknown: a provider may have charged and could not say; nothing else was tried                                  |
| 400    | Order id not 3 to 40 letters, digits or dashes; amount missing, a fraction or out of range                      |
| 402    | Declined, with `declineReason`                                                                                  |
| 404    | No such payment                                                                                                 |
| 409    | The order was sent with another amount; a refund larger than what is left, or of a payment that did not succeed |
| 503    | No provider could be reached (nothing charged); a refund's provider could not be reached (nothing refunded)     |

## Captured examples

Captured with curl from the running app on 22 Oct 2026, in this order. JSON bodies are indented for reading; `Date`, connection and standard security headers are left out.

### Case 1: a payment

**Why:** sim-alpha is primary and healthy.

Request

``` code
POST /payments HTTP/1.1
Content-Type: application/json

{
  "orderId": "ORD-1001",
  "amountPaise": 249900
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json

{
  "id": 1,
  "orderId": "ORD-1001",
  "amountPaise": 249900,
  "status": "succeeded",
  "provider": "sim-alpha",
  "providerRef": "ch_1",
  "declineReason": null,
  "refundedPaise": 0
}
```

### Case 2: the same order again, in lower case

**Why:** the same payment, the same answer; sim-alpha is not called.

Request

``` code
POST /payments HTTP/1.1
Content-Type: application/json

{
  "orderId": "ord-1001",
  "amountPaise": 249900
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json

{
  "id": 1,
  "orderId": "ORD-1001",
  "amountPaise": 249900,
  "status": "succeeded",
  "provider": "sim-alpha",
  "providerRef": "ch_1",
  "declineReason": null,
  "refundedPaise": 0
}
```

### Case 3: the same order, another amount

**Why:** `409`: probably a bug in the caller.

Request

``` code
POST /payments HTTP/1.1
Content-Type: application/json

{
  "orderId": "ORD-1001",
  "amountPaise": 100000
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Order ORD-1001 was already sent with a different amount",
  "instance": "/payments",
  "status": 409,
  "title": "Conflict"
}
```

### Case 4: a decline (amount ending in 51 paise)

**Why:** sim-alpha's `INSUFFICIENT_BALANCE` becomes our `INSUFFICIENT_FUNDS`, with `402`; sim-beta is not tried.

Request

``` code
POST /payments HTTP/1.1
Content-Type: application/json

{
  "orderId": "ORD-1002",
  "amountPaise": 249951
}
```

Response

``` code
HTTP/1.1 402 
Content-Type: application/json

{
  "id": 2,
  "orderId": "ORD-1002",
  "amountPaise": 249951,
  "status": "declined",
  "provider": "sim-alpha",
  "providerRef": null,
  "declineReason": "INSUFFICIENT_FUNDS",
  "refundedPaise": 0
}
```

### Case 5: sim-alpha charges, then its answer times out (amount ending in 97)

**Why:** the API asked sim-alpha, found the charge, and recorded it. sim-beta was not called.

Request

``` code
POST /payments HTTP/1.1
Content-Type: application/json

{
  "orderId": "ORD-1003",
  "amountPaise": 249997
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json

{
  "id": 3,
  "orderId": "ORD-1003",
  "amountPaise": 249997,
  "status": "succeeded",
  "provider": "sim-alpha",
  "providerRef": "ch_3",
  "declineReason": null,
  "refundedPaise": 0
}
```

### Case 6: sim-alpha refuses the connection (amount ending in 98)

**Why:** it certainly never charged, so sim-beta took the payment.

Request

``` code
POST /payments HTTP/1.1
Content-Type: application/json

{
  "orderId": "ORD-1004",
  "amountPaise": 249998
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json

{
  "id": 4,
  "orderId": "ORD-1004",
  "amountPaise": 249998,
  "status": "succeeded",
  "provider": "sim-beta",
  "providerRef": "T5001",
  "declineReason": null,
  "refundedPaise": 0
}
```

### Case 7: refund ₹1,000 of the first payment

**Why:** through sim-alpha, which took it.

Request

``` code
POST /payments/1/refunds HTTP/1.1
Content-Type: application/json

{
  "amountPaise": 100000
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 108

{
  "id": 1,
  "paymentId": 1,
  "amountPaise": 100000,
  "status": "succeeded",
  "provider": "sim-alpha",
  "providerRef": "rf_4"
}
```

### Case 8: refund the payment sim-beta took

**Why:** through sim-beta, although sim-alpha is primary.

Request

``` code
POST /payments/4/refunds HTTP/1.1
Content-Type: application/json

{
  "amountPaise": 249998
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 108

{
  "id": 2,
  "paymentId": 4,
  "amountPaise": 249998,
  "status": "succeeded",
  "provider": "sim-beta",
  "providerRef": "R5002"
}
```

### Case 9: refund more than is left

**Why:** `409`, saying how much is left.

Request

``` code
POST /payments/1/refunds HTTP/1.1
Content-Type: application/json

{
  "amountPaise": 200000
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "At most 149900 paise can still be refunded",
  "instance": "/payments/1/refunds",
  "status": 409,
  "title": "Conflict"
}
```

### Case 10: refund a declined payment

**Why:** `409`.

Request

``` code
POST /payments/2/refunds HTTP/1.1
Content-Type: application/json

{
  "amountPaise": 100
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Only a succeeded payment can be refunded; this one is declined",
  "instance": "/payments/2/refunds",
  "status": 409,
  "title": "Conflict"
}
```

### Case 11: an order id with a space

**Why:** `400`.

Request

``` code
POST /payments HTTP/1.1
Content-Type: application/json

{
  "orderId": "ORD 1005",
  "amountPaise": 249900
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/payments",
  "status": 400,
  "title": "Bad Request"
}
```

## The payments and refunds afterwards

``` code
 id | order_id | amount_paise |  status   | provider  | provider_ref |   decline_reason   | refunded_paise 
----+----------+--------------+-----------+-----------+--------------+--------------------+----------------
  1 | ORD-1001 |       249900 | succeeded | sim-alpha | ch_1         |                    |         100000
  2 | ORD-1002 |       249951 | declined  | sim-alpha |              | INSUFFICIENT_FUNDS |              0
  3 | ORD-1003 |       249997 | succeeded | sim-alpha | ch_3         |                    |              0
  4 | ORD-1004 |       249998 | succeeded | sim-beta  | T5001        |                    |         249998
(4 rows)
```

``` code
 id | payment_id | amount_paise |  status   | provider_ref 
----+------------+--------------+-----------+--------------
  1 |          1 |       100000 | succeeded | rf_4
  2 |          4 |       249998 | succeeded | R5002
(2 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                     | What happens                                          | Proved by                                                 |
|------------------------------------------|-------------------------------------------------------|-----------------------------------------------------------|
| A healthy primary                        | `201`, sim-alpha's reference                          | `aPaymentGoesToThePrimaryProvider`                        |
| A decline                                | `402`, our reason, no failover                        | `aDeclineIsAnAnswerNotAFailover`                          |
| Primary unreachable; both unreachable    | The fallback takes it; `503`                          | `anUnreachablePrimaryFailsOverAndBothDownIs503`           |
| Charged, then a timeout                  | Asked first: the charge is found, sim-beta not called | `afterATimeoutTheApiAsksFirstAndFindsTheCharge`           |
| A timeout and the status check down      | `202` unknown, sim-beta not called                    | `whenTheStatusCheckCannotSayEitherNoOtherProviderIsTried` |
| A timeout before charging                | sim-alpha says no such charge: sim-beta takes it      | `whenTheProviderSaysItNeverChargedTheFallbackIsTried`     |
| The same order again                     | The same body, one charge                             | `theSameOrderTwiceIsOnePaymentAndOneCharge`               |
| Five at the same moment                  | One payment, one charge                               | `fiveRetriesAtTheSameMomentAreOneCharge`                  |
| An unknown payment retried               | Still unknown; nothing sent again                     | `anUnknownPaymentRetriedIsNotSentAgain`                   |
| A refund of a sim-beta payment           | Goes to sim-beta, though sim-alpha is primary         | `aRefundGoesToTheProviderThatTookThePayment`              |
| Two refunds at once that cannot both fit | `201` and `409`                                       | `twoRefundsAtOnceCannotBothFit`                           |
| A refund the provider never got          | `503`, the amount freed                               | `aRefundTheProviderNeverGotGivesTheAmountBack`            |
| Each provider's codes                    | The same reasons                                      | `bothProvidersErrorsMapToTheSameReasons`                  |
| A wrong provider name in configuration   | The app does not start                                | `providersArePickedByNameAndAWrongNameStopsTheStart`      |
| Rules written by plain SQL               | Refused by named constraints                          | `paymentRulesHoldWithoutJava`                             |

## The trap

Plausible but wrong

Failing over to a second provider after a timeout when the first may already have charged.

- **The old code.** The test runs its logic against the two simulations: sim-alpha charges and then times out, the old code calls that a failure and charges sim-beta. Both have a charge for one order.
- **The API.** The same timeout: the API asks sim-alpha about its reference, finds the charge and records it. sim-beta is never called. If sim-alpha cannot say, the payment stays unknown.

While building, each part was undone once: no status check after a timeout turned 4 tests red; a timeout moving on to the next provider 2; a decline moving on 3; refunds through the current primary 1; no row lock on refunds 1; no handling of the same order sent at once 1; a failed refund not giving the amount back 1; another amount for the same order accepted 1; sim-alpha's funds code mapped wrong 3; sim-beta's code 62 forgotten 1; rupees sent without paise 8. The refund lock and the same-order race first turned no test red: see Tests.

``` code
package com.paysetu.payments;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old code treated any error from the first provider as "it failed" and charged the second one.
 * sim-alpha charges, then its answer times out: the customer was charged by both providers.
 */
class FailoverAfterTimeoutTrapTest extends ApiTest {

    @Test
    void theOldCodeChargedTheCustomerTwice() {
        alpha.fault = AlphaApi.Fault.TIMEOUT_AFTER_CHARGING;
        try {
            alpha.createCharge("pay_1", "2499.00");
        } catch (AlphaApi.ReadTimeout timeout) {
            beta.authorise("pay_1", 249900);   // "alpha failed, try beta"
        }
        assertThat(alpha.charges).containsKey("pay_1");
        assertThat(beta.authorisations).containsKey("pay_1");   // charged twice for one order
    }

    @Test
    void afterATimeoutTheApiAsksFirstAndFindsTheCharge() throws Exception {
        alpha.fault = AlphaApi.Fault.TIMEOUT_AFTER_CHARGING;
        pay("ORD-1001", 249900).andExpect(status().isCreated()).andExpect(jsonPath("$.status").value("succeeded"))
                .andExpect(jsonPath("$.provider").value("sim-alpha")).andExpect(jsonPath("$.providerRef").value("ch_1"));
        assertThat(beta.authorisations).isEmpty();
    }

    @Test
    void whenTheStatusCheckCannotSayEitherNoOtherProviderIsTried() throws Exception {
        alpha.fault = AlphaApi.Fault.TIMEOUT_AFTER_CHARGING;
        alpha.lookupDown = true;
        pay("ORD-1001", 249900).andExpect(status().isAccepted()).andExpect(jsonPath("$.status").value("unknown"))
                .andExpect(jsonPath("$.provider").value("sim-alpha"));
        assertThat(beta.authorisations).isEmpty();
    }

    @Test
    void whenTheProviderSaysItNeverChargedTheFallbackIsTried() throws Exception {
        alpha.fault = AlphaApi.Fault.TIMEOUT_BEFORE_CHARGING;
        pay("ORD-1001", 249900).andExpect(status().isCreated()).andExpect(jsonPath("$.provider").value("sim-beta"))
                .andExpect(jsonPath("$.providerRef").value("T5001"));
        assertThat(alpha.charges).isEmpty();
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                                           | Check with      |
|----------|-------------------------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below                    | `java -version` |
| Docker   | Docker Desktop (Windows, macOS) or Docker Engine (Linux), running | `docker info`   |
| Maven    | Not needed: the project ships the Maven wrapper                   |                 |

**macOS / Linux**

``` code
docker compose up -d        # PostgreSQL 17 on localhost:5432
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 25 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Make sim-beta the primary with no fallback, by configuration only, and pay:

``` code
./mvnw spring-boot:run -Dspring-boot.run.arguments="--paysetu.primary=sim-beta --paysetu.fallback="
curl -s -X POST http://localhost:8080/payments -H 'Content-Type: application/json' -d '{"orderId": "TRY-1", "amountPaise": 10000}'
```

The answer says `"provider":"sim-beta"` and a reference like `T5001`. Start it with `--paysetu.primary=sim-omega` instead: the app stops at start with `No payment provider named sim-omega; known: [sim-alpha, sim-beta]`.

## Troubleshooting

| You see                                                 | Cause                                                              | Fix                                                                  |
|---------------------------------------------------------|--------------------------------------------------------------------|----------------------------------------------------------------------|
| The app stops at start: `No payment provider named ...` | A name in `paysetu.primary` or `paysetu.fallback` has no adapter.  | Use a known name, or add the adapter (challenge 2).                  |
| A payment stays `unknown`                               | The provider timed out and its status check did not answer either. | Ask again later (challenge 1); never charge another provider for it. |
| `Could not find a valid Docker environment`             | Docker is not running.                                             | Start Docker Desktop or the Docker service.                          |

## Project layout

``` tree
stations/086-one-api-for-many-payment-providers/
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
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the adapters and the database behind it.

#### `src/main/java/com/paysetu/payments/PaymentController.java`

Does  
The two endpoints.

Why  
Checks the order id and amount, upper-cases the order id with `Locale.ROOT`, and answers with a status that follows the payment's state.

Without it  
A retry getting a different answer from the first try.

#### `src/main/java/com/paysetu/payments/Payments.java`

Does  
Payments and refunds, without knowing any provider.

Why  
Writes the payment before calling anyone; tries providers in order; after a timeout asks first; records the answer. Refunds reserve the amount under a row lock, call the provider that took the payment with no transaction open, then record the result.

Without it  
Double charges after a timeout, refunds sent to the wrong provider, refunds over the amount.

- `NotSent` and `Unknown` are different exceptions on purpose: only the first allows another provider.
- A decline ends the attempt: it is the customer's answer, not the provider's failure.
- The limit, in a `shortcut:` comment: one status check straight after the timeout. A provider still processing could say "no such charge" too early; real integrations wait and ask again, or wait for the provider's webhook.

#### `src/main/java/com/paysetu/payments/PaymentProvider.java`

Does  
The one interface every adapter implements.

Why  
Charge, look up, refund; our outcomes and our two exceptions.

Without it  
Provider types leaking into checkout code.

#### `src/main/java/com/paysetu/payments/Providers.java`

Does  
Picks adapters by name from configuration.

Why  
Spring hands it every adapter; the names in `application.yaml` choose primary and fallback.

Without it  
A code change and a release to switch provider.

A wrong name fails the start with the known names in the message, not the first payment.

#### `src/main/java/com/paysetu/payments/AlphaProvider.java`

Does  
The sim-alpha adapter.

Why  
Paise to rupee text (`BigDecimal`, exact), its states and word codes to our outcomes, its exceptions to ours.

Without it  
sim-alpha's format anywhere else.

#### `src/main/java/com/paysetu/payments/BetaProvider.java`

Does  
The sim-beta adapter.

Why  
Two-digit response codes to our outcomes; codes we do not know become `DECLINED_BY_PROVIDER`.

Without it  
A new code from the provider crashing checkout.

#### `src/main/java/com/paysetu/payments/AlphaApi.java`

The simulated sim-alpha, shaped like an SDK. Tests set its faults; demo amounts trigger them for the captures. Nothing is charged.

#### `src/main/java/com/paysetu/payments/BetaApi.java`

The simulated sim-beta. Nothing is charged.

#### `src/main/resources/db/migration/V1__payments_and_refunds.sql`

Does  
Payments and refunds.

Why  
One payment per order; refunds never more than the amount, and only on succeeded payments; known providers and states.

Without it  
A second payment for an order, or an over-refund, from any writer.

#### `src/main/resources/application.yaml`

Which provider is primary and which is the fallback; fractions refused for paise.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/paysetu/payments/PaymentsApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                            | Test class                                             | Result |
|---------------|--------------------------------------------------------|--------------------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found               | `PaymentContractTest` (5), `RefundTest` (4)            | pass   |
| Every station | Reproduce the failure before the fix                   | `FailoverAfterTimeoutTrapTest` (4)                     | pass   |
| Database      | Rollback and constraint tests against a real database  | `PaymentDatabaseTest` (3), `RefundConcurrencyTest` (1) | pass   |
| Idempotency   | A replay test: the same request twice gives one effect | `PaymentReplayTest` (4)                                | pass   |
| This station  | Adapters and selection by configuration                | `ProviderAdapterTest` (3), `PrimaryFromConfigTest` (1) | pass   |

Two mutations changed no test at first. Without the row lock on refunds, the database's CHECK still refused the second refund, with an error instead of a `409`; `RefundConcurrencyTest` now sends two refunds at once with a 200 ms reservation (a trigger). Without handling the same order sent at once, the five parallel retries passed in one run and failed in another; a 200 ms insert (a trigger) now makes all five look before the first is written, and the mutation fails every time. Found while building.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payments.FailoverAfterTimeoutTrapTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payments.PaymentDatabaseTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payments.PaymentReplayTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payments.ProviderAdapterTest
[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payments.RefundConcurrencyTest
[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payments.PrimaryFromConfigTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payments.PaymentContractTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payments.RefundTest
[INFO] Tests run: 25, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/paysetu/payments/FailoverAfterTimeoutTrapTest.java`

Written first: the old failover charging twice, and the API asking first.

#### `src/test/java/com/paysetu/payments/PaymentContractTest.java`

Payments through HTTP: success, decline, failover, bad requests.

#### `src/test/java/com/paysetu/payments/PaymentReplayTest.java`

The same order again, declined or unknown; five at once.

#### `src/test/java/com/paysetu/payments/RefundTest.java`

Part refunds, the right provider, a provider that cannot be reached.

#### `src/test/java/com/paysetu/payments/RefundConcurrencyTest.java`

Two refunds at once that cannot both fit.

#### `src/test/java/com/paysetu/payments/ProviderAdapterTest.java`

The adapters and the factory alone, without Spring.

#### `src/test/java/com/paysetu/payments/PrimaryFromConfigTest.java`

sim-beta as primary by a property alone.

#### `src/test/java/com/paysetu/payments/PaymentDatabaseTest.java`

Named constraints with plain SQL; a refund that cannot be recorded calls no provider.

#### `src/test/java/com/paysetu/payments/ApiTest.java`

Shared setup: both simulations reset and no payments before each test.

#### `src/test/java/com/paysetu/payments/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/paysetu/payments/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=StatusCheckChallengeTest` (Docker must be running). The sim-gamma test does not compile until `GammaApi` exists.
3.  Change the code until it passes, then run `./mvnw test` to check the other 25 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 30 tests pass (25 station tests and 5 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Settle unknown payments

`POST /payments/{id}/status-check` asks the provider that took an `unknown` payment: charged becomes `succeeded`, declined `declined`, never seen `failed`. If it still cannot say, nothing changes. Other payments are returned as they are.

**Done when:** the three tests in `StatusCheckChallengeTest` pass.

Hints

- Use `providers.named(payment.provider())`, never the current primary.
- It never charges: a payment that never happened becomes `failed`, and the customer pays again with a new order.

#### `challenge/StatusCheckChallengeTest.java`

``` code
package com.paysetu.payments;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.ResultActions;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /payments/{id}/status-check settles an "unknown" payment by asking the provider that took it:
 * charged, declined, or never seen (then "failed": nothing was charged). If it still cannot say, the payment stays unknown.
 */
class StatusCheckChallengeTest extends ApiTest {

    ResultActions check(long id) throws Exception {
        return mvc.perform(post("/payments/{id}/status-check", id));
    }

    void unknownPayment(AlphaApi.Fault fault) throws Exception {
        alpha.fault = fault;
        alpha.lookupDown = true;
        pay("ORD-7001", 50000).andExpect(jsonPath("$.status").value("unknown"));
        alpha.fault = AlphaApi.Fault.NONE;
    }

    @Test
    void aChargeThatHappenedBecomesSucceeded() throws Exception {
        unknownPayment(AlphaApi.Fault.TIMEOUT_AFTER_CHARGING);
        check(1).andExpect(status().isAccepted());   // still cannot say
        alpha.lookupDown = false;
        check(1).andExpect(status().isCreated()).andExpect(jsonPath("$.status").value("succeeded")).andExpect(jsonPath("$.providerRef").value("ch_1"));
        assertThat(beta.authorisations).isEmpty();
    }

    @Test
    void aChargeThatNeverHappenedBecomesFailed() throws Exception {
        unknownPayment(AlphaApi.Fault.TIMEOUT_BEFORE_CHARGING);
        alpha.lookupDown = false;
        check(1).andExpect(status().isServiceUnavailable()).andExpect(jsonPath("$.status").value("failed"));
        assertThat(alpha.charges).isEmpty();
    }

    @Test
    void settledPaymentsAreLeftAsTheyAre() throws Exception {
        pay("ORD-7002", 50000).andExpect(status().isCreated());
        alpha.lookupDown = true;   // a settled payment needs no question
        check(1).andExpect(status().isCreated()).andExpect(jsonPath("$.status").value("succeeded"));
        check(42).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No such payment"));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## A third provider

Add the simulated sim-gamma (`GammaApi`, yes/no answers with a reason word) and its adapter, then make it primary by configuration. `Payments` does not change.

**Done when:** both tests in `ThirdProviderChallengeTest` pass.

Hints

- An adapter is a `@Component` implementing `PaymentProvider`; `Providers` finds it by name.
- The database only allows known provider names: a V3 migration replaces `payments_known_provider`.

#### `challenge/ThirdProviderChallengeTest.java`

``` code
package com.paysetu.payments;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.TestPropertySource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: add the simulated provider sim-gamma (GammaApi, in the solution) with an adapter, and make it primary by
 * configuration alone. The payments code does not change; a V3 migration lets the database store the new name.
 */
@TestPropertySource(properties = {"paysetu.primary=sim-gamma", "paysetu.fallback=sim-alpha"})
class ThirdProviderChallengeTest extends ApiTest {

    @Autowired
    GammaApi gamma;

    @Test
    void sim_gammaTakesPaymentsAndItsErrorsMapToOurs() throws Exception {
        gamma.reset();
        pay("ORD-8001", 120000).andExpect(status().isCreated()).andExpect(jsonPath("$.provider").value("sim-gamma"))
                .andExpect(jsonPath("$.providerRef").value("g-1"));
        pay("ORD-8002", 120051).andExpect(status().isPaymentRequired()).andExpect(jsonPath("$.declineReason").value("INSUFFICIENT_FUNDS"));
        refund(1, 20000).andExpect(status().isCreated()).andExpect(jsonPath("$.provider").value("sim-gamma"));
        assertThat(gamma.refunds).containsExactly("g-1 20000");
        assertThat(alpha.charges).isEmpty();
    }

    @Test
    void whenSim_gammaIsUnreachableSimAlphaTakesOver() throws Exception {
        gamma.reset();
        gamma.unreachable = true;
        pay("ORD-8003", 120000).andExpect(status().isCreated()).andExpect(jsonPath("$.provider").value("sim-alpha"));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Routing and webhooks

Paysetu wants UPI through one provider and cards through another, and to move traffic away from a provider whose success rate drops. Design the routing rule and where it lives. Then add webhooks: each provider calls Paysetu when a payment settles. How do you verify the call is genuine, match it to a payment, and settle an `unknown` payment from it, safely if it arrives twice?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old failover against two simulations.
2.  Define `PaymentProvider` with our outcomes and two exceptions: not sent, unknown.
3.  Write one adapter per provider, and the factory that reads the configuration.
4.  Write the payment flow: record, try in order, ask after a timeout, record the answer. Then refunds to the provider that took the payment.

## Design alternatives and trade-offs

| Approach                                                                    | What it costs                                                                              | Verdict         |
|-----------------------------------------------------------------------------|--------------------------------------------------------------------------------------------|-----------------|
| Adapters behind one interface, chosen by configuration; ask after a timeout | One class per provider; payments can stay unknown for a while.                             | Chosen          |
| Fail over on any error                                                      | Double charges after timeouts.                                                             | The trap        |
| Provider SDK calls in the payment code                                      | Every switch touches everything.                                                           | The old code    |
| A payment orchestration service bought in                                   | Less code; another provider to depend on, and its own failure modes.                       | At larger scale |
| Wait for the webhook instead of asking                                      | No polling; the payment waits until the webhook arrives, and webhooks can be late or lost. | Use both        |

## Database design

| Object                                                              | What   | Why                                                                                |
|---------------------------------------------------------------------|--------|------------------------------------------------------------------------------------|
| `payments_order_once`                                               | UNIQUE | One payment per order, for every writer and every retry.                           |
| `payments_refunds_within_amount`, `payments_refunds_only_when_paid` | CHECKs | Never more refunded than paid; nothing refunded on a payment that did not succeed. |
| `payments_succeeded_has_ref`, `payments_declined_has_reason`        | CHECKs | A succeeded payment can be found at its provider; a decline says why.              |
| `payments_known_provider`, `payments_status`                        | CHECKs | Only names and states the code knows.                                              |

**Transaction boundaries:** the payment row is written and committed before any provider is called. No transaction is open during a provider call. A refund reserves its amount in one short transaction and records the result in another.

``` code
CREATE TABLE payments (
    id             bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT payments_pk PRIMARY KEY,
    order_id       text NOT NULL,
    amount_paise   bigint NOT NULL,
    provider       text NOT NULL,
    status         text NOT NULL,
    provider_ref   text,
    decline_reason text,
    refunded_paise bigint NOT NULL DEFAULT 0,
    created_at     timestamptz NOT NULL DEFAULT now(),
    -- One payment per order, whoever retries: the replay rule.
    CONSTRAINT payments_order_once UNIQUE (order_id),
    CONSTRAINT payments_order_shape CHECK (order_id ~ '^[A-Z0-9-]{3,40}$'),
    CONSTRAINT payments_amount_positive CHECK (amount_paise > 0),
    CONSTRAINT payments_known_provider CHECK (provider IN ('sim-alpha', 'sim-beta')),
    -- pending: being sent; unknown: a provider may have charged and could not say; failed: no provider was reached.
    CONSTRAINT payments_status CHECK (status IN ('pending', 'succeeded', 'declined', 'unknown', 'failed')),
    CONSTRAINT payments_succeeded_has_ref CHECK (status <> 'succeeded' OR provider_ref IS NOT NULL),
    CONSTRAINT payments_declined_has_reason CHECK ((status = 'declined') = (decline_reason IS NOT NULL)),
    CONSTRAINT payments_refunds_within_amount CHECK (refunded_paise BETWEEN 0 AND amount_paise),
    CONSTRAINT payments_refunds_only_when_paid CHECK (refunded_paise = 0 OR status = 'succeeded')
);

CREATE TABLE refunds (
    id           bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT refunds_pk PRIMARY KEY,
    payment_id   bigint NOT NULL CONSTRAINT refunds_payment_fk REFERENCES payments,
    amount_paise bigint NOT NULL,
    status       text NOT NULL,
    provider_ref text,
    created_at   timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT refunds_amount_positive CHECK (amount_paise > 0),
    CONSTRAINT refunds_status CHECK (status IN ('requested', 'succeeded', 'failed')),
    CONSTRAINT refunds_succeeded_has_ref CHECK (status <> 'succeeded' OR provider_ref IS NOT NULL)
);
```

# 3 · Go deeper: Production

Unknown payments  
Count them and settle them: a job that asks the provider again (challenge 1), and the provider's webhooks. An unknown payment should never be charged again elsewhere.

Your reference  
Send the provider your own reference (here `pay_<id>`) and use the provider's idempotency feature where it has one, so a status check can find the charge and a resend does not charge twice.

Timeouts  
Set connect and read timeouts on every provider client. A connect timeout means "not sent"; a read timeout means "unknown".

Reconciliation  
Compare each provider's settlement report with your payments every day; that is where the last mismatches show up.

# 3 · Go deeper: Interview

## Interview takeaways

What is the adapter pattern here?

One interface for what payments need (charge, look up, refund), and one class per provider that translates to that provider's API, formats and errors. The rest of the code only sees the interface.

How is the provider chosen?

By configuration: Spring hands all adapters to a factory, which picks by name. A wrong name fails the start, not the first payment.

When is failover safe?

When the first provider certainly did not charge: the connection was refused, or the provider says it has no such charge. After a timeout, ask first.

Why not fail over on a decline?

A decline is the bank's answer about the customer's money. Another provider would ask the same bank, or charge a different way the customer did not choose.

Where do refunds go?

To the provider that took the payment, stored on the payment. The current primary may never have seen it.

## Self-check rubric

| Area        | Meets the bar                                | Above the bar                                                                                          |
|-------------|----------------------------------------------|--------------------------------------------------------------------------------------------------------|
| Correctness | All 25 tests pass.                           | You ran the flawed version and explained each failure.                                                 |
| Adapters    | One class per provider.                      | Nothing outside the adapters names a provider's formats or codes.                                      |
| Failover    | Tries the fallback when the primary is down. | Never after a timeout without asking; never after a decline.                                           |
| Refunds     | Refunds work.                                | To the provider that took the payment, capped, under a lock, with no transaction open during the call. |

# 3 · Go deeper: Review

## The pull request

A teammate makes payments "more resilient": any exception from a provider, timeouts included, moves on to the next provider, and the status check is gone as "one more call that can fail". Refunds now always use the primary provider, "our main one". Read the file and list every problem before opening the findings.

#### `review/Payments.java`

``` code
package com.paysetu.payments;

import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.ErrorResponseException;

import java.util.Optional;

@Service
class Payments {

    record Payment(long id, String orderId, long amountPaise, String status, String provider, String providerRef,
                   String declineReason, long refundedPaise) {
    }

    record Refund(long id, long paymentId, long amountPaise, String status, String provider, String providerRef) {
    }

    private final JdbcClient jdbc;
    private final Providers providers;
    private final TransactionTemplate tx;

    Payments(JdbcClient jdbc, Providers providers, TransactionTemplate tx) {
        this.jdbc = jdbc;
        this.providers = providers;
        this.tx = tx;
    }

    /**
     * One payment per order. The row is written before any provider is called, so a retry finds it. Providers are
     * called with no transaction open. After a timeout the provider is asked what happened before anything else:
     * failing over then could charge the customer twice.
     */
    Payment pay(String orderId, long amountPaise) {
        Optional<Payment> earlier = byOrder(orderId);
        if (earlier.isPresent()) {
            return sameOrder(earlier.get(), amountPaise);
        }
        long id;
        try {
            id = jdbc.sql("INSERT INTO payments (order_id, amount_paise, provider, status) VALUES (?, ?, ?, 'pending') RETURNING id")
                    .params(orderId, amountPaise, providers.inOrder().getFirst().name()).query(Long.class).single();
        } catch (DuplicateKeyException e) {
            return sameOrder(byOrder(orderId).orElseThrow(), amountPaise);   // the same order, sent twice at once
        }
        String reference = "pay_" + id;
        for (PaymentProvider p : providers.inOrder()) {
            jdbc.sql("UPDATE payments SET provider = ? WHERE id = ?").params(p.name(), id).update();
            PaymentProvider.Outcome outcome;
            try {
                outcome = attempt(p, reference, amountPaise);
            } catch (PaymentProvider.Unknown e) {
                return settle(id, "unknown", null, null);   // it may have charged: no other provider may be tried
            }
            if (outcome instanceof PaymentProvider.Outcome.Charged c) {
                return settle(id, "succeeded", c.providerRef(), null);
            }
            if (outcome instanceof PaymentProvider.Outcome.Declined d) {
                return settle(id, "declined", null, d.reason().name());   // a decline is an answer: no failover
            }
            // null: this provider certainly did not charge, so the next one may be tried
        }
        return settle(id, "failed", null, null);
    }

    /** The provider's answer; null when it did not work, so the next provider is tried. */
    private static PaymentProvider.Outcome attempt(PaymentProvider p, String reference, long amountPaise) {
        try {
            return p.charge(reference, amountPaise);
        } catch (PaymentProvider.NotSent | PaymentProvider.Unknown e) {
            return null;   // resilience: any trouble with one provider, and the next one takes the payment
        }
    }

    /**
     * Refunds go to the provider that took the payment, whatever is primary today. The amount is reserved under a row
     * lock first (so two refunds cannot both fit), the provider is called with no transaction open, then the result is
     * recorded; a refund the provider never received gives its amount back.
     */
    Refund refund(long paymentId, long amountPaise) {
        Refund requested = tx.execute(s -> {
            Payment p = jdbc.sql("SELECT * FROM payments WHERE id = ? FOR UPDATE").param(paymentId).query(Payment.class).optional()
                    .orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "No such payment"));
            if (!"succeeded".equals(p.status())) {
                throw problem(HttpStatus.CONFLICT, "Only a succeeded payment can be refunded; this one is " + p.status());
            }
            if (p.refundedPaise() + amountPaise > p.amountPaise()) {
                throw problem(HttpStatus.CONFLICT, "At most " + (p.amountPaise() - p.refundedPaise()) + " paise can still be refunded");
            }
            jdbc.sql("UPDATE payments SET refunded_paise = refunded_paise + ? WHERE id = ?").params(amountPaise, paymentId).update();
            long id = jdbc.sql("INSERT INTO refunds (payment_id, amount_paise, status) VALUES (?, ?, 'requested') RETURNING id")
                    .params(paymentId, amountPaise).query(Long.class).single();
            return new Refund(id, paymentId, amountPaise, "requested", p.provider(), p.providerRef());
        });
        try {
            String ref = providers.inOrder().getFirst().refund(   // refunds go through our main provider
                    requested.providerRef(), amountPaise);
            jdbc.sql("UPDATE refunds SET status = 'succeeded', provider_ref = ? WHERE id = ?").params(ref, requested.id()).update();
            return new Refund(requested.id(), paymentId, amountPaise, "succeeded", requested.provider(), ref);
        } catch (PaymentProvider.NotSent e) {
            tx.executeWithoutResult(s -> {
                jdbc.sql("UPDATE refunds SET status = 'failed' WHERE id = ?").param(requested.id()).update();
                jdbc.sql("UPDATE payments SET refunded_paise = refunded_paise - ? WHERE id = ?").params(amountPaise, paymentId).update();
            });
            throw problem(HttpStatus.SERVICE_UNAVAILABLE, requested.provider() + " could not be reached; nothing was refunded. Try again.");
        }
    }

    private Payment sameOrder(Payment earlier, long amountPaise) {
        if (earlier.amountPaise() != amountPaise) {
            throw problem(HttpStatus.CONFLICT, "Order " + earlier.orderId() + " was already sent with a different amount");
        }
        return earlier;   // a retry: the same payment, nothing charged again
    }

    private Payment settle(long id, String status, String providerRef, String declineReason) {
        jdbc.sql("UPDATE payments SET status = ?, provider_ref = ?, decline_reason = ? WHERE id = ?").params(status, providerRef, declineReason, id).update();
        return jdbc.sql("SELECT * FROM payments WHERE id = ?").param(id).query(Payment.class).single();
    }

    private Optional<Payment> byOrder(String orderId) {
        return jdbc.sql("SELECT * FROM payments WHERE order_id = ?").param(orderId).query(Payment.class).optional();
    }

    static ErrorResponseException problem(HttpStatus status, String detail) {
        return new ErrorResponseException(status, ProblemDetail.forStatusAndDetail(status, detail), null);
    }
}
```

## Findings

1Failing over on a timeout

"Any trouble with one provider, and the next one takes the payment" treats "no answer" as "no". When sim-alpha charged and then timed out, sim-beta charges again: the customer pays twice. When sim-alpha's status check is down too, the payment should stay unknown; here it goes to sim-beta.

**Test evidence:** `afterATimeoutTheApiAsksFirstAndFindsTheCharge`, `whenTheStatusCheckCannotSayEitherNoOtherProviderIsTried`, `anUnknownPaymentRetriedIsNotSentAgain` and `theSimulationsDemoAmountsTriggerItsFaults` fail.

2Refunds through the current primary

"Refunds go through our main provider" works only while every payment was taken by it. A payment sim-beta took during an outage is refunded at sim-alpha, which has never seen that charge.

**Test evidence:** `aRefundGoesToTheProviderThatTookThePayment` fails.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class                     | Fixed version | Flawed version |
|--------------------------------|---------------|----------------|
| `PaymentDatabaseTest`          | 3 / 3         | 3 / 3          |
| `PrimaryFromConfigTest`        | 1 / 1         | 1 / 1          |
| `ProviderAdapterTest`          | 3 / 3         | 3 / 3          |
| `RefundConcurrencyTest`        | 1 / 1         | 1 / 1          |
| `FailoverAfterTimeoutTrapTest` | 4 / 4         | 2 / 4          |
| `PaymentContractTest`          | 5 / 5         | 4 / 5          |
| `PaymentReplayTest`            | 4 / 4         | 3 / 4          |
| `RefundTest`                   | 4 / 4         | 3 / 4          |

On a normal day the flawed version works: every payment succeeds at sim-alpha and every refund goes there. Both flaws need a bad evening, a slow provider or an outage, to show.
