# Station 057 · Audit trail that survives a rollback

Working Systems · 0–2 years · Core · Fintech · Types: Database

Spring Boot 4.1.1 · Java 25 · @Transactional propagation (REQUIRED, REQUIRES_NEW) · TransactionSynchronization afterCompletion · JdbcClient · PostgreSQL 17 · Flyway · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Accounts and transfers are demo data, not Tijori's. A transfer changes two balances and writes a record: no bank network (IMPS, NEFT, UPI) is involved.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 9 tests.

# 1 · Understand

## The problem in real life

1.  **Audit every attempt**

    Regulators and fraud teams want every transfer attempt recorded, especially the failed ones: those are where fraud shows.

2.  **The failures vanished**

    Tijori's code caught the failure and wrote an audit row, then rethrew. The transaction rolled back, as it should, and took the audit row with it. The trail showed only successes.

3.  **The fix**

    Write audit rows in a transaction of their own (REQUIRES_NEW), and write the outcome only when the transfer's transaction has really ended.

A record that must outlive a failure cannot live inside the failing transaction.

## What are we building?

`POST /transfers` records a transfer between two accounts: two balances change and a transfer record is written. Every attempt leaves events in the audit trail: one when it starts, and one outcome, COMPLETED or FAILED with a reason. `GET /audit-events?accountId=…` shows an account's trail, failures included.

## An everyday analogy

A bank's visitor register at the door. You sign it when you walk in, whatever happens at the counter. If your request is refused, the counter tears up your form, but nobody tears a page out of the visitor register. The old code kept the register on the counter, inside the form.

## How it works in 4 steps

1.  **The transfer starts** its transaction, and records TRANSFER_ATTEMPTED in a separate one, committed at once.
2.  **It debits, credits, records** the transfer; any refusal throws and rolls back.
3.  **When the transaction ends**, committed or rolled back, Spring calls the transfer's callback.
4.  **The callback records** COMPLETED or FAILED (with the reason), again in a transaction of its own.

Check yourself: why not write COMPLETED just before the method returns?

Because the transaction is not over: the commit can still fail, or a caller can roll back the transaction this method joined. The trail would then say COMPLETED for a transfer that never happened. Only after completion is the outcome known.

## What this station is not

- **No bank network.** Balances in one database.
- **No fraud rules.** A lockout is challenge 2.
- **No login.** Anyone can call the API.

## Key terms

| Term                            | Simple meaning                                                               | Everyday example                                                   | In this project            |
|---------------------------------|------------------------------------------------------------------------------|--------------------------------------------------------------------|----------------------------|
| **Rollback**                    | Undoing every change a transaction made.                                     | Tearing up a bill that was never paid.                             | A failed transfer          |
| **Propagation**                 | What a transactional method does when a transaction is already open.         | Joining the same bill, or opening your own.                        | `REQUIRED`, `REQUIRES_NEW` |
| **REQUIRED**                    | Join the caller's transaction; start one only if there is none.              | Adding a line to the same bill.                                    | `TransferService.transfer` |
| **REQUIRES_NEW**                | Pause the caller's transaction and run in a new one that commits on its own. | A separate receipt, signed at once.                                | `AuditTrail.record`        |
| **Transaction synchronization** | Code Spring calls when the transaction ends.                                 | A note to phone the customer once the bill is settled, or torn up. | `afterCompletion`          |
| **Attempt id**                  | One id shared by every event of one transfer attempt.                        | A token number at a counter.                                       | `attempt_id`               |

# 2 · Build: Spec

## Business problem

**Tijori** (a fictional digital bank) must keep an audit trail of every transfer attempt. Failed attempts disappeared from it, because their audit rows rolled back with the transfer.

## Acceptance criteria

1.  **Given** Asha (₹25,000) sends Ravi ₹1,500, **then** `201`, both balances change, and the trail has ATTEMPTED then COMPLETED with one attempt id.
2.  **Given** Ravi (₹100) tries to send ₹5,000, **then** `422`, his balance is unchanged, and the trail has ATTEMPTED then FAILED "Insufficient funds".
3.  **Given** a transfer to account 99, **then** `422`, Asha's debit is rolled back, and the attempt is still in the trail.
4.  **Given** a caller rolls back a transfer that returned normally, **then** the trail says FAILED, never COMPLETED.
5.  **Given** a malformed body, **then** `400` and no attempt; an unknown account's trail, `404`.

## Requirements

- Audit rows commit on their own; no business rollback can remove them.
- Each attempt has exactly one outcome, enforced by the database.
- The outcome is written only after the transaction's real end.
- Money in integer paise; balances never below zero.

## Learning objectives

- Choose between `REQUIRED` and `REQUIRES_NEW`, and know what each costs.
- Run code after commit or rollback with a transaction synchronization.
- Know that data access in those callbacks needs its own transaction.
- Prove propagation behaviour against a real database.

# 2 · Build: API contract

## Endpoints

| Method | Path                        | Purpose                                                                  |
|--------|-----------------------------|--------------------------------------------------------------------------|
| `POST` | `/transfers`                | Transfer: `fromAccountId`, `toAccountId`, `amountPaise` (₹1 to ₹5 lakh). |
| `GET`  | `/audit-events?accountId=1` | Every event where the account sent or would have received, oldest first. |

## Status codes

| Status | When                                                                            |
|--------|---------------------------------------------------------------------------------|
| 201    | Transferred; audited ATTEMPTED and COMPLETED                                    |
| 200    | The trail                                                                       |
| 400    | Malformed body (not an attempt, not audited); no `accountId`                    |
| 404    | No such account (trail)                                                         |
| 422    | Insufficient funds, same account, unknown account: audited ATTEMPTED and FAILED |

## Captured examples

Captured with curl from the running app on 16 Oct 2026, in this order, against one fresh database. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: Asha sends Ravi ₹1,500

**Why:** `201`.

Request

``` code
POST /transfers HTTP/1.1
Content-Type: application/json

{
  "fromAccountId": 1,
  "toAccountId": 2,
  "amountPaise": 150000
}
```

Response

``` code
HTTP/1.1 201 
Location: /transfers/1
Content-Type: application/json

{
  "id": 1,
  "attemptId": "8b856395-8c84-4990-8b92-5ab8479a9c79",
  "fromAccountId": 1,
  "toAccountId": 2,
  "amountPaise": 150000,
  "status": "COMPLETED"
}
```

### Case 2: Ravi (₹100) tries ₹5,000

**Why:** `422`, and still audited.

Request

``` code
POST /transfers HTTP/1.1
Content-Type: application/json

{
  "fromAccountId": 2,
  "toAccountId": 1,
  "amountPaise": 500000
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "Account 2 cannot send 500000 paise.",
  "instance": "/transfers",
  "status": 422,
  "title": "Insufficient funds"
}
```

### Case 3: Asha sends ₹10 to account 99

**Why:** her debit ran, then the credit found no account: rolled back, `422`.

Request

``` code
POST /transfers HTTP/1.1
Content-Type: application/json

{
  "fromAccountId": 1,
  "toAccountId": 99,
  "amountPaise": 1000
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "No account 99.",
  "instance": "/transfers",
  "status": 422,
  "title": "Unknown account"
}
```

### Case 4: Asha's trail

**Why:** two attempts, one COMPLETED, one FAILED, each pair sharing its attempt id.

Request

``` code
GET /audit-events?accountId=1 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 1156

[
  {
    "id": 1,
    "attemptId": "8b856395-8c84-4990-8b92-5ab8479a9c79",
    "event": "TRANSFER_ATTEMPTED",
    "fromAccount": 1,
    "toAccount": 2,
    "amountPaise": 150000,
    "reason": null,
    "at": "2026-10-16T07:11:57.140904Z"
  },
  {
    "id": 2,
    "attemptId": "8b856395-8c84-4990-8b92-5ab8479a9c79",
    "event": "TRANSFER_COMPLETED",
    "fromAccount": 1,
    "toAccount": 2,
    "amountPaise": 150000,
    "reason": null,
    "at": "2026-10-16T07:11:57.156129Z"
  },
  {
    "id": 3,
    "attemptId": "b37e2491-aebf-4b17-8e3c-167fd1f2cf11",
    "event": "TRANSFER_ATTEMPTED",
    "fromAccount": 2,
    "toAccount": 1,
    "amountPaise": 500000,
    "reason": null,
    "at": "2026-10-16T07:11:57.181663Z"
  },
  {
    "id": 4,
    "attemptId": "b37e2491-aebf-4b17-8e3c-167fd1f2cf11",
    "event": "TRANSFER_FAILED",
    "fromAccount": 2,
    "toAccount": 1,
    "amountPaise": 500000,
    "reason": "Insufficient funds",
    "at": "2026-10-16T07:11:57.190755Z"
  },
  {
    "id": 5,
    "attemptId": "e2b00bb2-6dd1-4d67-b911-0c356bcf5eda",
    "event": "TRANSFER_ATTEMPTED",
    "fromAccount": 1,
    "toAccount": 99,
    "amountPaise": 1000,
    "reason": null,
    "at": "2026-10-16T07:11:57.209125Z"
  },
  {
    "id": 6,
    "attemptId": "e2b00bb2-6dd1-4d67-b911-0c356bcf5eda",
    "event": "TRANSFER_FAILED",
    "fromAccount": 1,
    "toAccount": 99,
    "amountPaise": 1000,
    "reason": "Unknown account",
    "at": "2026-10-16T07:11:57.213725Z"
  }
]
```

### Case 5: Ravi's trail

**Why:** the transfer he received and the one he failed to send.

Request

``` code
GET /audit-events?accountId=2 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 770

[
  {
    "id": 1,
    "attemptId": "8b856395-8c84-4990-8b92-5ab8479a9c79",
    "event": "TRANSFER_ATTEMPTED",
    "fromAccount": 1,
    "toAccount": 2,
    "amountPaise": 150000,
    "reason": null,
    "at": "2026-10-16T07:11:57.140904Z"
  },
  {
    "id": 2,
    "attemptId": "8b856395-8c84-4990-8b92-5ab8479a9c79",
    "event": "TRANSFER_COMPLETED",
    "fromAccount": 1,
    "toAccount": 2,
    "amountPaise": 150000,
    "reason": null,
    "at": "2026-10-16T07:11:57.156129Z"
  },
  {
    "id": 3,
    "attemptId": "b37e2491-aebf-4b17-8e3c-167fd1f2cf11",
    "event": "TRANSFER_ATTEMPTED",
    "fromAccount": 2,
    "toAccount": 1,
    "amountPaise": 500000,
    "reason": null,
    "at": "2026-10-16T07:11:57.181663Z"
  },
  {
    "id": 4,
    "attemptId": "b37e2491-aebf-4b17-8e3c-167fd1f2cf11",
    "event": "TRANSFER_FAILED",
    "fromAccount": 2,
    "toAccount": 1,
    "amountPaise": 500000,
    "reason": "Insufficient funds",
    "at": "2026-10-16T07:11:57.190755Z"
  }
]
```

### Case 6: account 99's trail

**Why:** no such account: `404`.

Request

``` code
GET /audit-events?accountId=99 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No account 99.",
  "instance": "/audit-events",
  "status": 404,
  "title": "Account not found"
}
```

### Case 7: 99 paise

**Why:** `400`: a malformed request is not an attempt.

Request

``` code
POST /transfers HTTP/1.1
Content-Type: application/json

{
  "fromAccountId": 1,
  "toAccountId": 2,
  "amountPaise": 99
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/transfers",
  "status": 400,
  "title": "Bad Request"
}
```

## The balances afterwards

Read with psql after the requests above (`docs/captures/balances.txt`): Asha was debited once, ₹1,500. Case 3's debit was rolled back; its audit events were not.

``` code
 id |   holder   | balance_paise 
----+------------+---------------
  1 | Asha Verma |       2350000
  2 | Ravi Menon |        160000
(2 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                       | What happens                                                  | Proved by                                                     |
|------------------------------------------------------------|---------------------------------------------------------------|---------------------------------------------------------------|
| A transfer                                                 | Both balances change; ATTEMPTED and COMPLETED, one attempt id | `aTransferChangesBothBalancesAndIsAuditedTwice`               |
| Insufficient funds, same account, unknown account          | `422` each; debit rolled back; each audited with its reason   | `everyRefusalIsAuditedWithItsReason`                          |
| Malformed bodies                                           | `400`; no events                                              | `malformedTransfersAre400AndNotAttempts`                      |
| Unknown account's trail; no account given                  | `404`; `400`                                                  | `unknownAccountsHaveNoTrail`                                  |
| Bad rows written directly; two outcomes for one attempt    | Refused by named constraints                                  | `namedConstraintsHoldWithoutJava`                             |
| REQUIRES_NEW and REQUIRED inside a rolled-back transaction | The first survives, the second does not                       | `requiresNewSurvivesTheCallersRollbackAndRequiredDoesNot`     |
| A caller rolls back a transfer that returned normally      | FAILED, not COMPLETED; balances unchanged                     | `aTransferRolledBackByItsCallerIsAuditedAsFailedNotCompleted` |

## The trap

Plausible but wrong

Writing the audit row in the same transaction, so it rolls back too.

The old service is kept in the tests as `OldTransferService`, a real proxied bean. Its catch block writes a TRANSFER_FAILED row with the same `JdbcClient`, then rethrows. Ravi's ₹5,000 attempt fails as it should, and the trail is empty: the rollback took the audit row too. The same attempt through the fixed API leaves ATTEMPTED and FAILED "Insufficient funds", and Ravi's balance unchanged.

While building, each part was undone once. `REQUIRED` instead of `REQUIRES_NEW` on the audit write turned 4 tests red. Writing COMPLETED inside the method, before the commit, turned 1 red: the test whose caller rolls back, where the trail then claimed a completed transfer. Not capturing the reason turned 2 red.

``` code
package com.tijori.transfers;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Import;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: Ravi (₹100) tries to send ₹5,000, the old way and the new way. */
@Import(OldTransferService.class)
class AuditRollbackTrapTest extends ApiTest {

    @Autowired
    OldTransferService old;

    @Test
    void theOldAuditRowRolledBackWithTheTransfer() {
        assertThatThrownBy(() -> old.transfer(2, 1, 500_000)).hasMessage("insufficient funds");
        assertThat(events()).isEmpty();   // the failed attempt left no trace: exactly what the auditors asked for, gone
    }

    @Test
    void theNewTrailKeepsTheAttemptAndItsFailure() throws Exception {
        transfer(2, 1, 500_000).andExpect(status().isUnprocessableContent());
        assertThat(events()).containsExactly("TRANSFER_ATTEMPTED", "TRANSFER_FAILED Insufficient funds");
        assertThat(balance(2)).isEqualTo(10_000);
    }
}
```

``` code
package com.tijori.transfers;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.transaction.annotation.Transactional;

/**
 * The transfer as it shipped, kept only in tests (the trap test registers it as a bean). It audits the failure,
 * carefully, in a catch block, with the same JdbcClient, in the same transaction that is about to roll back.
 */
class OldTransferService {

    private final JdbcClient jdbc;

    OldTransferService(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Transactional
    public void transfer(long from, long to, long amountPaise) {
        try {
            int debited = jdbc.sql("UPDATE accounts SET balance_paise = balance_paise - ? WHERE id = ? AND balance_paise >= ?").params(amountPaise, from, amountPaise).update();
            if (debited == 0) {
                throw new IllegalStateException("insufficient funds");
            }
            jdbc.sql("UPDATE accounts SET balance_paise = balance_paise + ? WHERE id = ?").params(amountPaise, to).update();
        } catch (IllegalStateException e) {
            jdbc.sql("INSERT INTO audit_events (attempt_id, event, from_account, to_account, amount_paise, reason) VALUES (gen_random_uuid(), 'TRANSFER_FAILED', ?, ?, ?, ?)")
                    .params(from, to, amountPaise, e.getMessage()).update();
            throw e;   // ...and the rollback takes the audit row with it
        }
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
./mvnw test                 # all 9 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Change `REQUIRES_NEW` to the default in `AuditTrail` (remove `propagation = …`) and run:

``` code
./mvnw test -Dtest=AuditRollbackTrapTest
```

The new trail now loses its failures exactly like the old one. Put it back.

## Troubleshooting

| You see                                                           | Cause                                                                                   | Fix                                                              |
|-------------------------------------------------------------------|-----------------------------------------------------------------------------------------|------------------------------------------------------------------|
| Audit rows of failed operations are missing                       | Written in the failing transaction.                                                     | `REQUIRES_NEW`, or write outside the transaction.                |
| A write in `afterCommit`/`afterCompletion` does nothing or errors | It tried to join a transaction that is already finished.                                | Call a `REQUIRES_NEW` method from the callback.                  |
| Requests hang under load                                          | Each `REQUIRES_NEW` holds a second connection while the first waits: the pool runs dry. | Pool size above the concurrency; keep nested transactions short. |
| COMPLETED in the trail for a transfer that rolled back            | Outcome written before the commit.                                                      | Write it in `afterCompletion`, from the real status.             |
| `Transaction synchronization is not active`                       | `registerSynchronization` called outside a transaction.                                 | Call it inside a `@Transactional` method.                        |

## Project layout

``` tree
stations/057-audit-trail-that-survives-a-rollback/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/tijori/transfers/
│   ├── TransferController.java   ├── TransferService.java   ├── AuditTrail.java   └── TransfersApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__accounts_transfers_audit.sql, V2__demo_accounts.sql
├── src/test/java/com/tijori/transfers/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database.

#### `src/main/java/com/tijori/transfers/TransferController.java`

Does  
Validates the transfer; reads an account's trail.

Why  
HTTP only; a malformed body never becomes an attempt.

Without it  
Validation errors audited as attempts.

#### `src/main/java/com/tijori/transfers/TransferService.java`

Does  
Records the attempt, moves the money, and leaves the outcome to the end of the transaction.

Why  
REQUIRED for the business work; a synchronization for the outcome.

Without it  
COMPLETED for a transfer that rolled back.

- `registerSynchronization` hooks into the transaction this call runs in, even if it is the caller's.
- The reason is kept in an `AtomicReference` set in the catch block and read in `afterCompletion`.
- The debit is conditional: zero rows means insufficient funds (or no account).

#### `src/main/java/com/tijori/transfers/AuditTrail.java`

Does  
Writes and reads audit events.

Why  
`REQUIRES_NEW`: each write commits on its own, also when called from `afterCompletion`.

Without it  
Audit rows that roll back.

#### `src/main/resources/db/migration/V1__accounts_transfers_audit.sql`

Accounts, transfers and the audit table, with named constraints and one outcome per attempt.

#### `src/main/resources/db/migration/V2__demo_accounts.sql`

Asha (₹25,000) and Ravi (₹100).

#### `src/main/resources/application.yaml`

Problem details on; decimals refused for whole-number fields.

#### `src/main/java/com/tijori/transfers/TransfersApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                  | Result |
|---------------|-------------------------------------------------------|-----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `TransferContractTest` (4)  | pass   |
| Every station | Reproduce the failure before the fix                  | `AuditRollbackTrapTest` (2) | pass   |
| Database      | Rollback and constraint tests against a real database | `AuditDatabaseTest` (3)     | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.transfers.AuditRollbackTrapTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.transfers.TransferContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.transfers.AuditDatabaseTest
[INFO] Tests run: 9, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tijori/transfers/AuditRollbackTrapTest.java`

Written first: the old catch-block audit, and the new trail, for the same failed attempt.

#### `src/test/java/com/tijori/transfers/TransferContractTest.java`

Transfers, refusals with reasons, and the trail.

#### `src/test/java/com/tijori/transfers/AuditDatabaseTest.java`

Named constraints; REQUIRES_NEW vs REQUIRED; a caller's rollback after a normal return.

#### `src/test/java/com/tijori/transfers/OldTransferService.java`

The old service, kept only in tests.

#### `src/test/java/com/tijori/transfers/RequiredPropagation.java`

Test-only bean: the same insert with REQUIRED, for comparison.

#### `src/test/java/com/tijori/transfers/ApiTest.java`

Shared setup: no transfers or events, balances reset.

#### `src/test/java/com/tijori/transfers/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tijori/transfers/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=AttemptIdChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 9 tests.

Checked (`docs/challenge-run.txt`): with the reference solution copied in, all 11 tests pass (9 station tests and 2 challenge tests).

Challenge 1 · Beginner-friendly · about 15 minutes

## The attempt id in the refusal

Add `attemptId` to every refused transfer's problem response: the same id its audit events carry.

**Done when:** the test in `AttemptIdChallengeTest` passes.

Hints

- `ProblemDetail.setProperty` adds a field to the response.
- The catch block already has the problem and the attempt id.

#### `challenge/AttemptIdChallengeTest.java`

``` code
package com.tijori.transfers;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: a refused transfer's problem response carries "attemptId", the same id as its audit events, so a
 * customer reading it to support can be found in the trail at once.
 */
class AttemptIdChallengeTest extends ApiTest {

    @Test
    void theRefusalNamesItsAttempt() throws Exception {
        String body = transfer(2, 1, 500_000).andExpect(status().isUnprocessableContent()).andReturn().getResponse().getContentAsString();
        String attemptId = com.jayway.jsonpath.JsonPath.read(body, "$.attemptId");
        assertThat(jdbc.sql("SELECT event FROM audit_events WHERE attempt_id = ?::uuid ORDER BY id").param(attemptId).query(String.class).list())
                .containsExactly("TRANSFER_ATTEMPTED", "TRANSFER_FAILED");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 25 minutes

## Lock out repeated failures

After 3 failed transfers from an account within 10 minutes, refuse its next ones with `429` "Too many failed attempts", until the failures age. Count from the audit trail.

**Done when:** the test in `LockoutChallengeTest` passes.

Hints

- The count only works because failures survive their rollbacks: that is the point.
- The blocked attempt is itself an attempt: it is audited like the others.

#### `challenge/LockoutChallengeTest.java`

``` code
package com.tijori.transfers;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: after 3 failed transfers from an account in the last 10 minutes, further transfers from it are 429
 * "Too many failed attempts" (and audited as failed attempts). The count comes from the audit trail, which only
 * works because failures survive their rollbacks. Other accounts are not affected. Demo rule, not a bank's.
 */
class LockoutChallengeTest extends ApiTest {

    @Test
    void threeFailuresLockTheSenderForAWhile() throws Exception {
        for (int i = 0; i < 3; i++) {
            transfer(2, 1, 500_000).andExpect(status().isUnprocessableContent());
        }
        transfer(2, 1, 1_000).andExpect(status().isTooManyRequests()).andExpect(jsonPath("$.title").value("Too many failed attempts"));
        assertThat(balance(2)).isEqualTo(10_000);
        transfer(1, 2, 1_000).andExpect(status().isCreated());   // Asha is not locked
        jdbc.sql("UPDATE audit_events SET at = at - interval '11 minutes'").update();
        transfer(2, 1, 1_000).andExpect(status().isCreated());   // ten minutes later, Ravi can try again
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Where should the audit trail live?

Compare three homes for it: a table in the same database written with REQUIRES_NEW (this station), an outbox table written in the same transaction and shipped elsewhere, and a log line sent to a log pipeline. For each: can an event be lost, can it describe something that never happened, and who can change it later?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test with the old catch-block audit as a real bean.
2.  Move audit writes to a bean whose method is `REQUIRES_NEW`.
3.  Record the attempt first; record the outcome from `afterCompletion`.
4.  Prove both against a rollback by a caller, not only by an exception.

## Design alternatives and trade-offs

| Approach                                                  | What it costs                                                                | Verdict    |
|-----------------------------------------------------------|------------------------------------------------------------------------------|------------|
| `REQUIRES_NEW` audit writes + `afterCompletion` outcome   | A second connection per audit write.                                         | Chosen     |
| Audit in the same transaction                             | Failures vanish.                                                             | The trap   |
| `@TransactionalEventListener(phase = AFTER_COMPLETION)`   | The same idea through events; the listener still needs `REQUIRES_NEW`.       | Equivalent |
| Audit written by the controller after the service returns | Misses calls from jobs and other services; a caller's rollback is invisible. | Incomplete |
| `NESTED` (savepoints)                                     | Rolls back with the outer transaction: the opposite of what an audit needs.  | Wrong tool |

## Database design

| Table          | Constraints                                                                                                                                                          |
|----------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `accounts`     | `accounts_balance_not_negative`                                                                                                                                      |
| `transfers`    | `transfers_from_fk`, `transfers_to_fk`, `transfers_not_to_self`, `transfers_amount_range`, `transfers_attempt_unique`                                                |
| `audit_events` | `audit_events_event_known`, `audit_events_reason_on_failure`, `audit_events_one_per_attempt`, partial unique `audit_events_one_outcome`; no foreign keys, on purpose |

``` code
-- Tijori transfers and their audit trail. Audit rows reference accounts only loosely: an attempt to an account that
-- does not exist must still be recorded, so audit_events has no foreign keys.
CREATE TABLE accounts (
    id            BIGINT PRIMARY KEY,
    holder        VARCHAR(80) NOT NULL,
    balance_paise BIGINT      NOT NULL,
    CONSTRAINT accounts_balance_not_negative CHECK (balance_paise >= 0)
);

CREATE TABLE transfers (
    id           BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    attempt_id   UUID        NOT NULL,
    from_account BIGINT      NOT NULL,
    to_account   BIGINT      NOT NULL,
    amount_paise BIGINT      NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT transfers_from_fk FOREIGN KEY (from_account) REFERENCES accounts (id),
    CONSTRAINT transfers_to_fk FOREIGN KEY (to_account) REFERENCES accounts (id),
    CONSTRAINT transfers_not_to_self CHECK (from_account <> to_account),
    CONSTRAINT transfers_amount_range CHECK (amount_paise BETWEEN 100 AND 50000000),
    CONSTRAINT transfers_attempt_unique UNIQUE (attempt_id)
);

CREATE TABLE audit_events (
    id           BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    attempt_id   UUID         NOT NULL,
    event        VARCHAR(20)  NOT NULL,
    from_account BIGINT       NOT NULL,
    to_account   BIGINT       NOT NULL,
    amount_paise BIGINT       NOT NULL,
    reason       VARCHAR(120),
    at           TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT audit_events_event_known CHECK (event IN ('TRANSFER_ATTEMPTED', 'TRANSFER_COMPLETED', 'TRANSFER_FAILED')),
    CONSTRAINT audit_events_reason_on_failure CHECK ((event = 'TRANSFER_FAILED') = (reason IS NOT NULL)),
    -- One outcome per attempt: never both COMPLETED and FAILED.
    CONSTRAINT audit_events_one_per_attempt UNIQUE (attempt_id, event)
);

CREATE UNIQUE INDEX audit_events_one_outcome ON audit_events (attempt_id) WHERE event <> 'TRANSFER_ATTEMPTED';
CREATE INDEX audit_events_from ON audit_events (from_account);
CREATE INDEX audit_events_to ON audit_events (to_account);
```

# 3 · Go deeper: Production

Connections  
Each `REQUIRES_NEW` borrows a second connection while the first is held. Under load, a pool smaller than twice the concurrent requests can deadlock on itself.

A crash between the two  
If the app dies after ATTEMPTED and before the outcome, the attempt has no outcome. A nightly check lists attempts older than a few minutes with no outcome, for a person to resolve.

Keep it append-only  
Grant the application INSERT and SELECT on `audit_events`, never UPDATE or DELETE.

Retention  
Audit trails often must be kept for years; plan partitions or archiving from the start.

# 3 · Go deeper: Interview

## Interview takeaways

REQUIRED vs REQUIRES_NEW?

REQUIRED joins the current transaction (or starts one): it commits or rolls back with the caller. REQUIRES_NEW suspends the caller's transaction and runs in a new one that commits independently.

Why does a failure audit need REQUIRES_NEW?

The failure makes the business transaction roll back. Anything written in it, including the audit row, rolls back too. A separate transaction is the only way the row survives.

How do you run code after a transaction commits?

Register a TransactionSynchronization (afterCommit or afterCompletion), or use @TransactionalEventListener with a phase. Data access there must use REQUIRES_NEW.

What does REQUIRES_NEW cost?

A second database connection and transaction per call, held while the outer one waits. It can exhaust the pool, and it can deadlock if the inner transaction needs rows the outer one locked.

Is NESTED the same as REQUIRES_NEW?

No. NESTED uses a savepoint inside the outer transaction: it can roll back on its own, but if the outer transaction rolls back, it goes too.

## Self-check rubric

| Area         | Meets the bar                           | Above the bar                                                      |
|--------------|-----------------------------------------|--------------------------------------------------------------------|
| Correctness  | All 9 tests pass.                       | You switched REQUIRES_NEW off and saw the trail lose its failures. |
| Propagation  | REQUIRED vs REQUIRES_NEW.               | You can explain NESTED and the connection cost.                    |
| Outcome      | Written after completion.               | You covered a caller's rollback, not only an exception.            |
| Audit design | One outcome per attempt, in the schema. | A plan for attempts with no outcome.                               |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any record that must survive a failure:

- Which transaction is this row written in, and what happens to it if that transaction rolls back?
- Is "it worked" recorded before or after the commit?
- Does a nested transaction lock rows the outer one also needs?
- Could the pool run out of connections when every request opens two?
