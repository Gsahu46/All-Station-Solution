# Station 082 · Movie seat holds

Working Systems · 0–2 years · Core · Events · Types: Database, Concurrency

Spring Boot 4.1.1 · Java 25 · SELECT ... FOR UPDATE, lock_timeout, SKIP LOCKED · JdbcClient · TransactionTemplate · PostgreSQL 17 · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The show, seats and customers are demo data, not SeatSure's. Payments are simulated: a charge records a reference after a short wait, a refund records that it happened; nothing is charged.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 13 tests.

# 1 · Understand

## The problem in real life

1.  **F12, twice**

    Two people paid for seat F12 at the same show. Both saw it free, both bought it.

2.  **A fix that froze the box office**

    The first fix locked the seat, then called the payment provider while still holding the lock, and waited for locks forever. One evening the provider took 30 seconds per payment: every customer for that seat, and the servers, waited with it.

3.  **The fix**

    Lock only for the milliseconds it takes to mark the seat held, never wait longer than two seconds, and pay with no lock at all. Booking is one short update afterwards.

Hold a lock for as little as possible, never across a call to someone else, and never wait for one forever.

## What are we building?

Hold named seats (or any free ones) for 10 minutes, then confirm: pay, then book.

## An everyday analogy

At a ticket window, the clerk puts your tickets in an envelope with your name and a time on it. You go to the bank machine with nothing locked. When you come back, the envelope is either still yours, or it expired and went back on sale.

## How it works in 4 steps

1.  **Hold**: lock the seat rows, check they are free, mark them held for 10 minutes, unlock. Milliseconds.
2.  **Busy?** If someone else has them locked for more than 2 seconds, answer "try again" instead of waiting.
3.  **Pay**: the provider is called with no lock held.
4.  **Book**: one update turns this hold's seats into bookings, if they are still this hold's.

Check yourself: Meera's payment takes 20 seconds. Can Arjun hold F13, next to her F12, meanwhile?

Yes, at once. Nothing is locked while Meera pays, so F12 answers "taken" immediately and F13 is simply free: `theApiPaysWithoutHoldingAnyLock`.

## What this station is not

- **No real payments.** A simulated provider waits, then records a reference.
- **No seat map.** Seats are read in the captures with `psql`.
- **No sign-in.** The customer is a name in the body.

## Key terms

| Term                           | Simple meaning                                                                     | Everyday example                                            | In this project                                  |
|--------------------------------|------------------------------------------------------------------------------------|-------------------------------------------------------------|--------------------------------------------------|
| **Hold**                       | A seat kept for one customer for 10 minutes while they pay.                        | A shop assistant putting a shirt aside.                     | `holds`                                          |
| **Row lock**                   | While one transaction works on a row, others wanting it wait.                      | One hand on the shirt at a time.                            | `SELECT ... FOR UPDATE`                          |
| **Lock timeout**               | The longest a request waits for a lock before giving up.                           | Waiting two minutes at the counter, then coming back later. | `lock_timeout`, 2 s                              |
| **SKIP LOCKED**                | Take rows nobody is locking right now, instead of waiting.                         | Picking any free till instead of the busy one.              | "any two seats"                                  |
| **Remote call**                | A request to another system, here the payment provider: slow, sometimes very slow. | Phoning the bank.                                           | `Payments.charge`                                |
| **Pessimistic and optimistic** | Lock first, then decide; or decide, then check nobody changed it.                  | Reserving a table, or walking in and seeing.                | this station locks; station 080 checks a version |

# 2 · Build: Spec

## Business problem

**SeatSure** (a fictional cinema booking app): two people paid for seat F12 in the same show.

## Acceptance criteria

Demo show: rows E, F and G, seats 10 to 14; row F ₹350, the others ₹250. Demo rules: holds last 10 minutes, at most 6 seats, nobody waits more than 2 seconds for a lock.

1.  **Given** free seats, **then** a hold for all of them, or none (`201`).
2.  **Given** a seat someone holds or booked, **then** `409` naming it.
3.  **Given** a seat someone else is locking for more than 2 seconds, **then** `503` with `Retry-After`.
4.  **Given** ten people holding F12 at once, **then** one hold.
5.  **Given** a confirm, **then** payment with no lock held, then the seats booked; a second confirm answers the same.
6.  **Given** a hold whose seats someone took after it ran out, **then** the payment is refunded and the confirm is `409`.

## Requirements

- No transaction holds a lock while calling another system.
- Every lock wait has a limit.
- The database refuses a seat that is both booked and held.

## Learning objectives

- Use `SELECT ... FOR UPDATE` for all-or-nothing holds.
- Set a lock timeout per transaction and turn it into a useful answer.
- Use `SKIP LOCKED` for "any free one" and for work queues.
- Keep remote calls out of transactions, and handle what changes while they run.

# 2 · Build: API contract

## Endpoints

| Method | Path                  | Purpose                                                                          |
|--------|-----------------------|----------------------------------------------------------------------------------|
| `POST` | `/shows/{id}/holds`   | `{customer, seats: ["F12", ...]}` or `{customer, count}`: a hold for 10 minutes. |
| `POST` | `/holds/{id}/confirm` | Pay (simulated), then book the hold's seats.                                     |

## Status codes

| Status    | When                                                                                    |
|-----------|-----------------------------------------------------------------------------------------|
| 200 / 201 | Confirmed (also for a second confirm) / held                                            |
| 400       | Both or neither of seats and count; a seat name of the wrong shape; more than 6         |
| 404       | No such show, seat or hold                                                              |
| 409       | A seat taken; a hold expired; the seats taken after the hold ran out (payment refunded) |
| 503       | Someone else is locking the seat for longer than 2 seconds: `Retry-After: 1`            |

## Captured examples

Captured with curl from the running app on 22 Oct 2026, in this order. JSON bodies are indented for reading; `Date`, connection and standard security headers are left out.

### Case 1: Meera holds F12 and F13

**Why:** both free: one hold, ₹700, for 10 minutes.

Request

``` code
POST /shows/1/holds HTTP/1.1
Content-Type: application/json

{
  "customer": "meera",
  "seats": [
    "F12",
    "F13"
  ]
}
```

Response

``` code
HTTP/1.1 201 
Location: /holds/c4c33602-dcd1-41d3-a809-98f4c5d72439
Content-Type: application/json

{
  "id": "c4c33602-dcd1-41d3-a809-98f4c5d72439",
  "showId": 1,
  "customer": "meera",
  "seatNos": [
    "F12",
    "F13"
  ],
  "totalPaise": 70000,
  "expiresAt": "2026-10-22T11:27:50.222575Z",
  "status": "held",
  "paymentRef": null
}
```

### Case 2: Arjun asks for F11 and F12

**Why:** F12 is held: `409`, and F11 is not held either (all or none).

Request

``` code
POST /shows/1/holds HTTP/1.1
Content-Type: application/json

{
  "customer": "arjun",
  "seats": [
    "F11",
    "F12"
  ]
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Taken: F12",
  "instance": "/shows/1/holds",
  "status": 409,
  "title": "Conflict"
}
```

### Case 3: Arjun asks for any two

**Why:** the first two free seats.

Request

``` code
POST /shows/1/holds HTTP/1.1
Content-Type: application/json

{
  "customer": "arjun",
  "count": 2
}
```

Response

``` code
HTTP/1.1 201 
Location: /holds/9e0d1d6f-572f-4135-b67d-0f3288e1ddc5
Content-Type: application/json

{
  "id": "9e0d1d6f-572f-4135-b67d-0f3288e1ddc5",
  "showId": 1,
  "customer": "arjun",
  "seatNos": [
    "E10",
    "E11"
  ],
  "totalPaise": 50000,
  "expiresAt": "2026-10-22T11:27:50.311783Z",
  "status": "held",
  "paymentRef": null
}
```

### Case 4: Meera confirms

**Why:** paid with no lock held, then booked.

Request

``` code
POST /holds/c4c33602-dcd1-41d3-a809-98f4c5d72439/confirm HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 209

{
  "id": "c4c33602-dcd1-41d3-a809-98f4c5d72439",
  "showId": 1,
  "customer": "meera",
  "seatNos": [
    "F12",
    "F13"
  ],
  "totalPaise": 70000,
  "expiresAt": "2026-10-22T11:27:50.222575Z",
  "status": "confirmed",
  "paymentRef": "pay_c4c33602"
}
```

### Case 5: Meera's app retries

**Why:** the same answer, no second charge.

Request

``` code
POST /holds/c4c33602-dcd1-41d3-a809-98f4c5d72439/confirm HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 209

{
  "id": "c4c33602-dcd1-41d3-a809-98f4c5d72439",
  "showId": 1,
  "customer": "meera",
  "seatNos": [
    "F12",
    "F13"
  ],
  "totalPaise": 70000,
  "expiresAt": "2026-10-22T11:27:50.222575Z",
  "status": "confirmed",
  "paymentRef": "pay_c4c33602"
}
```

### Case 6: G12, locked for 4 seconds by another transaction

**Why:** `503` after the 2-second limit, with `Retry-After`.

Request

``` code
POST /shows/1/holds HTTP/1.1
Content-Type: application/json

{
  "customer": "kabir",
  "seats": [
    "G12"
  ]
}
```

Response

``` code
HTTP/1.1 503 
Retry-After: 1
Content-Type: application/problem+json

{
  "detail": "Someone is booking this seat right now. Try again in a moment.",
  "instance": "/shows/1/holds",
  "status": 503,
  "title": "Service Unavailable"
}
```

### Case 7: seats and count together

**Why:** `400`.

Request

``` code
POST /shows/1/holds HTTP/1.1
Content-Type: application/json

{
  "customer": "kabir",
  "seats": [
    "G12"
  ],
  "count": 1
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Send either seats or count",
  "instance": "/shows/1/holds",
  "status": 400,
  "title": "Bad Request"
}
```

Case 6, timed by `docs/capture.sh`: answered after 2000 ms (to the nearest 100 ms).

## The seats and holds afterwards

``` code
 seat_no | price_paise | held | booked_by 
---------+-------------+------+-----------
 E10     |       25000 | t    | 
 E11     |       25000 | t    | 
 F12     |       35000 | f    | meera
 F13     |       35000 | f    | meera
(4 rows)
```

``` code
 customer | seat_nos  | total_paise |  status   | payment_ref  
----------+-----------+-------------+-----------+--------------
 arjun    | {E10,E11} |       50000 | held      | 
 meera    | {F12,F13} |       70000 | confirmed | pay_c4c33602
(2 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                             | What happens                                   | Proved by                                                |
|----------------------------------|------------------------------------------------|----------------------------------------------------------|
| Named seats                      | Held for 10 minutes, priced                    | `namedSeatsAreHeldForTenMinutes`                         |
| Any two seats                    | The first two free                             | `anyTwoSeatsCanBeAskedFor`                               |
| Confirm, and confirm again       | Booked; the same answer                        | `confirmingBooksTheSeatsAndASecondConfirmAnswersTheSame` |
| A taken seat among others        | `409` naming it; the others not held           | `aTakenSeatIs409AndNamesIt`                              |
| An expired hold                  | `409`; the seat is free again                  | `anExpiredHoldCannotBeConfirmedAndTheSeatIsFreeAgain`    |
| Unknown seat or hold; bad bodies | `404`; `400`                                   | `unknownThingsAre404AndBadBodiesAre400`                  |
| Ten holds of F12 at once         | One hold                                       | `tenPeopleHoldingF12AtOnceGetOneHold`                    |
| Seven "any two" at once          | Fourteen different seats                       | `sevenPeopleAskingForAnyTwoGetFourteenDifferentSeats`    |
| A hold taken over while paying   | Refunded, `409`, the seat not booked for Meera | `aHoldThatRunsOutWhilePayingIsRefunded`                  |
| Rules written by plain SQL       | Refused by named constraints                   | `seatAndHoldRulesHoldWithoutJava`                        |
| A hold that cannot be written    | No seat held                                   | `aHoldThatCannotBeWrittenHoldsNoSeat`                    |

## The trap

Plausible but wrong

Locking without a timeout, or holding locks across remote calls.

- **The old confirm.** The test runs it against the real database: lock F12, then "call the provider" for 3 seconds inside the same transaction. The old code had no lock timeout, so everyone asking for F12 waited too. The API answers within the half-second limit set for tests: `503`, `Retry-After: 1`; once the lock is gone, F12 can be held.
- **The API's confirm.** With a 2-second provider, F12 answers "taken" at once and F13 next to it is free: nothing is locked while paying.

While building, each part was undone once: no `FOR UPDATE` turned 1 test red; no lock timeout 1; no `SKIP LOCKED` 1; a confirm that charges again 1; the lock timeout not turned into a `503` 1. The first parallel tests passed with `FOR UPDATE` and `SKIP LOCKED` removed: see Tests.

``` code
package com.seatsure.holds;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Duration;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old booking code locked the seat, called the payment provider while still holding the lock,
 * and waited for locks with no time limit. When the provider was slow, every other customer for that seat waited
 * with it, and requests piled up. Each test plays the old behaviour against the real database, then the API.
 */
class LockAcrossPaymentTrapTest extends ApiTest {

    @Autowired
    TransactionTemplate tx;

    @Test
    void aLockHeldAcrossASlowPaymentMadeEveryoneElseWait() throws Exception {
        CountDownLatch locked = new CountDownLatch(1);
        // The old confirm: lock F12, then "call the provider" (3 seconds) inside the same transaction.
        CompletableFuture<Void> oldConfirm = CompletableFuture.runAsync(() -> tx.executeWithoutResult(s -> {
            jdbc.sql("SELECT seat_no FROM seats WHERE show_id = 1 AND seat_no = 'F12' FOR UPDATE").query(String.class).single();
            locked.countDown();
            try {
                Thread.sleep(3000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }));
        locked.await();
        long started = System.nanoTime();
        // The old code had no lock timeout. The API has one: it answers within about half a second, and says why.
        hold("arjun", "F12").andExpect(status().isServiceUnavailable()).andExpect(header().string("Retry-After", "1"));
        assertThat(Duration.ofNanos(System.nanoTime() - started)).isLessThan(Duration.ofSeconds(2));
        oldConfirm.join();
        hold("arjun", "F12").andExpect(status().isCreated());   // and once the lock is gone, the seat can be held
    }

    @Test
    void theApiPaysWithoutHoldingAnyLock() throws Exception {
        String meera = holdId("meera", "F12");
        payments.delay = Duration.ofSeconds(2);   // a slow provider
        CompletableFuture<Integer> paying = CompletableFuture.supplyAsync(() -> {
            try {
                return confirm(meera).andReturn().getResponse().getStatus();
            } catch (Exception e) {
                throw new IllegalStateException(e);
            }
        });
        Thread.sleep(300);   // meera's confirm is now waiting on the provider
        long started = System.nanoTime();
        hold("arjun", "F12").andExpect(status().isConflict());   // held by meera: told at once, no waiting
        hold("arjun", "F13").andExpect(status().isCreated());    // and the row next to it is not blocked at all
        assertThat(Duration.ofNanos(System.nanoTime() - started)).isLessThan(Duration.ofMillis(500));
        assertThat(paying.join()).isEqualTo(200);
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
./mvnw test                 # all 13 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Lock a seat from `psql` for five seconds, and ask the API for it meanwhile:

``` code
docker compose exec -T postgres psql -U seatsure -d seatsure -c "BEGIN; SELECT * FROM seats WHERE seat_no = 'G10' FOR UPDATE; SELECT pg_sleep(5); COMMIT;" > /dev/null &
sleep 1
curl -s -o /dev/null -w '%{http_code} after %{time_total}s\n' -X POST http://localhost:8080/shows/1/holds -H 'Content-Type: application/json' -d '{"customer": "you", "seats": ["G10"]}'
```

It prints `503` after about 2 seconds. Run the `curl` again once the five seconds are over: `201`.

## Troubleshooting

| You see                                                             | Cause                                                              | Fix                                                                                     |
|---------------------------------------------------------------------|--------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| `canceling statement due to lock timeout` (SQLState 55P03) as a 500 | Spring's translation of 55P03 is not `CannotAcquireLockException`. | Match the SQLState, as `Holds` does. Found while building this station.                 |
| Parallel tests pass even with the lock removed                      | The race window is too small for the test to hit it.               | Widen it on purpose (here a 200 ms trigger), and check the test fails without the lock. |
| `expiresAt` differs between create and read                         | Java nanoseconds against PostgreSQL microseconds.                  | Truncate the clock to microseconds.                                                     |
| `Could not find a valid Docker environment`                         | Docker is not running.                                             | Start Docker Desktop or the Docker service.                                             |

## Project layout

``` tree
stations/082-movie-seat-holds/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/seatsure/holds/
│   ├── Holds.java   ├── HoldController.java   ├── Payments.java   └── HoldsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__shows_seats_holds.sql, V2__demo_show.sql
├── src/test/java/com/seatsure/holds/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/seatsure/holds/Holds.java`

Does  
Holding, picking and confirming seats.

Why  
Short transactions with a lock timeout; `FOR UPDATE` for named seats, `SKIP LOCKED` for any; payment outside any transaction; booking by one update on the hold id.

Without it  
Double-sold seats, customers stuck behind a slow provider, and seats paid for twice.

- Spring 7 reports PostgreSQL's lock timeout (SQLState 55P03) as `UncategorizedSQLException`, not `CannotAcquireLockException`: the code matches the SQLState. Found while building.
- The lock timeout is set with `set_config('lock_timeout', ..., true)`, the function form of `SET LOCAL`, so it ends with the transaction.
- A hold that ran out while paying, but whose seats nobody took, still books. A first version also required `held_until > now`; removing it changed no test, because the hold id already changes when someone else takes the seat.
- Times are cut to microseconds: PostgreSQL keeps no more, and the API answered a different `expiresAt` before and after storing it. Found in the captures.

#### `src/main/java/com/seatsure/holds/HoldController.java`

Does  
The two endpoints.

Why  
Seats or count, never both; the lock timeout becomes `503` with `Retry-After`.

Without it  
A request hanging until a load balancer gives up.

#### `src/main/java/com/seatsure/holds/Payments.java`

The simulated provider: waits, then records a reference; the same hold always gets the same reference.

#### `src/main/resources/db/migration/V1__shows_seats_holds.sql`

Does  
Shows, seats and holds.

Why  
One row per seat (its row lock is the seat's lock); a hold has an id and an end together; a booked seat is not held.

Without it  
Seat states that cannot exist.

#### `src/main/resources/db/migration/V2__demo_show.sql`

One show, fifteen seats.

#### `src/main/resources/application.yaml`

The demo rules: 10-minute holds, a 2-second lock timeout, the simulated provider's delay.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/seatsure/holds/HoldsApplication.java`

Entry point, and the `Clock` every expiry uses.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                             | Test class                      | Result |
|---------------|---------------------------------------------------------|---------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                | `HoldContractTest` (6)          | pass   |
| Every station | Reproduce the failure before the fix                    | `LockAcrossPaymentTrapTest` (2) | pass   |
| Database      | Rollback and constraint tests against a real database   | `HoldDatabaseTest` (2)          | pass   |
| Concurrency   | A real concurrency test that proves the invariant holds | `HoldConcurrencyTest` (3)       | pass   |

The parallel tests run on virtual threads released by one latch. Their first version passed with `FOR UPDATE` and `SKIP LOCKED` removed: the requests barely overlapped, so the race never happened. A trigger now makes each hold take 200 ms to write, as on a busy database, and without the locks those tests fail every time. Found while building. Tests use a lock timeout of 500 ms.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.seatsure.holds.HoldConcurrencyTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.seatsure.holds.HoldDatabaseTest
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.seatsure.holds.HoldContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.seatsure.holds.LockAcrossPaymentTrapTest
[INFO] Tests run: 13, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/seatsure/holds/LockAcrossPaymentTrapTest.java`

Written first: the old lock held across a payment, against the API's timeout and lock-free payment.

#### `src/test/java/com/seatsure/holds/HoldConcurrencyTest.java`

Ten holders of one seat, seven pickers, a hold taken over while paying.

#### `src/test/java/com/seatsure/holds/HoldDatabaseTest.java`

Named constraints with plain SQL; a hold that cannot be written holds nothing.

#### `src/test/java/com/seatsure/holds/HoldContractTest.java`

Holds and confirms through HTTP.

#### `src/test/java/com/seatsure/holds/ApiTest.java`

Shared setup: the test clock, free seats and a fast provider before each test, request helpers.

#### `src/test/java/com/seatsure/holds/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/seatsure/holds/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=ReleaseHoldChallengeTest` (Docker must be running). The sweeper test does not compile until `HoldSweeper` exists.
3.  Change the code until it passes, then run `./mvnw test` to check the other 13 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 16 tests pass (13 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Give the seats back

`DELETE /holds/{id}` frees the hold's seats at once (`204`); a confirmed hold stays (`409`).

**Done when:** both tests in `ReleaseHoldChallengeTest` pass.

Hints

- Lock the hold row, check it is still held, clear its seats, mark it released.
- The database refuses the new status until a V3 migration changes `holds_status`; challenge 2 needs the same.

#### `challenge/ReleaseHoldChallengeTest.java`

``` code
package com.seatsure.holds;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: DELETE /holds/{id} gives the seats back at once (204); a confirmed hold cannot be released (409). */
class ReleaseHoldChallengeTest extends ApiTest {

    @Test
    void releasingFreesTheSeats() throws Exception {
        String id = holdId("meera", "F12", "F13");
        mvc.perform(delete("/holds/{id}", id)).andExpect(status().isNoContent());
        hold("arjun", "F12", "F13").andExpect(status().isCreated());
    }

    @Test
    void aConfirmedHoldStays() throws Exception {
        String id = holdId("meera", "F12");
        confirm(id);
        mvc.perform(delete("/holds/{id}", id)).andExpect(status().isConflict());
        mvc.perform(delete("/holds/{id}", "00000000-0000-0000-0000-000000000000")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Sweep expired holds, twice at once

`HoldSweeper.sweep(batchSize)` marks expired holds `expired` and clears their seats. Two app instances run it at the same moment: they share the work and no hold is swept twice.

**Done when:** the test in `ExpiredHoldSweepChallengeTest` passes.

Hints

- `SELECT ... FOR UPDATE SKIP LOCKED LIMIT n` makes the holds table a work queue.
- `holds_confirmed_paid` must allow released and expired holds without a payment reference.

#### `challenge/ExpiredHoldSweepChallengeTest.java`

``` code
package com.seatsure.holds;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.Duration;
import java.util.concurrent.CompletableFuture;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 2: HoldSweeper.sweep(batchSize) marks expired holds 'expired' and clears their seats, a batch at a time.
 * Two app instances run it at once: with FOR UPDATE SKIP LOCKED they share the work, and no hold is swept twice.
 * Returns how many holds this call swept.
 */
class ExpiredHoldSweepChallengeTest extends ApiTest {

    @Autowired
    HoldSweeper sweeper;

    @Test
    void twoSweepersShareTheWork() throws Exception {
        for (String seat : new String[]{"E10", "E11", "E12", "E13", "E14", "G10"}) {
            hold("someone", seat);
        }
        later(Duration.ofMinutes(11));
        CompletableFuture<Integer> one = CompletableFuture.supplyAsync(() -> sweeper.sweep(10));
        CompletableFuture<Integer> two = CompletableFuture.supplyAsync(() -> sweeper.sweep(10));
        assertThat(one.join() + two.join()).isEqualTo(6);
        assertThat(jdbc.sql("SELECT count(*) FROM holds WHERE status = 'expired'").query(Long.class).single()).isEqualTo(6);
        assertThat(jdbc.sql("SELECT count(*) FROM seats WHERE hold_id IS NOT NULL").query(Long.class).single()).isZero();
        assertThat(sweeper.sweep(10)).isZero();
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Without row locks, and on release day

Design holds without `FOR UPDATE`: one conditional `UPDATE seats ... WHERE hold_id IS NULL` per seat, and what "all or none" then needs. Then: tickets for a big release open at 10:00 and 200,000 people arrive. Where do locks stop scaling, and how would a waiting room (a queue in front of holds) change the design?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: a lock held across a slow payment.
2.  One row per seat; hold with `FOR UPDATE` in a short transaction with a lock timeout.
3.  Pick "any" seats with `SKIP LOCKED`.
4.  Pay outside any transaction; book with one update; refund if the seats were taken meanwhile.

## Design alternatives and trade-offs

| Approach                                                | What it costs                                                   | Verdict           |
|---------------------------------------------------------|-----------------------------------------------------------------|-------------------|
| Short FOR UPDATE with a lock timeout; pay without locks | A hold can run out while paying: refund needed.                 | Chosen            |
| Lock across the payment call                            | Everyone waits on the slowest provider.                         | The trap          |
| Locks with no timeout                                   | Requests pile up behind one stuck transaction.                  | The trap          |
| Optimistic: conditional UPDATE per seat                 | No waiting at all; all-or-none needs care across several seats. | Good for one seat |
| Holds in Valkey with expiring keys                      | Fast; a second store to keep consistent with bookings.          | At very high load |

## Database design

| Object                                         | What                      | Why                                                               |
|------------------------------------------------|---------------------------|-------------------------------------------------------------------|
| `seats_pk`                                     | One row per seat per show | The row lock is the seat's lock.                                  |
| `seats_hold_complete`, `seats_booked_not_held` | CHECKs                    | A seat is free, held until a time, or booked: nothing in between. |
| `holds_confirmed_paid`                         | CHECK                     | No confirmed hold without a payment reference.                    |
| `holds_some_seats`, `holds_total_positive`     | CHECKs                    | Every hold is for something.                                      |

**Transaction boundaries:** a hold is one short transaction (seats and hold row). The payment is outside any transaction. Booking is one more short transaction.

``` code
CREATE TABLE shows (
    id        bigint CONSTRAINT shows_pk PRIMARY KEY,
    title     text NOT NULL,
    starts_at timestamptz NOT NULL
);

-- One row per seat per show: the row lock on it is the lock on the seat.
CREATE TABLE seats (
    show_id     bigint NOT NULL CONSTRAINT seats_show_fk REFERENCES shows,
    seat_no     text NOT NULL,
    price_paise bigint NOT NULL,
    hold_id     uuid,
    held_until  timestamptz,
    booked_by   text,
    CONSTRAINT seats_pk PRIMARY KEY (show_id, seat_no),
    CONSTRAINT seats_no_shape CHECK (seat_no ~ '^[A-Z][0-9]{1,2}$'),
    CONSTRAINT seats_price_positive CHECK (price_paise > 0),
    -- A hold has both an id and an end; a booked seat is not also held.
    CONSTRAINT seats_hold_complete CHECK ((hold_id IS NULL) = (held_until IS NULL)),
    CONSTRAINT seats_booked_not_held CHECK (booked_by IS NULL OR hold_id IS NULL)
);

CREATE TABLE holds (
    id          uuid CONSTRAINT holds_pk PRIMARY KEY,
    show_id     bigint NOT NULL CONSTRAINT holds_show_fk REFERENCES shows,
    customer    text NOT NULL,
    seat_nos    text[] NOT NULL,
    total_paise bigint NOT NULL,
    expires_at  timestamptz NOT NULL,
    status      text NOT NULL,
    payment_ref text,
    CONSTRAINT holds_status CHECK (status IN ('held', 'confirmed', 'refunded')),
    CONSTRAINT holds_total_positive CHECK (total_paise > 0),
    CONSTRAINT holds_some_seats CHECK (cardinality(seat_nos) BETWEEN 1 AND 6),
    CONSTRAINT holds_confirmed_paid CHECK (status = 'held' OR payment_ref IS NOT NULL)
);
```

# 3 · Go deeper: Production

Timeouts everywhere  
Lock timeout per transaction, a statement timeout for the rest, and a time limit on the provider call. The lock timeout must be shorter than whatever sits in front of the app (load balancer, client).

Lock waits  
Watch lock waits in PostgreSQL (`pg_locks`, `log_lock_waits`); a rising count of 503s means a long transaction somewhere.

Refunds  
A refund after a taken-over hold must really happen: put it in an outbox and retry it, not in a log line.

Expired holds  
Expired holds free their seats by time alone; a sweeper (challenge 2) keeps the tables tidy.

# 3 · Go deeper: Interview

## Interview takeaways

Why not hold a lock while calling the payment provider?

The provider's slowest moment becomes everyone's waiting time, and connections and threads pile up behind the lock. Keep transactions short and make remote calls outside them.

What does lock_timeout do?

It makes a statement give up after waiting that long for a lock, instead of waiting forever; the error (SQLState 55P03) can become a "try again" answer.

When is SKIP LOCKED right?

When any of several rows will do: picking free seats, taking jobs from a queue. It is wrong when you need specific rows.

Pessimistic or optimistic?

Pessimistic (lock, then check) when conflicts are common and the work is short, like hot seats. Optimistic (check a version on write) when conflicts are rare, like editing a task.

How do you test a race?

Run the requests in parallel with a start latch, and make sure the test fails without the fix; widen the window if it does not.

## Self-check rubric

| Area        | Meets the bar       | Above the bar                                          |
|-------------|---------------------|--------------------------------------------------------|
| Correctness | All 13 tests pass.  | You ran the flawed version and explained each failure. |
| Locking     | No seat sold twice. | Locks short, bounded, never across a remote call.      |
| Answers     | 409 for taken.      | 503 with Retry-After for busy, and a refund path.      |
| Proof       | A parallel test.    | One that fails without the lock, every time.           |

# 3 · Go deeper: Review

## The pull request

A teammate makes booking "atomic": the confirm locks the hold's seats, charges, and books, all in one transaction. They also remove the lock timeout, because customers complained about "try again" errors. Read the file and list every problem before opening the findings.

#### `review/Holds.java`

``` code
package com.seatsure.holds;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.sql.SQLException;
import java.time.Clock;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
class Holds {

    record Hold(UUID id, long showId, String customer, List<String> seatNos, long totalPaise, OffsetDateTime expiresAt, String status, String paymentRef) {
    }

    /** The seat is being locked by someone else for longer than we are willing to wait. */
    static final class SeatBusy extends RuntimeException {
    }

    private record Seat(String seatNo, long pricePaise, boolean free) {
    }

    private final JdbcClient jdbc;
    private final TransactionTemplate tx;
    private final Payments payments;
    private final Clock clock;
    private final Duration holdFor;
    private final long lockTimeoutMs;

    Holds(JdbcClient jdbc, TransactionTemplate tx, Payments payments, Clock clock,
          @Value("${seatsure.hold-for}") Duration holdFor, @Value("${seatsure.lock-timeout}") Duration lockTimeout) {
        this.jdbc = jdbc;
        this.tx = tx;
        this.payments = payments;
        this.clock = clock;
        this.holdFor = holdFor;
        this.lockTimeoutMs = lockTimeout.toMillis();
    }

    /**
     * Holds these seats, all or none. The seat rows are locked (SELECT ... FOR UPDATE) for the few milliseconds of
     * this transaction only, and never waited on for longer than the lock timeout.
     */
    Hold hold(long showId, String customer, List<String> seatNos) {
        return inSeatTransaction(() -> {
            OffsetDateTime now = now();
            List<Seat> seats = jdbc.sql("""
                            SELECT seat_no, price_paise, booked_by IS NULL AND (hold_id IS NULL OR held_until <= ?) AS free
                            FROM seats WHERE show_id = ? AND seat_no = ANY(?) ORDER BY seat_no FOR UPDATE""")
                    .params(now, showId, seatNos.toArray(String[]::new)).query(Seat.class).list();
            if (seats.size() != seatNos.size()) {
                throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No such show or seat");
            }
            if (!seats.stream().allMatch(Seat::free)) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "Taken: " + String.join(", ", seats.stream().filter(s -> !s.free()).map(Seat::seatNo).toList()));
            }
            return save(showId, customer, seats, now);
        });
    }

    /**
     * Any n free seats. FOR UPDATE SKIP LOCKED: seats someone is locking right now are passed over instead of
     * waited for, so ten people asking at once get ten different pairs.
     */
    Hold holdAny(long showId, String customer, int count) {
        return inSeatTransaction(() -> {
            OffsetDateTime now = now();
            List<Seat> seats = jdbc.sql("""
                            SELECT seat_no, price_paise, true AS free FROM seats
                            WHERE show_id = ? AND booked_by IS NULL AND (hold_id IS NULL OR held_until <= ?)
                            ORDER BY seat_no LIMIT ? FOR UPDATE SKIP LOCKED""")
                    .params(showId, now, count).query(Seat.class).list();
            if (seats.size() < count) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "Not enough free seats");
            }
            return save(showId, customer, seats, now);
        });
    }

    private Hold save(long showId, String customer, List<Seat> seats, OffsetDateTime now) {
        UUID id = UUID.randomUUID();
        OffsetDateTime until = now.plus(holdFor);
        List<String> nos = seats.stream().map(Seat::seatNo).toList();
        long total = seats.stream().mapToLong(Seat::pricePaise).sum();
        jdbc.sql("UPDATE seats SET hold_id = ?, held_until = ? WHERE show_id = ? AND seat_no = ANY(?)").params(id, until, showId, nos.toArray(String[]::new)).update();
        jdbc.sql("INSERT INTO holds (id, show_id, customer, seat_nos, total_paise, expires_at, status) VALUES (?, ?, ?, ?, ?, ?, 'held')")
                .params(id, showId, customer, nos.toArray(String[]::new), total, until).update();
        return new Hold(id, showId, customer, nos, total, until, "held", null);
    }

    /**
     * Locks the hold's seats, charges, and books them, all in one transaction: a seat can never be booked without
     * a payment, or paid for without being booked.
     */
    Hold confirm(UUID holdId) {
        Hold hold = find(holdId).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "No such hold"));
        if (!hold.status().equals("held")) {
            return hold;   // confirming twice answers the same: a retry after a timeout is safe
        }
        if (!hold.expiresAt().isAfter(now())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "This hold has expired");
        }
        tx.executeWithoutResult(s -> {
            List<String> mine = jdbc.sql("SELECT seat_no FROM seats WHERE hold_id = ? FOR UPDATE").param(holdId).query(String.class).list();
            if (mine.size() != hold.seatNos().size()) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "This hold has expired");
            }
            String paymentRef = payments.charge(holdId.toString(), hold.totalPaise());
            jdbc.sql("UPDATE seats SET booked_by = ?, hold_id = NULL, held_until = NULL WHERE hold_id = ?").params(hold.customer(), holdId).update();
            jdbc.sql("UPDATE holds SET status = 'confirmed', payment_ref = ? WHERE id = ?").params(paymentRef, holdId).update();
        });
        return find(holdId).orElseThrow();
    }

    Optional<Hold> find(UUID holdId) {
        return jdbc.sql("SELECT id, show_id, customer, seat_nos, total_paise, expires_at, status, payment_ref FROM holds WHERE id = ?").param(holdId)
                .query((rs, n) -> new Hold(rs.getObject(1, UUID.class), rs.getLong(2), rs.getString(3), List.of((String[]) rs.getArray(4).getArray()),
                        rs.getLong(5), rs.getObject(6, OffsetDateTime.class), rs.getString(7), rs.getString(8))).optional();
    }

    private <T> T inSeatTransaction(java.util.function.Supplier<T> work) {
        try {
            return tx.execute(s -> work.get());   // no lock timeout: customers saw "try again" errors, now they simply wait
        } catch (DataAccessException e) {
            // PostgreSQL's lock timeout is SQLState 55P03; Spring 7 reports it as UncategorizedSQLException, so match the state.
            if (e.getMostSpecificCause() instanceof SQLException sql && "55P03".equals(sql.getSQLState())) {
                throw new SeatBusy();
            }
            throw e;
        }
    }

    private OffsetDateTime now() {
        // PostgreSQL keeps microseconds: without this, the expiresAt we answer differs from the one we stored.
        return OffsetDateTime.ofInstant(clock.instant().truncatedTo(ChronoUnit.MICROS), ZoneOffset.UTC);
    }
}
```

## Findings

1Payment inside the seat transaction

"Never booked without a payment" is bought by holding the seat locks for the whole provider call. A slow provider now freezes every request for those seats, and the confirm that re-holds the seats waits behind it.

**Test evidence:** `theApiPaysWithoutHoldingAnyLock` and `aHoldThatRunsOutWhilePayingIsRefunded` fail.

2No lock timeout

"Customers saw try-again errors": now they wait, as long as the longest lock. With the first flaw, that is as long as the slowest payment.

**Test evidence:** `aLockHeldAcrossASlowPaymentMadeEveryoneElseWait` fails.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class                  | Fixed version | Flawed version |
|-----------------------------|---------------|----------------|
| `HoldContractTest`          | 6 / 6         | 6 / 6          |
| `HoldDatabaseTest`          | 2 / 2         | 2 / 2          |
| `HoldConcurrencyTest`       | 3 / 3         | 2 / 3          |
| `LockAcrossPaymentTrapTest` | 2 / 2         | 0 / 2          |

Both changes answer real complaints, and both look safer. The tests that fail are the ones with a slow provider: in production that is a bad evening, not a normal day.
