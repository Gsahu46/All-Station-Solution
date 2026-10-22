# Station 083 · On-call doctor roster

Working Systems · 0–2 years · Core · Healthcare · Types: Database, Concurrency, Idempotency

Spring Boot 4.1.1 · Java 25 · SERIALIZABLE transactions and retries · TransactionTemplate · JdbcClient · constraint triggers · PostgreSQL 17 · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The wards, doctors and roster are demo data, not Mediqo's. Nobody is paged: going off call changes a row and records the change.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 13 tests.

# 1 · Understand

## The problem in real life

1.  **Nobody on call**

    At 02:00 two cardiology doctors pressed "go off call" at the same second. Each request counted two doctors on call, decided the other one was staying, and took its own doctor off. Cardiology had nobody on call for 40 minutes.

2.  **Why the check did not help**

    The check was right, the database was right, and the transactions were right one at a time. Together they were wrong: each saw the world before the other's change. The default isolation level, READ COMMITTED, allows that.

3.  **The fix**

    Run the check and the change in a SERIALIZABLE transaction. When two of them cannot both be right, PostgreSQL stops one; it runs again, sees one doctor left, and is refused. A rule in the database checks every writer at commit.

A rule about several rows ("at least one doctor on call") is not protected by the default isolation level. Use SERIALIZABLE and retry, or lock what the rule depends on.

## What are we building?

One endpoint: a doctor goes off call, unless the ward would then have fewer doctors on call than it needs.

## An everyday analogy

Two people share a car to the office and each wants to take the day off. Each looks at the calendar, sees the other is coming in, and books leave. Nobody drives. The fix: whoever books second must look at the calendar again, after the first booking.

## How it works in 4 steps

1.  **Read**: the ward's minimum, the doctor, how many are on call. In a SERIALIZABLE transaction.
2.  **Decide**: refuse if the ward would drop below its minimum; if the doctor is already off, answer the same as before.
3.  **Write**: take the doctor off and record the change.
4.  **Commit, or start again**: if PostgreSQL says another transaction got in the way (40001), run all of it again.

Check yourself: Orthopaedics has three doctors on call and needs one. All three ask to go at once. What happens?

Two go off, one is refused, in whatever order PostgreSQL lets them commit: `threeDoctorsLeavingAtOnceFromAWardThatNeedsOne`. The captures show one real run.

## What this station is not

- **No shifts or times.** "On call" is a yes or no for tonight; challenge 3 adds time ranges.
- **No sign-in.** Any caller can name any doctor; station 077 shows how to check who may.
- **No paging.** Nobody is notified: a row changes and the change is recorded.

## Key terms

| Term                      | Simple meaning                                                                                                         | Everyday example                                             | In this project                        |
|---------------------------|------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------|----------------------------------------|
| **Transaction**           | Several reads and writes that count as one: all happen, or none.                                                       | Paying and getting the receipt together.                     | `TransactionTemplate`                  |
| **Isolation level**       | How much a transaction can see of others that run at the same time.                                                    | Whether you see a colleague's half-filled form.              | READ COMMITTED (default), SERIALIZABLE |
| **Write skew**            | Two transactions each read the same facts, then change different rows; together they break a rule neither broke alone. | Two doctors each checking the other is staying.              | `WriteSkewTrapTest`                    |
| **Serialization failure** | PostgreSQL stops a SERIALIZABLE transaction that cannot fit with another one. SQLState 40001.                          | "Someone changed this while you were deciding: start again." | `Roster.offCall`                       |
| **Retry**                 | Running the whole transaction again from the start after a serialization failure.                                      | Re-reading the board before deciding again.                  | up to 5 attempts in all                |
| **Constraint trigger**    | A database check that runs at commit and can look at many rows.                                                        | A ward sister checking the board before signing it.          | `wards_keep_min_on_call`               |

# 2 · Build: Spec

## Business problem

**Mediqo** (a fictional hospital group): two doctors went off call at the same moment and a ward was left with nobody on call.

## Acceptance criteria

Demo roster: Cardiology needs 1 on call and has dr.sharma and dr.iyer (dr.menon is off); Orthopaedics needs 1 and has dr.bose, dr.khan and dr.rao. Demo rule: a lost race is tried up to 5 times in all.

1.  **Given** two doctors on call and a minimum of one, **when** one goes off, **then** `200` and one on call.
2.  **Given** the last doctor needed, **then** `409` and nothing changes.
3.  **Given** two doctors going off at the same moment, **then** one goes, one is refused; the ward keeps its minimum.
4.  **Given** the same request twice, **then** the same answer and one recorded change, even if the ward is now at its minimum.
5.  **Given** a race lost on every attempt, **then** `503`: try again, nothing changed.
6.  **Given** an unknown ward or doctor, **then** `404`; a name not shaped `dr.name`, `400`.

## Requirements

- The check and the change run in one SERIALIZABLE transaction, retried on SQLState 40001.
- The database refuses, at commit, any change that leaves a ward below its minimum, whoever writes it.
- Every real change is recorded in `roster_changes` in the same transaction.

## Learning objectives

- Explain write skew and why READ COMMITTED allows it.
- Run a transaction at SERIALIZABLE and retry it correctly, the whole transaction from the start.
- Tell a lost race (try again) from a business refusal (409).
- Reproduce a race deterministically with two database connections.

# 2 · Build: API contract

## Endpoint

| Method | Path                       | Purpose                                               |
|--------|----------------------------|-------------------------------------------------------|
| `POST` | `/rosters/{ward}/off-call` | `{doctor}`: take the doctor off call. Safe to repeat. |

## Status codes

| Status | When                                                            |
|--------|-----------------------------------------------------------------|
| 200    | Off call now, or already off (the same answer, nothing changes) |
| 400    | No doctor, or a name not shaped `dr.name`                       |
| 404    | No such ward, or no such doctor on this ward                    |
| 409    | The ward would drop below its minimum                           |
| 503    | The roster kept changing during every attempt: try again        |

## Captured examples

Captured with curl from the running app on 22 Oct 2026, in this order. JSON bodies are indented for reading; `Date`, connection and standard security headers are left out.

### Case 1: dr.sharma goes off call

**Why:** dr.iyer stays: one on call, the minimum.

Request

``` code
POST /rosters/cardiology/off-call HTTP/1.1
Content-Type: application/json

{
  "doctor": "dr.sharma"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 74

{
  "ward": "cardiology",
  "doctor": "dr.sharma",
  "onCall": false,
  "onCallInWard": 1
}
```

### Case 2: dr.iyer asks to go too

**Why:** Cardiology would have nobody: `409`.

Request

``` code
POST /rosters/cardiology/off-call HTTP/1.1
Content-Type: application/json

{
  "doctor": "dr.iyer"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Cardiology needs at least 1 doctor on call",
  "instance": "/rosters/cardiology/off-call",
  "status": 409,
  "title": "Conflict"
}
```

### Case 3: dr.sharma's app sends it again

**Why:** already off: the same answer, no second change, and no `409` although the ward is at its minimum.

Request

``` code
POST /rosters/cardiology/off-call HTTP/1.1
Content-Type: application/json

{
  "doctor": "dr.sharma"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 74

{
  "ward": "cardiology",
  "doctor": "dr.sharma",
  "onCall": false,
  "onCallInWard": 1
}
```

### Case 4: a ward that does not exist

**Why:** `404`.

Request

``` code
POST /rosters/neurology/off-call HTTP/1.1
Content-Type: application/json

{
  "doctor": "dr.sharma"
}
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No such ward",
  "instance": "/rosters/neurology/off-call",
  "status": 404,
  "title": "Not Found"
}
```

### Case 5: a name not shaped dr.name

**Why:** `400`.

Request

``` code
POST /rosters/cardiology/off-call HTTP/1.1
Content-Type: application/json

{
  "doctor": "Sharma"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/rosters/cardiology/off-call",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 6a: dr.bose, at the same moment as 6b and 6c

**Why:** the three Orthopaedics requests were sent together. Which two go depends on timing; two of three always do.

Request

``` code
POST /rosters/orthopaedics/off-call HTTP/1.1
Content-Type: application/json

{
  "doctor": "dr.bose"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Orthopaedics needs at least 1 doctor on call",
  "instance": "/rosters/orthopaedics/off-call",
  "status": 409,
  "title": "Conflict"
}
```

### Case 6b: dr.khan

**Why:** see 6a.

Request

``` code
POST /rosters/orthopaedics/off-call HTTP/1.1
Content-Type: application/json

{
  "doctor": "dr.khan"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 74

{
  "ward": "orthopaedics",
  "doctor": "dr.khan",
  "onCall": false,
  "onCallInWard": 1
}
```

### Case 6c: dr.rao

**Why:** see 6a.

Request

``` code
POST /rosters/orthopaedics/off-call HTTP/1.1
Content-Type: application/json

{
  "doctor": "dr.rao"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 73

{
  "ward": "orthopaedics",
  "doctor": "dr.rao",
  "onCall": false,
  "onCallInWard": 2
}
```

## The roster and the recorded changes afterwards

``` code
     ward     |  doctor   | on_call 
--------------+-----------+---------
 cardiology   | dr.iyer   | t
 cardiology   | dr.menon  | f
 cardiology   | dr.sharma | f
 orthopaedics | dr.bose   | t
 orthopaedics | dr.khan   | f
 orthopaedics | dr.rao    | f
(6 rows)
```

``` code
     ward     |  doctor   | went 
--------------+-----------+------
 cardiology   | dr.sharma | off
 orthopaedics | dr.rao    | off
 orthopaedics | dr.khan   | off
(3 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                    | What happens                                  | Proved by                                            |
|-----------------------------------------|-----------------------------------------------|------------------------------------------------------|
| One of two goes off                     | `200`, one on call                            | `aDoctorGoesOffCallWhileAnotherStaysOn`              |
| The last one needed                     | `409`, nothing changes                        | `theLastDoctorOnCallCannotGo`                        |
| Unknown ward or doctor; a bad name      | `404`; `400`                                  | `unknownWardsAndDoctorsAre404AndBadNamesAre400`      |
| The same request twice                  | The same answer, one recorded change          | `theSameOffCallTwiceChangesTheRosterOnce`            |
| A retry once the ward is at its minimum | `200`, not `409`: the change already happened | `aRetryIsNotRefusedEvenWhenTheWardIsNowAtItsMinimum` |
| Two doctors at once                     | One goes, one `409`, after a retry            | `twoDoctorsLeavingAtOnceLeaveOneOnCall`              |
| Three doctors at once, minimum one      | Two go, one `409`                             | `threeDoctorsLeavingAtOnceFromAWardThatNeedsOne`     |
| A race lost on every attempt            | `503`, nothing changed                        | `aLostRaceWithNoRetriesLeftIs503AndChangesNothing`   |
| Plain SQL leaving a ward with nobody    | Refused at commit by `wards_keep_min_on_call` | `aWardIsNeverLeftWithoutItsMinimumByAnyWriter`       |
| Other rules written by plain SQL        | Refused by named constraints                  | `otherRulesHoldWithoutJava`                          |
| The change record cannot be written     | The doctor stays on call                      | `anOffCallWhoseRecordFailsChangesNothing`            |

## The trap

Plausible but wrong

Assuming READ COMMITTED prevents write skew.

- **The old code, READ COMMITTED.** The test opens two real database connections and runs them step by step: both count two doctors on call, both take their own doctor off. They change different rows, so nothing waits and nothing conflicts. Both commit: Cardiology has nobody.
- **The same steps, SERIALIZABLE.** The first commit succeeds; the second fails with SQLState 40001, and one doctor stays on call. The app then runs the second request again from the start, and it is refused with `409`.

The ward rule in the database is switched off in this test, because the old schema had none and because only isolation is tested here.

While building, each part was undone once: READ COMMITTED instead of SERIALIZABLE turned 1 test red; no retry 2; no minimum check 1; no database rule 3; no "already off" answer 2; the lost race not turned into a `503` 1; no change record 3; a minimum of 0 allowed 1. With READ COMMITTED, the parallel tests still ended with one doctor on call: the database rule refused the second commit. Only the check that a retry happened failed. See Tests.

``` code
package com.mediqo.roster;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.SQLException;
import java.sql.Statement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.catchThrowable;

/**
 * Written first. The old code ran "count the doctors on call; if more than one, take me off" in a READ COMMITTED
 * transaction, the default. Two doctors at the same moment each counted two, each took themselves off, and the
 * ward had nobody. These tests drive two real database transactions step by step, so the bad order happens every time.
 */
class WriteSkewTrapTest extends ApiTest {

    @Autowired
    DataSource dataSource;

    Connection begin(int isolation) throws SQLException {
        Connection c = dataSource.getConnection();
        c.setAutoCommit(false);
        c.setTransactionIsolation(isolation);
        return c;
    }

    static int countOnCall(Connection c) throws SQLException {
        try (var rs = c.createStatement().executeQuery("SELECT count(*) FROM roster WHERE ward = 'cardiology' AND on_call")) {
            rs.next();
            return rs.getInt(1);
        }
    }

    static void goOff(Connection c, String doctor) throws SQLException {
        try (Statement s = c.createStatement()) {
            s.executeUpdate("UPDATE roster SET on_call = false WHERE ward = 'cardiology' AND doctor = '" + doctor + "'");
        }
    }

    @Test
    void underReadCommittedBothDoctorsLeftAndTheWardHadNobody() throws Exception {
        jdbc.sql("ALTER TABLE roster DISABLE TRIGGER wards_keep_min_on_call").update();   // the old schema had no such rule
        try (Connection sharma = begin(Connection.TRANSACTION_READ_COMMITTED); Connection iyer = begin(Connection.TRANSACTION_READ_COMMITTED)) {
            assertThat(countOnCall(sharma)).isEqualTo(2);   // "iyer is still on call, I can go"
            assertThat(countOnCall(iyer)).isEqualTo(2);     // "sharma is still on call, I can go"
            goOff(sharma, "dr.sharma");
            goOff(iyer, "dr.iyer");                         // different rows: nothing waits, nothing conflicts
            sharma.commit();
            iyer.commit();
        } finally {
            jdbc.sql("ALTER TABLE roster ENABLE TRIGGER wards_keep_min_on_call").update();
        }
        assertThat(onCall("cardiology")).isZero();
    }

    @Test
    void underSerializableOneOfThemIsStopped() throws Exception {
        jdbc.sql("ALTER TABLE roster DISABLE TRIGGER wards_keep_min_on_call").update();   // only isolation is tested here
        Throwable stopped;
        try (Connection sharma = begin(Connection.TRANSACTION_SERIALIZABLE); Connection iyer = begin(Connection.TRANSACTION_SERIALIZABLE)) {
            countOnCall(sharma);
            countOnCall(iyer);
            goOff(sharma, "dr.sharma");
            goOff(iyer, "dr.iyer");
            sharma.commit();
            stopped = catchThrowable(iyer::commit);
            iyer.rollback();
        } finally {
            jdbc.sql("ALTER TABLE roster ENABLE TRIGGER wards_keep_min_on_call").update();
        }
        assertThat(stopped).isInstanceOf(SQLException.class);
        assertThat(((SQLException) stopped).getSQLState()).isEqualTo("40001");   // could not serialize: run it again
        assertThat(onCall("cardiology")).isEqualTo(1);
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

See write skew with your own eyes in two `psql` sessions. Open two terminals and run in each:

``` code
docker compose exec postgres psql -U mediqo -d mediqo
```

Then type, alternating between them (A, then B, then A...):

``` code
-- A and B:
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT count(*) FROM roster WHERE ward = 'cardiology' AND on_call;   -- both see 2
-- A:
UPDATE roster SET on_call = false WHERE ward = 'cardiology' AND doctor = 'dr.sharma';
-- B:
UPDATE roster SET on_call = false WHERE ward = 'cardiology' AND doctor = 'dr.iyer';
-- A:
COMMIT;
-- B:
COMMIT;
```

A's `COMMIT` succeeds. B's fails with `could not serialize access due to read/write dependencies among transactions`: that is the 40001 the app retries. Put dr.sharma back on call (in A: `UPDATE roster SET on_call = true WHERE ward = 'cardiology' AND doctor = 'dr.sharma';`), then repeat the steps with `BEGIN ISOLATION LEVEL READ COMMITTED`: this time both updates and A's commit pass, and B's `COMMIT` is refused by `wards_keep_min_on_call`, the database rule, not by isolation.

## Troubleshooting

| You see                                                | Cause                                                                                   | Fix                                                                                              |
|--------------------------------------------------------|-----------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| `could not serialize access` (SQLState 40001) as a 500 | A SERIALIZABLE transaction lost a race and nothing retried it.                          | Retry the whole transaction, as `Roster.offCall` does.                                           |
| Parallel tests pass with READ COMMITTED                | The database rule refused the second commit; the answer was right for the wrong reason. | Check that the retry happened (`roster.retries`), and test isolation alone with two connections. |
| `Could not find a valid Docker environment`            | Docker is not running.                                                                  | Start Docker Desktop or the Docker service.                                                      |

## Project layout

``` tree
stations/083-on-call-doctor-roster/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/mediqo/roster/
│   ├── RosterController.java   ├── Roster.java   └── RosterApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__wards_and_roster.sql, V2__demo_roster.sql
├── src/test/java/com/mediqo/roster/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/mediqo/roster/RosterController.java`

Does  
The endpoint.

Why  
Checks the doctor's name shape and hands over to `Roster`.

Without it  
Any string reaching the database.

#### `src/main/java/com/mediqo/roster/Roster.java`

Does  
Going off call, safely when two ask at once.

Why  
One SERIALIZABLE transaction for the check and the change; SQLState 40001 runs it again, up to 5 attempts in all, with a short random wait; then `503`. A doctor already off gets the same answer before any rule is checked.

Without it  
A ward left with nobody when two doctors press at the same second.

- The retry repeats the whole transaction, reads included: retrying only the update would act on what was read before the other change.
- Spring reports 40001 as a `DataAccessException` subclass; the code matches the SQLState, as station 082 does for lock timeouts.
- The "already off" answer comes before the minimum check. The other order refuses a retry with `409` once the ward is at its minimum, although the change was made.
- The `retries` counter is there for tests and dashboards.

#### `src/main/resources/db/migration/V1__wards_and_roster.sql`

Does  
Wards, the roster, recorded changes, and the ward rule.

Why  
A constraint trigger, deferred to commit, refuses any change that leaves a ward below its minimum.

Without it  
A plain SQL fix at night that leaves a ward with nobody.

Its limit, written in the file: two READ COMMITTED transactions committing at the same instant can each miss the other's change, and deleting a roster row is not covered. The application therefore also runs SERIALIZABLE.

#### `src/main/resources/db/migration/V2__demo_roster.sql`

Two wards, six doctors.

#### `src/main/resources/application.yaml`

The demo rule: 5 attempts in all for a lost race.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/mediqo/roster/RosterApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                             | Test class                                        | Result |
|---------------|---------------------------------------------------------|---------------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                | `RosterContractTest` (3)                          | pass   |
| Every station | Reproduce the failure before the fix                    | `WriteSkewTrapTest` (2)                           | pass   |
| Database      | Rollback and constraint tests against a real database   | `RosterDatabaseTest` (3)                          | pass   |
| Concurrency   | A real concurrency test that proves the invariant holds | `RosterConcurrencyTest` (2), `RosterBusyTest` (1) | pass   |
| Idempotency   | A replay test: the same request twice gives one effect  | `OffCallReplayTest` (2)                           | pass   |

The parallel tests run on virtual threads released by one latch. A trigger makes each recorded change take 200 ms to write, so the transactions overlap every time. With READ COMMITTED instead of SERIALIZABLE they still ended with one doctor on call, because the database rule refused the second commit; only the check that a retry happened (`roster.retries`) turned red. That is why the trap test checks isolation alone, with the rule switched off. Removing the `503` changed no test at first; `RosterBusyTest` (1 attempt in all) was added. Found while building.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.roster.RosterConcurrencyTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.roster.OffCallReplayTest
[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.roster.RosterBusyTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.roster.RosterContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.roster.WriteSkewTrapTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.roster.RosterDatabaseTest
[INFO] Tests run: 13, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/mediqo/roster/WriteSkewTrapTest.java`

Written first: two real transactions, step by step, at READ COMMITTED and at SERIALIZABLE.

#### `src/test/java/com/mediqo/roster/RosterConcurrencyTest.java`

Two and three doctors leaving at once through the API.

#### `src/test/java/com/mediqo/roster/RosterBusyTest.java`

No retries left: `503`, nothing changed.

#### `src/test/java/com/mediqo/roster/OffCallReplayTest.java`

The same request twice; a retry once the ward is at its minimum.

#### `src/test/java/com/mediqo/roster/RosterDatabaseTest.java`

The ward rule and named constraints with plain SQL; a change whose record fails changes nothing.

#### `src/test/java/com/mediqo/roster/RosterContractTest.java`

The endpoint through HTTP.

#### `src/test/java/com/mediqo/roster/ParallelApiTest.java`

Shared by the parallel tests: the slow-write trigger and the start latch.

#### `src/test/java/com/mediqo/roster/ApiTest.java`

Shared setup: the demo roster before each test, request helpers.

#### `src/test/java/com/mediqo/roster/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/mediqo/roster/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=HandoverChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 13 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 18 tests pass (13 station tests and 5 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Hand over

`POST /rosters/{ward}/handover {from, to}`: the doctor taking over goes on call and the other goes off, in one transaction, so it works even when the ward is at its minimum. A handover already done answers the same.

**Done when:** both tests in `HandoverChallengeTest` pass.

Hints

- Use the same SERIALIZABLE retry as `offCall`: move it into a method that takes the work.
- The ward rule is checked at commit, so the order of the two updates inside the transaction does not matter to it.

#### `challenge/HandoverChallengeTest.java`

``` code
package com.mediqo.roster;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /rosters/{ward}/handover {from, to}. The doctor taking over goes on call and the other goes off in
 * one transaction, so it works even when the ward is at its minimum. Repeating a done handover changes nothing.
 */
class HandoverChallengeTest extends ApiTest {

    ResultActions handover(String ward, String from, String to) throws Exception {
        return mvc.perform(post("/rosters/{ward}/handover", ward).contentType(MediaType.APPLICATION_JSON)
                .content("{\"from\":\"" + from + "\",\"to\":\"" + to + "\"}"));
    }

    @Test
    void theLastDoctorOnCallCanHandOver() throws Exception {
        offCall("cardiology", "dr.sharma").andExpect(status().isOk());   // dr.iyer is now the only one on call
        handover("cardiology", "dr.iyer", "dr.menon").andExpect(status().isOk()).andExpect(jsonPath("$.onCallInWard").value(1));
        assertThat(jdbc.sql("SELECT doctor FROM roster WHERE ward = 'cardiology' AND on_call").query(String.class).list()).containsExactly("dr.menon");
        assertThat(jdbc.sql("SELECT doctor || ' ' || went FROM roster_changes WHERE doctor <> 'dr.sharma' ORDER BY id").query(String.class).list())
                .containsExactly("dr.menon on", "dr.iyer off");
    }

    @Test
    void aRepeatedHandoverChangesNothingAndAWrongOneIs409Or404() throws Exception {
        handover("cardiology", "dr.iyer", "dr.menon").andExpect(status().isOk());
        handover("cardiology", "dr.iyer", "dr.menon").andExpect(status().isOk());
        assertThat(jdbc.sql("SELECT count(*) FROM roster_changes").query(Integer.class).single()).isEqualTo(2);
        handover("cardiology", "dr.sharma", "dr.iyer").andExpect(status().isOk());       // dr.sharma off, dr.iyer back on
        handover("cardiology", "dr.sharma", "dr.sharma").andExpect(status().isBadRequest());
        handover("cardiology", "dr.iyer", "dr.bose").andExpect(status().isNotFound());   // dr.bose is on another ward
        handover("cardiology", "dr.menon", "dr.sharma").andExpect(status().isOk());
        handover("cardiology", "dr.iyer", "dr.sharma").andExpect(status().isConflict()); // nothing to hand over: dr.sharma is already on
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Raise the minimum

`PUT /rosters/{ward}/minimum {minOnCall}`, 1 to 50. A minimum above the doctors on call right now is refused (`409`), by the API and by the database.

**Done when:** the three tests in `MinimumChallengeTest` pass.

Hints

- Raising the minimum while a doctor goes off is the same write skew from the other side: run it SERIALIZABLE too.
- The V1 rule watches `roster` only. A V3 migration adds a deferred constraint trigger on `wards` named `wards_minimum_is_met`.

#### `challenge/MinimumChallengeTest.java`

``` code
package com.mediqo.roster;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: PUT /rosters/{ward}/minimum {minOnCall}. A minimum above the doctors on call right now is refused (409),
 * by the API and by the database (a V3 migration), because raising it is the same write skew seen from the other side.
 */
class MinimumChallengeTest extends ApiTest {

    ResultActions minimum(String ward, String body) throws Exception {
        return mvc.perform(put("/rosters/{ward}/minimum", ward).contentType(MediaType.APPLICATION_JSON).content(body));
    }

    @Test
    void aHigherMinimumThenStopsTheNextOffCall() throws Exception {
        minimum("cardiology", "{\"minOnCall\": 2}").andExpect(status().isOk()).andExpect(jsonPath("$.minOnCall").value(2));
        offCall("cardiology", "dr.sharma").andExpect(status().isConflict()).andExpect(jsonPath("$.detail").value("Cardiology needs at least 2 doctor on call"));
    }

    @Test
    void aMinimumAboveWhoIsOnCallIsRefused() throws Exception {
        minimum("cardiology", "{\"minOnCall\": 3}").andExpect(status().isConflict()).andExpect(jsonPath("$.detail").value("Cardiology has only 2 doctor on call"));
        minimum("cardiology", "{\"minOnCall\": 0}").andExpect(status().isBadRequest());
        minimum("neurology", "{\"minOnCall\": 1}").andExpect(status().isNotFound());
        assertThat(jdbc.sql("SELECT min_on_call FROM wards WHERE id = 'cardiology'").query(Integer.class).single()).isEqualTo(1);
    }

    @Test
    void theDatabaseRefusesItToo() {
        assertThatThrownBy(() -> jdbc.sql("UPDATE wards SET min_on_call = 3 WHERE id = 'cardiology'").update())
                .hasMessageContaining("wards_minimum_is_met");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## A roster with times

Real rosters are time ranges: dr.iyer is on call from 20:00 to 08:00. Design the table so that a ward never has a moment below its minimum. Which rule can an exclusion constraint (`EXCLUDE USING gist` with `tstzrange`) hold, and which one ("at least one at every moment") still needs SERIALIZABLE or a lock on the ward row? Compare the two ways out of write skew: SERIALIZABLE and retries, or `SELECT ... FOR UPDATE` on the ward row so every change to one ward waits its turn.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: two connections, step by step, at READ COMMITTED.
2.  Run the check and the change in one SERIALIZABLE transaction.
3.  Retry the whole transaction on 40001, a few times, with a short random wait; then `503`.
4.  Add the ward rule to the database, checked at commit, for every other writer.

## Design alternatives and trade-offs

| Approach                                    | What it costs                                                                               | Verdict                   |
|---------------------------------------------|---------------------------------------------------------------------------------------------|---------------------------|
| SERIALIZABLE and retry                      | Retries under heavy contention; every transaction must be safe to run again.                | Chosen                    |
| READ COMMITTED and a Java check             | Write skew: the ward can be left with nobody.                                               | The trap                  |
| Lock the ward row (`SELECT ... FOR UPDATE`) | No retries; every change to one ward waits in line, and every writer must remember to lock. | Good, if all writers lock |
| A counter column on wards, with a CHECK     | One row holds the rule; the counter must be kept in step with the roster.                   | Works, more to keep right |
| Only the database trigger                   | Catches most races at commit, but two commits at the same instant can both pass.            | A safety net, not the fix |

## Database design

| Object                             | What                                   | Why                                                                                                 |
|------------------------------------|----------------------------------------|-----------------------------------------------------------------------------------------------------|
| `wards_keep_min_on_call`           | Constraint trigger, deferred to commit | The rule spans rows, so a CHECK cannot hold it; checked once, after all changes in the transaction. |
| `wards_min_on_call_positive`       | CHECK                                  | A ward needs at least one doctor on call.                                                           |
| `roster_pk`, `roster_doctor_shape` | Primary key, CHECK                     | One row per doctor per ward; names shaped `dr.name`.                                                |
| `roster_changes_went`              | CHECK                                  | A change is off or on.                                                                              |

**Transaction boundary:** one SERIALIZABLE transaction reads the ward, the doctor and the count, updates the roster and records the change. A retry starts a new one.

``` code
CREATE TABLE wards (
    id          text CONSTRAINT wards_pk PRIMARY KEY,
    name        text NOT NULL,
    min_on_call integer NOT NULL,
    CONSTRAINT wards_min_on_call_positive CHECK (min_on_call >= 1)
);

CREATE TABLE roster (
    ward    text NOT NULL CONSTRAINT roster_ward_fk REFERENCES wards,
    doctor  text NOT NULL,
    on_call boolean NOT NULL,
    CONSTRAINT roster_pk PRIMARY KEY (ward, doctor),
    CONSTRAINT roster_doctor_shape CHECK (doctor ~ '^dr\.[a-z]{2,30}$')
);

-- One row per real change: who went off or on call, and when.
CREATE TABLE roster_changes (
    id        bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT roster_changes_pk PRIMARY KEY,
    ward      text NOT NULL,
    doctor    text NOT NULL,
    went      text NOT NULL,
    changed_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT roster_changes_went CHECK (went IN ('off', 'on'))
);

-- The rule for every writer: a ward never has fewer doctors on call than its minimum. It spans rows, so it is a
-- constraint trigger, checked at commit. Its limit: two READ COMMITTED transactions committing at the same instant
-- can each see the other's change as not yet committed. The application therefore also runs SERIALIZABLE.
-- It watches changes of on_call; deleting a roster row is not covered (this API never deletes one).
CREATE FUNCTION wards_keep_min_on_call() RETURNS trigger AS $$
DECLARE
    on_call_now integer;
    minimum integer;
BEGIN
    SELECT count(*) FILTER (WHERE r.on_call), w.min_on_call INTO on_call_now, minimum
    FROM wards w LEFT JOIN roster r ON r.ward = w.id WHERE w.id = NEW.ward GROUP BY w.min_on_call;
    IF on_call_now < minimum THEN
        RAISE EXCEPTION 'wards_keep_min_on_call: % has % on call, needs %', NEW.ward, on_call_now, minimum USING ERRCODE = 'check_violation';
    END IF;
    RETURN NULL;
END $$ LANGUAGE plpgsql;
CREATE CONSTRAINT TRIGGER wards_keep_min_on_call AFTER UPDATE OF on_call ON roster
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION wards_keep_min_on_call();
```

# 3 · Go deeper: Production

Retries are part of SERIALIZABLE  
PostgreSQL's documentation says applications using it must be ready to retry. Retry the whole transaction, never with side effects (emails, calls) inside it.

Count the retries  
A rising retry or `503` count means contention: many writers on the same rows. Lock the ward row instead, or split the work.

Read-only transactions  
Screens that only show the roster can run READ COMMITTED; only the decide-then-write paths need SERIALIZABLE.

Every writer  
Night fixes in `psql` skip the API. The database rule covers them, within its limit.

# 3 · Go deeper: Interview

## Interview takeaways

What is write skew?

Two transactions read the same facts, each changes a different row based on them, and together they break a rule neither broke alone. No row is written twice, so row locks do not see it.

Does READ COMMITTED prevent it? REPEATABLE READ?

No to both in PostgreSQL. REPEATABLE READ gives each transaction a fixed snapshot, but both snapshots still show the other doctor on call. SERIALIZABLE detects it.

What must you do when you use SERIALIZABLE?

Retry on SQLState 40001: run the whole transaction again from the start, a limited number of times, with a short random wait.

How else can you prevent write skew?

Lock a row that every writer touches (the ward), or turn the rule into one row with a CHECK (a counter). Both make the writers meet on one row.

How do you test it?

Drive two connections step by step so the bad order happens every time; then a parallel test through the API, checked to fail without the fix.

## Self-check rubric

| Area        | Meets the bar                  | Above the bar                                                                               |
|-------------|--------------------------------|---------------------------------------------------------------------------------------------|
| Correctness | All 13 tests pass.             | You ran the flawed version and explained each failure.                                      |
| Isolation   | SERIALIZABLE for the decision. | You can show write skew with two connections and explain why REPEATABLE READ is not enough. |
| Retries     | 40001 retried.                 | The whole transaction, bounded, with a random wait, and a 503 at the end.                   |
| Proof       | A parallel test.               | One that fails without the fix, and a database rule for other writers.                      |

# 3 · Go deeper: Review

## The pull request

A teammate simplifies `Roster`: "the retry loop is complicated; if PostgreSQL stops us, someone else changed the ward, so refuse". They also move the minimum check to the top, "safety first". Read the file and list every problem before opening the findings.

#### `review/Roster.java`

``` code
package com.mediqo.roster;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DataAccessException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.sql.SQLException;
import java.util.concurrent.atomic.AtomicInteger;

@Service
class Roster {

    record OffCall(String ward, String doctor, boolean onCall, int onCallInWard) {
    }

    private record Ward(String name, int minOnCall) {
    }

    private final JdbcClient jdbc;
    private final TransactionTemplate serializable;
    private final int attempts;
    /** How many times a lost race was retried, for tests and dashboards. */
    final AtomicInteger retries = new AtomicInteger();

    Roster(JdbcClient jdbc, PlatformTransactionManager transactions, @Value("${mediqo.serializable-attempts}") int attempts) {
        this.jdbc = jdbc;
        this.serializable = new TransactionTemplate(transactions);
        this.serializable.setIsolationLevel(TransactionDefinition.ISOLATION_SERIALIZABLE);
        this.attempts = attempts;
    }

    /**
     * "Is someone else still on call? Then I may go." Two doctors asking at once each see the other on call: write
     * skew. Under SERIALIZABLE, PostgreSQL notices that the two transactions cannot both be right and fails one with
     * SQLState 40001; it is then run again from the start, sees the truth, and is refused.
     */
    OffCall offCall(String ward, String doctor) {
        try {
            return serializable.execute(s -> tryOffCall(ward, doctor));
        } catch (DataAccessException e) {
            // Someone else changed the ward at the same moment, so they won: refuse this one. No retry loop needed.
            if (sqlState(e, "40001") || e instanceof DataIntegrityViolationException) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "This ward needs a doctor on call");
            }
            throw e;
        }
    }

    private OffCall tryOffCall(String ward, String doctor) {
        Ward w = jdbc.sql("SELECT name, min_on_call FROM wards WHERE id = ?").param(ward).query(Ward.class).optional()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "No such ward"));
        boolean onCall = jdbc.sql("SELECT on_call FROM roster WHERE ward = ? AND doctor = ?").params(ward, doctor).query(Boolean.class).optional()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "No such doctor on this ward"));
        int onCallNow = jdbc.sql("SELECT count(*) FROM roster WHERE ward = ? AND on_call").param(ward).query(Integer.class).single();
        // The safety rule comes first, before anything else.
        if (onCallNow - 1 < w.minOnCall()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, w.name() + " needs at least " + w.minOnCall() + " doctor on call");
        }
        if (!onCall) {
            return new OffCall(ward, doctor, false, onCallNow);   // already off: the same answer, nothing changes
        }
        jdbc.sql("UPDATE roster SET on_call = false WHERE ward = ? AND doctor = ?").params(ward, doctor).update();
        jdbc.sql("INSERT INTO roster_changes (ward, doctor, went) VALUES (?, ?, 'off')").params(ward, doctor).update();
        return new OffCall(ward, doctor, false, onCallNow - 1);
    }

    static boolean sqlState(DataAccessException e, String state) {
        return e.getMostSpecificCause() instanceof SQLException sql && state.equals(sql.getSQLState());
    }
}
```

## Findings

1A lost race answered as a refusal

"If PostgreSQL stopped us, the other doctor won": not always. Two Orthopaedics doctors may both go (three on call, one needed), but SERIALIZABLE can still stop one of them. Without a retry, that doctor is told the ward needs them, which is false. A 40001 means "run again", not "no".

**Test evidence:** `twoDoctorsLeavingAtOnceLeaveOneOnCall`, `threeDoctorsLeavingAtOnceFromAWardThatNeedsOne` and `aLostRaceWithNoRetriesLeftIs503AndChangesNothing` fail.

2The safety rule before the "already off" answer

"Safety first" sounds right, but a phone that retries after a timeout now gets `409` once the ward is at its minimum, although its doctor did go off. The app shows an error for a change that happened.

**Test evidence:** `aRetryIsNotRefusedEvenWhenTheWardIsNowAtItsMinimum` fails.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class              | Fixed version | Flawed version |
|-------------------------|---------------|----------------|
| `RosterContractTest`    | 3 / 3         | 3 / 3          |
| `RosterDatabaseTest`    | 3 / 3         | 3 / 3          |
| `WriteSkewTrapTest`     | 2 / 2         | 2 / 2          |
| `OffCallReplayTest`     | 2 / 2         | 1 / 2          |
| `RosterBusyTest`        | 1 / 1         | 0 / 1          |
| `RosterConcurrencyTest` | 2 / 2         | 0 / 2          |

The ward is never left with nobody in the flawed version: SERIALIZABLE and the database rule still hold. What breaks is the answer: doctors refused who were allowed to go, and retries told "no" for a change already made.
