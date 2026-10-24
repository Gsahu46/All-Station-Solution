# Station 102 · Ticket sale when the pool runs dry

Working Systems · 0–2 years · Core · Events · Types: Database, Operations

Spring Boot 4.1.1 · Java 25 · HikariCP · TransactionTemplate · RestClient with timeouts · Actuator and Micrometer · PostgreSQL 17 · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). Python 3 runs the test gateway in Try it yourself. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The payment gateway is simulated: a small server answers each charge (no money moves). The sales and buyers are demo data.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 10 tests.

# 1 · Understand

## The problem in real life

1.  **Sale opens**

    Tickets for India vs Australia go on sale. Thousands of fans press "Buy" at once.

2.  **Thirty seconds, then an error**

    Each order took a database connection, then called the payment gateway inside the same transaction. The gateway took a second or two. Ten slow charges held all ten connections; every other request waited 30 seconds for one and failed. The database itself was nearly idle.

3.  **The fix**

    The order is split: take the seats and commit, call the gateway with no connection held, then record the result in a second short transaction. A connection is held for milliseconds, and a request that cannot get one is told so in 2 seconds.

Never hold a database connection while you wait for someone else. A pool runs dry long before the database does.

## What are we building?

A ticket order that takes seats, charges the buyer and records the result, without holding a connection during the charge, with metrics and drills for the night of the sale.

## An everyday analogy

A bank clerk who phones head office in the middle of serving you blocks the counter for everyone behind you. A good clerk takes your form, sends you to wait while head office answers, and calls the next customer.

## How it works in 4 steps

1.  **Reserve**: one short transaction takes the seats (only if they are there) and records the order as waiting for payment.
2.  **Charge**: call the gateway with no connection held, for at most 3 seconds.
3.  **Record**: a second short transaction marks the order paid, or failed and gives the seats back.
4.  **Watch**: the pool's metrics show waiting requests and timeouts; the alerts read them.

Check yourself: why not just make the pool bigger?

A bigger pool only moves the wall: 10 or 100 connections, slow charges fill them all, and each connection costs the database memory. Holding none during the charge removes the wall.

## What this station is not

- **No real payments.** A test gateway answers.
- **No seat map.** A sale is a count of seats.
- **No reconciliation job.** A timed-out charge's seats are given back (a shortcut, see Code).

## Key terms

| Term                   | Simple meaning                                                                                 | Everyday example                                           | In this project              |
|------------------------|------------------------------------------------------------------------------------------------|------------------------------------------------------------|------------------------------|
| **Connection pool**    | A few ready database connections the app lends to requests and takes back.                     | A bank with ten counters.                                  | HikariCP, 10                 |
| **Connection timeout** | How long a request waits for a free connection before giving up.                               | How long you stand in the queue for a counter.             | 2 s (Hikari's default: 30 s) |
| **Transaction**        | Work on the database that commits or rolls back together; it holds a connection until it ends. | Your time at the counter.                                  | `TransactionTemplate`        |
| **Remote call**        | A request to another system over the network: slow, sometimes very slow.                       | The clerk phoning head office mid-transaction.             | the payment gateway          |
| **Pool metrics**       | Numbers the pool publishes: waiting requests, timeouts, how long connections are held.         | The token display over the counters.                       | `hikaricp.connections.*`     |
| **Bulkhead**           | A limit on how many requests may wait on one slow thing.                                       | Only three customers allowed at the foreign-exchange desk. | challenge 2                  |

# 2 · Build: Spec

## Business problem

**SeatSure** (a fictional ticketing site): during a cricket ticket sale every request waits 30 seconds, then fails, while the database is idle.

## Acceptance criteria

Demo rules: 10 connections, 2 s to get one; 1 to 6 seats per order; the gateway gets 1 s to connect and 3 s to answer.

1.  **Given** seats and a paying buyer, **then** `201`, PAID, the amount in paise and the charge id.
2.  **Given** a declined payment, a gateway error or a gateway slower than 3 s, **then** `402`, `502` or `504`, and the seats are given back.
3.  **Given** many orders while the gateway is slow, **then** no connection is held during charges, and other requests answer at once.
4.  **Given** no free connection, **then** `503` with `Retry-After` within the pool's timeout, not after 30 s.
5.  **Given** too few seats, an unknown sale or bad input, **then** `409`, `404`, `400`, and nothing charged.

## Requirements

- No transaction is open during a remote call.
- Never more seats sold than there are, in the database too.
- Pool metrics published; drills for the two failures that matter.

## Learning objectives

- Size a Hikari pool and set its connection timeout.
- Split a request into short transactions around a remote call.
- Put timeouts on every remote call.
- Read pool metrics and write alerts and a runbook from them.
- Prove pool behaviour with concurrent tests and drills.

# 2 · Build: API contract

## Endpoints

| Method | Path                                       | Purpose                                        |
|--------|--------------------------------------------|------------------------------------------------|
| `POST` | `/sales/{id}/orders`                       | Buy 1 to 6 seats: `{buyer, seats}`.            |
| `GET`  | `/sales/{id}`                              | Capacity, sold and left.                       |
| `GET`  | `/actuator/metrics/hikaricp.connections.*` | The pool's metrics, for dashboards and alerts. |

## Status codes

| Status    | When                                                |
|-----------|-----------------------------------------------------|
| 201       | Paid                                                |
| 400       | No buyer; seats not 1 to 6                          |
| 402       | The payment was declined                            |
| 404       | No such sale                                        |
| 409       | Not enough seats left                               |
| 502 / 504 | The gateway failed / did not answer within 3 s      |
| 503       | No database connection within 2 s; `Retry-After: 5` |

## Captured examples

Captured with curl from the running app on 24 Oct 2026, in this order, against `docs/test-gateway.py`, a small simulated gateway. `Date`, connection and standard security headers are left out.

### Case 1: two seats for the big match

**Why:** `201`, paid; 2 × ₹1,500 = 300000 paise.

Request

``` code
POST /sales/1/orders HTTP/1.1
Content-Type: application/json

{
  "buyer": "Priya Nair",
  "seats": 2
}
```

Response

``` code
HTTP/1.1 201 
Location: /orders/1
Content-Type: application/json

{
  "id": 1,
  "saleId": 1,
  "buyer": "Priya Nair",
  "seats": 2,
  "amountPaise": 300000,
  "status": "PAID",
  "chargeId": "ch_1"
}
```

### Case 2: the sale afterwards

**Why:** two seats fewer.

Request

``` code
GET /sales/1 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 92

{
  "id": 1,
  "name": "India vs Australia, Wankhede, day 1",
  "capacity": 30000,
  "sold": 2,
  "left": 29998
}
```

### Case 3: all four seats of the small match

**Why:** `201`.

Request

``` code
POST /sales/2/orders HTTP/1.1
Content-Type: application/json

{
  "buyer": "Ravi Kumar",
  "seats": 4
}
```

Response

``` code
HTTP/1.1 201 
Location: /orders/2
Content-Type: application/json

{
  "id": 2,
  "saleId": 2,
  "buyer": "Ravi Kumar",
  "seats": 4,
  "amountPaise": 120000,
  "status": "PAID",
  "chargeId": "ch_2"
}
```

### Case 4: one more

**Why:** `409`; nothing charged.

Request

``` code
POST /sales/2/orders HTTP/1.1
Content-Type: application/json

{
  "buyer": "Asha Rao",
  "seats": 1
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Not enough seats left.",
  "instance": "/sales/2/orders",
  "status": 409,
  "title": "Conflict"
}
```

### Case 5: seven seats

**Why:** `400`.

Request

``` code
POST /sales/1/orders HTTP/1.1
Content-Type: application/json

{
  "buyer": "Asha Rao",
  "seats": 7
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/sales/1/orders",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 6: no such sale

**Why:** `404`.

Request

``` code
POST /sales/9/orders HTTP/1.1
Content-Type: application/json

{
  "buyer": "Asha Rao",
  "seats": 1
}
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No such sale.",
  "instance": "/sales/9/orders",
  "status": 404,
  "title": "Not Found"
}
```

## The drill, captured

`docs/capture.sh` makes the gateway hang for 10 s, sends 20 orders at once (twice the pool), and reads the sale while they wait. Status codes of the 20, and the slowest one:

``` code
504 x 20
slowest: 3.1 s
```

``` code
GET /sales/1 during the hang: 200 in 0.008001 s
```

### Case 7: the sale after the drill

**Why:** the 20 failed orders gave their seats back.

Request

``` code
GET /sales/1 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 92

{
  "id": 1,
  "name": "India vs Australia, Wankhede, day 1",
  "capacity": 30000,
  "sold": 2,
  "left": 29998
}
```

And the pool's metrics at the end:

``` code
hikaricp.connections.timeout = 0.0
hikaricp.connections.usage: count = 49 , max = 85.0 ms
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                           | What happens                                           | Proved by                                                   |
|------------------------------------------------|--------------------------------------------------------|-------------------------------------------------------------|
| The old way: 16 fans, pool 4, a 0.7 s gateway  | Some get no connection; pool timeouts rise             | `theOldWayHoldsAConnectionThroughEachChargeAndFansTimeOut`  |
| The API, the same 16                           | All paid; no pool timeouts                             | `theApiHoldsAConnectionForMillisecondsAndEveryFanGetsASeat` |
| A paid order                                   | `201`, amount, charge id, Idempotency-Key              | `aPaidOrderTakesItsSeats`                                   |
| A declined payment                             | `402`, order FAILED, seats back                        | `aDeclinedPaymentGivesTheSeatsBack`                         |
| 0 or 7 seats, no buyer, no sale, too few seats | `400`, `404`, `409`; nothing charged                   | `badOrdersAre400UnknownSales404AndASoldOutSale409`          |
| Rules written by plain SQL                     | Refused by named constraints                           | `saleAndOrderRulesHoldWithoutJava`                          |
| An order that cannot be recorded               | No seats taken                                         | `anOrderThatCannotBeRecordedTakesNoSeats`                   |
| Drill: the gateway hangs                       | `504` after 1 s each; reads answer at once; seats back | `aHangingGatewayIsCutOffAndTheDatabaseStaysFree`            |
| Drill: the pool is held by something else      | `503` after about 1 s, logged; recovers                | `withNoConnectionFreeTheAnswerIs503AfterOneSecondNotThirty` |
| The alerts' metrics                            | Published                                              | `theMetricsTheAlertsReadArePublished`                       |

## The trap

Plausible but wrong

Calling remote services inside a transaction while holding a connection.

- **The old way.** One `@Transactional` method takes the seats, charges the buyer and records the result. Sixteen fans at once, a pool of four, a gateway that takes 0.7 s: four charges at a time, each holding a connection, and the fans still waiting after 1 s get none. `hikaricp.connections.timeout` rises.
- **The API.** The same sixteen: every one paid, and no request waited too long for a connection, because none was held during a charge.

While building, each part was undone once: one transaction around the order turned 3 tests red; no read timeout 1; no seat check in the UPDATE 1; seats kept after a decline 1; seats kept after a gateway failure 1; no `503` for an empty pool 1; no Idempotency-Key 1; timeouts taken for other errors 1.

``` code
package com.seatsure.sales;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static com.seatsure.sales.TestGateway.GATEWAY;
import static org.assertj.core.api.Assertions.assertThat;

/** The sale opens: sixteen fans at once, a gateway that takes 0.7 s per charge, a pool of four. Written first. */
@Import(PoolExhaustionTrapTest.OldWay.class)
class PoolExhaustionTrapTest extends ApiTest {

    /** The old way: one transaction around everything, so a connection is held while the gateway thinks. */
    @TestConfiguration
    static class OldWay {
        @Bean
        OldOrders oldOrders(TicketOrders orders, PaymentGateway gateway, JdbcClient jdbc) {
            return new OldOrders(orders, gateway, jdbc);
        }
    }

    static class OldOrders {
        private final TicketOrders orders;
        private final PaymentGateway gateway;
        private final JdbcClient jdbc;

        OldOrders(TicketOrders orders, PaymentGateway gateway, JdbcClient jdbc) {
            this.orders = orders;
            this.gateway = gateway;
            this.jdbc = jdbc;
        }

        @Transactional
        public String place(long saleId, String buyer, int seats) {
            TicketOrders.Order pending = orders.reserve(saleId, buyer, seats);
            PaymentGateway.Charge charge = gateway.charge(pending.id(), pending.amountPaise());
            jdbc.sql("UPDATE orders SET status = 'PAID', charge_id = ? WHERE id = ?").params(charge.chargeId(), pending.id()).update();
            return "PAID";
        }
    }

    @Autowired
    OldOrders oldOrders;

    List<String> sixteenFansAtOnce(Callable<String> buy) throws Exception {
        CountDownLatch open = new CountDownLatch(1);
        List<Future<String>> fans = new ArrayList<>();
        try (var threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 16; i++) {
                fans.add(threads.submit(() -> {
                    open.await();
                    try {
                        return buy.call();
                    } catch (Exception e) {
                        return e.getClass().getSimpleName();
                    }
                }));
            }
            open.countDown();
        }
        return fans.stream().map(Future::resultNow).toList();
    }

    @Test
    void theOldWayHoldsAConnectionThroughEachChargeAndFansTimeOut() throws Exception {
        GATEWAY.delayMillis = 700;
        double before = poolTimeouts();
        List<String> outcomes = sixteenFansAtOnce(() -> oldOrders.place(1, "fan", 1));
        // Four charges at a time, 0.7 s each: the fans still waiting after 1 s get no connection at all.
        assertThat(outcomes).contains("CannotCreateTransactionException");   // no connection within 1 s
        assertThat(outcomes.stream().filter("PAID"::equals).count()).isLessThan(16);
        assertThat(poolTimeouts()).isGreaterThan(before);
    }

    @Test
    void theApiHoldsAConnectionForMillisecondsAndEveryFanGetsASeat() throws Exception {
        GATEWAY.delayMillis = 700;
        double before = poolTimeouts();
        List<String> outcomes = sixteenFansAtOnce(() -> String.valueOf(order(1, "fan", 1).andReturn().getResponse().getStatus()));
        assertThat(outcomes).containsOnly("201");
        assertThat(sold(1)).isEqualTo(16);
        assertThat(poolTimeouts()).isEqualTo(before);
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                                           | Check with          |
|----------|-------------------------------------------------------------------|---------------------|
| JDK      | 25 (recommended). JDK 21 also works, see below                    | `java -version`     |
| Docker   | Docker Desktop (Windows, macOS) or Docker Engine (Linux), running | `docker info`       |
| Python 3 | Only for the test gateway in Try it yourself                      | `python3 --version` |
| Maven    | Not needed: the project ships the Maven wrapper                   |                     |

**macOS / Linux**

``` code
docker compose up -d        # PostgreSQL 17 on localhost:5432
python3 docs/test-gateway.py 9099 &   # the simulated payment gateway
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 10 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
Start-Process python -ArgumentList 'docs/test-gateway.py','9099'
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Make the gateway hang, then watch the pool while orders wait:

``` code
curl -d '{"seconds":10}' http://127.0.0.1:9099/delay
for i in $(seq 1 20); do curl -s -o /dev/null -w '%{http_code}\n' -H 'Content-Type: application/json' -d '{"buyer":"fan","seats":1}' localhost:8080/sales/1/orders & done
curl localhost:8080/actuator/metrics/hikaricp.connections.pending
```

Every order ends `504` after 3 s; `pending` stays 0. Then put the transaction back around the whole order (the Review tab's version) and try again.

## Troubleshooting

| You see                                                     | Cause                                                        | Fix                                                                                |
|-------------------------------------------------------------|--------------------------------------------------------------|------------------------------------------------------------------------------------|
| Requests fail after exactly 30 s                            | Hikari's default connection timeout; the pool is empty.      | Find what holds connections (`hikaricp.connections.usage`); set a shorter timeout. |
| `NumberFormatException: For input string: "2s"` at start-up | Hikari properties take milliseconds as numbers.              | `connection-timeout: 2000`.                                                        |
| Connections held for seconds                                | A remote call, a file, or a slow query inside a transaction. | Move it out; keep transactions short.                                              |

## Project layout

``` tree
stations/102-ticket-sale-when-the-pool-runs-dry/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/seatsure/sales/
│   ├── SaleController.java   ├── TicketOrders.java   ├── PaymentGateway.java   └── SalesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__sales_and_orders.sql, V2__demo_sales.sql
├── src/test/java/com/seatsure/sales/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, test gateway, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the configuration and the database.

#### `src/main/java/com/seatsure/sales/SaleController.java`

Does  
The endpoints, and the empty pool.

Why  
Validates the order; turns "no connection within the pool's timeout" into `503` with `Retry-After`, logged at ERROR.

Without it  
A 500 after 30 s; nobody knowing why.

- Inside a transaction, the pool's timeout arrives as `CannotCreateTransactionException`; outside one, as `CannotGetJdbcConnectionException`. Both are handled. Found while building.

#### `src/main/java/com/seatsure/sales/TicketOrders.java`

Does  
The order in three short transactions.

Why  
Reserve and commit; charge with nothing open; record PAID, or FAILED and give the seats back.

Without it  
A connection held for the length of a charge.

- Shortcut: a charge that timed out may still have gone through. Here the seats are given back; production asks the gateway about the order's Idempotency-Key first, or keeps the order pending until a reconciliation job does.

#### `src/main/java/com/seatsure/sales/PaymentGateway.java`

Does  
The gateway client.

Why  
Sends the order id as Idempotency-Key; tells a decline, a timeout and other failures apart.

Without it  
A slow gateway taken for a broken one.

- A timeout is recognised by its cause (`HttpTimeoutException`), not by the words of its message: the first version looked for "timed out" and called every timeout a 502. Found while building.

#### `src/main/java/com/seatsure/sales/SalesApplication.java`

Does  
The gateway's HTTP client.

Why  
Connect 1 s, read 3 s.

Without it  
A request thread waiting for ever.

#### `src/main/resources/application.yaml`

Does  
The pool.

Why  
10 connections, 2 s to get one; metrics exposed.

Without it  
Hikari's default 30 s wait.

- `spring.datasource.hikari.*` binds straight to Hikari's setters: `connection-timeout` is milliseconds as a number. `2s` stops the app at start-up. Found while building.

#### `src/main/resources/db/migration/V1__sales_and_orders.sql`

Does  
Sales and orders.

Why  
Named constraints for seats, amounts and states.

Without it  
Overselling from any writer.

#### `src/main/resources/db/migration/V2__demo_sales.sql`

A big match and a small one.

#### `compose.yaml`

PostgreSQL 17 for running the app.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                  | Test class                                        | Result |
|---------------|--------------------------------------------------------------|---------------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                     | `TicketOrderContractTest` (3)                     | pass   |
| Every station | Reproduce the failure before the fix                         | `PoolExhaustionTrapTest` (2)                      | pass   |
| Database      | Rollback and constraint tests against a real database        | `TicketDatabaseTest` (2)                          | pass   |
| Operations    | Metric, alert, rollback, runbook; a controlled failure drill | `OperationsDrillTest` (3), and the Production tab | pass   |

A pool of 4, 1 s to get a connection, and a test gateway with a 1 s limit: a full pool and a hanging gateway are reached in a second instead of thirty. Concurrency is real: sixteen threads released together.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.seatsure.sales.OperationsDrillTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.seatsure.sales.TicketOrderContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.seatsure.sales.TicketDatabaseTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.seatsure.sales.PoolExhaustionTrapTest
[INFO] Tests run: 10, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/seatsure/sales/PoolExhaustionTrapTest.java`

Written first: the old one-transaction order against the API, sixteen fans at once.

#### `src/test/java/com/seatsure/sales/TicketOrderContractTest.java`

Paid, declined, bad and unknown orders.

#### `src/test/java/com/seatsure/sales/TicketDatabaseTest.java`

Named constraints with plain SQL; a rollback.

#### `src/test/java/com/seatsure/sales/OperationsDrillTest.java`

The drills: a hanging gateway, an empty pool; the metrics.

#### `src/test/java/com/seatsure/sales/TestGateway.java`

A gateway that answers when, and how, the test says.

#### `src/test/java/com/seatsure/sales/ApiTest.java`

Shared setup: the small pool, the gateway's address, fresh sales.

#### `src/test/java/com/seatsure/sales/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/seatsure/sales/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=OrderOutcomeMetricChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 10 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 13 tests pass (10 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## How did the orders end?

The pool's metrics say whether the database is coping; add one that says how orders end: a counter `ticket.orders` tagged `outcome` = paid, declined, gateway_timeout, gateway_error or no_seats.

**Done when:** both tests in `OrderOutcomeMetricChallengeTest` pass.

Hints

- Inject `MeterRegistry`; `counter(name, "outcome", value).increment()` where each path ends.
- Keep tag values few and fixed: never a buyer or an order id.

#### `challenge/OrderOutcomeMetricChallengeTest.java`

``` code
package com.seatsure.sales;

import org.junit.jupiter.api.Test;

import static com.seatsure.sales.TestGateway.GATEWAY;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: the pool's metrics say the database is fine or not; this one says how orders end. A counter
 * ticket.orders tagged outcome = paid, declined, gateway_timeout, gateway_error or no_seats, published at /actuator/metrics.
 */
class OrderOutcomeMetricChallengeTest extends ApiTest {

    double outcome(String name) {
        var c = metrics.find("ticket.orders").tag("outcome", name).counter();
        return c == null ? 0 : c.count();
    }

    @Test
    void everyOrderIsCountedByHowItEnded() throws Exception {
        double paid = outcome("paid"), declined = outcome("declined"), noSeats = outcome("no_seats");
        order(2, "Priya Nair", 4).andExpect(status().isCreated());
        order(2, "Ravi Kumar", 1).andExpect(status().isConflict());
        GATEWAY.status = 402;
        order(1, "Ravi Kumar", 1).andExpect(status().isPaymentRequired());
        assertThat(outcome("paid")).isEqualTo(paid + 1);
        assertThat(outcome("no_seats")).isEqualTo(noSeats + 1);
        assertThat(outcome("declined")).isEqualTo(declined + 1);
        mvc.perform(get("/actuator/metrics/ticket.orders")).andExpect(status().isOk()).andExpect(jsonPath("$.name").value("ticket.orders"));
    }

    @Test
    void aHangingGatewayIsCountedAsATimeout() throws Exception {
        double before = outcome("gateway_timeout");
        GATEWAY.delayMillis = 2_000;
        order(1, "Priya Nair", 1).andExpect(status().isGatewayTimeout());
        assertThat(outcome("gateway_timeout")).isEqualTo(before + 1);
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## A bulkhead for the gateway

No connection is held during a charge, but a request thread is. Let at most `seatsure.payments.max-concurrent` charges wait on the gateway at once (4 in the test); the next order is refused at once with `503` and its seats are given back.

**Done when:** the test in `GatewayBulkheadChallengeTest` passes.

Hints

- A `Semaphore` with `tryAcquire()`: refuse instead of queueing.
- Release it in a `finally`, or one exception leaks a place for good.
- A generous default (100) keeps normal days unaffected.

#### `challenge/GatewayBulkheadChallengeTest.java`

``` code
package com.seatsure.sales;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static com.seatsure.sales.TestGateway.GATEWAY;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: no connection is held while the gateway thinks, but a request thread still is. A bulkhead lets at
 * most seatsure.payments.max-concurrent charges wait on the gateway (4 in this test); the next order is refused at
 * once with 503, and its seats are given back, instead of one more thread hanging for the full timeout.
 */
@TestPropertySource(properties = "seatsure.payments.max-concurrent=4")
class GatewayBulkheadChallengeTest extends ApiTest {

    @Test
    void beyondTheLimitOrdersAreRefusedAtOnce() throws Exception {
        GATEWAY.delayMillis = 3_000;   // hangs past the 1 s limit
        CountDownLatch open = new CountDownLatch(1);
        List<Future<Integer>> fans = new ArrayList<>();
        try (var threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 8; i++) {
                fans.add(threads.submit(() -> {
                    open.await();
                    return order(1, "fan", 1).andReturn().getResponse().getStatus();
                }));
            }
            open.countDown();
        }
        assertThat(fans).extracting(Future::resultNow).filteredOn(s -> s == 504).hasSize(4);
        assertThat(fans).extracting(Future::resultNow).filteredOn(s -> s == 503).hasSize(4);
        assertThat(GATEWAY.idempotencyKeys).hasSize(4);   // the refused four never reached the gateway
        assertThat(sold(1)).isZero();

        GATEWAY.delayMillis = 0;
        order(1, "fan", 1).andExpect(status().isCreated());   // places freed again
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## The final, ten times bigger

The World Cup final sale expects ten times the traffic, on eight servers against one PostgreSQL that allows 200 connections. Work out the pool per server, what happens when the gateway slows to 5 s, and where a queue (a virtual waiting room) belongs. Which number would you alert on first, and at what value?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the one-transaction order, sixteen at once, a small pool.
2.  Split the order into reserve, charge (nothing open), record.
3.  Timeouts on the gateway; a short pool timeout and a `503` for it.
4.  Metrics, alerts and drills.

## Design alternatives and trade-offs

| Approach                                  | What it costs                                              | Verdict                |
|-------------------------------------------|------------------------------------------------------------|------------------------|
| Short transactions around the remote call | Two writes per order; a pending state to handle.           | Chosen                 |
| One transaction around everything         | A connection per waiting charge: the pool empties.         | The trap               |
| A bigger pool                             | More database memory; the wall moves, it does not go away. | Not a fix              |
| Charge asynchronously (queue, webhook)    | The buyer waits for a callback; more moving parts.         | For very slow gateways |
| Hikari's default 30 s timeout             | Users wait 30 s for an error.                              | Shorten it             |

## Database design

| Object                                         | What                              | Why                                                 |
|------------------------------------------------|-----------------------------------|-----------------------------------------------------|
| `sales_sold_range`                             | CHECK sold BETWEEN 0 AND capacity | No overselling, no negative counts, for any writer. |
| `orders_seats_range`, `orders_amount_positive` | CHECKs                            | 1 to 6 seats; a real amount.                        |
| `orders_status`, `orders_paid_has_charge`      | CHECKs                            | Known states; paid exactly when a charge id exists. |

**Transaction boundaries:** reserve (seats and pending order) commits on its own; no transaction is open during the charge; the outcome (paid, or failed with seats back) commits on its own.

``` code
-- A sale: seats to sell and how many are taken. "Never more taken than there are" is checked here too.
CREATE TABLE sales (
    id          bigint PRIMARY KEY,
    name        text   NOT NULL,
    capacity    int    NOT NULL,
    sold        int    NOT NULL DEFAULT 0,
    price_paise bigint NOT NULL,
    CONSTRAINT sales_sold_range CHECK (sold BETWEEN 0 AND capacity),
    CONSTRAINT sales_price_positive CHECK (price_paise > 0)
);

CREATE TABLE orders (
    id           bigserial   PRIMARY KEY,
    sale_id      bigint      NOT NULL REFERENCES sales,
    buyer        text        NOT NULL,
    seats        int         NOT NULL,
    amount_paise bigint      NOT NULL,
    status       text        NOT NULL,
    charge_id    text,
    created_at   timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT orders_seats_range CHECK (seats BETWEEN 1 AND 6),
    CONSTRAINT orders_amount_positive CHECK (amount_paise > 0),
    CONSTRAINT orders_status CHECK (status IN ('PENDING_PAYMENT', 'PAID', 'FAILED')),
    CONSTRAINT orders_paid_has_charge CHECK ((status = 'PAID') = (charge_id IS NOT NULL))
);
```

# 3 · Go deeper: Production

## Operations

Metrics  
`hikaricp.connections.pending` (requests waiting for a connection), `hikaricp.connections.timeout` (requests that gave up), `hikaricp.connections.usage` (how long connections are held). With challenge 1, `ticket.orders{outcome}`.

Alerts  
Page when `timeout` rises at all during a sale, or `pending` stays above 0 for 1 minute. Warn when the 99th percentile of `usage` passes 100 ms: something is holding connections. (Starting points; tune them on real traffic.)

Rollback  
No data shape changes in this release: rolling back is redeploying the previous version. If a release puts a remote call back inside a transaction, `usage` jumps from milliseconds to seconds: roll back first, investigate after.

## Runbook: "orders are failing during the sale"

1.  Look at the status codes. `503`s: the pool is empty. `504`s: the gateway is slow. `409`s: sold out, not an incident.
2.  For `503`s: check `hikaricp.connections.usage`. Connections held for seconds mean a slow query or a remote call inside a transaction; the ERROR line "No database connection within the pool's timeout" marks each refusal.
3.  For `504`s: check the gateway's status page; reads and other pages should still answer at once. If they do not, connections are being held after all: see step 2.
4.  Tell fans to retry: the `503` says `Retry-After: 5`. Never raise the pool to fix a slow gateway.

## Failure drills

1.  **Gateway hangs.** Make the test gateway wait 10 s (`POST /delay`), send 20 orders at once: all `504` after 3 s, `GET /sales/1` answers at once, `timeout` stays 0. (Captured on the API contract tab.)
2.  **Pool held.** Take every connection from outside the app (a long query, or a test holding them): orders get `503` after 2 s, the ERROR line appears, and orders work again once the connections are released.

Both drills run on every build as `OperationsDrillTest` (3 tests, passing in `docs/test-run.txt`).

## Real-world considerations

Pool size  
Start small: connections ≈ cores × 2 on the database, divided across servers. Eight servers × 10 = 80 connections.

Virtual threads  
They make waiting threads cheap, not connections: the pool is still the limit.

Leak detection  
`leak-detection-threshold` logs a stack trace when a connection is held too long: useful in staging.

# 3 · Go deeper: Interview

## Interview takeaways

Why do requests time out while the database is idle?

The connection pool is empty: every connection is held by a request doing something else (here, waiting on a remote call).

What does Hikari's connection timeout do?

How long a request waits for a free connection before an exception. The default 30 s is far too long for a web request.

How do you call a payment gateway safely from an order?

Commit the reservation, call it with no transaction open and with timeouts, then record the result in a new short transaction.

Is a bigger pool the fix?

No: the slow calls fill any size, and connections cost database memory.

Which metrics show this problem?

Pending requests and timeouts on the pool, and how long connections are held.

How do you test it?

A small pool, a slow fake gateway, and many concurrent requests: count the pool timeouts.

## Self-check rubric

| Area         | Meets the bar      | Above the bar                                                          |
|--------------|--------------------|------------------------------------------------------------------------|
| Correctness  | All 10 tests pass. | You ran the flawed version and explained each failure.                 |
| Transactions | Short ones.        | No transaction during any remote call, with the pending state handled. |
| Timeouts     | On the gateway.    | On the gateway and the pool, each with an honest answer to the user.   |
| Operations   | Metrics exposed.   | Alerts, a runbook and drills that run on every build.                  |

# 3 · Go deeper: Review

## The pull request

A teammate "simplifies" the order: one `@Transactional` method, "so if anything fails, everything rolls back, seats included, and the release code can go". Read the file and list every problem before opening the findings.

#### `review/TicketOrders.java`

``` code
package com.seatsure.sales;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.ErrorResponseException;

import java.util.Optional;

/**
 * An order: take the seats, charge the buyer, record the outcome.
 */
@Service
class TicketOrders {

    record Order(long id, long saleId, String buyer, int seats, long amountPaise, String status, String chargeId) {
    }

    record Sale(long id, String name, int capacity, int sold) {
    }

    private final JdbcClient jdbc;
    private final TransactionTemplate tx;
    private final PaymentGateway gateway;

    TicketOrders(JdbcClient jdbc, PlatformTransactionManager transactions, PaymentGateway gateway) {
        this.jdbc = jdbc;
        this.tx = new TransactionTemplate(transactions);
        this.gateway = gateway;
    }

    /** One transaction: if anything fails, everything rolls back, seats included. No release code needed. */
    @Transactional
    public Order place(long saleId, String buyer, int seats) {
        Order pending = reserve(saleId, buyer, seats);
        PaymentGateway.Charge charge;
        try {
            charge = gateway.charge(pending.id(), pending.amountPaise());
        } catch (PaymentGateway.Declined declined) {
            throw problem(HttpStatus.PAYMENT_REQUIRED, declined.getMessage());
        } catch (PaymentGateway.Unavailable down) {
            throw problem(down.timedOut ? HttpStatus.GATEWAY_TIMEOUT : HttpStatus.BAD_GATEWAY, down.getMessage());
        }
        jdbc.sql("UPDATE orders SET status = 'PAID', charge_id = ? WHERE id = ?").params(charge.chargeId(), pending.id()).update();
        return find(pending.id()).orElseThrow();
    }

    /** Takes the seats only if they are there, in one statement, and records the order as waiting for payment. */
    Order reserve(long saleId, String buyer, int seats) {
        Optional<Long> price = jdbc.sql("UPDATE sales SET sold = sold + ? WHERE id = ? AND sold + ? <= capacity RETURNING price_paise")
                .params(seats, saleId, seats).query(Long.class).optional();
        if (price.isEmpty()) {
            throw sale(saleId).isPresent() ? problem(HttpStatus.CONFLICT, "Not enough seats left.") : problem(HttpStatus.NOT_FOUND, "No such sale.");
        }
        long id = jdbc.sql("INSERT INTO orders (sale_id, buyer, seats, amount_paise, status) VALUES (?, ?, ?, ?, 'PENDING_PAYMENT') RETURNING id")
                .params(saleId, buyer, seats, price.get() * seats).query(Long.class).single();
        return find(id).orElseThrow();
    }

    void release(Order order) {
        jdbc.sql("UPDATE orders SET status = 'FAILED' WHERE id = ? AND status = 'PENDING_PAYMENT'").param(order.id()).update();
        jdbc.sql("UPDATE sales SET sold = sold - ? WHERE id = ?").params(order.seats(), order.saleId()).update();
    }

    Optional<Order> find(long id) {
        return jdbc.sql("SELECT id, sale_id, buyer, seats, amount_paise, status, charge_id FROM orders WHERE id = ?").param(id).query(Order.class).optional();
    }

    Optional<Sale> sale(long id) {
        return jdbc.sql("SELECT id, name, capacity, sold FROM sales WHERE id = ?").param(id).query(Sale.class).optional();
    }

    static ErrorResponseException problem(HttpStatus status, String detail) {
        return new ErrorResponseException(status, ProblemDetail.forStatusAndDetail(status, detail), null);
    }
}
```

## Findings

1A connection held through every charge

"One transaction: if anything fails, everything rolls back. No release code needed": true, and while the gateway thinks, the order holds a database connection. On the night of the sale, slow charges hold the whole pool, and every other request, even a read, waits for one.

**Test evidence:** `theApiHoldsAConnectionForMillisecondsAndEveryFanGetsASeat` and `aHangingGatewayIsCutOffAndTheDatabaseStaysFree` fail.

2A declined order vanishes

The rollback also removes the order row: there is no record that the buyer tried and was declined, nothing for support to look up, nothing to count.

**Test evidence:** `aDeclinedPaymentGivesTheSeatsBack` fails: there is no FAILED order.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class                | Fixed version | Flawed version |
|---------------------------|---------------|----------------|
| `TicketDatabaseTest`      | 2 / 2         | 2 / 2          |
| `OperationsDrillTest`     | 3 / 3         | 2 / 3          |
| `PoolExhaustionTrapTest`  | 2 / 2         | 1 / 2          |
| `TicketOrderContractTest` | 3 / 3         | 2 / 3          |

With a fast gateway and a few buyers, the flawed version is correct and even simpler. It fails only on the one night that matters: the sale.
