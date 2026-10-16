# Station 059 · Loyalty points tested on real PostgreSQL

Working Systems · 0–2 years · Core · Retail · Types: Database

Spring Boot 4.1.1 · Java 25 · @SpringBootTest · Testcontainers with @ServiceConnection and disabledWithoutDocker · PostgreSQL 17 upsert (ON CONFLICT ... RETURNING) · H2 (trap test only) · JdbcClient · Flyway. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests; without Docker the tests are skipped, not passed). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Customers, orders and points are demo data, not Basketo's. Points are rows in a ledger; no shop or payment system calls in. The earning rate is a demo rule.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 11 tests.

# 1 · Understand

## The problem in real life

1.  **Green on H2**

    Basketo's loyalty tests ran on H2, in PostgreSQL mode. The upsert, written in H2's MERGE ... KEY syntax, passed every test.

2.  **Red in production**

    The first customer to earn points after the release got an error: PostgreSQL does not know that syntax. Nobody's points were saved until a hotfix.

3.  **The fix**

    Write the upsert PostgreSQL understands, and run every test against a real PostgreSQL 17 in Docker, the same version as production.

A test proves something only about the database it ran on. Test on the one you ship to.

## What are we building?

Customers earn points on orders (`POST /loyalty/{id}/earn`) and spend them (`POST /loyalty/{id}/redeem`). Every change is a ledger entry plus an atomic change of the balance, and every test runs on real PostgreSQL.

## An everyday analogy

A driving test in a simulator that lets you drive on the left and the right. You pass; then the real road only allows one. H2 in PostgreSQL mode is the simulator: friendly, fast, and not the road.

## How it works in 4 steps

1.  **The tests start** PostgreSQL 17 in Docker; Spring connects to it (`@ServiceConnection`).
2.  **Flyway** creates the real schema, constraints and all.
3.  **Each test** makes its own customers, so it never depends on another test's data.
4.  **Without Docker**, the tests are skipped, and say so: never passed, never failed.

Check yourself: why not keep H2 for speed and add a few PostgreSQL tests?

Because every query is a chance for a dialect difference, and you do not know in advance which ones. The shared PostgreSQL container starts once per run; after that, tests are about as fast.

## What this station is not

- **No order system.** Earn is called directly.
- **No expiry or tiers.** Points stay.
- **No history endpoint.** That is challenge 1.

## Key terms

| Term                    | Simple meaning                                                           | Everyday example                            | In this project             |
|-------------------------|--------------------------------------------------------------------------|---------------------------------------------|-----------------------------|
| **H2**                  | A small database that runs inside the test, in memory.                   | A practice pitch, not the stadium.          | The old tests               |
| **Compatibility mode**  | H2 imitating another database: some of its syntax, not all.              | An actor playing a doctor.                  | `MODE=PostgreSQL`           |
| **Upsert**              | Insert a row, or update it if it already exists, in one statement.       | Open an account, or add to it if it exists. | `ON CONFLICT ... DO UPDATE` |
| **Testcontainers**      | Real databases in Docker, started by the tests.                          | Playing in the real stadium for practice.   | `PostgresTestConfig`        |
| **@ServiceConnection**  | Tells Spring to connect to that container, with no URL in a config file. | A team bus that knows where the stadium is. | `@ServiceConnection`        |
| **Test data isolation** | Each test makes the data it needs, so tests never depend on each other.  | Each player bringing their own ball.        | `newCustomer()`             |

# 2 · Build: Spec

## Business problem

**Basketo** (a fictional grocery chain) shipped loyalty code whose only tests ran on H2. PostgreSQL rejected its upsert in production.

## Acceptance criteria

1.  **Given** a customer with no points earns on a ₹1,499 order, **then** `201`, 14 points, and the balance row is created.
2.  **Given** another order, **then** the points are added to the same row; an order under ₹100 earns 0.
3.  **Given** the same order again, in any case, **then** `409` and the balance is unchanged.
4.  **Given** 20 earns at once for a new customer, **then** all 20 are counted.
5.  **Given** a redemption above the balance, **then** `422`; an unknown customer, `404`; a malformed body, `400`.
6.  **Given** Docker is not running, **then** the tests are reported as skipped.

## Requirements

- Every test runs on the database version production runs.
- No test depends on data another test created.
- Balances never go below zero; an order earns once; both enforced by the database.
- The ledger entry and the balance change commit together.

## Learning objectives

- Write `@SpringBootTest` tests against a real database with Testcontainers and `@ServiceConnection`.
- Keep tests independent of each other's data.
- Write PostgreSQL's upsert and know why it is safe under concurrency.
- Choose a strategy for machines without Docker that never lies.

# 2 · Build: API contract

## Endpoints

| Method | Path                           | Purpose                                                                               |
|--------|--------------------------------|---------------------------------------------------------------------------------------|
| `POST` | `/loyalty/{customerId}/earn`   | Points for an order: `orderRef` and `amountPaise`; 1 point per full ₹100 (demo rule). |
| `POST` | `/loyalty/{customerId}/redeem` | Spend `points` (1 to 100,000).                                                        |

## Status codes

| Status | When                             |
|--------|----------------------------------|
| 201    | Points earned                    |
| 200    | Points redeemed                  |
| 400    | Malformed body                   |
| 404    | No such customer                 |
| 409    | This order already earned points |
| 422    | Not enough points                |

## Captured examples

Captured with curl from the running app on 16 Oct 2026, in this order, against one fresh database (Asha has 120 points; Rohan none). JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: Asha, a ₹1,499 order

**Why:** 14 points added: 134.

Request

``` code
POST /loyalty/1/earn HTTP/1.1
Content-Type: application/json

{
  "orderRef": "BK-1002",
  "amountPaise": 149900
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 63

{
  "customerId": 1,
  "orderRef": "BK-1002",
  "earned": 14,
  "balance": 134
}
```

### Case 2: Rohan's first points

**Why:** no balance row yet: the upsert creates it.

Request

``` code
POST /loyalty/2/earn HTTP/1.1
Content-Type: application/json

{
  "orderRef": "BK-1003",
  "amountPaise": 25000
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 60

{
  "customerId": 2,
  "orderRef": "BK-1003",
  "earned": 2,
  "balance": 2
}
```

### Case 3: the same order, lower case

**Why:** one order earns once: `409`.

Request

``` code
POST /loyalty/2/earn HTTP/1.1
Content-Type: application/json

{
  "orderRef": "bk-1003",
  "amountPaise": 25000
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Order BK-1003 already earned points for customer 2.",
  "instance": "/loyalty/2/earn",
  "status": 409,
  "title": "Already earned"
}
```

### Case 4: Asha spends 100

**Why:** 34 left.

Request

``` code
POST /loyalty/1/redeem HTTP/1.1
Content-Type: application/json

{
  "points": 100
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 44

{
  "customerId": 1,
  "redeemed": 100,
  "balance": 34
}
```

### Case 5: Asha spends 500

**Why:** not enough: `422`.

Request

``` code
POST /loyalty/1/redeem HTTP/1.1
Content-Type: application/json

{
  "points": 500
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "Customer 1 has fewer than 500 points.",
  "instance": "/loyalty/1/redeem",
  "status": 422,
  "title": "Not enough points"
}
```

### Case 6: customer 99

**Why:** `404`.

Request

``` code
POST /loyalty/99/earn HTTP/1.1
Content-Type: application/json

{
  "orderRef": "BK-1004",
  "amountPaise": 10000
}
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No customer 99.",
  "instance": "/loyalty/99/earn",
  "status": 404,
  "title": "Customer not found"
}
```

### Case 7: an amount of 0

**Why:** `400`.

Request

``` code
POST /loyalty/1/earn HTTP/1.1
Content-Type: application/json

{
  "orderRef": "BK-1005",
  "amountPaise": 0
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/loyalty/1/earn",
  "status": 400,
  "title": "Bad Request"
}
```

## The old upsert, on this PostgreSQL

Sent with psql to the database the captures ran against (`docs/captures/old-upsert.txt`):

``` code
ERROR:  syntax error at or near "("
LINE 1: MERGE INTO point_balances (customer_id, points) KEY (custome...
                                  ^
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                      | What happens                         | Proved by                                         |
|-------------------------------------------|--------------------------------------|---------------------------------------------------|
| First earn, second earn, under ₹100       | Row created, then added to; 0 points | `theFirstEarnCreatesTheBalanceAndTheNextAddsToIt` |
| The same order twice, in two cases        | `409`; balance unchanged             | `anOrderEarnsOnceInAnyCase`                       |
| Redeem within, above, with no balance row | `200`; `422`; `422`                  | `redeemingTakesPointsAndNeverMoreThanThere`       |
| Malformed bodies                          | `400`                                | `malformedRequestsAre400`                         |
| Unknown customer                          | `404`                                | `unknownCustomersAre404`                          |
| Bad rows written directly                 | Refused by named constraints         | `namedConstraintsHoldWithoutJava`                 |
| An earn whose caller fails after it       | Entry and balance rolled back        | `anEarnThatFailsAfterItsWritesLeavesNeither`      |
| 20 earns at once, no row yet              | All counted                          | `twentyEarnsAtOnceForANewCustomerAddUp`           |

## The trap

Plausible but wrong

Testing on H2 and shipping SQL that PostgreSQL rejects.

The trap test runs the old upsert, `MERGE INTO point_balances (customer_id, points) KEY (customer_id) VALUES (?, ?)`, in two places. On in-memory H2 in PostgreSQL mode it works: the old suite was green. On PostgreSQL 17 it is a syntax error at the column list, because PostgreSQL's MERGE is the SQL-standard one (`MERGE INTO t USING …`). The third test turns it around: H2 cannot even parse the upsert PostgreSQL needs, so code that is right for production could never have been tested on H2.

While building, each part was undone once. Putting the old MERGE back turned 5 tests red; an upsert that replaces the balance instead of adding to it, 2 (including the 20-at-once test); a redemption without the `points >= ?` condition, 1.

``` code
package com.basketo.loyalty;

import org.junit.jupiter.api.Test;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The first test written for this station. The old upsert, from the code that shipped, run on the in-memory H2 the
 * old tests used (even in its PostgreSQL compatibility mode it accepts H2's own syntax), and on the real PostgreSQL
 * production runs.
 */
class H2VersusPostgresTrapTest extends ApiTest {

    /** H2's own MERGE syntax (a column list and a KEY clause): not SQL standard, not PostgreSQL. */
    static final String OLD_UPSERT = "MERGE INTO point_balances (customer_id, points) KEY (customer_id) VALUES (?, ?)";

    static final String NEW_UPSERT = """
            INSERT INTO point_balances (customer_id, points) VALUES (?, ?)
            ON CONFLICT (customer_id) DO UPDATE SET points = point_balances.points + EXCLUDED.points RETURNING points""";

    static Connection h2() throws SQLException {
        Connection c = DriverManager.getConnection("jdbc:h2:mem:old-tests;MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE");
        try (Statement s = c.createStatement()) {
            s.execute("CREATE TABLE IF NOT EXISTS point_balances (customer_id BIGINT PRIMARY KEY, points INT NOT NULL)");
        }
        return c;
    }

    @Test
    void theOldUpsertRunsOnH2() throws SQLException {
        try (Connection c = h2(); var merge = c.prepareStatement(OLD_UPSERT)) {
            merge.setLong(1, 7);
            merge.setInt(2, 14);
            assertThat(merge.executeUpdate()).isEqualTo(1);   // green on H2: the old test suite passed
        }
    }

    @Test
    void andPostgresqlRejectsIt() {
        long customer = newCustomer();
        // PostgreSQL has a standard MERGE (MERGE INTO t USING ...), so it stops at the column list H2 allowed.
        assertThatThrownBy(() -> jdbc.sql(OLD_UPSERT).params(customer, 14).update())
                .rootCause().hasMessageContaining("syntax error at or near \"(\"");   // the first production earn after the release
    }

    @Test
    void theRightSqlForPostgresqlIsNotH2Sql() throws SQLException {
        try (Connection c = h2()) {
            assertThatThrownBy(() -> c.prepareStatement(NEW_UPSERT)).isInstanceOf(SQLException.class)
                    .hasMessageContaining("Syntax error");   // H2 cannot even parse it: it can only be tested on PostgreSQL
        }
        long customer = newCustomer();
        assertThat(jdbc.sql(NEW_UPSERT).params(customer, 14).query(Integer.class).single()).isEqualTo(14);
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

## Try it yourself: without Docker

Stop Docker and run the tests. This was done while building the station (`docs/no-docker-run.txt`):

``` code
# ./mvnw test with Docker stopped, 16 Oct 2026: every test that needs PostgreSQL is skipped, none fails, none passes
[WARNING] Tests run: 3, Failures: 0, Errors: 0, Skipped: 3 -- in com.basketo.loyalty.LoyaltyDatabaseTest
[WARNING] Tests run: 5, Failures: 0, Errors: 0, Skipped: 5 -- in com.basketo.loyalty.LoyaltyContractTest
[WARNING] Tests run: 3, Failures: 0, Errors: 0, Skipped: 3 -- in com.basketo.loyalty.H2VersusPostgresTrapTest
Tests run: 11, Failures: 0, Errors: 0, Skipped: 11
BUILD SUCCESS
```

Every test is skipped and Maven still says BUILD SUCCESS. That is honest on a laptop, and dangerous in CI: see Production.

## Troubleshooting

| You see                                     | Cause                                            | Fix                                                              |
|---------------------------------------------|--------------------------------------------------|------------------------------------------------------------------|
| Green tests, production SQL errors          | Tests on a different database than production.   | Testcontainers with production's version.                        |
| `syntax error at or near "("` on a MERGE    | H2's `MERGE ... KEY` syntax on PostgreSQL.       | `INSERT ... ON CONFLICT ... DO UPDATE`.                          |
| All tests skipped                           | Docker is not running (`disabledWithoutDocker`). | Start Docker; in CI, treat skips as failure.                     |
| A test passes alone, fails in the suite     | It depends on data another test changed.         | Each test creates its own data.                                  |
| `Could not find a valid Docker environment` | Docker stopped, without `disabledWithoutDocker`. | Start Docker, or add the annotation so tests skip with a reason. |

## Project layout

``` tree
stations/059-loyalty-points-tested-on-real-postgresql/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/basketo/loyalty/
│   ├── LoyaltyController.java   ├── LoyaltyLedger.java   └── LoyaltyApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__customers_points.sql, V2__demo_customers.sql
├── src/test/java/com/basketo/loyalty/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs (with and without Docker)
```

## Code walkthrough

In the order a request travels, then the database.

#### `src/main/java/com/basketo/loyalty/LoyaltyController.java`

Does  
Validates earn and redeem; normalises order references.

Why  
HTTP only.

Without it  
Earn called by anyone (in a shop, only the order system).

#### `src/main/java/com/basketo/loyalty/LoyaltyLedger.java`

Does  
Ledger entry plus balance change, in one transaction.

Why  
PostgreSQL's upsert: atomic, even for a customer's first points arriving twice at once.

Without it  
Lost or doubled points.

- `ON CONFLICT (customer_id) DO UPDATE SET points = point_balances.points + EXCLUDED.points` adds, it does not replace.
- `RETURNING points` gives the new balance without a second query.
- Redeem is `UPDATE ... WHERE points >= ?`: no row means not enough.

#### `src/main/resources/db/migration/V1__customers_points.sql`

Customers, balances and the ledger, with named constraints.

#### `src/main/resources/db/migration/V2__demo_customers.sql`

Asha with 120 points, Rohan with none.

#### `pom.xml`

Testcontainers and its JUnit extension; H2 for the trap test only.

#### `src/main/resources/application.yaml`

The local PostgreSQL; decimals refused for whole-number fields.

#### `src/main/java/com/basketo/loyalty/LoyaltyApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                     | Result |
|---------------|-------------------------------------------------------|--------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `LoyaltyContractTest` (5)      | pass   |
| Every station | Reproduce the failure before the fix                  | `H2VersusPostgresTrapTest` (3) | pass   |
| Database      | Rollback and constraint tests against a real database | `LoyaltyDatabaseTest` (3)      | pass   |

## How these tests are built

The whole app  
`@SpringBootTest` starts everything: controllers, transactions, Flyway, on real PostgreSQL.

The database  
`PostgresTestConfig` declares a PostgreSQL 17 container with `@ServiceConnection`: Spring connects to it, no URL anywhere.

Isolation  
No test cleans tables or relies on what another left: each makes fresh customers with `newCustomer()`.

No Docker  
`@Testcontainers(disabledWithoutDocker = true)` on the base class: skipped, with the reason, not failed and not passed.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.basketo.loyalty.LoyaltyDatabaseTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.basketo.loyalty.LoyaltyContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.basketo.loyalty.H2VersusPostgresTrapTest
[INFO] Tests run: 11, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/basketo/loyalty/H2VersusPostgresTrapTest.java`

Written first: the old upsert on H2 and on PostgreSQL, and the new one on both.

#### `src/test/java/com/basketo/loyalty/LoyaltyContractTest.java`

Earn and redeem, and every refusal.

#### `src/test/java/com/basketo/loyalty/LoyaltyDatabaseTest.java`

Named constraints, a rollback of both rows, and 20 earns at once.

#### `src/test/java/com/basketo/loyalty/ApiTest.java`

Shared setup: `@SpringBootTest`, the Docker rule, and fresh customers.

#### `src/test/java/com/basketo/loyalty/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers and `@ServiceConnection`.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/basketo/loyalty/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=BalanceChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 11 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in (Java files and one migration), all 13 tests pass (11 station tests and 2 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Balance and history

Add `GET /loyalty/{customerId}`: the balance (0 if nothing was ever earned) and the ledger, newest first. Unknown: `404`.

**Done when:** the test in `BalanceChallengeTest` passes.

Hints

- `coalesce` turns "no balance row" into 0.
- `JdbcClient` maps `order_ref` to `orderRef` by itself.

#### `challenge/BalanceChallengeTest.java`

``` code
package com.basketo.loyalty;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /loyalty/{customerId}: the balance (0 when nothing was ever earned) and the ledger, newest first,
 * as reason, delta and orderRef. Unknown customer: 404.
 */
class BalanceChallengeTest extends ApiTest {

    @Test
    void theBalanceAndItsHistory() throws Exception {
        long c = newCustomer();
        mvc.perform(get("/loyalty/{id}", c)).andExpect(status().isOk()).andExpect(content().json("{\"balance\":0,\"entries\":[]}"));
        earn(c, "BK-8001", 500_000);
        redeem(c, 20);
        mvc.perform(get("/loyalty/{id}", c)).andExpect(content().json("""
                {"customerId":%d,"balance":30,"entries":[
                 {"reason":"REDEEM","delta":-20,"orderRef":null},{"reason":"EARN","delta":50,"orderRef":"BK-8001"}]}""".formatted(c), true));
        mvc.perform(get("/loyalty/999999")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Reverse a returned order

Add `POST /loyalty/{customerId}/earn/{orderRef}/reversal`: take back that order's points once, as a REVERSE entry. Already spent: `409`. Unknown order: `404`.

**Done when:** the test in `ReversalChallengeTest` passes.

Hints

- The schema must allow a third reason, and an order with both an EARN and a REVERSE entry: a migration.
- The conditional UPDATE decides "already spent"; the unique key decides "already reversed".

#### `challenge/ReversalChallengeTest.java`

``` code
package com.basketo.loyalty;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /loyalty/{customerId}/earn/{orderRef}/reversal takes back the points an order earned (the order
 * was returned), as a REVERSE ledger entry, once. Points already spent: 409, nothing changes. Unknown order: 404.
 * The schema must allow the new entry (a migration).
 */
class ReversalChallengeTest extends ApiTest {

    @Test
    void aReturnedOrderGivesItsPointsBackOnce() throws Exception {
        long c = newCustomer();
        earn(c, "BK-9001", 500_000);   // 50
        earn(c, "BK-9002", 200_000);   // 20
        mvc.perform(post("/loyalty/{id}/earn/{order}/reversal", c, "bk-9002")).andExpect(status().isOk()).andExpect(jsonPath("$.balance").value(50));
        mvc.perform(post("/loyalty/{id}/earn/{order}/reversal", c, "BK-9002")).andExpect(status().isConflict());
        redeem(c, 45);
        mvc.perform(post("/loyalty/{id}/earn/{order}/reversal", c, "BK-9001")).andExpect(status().isConflict())
                .andExpect(jsonPath("$.title").value("Points already spent"));
        assertThat(balance(c)).isEqualTo(5);
        mvc.perform(post("/loyalty/{id}/earn/{order}/reversal", c, "BK-0000")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## When is an in-memory database fine?

List three kinds of test in your projects (a mapping function, a repository query, a whole HTTP flow). For each, would H2 do, would a mock do, or does it need the real database? What would make you change your mind?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old SQL on H2 and on PostgreSQL.
2.  Move every test to a shared PostgreSQL container with `@ServiceConnection`.
3.  Make each test create its own data.
4.  Write PostgreSQL's upsert, and test it under concurrency.

## Design alternatives and trade-offs

| Approach                                            | What it costs                                                       | Verdict                 |
|-----------------------------------------------------|---------------------------------------------------------------------|-------------------------|
| Testcontainers with production's PostgreSQL version | Docker on every machine and in CI; a few seconds to start.          | Chosen                  |
| H2 in compatibility mode                            | Fast; accepts SQL production rejects, rejects SQL production needs. | The trap                |
| A shared test database on a server                  | Tests collide with each other and with people.                      | No                      |
| Embedded PostgreSQL binaries (no Docker)            | Real PostgreSQL; one more tool to keep at the right version.        | If Docker is impossible |
| Clean tables before each test                       | Simple; tests cannot run in parallel.                               | Fine for small suites   |

## Database design

| Table            | Constraints                                                                                                         |
|------------------|---------------------------------------------------------------------------------------------------------------------|
| `point_balances` | `point_balances_customer_fk`, `point_balances_not_negative`                                                         |
| `point_entries`  | `point_entries_customer_fk`, `point_entries_reason_known`, `point_entries_sign_matches`, `point_entries_order_once` |

``` code
-- Basketo loyalty: a ledger of every change, and one balance row per customer kept in step with it.
CREATE TABLE customers (
    id   BIGINT PRIMARY KEY,
    name VARCHAR(80) NOT NULL
);

CREATE TABLE point_balances (
    customer_id BIGINT PRIMARY KEY,
    points      INT NOT NULL,
    CONSTRAINT point_balances_customer_fk FOREIGN KEY (customer_id) REFERENCES customers (id),
    CONSTRAINT point_balances_not_negative CHECK (points >= 0)
);

CREATE TABLE point_entries (
    id          BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    customer_id BIGINT      NOT NULL,
    order_ref   VARCHAR(30),
    delta       INT         NOT NULL,
    reason      VARCHAR(10) NOT NULL,
    at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT point_entries_customer_fk FOREIGN KEY (customer_id) REFERENCES customers (id),
    CONSTRAINT point_entries_reason_known CHECK (reason IN ('EARN', 'REDEEM')),
    -- An earn has an order and adds (an order under ₹100 adds 0); a redemption has no order and takes away.
    CONSTRAINT point_entries_sign_matches CHECK ((reason = 'EARN' AND order_ref IS NOT NULL AND delta >= 0) OR (reason = 'REDEEM' AND order_ref IS NULL AND delta < 0)),
    CONSTRAINT point_entries_order_once UNIQUE (customer_id, order_ref)
);
```

# 3 · Go deeper: Production

CI must not go green on skips  
Skipping without Docker is honest on a laptop. In CI it would turn "no tests ran" into a green build. Make CI fail when tests were skipped, or when Docker is missing.

Same version  
Pin the container image to production's major version (here `postgres:17-alpine`) and upgrade both together.

Speed  
One container per run, shared by every test, keeps the cost to a few seconds. Reusable containers can keep it across runs on a developer machine.

Upsert and sequences  
`ON CONFLICT DO UPDATE` still uses up identity values on conflict; gaps in ids are normal.

# 3 · Go deeper: Interview

## Interview takeaways

Why not test with H2?

Because H2 is not the database you ship to. Its compatibility modes accept syntax production rejects and lack features production has, so green tests prove little about production SQL.

What does @ServiceConnection do?

It turns a container bean into Spring's connection details: the datasource URL, user and password come from the running container, with no properties to write.

How do you keep tests independent?

Each test creates its own data (fresh ids) or resets what it uses, and never relies on the order tests run in.

What happens when Docker is missing?

With @Testcontainers(disabledWithoutDocker = true), the tests are skipped and reported as skipped. Without it, they fail. Neither is a pass.

Why is INSERT ... ON CONFLICT DO UPDATE safe under concurrency?

PostgreSQL resolves the conflict with the unique index inside one statement: concurrent upserts for the same key wait for each other and then update, instead of both inserting or one failing.

## Self-check rubric

| Area           | Meets the bar                                | Above the bar                                     |
|----------------|----------------------------------------------|---------------------------------------------------|
| Correctness    | All 11 tests pass, on PostgreSQL.            | You ran them without Docker and read the result.  |
| Testcontainers | `@ServiceConnection` and a shared container. | CI that fails on skips.                           |
| Isolation      | Fresh data per test.                         | Tests that could run in parallel.                 |
| SQL            | PostgreSQL's upsert.                         | You can explain why it is safe under concurrency. |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any test suite with a database:

- Which database, and which version, do the tests run on?
- Does any test need another test's data, or a particular order?
- What happens on a machine without Docker: skip, fail, or a lie?
- Is there SQL in the code that only one database understands, and is it tested on that one?
