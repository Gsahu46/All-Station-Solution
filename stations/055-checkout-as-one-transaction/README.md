# Station 055 · Checkout as one transaction

Working Systems · 0–2 years · Core · E-commerce · Types: Database

Spring Boot 4.1.1 · Java 25 · @Transactional proxies · rollback rules · readOnly transactions · JdbcClient · PostgreSQL 17 · Flyway · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Products, orders and payments are demo data, not Kartwala's. A payment is a record in the payments table: no gateway is called and no money moves. A real gateway call could not be undone by a database rollback (see Production).

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 11 tests.

# 1 · Understand

## The problem in real life

1.  **A transaction on paper**

    Kartwala's placeOrder() said @Transactional. It saved the order, then the payment record, then reserved stock line by line.

2.  **Paid, half reserved**

    Customers were charged for orders whose stock was only partly reserved. Logs showed an out-of-stock exception, and no rollback. The controller called checkout(), which called this.placeOrder(): the annotation was never reached.

3.  **The fix**

    Put @Transactional on the method the controller calls, through Spring's proxy; throw only exceptions that roll back; reserve stock before recording the payment.

An annotation is only as good as the call that reaches it. Know where your transaction starts.

## What are we building?

`POST /checkouts` takes a basket. It creates the order, reserves stock for every line, and records the payment, in one transaction. If anything fails, nothing is kept. `GET /checkouts/{id}` reads it back.

## An everyday analogy

A shop counter with a rule: the shopkeeper opens a bill, puts each item behind the counter, and takes the money last. If an item is missing, every item goes back on the shelf and the bill is torn up. The old code took the money first, and had nobody to enforce "tear it up" because it never opened the bill properly.

## How it works in 4 steps

1.  **The controller calls** `checkout()` on the proxy: a transaction starts.
2.  **The order is written**; each line's stock is reserved only if there is enough.
3.  **The payment record** is written last.
4.  **Any exception** (all of them unchecked) rolls everything back; success commits everything.

Check yourself: the old placeOrder() had @Transactional. Why did it not work?

Spring adds transactions with a proxy that wraps the bean. Calls from outside go through the proxy; a call from inside the same object (`this.placeOrder()`) goes straight to the method. No proxy, no transaction.

## What this station is not

- **No real payment.** A record, not a charge.
- **No cancellation.** Challenge 1.
- **No login.** The customer is named in the body.

## Key terms

| Term                | Simple meaning                                                                                   | Everyday example                                                              | In this project                            |
|---------------------|--------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|--------------------------------------------|
| **Transaction**     | Several database changes that are kept together or undone together.                              | A bank transfer: debit and credit, both or neither.                           | One checkout                               |
| **Proxy**           | An object Spring puts in front of yours, which starts and ends the transaction around each call. | A receptionist who opens a file before you see the clerk and closes it after. | `CheckoutService` as injected              |
| **Self-invocation** | A method calling another method of the same object directly, past the proxy.                     | The clerk walking to the next desk without the receptionist.                  | `this.placeOrder()`                        |
| **Rollback rule**   | Which exceptions undo the transaction.                                                           | "Any error undoes the transfer", or only some.                                | Unchecked: rolled back; checked: committed |
| **readOnly**        | A transaction that promises not to write.                                                        | A visitor's pass for the records room: look, do not touch.                    | `find()`                                   |
| **Reservation**     | Stock set aside for one order.                                                                   | Items put behind the counter with a name on them.                             | `reservations`                             |

# 2 · Build: Spec

## Business problem

**Kartwala** (a fictional marketplace) charged customers for orders whose stock was not fully reserved, because the checkout's transaction never started.

## Acceptance criteria

1.  **Given** 2 Assam tea and 5 Kashmiri chilli (all 5 left), **then** `201`, ₹1,343 total, a payment record, and stock 48 and 0.
2.  **Given** 2 tea and a sold-out tiffin box, **then** `409`, and no order, reservation or payment; tea stock still 50.
3.  **Given** an unknown product, or the same product twice, **then** `422`.
4.  **Given** no lines, quantity 0, 11 or 1.5, or no customer, **then** `400`.
5.  **Given** an unknown checkout id, **then** `404`.

## Requirements

- The order, its reservations and its payment record commit together or not at all.
- The transaction starts at the method the controller calls.
- Stock never goes below zero, also in the database.
- Reads that must not write run in read-only transactions.

## Learning objectives

- Explain how Spring's transaction proxy works, and why self-invocation bypasses it.
- Know which exceptions roll back by default, and how to change it.
- Use `readOnly` and know what it does on PostgreSQL.
- Order the steps of a business operation so the risky ones come first.

# 2 · Build: API contract

## Endpoints

| Method | Path              | Purpose                                                                            |
|--------|-------------------|------------------------------------------------------------------------------------|
| `POST` | `/checkouts`      | Check out: `customerId` and 1 to 20 lines of `productId` and `quantity` (1 to 10). |
| `GET`  | `/checkouts/{id}` | The checkout: total, payment record and lines.                                     |

## Status codes

| Status | When                                         |
|--------|----------------------------------------------|
| 201    | Checked out; `Location` points at it         |
| 200    | The checkout                                 |
| 400    | Malformed basket                             |
| 404    | No such checkout                             |
| 409    | Not enough stock for a line: nothing is kept |
| 422    | Unknown product, or a product listed twice   |

## Captured examples

Captured with curl from the running app on 16 Oct 2026, in this order, against one fresh database (tea 50, chilli 5, tiffin box 0). JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: 2 tea and 5 chilli

**Why:** everything reserved and recorded together: `201`.

Request

``` code
POST /checkouts HTTP/1.1
Content-Type: application/json

{
  "customerId": 7,
  "lines": [
    {
      "productId": 1,
      "quantity": 2
    },
    {
      "productId": 2,
      "quantity": 5
    }
  ]
}
```

Response

``` code
HTTP/1.1 201 
Location: /checkouts/1
Content-Type: application/json

{
  "id": 1,
  "customerId": 7,
  "totalPaise": 134300,
  "payment": {
    "status": "CAPTURED",
    "amountPaise": 134300
  },
  "lines": [
    {
      "productId": 1,
      "name": "Assam tea, 500 g",
      "quantity": 2,
      "unitPricePaise": 34900
    },
    {
      "productId": 2,
      "name": "Kashmiri chilli, 100 g",
      "quantity": 5,
      "unitPricePaise": 12900
    }
  ]
}
```

### Case 2: read it back

**Why:** a read-only transaction.

Request

``` code
GET /checkouts/1 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 268

{
  "id": 1,
  "customerId": 7,
  "totalPaise": 134300,
  "payment": {
    "status": "CAPTURED",
    "amountPaise": 134300
  },
  "lines": [
    {
      "productId": 1,
      "name": "Assam tea, 500 g",
      "quantity": 2,
      "unitPricePaise": 34900
    },
    {
      "productId": 2,
      "name": "Kashmiri chilli, 100 g",
      "quantity": 5,
      "unitPricePaise": 12900
    }
  ]
}
```

### Case 3: another shopper wants 1 chilli

**Why:** case 1 took the last 5: `409`.

Request

``` code
POST /checkouts HTTP/1.1
Content-Type: application/json

{
  "customerId": 8,
  "lines": [
    {
      "productId": 2,
      "quantity": 1
    }
  ]
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Not enough \"Kashmiri chilli, 100 g\" for 1.",
  "instance": "/checkouts",
  "status": 409,
  "title": "Not enough stock"
}
```

### Case 4: 2 tea and a sold-out tiffin box

**Why:** the tea was reserved, then the box failed, so the tea went back: `409`.

Request

``` code
POST /checkouts HTTP/1.1
Content-Type: application/json

{
  "customerId": 8,
  "lines": [
    {
      "productId": 1,
      "quantity": 2
    },
    {
      "productId": 3,
      "quantity": 1
    }
  ]
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Not enough \"Steel tiffin box\" for 1.",
  "instance": "/checkouts",
  "status": 409,
  "title": "Not enough stock"
}
```

### Case 5: product 99

**Why:** `422`.

Request

``` code
POST /checkouts HTTP/1.1
Content-Type: application/json

{
  "customerId": 8,
  "lines": [
    {
      "productId": 99,
      "quantity": 1
    }
  ]
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "No product 99.",
  "instance": "/checkouts",
  "status": 422,
  "title": "Unknown product"
}
```

### Case 6: quantity 0

**Why:** `400`.

Request

``` code
POST /checkouts HTTP/1.1
Content-Type: application/json

{
  "customerId": 8,
  "lines": [
    {
      "productId": 1,
      "quantity": 0
    }
  ]
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/checkouts",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 7: checkout 99

**Why:** `404`.

Request

``` code
GET /checkouts/99 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No checkout 99.",
  "instance": "/checkouts/99",
  "status": 404,
  "title": "Checkout not found"
}
```

## What the database holds afterwards

Read with psql after the requests above (`docs/captures/state.txt`): one order, tea at 48 (case 4's reservation was rolled back), chilli at 0.

``` code
 orders | reservations | payments | tea_stock | chilli_stock 
--------+--------------+----------+-----------+--------------
      1 |            2 |        1 |        48 |            0
(1 row)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                                     | What happens                             | Proved by                                     |
|------------------------------------------------------------------------------------------|------------------------------------------|-----------------------------------------------|
| A basket that fits                                                                       | Order, reservations, payment; stock down | `aCheckoutReservesStockAndRecordsThePayment`  |
| One line out of stock                                                                    | `409`; nothing kept                      | `outOfStockIs409AndNothingIsKept`             |
| Unknown or repeated product                                                              | `422`; nothing kept                      | `unknownOrRepeatedProductsAre422`             |
| Malformed baskets                                                                        | `400`; nothing kept                      | `malformedCheckoutsAre400`                    |
| Unknown checkout                                                                         | `404`                                    | `unknownCheckoutsAre404`                      |
| Negative stock, second payment, orphan payment, bad quantity or status, written directly | Refused by named constraints             | `namedConstraintsHoldWithoutJava`             |
| Checked vs unchecked exceptions; rollbackFor                                             | Checked commits by default               | `aCheckedExceptionCommitsUnlessToldOtherwise` |
| A write inside a readOnly transaction                                                    | Refused by PostgreSQL                    | `aReadOnlyTransactionRefusesWrites`           |

## The trap

Plausible but wrong

Calling a `@Transactional` method from the same class, so no transaction starts.

The old service is kept in the tests as `OldCheckoutService`, and the trap test registers it as a real Spring bean, so it is proxied exactly as in production (the test checks that it is). Called the way the controller called it, through `checkout()`, the out-of-stock exception leaves 1 order, 1 reservation, 1 payment record, and tea stock down by 2: a paid order with half its stock. Calling `placeOrder()` itself through the proxy rolls everything back, which proves the annotation was fine and the call was not. The fixed API rolls back the same basket whole.

While building, each part was undone once. Without `@Transactional` on `checkout`, 2 tests turned red; reserving without the `stock >= quantity` condition, 2 (the database's check refused it as a `500`). Adding a non-transactional method that calls `this.checkout()`, and pointing the controller at it, turned the same 2 red: the old bug, rebuilt in the new code.

``` code
package com.kartwala.checkout;

import org.junit.jupiter.api.Test;
import org.springframework.aop.support.AopUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Import;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: the old checkout as a real Spring bean, so it is proxied exactly as in
 * production. The same basket every time: 2 Assam tea (in stock) and 6 Kashmiri chilli (only 5 left).
 */
@Import(OldCheckoutService.class)
class SelfInvocationTrapTest extends ApiTest {

    @Autowired
    OldCheckoutService old;

    final List<CheckoutService.LineRequest> basket = List.of(new CheckoutService.LineRequest(1, 2), new CheckoutService.LineRequest(2, 6));

    @Test
    void throughSelfInvocationNothingIsRolledBack() {
        assertThat(AopUtils.isAopProxy(old)).isTrue();   // it IS proxied; the call inside it just does not go through the proxy
        assertThatThrownBy(() -> old.checkout(7, basket)).hasMessageContaining("out of stock");
        // 1 order, 1 reservation (the tea), 1 payment: a paid order with half its stock, tea stock down by 2.
        assertThat(state()).isEqualTo("1/1/1/48/5");
    }

    @Test
    void theSameMethodCalledThroughTheProxyRollsBackWhole() {
        assertThatThrownBy(() -> old.placeOrder(7, basket)).hasMessageContaining("out of stock");
        assertThat(state()).isEqualTo("0/0/0/50/5");
    }

    @Test
    void theFixedCheckoutRollsBackWhole() throws Exception {
        checkout("[{\"productId\":1,\"quantity\":2},{\"productId\":2,\"quantity\":6}]").andExpect(status().isConflict());
        assertThat(state()).isEqualTo("0/0/0/50/5");
    }
}
```

``` code
package com.kartwala.checkout;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * The checkout as it shipped, kept only in tests (registered as a bean by the trap test, so Spring proxies it as it
 * did in production). placeOrder is @Transactional. checkout, the method the controller called, is not, and it
 * calls placeOrder on "this": the proxy is never involved, so no transaction starts.
 */
class OldCheckoutService {

    private final JdbcClient jdbc;

    OldCheckoutService(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public long checkout(long customerId, List<CheckoutService.LineRequest> lines) {
        if (lines.isEmpty()) {
            throw new IllegalArgumentException("no lines");
        }
        return placeOrder(customerId, lines);   // self-invocation: @Transactional below does nothing here
    }

    @Transactional
    public long placeOrder(long customerId, List<CheckoutService.LineRequest> lines) {
        long orderId = jdbc.sql("INSERT INTO orders (customer_id, total_paise) VALUES (?, 100) RETURNING id").param(customerId).query(Long.class).single();
        jdbc.sql("INSERT INTO payments (order_id, amount_paise, status) VALUES (?, 100, 'CAPTURED')").param(orderId).update();   // paid first
        for (CheckoutService.LineRequest line : lines) {
            int reserved = jdbc.sql("UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?").params(line.quantity(), line.productId(), line.quantity()).update();
            if (reserved == 0) {
                throw new IllegalStateException("out of stock: product " + line.productId());
            }
            jdbc.sql("INSERT INTO reservations (order_id, product_id, quantity, unit_price_paise) VALUES (?, ?, ?, 100)").params(orderId, line.productId(), line.quantity()).update();
        }
        return orderId;
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
./mvnw test                 # all 11 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

See the transaction start and end. Run the app with transaction logging:

``` code
./mvnw spring-boot:run -Dspring-boot.run.arguments=--logging.level.org.springframework.jdbc.support.JdbcTransactionManager=DEBUG
```

Send case 4 from the API tab and look for "Creating new transaction", then "Initiating transaction rollback". The old code would print neither.

## Troubleshooting

| You see                                            | Cause                                                    | Fix                                                               |
|----------------------------------------------------|----------------------------------------------------------|-------------------------------------------------------------------|
| `@Transactional` seems to do nothing               | The method is called from the same class, or is private. | Call it from another bean; put the annotation on the entry point. |
| A failed operation's rows are still there          | A checked exception: Spring commits by default.          | Throw unchecked, or `rollbackFor = ThatException.class`.          |
| `cannot execute INSERT in a read-only transaction` | A write inside `readOnly = true`.                        | Move the write out, or drop `readOnly` for that method.           |
| `500` with `products_stock_not_negative`           | Stock reduced without checking it first.                 | `UPDATE ... WHERE stock >= ?` and check the row count.            |
| The payment is recorded for a failed order         | Payment written before the steps that can fail.          | Write it last, inside the same transaction.                       |

## Project layout

``` tree
stations/055-checkout-as-one-transaction/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/checkout/
│   ├── CheckoutController.java   ├── CheckoutService.java   └── CheckoutApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__products_orders_payments.sql, V2__demo_products.sql
├── src/test/java/com/kartwala/checkout/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database.

#### `src/main/java/com/kartwala/checkout/CheckoutController.java`

Does  
Validates the basket; calls the service through its proxy.

Why  
The transaction starts at the first call into the service.

Without it  
A non-transactional entry point.

#### `src/main/java/com/kartwala/checkout/CheckoutService.java`

Does  
Prices the lines, writes the order, reserves stock, records the payment last; reads back read-only.

Why  
`@Transactional` on the method callers use; only unchecked exceptions.

Without it  
Half-done checkouts.

- Each reservation is `UPDATE ... WHERE stock >= ?`: zero rows means not enough, safe under concurrency.
- The payment record comes last, after everything that can fail.
- `readOnly = true` makes PostgreSQL refuse writes in `find`.

#### `src/main/resources/db/migration/V1__products_orders_payments.sql`

Products, orders, reservations and payments, with named constraints.

#### `src/main/resources/db/migration/V2__demo_products.sql`

Tea (50), chilli (5) and a sold-out tiffin box.

#### `src/main/resources/application.yaml`

Problem details on; decimals refused for whole-number fields.

#### `src/main/java/com/kartwala/checkout/CheckoutApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                   | Result |
|---------------|-------------------------------------------------------|------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `CheckoutContractTest` (5)   | pass   |
| Every station | Reproduce the failure before the fix                  | `SelfInvocationTrapTest` (3) | pass   |
| Database      | Rollback and constraint tests against a real database | `CheckoutDatabaseTest` (3)   | pass   |

## Testing a proxy, for real

A transaction bug only shows with a real Spring proxy and a real database. So the old service and the rollback-rule examples are real beans (`@Import` in the test), the database is a real PostgreSQL, and every test checks the rows, not only the HTTP answer. No test runs inside a test transaction, which would hide exactly this bug.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.checkout.CheckoutContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.checkout.SelfInvocationTrapTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.checkout.CheckoutDatabaseTest
[INFO] Tests run: 11, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/kartwala/checkout/SelfInvocationTrapTest.java`

Written first: the old service through `checkout()` and through the proxy, and the fixed API.

#### `src/test/java/com/kartwala/checkout/CheckoutContractTest.java`

Checkout, read-back, and every refusal, with the rows checked each time.

#### `src/test/java/com/kartwala/checkout/CheckoutDatabaseTest.java`

Named constraints, rollback rules and read-only mode.

#### `src/test/java/com/kartwala/checkout/RollbackRules.java`

Test-only bean: one write under four transaction settings.

#### `src/test/java/com/kartwala/checkout/OldCheckoutService.java`

The old service, kept only in tests.

#### `src/test/java/com/kartwala/checkout/ApiTest.java`

Shared setup: empty orders and reset stock before each test; one string for the whole state.

#### `src/test/java/com/kartwala/checkout/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/kartwala/checkout/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=CancelChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 11 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 13 tests pass (11 station tests and 2 challenge tests). Without `rollbackFor` in the solution, challenge 2's test failed with one order and one reservation left behind.

Challenge 1 · Beginner-friendly · about 25 minutes

## Cancel a checkout

Add `POST /checkouts/{id}/cancellation`: order CANCELLED, stock back, payment record REFUNDED, in one transaction. Again: `409`; unknown: `404`.

**Done when:** the test in `CancelChallengeTest` passes.

Hints

- Lock the order row (`SELECT ... FOR UPDATE`) so two cancellations cannot both give stock back.
- One UPDATE can return the stock of every line: `UPDATE products ... FROM reservations`.

#### `challenge/CancelChallengeTest.java`

``` code
package com.kartwala.checkout;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /checkouts/{id}/cancellation, in one transaction: the order becomes CANCELLED, the reserved stock
 * goes back, the payment record becomes REFUNDED (simulated). The reservations stay as history. Again: 409. Unknown: 404.
 */
class CancelChallengeTest extends ApiTest {

    @Test
    void cancellingGivesTheStockBack() throws Exception {
        checkout("[{\"productId\":1,\"quantity\":2},{\"productId\":2,\"quantity\":5}]");
        assertThat(state()).isEqualTo("1/2/1/48/0");
        mvc.perform(post("/checkouts/1/cancellation")).andExpect(status().isOk()).andExpect(jsonPath("$.payment.status").value("REFUNDED"));
        assertThat(state()).isEqualTo("1/2/1/50/5");
        assertThat(jdbc.sql("SELECT status FROM orders WHERE id = 1").query(String.class).single()).isEqualTo("CANCELLED");
        mvc.perform(post("/checkouts/1/cancellation")).andExpect(status().isConflict());
        assertThat(state()).isEqualTo("1/2/1/50/5");   // not given back twice
        mvc.perform(post("/checkouts/99/cancellation")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 25 minutes

## A declined payment

The demo gateway declines totals above ₹2,000 by throwing a checked `PaymentDeclined` from the payment step. The checkout must roll back everything and answer `422`.

**Done when:** the test in `PaymentDeclinedChallengeTest` passes.

Hints

- A checked exception commits by default: `@Transactional(rollbackFor = PaymentDeclined.class)`.
- Catch it in the controller, after the proxy has rolled back.

#### `challenge/PaymentDeclinedChallengeTest.java`

``` code
package com.kartwala.checkout;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: the demo payment gateway declines totals above ₹2,000 by throwing a CHECKED PaymentDeclined from the
 * step that records the payment. The checkout must still roll back everything (stock, order) and answer 422.
 */
class PaymentDeclinedChallengeTest extends ApiTest {

    @Test
    void aDeclinedPaymentLeavesNothingBehind() throws Exception {
        checkout("[{\"productId\":1,\"quantity\":6}]").andExpect(status().isUnprocessableContent())   // ₹2,094
                .andExpect(jsonPath("$.title").value("Payment declined"));
        assertThat(state()).isEqualTo("0/0/0/50/5");
        checkout("[{\"productId\":1,\"quantity\":5}]").andExpect(status().isCreated());              // ₹1,745
        assertThat(state()).isEqualTo("1/1/1/45/5");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## When the payment is someone else's

Replace the payment record with a call to a real gateway that charges the card. The database transaction can roll back; the charge cannot. Order the steps, and decide what happens when the charge succeeds and the commit fails, or the charge times out.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test with the old service as a real proxied bean.
2.  Put `@Transactional` on the method the controller calls.
3.  Make every failure an unchecked exception (or name it in `rollbackFor`).
4.  Order the steps: the ones that can fail first, the payment last.

## Design alternatives and trade-offs

| Approach                                                        | What it costs                                                | Verdict              |
|-----------------------------------------------------------------|--------------------------------------------------------------|----------------------|
| `@Transactional` on the public entry method                     | Know where calls come from.                                  | Chosen               |
| Annotate an inner method and call it with `this.`               | Nothing happens.                                             | The trap             |
| Inject the bean into itself, or move the method to another bean | Works; the second is cleaner.                                | If the split is real |
| `TransactionTemplate` in the code                               | Explicit and visible; more code.                             | For fine control     |
| AspectJ weaving instead of proxies                              | Self-invocation works; build setup and surprise for readers. | Rarely worth it      |

## Database design

| Table          | Constraints                                                                                                       |
|----------------|-------------------------------------------------------------------------------------------------------------------|
| `products`     | `products_price_positive`, `products_stock_not_negative`                                                          |
| `orders`       | `orders_total_positive`, `orders_status_known`                                                                    |
| `reservations` | `reservations_order_fk`, `reservations_product_fk`, `reservations_one_per_product`, `reservations_quantity_range` |
| `payments`     | `payments_order_fk`, `payments_one_per_order`, `payments_amount_positive`, `payments_status_known`                |

``` code
-- Kartwala checkout: an order, its stock reservations and its payment record belong together.
CREATE TABLE products (
    id          BIGINT PRIMARY KEY,
    name        VARCHAR(120) NOT NULL,
    price_paise BIGINT       NOT NULL,
    stock       INT          NOT NULL,
    CONSTRAINT products_price_positive CHECK (price_paise > 0),
    CONSTRAINT products_stock_not_negative CHECK (stock >= 0)
);

CREATE TABLE orders (
    id          BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    customer_id BIGINT      NOT NULL,
    total_paise BIGINT      NOT NULL,
    status      VARCHAR(10) NOT NULL DEFAULT 'PLACED',
    CONSTRAINT orders_total_positive CHECK (total_paise > 0),
    CONSTRAINT orders_status_known CHECK (status IN ('PLACED', 'CANCELLED'))
);

CREATE TABLE reservations (
    id               BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    order_id         BIGINT NOT NULL,
    product_id       BIGINT NOT NULL,
    quantity         INT    NOT NULL,
    unit_price_paise BIGINT NOT NULL,
    CONSTRAINT reservations_order_fk FOREIGN KEY (order_id) REFERENCES orders (id),
    CONSTRAINT reservations_product_fk FOREIGN KEY (product_id) REFERENCES products (id),
    CONSTRAINT reservations_one_per_product UNIQUE (order_id, product_id),
    CONSTRAINT reservations_quantity_range CHECK (quantity BETWEEN 1 AND 10)
);

CREATE TABLE payments (
    id           BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    order_id     BIGINT      NOT NULL,
    amount_paise BIGINT      NOT NULL,
    status       VARCHAR(10) NOT NULL,
    CONSTRAINT payments_order_fk FOREIGN KEY (order_id) REFERENCES orders (id),
    CONSTRAINT payments_one_per_order UNIQUE (order_id),
    CONSTRAINT payments_amount_positive CHECK (amount_paise > 0),
    CONSTRAINT payments_status_known CHECK (status IN ('CAPTURED', 'REFUNDED'))
);
```

# 3 · Go deeper: Production

Real payments are outside the transaction  
A gateway charge is not undone by a rollback. Reserve and commit first, then charge; or record "payment pending", charge, and confirm; and refund when a later step fails. Station 085 covers idempotent payments.

Find the damage  
Orders with a payment but fewer reservations than lines are the old bug's leftovers. A query finds them; customer support refunds or ships.

Transactions are short  
Hold no transaction open across a slow network call; rows stay locked meanwhile.

Logging  
`JdbcTransactionManager` at DEBUG shows every begin, commit and rollback: the fastest way to see where a transaction really is.

# 3 · Go deeper: Interview

## Interview takeaways

Why does self-invocation skip @Transactional?

Spring applies @Transactional with a proxy around the bean. A call from inside the bean uses this, the real object, not the proxy, so no transaction logic runs.

Which exceptions roll back by default?

Unchecked ones (RuntimeException and Error). Checked exceptions commit, unless listed in rollbackFor.

What does readOnly = true do?

It tells the transaction manager and the database that no writes will happen. On PostgreSQL the transaction is read-only, so a write fails; ORMs can also skip dirty checking.

Does @Transactional work on private methods?

Not with Spring's proxies: they can only intercept calls they can override or forward, and private methods are neither.

How do you prove a transaction works?

With a real proxy and a real database: make a later step fail and check the rows the earlier steps wrote are gone.

## Self-check rubric

| Area        | Meets the bar                          | Above the bar                                               |
|-------------|----------------------------------------|-------------------------------------------------------------|
| Correctness | All 11 tests pass.                     | You rebuilt the self-invocation bug and watched it fail.    |
| Proxies     | You know where the transaction starts. | You can explain proxy, self-invocation and private methods. |
| Rollback    | Unchecked exceptions only.             | You know what `rollbackFor` is for.                         |
| Ordering    | Payment last.                          | A plan for a real gateway.                                  |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any `@Transactional`:

- Is the annotated method the one callers from other beans call?
- Can any exception thrown inside be checked, and is it in `rollbackFor`?
- What happens to the rows already written if the last step fails?
- Is anything inside the transaction that a rollback cannot undo (a call, an email, a file)?
