# Station 087 · Saving cards with network tokens

Working Systems · 0–2 years · Core · Payments · Types: Database, Security

Spring Boot 4.1.1 · Java 25 · Spring Security 7 (HTTP Basic) · card-on-file tokens (simulated network) · JdbcClient · PostgreSQL 17 · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The card network's token service is a simulation inside the app (SimNetwork): its "vault" is a map that stands for the network's side, and nothing is charged. The cards are standard test numbers that belong to nobody; the customers are demo data.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 17 tests.

# 1 · Understand

## The problem in real life

1.  **One-click checkout**

    A shop on Paysetu kept customers' card numbers for one-click checkout. A developer added a column "just for retries", so a failed payment could be sent again.

2.  **The breach**

    An attacker copied a database backup. Thousands of card numbers with expiry dates were in it. RBI's card-on-file rules, in force since 1 October 2022, allow only card issuers and networks to store card data at all.

3.  **The fix**

    The card number goes once to the card network's token service, which keeps it and returns a token. The shop keeps the token, the last four digits and the expiry. Payments and retries use the token.

The safest card number is the one you never had. Keep a token; let the network keep the card.

## What are we building?

Save a card as a network token (with the customer's consent), list saved cards, and pay with one. No card number is kept anywhere in our tables or logs.

## An everyday analogy

A hotel does not keep a copy of your house key. It gives you a key card that opens one room, for a while, and can be switched off. Losing it is a nuisance, not a disaster.

## How it works in 4 steps

1.  **Check** the number's shape and check digit, and that the customer said yes.
2.  **Send** it to the network's token service; get a token, the network and the last four digits back.
3.  **Keep** only the token and what the customer needs to recognise the card. Forget the number.
4.  **Pay** with the token and a fresh one-time cryptogram from the network.

Check yourself: a payment is declined and the customer taps "try again". Do you need the card number?

No. The retry asks the network for a new cryptogram for the same token: `afterSavingPayingAndRetryingTheCardNumberIsNowhereInOurDatabaseOrLog`. "Just for retries" was never a reason to keep it.

## What this station is not

- **Not a real network.** The token service is simulated; real ones are reached through a payment aggregator, with their own APIs.
- **Not a checkout page.** In real life the number is often typed into the aggregator's own form, so it never reaches the merchant at all (challenge 3).
- **Not legal advice.** The rules are summarised; read RBI's circulars and your aggregator's terms.

## Key terms

| Term                  | Simple meaning                                                                          | Everyday example                                | In this project                        |
|-----------------------|-----------------------------------------------------------------------------------------|-------------------------------------------------|----------------------------------------|
| **Card number (PAN)** | The 13 to 19 digits on the card. Whoever has it, with the expiry, can often pay.        | The key to a house.                             | sent once to the network, never kept   |
| **Token**             | A stand-in for the card that only works for one merchant, through the network.          | A hotel key card that opens one room.           | `tkn_` + 20 letters                    |
| **Card network**      | Visa, Mastercard, RuPay: they run the card system and its token service.                | The company that makes the hotel's lock system. | `SimNetwork` (simulated)               |
| **Cryptogram**        | A one-time value the network gives for each payment with a token.                       | A one-time password.                            | `cryptogram`                           |
| **Consent**           | The customer saying yes to saving the card, each time.                                  | Ticking "save this card".                       | `consent: true`                        |
| **PCI DSS scope**     | Every system that touches card numbers must meet the card industry's security standard. | Every room the key passes through needs a lock. | kept small by never holding the number |

# 2 · Build: Spec

## Business problem

**Paysetu** (a fictional payments company): a merchant's breach exposed card numbers kept for one-click checkout, which RBI's rules do not allow merchants to store.

## Acceptance criteria

Demo customers: asha (customer 1) and rohan (customer 2), password `name-demo-pass`. Demo rules of the simulation: cards starting 4 are VISA, 5 MASTERCARD, 6 RUPAY; an amount ending in 51 paise is declined.

1.  **Given** a valid card and consent, **then** `201` with the network, last four digits and expiry; no number, no token in the answer.
2.  **Given** a wrong check digit, a wrong length or no consent, **then** `400`, and the number is not repeated in the answer or the log.
3.  **Given** an expired or unsupported card, **then** `422`.
4.  **Given** a payment with a saved card, **then** the token pays; a retry of the same order gets the same payment.
5.  **Given** another customer's cards, **then** `403` for their path, `404` for their card id; no sign-in, `401`.

## Requirements

- No card number in any table, log line, error message or object's printout.
- The database refuses a card number in the token and last-four columns.
- The customer id comes from the sign-in, never from the request alone.

## Learning objectives

- Explain card-on-file tokenisation and why it shrinks what a breach can take.
- Keep sensitive input out of fields, columns, logs and error messages.
- Handle a token's life: create, use with a cryptogram, expire, delete.
- Test that sensitive data is absent, with a test that can fail.

# 2 · Build: API contract

## Endpoints

| Method | Path                          | Purpose                                                                                           |
|--------|-------------------------------|---------------------------------------------------------------------------------------------------|
| `POST` | `/customers/{id}/saved-cards` | `{cardNumber, expiryMonth, expiryYear, consent}`: save a card as a token.                         |
| `GET`  | `/customers/{id}/saved-cards` | The customer's saved cards: network, last four, expiry.                                           |
| `POST` | `/payments`                   | `{orderId, savedCardId, amountPaise}`: pay with a saved card. Safe to repeat with the same order. |

## Status codes

| Status    | When                                                                                        |
|-----------|---------------------------------------------------------------------------------------------|
| 200 / 201 | Listed / saved, or paid (also on a retry)                                                   |
| 400       | Card number of the wrong shape, length or check digit; no consent; a bad order id or amount |
| 401       | No sign-in, or a wrong password                                                             |
| 402       | Declined                                                                                    |
| 403       | Another customer's saved cards                                                              |
| 404       | No such saved card for this customer (also someone else's)                                  |
| 409       | The order id belongs to another customer                                                    |
| 422       | The network refuses the card (expired, unsupported), or the saved card has expired          |

## Captured examples

Captured with curl from the running app on 22 Oct 2026, in this order. JSON bodies are indented for reading; `Date`, connection and standard security headers are left out.

### Case 1: Asha saves a card

**Why:** spaces are allowed; the answer has no number and no token.

Request

``` code
POST /customers/1/saved-cards HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "cardNumber": "4111 1111 1111 1111",
  "expiryMonth": 12,
  "expiryYear": 2028,
  "consent": true
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 75

{
  "id": 1,
  "network": "VISA",
  "last4": "1111",
  "expiryMonth": 12,
  "expiryYear": 2028
}
```

### Case 2: Asha lists her cards

**Why:** what she needs to recognise it.

Request

``` code
GET /customers/1/saved-cards HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 77

[
  {
    "id": 1,
    "network": "VISA",
    "last4": "1111",
    "expiryMonth": 12,
    "expiryYear": 2028
  }
]
```

### Case 3: Rohan asks for Asha's cards

**Why:** `403`, before anything is read.

Request

``` code
GET /customers/1/saved-cards HTTP/1.1
Authorization: Basic cm9oYW46cm9oYW4tZGVtby1wYXNz
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json
Content-Length: 114

{
  "title": "Not allowed",
  "status": 403,
  "detail": "This sign-in cannot do this.",
  "instance": "/customers/1/saved-cards"
}
```

### Case 4: no sign-in

**Why:** `401`.

Request

``` code
GET /customers/1/saved-cards HTTP/1.1
```

Response

``` code
HTTP/1.1 401 
WWW-Authenticate: Basic realm="paysetu"
Content-Type: application/problem+json
Content-Length: 126

{
  "title": "Sign-in required",
  "status": 401,
  "detail": "Send a valid username and password.",
  "instance": "/customers/1/saved-cards"
}
```

### Case 5: a mistyped number

**Why:** the check digit catches it; the number is not repeated.

Request

``` code
POST /customers/1/saved-cards HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "cardNumber": "4111111111111112",
  "expiryMonth": 12,
  "expiryYear": 2028,
  "consent": true
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "This is not a valid card number",
  "instance": "/customers/1/saved-cards",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 6: consent false

**Why:** `400`; nothing is sent to the network.

Request

``` code
POST /customers/1/saved-cards HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "cardNumber": "5555555555554444",
  "expiryMonth": 1,
  "expiryYear": 2027,
  "consent": false
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/customers/1/saved-cards",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 7: Asha pays with her saved card

**Why:** the token and a fresh cryptogram.

Request

``` code
POST /payments HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "orderId": "ORD-1001",
  "savedCardId": 1,
  "amountPaise": 129900
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json

{
  "id": 1,
  "orderId": "ORD-1001",
  "savedCardId": 1,
  "amountPaise": 129900,
  "status": "succeeded",
  "networkRef": "auth_2"
}
```

### Case 8: the same order again

**Why:** the same payment.

Request

``` code
POST /payments HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "orderId": "ORD-1001",
  "savedCardId": 1,
  "amountPaise": 129900
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json

{
  "id": 1,
  "orderId": "ORD-1001",
  "savedCardId": 1,
  "amountPaise": 129900,
  "status": "succeeded",
  "networkRef": "auth_2"
}
```

### Case 9: Rohan tries Asha's card id

**Why:** `404`: not his, and not confirmed to exist.

Request

``` code
POST /payments HTTP/1.1
Authorization: Basic cm9oYW46cm9oYW4tZGVtby1wYXNz
Content-Type: application/json

{
  "orderId": "ORD-2001",
  "savedCardId": 1,
  "amountPaise": 129900
}
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No such saved card",
  "instance": "/payments",
  "status": 404,
  "title": "Not Found"
}
```

### Case 10: a decline (amount ending in 51 paise)

**Why:** `402`.

Request

``` code
POST /payments HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "orderId": "ORD-1002",
  "savedCardId": 1,
  "amountPaise": 129951
}
```

Response

``` code
HTTP/1.1 402 
Content-Type: application/json

{
  "id": 2,
  "orderId": "ORD-1002",
  "savedCardId": 1,
  "amountPaise": 129951,
  "status": "declined",
  "networkRef": null
}
```

## What is stored

``` code
 id | customer_id |        token_ref         | network | last4 | expiry_month | expiry_year | status 
----+-------------+--------------------------+---------+-------+--------------+-------------+--------
  1 |           1 | tkn_vgwsnyddskzefluuvooc | VISA    | 1111  |           12 |        2028 | active
(1 row)
```

``` code
 id | order_id | saved_card_id | amount_paise |  status   | network_ref 
----+----------+---------------+--------------+-----------+-------------
  1 | ORD-1001 |             1 |       129900 | succeeded | auth_2
  2 | ORD-1002 |             1 |       129951 | declined  | 
(2 rows)
```

Searched by `docs/capture.sh` with `pg_dump --data-only | grep -c`, after the captures above:

``` code
Lines in a full data dump of the database containing 4111111111111111: 0
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                       | What happens                               | Proved by                                              |
|------------------------------------------------------------|--------------------------------------------|--------------------------------------------------------|
| Save VISA, MASTERCARD, RUPAY; list                         | Network, last four, expiry; own cards only | `aSavedCardShowsOnlyWhatTheCustomerNeedsToRecogniseIt` |
| Wrong check digit, too short, dashes, month 13, no consent | `400`                                      | `badCardsAre400AndRefusedOnesAre422`                   |
| Expired or unsupported card                                | `422` from the network                     | `badCardsAre400AndRefusedOnesAre422`                   |
| Pay; a decline                                             | `201`; `402`                               | `aPaymentWithASavedCardUsesItsToken`                   |
| The same order twice                                       | One payment, the same body                 | `theSameOrderTwiceIsOnePayment`                        |
| A retry after the card expired                             | The first answer, not a `422`              | `aRetryAfterTheCardExpiredStillGetsTheFirstAnswer`     |
| The last minute of the expiry month, in IST                | Still valid; one second later `422`        | `anExpiredSavedCardIs422`                              |
| No sign-in, wrong password                                 | `401`                                      | `withoutAValidSignInEverythingIs401`                   |
| Another customer's path; their card id                     | `403`; `404`                               | `oneCustomerCannotSeeOrAddToAnothersCards`             |
| Another customer's order id                                | `409`, never their payment                 | `anOrderIdBelongsToOneCustomer`                        |
| Injection-shaped and 5,000-digit input                     | `400` before anything runs                 | `maliciousInputIsRefusedBeforeAnythingRuns`            |
| A card number written by plain SQL                         | Refused by the shape constraints           | `aCardNumberCannotBeStoredAsATokenOrALast4`            |
| The saved card cannot be recorded                          | The token is deleted at the network        | `aCardThatCannotBeRecordedLeavesNoTokenAtTheNetwork`   |

## The trap

Plausible but wrong

Keeping the card number "just for retries", which breaks RBI's rules and pulls every system into PCI scope.

- **The search can find it.** The test searches every text column of every table for the digits. On a table shaped like the old design it finds `old_saved_cards.card_number`: the search is able to fail.
- **Nowhere now.** After saving a card, a declined payment, a retry, a save without consent and a mistyped number, the same search finds nothing, and the application's log does not contain the number. The network's vault does: that is the network's side.
- **Printing the request.** A Java record's default `toString` prints every field, so one log line or a debugger shows the number. The request masks it.

While building, each part was undone once: no check digit turned 2 tests red; no length check 1; the number in the error message 1; the number stored as the token 8; no owner check on the path 1; any customer's card id 1; another customer's order id answered 1; no expiry check 1; the expiry month in UTC 1; the token left at the network when saving failed 1; no consent 1; the default `toString` 1; no replay check before the card checks 1.

``` code
package com.paysetu.cards;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old code kept the card number in saved_cards "just for retries": the breach copied it. These
 * tests search every text column of every table, and the application's log, for the card number.
 */
@ExtendWith(OutputCaptureExtension.class)
class CardNumberStorageTrapTest extends ApiTest {

    /** Every table and text column holding these digits. */
    List<String> placesHolding(String digits) {
        List<String> found = new ArrayList<>();
        for (Map<String, Object> c : jdbc.sql("""
                SELECT table_name, column_name FROM information_schema.columns
                WHERE table_schema = current_schema() AND data_type IN ('text', 'character varying')""").query().listOfRows()) {
            String sql = "SELECT count(*) FROM \"%s\" WHERE \"%s\" LIKE ?".formatted(c.get("table_name"), c.get("column_name"));
            if (jdbc.sql(sql).param("%" + digits + "%").query(Long.class).single() > 0) {
                found.add(c.get("table_name") + "." + c.get("column_name"));
            }
        }
        return found;
    }

    @Test
    void theOldDesignKeptTheCardNumberAndTheSearchFindsIt() {
        jdbc.sql("CREATE TABLE old_saved_cards (customer_id bigint, card_number text, token_ref text)").update();
        try {
            jdbc.sql("INSERT INTO old_saved_cards VALUES (1, ?, 'tkn_abcdefghijklmnopqrst')").param(VISA).update();   // "just for retries"
            assertThat(placesHolding(VISA)).containsExactly("old_saved_cards.card_number");
        } finally {
            jdbc.sql("DROP TABLE old_saved_cards").update();
        }
    }

    @Test
    void afterSavingPayingAndRetryingTheCardNumberIsNowhereInOurDatabaseOrLog(CapturedOutput log) throws Exception {
        long card = savedCardId("asha", ASHA, VISA);
        pay("asha", "ORD-1", card, 50051).andExpect(status().isPaymentRequired());   // declined
        pay("asha", "ORD-2", card, 50000).andExpect(status().isCreated());           // the retry uses the token, not the number
        save("asha", ASHA, "{\"cardNumber\":\"" + VISA + "\",\"expiryMonth\":12,\"expiryYear\":2028,\"consent\":false}").andExpect(status().isBadRequest());
        save("asha", ASHA, "{\"cardNumber\":\"4111111111111112\",\"expiryMonth\":12,\"expiryYear\":2028,\"consent\":true}").andExpect(status().isBadRequest());
        assertThat(placesHolding(VISA)).isEmpty();
        assertThat(placesHolding(VISA.substring(0, 12))).isEmpty();
        assertThat(log.getAll()).doesNotContain(VISA).doesNotContain("4111111111111112");
        assertThat(network.holds(VISA)).isTrue();   // the network's vault has it, outside Paysetu's systems
    }

    @Test
    void theRequestNeverPrintsTheCardNumber() {
        assertThat(new CardController.SaveCardRequest(VISA, 12, 2028, true).toString()).doesNotContain(VISA).contains("****");
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
./mvnw test                 # all 17 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Save a card, then search a full dump of the database for its number:

``` code
curl -s -u asha:asha-demo-pass -X POST http://localhost:8080/customers/1/saved-cards -H 'Content-Type: application/json' -d '{"cardNumber": "4111 1111 1111 1111", "expiryMonth": 12, "expiryYear": 2028, "consent": true}'
docker compose exec -T postgres pg_dump -U paysetu -d paysetu --data-only | grep -c 4111111111111111
```

The count is `0`, as in `docs/captures/dump-search.txt`. The search over every text column in `CardNumberStorageTrapTest` does the same inside the tests.

## Troubleshooting

| You see                                     | Cause                                                                           | Fix                                                                 |
|---------------------------------------------|---------------------------------------------------------------------------------|---------------------------------------------------------------------|
| A card number in a log line                 | Something printed the request: a record's default `toString` shows every field. | Mask it in `toString`, and never log request bodies with card data. |
| `401` with the right password               | The user is not one of the demo users.                                          | Use asha or rohan with `name-demo-pass`.                            |
| `Could not find a valid Docker environment` | Docker is not running.                                                          | Start Docker Desktop or the Docker service.                         |

## Project layout

``` tree
stations/087-saving-cards-with-network-tokens/
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
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/paysetu/cards/SecurityConfig.java`

Does  
Who may call what.

Why  
HTTP Basic with demo customers; saved cards and payments need the CUSTOMER role; everything else is refused.

Without it  
Anyone reading anyone's saved cards.

#### `src/main/java/com/paysetu/cards/CardController.java`

Does  
The three endpoints.

Why  
Checks the number's shape, the expiry and consent; makes sure the path's customer is the signed-in one; masks the number in `toString`.

Without it  
A card number in a log line, and one customer's cards in another's app.

- Someone else's customer id is `403`; someone else's card id in a payment is `404`, so it does not confirm that the card exists.
- The record overrides `toString`: by default it prints every field.

#### `src/main/java/com/paysetu/cards/Cards.java`

Does  
Saving, listing and paying.

Why  
The number is a parameter that goes to the network and nowhere else; the payment row is written before the network is called; expiry is checked by the month in IST.

Without it  
Card numbers in the database, double charges on a double tap.

- If the saved card cannot be recorded, the token is deleted at the network, so nothing usable is left behind.
- A retry of an order is answered before the card checks: the payment happened, whatever the card's state is now.

#### `src/main/java/com/paysetu/cards/Customers.java`

The customer id of the signed-in user, from the database.

#### `src/main/java/com/paysetu/cards/SimNetwork.java`

The simulated network's token service: provisions tokens, issues one-time cryptograms, authorises. Its vault stands for the network's side. Nothing is charged.

#### `src/main/java/com/paysetu/cards/ProblemResponses.java`

`401` and `403` in the same problem shape as other errors.

#### `src/main/resources/db/migration/V1__customers_saved_cards_payments.sql`

Does  
Customers, saved cards and payments.

Why  
Shape rules on the token and the last four digits make a card number impossible to store in them.

Without it  
A "temporary" column or a script putting the number back.

#### `src/main/resources/db/migration/V2__demo_customers.sql`

Two customers.

#### `src/main/resources/application.yaml`

Database connection; fractions refused for whole-number fields.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/paysetu/cards/CardsApplication.java`

Entry point, and the `Clock` expiry is checked against.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                       | Test class                                          | Result |
|---------------|-------------------------------------------------------------------|-----------------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                          | `SavedCardContractTest` (2), `TokenPaymentTest` (5) | pass   |
| Every station | Reproduce the failure before the fix                              | `CardNumberStorageTrapTest` (3)                     | pass   |
| Database      | Rollback and constraint tests against a real database             | `CardDatabaseTest` (3)                              | pass   |
| Security      | 401, 403, one user accessing another user's data, malicious input | `CardSecurityTest` (4)                              | pass   |

Two tests were corrected while building. The "too short" card number first failed its check digit, so removing the length check changed nothing; it is now a short number with a valid check digit. Removing the replay check before the card checks changed nothing either, because the unique order id returned the same payment; a retry after the card expired now shows the difference.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.cards.CardDatabaseTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.cards.TokenPaymentTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.cards.SavedCardContractTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.cards.CardSecurityTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.cards.CardNumberStorageTrapTest
[INFO] Tests run: 17, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/paysetu/cards/CardNumberStorageTrapTest.java`

Written first: the search over every text column, and the log.

#### `src/test/java/com/paysetu/cards/SavedCardContractTest.java`

Saving and listing through HTTP; bad and refused cards.

#### `src/test/java/com/paysetu/cards/TokenPaymentTest.java`

Paying with a token, retries, expiry at the IST month boundary.

#### `src/test/java/com/paysetu/cards/CardSecurityTest.java`

401, 403, other customers' cards and orders, malicious input.

#### `src/test/java/com/paysetu/cards/CardDatabaseTest.java`

Shape rules and named constraints with plain SQL; a card that cannot be recorded.

#### `src/test/java/com/paysetu/cards/ApiTest.java`

Shared setup: the test clock, the network simulation and customers before each test, request helpers, test card numbers.

#### `src/test/java/com/paysetu/cards/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/paysetu/cards/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=DeleteSavedCardChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 17 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 22 tests pass (17 station tests and 5 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Delete a saved card

`DELETE /customers/{id}/saved-cards/{cardId}`: the token is deleted at the network, the card leaves the list and cannot pay. Deleting it again is still `204`; another customer's path `403`; an unknown card `404`.

**Done when:** both tests in `DeleteSavedCardChallengeTest` pass.

Hints

- The security rules match paths: `/customers/*/saved-cards/*` needs adding.
- Mark the row deleted rather than removing it: payments still point at it.

#### `challenge/DeleteSavedCardChallengeTest.java`

``` code
package com.paysetu.cards;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.ResultActions;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: DELETE /customers/{id}/saved-cards/{cardId}. The token is deleted at the network too, the card leaves the
 * list and cannot pay; deleting it again is still 204. Another customer's card is 403, an unknown one 404.
 */
class DeleteSavedCardChallengeTest extends ApiTest {

    ResultActions remove(String user, long customer, long card) throws Exception {
        return mvc.perform(delete("/customers/{id}/saved-cards/{card}", customer, card).with(httpBasic(user, password(user))));
    }

    @Test
    void aDeletedCardIsGoneEverywhere() throws Exception {
        long card = savedCardId("asha", ASHA, VISA);
        remove("asha", ASHA, card).andExpect(status().isNoContent());
        remove("asha", ASHA, card).andExpect(status().isNoContent());
        list("asha", ASHA).andExpect(jsonPath("$.length()").value(0));
        pay("asha", "ORD-1", card, 50000).andExpect(status().isNotFound());
        assertThat(network.holds(VISA)).isFalse();
    }

    @Test
    void onlyTheOwnerCanDeleteAndUnknownCardsAre404() throws Exception {
        long card = savedCardId("asha", ASHA, VISA);
        remove("rohan", ASHA, card).andExpect(status().isForbidden());
        remove("rohan", ROHAN, card).andExpect(status().isNotFound());   // Asha's card through Rohan's own path
        remove("asha", ASHA, 99).andExpect(status().isNotFound());
        assertThat(network.holds(VISA)).isTrue();
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Events from the network

`POST /network/token-events`, signed in as the network (`sim-network`): `UPDATED` with a new expiry when the bank re-issues the card (the token stays, and payments work again), `SUSPENDED` and `RESUMED`. Customers get `403`.

**Done when:** the three tests in `TokenEventsChallengeTest` pass.

Hints

- A new role, `NETWORK`, and a user for it.
- A V3 migration lets `saved_cards_status` hold `suspended`; a suspended card answers `422`, not `404`.

#### `challenge/TokenEventsChallengeTest.java`

``` code
package com.paysetu.cards;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import java.time.Instant;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: the network tells Paysetu about a token's life. POST /network/token-events, signed in as the network
 * (user sim-network, password sim-network-demo-pass): UPDATED with a new expiry when the bank re-issues the card (the
 * token stays the same), SUSPENDED and RESUMED. Customers may not send events. A V3 migration allows "suspended".
 */
class TokenEventsChallengeTest extends ApiTest {

    String tokenOf(long card) {
        return jdbc.sql("SELECT token_ref FROM saved_cards WHERE id = ?").param(card).query(String.class).single();
    }

    ResultActions event(String user, String json) throws Exception {
        return mvc.perform(post("/network/token-events").with(httpBasic(user, password(user))).contentType(MediaType.APPLICATION_JSON).content(json));
    }

    @Test
    void aReissuedCardKeepsItsTokenWithTheNewExpiry() throws Exception {
        long card = savedCardId("asha", ASHA, VISA);   // 12/2028
        CLOCK.now = Instant.parse("2029-01-10T06:30:00Z");
        pay("asha", "ORD-1", card, 50000).andExpect(status().isUnprocessableContent());
        event("sim-network", "{\"tokenRef\":\"%s\",\"event\":\"UPDATED\",\"expiryMonth\":12,\"expiryYear\":2033}".formatted(tokenOf(card))).andExpect(status().isNoContent());
        pay("asha", "ORD-2", card, 50000).andExpect(status().isCreated());
        list("asha", ASHA).andExpect(jsonPath("$[0].expiryYear").value(2033));
    }

    @Test
    void aSuspendedTokenCannotPayUntilResumed() throws Exception {
        long card = savedCardId("asha", ASHA, VISA);
        event("sim-network", "{\"tokenRef\":\"%s\",\"event\":\"SUSPENDED\"}".formatted(tokenOf(card))).andExpect(status().isNoContent());
        pay("asha", "ORD-3", card, 50000).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("This saved card is suspended by the bank"));
        event("sim-network", "{\"tokenRef\":\"%s\",\"event\":\"RESUMED\"}".formatted(tokenOf(card))).andExpect(status().isNoContent());
        pay("asha", "ORD-4", card, 50000).andExpect(status().isCreated());
    }

    @Test
    void onlyTheNetworkSendsEventsAndUnknownTokensAre404() throws Exception {
        long card = savedCardId("asha", ASHA, VISA);
        event("asha", "{\"tokenRef\":\"%s\",\"event\":\"SUSPENDED\"}".formatted(tokenOf(card))).andExpect(status().isForbidden());
        event("sim-network", "{\"tokenRef\":\"tkn_aaaaaaaaaaaaaaaaaaaa\",\"event\":\"SUSPENDED\"}").andExpect(status().isNotFound());
        event("sim-network", "{\"tokenRef\":\"%s\",\"event\":\"STOLEN\"}".formatted(tokenOf(card))).andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Never even seeing the number

Here the card number still passes through Paysetu's API on its way to the network. Redesign checkout so it never does: the customer types it into the aggregator's own form or SDK, and Paysetu only receives a token. What changes for PCI DSS scope, for logs and for support? And for guest checkout without saving: what may be kept, and for how long?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: a search over every text column, shown to find a number in an old-design table.
2.  Save: check shape, check digit and consent; send to the network; keep the token and display data only.
3.  Pay: write the payment row, get a cryptogram, authorise, record.
4.  Lock down who sees what, and make the database refuse a number in the card columns.

## Design alternatives and trade-offs

| Approach                                      | What it costs                                                               | Verdict                    |
|-----------------------------------------------|-----------------------------------------------------------------------------|----------------------------|
| Network tokens; keep token, last four, expiry | Depends on the network and aggregator for every payment.                    | Chosen                     |
| Keep the card number "just for retries"       | Breaks RBI's rules; a breach takes the cards; every system in PCI scope.    | The trap                   |
| Keep it encrypted                             | Still card data stored by the merchant; the key is one more secret to lose. | Not allowed for merchants  |
| Aggregator's hosted form or SDK               | The number never reaches Paysetu; less control over the page.               | Better still (challenge 3) |
| Ask for the card every time                   | Safe, but no one-click checkout.                                            | Fine for guests            |

## Database design

| Object                                               | What   | Why                                                               |
|------------------------------------------------------|--------|-------------------------------------------------------------------|
| `saved_cards_token_shape`, `saved_cards_last4_shape` | CHECKs | A card number cannot be written into these columns by any writer. |
| `saved_cards_token_unique`                           | UNIQUE | One saved card per token.                                         |
| `payments_order_once`                                | UNIQUE | One payment per order, written before the network is called.      |
| `payments_succeeded_has_ref`                         | CHECK  | A succeeded payment can be found at the network.                  |

**Transaction boundaries:** no transaction is open while the network is called. A saved card is one insert after the token exists; if it fails, the token is deleted at the network.

``` code
CREATE TABLE customers (
    id       bigint CONSTRAINT customers_pk PRIMARY KEY,
    username text NOT NULL CONSTRAINT customers_username_unique UNIQUE
);

-- What a merchant may keep: the token service's reference, and what the customer needs to recognise the card.
-- No card number, no CVV, ever. The shape rules make a card number impossible to store in any of these columns.
CREATE TABLE saved_cards (
    id           bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT saved_cards_pk PRIMARY KEY,
    customer_id  bigint NOT NULL CONSTRAINT saved_cards_customer_fk REFERENCES customers,
    token_ref    text NOT NULL CONSTRAINT saved_cards_token_unique UNIQUE,
    network      text NOT NULL,
    last4        text NOT NULL,
    expiry_month smallint NOT NULL,
    expiry_year  smallint NOT NULL,
    status       text NOT NULL DEFAULT 'active',
    consent_at   timestamptz NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT saved_cards_token_shape CHECK (token_ref ~ '^tkn_[a-z]{20}$'),
    CONSTRAINT saved_cards_last4_shape CHECK (last4 ~ '^[0-9]{4}$'),
    CONSTRAINT saved_cards_network CHECK (network IN ('VISA', 'MASTERCARD', 'RUPAY')),
    CONSTRAINT saved_cards_expiry CHECK (expiry_month BETWEEN 1 AND 12 AND expiry_year BETWEEN 2000 AND 2100),
    CONSTRAINT saved_cards_status CHECK (status IN ('active', 'deleted'))
);

CREATE TABLE payments (
    id            bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT payments_pk PRIMARY KEY,
    customer_id   bigint NOT NULL CONSTRAINT payments_customer_fk REFERENCES customers,
    saved_card_id bigint NOT NULL CONSTRAINT payments_saved_card_fk REFERENCES saved_cards,
    order_id      text NOT NULL CONSTRAINT payments_order_once UNIQUE,
    amount_paise  bigint NOT NULL,
    status        text NOT NULL,
    network_ref   text,
    created_at    timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT payments_amount_positive CHECK (amount_paise > 0),
    -- pending: sent to the network; failed: the network refused the token, nothing was charged.
    CONSTRAINT payments_status CHECK (status IN ('pending', 'succeeded', 'declined', 'failed')),
    CONSTRAINT payments_succeeded_has_ref CHECK (status <> 'succeeded' OR network_ref IS NOT NULL)
);
```

# 3 · Go deeper: Production

Rules  
RBI's card-on-file tokenisation rules, in force since 1 October 2022, allow only card issuers and networks to store card data; merchants keep tokens, with the customer's consent. Read the circulars themselves and your aggregator's terms.

Logs and tools  
Request logging, error trackers, APM and support tools copy bodies by default in many setups. Mask card fields before anything leaves the process.

Token life  
Networks tell you when a card is re-issued or a token suspended (challenge 2); a token outlives the plastic card, which is part of why checkout keeps working.

Scope  
Every system the number passes through is in PCI DSS scope. Fewer systems, smaller audits, smaller breaches.

# 3 · Go deeper: Interview

## Interview takeaways

What is a network token?

A stand-in for a card number, issued by the card network for one merchant. It is useless elsewhere, can be suspended or deleted, and survives a card re-issue.

Why not keep the card number encrypted?

In India, RBI's rules do not allow merchants to store card data at all. Elsewhere it keeps you in PCI scope, and a breach of the key exposes everything.

How do you retry a declined payment without the card number?

With the token: ask the network for a new one-time cryptogram and send the payment again.

How do you prove card numbers are not stored or logged?

Search every text column and the captured log for the digits in a test, and show the search finds them in a table built the old way.

Why 404 for someone else's card id but 403 for their path?

The path names the customer, which the caller already knows. A card id they do not own should not be confirmed to exist.

## Self-check rubric

| Area        | Meets the bar          | Above the bar                                                                 |
|-------------|------------------------|-------------------------------------------------------------------------------|
| Correctness | All 17 tests pass.     | You ran the flawed version and explained each failure.                        |
| Card data   | No card number column. | Not in logs, errors, toString or any table, proven by a search that can fail. |
| Access      | 401 and 403.           | 404 for others' card ids; the customer from the sign-in only.                 |
| Lifecycle   | Save and pay.          | Expiry in IST, retries with tokens, tokens cleaned up when saving fails.      |

# 3 · Go deeper: Review

## The pull request

A teammate helps support: a log line when a card is saved, and the masking `toString` removed as "noise". They also drop the owner check from listing cards, since it is read-only and shows only the last four digits. Read the file and list every problem before opening the findings.

#### `review/CardController.java`

``` code
package com.paysetu.cards;

import jakarta.validation.Valid;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.time.YearMonth;
import java.util.List;
import java.util.Locale;
import java.util.Map;

@RestController
class CardController {

    /** Spaces between groups of digits are allowed, as people type them. */
    record SaveCardRequest(@NotNull @Pattern(regexp = "[0-9]{4}( ?[0-9]{2,4}){2,4}") String cardNumber,
                           @Min(1) @Max(12) int expiryMonth, @Min(2000) @Max(2100) int expiryYear,
                           @AssertTrue(message = "the customer must agree to save the card") boolean consent) {
    }

    record PaymentRequest(@NotNull @Pattern(regexp = "[A-Za-z0-9-]{3,40}") String orderId, @Min(1) long savedCardId,
                          @Min(100) @Max(10_000_000) long amountPaise) {
    }

    private static final Map<String, HttpStatus> STATUS = Map.of("succeeded", HttpStatus.CREATED, "declined", HttpStatus.PAYMENT_REQUIRED,
            "pending", HttpStatus.ACCEPTED, "failed", HttpStatus.UNPROCESSABLE_CONTENT);

    private static final Logger log = LoggerFactory.getLogger(CardController.class);

    private final Cards cards;
    private final Customers customers;

    CardController(Cards cards, Customers customers) {
        this.cards = cards;
        this.customers = customers;
    }

    @PostMapping("/customers/{id}/saved-cards")
    @ResponseStatus(HttpStatus.CREATED)
    Cards.SavedCard save(@PathVariable long id, @Valid @RequestBody SaveCardRequest body, Authentication who) {
        own(id, who);
        log.info("Saving a card for customer {}: {}", id, body);   // support needs this to debug failed saves
        return cards.save(id, body.cardNumber().replace(" ", ""), YearMonth.of(body.expiryYear(), body.expiryMonth()));
    }

    @GetMapping("/customers/{id}/saved-cards")
    List<Cards.SavedCard> list(@PathVariable long id, Authentication who) {
        return cards.list(id);   // read-only, and it shows only the last 4 digits
    }

    /** Pays as the signed-in customer, with one of their saved cards. Safe to repeat with the same order id. */
    @PostMapping("/payments")
    ResponseEntity<Cards.Payment> pay(@Valid @RequestBody PaymentRequest body, Authentication who) {
        Cards.Payment p = cards.pay(customers.idOf(who), body.savedCardId(), body.orderId().toUpperCase(Locale.ROOT), body.amountPaise());
        return ResponseEntity.status(STATUS.get(p.status())).body(p);
    }

    /** A customer's own cards only: someone else's customer id is refused (403) before anything is read. */
    private void own(long customerId, Authentication who) {
        if (customers.idOf(who) != customerId) {
            throw new AccessDeniedException("not this customer's cards");
        }
    }
}
```

## Findings

1Logging the request

"Support needs this to debug failed saves": the log line prints the request record, and without the masking `toString` that is the full card number, in every log store and backup it reaches.

**Test evidence:** `afterSavingPayingAndRetryingTheCardNumberIsNowhereInOurDatabaseOrLog` and `theRequestNeverPrintsTheCardNumber` fail.

2No owner check on listing

"Read-only, and it shows only the last 4 digits": any signed-in customer can list anyone's saved cards by changing the id in the path, and the card ids they learn are what payments ask for.

**Test evidence:** `oneCustomerCannotSeeOrAddToAnothersCards` fails.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class                  | Fixed version | Flawed version |
|-----------------------------|---------------|----------------|
| `CardDatabaseTest`          | 3 / 3         | 3 / 3          |
| `SavedCardContractTest`     | 2 / 2         | 2 / 2          |
| `TokenPaymentTest`          | 5 / 5         | 5 / 5          |
| `CardNumberStorageTrapTest` | 3 / 3         | 1 / 3          |
| `CardSecurityTest`          | 4 / 4         | 3 / 4          |

The database is clean in the flawed version: the card number leaks through the log, which no database constraint can see. Only a test that reads the log catches it.
