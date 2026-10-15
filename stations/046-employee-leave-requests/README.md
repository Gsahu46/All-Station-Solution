# Station 046 · Employee leave requests

Foundations · 0–1 years · Core · HR SaaS · Types: Database

Spring Boot 4.1.1 · Java 25 · Spring Data JPA (Hibernate 7) · @Transactional · @Version · @DataJpaTest · PostgreSQL 17 · Flyway · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Employees, balances and requests are demo data, not Teamdesk's. Approving creates a record and changes a number; no payroll, calendar or email is involved. Weekends are free; public holidays are not modelled (a demo rule).

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 18 tests.

# 1 · Understand

## The problem in real life

1.  **The balance that did not move**

    Teamdesk's HR found employees with approved leave and an untouched balance. The manager's screen had shown the right number at approval: 12 days, 3 approved, 9 left.

2.  **It depended on the method**

    Approvals from the mobile app were fine; approvals from the web inbox were not. Both called the same lines of code, but only one of them ran inside a transaction.

3.  **The fix**

    One transactional service method that loads the request and the employee, changes both, and lets Hibernate write both at commit.

A change to an object is saved only while Hibernate is watching it, and Hibernate watches only inside a transaction.

## What are we building?

An employee asks for leave (`POST /leave-requests`); a manager approves it (`POST /leave-requests/{id}/approval`), which marks the request approved and takes the days off the balance; anyone can read the balance (`GET /employees/{id}/leave-balance`). The request and the balance always change together.

## An everyday analogy

A clerk with a desk. While the cards are on the desk, any correction goes into the file when the clerk closes for the day. A photocopy taken home can be corrected all evening; the file never hears of it. The old code corrected the photocopy of the employee's card, and refiled only the leave form.

## How it works in 4 steps

1.  **The approval starts** a transaction, with a fresh persistence context.
2.  **It loads** the request and its employee: both are now managed.
3.  **It checks and changes** them in memory: status APPROVED, balance minus the days.
4.  **At commit**, Hibernate finds both changes and writes both rows, or neither.

Check yourself: the fixed `approve` never calls `save()`. How do the changes reach the database?

Both entities were loaded inside the transaction, so they are managed. At commit, Hibernate compares them with what it loaded (dirty checking) and writes an UPDATE for each one that changed.

## What this station is not

- **No login.** Anyone may approve; a real desk checks the manager.
- **No holidays or half days.** Monday to Friday count; nothing else is modelled.
- **No overlap check.** Two requests for the same days are both accepted.

## Key terms

| Term                    | Simple meaning                                                                                    | Everyday example                                                 | In this project               |
|-------------------------|---------------------------------------------------------------------------------------------------|------------------------------------------------------------------|-------------------------------|
| **Entity**              | A Java object that stands for one row of a table.                                                 | A file card for one employee.                                    | `Employee`, `LeaveRequest`    |
| **Persistence context** | The set of entities Hibernate is watching during one transaction.                                 | The cards on the clerk's desk right now.                         | One per `@Transactional` call |
| **Managed**             | An entity inside the persistence context: its changes are saved by themselves.                    | A card on the desk: any edit goes into the file at closing time. | Inside `LeaveDesk.approve`    |
| **Detached**            | An entity whose transaction has ended: changes stay in memory.                                    | A photocopy taken home: editing it changes nothing in the file.  | What the old desk worked on   |
| **Dirty checking**      | At commit, Hibernate compares each managed entity with what it loaded and writes the differences. | The clerk checking every card on the desk before filing.         | No `save()` in `approve`      |
| **`@Transactional`**    | Runs a method in one transaction: one persistence context, one commit or one rollback.            | One sitting at the desk.                                         | `LeaveDesk`                   |

# 2 · Build: Spec

## Business problem

**Teamdesk** (a fictional HR SaaS) approves leave and keeps each employee's balance. Approvals saved the request but sometimes not the balance, depending on which code path ran.

## Acceptance criteria

1.  **Given** Asha asks for Friday 6 to Tuesday 10 November 2026, **then** `201`, 3 working days, PENDING, and her balance is still 12.
2.  **Given** the manager approves it, **then** `200`, and both the response and `GET` show 9.
3.  **Given** it is approved again, **then** `409` and the balance stays 9.
4.  **Given** Rohan has 2 days and asks for 3, **then** approval is `422` and nothing changes.
5.  **Given** 8 managers approve the same request at the same moment, **then** one `200`, seven `409`, and 3 days are taken once.
6.  **Given** a malformed body, `400`; impossible dates or an unknown employee, `422`; an unknown request or employee in the path, `404`.

## Requirements

- Approval changes the request and the balance in one transaction.
- A balance never goes below zero, and a request is approved at most once, also in the database.
- Days are counted on the server: Monday to Friday, at most 42 calendar days per request (demo rules).
- Two approvals at once never lose a deduction.

## Learning objectives

- Explain the persistence context: managed and detached entities, dirty checking.
- Put `@Transactional` on the service method that owns a business change.
- Know what `save()` does on a managed entity (nothing) and on a detached one (merge, returning a copy).
- Write a `@DataJpaTest`, and know what its automatic transaction can hide.

# 2 · Build: API contract

## Endpoints

| Method | Path                            | Purpose                                                                                                     |
|--------|---------------------------------|-------------------------------------------------------------------------------------------------------------|
| `POST` | `/leave-requests`               | Ask for leave: `employeeId`, `startDate`, `endDate` (inclusive, ISO dates), `reason` (1 to 200 characters). |
| `POST` | `/leave-requests/{id}/approval` | Approve a pending request: the days come off the balance.                                                   |
| `GET`  | `/employees/{id}/leave-balance` | The employee's balance in working days.                                                                     |

## Status codes

| Status | When                                                                                      |
|--------|-------------------------------------------------------------------------------------------|
| 201    | Request created, PENDING                                                                  |
| 200    | Approved; or the balance                                                                  |
| 400    | A field missing or malformed                                                              |
| 404    | No such request or employee in the path                                                   |
| 409    | Already decided, or another approval changed it at the same moment (reload and retry)     |
| 422    | End before start, weekends only, more than 42 days, unknown employee, or not enough leave |

## Captured examples

Captured with curl from the running app on 15 Oct 2026, in this order, against one fresh database (Asha 12 days, Rohan 2). JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: Asha asks for Friday to Tuesday

**Why:** 5 dates, 3 working days; PENDING.

Request

``` code
POST /leave-requests HTTP/1.1
Content-Type: application/json

{
  "employeeId": 1,
  "startDate": "2026-11-06",
  "endDate": "2026-11-10",
  "reason": "Sister's wedding in Jaipur"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 137

{
  "id": 1,
  "employeeId": 1,
  "startDate": "2026-11-06",
  "endDate": "2026-11-10",
  "days": 3,
  "reason": "Sister's wedding in Jaipur",
  "status": "PENDING"
}
```

### Case 2: the manager approves

**Why:** 12 − 3 = 9, in the response...

Request

``` code
POST /leave-requests/1/approval HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 75

{
  "requestId": 1,
  "status": "APPROVED",
  "days": 3,
  "employeeId": 1,
  "balanceDays": 9
}
```

### Case 3: Asha's balance

**Why:** ...and in the database. This is the number the old code lost.

Request

``` code
GET /employees/1/leave-balance HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 52

{
  "employeeId": 1,
  "name": "Asha Verma",
  "balanceDays": 9
}
```

### Case 4: the same approval again

**Why:** already decided: `409`.

Request

``` code
POST /leave-requests/1/approval HTTP/1.1
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Leave request 1 is already APPROVED.",
  "instance": "/leave-requests/1/approval",
  "status": 409,
  "title": "Already decided"
}
```

### Case 5: Rohan asks for the same dates

**Why:** a request may exceed the balance; approval decides.

Request

``` code
POST /leave-requests HTTP/1.1
Content-Type: application/json

{
  "employeeId": 2,
  "startDate": "2026-11-06",
  "endDate": "2026-11-10",
  "reason": "Sister's wedding in Jaipur"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 137

{
  "id": 2,
  "employeeId": 2,
  "startDate": "2026-11-06",
  "endDate": "2026-11-10",
  "days": 3,
  "reason": "Sister's wedding in Jaipur",
  "status": "PENDING"
}
```

### Case 6: approving Rohan's request

**Why:** 2 days left, 3 needed: `422`.

Request

``` code
POST /leave-requests/2/approval HTTP/1.1
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "Rohan Iyer has 2 days left; this request needs 3.",
  "instance": "/leave-requests/2/approval",
  "status": 422,
  "title": "Not enough leave"
}
```

### Case 7: Saturday 7 to Sunday 8

**Why:** no working day to take: `422`.

Request

``` code
POST /leave-requests HTTP/1.1
Content-Type: application/json

{
  "employeeId": 1,
  "startDate": "2026-11-07",
  "endDate": "2026-11-08",
  "reason": "Sister's wedding in Jaipur"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "Every date from 2026-11-07 to 2026-11-08 is a weekend.",
  "instance": "/leave-requests",
  "status": 422,
  "title": "No working days"
}
```

### Case 8: request 99

**Why:** `404`.

Request

``` code
POST /leave-requests/99/approval HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No leave request 99.",
  "instance": "/leave-requests/99/approval",
  "status": 404,
  "title": "Leave request not found"
}
```

## What the database kept

Read with psql after the requests above (`docs/captures/rows.txt`). Each approval raised the `version` of both rows it changed.

``` code
 id |    name    | balance_days | version 
----+------------+--------------+---------
  1 | Asha Verma |            9 |       1
  2 | Rohan Iyer |            2 |       0
(2 rows)

 id | employee_id | start_date |  end_date  | days |  status  | version 
----+-------------+------------+------------+------+----------+---------
  1 |           1 | 2026-11-06 | 2026-11-10 |    3 | APPROVED |       1
  2 |           2 | 2026-11-06 | 2026-11-10 |    3 | PENDING  |       0
(2 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                          | What happens                                          | Proved by                                              |
|---------------------------------------------------------------|-------------------------------------------------------|--------------------------------------------------------|
| Friday to Tuesday                                             | 3 working days                                        | `aRequestCountsWorkingDaysAndWaits`                    |
| Approve, then read the balance                                | Both say 9                                            | `approvalTakesTheDaysAndTheBalanceShowsIt`             |
| Approve twice                                                 | `409`, deducted once                                  | `aDecidedRequestCannotBeApprovedAgain`                 |
| Not enough leave                                              | `422`, nothing changes                                | `moreDaysThanTheBalanceIs422AndChangesNothing`         |
| Reversed dates, weekend only, 43 days, unknown employee       | `422`; exactly 42 days is 30 working days and allowed | `impossibleRequestsAre422`                             |
| Negative balance, bad status, dates or days, written directly | Refused by named constraints                          | `namedConstraintsHoldWithoutJava`                      |
| The balance write fails                                       | The request stays PENDING too                         | `whenTheBalanceWriteFailsTheApprovalRollsBackToo`      |
| 8 approvals of one request at once                            | One `200`, seven `409`, 3 days taken                  | `eightManagersApprovingTheSameRequestDeductOnce`       |
| 6 different requests approved at once                         | Each `200` took its days; the rest are `409` or `422` | `approvingDifferentRequestsAtOnceNeverLosesADeduction` |

## The trap

Plausible but wrong

Changing a managed entity outside a transaction and expecting it to be saved.

The old desk, kept in the tests, has no `@Transactional`. Each repository call runs in its own short transaction, so the request and employee it loads are detached when the call returns. It sets the status and the balance, then calls `requests.save(request)`: a merge, which copies the request's own columns and nothing from the employee, because the association is not cascaded. The manager sees 9; the database keeps 12.

The second test runs the very same lines inside a transaction: both rows are saved, with no extra code. That is the "depends on which method ran" in the bug report.

While building, each part was undone once. Removing `@Transactional` from `approve` turned 5 tests red; removing `@Version` from `Employee` 1 (the parallel test with different requests); removing the PENDING check 2; removing the balance check 1. Removing `@Version` from `LeaveRequest` turned none red: every approval also changes the employee, whose version already catches the race. It is kept because rejecting (challenge 1) changes only the request.

``` code
package com.teamdesk.leave;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The first test written for this station: the old approval, run the way production ran it. The same lines save
 * everything or half of it, depending only on whether a transaction was open around them.
 */
class DetachedEntityTrapTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;

    @Test
    void withoutATransactionTheManagerSeesNineButTheDatabaseKeepsTwelve() throws Exception {
        long id = newRequest(1, "2026-11-06", "2026-11-10");
        int shown = new OldLeaveDesk(requests).approve(id);
        assertThat(shown).isEqualTo(9);
        assertThat(statusInTheDatabase(id)).isEqualTo("APPROVED");   // the request was saved...
        assertThat(balanceInTheDatabase(1)).isEqualTo(12);           // ...the balance was not: 3 days of leave for free
    }

    @Test
    void theSameLinesInsideATransactionSaveBoth() throws Exception {
        long id = newRequest(1, "2026-11-06", "2026-11-10");
        transaction.executeWithoutResult(status -> new OldLeaveDesk(requests).approve(id));
        assertThat(statusInTheDatabase(id)).isEqualTo("APPROVED");
        assertThat(balanceInTheDatabase(1)).isEqualTo(9);   // dirty checking wrote the employee too
    }

    @Test
    void theFixedDeskSavesBothWithoutCallingSave() throws Exception {
        long id = newRequest(1, "2026-11-06", "2026-11-10");
        approve(id);
        assertThat(statusInTheDatabase(id)).isEqualTo("APPROVED");
        assertThat(balanceInTheDatabase(1)).isEqualTo(9);
    }
}
```

``` code
package com.teamdesk.leave;

/**
 * The approval as it shipped, kept to reproduce the bug. No @Transactional: each repository call runs in its own
 * short transaction, so the entities it returns are detached the moment it returns.
 */
class OldLeaveDesk {

    private final LeaveRequestRepository requests;

    OldLeaveDesk(LeaveRequestRepository requests) {
        this.requests = requests;
    }

    /** Returns the balance it showed the manager. */
    int approve(long id) {
        LeaveRequest request = requests.findWithEmployeeById(id).orElseThrow();
        request.approve();       // status APPROVED, and the employee's balance goes down: in memory
        requests.save(request);  // merge copies the request's columns; the employee is not cascaded, so its change is dropped
        return request.getEmployee().getBalanceDays();
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
./mvnw test                 # all 18 tests; starts its own PostgreSQL containers
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Delete the `@Transactional` line above `approve` in `LeaveDesk` and run the contract tests.

``` code
./mvnw test -Dtest=LeaveContractTest
```

The approval still answers 9, but the balance read back is 12: without a transaction, the loaded entities are detached and nothing calls `save()`. Put the line back.

## Troubleshooting

| You see                                               | Cause                                                                                                       | Fix                                                                                          |
|-------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------|
| A change in the response but not in the database      | The entity was detached: no transaction around the change.                                                  | Make the change inside a `@Transactional` service method.                                    |
| `@Transactional` on a method, and still nothing saved | It was called from the same class (`this.approve()`), which skips Spring's proxy; or the method is private. | Call it from another bean; keep it non-private.                                              |
| `LazyInitializationException ... no session`          | A lazy association read after the transaction ended.                                                        | Load what you need inside it (`@EntityGraph`), and map to a response there.                  |
| `409 Changed meanwhile`                               | A `@Version` check failed: another approval committed first.                                                | Reload and retry; that is the intended answer.                                               |
| A `@DataJpaTest` passes but the app does not save     | The test's own transaction kept the entities managed.                                                       | Also test through the real entry point, with no test transaction (`DetachedEntityTrapTest`). |

## Project layout

``` tree
stations/046-employee-leave-requests/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/teamdesk/leave/
│   ├── LeaveController.java   ├── LeaveDesk.java   ├── LeaveRequest.java   ├── Employee.java
│   ├── LeaveRequestRepository.java   ├── EmployeeRepository.java   └── LeaveApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__employees_and_leave_requests.sql, V2__demo_team.sql
├── src/test/java/com/teamdesk/leave/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the entities and the database.

#### `src/main/java/com/teamdesk/leave/LeaveController.java`

Does  
Validates the body and calls the desk; turns a failed version check into `409`.

Why  
HTTP only.

Without it  
Transactions started in the controller.

#### `src/main/java/com/teamdesk/leave/LeaveDesk.java`

Does  
Counts working days, creates requests, approves them, reads balances.

Why  
`approve` is one transaction and calls no `save()`.

Without it  
Half-saved approvals.

- The checks (PENDING, enough days) run on the loaded entities, then `request.approve()` changes both.
- The response is built inside the transaction, from the same objects that are about to be written.
- Errors are `ErrorResponseException` with a `ProblemDetail`; the transaction rolls back on them.

#### `src/main/java/com/teamdesk/leave/LeaveRequest.java`

Does  
The leave_requests table, with a lazy link to the employee.

Why  
`approve()` changes two objects; `@Version` guards the row.

Without it  
Two decisions on the same request at once.

#### `src/main/java/com/teamdesk/leave/Employee.java`

Does  
The employees table: name and balance.

Why  
`@Version`: two approvals for one person cannot overwrite each other's deduction.

Without it  
A lost update: 12 − 3 − 3 saved as 9.

#### `src/main/java/com/teamdesk/leave/LeaveRequestRepository.java`

`findWithEmployeeById` loads the request and its employee in one query (`@EntityGraph`).

#### `src/main/java/com/teamdesk/leave/EmployeeRepository.java`

Spring Data repository.

#### `src/main/resources/db/migration/V1__employees_and_leave_requests.sql`

Both tables, version columns, and the named constraints.

#### `src/main/resources/db/migration/V2__demo_team.sql`

Asha (12 days) and Rohan (2 days).

#### `src/main/resources/application.yaml`

open-in-view off, so nothing is managed outside a service transaction; schema validation.

#### `pom.xml`

Data JPA, Flyway, PostgreSQL; `spring-boot-starter-data-jpa-test` for `@DataJpaTest`.

#### `src/main/java/com/teamdesk/leave/LeaveApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by             | Requirement                                           | Test class                   | Result |
|-------------------------|-------------------------------------------------------|------------------------------|--------|
| Every station           | HTTP contract: valid, invalid, not found              | `LeaveContractTest` (7)      | pass   |
| Every station           | Reproduce the failure before the fix                  | `DetachedEntityTrapTest` (3) | pass   |
| Database                | Rollback and constraint tests against a real database | `LeaveDatabaseTest` (4)      | pass   |
| This station's concepts | `@DataJpaTest`: dirty checking, save vs merge         | `LeaveJpaTest` (4)           | pass   |

## Two kinds of test, on purpose

`LeaveJpaTest` is a `@DataJpaTest`: it starts only JPA and wraps every test in a transaction that is rolled back. That is fast and keeps tests independent, and it is also why the old approval passes there (its last test shows it). The other classes start the whole app with no test transaction, exactly as production runs, and that is where the bug shows.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 7, Failures: 0, Errors: 0, Skipped: 0 -- in com.teamdesk.leave.LeaveContractTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.teamdesk.leave.LeaveDatabaseTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.teamdesk.leave.DetachedEntityTrapTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.teamdesk.leave.LeaveJpaTest
[INFO] Tests run: 18, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/teamdesk/leave/DetachedEntityTrapTest.java`

Written first: the old desk without and with a transaction, and the fixed desk.

#### `src/test/java/com/teamdesk/leave/LeaveContractTest.java`

Requests, approvals and balances; every refusal.

#### `src/test/java/com/teamdesk/leave/LeaveDatabaseTest.java`

Named constraints, a rollback across both rows, and approvals in parallel (virtual threads and a start latch).

#### `src/test/java/com/teamdesk/leave/LeaveJpaTest.java`

`@DataJpaTest`: dirty checking, `save()` on managed and detached entities.

#### `src/test/java/com/teamdesk/leave/OldLeaveDesk.java`

The old approval, kept only in tests.

#### `src/test/java/com/teamdesk/leave/ApiTest.java`

Shared setup: resets the demo team before each test.

#### `src/test/java/com/teamdesk/leave/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/teamdesk/leave/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=RejectChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 18 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in (Java files and one migration), all 22 tests pass (18 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Reject a request

Add `POST /leave-requests/{id}/rejection` with a required note: PENDING becomes REJECTED and the balance is untouched. A decided request is `409`.

**Done when:** both tests in `RejectChallengeTest` pass.

Hints

- Same shape as `approve`: load, check PENDING, change, no `save()`.
- Only the request changes here, so its own `@Version` is what stops a rejection racing an approval.

#### `challenge/RejectChallengeTest.java`

``` code
package com.teamdesk.leave;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /leave-requests/{id}/rejection with {"note": "..."} (1 to 200 characters) turns a PENDING request
 * into REJECTED and leaves the balance alone. A request that is already decided is 409; an unknown one is 404.
 */
class RejectChallengeTest extends ApiTest {

    org.springframework.test.web.servlet.ResultActions reject(long id) throws Exception {
        return mvc.perform(post("/leave-requests/{id}/rejection", id).contentType(MediaType.APPLICATION_JSON)
                .content("{\"note\":\"Quarter-end release that week\"}"));
    }

    @Test
    void aRejectionKeepsTheBalance() throws Exception {
        long id = newRequest(1, "2026-11-06", "2026-11-10");
        reject(id).andExpect(status().isOk()).andExpect(jsonPath("$.status").value("REJECTED"));
        mvc.perform(get("/employees/1/leave-balance")).andExpect(jsonPath("$.balanceDays").value(12));
        approve(id).andExpect(status().isConflict());
    }

    @Test
    void anApprovedOrUnknownRequestCannotBeRejected() throws Exception {
        long id = newRequest(1, "2026-11-06", "2026-11-10");
        approve(id).andExpect(status().isOk());
        reject(id).andExpect(status().isConflict());
        reject(999).andExpect(status().isNotFound());
        mvc.perform(post("/leave-requests/{id}/rejection", id).contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Cancel approved leave

Add `POST /leave-requests/{id}/cancellation`: APPROVED becomes CANCELLED and the days go back to the balance, together. Anything else is `409`.

**Done when:** both tests in `CancelChallengeTest` pass.

Hints

- The database refuses the new status until a migration changes `leave_requests_status_known`.
- A refund is the mirror of a deduction: two managed objects, one transaction.

#### `challenge/CancelChallengeTest.java`

``` code
package com.teamdesk.leave;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /leave-requests/{id}/cancellation cancels APPROVED leave: status CANCELLED and the days go back
 * to the balance, both in one transaction. Anything not APPROVED is 409. The database must accept the new status.
 */
class CancelChallengeTest extends ApiTest {

    @Test
    void cancellingApprovedLeaveGivesTheDaysBack() throws Exception {
        long id = newRequest(1, "2026-11-06", "2026-11-10");
        approve(id).andExpect(status().isOk());
        mvc.perform(post("/leave-requests/{id}/cancellation", id)).andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("CANCELLED")).andExpect(jsonPath("$.balanceDays").value(12));
        mvc.perform(get("/employees/1/leave-balance")).andExpect(jsonPath("$.balanceDays").value(12));
        assertThat(statusInTheDatabase(id)).isEqualTo("CANCELLED");
        mvc.perform(post("/leave-requests/{id}/cancellation", id)).andExpect(status().isConflict());
    }

    @Test
    void onlyApprovedLeaveCanBeCancelled() throws Exception {
        long id = newRequest(1, "2026-11-06", "2026-11-10");
        mvc.perform(post("/leave-requests/{id}/cancellation", id)).andExpect(status().isConflict());
        mvc.perform(post("/leave-requests/{id}/cancellation", 999)).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## When the balance lives elsewhere

Teamdesk moves balances to a payroll service with its own database. An approval must now change a row here and a number there, and no single transaction covers both. Sketch what happens when the payroll call fails after the request is APPROVED, and how a manager or a job would notice and repair it.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: run the old approval with no transaction and read both rows back with SQL.
2.  Put the business change in one `@Transactional` service method; load what it changes with one query.
3.  Delete the `save()` calls that only hid the problem.
4.  Add `@Version` and a parallel test, because approvals are clicked twice.

## Design alternatives and trade-offs

| Approach                                        | What it costs                                                                       | Verdict           |
|-------------------------------------------------|-------------------------------------------------------------------------------------|-------------------|
| `@Transactional` service method, dirty checking | Knowing which objects are managed.                                                  | Chosen            |
| No transaction, `save()` each entity            | Two commits: a crash between them leaves half an approval.                          | Fragile           |
| `cascade = MERGE` from request to employee      | Saves the employee by accident from any request merge.                              | Surprising        |
| One SQL `UPDATE ... WHERE balance_days >= ?`    | Fast and race-free for one row, but the status change is a second statement anyway. | Station 042 style |
| `@Transactional` on the controller              | Transactions that include HTTP work; easy to leak.                                  | No                |

## Database design

| Table            | Constraints                                                                                                                                               | Mapped as                                                                   |
|------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| `employees`      | `employees_balance_not_negative`                                                                                                                          | `Employee`, with `@Version`                                                 |
| `leave_requests` | `leave_requests_employee_fk`, `leave_requests_dates_ordered`, `leave_requests_days_range`, `leave_requests_days_fit_dates`, `leave_requests_status_known` | `LeaveRequest`, `@ManyToOne(fetch = LAZY)` to the employee, with `@Version` |

``` code
-- Teamdesk leave: each employee has a balance of working days; a request is approved at most once.
CREATE TABLE employees (
    id           BIGINT PRIMARY KEY,
    name         VARCHAR(80) NOT NULL,
    balance_days INT         NOT NULL,
    version      BIGINT      NOT NULL DEFAULT 0,
    CONSTRAINT employees_balance_not_negative CHECK (balance_days >= 0)
);

CREATE TABLE leave_requests (
    id          BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    employee_id BIGINT       NOT NULL,
    start_date  DATE         NOT NULL,
    end_date    DATE         NOT NULL,
    days        INT          NOT NULL,
    reason      VARCHAR(200) NOT NULL,
    status      VARCHAR(10)  NOT NULL DEFAULT 'PENDING',
    version     BIGINT       NOT NULL DEFAULT 0,
    CONSTRAINT leave_requests_employee_fk FOREIGN KEY (employee_id) REFERENCES employees (id),
    CONSTRAINT leave_requests_dates_ordered CHECK (end_date >= start_date),
    CONSTRAINT leave_requests_days_range CHECK (days BETWEEN 1 AND 30),
    CONSTRAINT leave_requests_days_fit_dates CHECK (days <= end_date - start_date + 1),
    CONSTRAINT leave_requests_status_known CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED'))
);

CREATE INDEX leave_requests_employee ON leave_requests (employee_id);
```

# 3 · Go deeper: Production

Where transactions belong  
On the service method that owns one business change. Not on repositories one by one, and not around HTTP work.

Self-invocation  
`@Transactional` works through a Spring proxy: a call from inside the same class skips it. A classic way to get exactly this station's bug.

open-in-view  
Off here. On (Spring's default), it keeps entities loadable during the response, which hides where the transaction really ends.

Retries  
A `409 Changed meanwhile` is safe to retry after reloading; approval checks PENDING again, so a retry never deducts twice.

Audit  
HR needs who approved what and when; this station keeps only the status. A real system records the decision as its own row.

# 3 · Go deeper: Interview

## Interview takeaways

What is the persistence context?

The set of entities Hibernate tracks in one session, usually one transaction. It returns the same object for the same row, and at flush writes every change it finds by dirty checking.

Why did save() not save the balance?

The request was detached, so save() merged it: Hibernate copied its columns onto a managed copy. The employee association is not cascaded, so the employee's changes were not copied, and the employee itself was never managed.

Is there an update() in Spring Data JPA?

No. save() on a managed entity does nothing; on a new one it persists; on a detached one it merges and returns a different, managed object. Keep using the returned one.

What can @DataJpaTest hide?

Each test runs in a transaction, so code that forgets its own transaction still works in the test. Test the real entry point without a test transaction as well.

How do you stop two approvals deducting twice?

Check the status inside the transaction and add @Version: the second commit finds a changed version and fails, which you answer with 409. A pessimistic lock is the alternative.

## Self-check rubric

| Area                | Meets the bar                              | Above the bar                                             |
|---------------------|--------------------------------------------|-----------------------------------------------------------|
| Correctness         | All 18 tests pass.                         | You removed `@Transactional` and explained the red tests. |
| Transactions        | One service method per business change.    | You can explain self-invocation and open-in-view.         |
| Persistence context | Managed vs detached; no needless `save()`. | What merge returns, and why that matters.                 |
| Testing             | A `@DataJpaTest`.                          | You know when its transaction hides a bug.                |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any JPA change:

- Which method starts the transaction, and does every change happen inside it?
- Is a `@Transactional` method called from its own class, or private?
- Does code keep using the object it passed to `save()` instead of the one returned?
- Could two people change the same row at once, and what stops the second?
