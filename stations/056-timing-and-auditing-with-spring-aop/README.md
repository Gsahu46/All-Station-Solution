# Station 056 · Timing and auditing with Spring AOP

Working Systems · 0–2 years · Core · Payments · Types: Database

Spring Boot 4.1.1 · Java 25 · Spring AOP (spring-boot-starter-aspectj) · custom annotation · @Around advice · @Transactional · JdbcClient · PostgreSQL 17 · Flyway · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Merchants, balances and payouts are demo data, not Paysetu's. A payout is a record in the payouts table: no bank is called and no money moves.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 12 tests.

# 1 · Understand

## The problem in real life

1.  **120 copies**

    Paysetu's services each started a timer, ran, then wrote an audit row, by hand. The copies drifted: some forgot failures, some forgot the audit.

2.  **Half missing**

    A compliance review found that half the money-moving methods left no audit trail at all.

3.  **The fix, and its limits**

    One @Audited annotation and one aspect replace every copy. Then the team learned where Spring's aspects cannot reach: calls inside the same class, final methods, private methods.

Write the shared behaviour once, and know exactly which calls it can see.

## What are we building?

`POST /payouts` pays a merchant's balance out to a bank account (a record). Every call, accepted or refused, leaves one audit event with its outcome and duration, readable at `GET /audit-events`. The payout code has no timing or audit lines: one annotation does it.

## An everyday analogy

A bank branch where every counter must log each transaction. Instead of every clerk keeping their own notebook (and some forgetting), a supervisor stands at the entrance to each counter and logs everyone who goes up to it. A clerk who walks to the next counter through the back door is not logged: the supervisor only sees the front.

## How it works in 4 steps

1.  **Spring sees** `@Audited` on a bean's method and wraps the bean in a proxy.
2.  **A call from another bean** reaches the proxy; the aspect starts a timer.
3.  **The real method runs**, inside its transaction.
4.  **The aspect writes** one event, SUCCESS or FAILURE, and passes the result or the exception on unchanged.

Check yourself: why is a method called with `this.monthly()` not audited?

The aspect lives in the proxy. `this` is the real object behind it, so the call never passes the proxy. The same is true for `@Transactional` (station 055).

## What this station is not

- **No real payouts.** Records only.
- **No metrics system.** Durations go to the audit table and the log.
- **No login.** Who did it is challenge 2.

## Key terms

| Term                      | Simple meaning                                                | Everyday example                               | In this project               |
|---------------------------|---------------------------------------------------------------|------------------------------------------------|-------------------------------|
| **Cross-cutting concern** | Something many methods need, unrelated to what each one does. | Every shop till printing a receipt.            | Timing, audit                 |
| **Aspect**                | A class that holds code to run around many methods.           | The receipt printer attached to every till.    | `AuditAspect`                 |
| **Pointcut**              | Which methods the aspect applies to.                          | "Every till marked with a sticker".            | `@annotation(audited)`        |
| **Advice**                | The code that runs: before, after, or around the method.      | Print the receipt after the sale.              | `@Around`                     |
| **Custom annotation**     | A label you invent and put on methods.                        | The sticker on the till.                       | `@Audited`                    |
| **Proxy**                 | The object Spring puts in front of a bean to run the advice.  | A cashier who stands between you and the till. | CGLIB subclass of the service |

# 2 · Build: Spec

## Business problem

**Paysetu** (a fictional payments company) must be able to show who asked for every payout, when, and with what result. The hand-written audit code was missing from half the methods that move money.

## Acceptance criteria

1.  **Given** a ₹10,000 payout from Chaiwala Traders (₹50,000), **then** `201`, balance ₹40,000, and one SUCCESS event with subject 1 and a duration.
2.  **Given** a ₹500 payout from Desi Spices (₹200), **then** `422`, balance unchanged, and one FAILURE event: "Not enough balance".
3.  **Given** a payout the database refuses after the debit, **then** the debit is rolled back and the FAILURE event is still there.
4.  **Given** any event, **then** it never contains the account number.
5.  **Given** a malformed body, **then** `400` and no event (the audited method was never called); an unknown payout, `404`.

## Requirements

- Timing and audit live in one aspect; business methods carry only the annotation.
- The aspect never changes a result or an exception.
- It records only the parameter named for it, never all arguments.
- Failure events survive the business transaction's rollback.

## Learning objectives

- Write an aspect with a pointcut on a custom annotation and around advice.
- Explain how Spring's proxies apply aspects, and order them against transactions.
- Know the limits: self-invocation, final and private methods.
- Keep an audit log useful and free of personal data.

# 2 · Build: API contract

## Endpoints

| Method | Path                             | Purpose                                                                                                         |
|--------|----------------------------------|-----------------------------------------------------------------------------------------------------------------|
| `POST` | `/payouts`                       | A payout: `merchantId`, `amountPaise` (₹1 to ₹10 lakh), `ifsc`, `accountNumber`. Audited as `PAYOUT_REQUESTED`. |
| `GET`  | `/payouts/{id}`                  | The payout record.                                                                                              |
| `GET`  | `/audit-events?action=&limit=20` | Audit events, newest first, optionally of one action; 1 to 100.                                                 |

## Status codes

| Status | When                                          |
|--------|-----------------------------------------------|
| 201    | Payout recorded; `Location` points at it      |
| 200    | A payout; the audit events                    |
| 400    | Malformed payout, or a limit outside 1 to 100 |
| 404    | No such payout                                |
| 422    | Unknown merchant, or not enough balance       |

## Captured examples

Captured with curl from the running app on 16 Oct 2026, in this order, against one fresh database. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: ₹10,000 from Chaiwala Traders

**Why:** recorded: `201`, and audited.

Request

``` code
POST /payouts HTTP/1.1
Content-Type: application/json

{
  "merchantId": 1,
  "amountPaise": 1000000,
  "ifsc": "HDFC0001234",
  "accountNumber": "50100123457890"
}
```

Response

``` code
HTTP/1.1 201 
Location: /payouts/1
Content-Type: application/json

{
  "id": 1,
  "merchantId": 1,
  "amountPaise": 1000000,
  "ifsc": "HDFC0001234",
  "accountLast4": "7890",
  "status": "REQUESTED"
}
```

### Case 2: read it back

**Why:** not audited: only `@Audited` methods are.

Request

``` code
GET /payouts/1 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 109

{
  "id": 1,
  "merchantId": 1,
  "amountPaise": 1000000,
  "ifsc": "HDFC0001234",
  "accountLast4": "7890",
  "status": "REQUESTED"
}
```

### Case 3: ₹500 from Desi Spices (₹200)

**Why:** `422`, and a FAILURE event.

Request

``` code
POST /payouts HTTP/1.1
Content-Type: application/json

{
  "merchantId": 2,
  "amountPaise": 50000,
  "ifsc": "SBIN0004567",
  "accountNumber": "30012345678"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "Merchant 2 cannot pay out 50000 paise.",
  "instance": "/payouts",
  "status": 422,
  "title": "Not enough balance"
}
```

### Case 4: merchant 99

**Why:** `422`, and a FAILURE event.

Request

``` code
POST /payouts HTTP/1.1
Content-Type: application/json

{
  "merchantId": 99,
  "amountPaise": 1000,
  "ifsc": "HDFC0001234",
  "accountNumber": "50100123457890"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "No merchant 99.",
  "instance": "/payouts",
  "status": 422,
  "title": "Unknown merchant"
}
```

### Case 5: an IFSC without its 0

**Why:** `400` before the service: no event.

Request

``` code
POST /payouts HTTP/1.1
Content-Type: application/json

{
  "merchantId": 1,
  "amountPaise": 1000,
  "ifsc": "HDFC1001234",
  "accountNumber": "50100123457890"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/payouts",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 6: the audit log

**Why:** three events, newest first, with durations; no account numbers.

Request

``` code
GET /audit-events HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 534

[
  {
    "id": 3,
    "action": "PAYOUT_REQUESTED",
    "outcome": "FAILURE",
    "subject": "99",
    "method": "PayoutService.request",
    "error": "Unknown merchant",
    "durationMs": 2,
    "at": "2026-10-16T06:59:26.133526Z"
  },
  {
    "id": 2,
    "action": "PAYOUT_REQUESTED",
    "outcome": "FAILURE",
    "subject": "2",
    "method": "PayoutService.request",
    "error": "Not enough balance",
    "durationMs": 7,
    "at": "2026-10-16T06:59:26.113086Z"
  },
  {
    "id": 1,
    "action": "PAYOUT_REQUESTED",
    "outcome": "SUCCESS",
    "subject": "1",
    "method": "PayoutService.request",
    "error": null,
    "durationMs": 44,
    "at": "2026-10-16T06:59:26.039869Z"
  }
]
```

### Case 7: payout 99

**Why:** `404`.

Request

``` code
GET /payouts/99 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No payout 99.",
  "instance": "/payouts/99",
  "status": 404,
  "title": "Payout not found"
}
```

## The aspect's log lines

From the running app's log during the captures (`docs/captures/app-log.txt`): the timing, written by the same advice.

``` code
PAYOUT_REQUESTED SUCCESS PayoutService.request in 44 ms
PAYOUT_REQUESTED FAILURE PayoutService.request in 7 ms
PAYOUT_REQUESTED FAILURE PayoutService.request in 2 ms
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                             | What happens                          | Proved by                                                           |
|----------------------------------|---------------------------------------|---------------------------------------------------------------------|
| A payout                         | Recorded, debited, one SUCCESS event  | `aPayoutIsRecordedAndAudited`                                       |
| Not enough balance               | `422`, one FAILURE event              | `aRefusedPayoutIsAuditedAsAFailure`                                 |
| The account number               | Never in the audit table              | `theAuditLogNeverHoldsTheAccountNumber`                             |
| Several events; a filter         | Newest first; filtered by action      | `eventsComeNewestFirstAndCanBeFiltered`                             |
| Malformed bodies; a bad limit    | `400`, no events                      | `malformedPayoutsAre400AndNeverReachTheAuditedMethod`               |
| Unknown merchant; unknown payout | `422`; `404`                          | `unknownMerchantsAre422AndUnknownPayouts404`                        |
| Bad rows written directly        | Refused by named constraints          | `namedConstraintsHoldWithoutJava`                                   |
| Refused after the debit          | Debit rolled back; FAILURE event kept | `aPayoutTheDatabaseRefusesAfterTheDebitIsRolledBackButStillAudited` |

## The trap

Plausible but wrong

Expecting aspects to run on private, final or self-invoked methods.

The trap test registers a small test-only bean, `MonthEndReports`, whose methods all carry `@Audited`, and checks that Spring proxied it. Called from outside, `monthly()` leaves one event. Called through `dailyThenMonthly()`, which calls `this.monthly()`, it leaves none. A `final` method leaves none, and worse: it runs on the proxy object itself, whose injected field was never set, so it sees `null`. A `private` method leaves none.

While building, each part was undone once. Without the annotation on `request`, 4 tests turned red. Ordering the aspect inside the transaction, 3: the FAILURE events were rolled back with the payouts they described. Recording every argument, 5 (the account number reached the audit table). Swallowing the exception instead of rethrowing it, 4. One real bug was found: `@Order(HIGHEST_PRECEDENCE)` made every audited call fail with "JoinPointMatch was NOT bound", because the aspect then runs before Spring's `ExposeInvocationInterceptor`. `@Order(0)` still wraps the transaction.

``` code
package com.paysetu.payouts;

import org.junit.jupiter.api.Test;
import org.springframework.aop.support.AopUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Import;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The first test written for this station. The audit annotation replaced 120 copies of timing code, and then some
 * methods were still not audited. Each test calls one @Audited method in a different way and counts the events.
 */
@Import(MonthEndReports.class)
class ProxyLimitsTrapTest extends ApiTest {

    @Autowired
    MonthEndReports reports;

    @Test
    void aPublicMethodCalledFromOutsideIsAudited() {
        assertThat(AopUtils.isCglibProxy(reports)).isTrue();
        assertThat(reports.monthly()).isEqualTo("ran");
        assertThat(auditEvents()).isEqualTo(1);
    }

    @Test
    void aSelfInvokedMethodIsNot() {
        assertThat(reports.dailyThenMonthly()).isEqualTo("ran");
        assertThat(auditEvents()).isZero();
    }

    @Test
    void aFinalMethodIsNotAndRunsWithoutItsFields() {
        assertThat(reports.finalReport()).isEqualTo("jdbc was null");   // on the proxy, not on the real bean
        assertThat(auditEvents()).isZero();
    }

    @Test
    void aPrivateMethodIsNot() {
        assertThat(reports.viaPrivate()).isEqualTo("ran");
        assertThat(auditEvents()).isZero();
    }
}
```

``` code
package com.paysetu.payouts;

import org.springframework.jdbc.core.simple.JdbcClient;

/**
 * A test-only bean with @Audited methods called in each of the ways that matter. The trap test registers it, so
 * Spring proxies it exactly as it would a service.
 */
class MonthEndReports {

    private final JdbcClient jdbc;

    MonthEndReports(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Audited(action = "REPORT_RUN")
    public String monthly() {
        return "ran";
    }

    /** Self-invocation: "this.monthly()", past the proxy. */
    public String dailyThenMonthly() {
        return monthly();
    }

    /** Final: the proxy cannot override it, so it runs on the proxy object itself, whose fields were never set. */
    @Audited(action = "REPORT_RUN")
    public final String finalReport() {
        return jdbc == null ? "jdbc was null" : "ran";
    }

    public String viaPrivate() {
        return privateReport();
    }

    /** Private: a proxy cannot see it at all. */
    @Audited(action = "REPORT_RUN")
    private String privateReport() {
        return "ran";
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
./mvnw test                 # all 12 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Make `request` in `PayoutService` `final` and run the contract tests:

``` code
./mvnw test -Dtest=PayoutContractTest
```

Nothing is audited any more, and the method runs on the proxy, where `jdbc` is `null`. Remove `final`.

## Troubleshooting

| You see                                                                         | Cause                                                                           | Fix                                                      |
|---------------------------------------------------------------------------------|---------------------------------------------------------------------------------|----------------------------------------------------------|
| An annotated method is never advised                                            | Self-invocation, or the method is private or final.                             | Call it from another bean; make it public and not final. |
| `NullPointerException` on an injected field in a final method                   | The final method ran on the proxy, whose fields are empty.                      | Do not make proxied methods final.                       |
| `Required to bind 2 arguments, but only bound 1 (JoinPointMatch was NOT bound)` | The aspect is ordered at `HIGHEST_PRECEDENCE`, before Spring's own interceptor. | Any order after it, such as `@Order(0)`.                 |
| Failure events disappear                                                        | The aspect runs inside the transaction and is rolled back with it.              | Order it ahead of the transaction advisor.               |
| Which starter brings AOP?                                                       | In Boot 4 it is `spring-boot-starter-aspectj` (the one this project uses).      | Add it; Boot then turns on `@Aspect` beans.              |

## Project layout

``` tree
stations/056-timing-and-auditing-with-spring-aop/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/paysetu/payouts/
│   ├── PayoutController.java   ├── PayoutService.java   ├── Audited.java   ├── AuditAspect.java
│   ├── AuditLog.java   └── PayoutsApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__merchants_payouts_audit.sql, V2__demo_merchants.sql
├── src/test/java/com/paysetu/payouts/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the aspect and the database.

#### `src/main/java/com/paysetu/payouts/PayoutController.java`

Does  
Validates the payout; reads payouts and audit events.

Why  
HTTP only; calls the service through its proxy.

Without it  
Validation inside the audited method (so a bad body would be audited).

#### `src/main/java/com/paysetu/payouts/PayoutService.java`

Does  
Debits the balance if it can, then records the payout, in one transaction.

Why  
One annotation instead of timing and audit code.

Without it  
The 121st copy-paste.

#### `src/main/java/com/paysetu/payouts/Audited.java`

Does  
The annotation: an action name and the parameter that names the subject.

Why  
Explicit about what is recorded.

Without it  
Logging every argument.

#### `src/main/java/com/paysetu/payouts/AuditAspect.java`

Does  
Around every `@Audited` call: time, run, record, rethrow.

Why  
One place for the cross-cutting code; its order puts it outside the transaction.

Without it  
Lost failure events; changed exceptions.

- `@annotation(audited)` binds the annotation itself, so the advice reads `action()`.
- `@Order(0)`: ahead of the transaction advisor, behind Spring's own `ExposeInvocationInterceptor`.
- The subject comes from the one named parameter, found by name.

#### `src/main/java/com/paysetu/payouts/AuditLog.java`

Writes and reads `audit_events`.

#### `src/main/resources/db/migration/V1__merchants_payouts_audit.sql`

Merchants, payouts and audit events, with named constraints.

#### `src/main/resources/db/migration/V2__demo_merchants.sql`

Two merchants and their balances.

#### `pom.xml`

`spring-boot-starter-aspectj` (Boot 4's name for the AOP starter).

#### `src/main/java/com/paysetu/payouts/PayoutsApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                | Result |
|---------------|-------------------------------------------------------|---------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `PayoutContractTest` (6)  | pass   |
| Every station | Reproduce the failure before the fix                  | `ProxyLimitsTrapTest` (4) | pass   |
| Database      | Rollback and constraint tests against a real database | `PayoutDatabaseTest` (2)  | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payouts.PayoutDatabaseTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payouts.ProxyLimitsTrapTest
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.payouts.PayoutContractTest
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/paysetu/payouts/ProxyLimitsTrapTest.java`

Written first: which calls the aspect can see.

#### `src/test/java/com/paysetu/payouts/PayoutContractTest.java`

Payouts and their events, and every refusal.

#### `src/test/java/com/paysetu/payouts/PayoutDatabaseTest.java`

Named constraints; a rollback with its FAILURE event kept.

#### `src/test/java/com/paysetu/payouts/MonthEndReports.java`

Test-only bean: one audited method reached four ways.

#### `src/test/java/com/paysetu/payouts/ApiTest.java`

Shared setup: no payouts or events, balances reset.

#### `src/test/java/com/paysetu/payouts/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/paysetu/payouts/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=CancelPayoutChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 12 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in (Java files and one migration), all 14 tests pass (12 station tests and 2 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Cancel a payout

Add `POST /payouts/{id}/cancellation`: REQUESTED becomes CANCELLED and the money returns to the balance. Audit it as `PAYOUT_CANCELLED`, subject the payout id, without writing any audit code.

**Done when:** the test in `CancelPayoutChallengeTest` passes.

Hints

- `@Audited(action = "PAYOUT_CANCELLED", subjectParam = "payoutId")` on a public method of the service.
- Lock the payout row so two cancellations cannot both refund.

#### `challenge/CancelPayoutChallengeTest.java`

``` code
package com.paysetu.payouts;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /payouts/{id}/cancellation cancels a REQUESTED payout and returns the money to the balance, and
 * is audited as PAYOUT_CANCELLED (subject: the payout id) without a line of audit code. Twice: 409. Unknown: 404.
 */
class CancelPayoutChallengeTest extends ApiTest {

    @Test
    void cancellingIsAuditedByTheAnnotationAlone() throws Exception {
        payout(1, 1_000_000);
        mvc.perform(post("/payouts/1/cancellation")).andExpect(status().isOk()).andExpect(jsonPath("$.status").value("CANCELLED"));
        assertThat(balance(1)).isEqualTo(5_000_000);
        mvc.perform(post("/payouts/1/cancellation")).andExpect(status().isConflict());
        mvc.perform(post("/payouts/99/cancellation")).andExpect(status().isNotFound());
        mvc.perform(get("/audit-events").param("action", "PAYOUT_CANCELLED")).andExpect(content().json("""
                [{"outcome":"FAILURE","subject":"99"},{"outcome":"FAILURE","subject":"1"},{"outcome":"SUCCESS","subject":"1"}]"""));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Who did it

Record the actor on every event: the `X-Operator` header of the HTTP request, or "system" outside one. A migration adds the column with a check.

**Done when:** the test in `OperatorChallengeTest` passes.

Hints

- `RequestContextHolder.getRequestAttributes()` is the current request, or `null` outside one.
- The aspect changes; no service does.

#### `challenge/OperatorChallengeTest.java`

``` code
package com.paysetu.payouts;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Challenge 2: every audit event also records who: the X-Operator header of the HTTP request (an operations person's
 * id), or "system" when there is none (a scheduled job, or a call without the header). A new migration adds the
 * column with a check; the aspect reads the current request. Demo: the header is trusted; a real app uses the login.
 */
class OperatorChallengeTest extends ApiTest {

    @Test
    void theAuditEventNamesTheOperator() throws Exception {
        mvc.perform(post("/payouts").header("X-Operator", "ops-asha").contentType(MediaType.APPLICATION_JSON)
                .content("{\"merchantId\":1,\"amountPaise\":1000,\"ifsc\":\"HDFC0001234\",\"accountNumber\":\"50100123457890\"}"));
        payout(1, 1000);
        assertThat(jdbc.sql("SELECT actor FROM audit_events ORDER BY id").query(String.class).list()).containsExactly("ops-asha", "system");
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> jdbc.sql("UPDATE audit_events SET actor = ' '").update())
                .hasMessageContaining("audit_events_actor_not_blank");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Aspect, filter, or a plain call?

Timing every HTTP request, auditing payouts, and retrying a flaky bank call: for each, choose a servlet filter, an aspect, or an explicit call in the code. What does each choice hide from the next reader, and what does it stop people forgetting?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: one audited method, reached four ways.
2.  Design the annotation: what is recorded, and what never is.
3.  Write the around advice; rethrow everything; order it against the transaction.
4.  Delete the copy-pasted code; test that refusals and rollbacks are still audited.

## Design alternatives and trade-offs

| Approach                                                             | What it costs                                            | Verdict            |
|----------------------------------------------------------------------|----------------------------------------------------------|--------------------|
| Custom annotation + around aspect                                    | Behaviour not visible in the method body; proxy limits.  | Chosen             |
| Copy-pasted timing and audit code                                    | Drifts and goes missing.                                 | The problem        |
| A pointcut on a package (`execution(* com.paysetu..*Service.*(..))`) | No annotation to forget; audits methods nobody meant to. | Too wide here      |
| Servlet filter                                                       | Sees HTTP requests only, not service calls from jobs.    | For request timing |
| Micrometer `@Timed` / `@Observed`                                    | Metrics and traces, not an audit trail.                  | For timing         |

## Database design

| Table          | Constraints                                                                                         |
|----------------|-----------------------------------------------------------------------------------------------------|
| `merchants`    | `merchants_balance_not_negative`                                                                    |
| `payouts`      | `payouts_merchant_fk`, `payouts_amount_range`, `payouts_ifsc_shape`, `payouts_status_known`         |
| `audit_events` | `audit_events_outcome_known`, `audit_events_error_on_failure`, `audit_events_duration_not_negative` |

``` code
-- Paysetu payouts and the audit log that records every attempt.
CREATE TABLE merchants (
    id            BIGINT PRIMARY KEY,
    name          VARCHAR(80) NOT NULL,
    balance_paise BIGINT      NOT NULL,
    CONSTRAINT merchants_balance_not_negative CHECK (balance_paise >= 0)
);

CREATE TABLE payouts (
    id            BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    merchant_id   BIGINT      NOT NULL,
    amount_paise  BIGINT      NOT NULL,
    ifsc          CHAR(11)    NOT NULL,
    account_last4 CHAR(4)     NOT NULL,
    status        VARCHAR(10) NOT NULL DEFAULT 'REQUESTED',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT payouts_merchant_fk FOREIGN KEY (merchant_id) REFERENCES merchants (id),
    CONSTRAINT payouts_amount_range CHECK (amount_paise BETWEEN 100 AND 100000000),
    CONSTRAINT payouts_ifsc_shape CHECK (ifsc ~ '^[A-Z]{4}0[A-Z0-9]{6}$'),
    CONSTRAINT payouts_status_known CHECK (status IN ('REQUESTED', 'CANCELLED'))
);

CREATE TABLE audit_events (
    id          BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    action      VARCHAR(40)  NOT NULL,
    outcome     VARCHAR(10)  NOT NULL,
    subject     VARCHAR(40),
    method      VARCHAR(120) NOT NULL,
    error       VARCHAR(200),
    duration_ms BIGINT       NOT NULL,
    at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT audit_events_outcome_known CHECK (outcome IN ('SUCCESS', 'FAILURE')),
    CONSTRAINT audit_events_error_on_failure CHECK ((outcome = 'FAILURE') = (error IS NOT NULL)),
    CONSTRAINT audit_events_duration_not_negative CHECK (duration_ms >= 0)
);

CREATE INDEX audit_events_action ON audit_events (action, id DESC);
```

# 3 · Go deeper: Production

Audit is evidence  
An audit table is useful only if it is complete and nobody edits it. Restrict UPDATE and DELETE on it to nobody, and keep it longer than the business data.

No personal data by default  
Record identifiers and outcomes, not arguments. Account numbers, names and addresses copied into logs spread everywhere logs go.

Cost  
Every audited call writes a row. For hot paths, write asynchronously or batch, and accept the small window that opens.

Failure of the audit itself  
If the audit insert fails, this aspect's exception replaces the business result. Decide which matters more: for money, failing loudly is usually right.

# 3 · Go deeper: Interview

## Interview takeaways

What are a pointcut and an advice?

The pointcut selects join points (here: methods annotated with @Audited); the advice is the code run at them (here: around, so it can time the call and see its outcome).

How does Spring apply aspects?

It creates a proxy for each bean with advised methods, a JDK interface proxy or a CGLIB subclass, and runs the advice when calls go through the proxy.

Why are final and private methods not advised?

A CGLIB proxy works by overriding methods. Final methods cannot be overridden; private ones are not visible. A final method even runs on the proxy instance, whose fields are empty.

How do you order an aspect against @Transactional?

With @Order: a lower value runs outside. The transaction advisor has the lowest precedence by default, so @Order(0) wraps it.

When is an aspect the wrong tool?

When the behaviour is the point of the method (put it in the code), or when readers must see it to understand the method. Aspects suit concerns that are the same everywhere.

## Self-check rubric

| Area        | Meets the bar                        | Above the bar                                              |
|-------------|--------------------------------------|------------------------------------------------------------|
| Correctness | All 12 tests pass.                   | You made a method final and explained what broke.          |
| AOP         | Annotation, pointcut, around advice. | You can order it against transactions.                     |
| Proxies     | You know the three limits.           | You can explain the null field in a final method.          |
| Audit       | Every outcome recorded.              | No personal data, and a plan for the audit insert failing. |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any aspect:

- Are the advised methods public, not final, and called from other beans?
- Does the advice ever change the result or swallow an exception?
- Where does it sit relative to transactions, and is that on purpose?
- What data does it copy, and where does that data end up?
