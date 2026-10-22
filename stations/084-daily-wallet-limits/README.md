# Station 084 · Daily wallet limits

Working Systems · 0–2 years · Core · Fintech · Types: Database, Concurrency

Spring Boot 4.1.1 · Java 25 · SELECT ... FOR UPDATE on the parent row · IST day boundaries · JdbcClient · triggers · PostgreSQL 17 · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The wallets, owners and KYC tiers are demo data, not Tijori's, and the limits are demo rules, not RBI's. Nothing is charged: a top-up creates a record and raises a balance number; where the money comes from is another system.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 15 tests.

# 1 · Understand

## The problem in real life

1.  **₹12,000 on a ₹10,000 limit**

    Ananya's wallet has the minimum KYC: ₹10,000 of top-ups a day. Her app sent two top-ups of ₹6,000 in the same second (a double tap and a retry). Both went through.

2.  **Why the check did not help**

    Each request added up today's top-ups (₹0), saw that ₹6,000 fits, and inserted. Neither could see the other's row, because it was not committed yet. There was no existing row to lock or wait on.

3.  **The fix**

    Lock the wallet's row first, then add up, then insert. The second top-up waits at the lock for a few milliseconds, adds up again, sees ₹6,000, and is refused. The day is India's day, from midnight IST.

A limit over many rows needs one row to queue on. Lock the parent (the wallet) before you add up its children (the top-ups).

## What are we building?

One endpoint: top up a wallet, unless today's top-ups (in India's day) would pass the wallet's KYC limit.

## An everyday analogy

A shop allows each customer ten items on sale per day. If two cashiers each look at the customer's slip at the same moment, both see room. If the customer must hand the slip to one cashier at a time, the second cashier sees the first one's entry.

## How it works in 4 steps

1.  **Lock** the wallet row. Another top-up for this wallet waits here; other wallets do not.
2.  **Add up** this wallet's top-ups from 00:00 IST today.
3.  **Decide**: if the new one does not fit, `409` with how much is left.
4.  **Write** the top-up and the new balance, and commit, which releases the lock.

Check yourself: Ananya tops up ₹9,000 at 23:59 IST and ₹9,000 at 00:01 IST. Is the second refused?

No: 00:01 IST is a new day in India, so ₹9,000 fits. It would be refused if the day were counted in UTC, where both are on the same date: `theLimitResetsAtMidnightInIndia`.

## What this station is not

- **Not RBI's rules.** The real rules for prepaid wallets are different and change over time; the limits here are demo rules.
- **No real money.** A top-up records a row and raises a number; the bank or UPI side is another system.
- **No retries with a key.** A repeated request is a new top-up here; station 085 shows idempotency keys.

## Key terms

| Term            | Simple meaning                                                            | Everyday example                                                 | In this project                      |
|-----------------|---------------------------------------------------------------------------|------------------------------------------------------------------|--------------------------------------|
| **Wallet**      | Money kept in an app, spent by tapping or scanning.                       | A prepaid metro card.                                            | `wallets`                            |
| **Top-up**      | Adding money to the wallet.                                               | Recharging the metro card.                                       | `POST /wallets/{id}/top-ups`         |
| **KYC tier**    | How well the owner has been identified; better identified, higher limits. | A library card with or without an address proof.                 | `minimum`, `full`                    |
| **Daily limit** | The most that may be added in one day.                                    | An ATM's daily cash limit.                                       | ₹10,000 or ₹1,00,000 (demo rules)    |
| **Parent row**  | The one row every change for a thing goes through, here the wallet.       | The one register at a shop counter.                              | `SELECT ... FOR UPDATE` on `wallets` |
| **IST**         | India Standard Time, UTC+05:30, no daylight saving.                       | Midnight in Delhi is 18:30 in London the day before (in winter). | `Asia/Kolkata`                       |

# 2 · Build: Spec

## Business problem

**Tijori** (a fictional wallet app): two top-ups at the same second took a wallet past the ₹10,000 daily KYC limit.

## Acceptance criteria

Demo wallets: 1001 Ananya, minimum KYC, ₹500 balance; 1002 Vikram, full KYC. Demo rules: minimum KYC ₹10,000 of top-ups a day, full KYC ₹1,00,000; one top-up ₹1 to ₹1,00,000.

1.  **Given** room today, **then** `201`, the new balance and today's total.
2.  **Given** a top-up that passes the limit by even one paisa, **then** `409` with how much is left; exactly the limit is allowed.
3.  **Given** ten top-ups at once, **then** no more get through than fit.
4.  **Given** 00:00 IST, **then** a new day; 05:30 IST (midnight UTC) is not.
5.  **Given** an unknown wallet, **then** `404`; a fraction of a paisa, a missing or out-of-range amount, `400`.

## Requirements

- Money in integer paise, never a fraction.
- The wallet row is locked before today's top-ups are added up, in the same transaction as the insert.
- The database refuses a top-up past the limit from any writer, with the same lock.

## Learning objectives

- See why summing without a lock lets two writers through, even with correct code.
- Lock the parent row before checking a rule over its children.
- Count days in the business's time zone, not the server's.
- Back the rule with a database trigger that every writer meets.

# 2 · Build: API contract

## Endpoint

| Method | Path                    | Purpose                                                |
|--------|-------------------------|--------------------------------------------------------|
| `POST` | `/wallets/{id}/top-ups` | `{amountPaise}`: record a top-up within today's limit. |

## Status codes

| Status | When                                                                                 |
|--------|--------------------------------------------------------------------------------------|
| 201    | Recorded: the top-up, the new balance, today's total and the limit                   |
| 400    | Amount missing, a fraction, below ₹1 or above ₹1,00,000                              |
| 404    | No such wallet                                                                       |
| 409    | Today's top-ups would pass the limit: `remainingTodayPaise` says how much still fits |

## Captured examples

Captured with curl from the running app on 22 Oct 2026, in this order. JSON bodies are indented for reading; `Date`, connection and standard security headers are left out.

### Case 1: Ananya tops up ₹6,000

**Why:** ₹0 so far today: it fits.

Request

``` code
POST /wallets/1001/top-ups HTTP/1.1
Content-Type: application/json

{
  "amountPaise": 600000
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 163

{
  "id": 1,
  "walletId": 1001,
  "amountPaise": 600000,
  "balancePaise": 650000,
  "toppedUpTodayPaise": 600000,
  "dailyLimitPaise": 1000000,
  "createdAt": "2026-10-22T11:53:40.656586Z"
}
```

### Case 2: ₹5,000 more

**Why:** ₹11,000 would pass ₹10,000: `409`, and the app can offer ₹4,000.

Request

``` code
POST /wallets/1001/top-ups HTTP/1.1
Content-Type: application/json

{
  "amountPaise": 500000
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "The daily limit for minimum-KYC wallets is ₹10,000.00; ₹6,000.00 was topped up today (IST), so at most ₹4,000.00 more",
  "instance": "/wallets/1001/top-ups",
  "status": 409,
  "title": "Conflict",
  "remainingTodayPaise": 400000
}
```

### Case 3: exactly ₹4,000

**Why:** exactly the limit is allowed.

Request

``` code
POST /wallets/1001/top-ups HTTP/1.1
Content-Type: application/json

{
  "amountPaise": 400000
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 165

{
  "id": 2,
  "walletId": 1001,
  "amountPaise": 400000,
  "balancePaise": 1050000,
  "toppedUpTodayPaise": 1000000,
  "dailyLimitPaise": 1000000,
  "createdAt": "2026-10-22T11:53:40.752116Z"
}
```

### Case 4: Vikram, full KYC, ₹50,000

**Why:** his tier allows ₹1,00,000 a day.

Request

``` code
POST /wallets/1002/top-ups HTTP/1.1
Content-Type: application/json

{
  "amountPaise": 5000000
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 167

{
  "id": 3,
  "walletId": 1002,
  "amountPaise": 5000000,
  "balancePaise": 5000000,
  "toppedUpTodayPaise": 5000000,
  "dailyLimitPaise": 10000000,
  "createdAt": "2026-10-22T11:53:40.780833Z"
}
```

### Case 5: a wallet that does not exist

**Why:** `404`.

Request

``` code
POST /wallets/9999/top-ups HTTP/1.1
Content-Type: application/json

{
  "amountPaise": 100000
}
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No such wallet",
  "instance": "/wallets/9999/top-ups",
  "status": 404,
  "title": "Not Found"
}
```

### Case 6: 4000.5 paise

**Why:** paise are whole numbers: `400`, not rounded.

Request

``` code
POST /wallets/1001/top-ups HTTP/1.1
Content-Type: application/json

{
  "amountPaise": 4000.5
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Failed to read request",
  "instance": "/wallets/1001/top-ups",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 7: five top-ups of ₹20,000 for Vikram at the same moment (1 of 5)

**Why:** ₹50,000 was left: two fit, three are refused. Which two depends on timing.

Request

``` code
POST /wallets/1002/top-ups HTTP/1.1
Content-Type: application/json

{
  "amountPaise": 2000000
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 167

{
  "id": 4,
  "walletId": 1002,
  "amountPaise": 2000000,
  "balancePaise": 7000000,
  "toppedUpTodayPaise": 7000000,
  "dailyLimitPaise": 10000000,
  "createdAt": "2026-10-22T11:53:40.860792Z"
}
```

### Case 7 (2 of 5)

**Why:** see above.

Request

``` code
POST /wallets/1002/top-ups HTTP/1.1
Content-Type: application/json

{
  "amountPaise": 2000000
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "The daily limit for full-KYC wallets is ₹1,00,000.00; ₹90,000.00 was topped up today (IST), so at most ₹10,000.00 more",
  "instance": "/wallets/1002/top-ups",
  "status": 409,
  "title": "Conflict",
  "remainingTodayPaise": 1000000
}
```

### Case 7 (3 of 5)

**Why:** see above.

Request

``` code
POST /wallets/1002/top-ups HTTP/1.1
Content-Type: application/json

{
  "amountPaise": 2000000
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "The daily limit for full-KYC wallets is ₹1,00,000.00; ₹90,000.00 was topped up today (IST), so at most ₹10,000.00 more",
  "instance": "/wallets/1002/top-ups",
  "status": 409,
  "title": "Conflict",
  "remainingTodayPaise": 1000000
}
```

### Case 7 (4 of 5)

**Why:** see above.

Request

``` code
POST /wallets/1002/top-ups HTTP/1.1
Content-Type: application/json

{
  "amountPaise": 2000000
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 167

{
  "id": 5,
  "walletId": 1002,
  "amountPaise": 2000000,
  "balancePaise": 9000000,
  "toppedUpTodayPaise": 9000000,
  "dailyLimitPaise": 10000000,
  "createdAt": "2026-10-22T11:53:40.863278Z"
}
```

### Case 7 (5 of 5)

**Why:** see above.

Request

``` code
POST /wallets/1002/top-ups HTTP/1.1
Content-Type: application/json

{
  "amountPaise": 2000000
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "The daily limit for full-KYC wallets is ₹1,00,000.00; ₹90,000.00 was topped up today (IST), so at most ₹10,000.00 more",
  "instance": "/wallets/1002/top-ups",
  "status": 409,
  "title": "Conflict",
  "remainingTodayPaise": 1000000
}
```

## The wallets and top-ups afterwards

``` code
  id  | owner  |  tier   | balance_paise 
------+--------+---------+---------------
 1001 | Ananya | minimum |       1050000
 1002 | Vikram | full    |       9000000
(2 rows)
```

``` code
 wallet_id | amount_paise |   created_ist    
-----------+--------------+------------------
      1001 |       600000 | 2026-10-22 17:23
      1001 |       400000 | 2026-10-22 17:23
      1002 |      5000000 | 2026-10-22 17:23
      1002 |      2000000 | 2026-10-22 17:23
      1002 |      2000000 | 2026-10-22 17:23
(5 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                              | What happens                            | Proved by                                                |
|-----------------------------------|-----------------------------------------|----------------------------------------------------------|
| A top-up within the limit         | `201`, balance and today's total        | `aTopUpWithinTheLimitIsRecorded`                         |
| Exactly the limit; one paisa more | Allowed; `409` with what is left        | `exactlyTheLimitIsAllowedAndOnePaisaMoreIsNot`           |
| Full KYC                          | The higher limit                        | `theLimitDependsOnTheKycTier`                            |
| Unknown wallet; bad amounts       | `404`; `400`                            | `unknownWalletsAre404AndBadAmountsAre400`                |
| Amounts in messages               | ₹1,00,000.00, Indian grouping           | `amountsAreShownWithIndianDigitGrouping`                 |
| 23:59:59 and 00:00 IST            | Two different days                      | `theLimitResetsAtMidnightInIndia`                        |
| 00:30 and 06:30 IST               | One day, though UTC has two dates       | `earlyMorningInIndiaIsTheSameDayAsTheEveningBeforeInUtc` |
| Ten top-ups of ₹4,000 at once     | Two `201`, eight `409`                  | `tenTopUpsOfFourThousandAtOnceLetTwoThrough`             |
| Two wallets at once               | Neither waits for the other             | `twoWalletsDoNotWaitForEachOther`                        |
| Plain SQL past the limit          | Refused by `top_ups_within_daily_limit` | `theDailyLimitHoldsForEveryWriter`                       |
| Two plain SQL writers at once     | The second waits, then is refused       | `theDailyLimitHoldsForTwoPlainSqlWritersAtOnce`          |
| Other rules written by plain SQL  | Refused by named constraints            | `otherRulesHoldWithoutJava`                              |
| The balance cannot be raised      | No top-up recorded                      | `aTopUpWhoseBalanceCannotBeRaisedLeavesNoRecord`         |

## The trap

Plausible but wrong

Summing today's top-ups without locking, so two top-ups pass the limit.

- **The old code.** The test opens two real database connections and runs them step by step: both add up ₹0, both insert ₹6,000. A new row has nothing to wait for, so both commit: ₹12,000.
- **With the wallet locked.** The second connection asks for the wallet's lock and waits. The first inserts and commits; the second then adds up ₹6,000, and another ₹6,000 does not fit.

The database rule is switched off in this test, because the old schema had none and because only the application's lock is tested here.

While building, each part was undone once: no wallet lock turned 1 test red; the day in UTC 2; `>=` instead of `>` 2; no database rule 4; the rule without its own lock 1; the rule's day in UTC 2; no transaction 2; the balance not raised 3.

``` code
package com.tijori.wallets;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.concurrent.CompletableFuture;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Written first. The old code summed today's top-ups and, if the new one fitted, inserted it, with no lock. Two
 * top-ups of ₹6,000 at the same second each summed ₹0 and both went in: ₹12,000 on a ₹10,000 limit. These tests
 * drive two real transactions step by step, so the bad order happens every time.
 */
class UnlockedSumTrapTest extends ApiTest {

    @Autowired
    DataSource dataSource;

    Connection begin() throws SQLException {
        Connection c = dataSource.getConnection();
        c.setAutoCommit(false);
        return c;   // READ COMMITTED, the default
    }

    static long sumToday(Connection c) throws SQLException {
        try (var rs = c.createStatement().executeQuery("SELECT coalesce(sum(amount_paise), 0) FROM top_ups WHERE wallet_id = 1001")) {
            rs.next();
            return rs.getLong(1);
        }
    }

    static void lockWallet(Connection c) throws SQLException {
        c.createStatement().execute("SELECT id FROM wallets WHERE id = 1001 FOR UPDATE");
    }

    static void insert(Connection c, long paise) throws SQLException {
        try (PreparedStatement s = c.prepareStatement("INSERT INTO top_ups (wallet_id, amount_paise) VALUES (1001, ?)")) {
            s.setLong(1, paise);
            s.executeUpdate();
        }
    }

    @Test
    void withoutALockBothTopUpsSawNothingAndBothWentIn() throws Exception {
        jdbc.sql("ALTER TABLE top_ups DISABLE TRIGGER top_ups_within_daily_limit").update();   // the old schema had no such rule
        try (Connection first = begin(); Connection second = begin()) {
            assertThat(sumToday(first)).isZero();    // "₹0 so far, ₹6,000 fits"
            assertThat(sumToday(second)).isZero();   // "₹0 so far, ₹6,000 fits"
            insert(first, 600000);
            insert(second, 600000);                  // a new row: there was nothing to wait for
            first.commit();
            second.commit();
        } finally {
            jdbc.sql("ALTER TABLE top_ups ENABLE TRIGGER top_ups_within_daily_limit").update();
        }
        assertThat(toppedUp(ANANYA)).isEqualTo(1200000);
    }

    @Test
    void withTheWalletLockedTheSecondWaitsAndThenSeesTheFirst() throws Exception {
        jdbc.sql("ALTER TABLE top_ups DISABLE TRIGGER top_ups_within_daily_limit").update();   // only the application's lock is tested here
        try (Connection first = begin(); Connection second = begin()) {
            lockWallet(first);
            assertThat(sumToday(first)).isZero();
            CompletableFuture<Long> secondSum = CompletableFuture.supplyAsync(() -> {
                try {
                    lockWallet(second);              // waits for the first transaction
                    return sumToday(second);
                } catch (SQLException e) {
                    throw new IllegalStateException(e);
                }
            });
            Thread.sleep(300);
            assertThat(secondSum).isNotDone();
            insert(first, 600000);
            first.commit();
            assertThat(secondSum.get()).isEqualTo(600000);   // ₹6,000 already: another ₹6,000 does not fit
            second.rollback();
        } finally {
            jdbc.sql("ALTER TABLE top_ups ENABLE TRIGGER top_ups_within_daily_limit").update();
        }
        assertThat(toppedUp(ANANYA)).isEqualTo(600000);
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
./mvnw test                 # all 15 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Hold Ananya's wallet locked from `psql` for five seconds, and top up meanwhile, hers and Vikram's:

``` code
docker compose exec -T postgres psql -U tijori -d tijori -c "BEGIN; SELECT id FROM wallets WHERE id = 1001 FOR UPDATE; SELECT pg_sleep(5); COMMIT;" > /dev/null &
sleep 1
curl -s -o /dev/null -w '%{http_code} after %{time_total}s\n' -X POST http://localhost:8080/wallets/1001/top-ups -H 'Content-Type: application/json' -d '{"amountPaise": 100000}'
curl -s -o /dev/null -w '%{http_code} after %{time_total}s\n' -X POST http://localhost:8080/wallets/1002/top-ups -H 'Content-Type: application/json' -d '{"amountPaise": 100000}'
```

Ananya's top-up prints `201` after about 4 seconds: it waited at the wallet lock, then added up. Vikram's prints `201` at once: his wallet was not locked.

## Troubleshooting

| You see                                                       | Cause                                                                                                                                         | Fix                                                            |
|---------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| Top-ups at the same moment fail with a 500 instead of a `409` | The database rule refused top-ups the application let through: the application's lock is missing. Seen while building, with the lock removed. | Lock the wallet row before adding up, in the same transaction. |
| The limit resets at 05:30 in the morning                      | The day is counted in UTC (or the server's zone).                                                                                             | Compute the day in `Asia/Kolkata`.                             |
| `100,000.00` where `1,00,000.00` was expected                 | `DecimalFormat` keeps one grouping size.                                                                                                      | Group by hand, as `TopUps.rupees` does.                        |
| `Could not find a valid Docker environment`                   | Docker is not running.                                                                                                                        | Start Docker Desktop or the Docker service.                    |

## Project layout

``` tree
stations/084-daily-wallet-limits/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/tijori/wallets/
│   ├── TopUpController.java   ├── TopUps.java   └── WalletsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__wallets_and_top_ups.sql, V2__demo_wallets.sql
├── src/test/java/com/tijori/wallets/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/tijori/wallets/TopUpController.java`

Does  
The endpoint.

Why  
Checks the amount is whole paise between ₹1 and ₹1,00,000.

Without it  
A fraction of a paisa rounded silently.

Jackson accepts `4000.5` for a `long` and drops the fraction unless `accept-float-as-int` is off; `application.yaml` turns it off.

#### `src/main/java/com/tijori/wallets/TopUps.java`

Does  
A top-up within today's limit.

Why  
Locks the wallet row, adds up the IST day's top-ups, refuses with what is left, then inserts and raises the balance, in one transaction.

Without it  
Two top-ups at once both fitting in the same room.

- Lock the parent row, not the rows you add up: for the day's first top-up there are none, so a lock on them locks nothing.
- The day runs from 00:00 IST to the next 00:00 IST, computed with `Asia/Kolkata`; the server's own zone is never used.
- `NumberFormat` for `en-IN` prints `100,000.00`: Java's `DecimalFormat` keeps one grouping size, so `rupees` groups by hand. Found while building.
- The database rule's refusal is not turned into a `409`: if it fires, this code let something through, and a 500 says so.

#### `src/main/resources/db/migration/V1__wallets_and_top_ups.sql`

Does  
Tiers, wallets, top-ups and the daily rule.

Why  
A trigger before each insert locks the wallet row and adds up the IST day, so plain SQL writers meet the same limit.

Without it  
A script or a second service topping up past the limit.

Its limits, written in the file: it watches inserts only (changing an amount or a wallet's tier later is not checked), and its day is IST.

#### `src/main/resources/db/migration/V2__demo_wallets.sql`

Two tiers, two wallets.

#### `src/main/resources/application.yaml`

Database connection, and fractions refused for whole-number fields.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/tijori/wallets/WalletsApplication.java`

Entry point, and the `Clock` the day is taken from.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                             | Test class                                        | Result |
|---------------|---------------------------------------------------------|---------------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                | `TopUpContractTest` (5), `IstDayBoundaryTest` (2) | pass   |
| Every station | Reproduce the failure before the fix                    | `UnlockedSumTrapTest` (2)                         | pass   |
| Database      | Rollback and constraint tests against a real database   | `TopUpDatabaseTest` (4)                           | pass   |
| Concurrency   | A real concurrency test that proves the invariant holds | `TopUpConcurrencyTest` (2)                        | pass   |

The parallel tests run on virtual threads released by one latch. A trigger makes each top-up take 200 ms to write, so the requests overlap every time. The database rule would stop an over-limit total even without the application's lock, so the test counts answers: with the lock removed, eight of ten requests failed with the rule's error instead of a `409`. Found while building.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.wallets.TopUpContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.wallets.TopUpConcurrencyTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.wallets.UnlockedSumTrapTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.wallets.TopUpDatabaseTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.wallets.IstDayBoundaryTest
[INFO] Tests run: 15, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tijori/wallets/UnlockedSumTrapTest.java`

Written first: two real transactions, step by step, without and with the wallet lock.

#### `src/test/java/com/tijori/wallets/TopUpConcurrencyTest.java`

Ten top-ups at once; two wallets side by side.

#### `src/test/java/com/tijori/wallets/IstDayBoundaryTest.java`

Midnight in India, and the early morning that UTC puts on another date.

#### `src/test/java/com/tijori/wallets/TopUpDatabaseTest.java`

The rule and named constraints with plain SQL, two plain SQL writers at once, and a rollback.

#### `src/test/java/com/tijori/wallets/TopUpContractTest.java`

The endpoint through HTTP, and the rupee format.

#### `src/test/java/com/tijori/wallets/ApiTest.java`

Shared setup: the test clock at noon IST, the demo wallets before each test, request helpers.

#### `src/test/java/com/tijori/wallets/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tijori/wallets/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=LimitsChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 15 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 20 tests pass (15 station tests and 5 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## What is left today

`GET /wallets/{id}/limits`: the tier, the daily limit, today's total, what is left, and when the day resets (the next 00:00 IST, as a UTC time).

**Done when:** both tests in `LimitsChallengeTest` pass.

Hints

- Reuse the sum from `topUp`; a read needs no lock.
- `resetsAt` is tomorrow's IST date at its start of day in `Asia/Kolkata`.

#### `challenge/LimitsChallengeTest.java`

``` code
package com.tijori.wallets;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: GET /wallets/{id}/limits tells the app how much more fits today and when the day resets (midnight IST). */
class LimitsChallengeTest extends ApiTest {

    @Test
    void theAppCanShowWhatIsLeftToday() throws Exception {
        topUp(ANANYA, 250000);
        mvc.perform(get("/wallets/{id}/limits", ANANYA)).andExpect(status().isOk())
                .andExpect(jsonPath("$.tier").value("minimum"))
                .andExpect(jsonPath("$.dailyLimitPaise").value(1000000))
                .andExpect(jsonPath("$.toppedUpTodayPaise").value(250000))
                .andExpect(jsonPath("$.remainingTodayPaise").value(750000))
                .andExpect(jsonPath("$.resetsAt").value("2026-10-30T18:30:00Z"));   // 00:00 IST on 31 Oct
    }

    @Test
    void unknownWalletsAre404() throws Exception {
        mvc.perform(get("/wallets/{id}/limits", 9999)).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No such wallet"));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Reverse a top-up

`POST /wallets/{id}/top-ups/{topUpId}/reversal`, for a top-up whose money never arrived: the balance goes back down and the amount stops counting towards today's limit. A second reversal answers the same; a top-up already spent is `409`.

**Done when:** the three tests in `ReversalChallengeTest` pass.

Hints

- Lock the wallet row first, as a top-up does: the balance and today's total change together.
- A V3 migration adds `reversed_at` and changes the rule's function to skip reversed top-ups.

#### `challenge/ReversalChallengeTest.java`

``` code
package com.tijori.wallets;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.ResultActions;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /wallets/{id}/top-ups/{topUpId}/reversal, for a top-up whose money never arrived. The balance goes
 * back down, the amount no longer counts towards today's limit, and a second reversal answers the same. A V3 migration
 * adds reversed_at, and the database rule stops counting reversed top-ups.
 */
class ReversalChallengeTest extends ApiTest {

    ResultActions reverse(long wallet, long topUpId) throws Exception {
        return mvc.perform(post("/wallets/{id}/top-ups/{topUpId}/reversal", wallet, topUpId));
    }

    @Test
    void aReversedTopUpFreesTheLimitAndIsReversedOnce() throws Exception {
        topUp(ANANYA, 1000000).andExpect(status().isCreated());
        reverse(ANANYA, 1).andExpect(status().isOk()).andExpect(jsonPath("$.balancePaise").value(50000));
        reverse(ANANYA, 1).andExpect(status().isOk()).andExpect(jsonPath("$.balancePaise").value(50000));
        topUp(ANANYA, 1000000).andExpect(status().isCreated()).andExpect(jsonPath("$.toppedUpTodayPaise").value(1000000));
        assertThat(balance(ANANYA)).isEqualTo(1050000);
    }

    @Test
    void aSpentTopUpCannotBeReversedAndUnknownOnesAre404() throws Exception {
        topUp(ANANYA, 300000).andExpect(status().isCreated());
        jdbc.sql("UPDATE wallets SET balance_paise = 100000 WHERE id = 1001").update();   // most of it was spent
        reverse(ANANYA, 1).andExpect(status().isConflict());
        reverse(ANANYA, 99).andExpect(status().isNotFound());
        reverse(VIKRAM, 1).andExpect(status().isNotFound());   // not this wallet's top-up
        assertThat(balance(ANANYA)).isEqualTo(100000);
    }

    @Test
    void theDatabaseRuleSkipsReversedTopUps() {
        jdbc.sql("INSERT INTO top_ups (wallet_id, amount_paise, reversed_at) VALUES (1001, 1000000, now())").update();
        jdbc.sql("INSERT INTO top_ups (wallet_id, amount_paise) VALUES (1001, 1000000)").update();
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO top_ups (wallet_id, amount_paise) VALUES (1001, 100)").update())
                .hasMessageContaining("top_ups_within_daily_limit");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Months, years and tier changes

Add a monthly and a yearly limit next to the daily one. Adding up a year of top-ups on every request gets slow: design a per-wallet, per-day totals table kept in the same transaction, and say which row to lock. Then: Ananya completes full KYC at 15:00 having topped up ₹10,000. What does she have left today, and what if her tier goes down instead?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: two connections adding up and inserting, step by step.
2.  Lock the wallet row, then add up the IST day, then insert and raise the balance, in one transaction.
3.  Test the day boundary at midnight IST, and the early morning that UTC dates differently.
4.  Add the rule to the database with the same lock, for every other writer.

## Design alternatives and trade-offs

| Approach                             | What it costs                                                                                                           | Verdict             |
|--------------------------------------|-------------------------------------------------------------------------------------------------------------------------|---------------------|
| Lock the wallet row, then sum        | Top-ups for one wallet run one at a time (milliseconds each).                                                           | Chosen              |
| Sum without a lock                   | Two writers both see room.                                                                                              | The trap            |
| Lock the top-up rows being summed    | For the day's first top-up there are none: nothing is locked.                                                           | Review finding      |
| SERIALIZABLE and retry (station 083) | No explicit lock; retries under contention.                                                                             | Also correct        |
| A daily totals row with a CHECK      | `INSERT ... ON CONFLICT DO UPDATE SET total = total + x`; the row lock does the queueing. A second table to keep right. | Good at high volume |

## Database design

| Object                                                    | What                    | Why                                                                                                             |
|-----------------------------------------------------------|-------------------------|-----------------------------------------------------------------------------------------------------------------|
| `top_ups_within_daily_limit`                              | Trigger before insert   | The rule spans rows and a tier table, so a CHECK cannot hold it. It locks the wallet row, like the application. |
| `top_ups_wallet_time`                                     | Index on (wallet, time) | Adding up one wallet's day reads only its rows.                                                                 |
| `wallets_balance_not_negative`, `top_ups_amount_positive` | CHECKs                  | No negative balance, no zero top-up.                                                                            |
| `wallets_tier_fk`, `kyc_tiers_limit_positive`             | FK, CHECK               | Every wallet has a known tier with a real limit.                                                                |

**Transaction boundary:** one transaction locks the wallet, adds up, inserts the top-up and raises the balance. The lock ends with the commit.

``` code
-- Demo rules, not RBI's: how much a wallet may be topped up per day (IST), by KYC tier.
CREATE TABLE kyc_tiers (
    tier              text CONSTRAINT kyc_tiers_pk PRIMARY KEY,
    daily_limit_paise bigint NOT NULL,
    CONSTRAINT kyc_tiers_limit_positive CHECK (daily_limit_paise > 0)
);

CREATE TABLE wallets (
    id            bigint CONSTRAINT wallets_pk PRIMARY KEY,
    owner         text NOT NULL,
    tier          text NOT NULL CONSTRAINT wallets_tier_fk REFERENCES kyc_tiers,
    balance_paise bigint NOT NULL DEFAULT 0,
    CONSTRAINT wallets_balance_not_negative CHECK (balance_paise >= 0)
);

CREATE TABLE top_ups (
    id           bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT top_ups_pk PRIMARY KEY,
    wallet_id    bigint NOT NULL CONSTRAINT top_ups_wallet_fk REFERENCES wallets,
    amount_paise bigint NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT top_ups_amount_positive CHECK (amount_paise > 0)
);
CREATE INDEX top_ups_wallet_time ON top_ups (wallet_id, created_at);

-- The rule for every writer: a wallet's top-ups on one IST day stay within its tier's daily limit. It spans rows, so it
-- is a trigger. It locks the wallet row first, like the application does, so two writers cannot both sum the old total.
-- Its limits: it watches inserts only (changing an amount or a wallet's tier later is not checked), and its day is IST.
CREATE FUNCTION top_ups_within_daily_limit() RETURNS trigger AS $$
DECLARE
    day_start timestamptz := date_trunc('day', NEW.created_at AT TIME ZONE 'Asia/Kolkata') AT TIME ZONE 'Asia/Kolkata';
    total     bigint;
    day_limit bigint;
BEGIN
    SELECT t.daily_limit_paise INTO day_limit FROM wallets w JOIN kyc_tiers t ON t.tier = w.tier WHERE w.id = NEW.wallet_id FOR UPDATE OF w;
    SELECT coalesce(sum(amount_paise), 0) INTO total FROM top_ups
    WHERE wallet_id = NEW.wallet_id AND created_at >= day_start AND created_at < day_start + interval '1 day';
    IF total + NEW.amount_paise > day_limit THEN
        RAISE EXCEPTION 'top_ups_within_daily_limit: wallet % would reach % paise on %, limit %', NEW.wallet_id, total + NEW.amount_paise, day_start, day_limit
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER top_ups_within_daily_limit BEFORE INSERT ON top_ups FOR EACH ROW EXECUTE FUNCTION top_ups_within_daily_limit();
```

# 3 · Go deeper: Production

Regulation  
Real wallet limits come from the regulator and the company's policy, by month and year as well as by day, and they change. Keep them in data (`kyc_tiers`), not code.

Keep the lock short  
Nothing slow (a bank call, a notification) inside the locked transaction; station 082 shows why.

Retries  
A phone that retries a top-up needs an idempotency key (station 085), or the limit is spent twice for one payment.

Time zones  
Store instants (`timestamptz`); compute business days in the business's zone, in one place.

# 3 · Go deeper: Interview

## Interview takeaways

Why can two top-ups pass a limit when each one checks it?

Each transaction adds up the committed top-ups, and neither can see the other's uncommitted row. Inserting a new row waits for nothing, so both commit.

Why lock the wallet row and not the top-up rows?

The new top-up is a row that does not exist yet; locking existing rows does not stop a new one, and for the day's first top-up there is nothing to lock. Every writer touches the wallet row, so it is the place to queue.

Does SELECT ... FOR UPDATE slow other wallets?

No: it locks one row. Only top-ups for the same wallet wait, for as long as the transaction lasts.

Where does the day start?

Where the business says: here 00:00 IST, which is 18:30 UTC the evening before. Never the server's zone.

Why a trigger as well?

Scripts and other services write too. The trigger takes the same lock, so they meet the same limit, and a refusal from it shows a bug in the application.

## Self-check rubric

| Area        | Meets the bar                           | Above the bar                                           |
|-------------|-----------------------------------------|---------------------------------------------------------|
| Correctness | All 15 tests pass.                      | You ran the flawed version and explained each failure.  |
| Locking     | The limit holds under parallel top-ups. | You can say why locking the summed rows does not work.  |
| Time        | The day resets.                         | At midnight IST, tested on both sides and at 05:30 IST. |
| Database    | A rule in the database.                 | One that holds for two plain SQL writers at once.       |

# 3 · Go deeper: Review

## The pull request

A teammate "narrows the lock": instead of locking the whole wallet, the top-up locks only today's top-up rows it adds up, so other wallet updates are not blocked. They also tidy the day calculation to `LocalDate.now(clock)`. Read the file and list every problem before opening the findings.

#### `review/TopUps.java`

``` code
package com.tijori.wallets;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.ErrorResponseException;

import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.temporal.ChronoUnit;
import java.util.Locale;

@Service
class TopUps {

    /** Daily limits reset at midnight in India, not at midnight UTC (05:30 IST). */
    static final ZoneId IST = ZoneId.of("Asia/Kolkata");

    record TopUp(long id, long walletId, long amountPaise, long balancePaise, long toppedUpTodayPaise, long dailyLimitPaise, OffsetDateTime createdAt) {
    }

    private record Wallet(String tier, long dailyLimitPaise) {
    }

    private final JdbcClient jdbc;
    private final Clock clock;

    TopUps(JdbcClient jdbc, Clock clock) {
        this.jdbc = jdbc;
        this.clock = clock;
    }

    @Transactional
    TopUp topUp(long walletId, long amountPaise) {
        Instant now = clock.instant().truncatedTo(ChronoUnit.MICROS);   // what PostgreSQL keeps
        Wallet w = jdbc.sql("SELECT w.tier, t.daily_limit_paise FROM wallets w JOIN kyc_tiers t ON t.tier = w.tier WHERE w.id = ?")
                .param(walletId).query(Wallet.class).optional()
                .orElseThrow(() -> new ErrorResponseException(HttpStatus.NOT_FOUND, ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No such wallet"), null));
        // Lock exactly the rows we sum, not the whole wallet: other updates to the wallet are not blocked.
        LocalDate today = LocalDate.now(clock);
        long toppedUp = jdbc.sql("SELECT amount_paise FROM top_ups WHERE wallet_id = ? AND created_at >= ? AND created_at < ? FOR UPDATE")
                .params(walletId, at(today), at(today.plusDays(1))).query(Long.class).list().stream().mapToLong(Long::longValue).sum();
        if (toppedUp + amountPaise > w.dailyLimitPaise()) {
            long left = w.dailyLimitPaise() - toppedUp;
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, "The daily limit for " + w.tier() + "-KYC wallets is "
                    + rupees(w.dailyLimitPaise()) + "; " + rupees(toppedUp) + " was topped up today (IST), so at most " + rupees(left) + " more");
            p.setProperty("remainingTodayPaise", left);
            throw new ErrorResponseException(HttpStatus.CONFLICT, p, null);
        }
        long id = jdbc.sql("INSERT INTO top_ups (wallet_id, amount_paise, created_at) VALUES (?, ?, ?) RETURNING id")
                .params(walletId, amountPaise, at(now)).query(Long.class).single();
        long balance = jdbc.sql("UPDATE wallets SET balance_paise = balance_paise + ? WHERE id = ? RETURNING balance_paise")
                .params(amountPaise, walletId).query(Long.class).single();
        return new TopUp(id, walletId, amountPaise, balance, toppedUp + amountPaise, w.dailyLimitPaise(), at(now));
    }

    private static OffsetDateTime at(Instant i) {
        return i.atOffset(ZoneOffset.UTC);
    }

    private OffsetDateTime at(LocalDate day) {
        return at(day.atStartOfDay(clock.getZone()).toInstant());
    }

    /** ₹1,00,000.00: shown to people in India, so Indian digit grouping. */
    static String rupees(long paise) {
        // java.text.DecimalFormat keeps one grouping size, so the en-IN format prints 100,000.00: grouped here instead.
        String r = Long.toString(paise / 100);
        StringBuilder s = new StringBuilder(r.substring(Math.max(0, r.length() - 3)));
        for (int i = r.length() - 3; i > 0; i -= 2) {
            s.insert(0, r.substring(Math.max(0, i - 2), i) + ",");
        }
        return "₹" + s + "." + String.format(Locale.ROOT, "%02d", paise % 100);
    }
}
```

## Findings

1Locking the rows it adds up

"Lock only what we read" sounds careful, but the next top-up is a new row: nothing stops it. For the day's first top-ups there are no rows at all, so ten requests at once each lock nothing and each see ₹0. The database rule then refuses the extras with an error, not a clear answer.

**Test evidence:** `tenTopUpsOfFourThousandAtOnceLetTwoThrough` fails.

2The day taken from the server clock

`LocalDate.now(clock)` uses the clock's zone, UTC here, so the application's day runs from 05:30 IST. Just after midnight in India it refuses a top-up that fits, and at 06:30 IST it lets through one the database rule (which counts in IST) then refuses with an error.

**Test evidence:** `theLimitResetsAtMidnightInIndia` and `earlyMorningInIndiaIsTheSameDayAsTheEveningBeforeInUtc` fail.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class             | Fixed version | Flawed version |
|------------------------|---------------|----------------|
| `TopUpContractTest`    | 5 / 5         | 5 / 5          |
| `TopUpDatabaseTest`    | 4 / 4         | 4 / 4          |
| `UnlockedSumTrapTest`  | 2 / 2         | 2 / 2          |
| `IstDayBoundaryTest`   | 2 / 2         | 0 / 2          |
| `TopUpConcurrencyTest` | 2 / 2         | 1 / 2          |

Both changes pass every single-request test. One shows only under parallel requests, the other only between midnight and 05:30 in India: exactly when nobody is testing by hand.
