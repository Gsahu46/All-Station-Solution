# Station 018 · Payment methods with sealed interfaces

Foundations · 0–1 years · Core · Payments · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · sealed interfaces · records · switch pattern matching · Jackson 3 · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** A payment intent is a response describing what the payer does next. No UPI app, bank or card network is contacted, no money moves, and nothing is stored in this station. Card tokens are made-up strings.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 11 tests.

# 1 · Understand

## The problem in real life

1.  **Paysetu adds wallets**

    The payment class gets one more nullable field, `walletMobile`. Checkout works; the tests for checkout pass.

2.  **The first wallet refund**

    The refund code checks UPI, then card, then net banking, and returns nothing for anything else. Wallet refunds silently go nowhere, and support finds out from customers.

3.  **The fix**

    Model "one of four" as a sealed interface with a record per method, and handle them with switches that have no default. Adding a fifth method now stops the build at every place that forgot it.

Let the compiler keep the list of cases, so a new one cannot be forgotten quietly.

## What are we building?

`POST /payment-intents` takes an order, an amount and exactly one payment method. It answers with what the payer does next (approve in a UPI app, enter an OTP, log in to the bank, confirm a wallet debit) and where a refund would go.

## An everyday analogy

A paper form with a separate box for each way to pay, where you may fill in only one box. Nobody can tick "UPI" and also write a card number, and the clerk's checklist has a line for every box on the form.

## How it works in 4 steps

1.  **Read the type**: `"type": "UPI"` picks the UPI record; other fields are refused.
2.  **Validate** that record's own fields: a UPI ID, a 4-letter bank code, a 10-digit mobile.
3.  **Switch on the method** for the next action; the compiler checks all four are handled.
4.  **Switch again** for the refund route, with the same guarantee.

Check yourself: why not keep the old class and add a test for wallet refunds?

That test catches wallets, once. The next method (say, pay later) needs someone to remember every place again. With a sealed interface and no default branch, the build itself fails at each place that does not handle the new method.

## What this station is not

- **No real payment.** Nothing contacts NPCI, a bank or a card network.
- **No card numbers.** Only a token, the network and the last 4 digits; a full number is refused.
- **No storage.** Challenge 1 adds it.

## Key terms

| Term                        | Simple meaning                                                               | Everyday example                                                    | In this project                                       |
|-----------------------------|------------------------------------------------------------------------------|---------------------------------------------------------------------|-------------------------------------------------------|
| **Payment intent**          | A record of "this order wants to be paid this way", before any money moves.  | The checkout screen after you pick UPI.                             | `POST /payment-intents`                               |
| **Sealed interface**        | An interface that lists every type allowed to implement it. No one else can. | A menu with exactly four dishes printed on it.                      | `PaymentMethod permits Upi, Card, NetBanking, Wallet` |
| **Record**                  | A small class that is just its data, with equals and toString for free.      | A filled-in form.                                                   | `record Upi(String vpa)`                              |
| **Pattern matching switch** | A switch that picks a branch by type and unpacks its fields.                 | "If it is a UPI payment, take its UPI ID and…"                      | `case Upi(String vpa) ->`                             |
| **Exhaustive**              | Covers every case. For a sealed type, the compiler checks it.                | A checklist the inspector will not sign until every line is ticked. | No `default` in `Methods`                             |
| **Card token**              | A stand-in for a card number that is useless outside one merchant.           | A cloakroom ticket instead of the coat.                             | `token`, accepted but never returned                  |

# 2 · Build: Spec

## Business problem

**Paysetu** (a fictional payment gateway) has one `Payment` class with a nullable field for every method. Each new method means hunting for every `if (vpa != null) … else if …` chain. The refund chain was missed when wallets launched, so wallet refunds returned nothing. The class also accepts a payment that is UPI and card at once.

## Acceptance criteria

1.  **Given** a UPI ID in any case, **then** it is stored lower-case and the payer is asked to approve in their UPI app.
2.  **Given** a card, **then** the response shows the network and last 4 digits, never the token.
3.  **Given** net banking at `hdfc`, **then** a redirect to the (simulated) HDFC login; at a bank that is not offered, `422`.
4.  **Given** a wallet, **then** the refund route is the wallet, with the mobile number masked.
5.  **Given** a UPI method with card fields, an unknown or missing type, or a bad field, **then** `400`.
6.  **Given** every permitted payment method, **then** it can arrive as JSON and has a next action and a refund route.

## Requirements

- One record per method; each has only its own fields. A `switch` over methods has no `default`.
- Identifiers are normalised with `Locale.ROOT`: UPI IDs lower-case, bank codes upper-case.
- Amounts are whole paise, ₹1 to ₹1,00,000 (a demo rule).
- Secrets are write-only: the card token and wallet mobile are accepted, never returned in full.

## Learning objectives

- Model "exactly one of" data with a sealed interface and records.
- Use switch pattern matching and record patterns, and explain exhaustiveness.
- Read polymorphic JSON with a `type` field, and refuse fields that do not belong.
- Write a test that covers every subtype without listing them.

# 2 · Build: API contract

## Endpoint

| Method | Path               | Purpose                                                                       |
|--------|--------------------|-------------------------------------------------------------------------------|
| `POST` | `/payment-intents` | Create an intent for one method. `201` with the next action and refund route. |

## Request body

| Field         | Rule                                                       |
|---------------|------------------------------------------------------------|
| `orderId`     | 1 to 40 letters, digits, `-` or `_`.                       |
| `amountPaise` | 100 to 10,000,000, whole number.                           |
| `method`      | An object with `type` and only that type's fields (below). |

| type          | Fields                                                                            |
|---------------|-----------------------------------------------------------------------------------|
| `UPI`         | `vpa`: a UPI ID like `name@bank`                                                  |
| `CARD`        | `network` (`VISA`, `MASTERCARD`, `RUPAY`), `last4`, `token` (`tok_…`, write-only) |
| `NET_BANKING` | `bankCode`: 4 letters; offered: HDFC, ICIC, KKBK, SBIN, UTIB                      |
| `WALLET`      | `mobile`: 10 digits starting 6 to 9 (write-only; returned as `maskedMobile`)      |

## Status codes

| Status | When                                                                 |
|--------|----------------------------------------------------------------------|
| 201    | Intent created                                                       |
| 400    | Unknown or missing type, a field from another method, or a bad field |
| 422    | Net banking at a bank that is not offered                            |

## Captured examples

Captured with curl from the running app on 14 Oct 2026, in this order. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: UPI

**Why:** the UPI ID is normalised to lower-case; the payer approves in their app.

Request

``` code
POST /payment-intents HTTP/1.1
Content-Type: application/json

{
  "orderId": "ORD-1042",
  "amountPaise": 49900,
  "method": {
    "type": "UPI",
    "vpa": "Asha.R@OKAXIS"
  }
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 355

{
  "id": "pi_219ca11a03f646838ca9099d768f1afa",
  "orderId": "ORD-1042",
  "amountPaise": 49900,
  "status": "REQUIRES_ACTION",
  "method": {
    "type": "UPI",
    "vpa": "asha.r@okaxis"
  },
  "nextAction": {
    "type": "APPROVE_IN_UPI_APP",
    "detail": "Approve Rs 499.00 to Paysetu in the UPI app linked to asha.r@okaxis."
  },
  "refundRoute": "Back to the bank account behind the UPI ID asha.r@okaxis."
}
```

### Case 2: a saved card

**Why:** the token was accepted but is not in the response: only the network and last 4 digits are.

Request

``` code
POST /payment-intents HTTP/1.1
Content-Type: application/json

{
  "orderId": "ORD-1043",
  "amountPaise": 129900,
  "method": {
    "type": "CARD",
    "network": "RUPAY",
    "last4": "4242",
    "token": "tok_9f8e7d6c5b4a"
  }
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 351

{
  "id": "pi_729439693f7f468f8adff5854a8c3ebd",
  "orderId": "ORD-1043",
  "amountPaise": 129900,
  "status": "REQUIRES_ACTION",
  "method": {
    "type": "CARD",
    "network": "RUPAY",
    "last4": "4242"
  },
  "nextAction": {
    "type": "AUTHENTICATE_CARD",
    "detail": "Enter the one-time password from your bank for the RUPAY card ending 4242."
  },
  "refundRoute": "Back to the RUPAY card ending 4242."
}
```

### Case 3: net banking

**Why:** `hdfc` becomes `HDFC`; the next action is a redirect to a simulated bank page.

Request

``` code
POST /payment-intents HTTP/1.1
Content-Type: application/json

{
  "orderId": "ORD-1044",
  "amountPaise": 250000,
  "method": {
    "type": "NET_BANKING",
    "bankCode": "hdfc"
  }
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 310

{
  "id": "pi_13ef0631ce5d49eba89c9579c81b0d5a",
  "orderId": "ORD-1044",
  "amountPaise": 250000,
  "status": "REQUIRES_ACTION",
  "method": {
    "type": "NET_BANKING",
    "bankCode": "HDFC"
  },
  "nextAction": {
    "type": "REDIRECT_TO_BANK",
    "detail": "/simulated-banks/HDFC/login"
  },
  "refundRoute": "Back to the account at bank HDFC it was paid from."
}
```

### Case 4: wallet

**Why:** the case the old refund code forgot. The refund route is the wallet; the number is masked.

Request

``` code
POST /payment-intents HTTP/1.1
Content-Type: application/json

{
  "orderId": "ORD-1045",
  "amountPaise": 9900,
  "method": {
    "type": "WALLET",
    "mobile": "9876543210"
  }
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 344

{
  "id": "pi_ecc8cc2d41fa4e0bb15feb3d8c8e1a90",
  "orderId": "ORD-1045",
  "amountPaise": 9900,
  "status": "REQUIRES_ACTION",
  "method": {
    "type": "WALLET",
    "maskedMobile": "98******10"
  },
  "nextAction": {
    "type": "CONFIRM_WALLET_DEBIT",
    "detail": "Confirm the Rs 99.00 debit in the Paysetu wallet of 98******10."
  },
  "refundRoute": "Back to the Paysetu wallet of 98******10."
}
```

### Case 5: UPI with a card field

**Why:** `last4` is not a UPI field: `400` instead of guessing which method was meant.

Request

``` code
POST /payment-intents HTTP/1.1
Content-Type: application/json

{
  "orderId": "ORD-1046",
  "amountPaise": 49900,
  "method": {
    "type": "UPI",
    "vpa": "asha@okaxis",
    "last4": "4242"
  }
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Failed to read request",
  "instance": "/payment-intents",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 6: a cheque

**Why:** not one of the four types: `400`.

Request

``` code
POST /payment-intents HTTP/1.1
Content-Type: application/json

{
  "orderId": "ORD-1047",
  "amountPaise": 49900,
  "method": {
    "type": "CHEQUE",
    "number": "000123"
  }
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Failed to read request",
  "instance": "/payment-intents",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 7: a bank that is not offered

**Why:** a valid code shape, but no such option: `422` listing the banks.

Request

``` code
POST /payment-intents HTTP/1.1
Content-Type: application/json

{
  "orderId": "ORD-1048",
  "amountPaise": 49900,
  "method": {
    "type": "NET_BANKING",
    "bankCode": "ABCD"
  }
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "Net banking with bank ABCD is not available. Available: HDFC, ICIC, KKBK, SBIN, UTIB.",
  "instance": "/payment-intents",
  "status": 422,
  "title": "Bank not available"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                              | What happens                                            | Proved by                                         |
|-----------------------------------------------------------------------------------|---------------------------------------------------------|---------------------------------------------------|
| UPI ID in capitals                                                                | Lower-case; approve in app                              | `upiAsksThePayerToApproveInTheirApp`              |
| Card with a token                                                                 | Token not in the response                               | `aCardNeverEchoesItsToken`                        |
| Net banking `hdfc`; wallet                                                        | Redirect to HDFC; masked mobile                         | `netBankingRedirectsAndAWalletShowsAMaskedNumber` |
| Bank ABCD                                                                         | `422`                                                   | `aBankThatIsNotOfferedIs422`                      |
| CHEQUE; no type; bad UPI ID; full card number; short mobile; 99 paise; empty body | `400`                                                   | `badMethodsAre400`                                |
| Every permitted method                                                            | Registered for JSON; has a next action and refund route | `EveryMethodTest`                                 |
| A `case` removed from a switch                                                    | The build fails (below)                                 | The compiler                                      |

## The trap

Plausible but wrong

One class with nullable fields for every method, so a new method is silently missed.

The first test shows the old refund chain returning `null` for a wallet. The second shows the old class taking a UPI-and-card payment and picking whichever `if` comes first. The third shows the sealed model refunding the wallet and refusing the mixed body. While building, making JSON lenient, echoing the token, and unregistering wallets each turned tests red.

``` code
package com.paysetu.payments;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: it reproduces the bugs before the fix. */
class ForgottenWalletTrapTest extends ApiTest {

    /** The "before" model: one class, a nullable field per method. Kept only in tests. */
    record OldPayment(String vpa, String cardLast4, String bankCode, String walletMobile) {
    }

    /** The "before" refund path. It compiles, and nothing says wallets are missing. */
    static String oldRefundRoute(OldPayment p) {
        if (p.vpa() != null) {
            return "UPI " + p.vpa();
        } else if (p.cardLast4() != null) {
            return "card " + p.cardLast4();
        } else if (p.bankCode() != null) {
            return "bank " + p.bankCode();
        }
        return null;   // wallets were added later; nobody came back here
    }

    @Test
    void theOldRefundPathSilentlyForgetsWallets() {
        assertThat(oldRefundRoute(new OldPayment(null, null, null, "9876543210"))).isNull();
    }

    @Test
    void theOldClassAcceptsAPaymentThatIsTwoMethodsAtOnce() {
        // UPI and a card in one payment: the old code just picks whichever if comes first.
        assertThat(oldRefundRoute(new OldPayment("asha@okaxis", "4242", null, null))).isEqualTo("UPI asha@okaxis");
    }

    @Test
    void theSealedModelRefundsWalletsAndRefusesMixedMethods() throws Exception {
        intent("{\"type\":\"WALLET\",\"mobile\":\"9876543210\"}")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.refundRoute").value("Back to the Paysetu wallet of 98******10."));
        intent("{\"type\":\"UPI\",\"vpa\":\"asha@okaxis\",\"last4\":\"4242\"}").andExpect(status().isBadRequest());
    }
}
```

## And when a case is forgotten now

Removing the wallet branch from `refundRoute` no longer compiles. This is the real output, saved in `docs/missing-case-compile.txt`:

``` console
$ ./mvnw -q compile   # with "case Wallet" removed from refundRoute
[ERROR] src/main/java/com/paysetu/payments/Methods.java:[35,16] the switch expression does not cover all possible input values
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                         | Check with      |
|----------|-------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below  | `java -version` |
| Maven    | Not needed: the project ships the Maven wrapper |                 |
| Docker   | Not needed for this station                     |                 |

**macOS / Linux**

``` code
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 11 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Sealed interfaces, record patterns and pattern-matching switches are all final in Java 21.

## Try it yourself

The body is in `docs/upi-intent.json`. Then try adding `"last4": "4242"` to the method.

``` code
# Expect 201 with nextAction APPROVE_IN_UPI_APP
curl -i -X POST http://localhost:8080/payment-intents -H "Content-Type: application/json" -d "@docs/upi-intent.json"
```

## Troubleshooting

| You see                                                          | Cause                                                      | Fix                                                      |
|------------------------------------------------------------------|------------------------------------------------------------|----------------------------------------------------------|
| `400` for a body that looks right                                | A field that belongs to another method, or a misspelt one. | Send only the fields of the chosen `type`.               |
| `the switch expression does not cover all possible input values` | A method was added and a switch does not handle it.        | Add the `case`. That error is the feature.               |
| `release version 25 not supported`                               | Maven is using an older JDK.                               | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`. |

## Project layout

``` tree
stations/018-payment-methods-with-sealed-interfaces/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/paysetu/payments/
│   ├── PaymentIntentController.java   ├── PaymentMethod.java
│   ├── Methods.java                   └── PaymentsApplication.java
├── src/test/java/com/paysetu/payments/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/paysetu/payments/PaymentIntentController.java`

Does  
Validates the request, checks the bank is offered, and builds the intent.

Why  
The controller never asks which method it has, except for the one rule that only applies to net banking.

Without it  
`if (vpa != null) … else if …` chains.

#### `src/main/java/com/paysetu/payments/PaymentMethod.java`

Does  
The sealed interface and its four records, with the JSON type names.

Why  
"Exactly one of" written as a type: impossible states cannot be built.

Without it  
One class with four nullable fields.

- `@JsonTypeInfo` and `@JsonSubTypes` map `"type"` to a record.
- Compact constructors normalise UPI IDs and bank codes with `Locale.ROOT`.
- `WRITE_ONLY` keeps the token and mobile out of responses.

#### `src/main/java/com/paysetu/payments/Methods.java`

Does  
Next action and refund route: one switch each, no default.

Why  
Record patterns unpack fields in the `case`; the compiler checks every method is handled.

Without it  
The trap: a refund chain with no wallet branch.

#### `src/main/resources/application.yaml`

Problem bodies for errors, and `fail-on-unknown-properties`: a field from another method is a `400`.

#### `src/main/java/com/paysetu/payments/PaymentsApplication.java`

Standard Spring Boot entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                           | Test class                      | Result |
|---------------|-----------------------------------------------------------------------|---------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found (a bank that is not offered) | `PaymentIntentContractTest` (5) | pass   |
| Every station | Reproduce the failure before the fix                                  | `ForgottenWalletTrapTest` (3)   | pass   |
| This station  | Every permitted method, found by reflection                           | `EveryMethodTest` (3)           | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payments.PaymentIntentContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payments.ForgottenWalletTrapTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payments.EveryMethodTest
[INFO] Tests run: 11, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/paysetu/payments/ForgottenWalletTrapTest.java`

Written first: the old refund chain's `null`, the old class's mixed payment, and the sealed model's answers.

#### `src/test/java/com/paysetu/payments/PaymentIntentContractTest.java`

Each method, what is never echoed, and every refusal.

#### `src/test/java/com/paysetu/payments/EveryMethodTest.java`

Builds a placeholder of every permitted record by reflection, so a method added later is tested without editing this file.

#### `src/test/java/com/paysetu/payments/ApiTest.java`

Shared setup: the whole app through MockMvc and a helper that posts an intent.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/paysetu/payments/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=ReadBackChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 11 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 15 tests pass (11 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Read an intent back

Keep each intent in memory, answer `GET /payment-intents/{id}`, and return a `Location` header from the POST. An unknown id is `404`.

**Done when:** both tests in `ReadBackChallengeTest` pass, and the card token is still never returned.

Hints

- A `ConcurrentHashMap` keyed by id is enough here.
- `ResponseEntity.created(uri).body(intent)` gives the 201 and the header together.

#### `challenge/ReadBackChallengeTest.java`

``` code
package com.paysetu.payments;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: keep each intent, answer GET /payment-intents/{id}, and point to it with a Location header. */
class ReadBackChallengeTest extends ApiTest {

    @Test
    void anIntentCanBeReadBackWithoutItsCardToken() throws Exception {
        String location = intent("{\"type\":\"CARD\",\"network\":\"VISA\",\"last4\":\"1111\",\"token\":\"tok_a1b2c3d4e5f6\"}")
                .andExpect(header().string("Location", matchesPattern("/payment-intents/pi_[0-9a-f]{32}")))
                .andReturn().getResponse().getHeader("Location");
        mvc.perform(get(location))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(location.substring("/payment-intents/".length())))
                .andExpect(jsonPath("$.method.type").value("CARD"))
                .andExpect(jsonPath("$.method.token").doesNotExist());
    }

    @Test
    void anUnknownIntentIs404() throws Exception {
        mvc.perform(get("/payment-intents/pi_00000000000000000000000000000000"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.title").value("Payment intent not found"));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 25 minutes

## A fifth method: pay later

Add `PAY_LATER` (Paysetu Pay Later, fictional) with a `mobile`. Add the record to the `permits` list and build: the compiler names every switch that needs a new case.

**Done when:** both tests in `PayLaterChallengeTest` pass, and `EveryMethodTest` covers the new method without changes.

Hints

- Copy the wallet record's shape: a write-only mobile and a masked one.
- Register the JSON name in `@JsonSubTypes`, or `EveryMethodTest` will tell you.

#### `challenge/PayLaterChallengeTest.java`

``` code
package com.paysetu.payments;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: a fifth method, PAY_LATER, for Paysetu Pay Later (fictional) by mobile number. Add the record and let
 * the compiler show you every switch that must handle it. EveryMethodTest picks it up on its own.
 */
class PayLaterChallengeTest extends ApiTest {

    @Test
    void payLaterHasItsOwnNextActionAndRefundRoute() throws Exception {
        intent("{\"type\":\"PAY_LATER\",\"mobile\":\"9123456780\"}")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.method.type").value("PAY_LATER"))
                .andExpect(jsonPath("$.method.maskedMobile").value("91******80"))
                .andExpect(jsonPath("$.nextAction.type").value("APPROVE_PAY_LATER"))
                .andExpect(jsonPath("$.refundRoute").value("Back to the Paysetu Pay Later account of 91******80, lowering what is due."));
    }

    @Test
    void aBadMobileIs400() throws Exception {
        intent("{\"type\":\"PAY_LATER\",\"mobile\":\"0123\"}").andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Switches or methods on the records?

This station keeps `nextAction` and `refundRoute` as switches in one class. They could instead be methods on each record. With twelve methods and six operations, which is easier to change when a method is added, and which when an operation is added? Where would you want the compiler to help?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old refund chain returns `null` for a wallet.
2.  Write the sealed interface and one record per method, with their own validation.
3.  Map JSON `type` to records; refuse unknown fields.
4.  Write the switches without `default`; check by reflection that every method is reachable and handled.

## Design alternatives and trade-offs

| Approach                              | What it costs                                                                         | Verdict                      |
|---------------------------------------|---------------------------------------------------------------------------------------|------------------------------|
| Sealed interface + records + switches | A switch to update per operation when a method is added; the compiler finds them all. | Chosen                       |
| One class with nullable fields        | Impossible states (UPI and card at once); every new method is a hunt.                 | Wrong                        |
| A `default` branch in each switch     | Compiles when a method is forgotten: the trap, back again.                            | Wrong                        |
| An enum `type` plus a map of fields   | Loose typing; validation by hand.                                                     | Avoid                        |
| Methods on each record (polymorphism) | Easy to add a method, harder to add an operation; logic spread across records.        | Good when operations are few |

## Database design

None in this station. With a database: one `payment_intents` table with a `method_type` column and a check constraint per type that exactly its own columns are set (for example, `method_type = 'UPI'` requires `vpa` and forbids `card_last4`). The database then refuses mixed methods too.

# 3 · Go deeper: Production

Card data  
In India, RBI's card-on-file tokenisation rules stop merchants from storing card numbers. This API accepts only a token and what may be displayed, and refuses a full number.

Privacy  
Mobile numbers and tokens are write-only. Logs need the same care: never log the request body as-is.

Evolution  
A new method changes the API: old clients that do not know `PAY_LATER` must still read responses. Document new `type` values before shipping them.

Real gateways  
UPI, cards and net banking each have their own flows, timeouts and failure states. This station models only the first step.

# 3 · Go deeper: Interview

## Interview takeaways

What does a sealed interface give you?

A closed list of implementations, known to the compiler. A switch over it can be exhaustive without a default, so adding an implementation makes every incomplete switch a compile error.

Why no default branch?

A default branch makes an incomplete switch compile. Without it, the compiler tells you every place a new case must be handled.

What is a record pattern?

case Upi(String vpa) -\> matches a Upi and binds its component in one step, instead of a cast and a getter.

How do you read polymorphic JSON safely?

A type property mapped to known subtypes, so an unknown type fails, and fail-on-unknown-properties, so fields from another type are refused instead of ignored.

How do you test every subtype without listing them?

Class.getPermittedSubclasses() gives the list at runtime; build a placeholder of each and check the behaviour, so a new subtype is covered automatically.

## Self-check rubric

| Area        | Meets the bar                                                | Above the bar                                                 |
|-------------|--------------------------------------------------------------|---------------------------------------------------------------|
| Correctness | All 11 tests pass.                                           | You can add a method and follow the compiler to every switch. |
| Modelling   | One record per method, no nullable fields for other methods. | You can explain why a default branch brings the trap back.    |
| Security    | Tokens and mobile numbers are never returned.                | You know why a full card number is refused.                   |
| Explanation | Sealed interfaces in two sentences.                          | Switches versus methods on records, and when each wins.       |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any "one of several kinds" code:

- Can an object be two kinds at once, or none?
- Does any switch or if-chain over the kinds have a default that hides a missing case?
- Can every kind arrive from JSON, and are other kinds' fields refused?
- Is any secret field echoed back in a response or a log?
