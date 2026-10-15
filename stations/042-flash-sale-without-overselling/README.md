# Station 042 · Flash sale without overselling

Foundations · 0–1 years · Core · E-commerce · Types: Database, Concurrency

Spring Boot 4.1.1 · Java 25 · PostgreSQL 17 conditional UPDATE and row locks · rows-affected checks · @Transactional · JdbcClient · virtual threads · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Sales, products and prices are demo data, not Kartwala's. A purchase is a reservation record; no payment is taken and nothing ships.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 10 tests.

# 1 · Understand

## The problem in real life

1.  **500 phones, 20,000 buyers**

    At noon, the sale opens. In one minute, 20,000 people tap "Buy".

2.  **517 sold**

    Each request read the stock, saw it was above zero, then took one. Hundreds read "3 left" at the same moment. 517 customers got "Order confirmed" for 500 phones. 17 apology emails, 17 refunds, and a trending complaint.

3.  **The fix**

    Ask the database to "take one if there is one" in a single statement, and look at whether it did.

Never decide in code what the database can decide and change in one step.

## What are we building?

`POST /flash-sales/{saleId}/purchases` reserves one phone for a customer, or says why not: sold out, not started, ended, or already bought.

## An everyday analogy

A token counter with one person behind it. Everyone queues and asks "one please"; the person hands out a token only if there is one. Nobody reads the count off a board and helps themselves.

## How it works in 4 steps

1.  **Ask the database to take one**, only if stock is above zero and the sale is open.
2.  **Look at the answer**: one row changed means a phone was taken; zero means none.
3.  **Write the purchase** in the same transaction; a second purchase by the same customer puts the phone back.
4.  **If none was taken**, say why.

Check yourself: the database has a CHECK that stock can never go below zero. Is that enough?

It stops negative stock, but the request that hits it gets an error (a 500), not a polite "sold out". And a purchase written before the update would still be there without a transaction. The conditional update answers cleanly; the CHECK is the safety net.

## What this station is not

- **No payment.** A purchase is a reservation.
- **No queue or waiting room.** Challenge 3 is about 20,000 buyers a second.
- **No login.** The customer id in the body stands in for the signed-in customer.

## Key terms

| Term                   | Simple meaning                                                                   | Everyday example                                                    | In this project           |
|------------------------|----------------------------------------------------------------------------------|---------------------------------------------------------------------|---------------------------|
| **Check-then-act**     | Read a value, decide in code, then change it: two steps with a gap between them. | Two cashiers both seeing "1 left" on the shelf and both selling it. | the trap                  |
| **Conditional UPDATE** | One statement that changes a row only if a condition still holds.                | "Take one, if there is one" said to the stockroom.                  | `WHERE stock_left > 0`    |
| **Rows affected**      | How many rows a statement changed; 0 means the condition was not met.            | The stockroom saying "none left".                                   | `taken == 0`              |
| **Row lock**           | While one transaction updates a row, others wanting to update it wait.           | One person at the counter at a time.                                | PostgreSQL, automatically |
| **Transaction**        | Changes that succeed or fail together.                                           | The phone leaves the shelf only if the bill is written.             | `@Transactional`          |
| **Oversell**           | Promising more than there is.                                                    | Selling 517 tickets for 500 seats.                                  | the scenario              |

# 2 · Build: Spec

## Business problem

**Kartwala** (a fictional shopping app) ran a flash sale of 500 phones; 20,000 buyers came in one minute, and the database sold 517.

## Acceptance criteria

1.  **Given** 500 buyers at once for 50 phones, **then** exactly 50 get `201`, 450 get `409`, and stock ends at 0.
2.  **Given** one customer tapping 20 times at once, **then** one purchase, and stock goes down by one.
3.  **Given** a sold-out, ended or not-yet-started sale, **then** `409` with that reason; an unknown sale, `404`.
4.  **Given** a customer who already bought, **then** `409` "Already bought", and the stock is unchanged.
5.  **Given** a bad customer id or an extra field such as `quantity`, **then** `400`.

## Requirements

- Taking stock is one conditional statement; its rows-affected count is always checked.
- Stock update and purchase row in one transaction.
- Constraints: stock never below 0 or above the total; one purchase per customer per sale.
- Money in integer paise; customer ids normalised with `Locale.ROOT`.

## Learning objectives

- Recognise check-then-act, and move the check into the database.
- Write a conditional `UPDATE … WHERE` and use rows affected.
- Keep related writes in one transaction.
- Prove the invariant with a real concurrent test.

# 2 · Build: API contract

## Endpoint

| Method | Path                              | Body                         |
|--------|-----------------------------------|------------------------------|
| `POST` | `/flash-sales/{saleId}/purchases` | `{"customerId": "C-000123"}` |

## Status codes

| Status | When                                                                        |
|--------|-----------------------------------------------------------------------------|
| 201    | A phone was reserved for this customer                                      |
| 400    | A bad customer id, a missing field, an unknown field, a non-numeric sale id |
| 404    | No such sale                                                                |
| 409    | Sold out, not started, ended, or already bought; the title says which       |

## Captured examples

Captured with curl from the running app on 15 Oct 2026, in this order, against one fresh database. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: a buyer

**Why:** one row taken, purchase written, one transaction.

Request

``` code
POST /flash-sales/1/purchases HTTP/1.1
Content-Type: application/json

{
  "customerId": "C-000123"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 71

{
  "purchaseId": 1,
  "saleId": 1,
  "customerId": "C-000123",
  "pricePaise": 999900
}
```

### Case 2: the same buyer again

**Why:** `purchases_one_per_customer`; the stock taken for this attempt is rolled back.

Request

``` code
POST /flash-sales/1/purchases HTTP/1.1
Content-Type: application/json

{
  "customerId": "C-000123"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Customer C-000123 already has one from this sale.",
  "instance": "/flash-sales/1/purchases",
  "status": 409,
  "title": "Already bought"
}
```

### Case 3: sale 2, stock 0

**Why:** 0 rows affected; the sale is open but empty.

Request

``` code
POST /flash-sales/2/purchases HTTP/1.1
Content-Type: application/json

{
  "customerId": "C-000123"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Sale 2 is sold out.",
  "instance": "/flash-sales/2/purchases",
  "status": 409,
  "title": "Sold out"
}
```

### Case 4: sale 3

**Why:** 0 rows; outside the window.

Request

``` code
POST /flash-sales/3/purchases HTTP/1.1
Content-Type: application/json

{
  "customerId": "C-000123"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Sale 3 has ended.",
  "instance": "/flash-sales/3/purchases",
  "status": 409,
  "title": "Sale ended"
}
```

### Case 5: sale 4

**Why:** 0 rows; not yet open.

Request

``` code
POST /flash-sales/4/purchases HTTP/1.1
Content-Type: application/json

{
  "customerId": "C-000123"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Sale 4 starts at 2030-01-01T06:30Z.",
  "instance": "/flash-sales/4/purchases",
  "status": 409,
  "title": "Not started"
}
```

### Case 6: sale 99

**Why:** `404`.

Request

``` code
POST /flash-sales/99/purchases HTTP/1.1
Content-Type: application/json

{
  "customerId": "C-000123"
}
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No flash sale 99.",
  "instance": "/flash-sales/99/purchases",
  "status": 404,
  "title": "Sale not found"
}
```

## A rush against the running app

From `docs/capture.sh`: sale 5 with 50 phones, 300 different buyers sent by `curl` with 50 requests in flight at a time, then the database queried (`docs/captures/rush.txt`).

``` code
300 buyers, 50 phones, 50 requests at a time: HTTP status counts
     50 201
    250 409

 stock_total | stock_left | purchases 
-------------+------------+-----------
          50 |          0 |        50
(1 row)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                                  | What happens                  | Proved by                                          |
|---------------------------------------------------------------------------------------|-------------------------------|----------------------------------------------------|
| 500 buyers, 50 phones, at once                                                        | 50 sold, 450 refused, stock 0 | `fiveHundredBuyersForFiftyPhones`                  |
| One customer, 20 taps at once                                                         | 1 purchase, stock −1          | `oneCustomerTappingTwentyTimesGetsOnePhone`        |
| A second purchase by the same customer                                                | Refused, phone put back       | `aSecondPurchaseByTheSameCustomerPutsThePhoneBack` |
| The last phone, then one more buyer                                                   | 0 rows: nothing taken         | `zeroRowsAffectedMeansNothingWasTaken`             |
| Negative or excess stock, bad window, unknown sale, duplicate buyer, written directly | Refused by named constraints  | `namedConstraintsHoldWithoutJava`                  |
| Sold out, ended, not started, unknown                                                 | `409` with the reason; `404`  | `eachRefusalSaysWhy`                               |
| Bad id, missing field, `quantity`, non-numeric sale                                   | `400`                         | `badRequestsAre400`                                |

## The trap

Plausible but wrong

Read stock, check, then update: concurrent buyers oversell.

The old code runs on the old tables, which have no stock constraint. 100 buyers start at the same instant for 5 phones; more than 5 get a phone, and the stock ends below zero by exactly the oversold amount. This happened in each of the 3 runs while building. The same 100 buyers against the conditional update get exactly 5. While building, each fix was undone once:

- Removing `stock_left > 0` gave 4 errors. The CHECK constraint refused the row, so buyers got 500s instead of "sold out".
- Removing `@Transactional` turned 2 tests red.
- Ignoring rows affected turned 4 red.
- Reading the stock and writing back the value read turned 2 red.

``` code
package com.kartwala.flashsale;

import org.junit.jupiter.api.Test;

import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;

/** The first test written for this station: 100 buyers at once for 5 phones, on the old code and on the new. */
class OversellTrapTest extends ApiTest {

    @Test
    void readCheckUpdateSellsMorePhonesThanThereAre() throws Exception {
        OldFlashSaleStore.createTables(jdbc, 5);
        AtomicInteger n = new AtomicInteger();
        together(100, () -> OldFlashSaleStore.buy(jdbc, customer(n.incrementAndGet())));
        long sold = jdbc.sql("SELECT count(*) FROM old_purchases").query(Long.class).single();
        int left = jdbc.sql("SELECT stock_left FROM old_flash_sales").query(Integer.class).single();
        assertThat(sold).isGreaterThan(5);         // more buyers than phones were told "yours"
        assertThat(left).isEqualTo(5 - sold);      // and the stock went below zero to match
    }

    @Test
    void oneConditionalUpdateSellsExactlyFive() throws Exception {
        openSale(5);
        AtomicInteger n = new AtomicInteger();
        together(100, () -> store.buy(10, customer(n.incrementAndGet())).isPresent());
        assertThat(purchases(10)).isEqualTo(5);
        assertThat(stockLeft(10)).isZero();
    }
}
```

``` code
package com.kartwala.flashsale;

import org.springframework.jdbc.core.simple.JdbcClient;

/**
 * The purchase code before the fix, kept only in tests, on the tables as they were: no constraint on the stock.
 * Read the stock, check it in Java, then update: between the read and the update, other buyers read the same stock.
 */
final class OldFlashSaleStore {

    private OldFlashSaleStore() {
    }

    static void createTables(JdbcClient jdbc, int stock) {
        jdbc.sql("DROP TABLE IF EXISTS old_purchases, old_flash_sales").update();
        jdbc.sql("CREATE TABLE old_flash_sales (id BIGINT PRIMARY KEY, stock_left INT NOT NULL)").update();   // no CHECK
        jdbc.sql("CREATE TABLE old_purchases (sale_id BIGINT NOT NULL, customer_id VARCHAR(10) NOT NULL)").update();
        jdbc.sql("INSERT INTO old_flash_sales VALUES (1, ?)").param(stock).update();
    }

    static boolean buy(JdbcClient jdbc, String customerId) {
        int stock = jdbc.sql("SELECT stock_left FROM old_flash_sales WHERE id = 1").query(Integer.class).single();
        if (stock <= 0) {
            return false;   // "sold out"
        }
        jdbc.sql("UPDATE old_flash_sales SET stock_left = stock_left - 1 WHERE id = 1").update();
        jdbc.sql("INSERT INTO old_purchases (sale_id, customer_id) VALUES (1, ?)").param(customerId).update();
        return true;
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
./mvnw test                 # all 10 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Run your own rush (macOS / Linux): 200 buyers, 40 at a time, for the 500 phones of sale 1, then count.

``` code
seq 1 200 | xargs -P 40 -I{} sh -c 'curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8080/flash-sales/1/purchases -H "Content-Type: application/json" -d "{\"customerId\":\"C-$(printf %06d {})\"}"' | sort | uniq -c
docker compose exec postgres psql -U kartwala -d kartwala -c "SELECT stock_left FROM flash_sales WHERE id = 1"
```

## Troubleshooting

| You see                                                      | Cause                                                       | Fix                                                        |
|--------------------------------------------------------------|-------------------------------------------------------------|------------------------------------------------------------|
| `violates check constraint "flash_sales_stock_not_negative"` | An update without `stock_left > 0` reached the CHECK.       | Put the condition in the UPDATE and look at rows affected. |
| More purchases than stock                                    | Stock checked in code before updating.                      | One conditional update; never read-then-write.             |
| Stock lower than purchases                                   | The update ran, the insert failed, and nothing rolled back. | Both in one `@Transactional` method.                       |
| `Could not find a valid Docker environment`                  | Docker is not running.                                      | Start Docker, then run the tests again.                    |

## Project layout

``` tree
stations/042-flash-sale-without-overselling/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/flashsale/
│   ├── PurchaseController.java   ├── FlashSaleStore.java   └── FlashSaleApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__flash_sales_and_purchases.sql, V2__demo_sales.sql
├── src/test/java/com/kartwala/flashsale/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/kartwala/flashsale/PurchaseController.java`

Does  
Validates the request, buys, and explains a refusal.

Why  
The reason is looked up only after nothing was taken, so the common path is one statement.

Without it  
Checking the stock first, which is the trap again.

#### `src/main/java/com/kartwala/flashsale/FlashSaleStore.java`

Does  
The purchase: a conditional update and an insert, in one transaction.

Why  
PostgreSQL locks the sale's row for the update, so buyers take turns on it and each sees the stock the last one left.

Without it  
The trap: read, decide in Java, write.

- `update()` returns rows affected: 1 means a phone was taken.
- A duplicate customer fails the insert; the transaction rolls the update back with it.

#### `src/main/resources/db/migration/V1__flash_sales_and_purchases.sql`

Does  
Sales and purchases, with named constraints.

Why  
Stock can never be negative or above the total, whatever the code does.

Without it  
A bug elsewhere sells a phone that does not exist.

#### `src/main/resources/db/migration/V2__demo_sales.sql`

Four demo sales: open, sold out, ended, not started.

#### `src/main/resources/application.yaml`

The database and strict JSON.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/kartwala/flashsale/FlashSaleApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                             | Test class                     | Result |
|---------------|---------------------------------------------------------|--------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                | `PurchaseContractTest` (3)     | pass   |
| Every station | Reproduce the failure before the fix                    | `OversellTrapTest` (2)         | pass   |
| Database      | Rollback and constraint tests against a real database   | `FlashSaleDatabaseTest` (3)    | pass   |
| Concurrency   | A real concurrency test that proves the invariant holds | `FlashSaleConcurrencyTest` (2) | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.flashsale.PurchaseContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.flashsale.FlashSaleConcurrencyTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.flashsale.FlashSaleDatabaseTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.flashsale.OversellTrapTest
[INFO] Tests run: 10, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/kartwala/flashsale/OversellTrapTest.java`

Written first: 100 buyers for 5 phones, old code and new.

#### `src/test/java/com/kartwala/flashsale/FlashSaleConcurrencyTest.java`

500 buyers and one impatient customer, through HTTP, released by one latch.

#### `src/test/java/com/kartwala/flashsale/FlashSaleDatabaseTest.java`

Named constraints, the rollback that puts a phone back, and zero rows affected.

#### `src/test/java/com/kartwala/flashsale/PurchaseContractTest.java`

A purchase, every refusal, and bad requests.

#### `src/test/java/com/kartwala/flashsale/OldFlashSaleStore.java`

The old code and tables, kept only in tests.

#### `src/test/java/com/kartwala/flashsale/ApiTest.java`

Shared setup: fresh sales, a test sale of any size, and the latch helper.

#### `src/test/java/com/kartwala/flashsale/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/kartwala/flashsale/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=SaleStatusChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 10 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 14 tests pass (10 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Sale status for the app

Add `GET /flash-sales/{id}` with product, stock left, stock total and a status: UPCOMING, OPEN, SOLD_OUT or ENDED, worked out by the database with its own clock.

**Done when:** both tests in `SaleStatusChallengeTest` pass.

Hints

- A SQL `CASE WHEN … THEN … END` picks the first condition that holds.
- Order matters: an ended sale with stock left is ENDED, not OPEN.

#### `challenge/SaleStatusChallengeTest.java`

``` code
package com.kartwala.flashsale;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: the app shows a countdown and a stock bar. Add GET /flash-sales/{id}: product, stockLeft, stockTotal and
 * a status of UPCOMING, OPEN, SOLD_OUT or ENDED, worked out by the database with its own clock.
 */
class SaleStatusChallengeTest extends ApiTest {

    @Test
    void eachSaleHasItsStatus() throws Exception {
        mvc.perform(get("/flash-sales/1")).andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("OPEN")).andExpect(jsonPath("$.stockLeft").value(500));
        mvc.perform(get("/flash-sales/2")).andExpect(jsonPath("$.status").value("SOLD_OUT"));
        mvc.perform(get("/flash-sales/3")).andExpect(jsonPath("$.status").value("ENDED"));
        mvc.perform(get("/flash-sales/4")).andExpect(jsonPath("$.status").value("UPCOMING"));
        mvc.perform(get("/flash-sales/99")).andExpect(status().isNotFound());
    }

    @Test
    void stockLeftFollowsPurchases() throws Exception {
        buy(1, "C-000001");
        mvc.perform(get("/flash-sales/1")).andExpect(jsonPath("$.stockLeft").value(499));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Cancel and put the phone back

Add `DELETE /flash-sales/{saleId}/purchases/{purchaseId}`: delete the purchase and add one to the stock, in one transaction. Ten cancels of the same purchase at once put back one phone.

**Done when:** both tests in `CancelPurchaseChallengeTest` pass.

Hints

- Rows affected again: only the cancel whose DELETE removed the row may add to the stock.
- `flash_sales_stock_within_total` would catch a double return, as an error.

#### `challenge/CancelPurchaseChallengeTest.java`

``` code
package com.kartwala.flashsale;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: DELETE /flash-sales/{saleId}/purchases/{purchaseId} cancels a purchase and puts the phone back, in one
 * transaction: 204, or 404 if there is no such purchase. Ten cancels of the same purchase at once put back one phone.
 */
class CancelPurchaseChallengeTest extends ApiTest {

    long purchaseId() {
        return jdbc.sql("SELECT id FROM purchases WHERE sale_id = 10").query(Long.class).single();
    }

    @Test
    void cancellingPutsThePhoneBack() throws Exception {
        openSale(5);
        buy(10, "C-000001");
        mvc.perform(delete("/flash-sales/10/purchases/{id}", purchaseId())).andExpect(status().isNoContent());
        assertThat(stockLeft(10)).isEqualTo(5);
        assertThat(purchases(10)).isZero();
        mvc.perform(delete("/flash-sales/10/purchases/{id}", 99999)).andExpect(status().isNotFound());
    }

    @Test
    void tenCancelsAtOnceReturnOnePhone() throws Exception {
        openSale(5);
        buy(10, "C-000001");
        long id = purchaseId();
        List<Integer> statuses = together(10, () -> mvc.perform(delete("/flash-sales/10/purchases/{id}", id)).andReturn().getResponse().getStatus());
        assertThat(statuses).filteredOn(s -> s == 204).hasSize(1);
        assertThat(stockLeft(10)).isEqualTo(5);
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## 20,000 buyers a second

All buyers update one row, so they take turns on its lock. At 20,000 a second that row is the limit. Compare splitting the stock across 10 rows (buckets), a counter in a cache such as Valkey `DECR` with the database written after, and a queue with a waiting room. What can each oversell, and what does each customer see?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old code oversells under real concurrency.
2.  Write the constraints: stock between 0 and total, one purchase per customer.
3.  Write the purchase as a conditional update plus an insert, in one transaction.
4.  Prove it: 500 buyers for 50 phones, through HTTP.

## Design alternatives and trade-offs

| Approach                                                    | What it costs                                          | Verdict            |
|-------------------------------------------------------------|--------------------------------------------------------|--------------------|
| Conditional `UPDATE … WHERE stock_left > 0` + rows affected | Buyers queue on one row's lock.                        | Chosen             |
| Read, check in Java, update                                 | Oversells under load.                                  | The trap           |
| `SELECT … FOR UPDATE`, then update                          | Correct, but two statements holding the lock longer.   | Works, slower      |
| `synchronized` in Java                                      | Holds on one server only; the second server oversells. | Not across servers |
| SERIALIZABLE isolation with retries                         | Correct, but many retries under a rush.                | Heavier            |

## Database design

| Table         | Constraints                                                                                                                  | Why                                                              |
|---------------|------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------|
| `flash_sales` | `flash_sales_stock_not_negative`, `flash_sales_stock_within_total`, `flash_sales_price_positive`, `flash_sales_window_order` | Stock stays real whatever any code does.                         |
| `purchases`   | `purchases_sale_fk`, `purchases_one_per_customer (sale_id, customer_id)`                                                     | One phone per customer, enforced where races cannot get past it. |

**Transaction boundary:** `FlashSaleStore.buy`, at PostgreSQL's default `READ COMMITTED`. A buyer waiting on the row lock re-checks `stock_left > 0` on the row as the previous buyer committed it, which is why no stronger isolation is needed.

``` code
CREATE TABLE flash_sales (
    id          BIGINT       PRIMARY KEY,
    product     VARCHAR(80)  NOT NULL,
    stock_total INT          NOT NULL,
    stock_left  INT          NOT NULL,
    price_paise BIGINT       NOT NULL,
    starts_at   TIMESTAMPTZ  NOT NULL,
    ends_at     TIMESTAMPTZ  NOT NULL,
    -- The last line of defence: whatever the code does, stock can never go below zero or above what there was.
    CONSTRAINT flash_sales_stock_not_negative CHECK (stock_left >= 0),
    CONSTRAINT flash_sales_stock_within_total CHECK (stock_left <= stock_total),
    CONSTRAINT flash_sales_price_positive     CHECK (price_paise > 0),
    CONSTRAINT flash_sales_window_order       CHECK (ends_at > starts_at)
);

CREATE TABLE purchases (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sale_id     BIGINT      NOT NULL,
    customer_id VARCHAR(10) NOT NULL,
    price_paise BIGINT      NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT purchases_sale_fk          FOREIGN KEY (sale_id) REFERENCES flash_sales (id),
    CONSTRAINT purchases_one_per_customer UNIQUE (sale_id, customer_id)   -- demo rule: one phone per customer
);
```

# 3 · Go deeper: Production

Hot row  
Every buyer updates the same row. It is correct, and each update is short, but one row has a ceiling; challenge 3 is about going past it.

Connection pool  
Buyers waiting on the lock hold a pooled connection. Size the pool, and time out waits, so a rush cannot starve the rest of the app.

Bots  
Flash sales attract scripts. One purchase per customer helps; rate limits and checks at login help more.

Payment  
A real sale reserves stock, then takes payment within minutes, and releases unpaid reservations; that is a later station.

# 3 · Go deeper: Interview

## Interview takeaways

What is a check-then-act race?

Reading a value, deciding in code, then writing: between the read and the write, others read the same value and decide the same way. Fix it by making the check part of the write.

How does UPDATE … WHERE stock \> 0 prevent overselling?

The update locks the row; concurrent updates wait, then re-evaluate the WHERE on the latest committed row. When stock reaches 0, the condition fails and 0 rows are affected.

Why check rows affected?

It is the database telling you whether the condition held. Ignoring it means acting as if you got the item when you did not.

Why does the purchase insert belong in the same transaction?

If the insert fails (a duplicate buyer), the stock update must be undone; otherwise a phone disappears from stock with no purchase.

Would synchronized in Java fix it?

Only on one server, and only for code that goes through that lock. Two app servers, or a script, would still race. The database is the shared point.

## Self-check rubric

| Area         | Meets the bar                            | Above the bar                                          |
|--------------|------------------------------------------|--------------------------------------------------------|
| Correctness  | All 10 tests pass.                       | You ran the flawed version and explained each failure. |
| Concurrency  | A conditional update with rows affected. | Why READ COMMITTED is enough here.                     |
| Transactions | Update and insert together.              | What happens to stock when the insert fails.           |
| Scale        | Knows the row lock serialises buyers.    | Can design past one hot row.                           |

# 3 · Go deeper: Review

## The pull request

A teammate wants a faster checkout. The update's result is not checked, because "the WHERE already guards it". `@Transactional` goes, to save a round trip. Every refusal says "Sold out". The single-buyer tests mostly pass. Read both files and list every problem before opening the findings.

#### `review/FlashSaleStore.java`

``` code
package com.kartwala.flashsale;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import java.time.OffsetDateTime;
import java.util.Optional;

@Repository
class FlashSaleStore {

    record Purchase(long purchaseId, long saleId, String customerId, long pricePaise) {
    }

    record Sale(long id, int stockLeft, OffsetDateTime startsAt, OffsetDateTime endsAt) {
    }

    private final JdbcClient jdbc;

    FlashSaleStore(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /**
     * PR: "Faster checkout. The UPDATE already has stock_left > 0, so we do not need to look at its result, and
     * dropping @Transactional saves a round trip per purchase."
     */
    Optional<Purchase> buy(long saleId, String customerId) {
        jdbc.sql("""
                        UPDATE flash_sales SET stock_left = stock_left - 1
                         WHERE id = :sale AND stock_left > 0 AND now() >= starts_at AND now() < ends_at""")
                .param("sale", saleId).update();
        return Optional.of(jdbc.sql("""
                        INSERT INTO purchases (sale_id, customer_id, price_paise)
                        SELECT id, :customer, price_paise FROM flash_sales WHERE id = :sale
                        RETURNING id AS purchase_id, sale_id, customer_id, price_paise""")
                .param("sale", saleId).param("customer", customerId).query(Purchase.class).single());
    }

    /** Only to explain a refusal: the answer can be a moment old, which is fine for a message. */
    Optional<Sale> sale(long saleId) {
        return jdbc.sql("SELECT id, stock_left, starts_at, ends_at FROM flash_sales WHERE id = :sale")
                .param("sale", saleId).query(Sale.class).optional();
    }
}
```

#### `review/PurchaseController.java`

``` code
package com.kartwala.flashsale;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.Locale;

@RestController
class PurchaseController {

    /** customerId stands in for the signed-in customer (demo); a real app takes it from the login. */
    record PurchaseRequest(@NotNull @Pattern(regexp = "(?i)C-\\d{6}", message = "must look like C-000123") String customerId) {
    }

    private final FlashSaleStore store;

    PurchaseController(FlashSaleStore store) {
        this.store = store;
    }

    /** Reserves one unit for the customer: a purchase record is created; no payment is taken in this station. */
    @PostMapping("/flash-sales/{saleId}/purchases")
    @ResponseStatus(HttpStatus.CREATED)
    FlashSaleStore.Purchase buy(@PathVariable long saleId, @Valid @RequestBody PurchaseRequest request) {
        String customer = request.customerId().toUpperCase(Locale.ROOT);
        try {
            return store.buy(saleId, customer).orElseThrow(() -> refusal(saleId));
        } catch (DuplicateKeyException e) {   // purchases_one_per_customer; the transaction put the phone back
            throw problem(HttpStatus.CONFLICT, "Already bought", "Customer " + customer + " already has one from this sale.");
        }
    }

    /** PR: "One message for every refusal: simpler for the app, and we skip a query." */
    private ErrorResponseException refusal(long saleId) {
        return problem(HttpStatus.CONFLICT, "Sold out", "Sale " + saleId + " is sold out.");
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
```

## Findings

1Rows affected are ignored

"The UPDATE already has stock_left \> 0" is true, but when it matches nothing the code still writes a purchase. Once the stock is gone, every buyer still gets a phone.

**Test evidence:** `fiveHundredBuyersForFiftyPhones`, `oneConditionalUpdateSellsExactlyFive` and `zeroRowsAffectedMeansNothingWasTaken` fail: more purchases than phones.

2@Transactional removed

The update commits on its own. When the insert then fails, because this customer already bought, the phone is gone from stock with no purchase behind it.

**Test evidence:** `aSecondPurchaseByTheSameCustomerPutsThePhoneBack` and `oneCustomerTappingTwentyTimesGetsOnePhone` fail: stock lower than purchases.

3Every refusal says "Sold out"

"Simpler for the app", but a customer told "sold out" before the sale starts does not come back at noon.

**Test evidence:** `eachRefusalSaysWhy` fails.

## Same tests, flawed version

From `docs/review-run.txt`: the two flawed files copied over the real ones, then the full suite run.

| Test class                 | Fixed version | Flawed version |
|----------------------------|---------------|----------------|
| `FlashSaleConcurrencyTest` | 2 / 2         | 0 / 2          |
| `FlashSaleDatabaseTest`    | 3 / 3         | 1 / 3          |
| `OversellTrapTest`         | 2 / 2         | 1 / 2          |
| `PurchaseContractTest`     | 3 / 3         | 2 / 3          |

The first flaw passes a one-buyer happy path, and the stock CHECK never fires: the update simply changes nothing, and the code does not look.
