# Station 039 · Human-friendly order numbers

Foundations · 0–1 years · Core · Food delivery · Types: Database, Concurrency

Spring Boot 4.1.1 · Java 25 · PostgreSQL 17 sequences · unique constraints · Luhn check digits · JdbcClient · virtual threads · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Orders and outlets are demo data, not Tiffino's. An order is a record in this app's database; no kitchen, delivery or payment is involved.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 17 tests.

# 1 · Understand

## The problem in real life

1.  **Numbers nobody can say**

    Support asks for the order number; the customer reads out `f47ac10b-58cc-4372-a567-0e02b2c3d479`, letter by letter.

2.  **A shorter number, kept in memory**

    The fix was a counter in the app: \#1, \#2, \#3. After a restart it said \#1 again, and the second server had its own \#1. Two orders shared a number, and support refunded the wrong one.

3.  **The fix**

    The database's sequence hands out numbers for every server, forever. A check digit catches a misheard digit before anyone looks the order up.

A counter that matters lives where every server and every restart can see it: the database.

## What are we building?

`POST /orders` gives every order a number like `TF-1000001-6`, and `GET /orders/by-number/{number}` finds it however the customer reads it out.

## An everyday analogy

The token machine at a bank branch. However many counters are open, tokens come from one machine, so no two people hold token 42. If the counters each had their own roll of tokens, two people would.

## How it works in 4 steps

1.  **Take the next value** from the database's sequence.
2.  **Add a check digit** computed from it.
3.  **Insert the order**; a unique constraint guards the number.
4.  **On lookup**, tidy the number, check the digit, then search.

Check yourself: order numbers jump from …0427 to …0429. Is an order missing?

Not necessarily. An order that failed after taking 0428 rolled back, and sequences never hand a value out again. Numbers are labels, not a count.

## What this station is not

- **No kitchen or delivery.** An order is a record.
- **Not secret.** A readable number is guessable; challenge 1 adds a random id for apps.
- **One region.** Numbers across several databases are challenge 3.

## Key terms

| Term               | Simple meaning                                                                       | Everyday example                                                       | In this project                        |
|--------------------|--------------------------------------------------------------------------------------|------------------------------------------------------------------------|----------------------------------------|
| **Sequence**       | A counter kept by the database, shared by every app server and kept across restarts. | The token machine at a bank: one machine, whichever counter you go to. | `order_number_seq`                     |
| **UUID**           | A 128-bit random id: unique without a central counter, but 36 characters long.       | A serial number nobody could read out on the phone.                    | `f47ac10b-58cc-…`                      |
| **Check digit**    | An extra digit computed from the others, so most typos are noticed at once.          | The last digit of a card number.                                       | the `-3` in `TF-1000427-3`             |
| **Luhn algorithm** | The check-digit method on payment cards (ISO/IEC 7812-1).                            | A quick sum the computer does on every number you type.                | `OrderNumbers.checkDigit`              |
| **Gap**            | A number that was taken and never used, because its order failed.                    | A torn-off token nobody called.                                        | `aRolledBackOrderLeavesAGapNotARepeat` |
| **Race**           | Two requests reading the same "last number" at the same moment.                      | Two clerks both writing receipt 42.                                    | the Review tab                         |

# 2 · Build: Spec

## Business problem

**Tiffino** (a fictional food delivery brand) had customers reading out UUIDs to support. A counter in memory then gave two orders the same number after a restart.

## Acceptance criteria

1.  **Given** a new order, **then** its number is `TF-`, seven digits, `-`, and a check digit, and no other order has it, across servers and restarts.
2.  **Given** 100 orders at the same instant, **then** 100 different, valid numbers and no failures.
3.  **Given** the number in lower case with spaces, **then** the same order.
4.  **Given** a number with one wrong digit, **then** `400`, "one digit is probably wrong", without a database lookup.
5.  **Given** a valid number nobody has, `404`; something not shaped like an order number, `400`.

## Requirements

- Numbers come from a database sequence; uniqueness is also a constraint.
- Gaps are allowed; repeats never.
- When the sequence runs out, inserts fail; it never wraps around.
- Numbers are normalised with `Locale.ROOT`; money in integer paise.

## Learning objectives

- Use a database sequence, and explain gaps.
- Compare UUIDs, sequences and readable codes.
- Prove uniqueness under concurrency with a parallel test.
- Compute and check a Luhn check digit, and know its blind spot.

# 2 · Build: API contract

## Endpoints

| Method | Path                         | Purpose                                                                         |
|--------|------------------------------|---------------------------------------------------------------------------------|
| `POST` | `/orders`                    | `{"outletId", "totalPaise"}`: places an order; `Location` points at its number. |
| `GET`  | `/orders/by-number/{number}` | Finds an order by its number, in any case, with or without spaces and dashes.   |

## Status codes

| Status | When                                                                      |
|--------|---------------------------------------------------------------------------|
| 201    | An order was placed                                                       |
| 200    | The order for that number                                                 |
| 400    | Not shaped like an order number, a wrong check digit, or a bad order body |
| 404    | A valid number that no order has                                          |

## Captured examples

Captured with curl from the running app on 15 Oct 2026, in this order, against one fresh database. Cases 3 to 5 use the number case 1 received. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: an order

**Why:** the sequence's first value and its Luhn digit.

Request

``` code
POST /orders HTTP/1.1
Content-Type: application/json

{
  "outletId": "TF-07",
  "totalPaise": 45000
}
```

Response

``` code
HTTP/1.1 201 
Location: /orders/by-number/TF-1000001-6
Content-Type: application/json

{
  "orderNumber": "TF-1000001-6",
  "outletId": "TF-07",
  "totalPaise": 45000
}
```

### Case 2: another outlet's order

**Why:** the same sequence for every outlet and server.

Request

``` code
POST /orders HTTP/1.1
Content-Type: application/json

{
  "outletId": "TF-02",
  "totalPaise": 18900
}
```

Response

``` code
HTTP/1.1 201 
Location: /orders/by-number/TF-1000002-4
Content-Type: application/json

{
  "orderNumber": "TF-1000002-4",
  "outletId": "TF-02",
  "totalPaise": 18900
}
```

### Case 3: looked up as written

**Why:** `200`.

Request

``` code
GET /orders/by-number/TF-1000001-6 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 68

{
  "orderNumber": "TF-1000001-6",
  "outletId": "TF-07",
  "totalPaise": 45000
}
```

### Case 4: lower case, spaces

**Why:** normalised to the stored form first.

Request

``` code
GET /orders/by-number/tf%201000001%206 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 68

{
  "orderNumber": "TF-1000001-6",
  "outletId": "TF-07",
  "totalPaise": 45000
}
```

### Case 5: one digit off

**Why:** the check digit no longer matches: `400`, no lookup.

Request

``` code
GET /orders/by-number/TF-1010001-6 HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "TF-1010001-6 is not a valid order number: one digit is probably wrong.",
  "instance": "/orders/by-number/TF-1010001-6",
  "status": 400,
  "title": "Check the order number"
}
```

### Case 6: TF-9999999-7

**Why:** a correct check digit, but no such order: `404`.

Request

``` code
GET /orders/by-number/TF-9999999-7 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No order TF-9999999-7.",
  "instance": "/orders/by-number/TF-9999999-7",
  "status": 404,
  "title": "Order not found"
}
```

### Case 7: 12345

**Why:** `400`.

Request

``` code
GET /orders/by-number/12345 HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Order numbers look like TF-1000427-3.",
  "instance": "/orders/by-number/12345",
  "status": 400,
  "title": "Not an order number"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                 | What happens                 | Proved by                                                 |
|------------------------------------------------------|------------------------------|-----------------------------------------------------------|
| 100 orders at the same instant                       | 100 different, valid numbers | `aHundredOrdersAtOnceGetAHundredDifferentNumbers`         |
| Two servers and a restart, one database              | 101 numbers, all different   | `theSequenceIsSharedAndSurvivesARestart`                  |
| A duplicate written straight to the table            | `orders_number_unique`       | `andIfARepeatEverReachedTheTableTheConstraintWouldStopIt` |
| An order that fails after taking a number            | A gap, never a repeat        | `aRolledBackOrderLeavesAGapNotARepeat`                    |
| The sequence's end                                   | No wrap-around               | `theSequenceRefusesToWrapAround`                          |
| Any single wrong digit                               | Caught by the check digit    | `everySingleWrongDigitIsCaught`                           |
| Two neighbouring digits swapped                      | Caught, except 09 ↔ 90       | `swappedNeighboursAreCaughtExceptZeroAndNine`             |
| Any case, spaces, no dashes                          | The same number              | `numbersAreReadInAnyCaseWithOrWithoutSeparators`          |
| A wrong digit; an unknown valid number; not a number | `400`; `404`; `400`          | `OrderContractTest`                                       |

## The trap

Plausible but wrong

An in-memory counter that repeats numbers after a restart or on two servers.

Two servers, each with its own counter, both issue `#1`. A restarted server issues `#1` again. Two `OrderNumbers` on one database, plus a third standing in for a restarted server, issue 101 different numbers. If a repeat ever reached the table, `orders_number_unique` would refuse it. The Review tab shows a subtler version of the same mistake, a counter read from the table, failing under concurrency.

``` code
package com.tiffino.orders;

import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The first test written for this station: the in-memory counter repeats, the database sequence does not. */
class InMemoryCounterTrapTest extends ApiTest {

    @Test
    void twoServersWithTheirOwnCountersHandOutTheSameNumbers() {
        OldOrderNumbers serverA = new OldOrderNumbers();
        OldOrderNumbers serverB = new OldOrderNumbers();
        assertThat(serverA.next()).isEqualTo("#1").isEqualTo(serverB.next());
    }

    @Test
    void aRestartStartsTheCounterAgain() {
        OldOrderNumbers beforeRestart = new OldOrderNumbers();
        beforeRestart.next();
        beforeRestart.next();
        OldOrderNumbers afterRestart = new OldOrderNumbers();
        assertThat(afterRestart.next()).isEqualTo("#1");   // the 1st order of the morning, again
    }

    @Test
    void theSequenceIsSharedAndSurvivesARestart() {
        // Two "servers" (two OrderNumbers on the same database), and a third standing in for one restarted.
        OrderNumbers serverA = new OrderNumbers(jdbc);
        OrderNumbers serverB = new OrderNumbers(jdbc);
        Set<String> issued = new HashSet<>();
        for (int i = 0; i < 50; i++) {
            issued.add(serverA.next());
            issued.add(serverB.next());
        }
        issued.add(new OrderNumbers(jdbc).next());
        assertThat(issued).hasSize(101);
    }

    @Test
    void andIfARepeatEverReachedTheTableTheConstraintWouldStopIt() {
        String number = store.place("TF-07", 45_000).orderNumber();
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO orders (order_number, outlet_id, total_paise) VALUES (?, 'TF-02', 100)").param(number).update())
                .hasMessageContaining("orders_number_unique");
    }
}
```

``` code
package com.tiffino.orders;

import java.util.concurrent.atomic.AtomicLong;

/** The order numbers before the fix, kept only in tests: a counter in each app's memory. */
final class OldOrderNumbers {

    private final AtomicLong counter = new AtomicLong();   // starts at 0 every time the app starts

    String next() {
        return "#" + counter.incrementAndGet();
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

Place an order, stop the app, start it again, and place another: the number carries on. Then watch the sequence directly:

``` code
curl -X POST http://localhost:8080/orders -H "Content-Type: application/json" -d '{"outletId":"TF-07","totalPaise":45000}'
docker compose exec postgres psql -U tiffino -d tiffino -c "SELECT last_value FROM order_number_seq"
```

## Troubleshooting

| You see                                                                 | Cause                                             | Fix                                                                                 |
|-------------------------------------------------------------------------|---------------------------------------------------|-------------------------------------------------------------------------------------|
| `nextval: reached maximum value of sequence "order_number_seq"`         | All seven-digit numbers are used.                 | A planned change: a new prefix or an eighth digit, in a new migration. Never cycle. |
| `duplicate key value violates unique constraint "orders_number_unique"` | Something other than the sequence chose a number. | Find the writer; numbers come only from `nextval`.                                  |
| `Could not find a valid Docker environment`                             | Docker is not running.                            | Start Docker, then run the tests again.                                             |

## Project layout

``` tree
stations/039-human-friendly-order-numbers/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/tiffino/orders/
│   ├── OrderController.java   ├── OrderStore.java   ├── OrderNumbers.java   └── OrdersApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__orders_and_order_numbers.sql
├── src/test/java/com/tiffino/orders/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/OrderNumbers.java  The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/tiffino/orders/OrderController.java`

Does  
Places orders and looks them up by number.

Why  
A wrong check digit is answered before the database is asked: it is a typo, not a missing order.

Without it  
Looking up typos: customers hear "no such order" instead of "check the number".

#### `src/main/java/com/tiffino/orders/OrderStore.java`

Does  
Inserts and finds orders with `JdbcClient`.

Why  
The number is taken and the order inserted in one transaction.

Without it  
A number shown to the customer for an order that was never saved.

#### `src/main/java/com/tiffino/orders/OrderNumbers.java`

Does  
Takes the next sequence value, adds the Luhn digit, normalises and checks numbers.

Why  
The database decides the value; Java only formats it.

Without it  
The trap: a counter in memory.

- `nextval` never returns a value twice, even to transactions running at the same moment.
- Luhn doubles every second digit from the right, then rounds the sum up to a multiple of 10.

#### `src/main/resources/db/migration/V1__orders_and_order_numbers.sql`

Does  
The sequence and the orders table.

Why  
`NO CYCLE`: running out is an error, not a silent repeat; the unique constraint backs up the sequence.

Without it  
Numbers repeating after 99,99,999, or after someone resets the sequence.

#### `src/main/resources/application.yaml`

The database and strict JSON.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/tiffino/orders/OrdersApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                             | Test class                       | Result |
|---------------|---------------------------------------------------------|----------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                | `OrderContractTest` (5)          | pass   |
| Every station | Reproduce the failure before the fix                    | `InMemoryCounterTrapTest` (4)    | pass   |
| Database      | Rollback and constraint tests against a real database   | `OrderDatabaseTest` (3)          | pass   |
| Concurrency   | A real concurrency test that proves the invariant holds | `OrderNumberConcurrencyTest` (1) | pass   |
| This station  | What the check digit catches                            | `CheckDigitTest` (4)             | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.orders.OrderDatabaseTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.orders.InMemoryCounterTrapTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.orders.OrderContractTest
[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.orders.OrderNumberConcurrencyTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.orders.CheckDigitTest
[INFO] Tests run: 17, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tiffino/orders/InMemoryCounterTrapTest.java`

Written first: the old counter repeats; the sequence does not.

#### `src/test/java/com/tiffino/orders/OrderNumberConcurrencyTest.java`

100 orders on virtual threads, released together by a latch.

#### `src/test/java/com/tiffino/orders/OrderDatabaseTest.java`

Named constraints, a gap after a rollback, and no wrap-around.

#### `src/test/java/com/tiffino/orders/CheckDigitTest.java`

The standard Luhn example, every single-digit typo, every neighbour swap.

#### `src/test/java/com/tiffino/orders/OrderContractTest.java`

Placing and finding orders through HTTP, and every refusal.

#### `src/test/java/com/tiffino/orders/OldOrderNumbers.java`

The old counter, kept only in tests.

#### `src/test/java/com/tiffino/orders/ApiTest.java`

Shared setup: an empty orders table before each test.

#### `src/test/java/com/tiffino/orders/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tiffino/orders/`.
2.  Run it: `./mvnw test -Dtest=PublicIdChallengeTest` (Docker must be running). Challenge 2 does not compile until `DailyTokens` exists.
3.  Add a migration and change the code until it passes, then run `./mvnw test` to check the other 17 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in (three Java files and two migrations), all 22 tests pass (17 station tests and 5 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## A random id for apps

Readable numbers are guessable: the next order is one more. Give every order a random UUID too, generated by the database in a new migration; return it as `orderId` and add `GET /orders/{orderId}`.

**Done when:** both tests in `PublicIdChallengeTest` pass.

Hints

- `gen_random_uuid()` is built into PostgreSQL 13 and later.
- A `UUID` path variable makes Spring answer `400` for anything that is not one.

#### `challenge/PublicIdChallengeTest.java`

``` code
package com.tiffino.orders;

import org.junit.jupiter.api.Test;

import java.util.UUID;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: the readable number is for people, and it is guessable (the next order is one more). Give every order
 * a random UUID as well (a new migration, generated by the database), return it as "orderId", and add
 * GET /orders/{orderId} for apps and links.
 */
class PublicIdChallengeTest extends ApiTest {

    @Test
    void everyOrderHasARandomIdThatFindsIt() throws Exception {
        String body = place("""
                {"outletId":"TF-07","totalPaise":45000}""").andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        String id = body.replaceAll(".*\"orderId\":\"([^\"]+)\".*", "$1");
        UUID.fromString(id);   // throws if it is not a UUID
        mvc.perform(get("/orders/{id}", id)).andExpect(status().isOk()).andExpect(jsonPath("$.totalPaise").value(45000));
    }

    @Test
    void anUnknownIdIs404AndAMalformedOne400() throws Exception {
        mvc.perform(get("/orders/{id}", UUID.randomUUID())).andExpect(status().isNotFound());
        mvc.perform(get("/orders/{id}", "1004273")).andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Kitchen tokens that start again each day

The kitchen screen calls out 1, 2, 3…, per outlet, from 1 each day. Keep a counter row per outlet and day, and take the next token with one atomic statement, so 50 parallel orders get 1 to 50.

**Done when:** all three tests in `DailyTokenChallengeTest` pass.

Hints

- `INSERT … ON CONFLICT (outlet_id, day) DO UPDATE SET last_token = daily_tokens.last_token + 1 RETURNING last_token`.
- Reading the last token and writing +1 in two statements is the Review tab's mistake again.

#### `challenge/DailyTokenChallengeTest.java`

``` code
package com.tiffino.orders;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 2: the kitchen screen calls out short tokens, 1, 2, 3…, starting again each day for each outlet. Keep one
 * counter row per outlet and day, and take the next value with a single atomic statement
 * (INSERT … ON CONFLICT … DO UPDATE … RETURNING), so parallel orders never share a token.
 */
class DailyTokenChallengeTest extends ApiTest {

    @Autowired
    DailyTokens tokens;

    @Test
    void fiftyOrdersAtOnceAtOneOutletGetTokensOneToFifty() throws Exception {
        LocalDate day = LocalDate.of(2026, 10, 15);
        CountDownLatch start = new CountDownLatch(1);
        List<Future<Integer>> results = new ArrayList<>();
        try (ExecutorService threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 50; i++) {
                results.add(threads.submit(() -> {
                    start.await();
                    return tokens.next("TF-11", day);
                }));
            }
            start.countDown();
        }
        List<Integer> issued = new ArrayList<>();
        for (Future<Integer> f : results) {
            issued.add(f.get());
        }
        assertThat(issued).containsExactlyInAnyOrderElementsOf(java.util.stream.IntStream.rangeClosed(1, 50).boxed().toList());
    }

    @Test
    void eachOutletAndEachDayStartsAtOne() {
        LocalDate day = LocalDate.of(2026, 10, 16);
        assertThat(tokens.next("TF-12", day)).isEqualTo(1);
        assertThat(tokens.next("TF-12", day)).isEqualTo(2);
        assertThat(tokens.next("TF-13", day)).isEqualTo(1);
        assertThat(tokens.next("TF-12", day.plusDays(1))).isEqualTo(1);
    }

    @Test
    void anOrderShowsItsToken() throws Exception {
        place("""
                {"outletId":"TF-14","totalPaise":45000}""").andExpect(jsonPath("$.token").value(1));
        place("""
                {"outletId":"TF-14","totalPaise":45000}""").andExpect(jsonPath("$.token").value(2));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Numbers across regions

Tiffino opens in Dubai with its own database. Orders from both must never share a number, and support should tell the region from the number. Compare a region prefix with separate sequences, sequences with different ranges or increments, and a central number service. What happens when one region's database is down?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: two counters, a restart.
2.  Create the sequence and the table with a unique, formatted number.
3.  Format numbers in Java with a check digit; check digits on lookup before the database.
4.  Prove it under load: 100 orders at once.

## Design alternatives and trade-offs

| Approach                         | What it costs                                                                 | Verdict              |
|----------------------------------|-------------------------------------------------------------------------------|----------------------|
| Database sequence + check digit  | Gaps; one database decides.                                                   | Chosen               |
| A counter in memory              | Repeats after a restart and on every extra server.                            | The trap             |
| `max(number) + 1` from the table | Two requests read the same max; under load, duplicates or unique errors.      | The review           |
| UUID only                        | Unique anywhere without coordination, but unreadable on the phone.            | For apps, not people |
| Random short codes ("7KQ2-9XM")  | Unguessable and readable; needs a unique constraint and a retry on collision. | Station 040          |
| A per-day counter table          | Short daily numbers; one row lock per outlet per day.                         | Challenge 2          |

## Database design

| Object             | Definition                                                                                       | Why                                                                      |
|--------------------|--------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| `order_number_seq` | 1000001 to 9999999, `NO CYCLE`                                                                   | Seven digits, read out easily; running out is loud.                      |
| `orders`           | Identity PK (internal). `orders_number_unique`, `orders_number_format`, `orders_total_positive`. | The sequence prevents repeats; the constraint proves it to every writer. |

**Why gaps are fine:** `nextval` is not rolled back with the transaction, so a failed order uses up its number. That is what lets thousands of transactions take numbers at once without waiting for each other. A gap-free count needs a lock that every order waits for.

``` code
-- Order numbers come from a database sequence: one counter for every app instance, and it survives restarts.
-- nextval() never hands the same value out twice, even to transactions running at the same moment. Values used by a
-- transaction that rolls back are not returned, so numbers can have gaps; they are labels, not a count of orders.
-- 7 digits: 1000001 to 9999999 (about 90 lakh orders). NO CYCLE: when it runs out, inserts fail loudly instead of
-- repeating old numbers.
CREATE SEQUENCE order_number_seq START WITH 1000001 MINVALUE 1000001 MAXVALUE 9999999 NO CYCLE;

CREATE TABLE orders (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,   -- internal key, never shown to customers
    order_number VARCHAR(12) NOT NULL,
    outlet_id    VARCHAR(5)  NOT NULL,
    total_paise  BIGINT      NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT orders_number_unique  UNIQUE (order_number),
    CONSTRAINT orders_number_format  CHECK (order_number ~ '^TF-[0-9]{7}-[0-9]$'),
    CONSTRAINT orders_total_positive CHECK (total_paise > 0)
);
```

# 3 · Go deeper: Production

Capacity  
Seven digits give about 90 lakh orders. Watch `last_value` against the maximum, and plan the next format long before.

Restores  
After restoring a backup, check the sequence is ahead of the highest number in the table; `setval` fixes it.

Guessability  
Readable numbers are sequential. Never let a number alone reveal an order to someone who is not its customer; ask for the phone too, or use a random id (challenge 1).

Check digits  
Luhn misses 09 ↔ 90 swaps. The Damm and Verhoeff algorithms catch every single-digit error and every adjacent swap.

# 3 · Go deeper: Interview

## Interview takeaways

UUID, sequence or readable code?

UUIDs need no coordination and are unguessable but unreadable. Sequences are short and ordered but need one source and are guessable. Readable random codes sit between, at the cost of collision handling. Systems often use two: an internal key and a customer-facing number.

Why do sequence numbers have gaps?

nextval is not transactional: a value taken by a transaction that rolls back is never reused. That avoids making every insert wait for every other.

Why is SELECT max(id) + 1 wrong?

Two transactions read the same max and insert the same number. With a unique constraint one fails; without it, both succeed and the data is wrong.

What does a check digit protect against?

Typos: the Luhn digit catches every single wrong digit and most swaps of neighbours, so the system can say 'check the number' instead of 'not found'.

How do you test uniqueness under concurrency?

Start many threads, hold them at a latch, release them together, and assert the invariant: all values distinct, no failures, row count as expected.

## Self-check rubric

| Area        | Meets the bar                       | Above the bar                                             |
|-------------|-------------------------------------|-----------------------------------------------------------|
| Correctness | All 17 tests pass.                  | You ran the flawed version and read why each test failed. |
| Databases   | A sequence and a unique constraint. | Why gaps are the price of no waiting.                     |
| Concurrency | A latch-started parallel test.      | Why max()+1 passes every sequential test.                 |
| Design      | Readable number with a check digit. | When to add a random id or a regional prefix.             |

# 3 · Go deeper: Review

## The pull request

A teammate wants "cleaner" numbers. The sequence is gone and each number follows on from the last order, so there are no gaps and support can count orders. The check digit is simpler, and lookups take the number exactly as stored. Every test that places one order at a time still passes. Read the file and list every problem before opening the findings.

#### `review/OrderNumbers.java`

``` code
package com.tiffino.orders;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import java.util.Optional;

/**
 * PR: "Drop the sequence: numbers follow on from the last order, so there are no gaps and support can count orders
 * from them. Simpler check digit. Lookups take the number exactly as stored."
 */
@Component
class OrderNumbers {

    private final JdbcClient jdbc;

    OrderNumbers(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    String next() {
        long value = jdbc.sql("SELECT coalesce(max(substring(order_number from 4 for 7)::bigint), 1000000) + 1 FROM orders")
                .query(Long.class).single();
        String digits = Long.toString(value);
        return "TF-" + digits + "-" + checkDigit(digits);
    }

    /** The sum of the digits, last digit. */
    static int checkDigit(String digits) {
        int sum = 0;
        for (int i = 0; i < digits.length(); i++) {
            sum += digits.charAt(i) - '0';
        }
        return sum % 10;
    }

    static Optional<String> normalise(String raw) {
        String compact = raw.replaceAll("[\\s-]", "");
        if (!compact.matches("TF\\d{8}")) {
            return Optional.empty();
        }
        return Optional.of("TF-" + compact.substring(2, 9) + "-" + compact.charAt(9));
    }

    static boolean checkDigitMatches(String number) {
        return checkDigit(number.substring(3, 10)) == number.charAt(11) - '0';
    }
}
```

## Findings

1The number is read from the table: max() + 1

"No gaps, and support can count orders" sounds tidy. But 100 requests read the same max at the same moment and all try the same number; the unique constraint refuses all but one. Sequential tests cannot see it.

**Test evidence:** `aHundredOrdersAtOnceGetAHundredDifferentNumbers`: failures under load. `theSequenceIsSharedAndSurvivesARestart` and `aRolledBackOrderLeavesAGapNotARepeat` fail too, because nothing is taken from the sequence.

2The check digit is the sum of the digits

A digit sum notices one wrong digit, but swapped digits have the same sum, so "1004273" and "1002473" share a check digit. Swaps are the most common mistake when reading numbers aloud.

**Test evidence:** `swappedNeighboursAreCaughtExceptZeroAndNine` and `theStandardLuhnExample` fail. `everySingleWrongDigitIsCaught` still passes, which is why the change looked safe.

3Lookups no longer ignore letter case

"Take the number exactly as stored" breaks every customer who types tf instead of TF: the number is refused as not an order number.

**Test evidence:** `numbersAreReadInAnyCaseWithOrWithoutSeparators` and `anOrderGetsAReadableNumberAndALocation` fail.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class                   | Fixed version | Flawed version |
|------------------------------|---------------|----------------|
| `CheckDigitTest`             | 4 / 4         | 1 / 4          |
| `InMemoryCounterTrapTest`    | 4 / 4         | 3 / 4          |
| `OrderContractTest`          | 5 / 5         | 4 / 5          |
| `OrderDatabaseTest`          | 3 / 3         | 2 / 3          |
| `OrderNumberConcurrencyTest` | 1 / 1         | 0 / 1          |

The worst flaw, max() + 1, passes every test that places one order at a time. Only the parallel test and the sequence tests catch it.
