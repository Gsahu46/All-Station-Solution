# Station 100 · Expiring unpaid hotel holds

Working Systems · 0–2 years · Core · Travel · Types: Database, Concurrency, Idempotency

Spring Boot 4.1.1 · Java 25 · @Scheduled (fixed delay) · idempotent batch UPDATE ... RETURNING · FOR UPDATE SKIP LOCKED · Idempotency-Key · JdbcClient · PostgreSQL 17 · Testcontainers · Awaitility. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The hotel, its rooms and the guests are demo data. No payment happens: a hold only reserves a room in the database for 15 minutes.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 13 tests.

# 1 · Understand

## The problem in real life

1.  **Rooms that never come back**

    On Ghoomo, a guest holds a room while paying. Many never pay. With no clean-up, their holds blocked rooms for days during the Christmas rush.

2.  **Two servers, one job**

    A clean-up job fixed that, until a second server was added. Both ran the job at the same moment, both found the same expired hold, and both gave its room back: the hotel thought it had a free room it did not have, and sold it twice.

3.  **The fix**

    The job runs on every server, but expiring a hold and giving its room back happen in one statement that only touches holds still held. Whoever runs it, however often, each room comes back once.

A scheduled job will run on every server. Write it so running it twice at once is harmless.

## What are we building?

Room holds that last 15 minutes, a clean-up job that frees the rooms of unpaid ones, and a hold request that is safe to retry.

## An everyday analogy

Two watchmen do the same round. If each one hands back the keys of every room past its time, a room's key is handed back twice and the counter thinks two rooms are free. If the rule is "take the key off the hook only if it is still on the hook", the second watchman finds nothing to do.

## How it works in 4 steps

1.  **Hold**: take a room if one is free, in one statement, and record the hold for 15 minutes.
2.  **Retry**: the same Idempotency-Key and request return the same hold, not a second room.
3.  **Expire**: every 30 s, each server marks holds that are due and still held as expired, and gets back which rooms they had.
4.  **Give back**: only those rooms, in the same transaction.

Check yourself: why not just make sure the job runs on one server only?

That helps (and saves work), but it is a promise kept by another system: a lock that expires, a leader that changes. If the job is also harmless when it runs twice, a broken promise costs some wasted work instead of an overbooked hotel. Challenge 3 adds the lock on top.

## What this station is not

- **No payments.** Challenge 1 adds a confirmation; nothing is charged.
- **One night per hold**, one room type per request (demo rules).
- **No sign-in.** Holds show no guest details.

## Key terms

| Term                | Simple meaning                                             | Everyday example                             | In this project          |
|---------------------|------------------------------------------------------------|----------------------------------------------|--------------------------|
| **Hold**            | A room kept for one guest for a short time while they pay. | A shop keeping a dress aside for 15 minutes. | `holds`                  |
| **Scheduled job**   | Code the app runs by itself on a timetable.                | A watchman's round every half hour.          | `@Scheduled`             |
| **Fixed delay**     | The next run starts a set time after the last one ended.   | "Thirty seconds after you finish, go again". | 30 s                     |
| **Cron**            | Runs at set clock times.                                   | "At :00 and :30 of every hour".              | not used                 |
| **Idempotent**      | Doing it twice has the same effect as doing it once.       | Pressing a lift button twice.                | `WHERE status = 'HELD'`  |
| **Idempotency-Key** | A key the client sends so a retried request is recognised. | A token number at the counter.               | `Idempotency-Key` header |

# 2 · Build: Spec

## Business problem

**Ghoomo** (a fictional hotel booking site): unpaid holds block rooms for days; the cleanup job runs twice when there are two servers.

## Acceptance criteria

Demo hotel: 5 deluxe rooms (type 1) and 1 suite (type 2) for each night from 24 to 31 December 2026. Demo rules: a hold lasts 15 minutes; the job checks every 30 s.

1.  **Given** a free room, **then** `201` with the hold and when it expires; none free `409`.
2.  **Given** the same `Idempotency-Key` and request again, **then** `200` with the same hold, even if that took the last room; another request with that key `422`.
3.  **Given** 15 minutes without payment, **then** the job marks the hold `EXPIRED` and the room is free again.
4.  **Given** the job running on several servers at once, **then** each expired hold gives its room back once.
5.  **Given** twenty guests at once for five rooms, **then** exactly five holds.
6.  **Given** no key, a bad date or e-mail, **then** `400`; an unknown night or hold `404`.

## Requirements

- Never more rooms held than there are, in the database too.
- A hold and its room are taken, and given back, in one transaction.
- The job is safe to run on every server at the same moment.

## Learning objectives

- Schedule a job and choose fixed delay or cron.
- Write an idempotent batch update with `UPDATE ... RETURNING` and `SKIP LOCKED`.
- Take a limited resource with one conditional `UPDATE`.
- Make a create request safe to retry with an Idempotency-Key.
- Prove all of it with parallel tests and a clock you move.

# 2 · Build: API contract

## Endpoints

| Method | Path                            | Purpose                                                      |
|--------|---------------------------------|--------------------------------------------------------------|
| `POST` | `/holds` with `Idempotency-Key` | Hold a room for one night: `{roomTypeId, date, guestEmail}`. |
| `GET`  | `/holds/{id}`                   | A hold and its status: `HELD` or `EXPIRED`.                  |

The Idempotency-Key header is the one described in *The Idempotency-Key HTTP Header Field*, an Internet-Draft of the IETF httpapi working group: a draft, not a standard.

## Status codes

| Status | When                                                   |
|--------|--------------------------------------------------------|
| 201    | Hold created                                           |
| 200    | The same key and request again: the same hold; a read  |
| 400    | No or a malformed key; a bad date, e-mail or room type |
| 404    | No such room night, or hold                            |
| 409    | No room of that type is free that night                |
| 422    | The key was used for a different hold                  |

## Captured examples

Captured with curl from the running app on 23 Oct 2026, in this order. To skip 15 minutes of waiting, `docs/capture.sh` moves hold 1's times back 20 minutes in the database; the real job, every 30 s, does the rest. `Date`, connection and standard security headers are left out.

### Case 1: Asha holds the suite for New Year's Eve

**Why:** `201`, held for 15 minutes.

Request

``` code
POST /holds HTTP/1.1
Content-Type: application/json
Idempotency-Key: asha-nye-0001

{
  "roomTypeId": 2,
  "date": "2026-12-31",
  "guestEmail": "asha@example.com"
}
```

Response

``` code
HTTP/1.1 201 
Location: /holds/1
Content-Type: application/json

{
  "id": 1,
  "roomTypeId": 2,
  "date": "2026-12-31",
  "status": "HELD",
  "expiresAt": "2026-10-23T20:25:19.977883Z"
}
```

### Case 2: her app retries

**Why:** `200`, the same hold: although the only suite is taken, it is hers.

Request

``` code
POST /holds HTTP/1.1
Content-Type: application/json
Idempotency-Key: asha-nye-0001

{
  "roomTypeId": 2,
  "date": "2026-12-31",
  "guestEmail": "asha@example.com"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json

{
  "id": 1,
  "roomTypeId": 2,
  "date": "2026-12-31",
  "status": "HELD",
  "expiresAt": "2026-10-23T20:25:19.977883Z"
}
```

### Case 3: the same key, another night

**Why:** `422`.

Request

``` code
POST /holds HTTP/1.1
Content-Type: application/json
Idempotency-Key: asha-nye-0001

{
  "roomTypeId": 2,
  "date": "2026-12-30",
  "guestEmail": "asha@example.com"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "This Idempotency-Key was already used for a different hold.",
  "instance": "/holds",
  "status": 422,
  "title": "Unprocessable Content"
}
```

### Case 4: Ravi wants the suite too

**Why:** `409`.

Request

``` code
POST /holds HTTP/1.1
Content-Type: application/json
Idempotency-Key: ravi-nye-0001

{
  "roomTypeId": 2,
  "date": "2026-12-31",
  "guestEmail": "ravi@example.com"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "No room of this type is free that night.",
  "instance": "/holds",
  "status": 409,
  "title": "Conflict"
}
```

### Case 5: no Idempotency-Key

**Why:** `400`.

Request

``` code
POST /holds HTTP/1.1
Content-Type: application/json

{
  "roomTypeId": 2,
  "date": "2026-12-31",
  "guestEmail": "asha@example.com"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Required header 'Idempotency-Key' is not present.",
  "instance": "/holds",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 6: a night the hotel does not sell

**Why:** `404`.

Request

``` code
POST /holds HTTP/1.1
Content-Type: application/json
Idempotency-Key: asha-jan-0001

{
  "roomTypeId": 2,
  "date": "2027-01-15",
  "guestEmail": "asha@example.com"
}
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No such room type or night.",
  "instance": "/holds",
  "status": 404,
  "title": "Not Found"
}
```

### Case 7: Asha has not paid yet

**Why:** still `HELD`.

Request

``` code
GET /holds/1 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 101

{
  "id": 1,
  "roomTypeId": 2,
  "date": "2026-12-31",
  "status": "HELD",
  "expiresAt": "2026-10-23T20:25:19.977883Z"
}
```

### Case 8: after its time, the job expired it

**Why:** `EXPIRED`, by the scheduled job, not by a request.

Request

``` code
GET /holds/1 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 104

{
  "id": 1,
  "roomTypeId": 2,
  "date": "2026-12-31",
  "status": "EXPIRED",
  "expiresAt": "2026-10-23T20:05:19.977883Z"
}
```

### Case 9: Ravi tries again

**Why:** `201`: the suite is free again.

Request

``` code
POST /holds HTTP/1.1
Content-Type: application/json
Idempotency-Key: ravi-nye-0001

{
  "roomTypeId": 2,
  "date": "2026-12-31",
  "guestEmail": "ravi@example.com"
}
```

Response

``` code
HTTP/1.1 201 
Location: /holds/2
Content-Type: application/json

{
  "id": 2,
  "roomTypeId": 2,
  "date": "2026-12-31",
  "status": "HELD",
  "expiresAt": "2026-10-23T20:25:50.064931Z"
}
```

## The database afterwards

``` code
 id | room_type_id | stay_date  | status  | expired 
----+--------------+------------+---------+---------
  1 |            2 | 2026-12-31 | EXPIRED | t
  2 |            2 | 2026-12-31 | HELD    | f
(2 rows)

 room_type_id | stay_date  | total | held 
--------------+------------+-------+------
            1 | 2026-12-31 |     5 |    0
            2 | 2026-12-31 |     1 |    1
(2 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                | What happens                                           | Proved by                                                           |
|---------------------------------------------------------------------|--------------------------------------------------------|---------------------------------------------------------------------|
| The old job on two servers                                          | One hold, two rooms back; six guests in five rooms     | `theOldJobOnTwoServersGivesOneRoomBackTwiceAndTheHotelIsOverbooked` |
| The API's job on two servers                                        | One room back; the sixth guest `409`                   | `theApiJobOnTwoServersGivesItBackOnce`                              |
| A hold, then 15 minutes                                             | `201`, `409` for the next guest, then expired and free | `aHoldTakesARoomForFifteenMinutesThenExpires`                       |
| One second before its time                                          | Not expired                                            | `aHoldBeforeItsTimeIsNotExpired`                                    |
| No key, bad key, date, e-mail, room type; unknown night or hold     | `400`; `404`; nothing taken                            | `badRequestsAre400AndUnknownThings404`                              |
| Twenty guests at once, five rooms                                   | Exactly five                                           | `twentyGuestsAtOnceForFiveRoomsGetExactlyFive`                      |
| Four job runs at once                                               | Each room back once; then nothing to do                | `fourExpiryRunsAtOnceGiveEachRoomBackOnce`                          |
| The same request twice, on the last room; the key for another night | One hold; `422`                                        | `theSameRequestTwiceIsOneHold`                                      |
| Ten copies at the same moment                                       | One hold, the same id for all                          | `tenCopiesAtTheSameMomentAreOneHold`                                |
| Rules written by plain SQL                                          | Refused by named constraints                           | `roomAndHoldRulesHoldWithoutJava`                                   |
| A hold that cannot be recorded                                      | Its room is given back too                             | `aHoldThatCannotBeRecordedGivesItsRoomBack`                         |
| An expiry that cannot give the room back                            | Nothing expired; the next run does both                | `anExpiryThatCannotGiveTheRoomBackExpiresNothing`                   |
| The real schedule and clock                                         | Expired without anyone asking                          | `anUnpaidHoldExpiresOnItsOwn`                                       |

## The trap

Plausible but wrong

A @Scheduled job that runs on every server at once.

- **The old job.** It reads the expired holds, then for each one gives a room back and marks the hold. On two servers that both read before either writes (the test lines them up with a barrier), one expired hold gives back two rooms: the count says 3 held while 4 are. Two walk-ins are accepted: six guests holding five rooms.
- **The API's job.** The same two runs: one of them expires the hold and gets its room back from `RETURNING`; the other finds nothing still held. One room back, and the second walk-in is `409`.

While building, each part was undone once: no free-room condition turned 3 tests red; no transaction around a hold 2; no transaction around expiry 1 (only after a test made giving the room back fail); no replay check before taking a room 1; e-mails not lower-cased 1; no request check on a reused key 1; no room given back 3; no fallback when two copies race 1. The job's two guards, `SKIP LOCKED` and `AND status = 'HELD'`, were each enough alone in the tests; without both, 2 tests turned red. Both stay: one so servers do not wait for each other, the other so correctness does not depend on the lock.

``` code
package com.ghoomo.holds;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Duration;
import java.time.LocalDate;
import java.util.List;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.Executors;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Christmas Eve, five deluxe rooms, all held; one hold is unpaid and expires. Two servers run the clean-up at the
 * same moment. Written first.
 */
class DoubleExpiryTrapTest extends ApiTest {

    @Autowired
    PlatformTransactionManager transactions;

    void fiveHoldsOneOfThemDue() throws Exception {
        hold("unpaid-0001", 1, "2026-12-24", "late@example.com").andExpect(status().isCreated());
        CLOCK.advance(Duration.ofMinutes(10));
        for (int i = 2; i <= 5; i++) {
            hold("paying-000" + i, 1, "2026-12-24", "guest" + i + "@example.com").andExpect(status().isCreated());
        }
        CLOCK.advance(Duration.ofMinutes(6));   // the first is 16 minutes old: due; the others 6
        assertThat(held(1, "2026-12-24")).isEqualTo(5);
    }

    /** The old job: read what is due, then give each room back and mark the hold, whatever happened in between. */
    void oldJob(CyclicBarrier bothHaveRead) {
        record Due(long id, long roomTypeId, LocalDate stayDate) {
        }
        new TransactionTemplate(transactions).executeWithoutResult(tx -> {
            List<Due> due = jdbc.sql("SELECT id, room_type_id, stay_date FROM holds WHERE status = 'HELD' AND expires_at <= ?")
                    .param(java.time.OffsetDateTime.ofInstant(CLOCK.instant(), java.time.ZoneOffset.UTC)).query(Due.class).list();
            try {
                bothHaveRead.await();   // two servers, the same schedule: both read before either writes
            } catch (Exception e) {
                throw new IllegalStateException(e);
            }
            for (Due d : due) {
                jdbc.sql("UPDATE room_nights SET held = held - 1 WHERE room_type_id = ? AND stay_date = ?").params(d.roomTypeId(), d.stayDate()).update();
                jdbc.sql("UPDATE holds SET status = 'EXPIRED', expired_at = now() WHERE id = ?").param(d.id()).update();
            }
        });
    }

    @Test
    void theOldJobOnTwoServersGivesOneRoomBackTwiceAndTheHotelIsOverbooked() throws Exception {
        fiveHoldsOneOfThemDue();
        CyclicBarrier barrier = new CyclicBarrier(2);
        try (var servers = Executors.newVirtualThreadPerTaskExecutor()) {
            servers.submit(() -> oldJob(barrier));
            servers.submit(() -> oldJob(barrier));
        }
        assertThat(held(1, "2026-12-24")).isEqualTo(3);   // one hold expired, two rooms given back
        hold("walk-in-0001", 1, "2026-12-24", "a@example.com").andExpect(status().isCreated());
        hold("walk-in-0002", 1, "2026-12-24", "b@example.com").andExpect(status().isCreated());
        assertThat(active(1, "2026-12-24")).isEqualTo(6);   // six guests holding five rooms
    }

    @Test
    void theApiJobOnTwoServersGivesItBackOnce() throws Exception {
        fiveHoldsOneOfThemDue();
        int[] expired = new int[2];
        try (var servers = Executors.newVirtualThreadPerTaskExecutor()) {
            servers.submit(() -> expired[0] = holds.expireDue());
            servers.submit(() -> expired[1] = holds.expireDue());
        }
        assertThat(expired[0] + expired[1]).isEqualTo(1);
        assertThat(held(1, "2026-12-24")).isEqualTo(4);
        hold("walk-in-0001", 1, "2026-12-24", "a@example.com").andExpect(status().isCreated());
        hold("walk-in-0002", 1, "2026-12-24", "b@example.com").andExpect(status().isConflict());
        assertThat(active(1, "2026-12-24")).isEqualTo(5);
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

Start the app twice, on two ports, against the same database, and watch both run the job without giving a room back twice:

``` code
./mvnw spring-boot:run -Dspring-boot.run.arguments=--server.port=8081
curl -H 'Content-Type: application/json' -H 'Idempotency-Key: try-it-0001' -d '{"roomTypeId":1,"date":"2026-12-24","guestEmail":"you@example.com"}' http://localhost:8080/holds
```

Wait 15 minutes (or set `ghoomo.holds.ttl=1m`), then read `room_nights`: the room is back once.

## Troubleshooting

| You see                                     | Cause                                                         | Fix                                                              |
|---------------------------------------------|---------------------------------------------------------------|------------------------------------------------------------------|
| Rooms free that are still held              | Releases counted twice: the job read, then wrote.             | Expire with a conditional UPDATE and give back what it returned. |
| The job never runs                          | `@EnableScheduling` missing, or the property switched it off. | Check `ghoomo.holds.expiry.enabled`.                             |
| `Could not find a valid Docker environment` | Docker is not running.                                        | Start Docker Desktop or the Docker service.                      |

## Project layout

``` tree
stations/100-expiring-unpaid-hotel-holds/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/ghoomo/holds/
│   ├── HoldController.java   ├── Holds.java   ├── ExpirySchedule.java   └── HoldsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__room_nights_and_holds.sql, V2__demo_rooms.sql
├── src/test/java/com/ghoomo/holds/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the job and the database.

#### `src/main/java/com/ghoomo/holds/HoldController.java`

Does  
The two endpoints.

Why  
Validates the key and body; `201` or `200` for a replay; when two copies race, answers with the one that won.

Without it  
A retried request taking a second room.

#### `src/main/java/com/ghoomo/holds/Holds.java`

Does  
Taking rooms and expiring holds.

Why  
One conditional UPDATE takes a room; the hold is recorded in the same transaction; the expiry is one UPDATE ... RETURNING over holds still held.

Without it  
Overbooking from two guests at once, a retry, or two servers running the job.

- The replay check comes before taking a room: on a full night, a retry must find the guest's own hold, not "sold out". Found by a test on the one suite.
- The expiry and the rooms it gives back are one transaction: a hold expired without its room back would lose that room for good.
- At most 500 holds per run; the rest wait for the next run.

#### `src/main/java/com/ghoomo/holds/ExpirySchedule.java`

Does  
The timetable.

Why  
A fixed delay of 30 s: runs on one server never overlap.

Without it  
A slow run and the next one stepping on each other.

#### `src/main/resources/db/migration/V1__room_nights_and_holds.sql`

Does  
Rooms per night and holds.

Why  
`held BETWEEN 0 AND total`, one hold per key, states and times that agree.

Without it  
Overbooking by any writer.

#### `src/main/resources/db/migration/V2__demo_rooms.sql`

The demo hotel's rooms.

#### `src/main/resources/application.yaml`

Hold time and the job's interval.

#### `src/main/java/com/ghoomo/holds/HoldsApplication.java`

Entry point, and the `Clock`.

#### `compose.yaml`

PostgreSQL 17 for running the app.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                             | Test class                 | Result |
|---------------|---------------------------------------------------------|----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                | `HoldContractTest` (3)     | pass   |
| Every station | Reproduce the failure before the fix                    | `DoubleExpiryTrapTest` (2) | pass   |
| Database      | Rollback and constraint tests against a real database   | `HoldDatabaseTest` (3)     | pass   |
| Concurrency   | A real concurrency test that proves the invariant holds | `HoldConcurrencyTest` (2)  | pass   |
| Idempotency   | Replay: the same request twice gives one effect         | `HoldReplayTest` (2)       | pass   |

The job is switched off in the tests, which run it themselves at the moment they choose, on a clock they move: 15 minutes pass in an instant. `ScheduledExpiryTest` keeps the real schedule (every 200 ms, holds of 1 s) and waits with Awaitility.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.ghoomo.holds.HoldConcurrencyTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.ghoomo.holds.HoldDatabaseTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.ghoomo.holds.HoldReplayTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.ghoomo.holds.DoubleExpiryTrapTest
[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0 -- in com.ghoomo.holds.ScheduledExpiryTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.ghoomo.holds.HoldContractTest
[INFO] Tests run: 13, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/ghoomo/holds/DoubleExpiryTrapTest.java`

Written first: the old job and the API's, on two servers at once.

#### `src/test/java/com/ghoomo/holds/HoldContractTest.java`

A hold's life; its time to the second; bad and unknown requests.

#### `src/test/java/com/ghoomo/holds/HoldConcurrencyTest.java`

Twenty guests for five rooms; four job runs at once.

#### `src/test/java/com/ghoomo/holds/HoldReplayTest.java`

A retry on the last room; a reused key; ten copies at once.

#### `src/test/java/com/ghoomo/holds/HoldDatabaseTest.java`

Named constraints with plain SQL; two rollbacks.

#### `src/test/java/com/ghoomo/holds/ScheduledExpiryTest.java`

The real schedule and clock.

#### `src/test/java/com/ghoomo/holds/ApiTest.java`

Shared setup: no holds, the job off, the clock at 10:00 on 20 December.

#### `src/test/java/com/ghoomo/holds/TestClock.java`

A clock moved by hand.

#### `src/test/java/com/ghoomo/holds/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/ghoomo/holds/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=ConfirmChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 13 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 16 tests pass (13 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## The guest paid

`POST /holds/{id}/confirmation`, called when payment succeeds (simulated). A hold still within its time becomes `CONFIRMED`, keeps its room and never expires; calling it again is fine. Past its time, swept or not: `409`.

**Done when:** both tests in `ConfirmChallengeTest` pass.

Hints

- A V3 migration widens the status CHECK.
- One UPDATE with the conditions in its WHERE; 0 rows means 404 or 409: read the hold to tell which.
- "Past its time" is `expires_at`, not the status: the job may not have run yet.

#### `challenge/ConfirmChallengeTest.java`

``` code
package com.ghoomo.holds;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /holds/{id}/confirmation, called when the guest has paid (simulated: a status changes, no money
 * moves). A confirmed hold keeps its room and never expires. Too late (expired, or past its time): 409.
 */
class ConfirmChallengeTest extends ApiTest {

    @Test
    void aPaidHoldKeepsItsRoom() throws Exception {
        hold("pays-in-time1", 2, "2026-12-25", "asha@example.com").andExpect(status().isCreated());
        CLOCK.advance(Duration.ofMinutes(10));
        mvc.perform(post("/holds/1/confirmation")).andExpect(status().isOk()).andExpect(jsonPath("$.status").value("CONFIRMED"));
        mvc.perform(post("/holds/1/confirmation")).andExpect(status().isOk());   // a retry of the payment callback: no harm
        CLOCK.advance(Duration.ofHours(1));
        assertThat(holds.expireDue()).isZero();
        assertThat(held(2, "2026-12-25")).isEqualTo(1);
    }

    @Test
    void tooLateIs409() throws Exception {
        hold("pays-late-001", 1, "2026-12-25", "ravi@example.com").andExpect(status().isCreated());
        CLOCK.advance(Duration.ofMinutes(16));   // past its time, not swept yet
        mvc.perform(post("/holds/1/confirmation")).andExpect(status().isConflict());
        holds.expireDue();
        mvc.perform(post("/holds/1/confirmation")).andExpect(status().isConflict());
        mvc.perform(post("/holds/99/confirmation")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Cancel, once

`DELETE /holds/{id}`: the guest gives the room up at once. `204` every time, but the room comes back only once, even when the app sends five DELETEs at the same moment.

**Done when:** the test in `CancelChallengeTest` passes.

Hints

- The same shape as the job: `UPDATE ... WHERE status = 'HELD' RETURNING` the room, then give back only what came back.
- Five at once: the row lock makes four of them find the hold already cancelled.

#### `challenge/CancelChallengeTest.java`

``` code
package com.ghoomo.holds;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: DELETE /holds/{id}: the guest changes their mind and the room is free at once. 204 every time, but
 * the room is given back only once, even when the app sends the DELETE five times at the same moment.
 */
class CancelChallengeTest extends ApiTest {

    @Test
    void aCancelledHoldFreesItsRoomOnce() throws Exception {
        hold("changes-mind1", 1, "2026-12-28", "asha@example.com").andExpect(status().isCreated());
        hold("stays-booked1", 1, "2026-12-28", "ravi@example.com").andExpect(status().isCreated());
        CountDownLatch start = new CountDownLatch(1);
        List<Future<Integer>> answers = new ArrayList<>();
        try (var taps = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 5; i++) {
                answers.add(taps.submit(() -> {
                    start.await();
                    return mvc.perform(delete("/holds/1")).andReturn().getResponse().getStatus();
                }));
            }
            start.countDown();
        }
        assertThat(answers).extracting(Future::resultNow).containsOnly(204);
        assertThat(held(1, "2026-12-28")).isEqualTo(1);   // Ravi's
        mvc.perform(get("/holds/1")).andExpect(jsonPath("$.status").value("CANCELLED"));
        mvc.perform(delete("/holds/99")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Exactly one server

Ghoomo grows to twelve servers. The job is safe on all of them, but twelve runs every 30 s are wasted work, and a nightly job that emails guests must really run once. Compare: a lock table with a lease (ShedLock), `pg_try_advisory_lock`, a leader chosen by the platform (a Kubernetes CronJob), and a queue of due work. What happens to each when the server holding the lock pauses for a minute? Which job still needs to be idempotent, and why all of them?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old job on two servers, lined up with a barrier.
2.  Write the tables: rooms per night with `held BETWEEN 0 AND total`, and holds.
3.  Take a room with one conditional UPDATE; add the Idempotency-Key replay.
4.  Expire with one UPDATE ... RETURNING; prove it with parallel runs and a rollback.

## Design alternatives and trade-offs

| Approach                                      | What it costs                                                                  | Verdict             |
|-----------------------------------------------|--------------------------------------------------------------------------------|---------------------|
| An idempotent job on every server             | Some repeated work, all harmless.                                              | Chosen              |
| Read due holds, then release each             | Two servers release twice: overbooking.                                        | The trap            |
| `synchronized` on the job                     | Only within one server.                                                        | Review finding      |
| A distributed lock (ShedLock)                 | Saves work; a lease can expire under a slow run, so still be idempotent.       | On top, not instead |
| Expire on read ("held and not past its time") | No job needed for correctness, but the room count must be computed from holds. | A valid alternative |

## Fixed delay or cron?

Fixed delay: the next run starts 30 s after the last one ended, so one server's runs never overlap and slow runs space themselves out. Cron (`0/30 * * * * *`): runs at fixed clock times, so every server starts at the same second, which is exactly when the trap bites. Cron fits jobs tied to the clock (a report at 06:00); fixed delay fits "keep things tidy" jobs like this one.

## Database design

| Object                                                                   | What                                   | Why                                                    |
|--------------------------------------------------------------------------|----------------------------------------|--------------------------------------------------------|
| `room_nights_held_range`                                                 | CHECK held BETWEEN 0 AND total         | No overbooking and no negative counts, for any writer. |
| `holds_key_once`                                                         | UNIQUE (idempotency_key)               | A retried request cannot make a second hold.           |
| `holds_room_night`                                                       | Foreign key to the room night          | Only nights the hotel sells.                           |
| `holds_status`, `holds_expired_has_time`, `holds_expires_after_creation` | CHECKs                                 | States and times that agree.                           |
| `holds_due`                                                              | Partial index on expires_at, held only | The job reads only what is waiting.                    |

**Transaction boundaries:** taking a room and recording the hold commit together; so do expiring holds and giving their rooms back.

``` code
-- Rooms of one type on one night: how many there are, how many are held. The rule "never more held than there are"
-- is here, for every writer, not only in Java.
CREATE TABLE room_nights (
    room_type_id bigint NOT NULL,
    stay_date    date   NOT NULL,
    total        int    NOT NULL,
    held         int    NOT NULL DEFAULT 0,
    CONSTRAINT room_nights_pk PRIMARY KEY (room_type_id, stay_date),
    CONSTRAINT room_nights_held_range CHECK (held BETWEEN 0 AND total)
);

-- One hold: one room for one night, while the guest pays (demo rule: one night per hold).
CREATE TABLE holds (
    id              bigserial   PRIMARY KEY,
    idempotency_key text        NOT NULL,
    request_hash    text        NOT NULL,
    room_type_id    bigint      NOT NULL,
    stay_date       date        NOT NULL,
    guest_email     text        NOT NULL,
    status          text        NOT NULL DEFAULT 'HELD',
    created_at      timestamptz NOT NULL,
    expires_at      timestamptz NOT NULL,
    expired_at      timestamptz,
    CONSTRAINT holds_key_once UNIQUE (idempotency_key),
    CONSTRAINT holds_status CHECK (status IN ('HELD', 'EXPIRED')),
    CONSTRAINT holds_expires_after_creation CHECK (expires_at > created_at),
    CONSTRAINT holds_expired_has_time CHECK ((status = 'EXPIRED') = (expired_at IS NOT NULL)),
    CONSTRAINT holds_room_night FOREIGN KEY (room_type_id, stay_date) REFERENCES room_nights
);
CREATE INDEX holds_due ON holds (expires_at) WHERE status = 'HELD';
```

# 3 · Go deeper: Production

Backlog  
500 holds a run, every 30 s, per server. After an outage the backlog clears over a few runs; watch the age of the oldest due hold.

Clocks  
"Now" comes from the app server; servers' clocks drift. Using the database's clock (`now()`) in both the hold and the job removes that, at the cost of testability with a moved clock.

Keys  
Idempotency keys are kept for ever here. Expire old ones (a day) and scope them per client.

Guests  
Tell the guest when the hold ends, and email them when it does: an expired hold is a lost booking.

# 3 · Go deeper: Interview

## Interview takeaways

What happens to a @Scheduled job when you run two instances?

It runs on both, at about the same time. Unless the job is idempotent, its effect happens twice.

How do you make a batch job safe to run twice at once?

Change only rows still in the old state, in one statement, and act on what it returned: UPDATE ... WHERE status = 'HELD' RETURNING. SKIP LOCKED lets runs split the work without waiting.

Fixed delay, fixed rate or cron?

Fixed delay for clean-up (no overlap, self-spacing); fixed rate for steady sampling; cron for clock times.

How do you stop two guests taking the last room?

One conditional UPDATE: held = held + 1 WHERE held \< total. Check the row count. Back it with a CHECK.

Is a distributed lock enough?

It saves work, but leases expire under pauses; keep the job idempotent anyway.

How do you test it?

Run the job from several threads at once on a real database, with a clock you move.

## Self-check rubric

| Area        | Meets the bar             | Above the bar                                                                      |
|-------------|---------------------------|------------------------------------------------------------------------------------|
| Correctness | All 13 tests pass.        | You ran the flawed version and explained each failure.                             |
| The job     | Expires due holds.        | Idempotent across servers, one transaction with the release, bounded batches.      |
| Inventory   | Sold-out is a 409.        | One conditional UPDATE and a CHECK; a retry on the last room still finds its hold. |
| Testing     | A test that runs the job. | Parallel runs, a barrier for the trap, a moved clock, and one real schedule.       |

# 3 · Go deeper: Review

## The pull request

A teammate makes `Holds` "easier to read": taking a room becomes a check and an update, and the job reads due holds and releases each one, made "safe" with `synchronized`. Read the file and list every problem before opening the findings.

#### `review/Holds.java`

``` code
package com.ghoomo.holds;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.ErrorResponseException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.time.Duration;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.temporal.ChronoUnit;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Optional;

@Service
class Holds {

    record Hold(long id, long roomTypeId, LocalDate date, String status, OffsetDateTime expiresAt) {
    }

    record Created(Hold hold, boolean replay) {
    }

    private final JdbcClient jdbc;
    private final Clock clock;
    private final Duration ttl;

    Holds(JdbcClient jdbc, Clock clock, @Value("${ghoomo.holds.ttl}") Duration ttl) {
        this.jdbc = jdbc;
        this.clock = clock;
        this.ttl = ttl;
    }

    private static final String HOLD = "SELECT id, room_type_id, stay_date AS date, status, expires_at FROM holds";

    /**
     * Takes a room and records the hold, in one transaction. The same Idempotency-Key with the same request returns
     * the first hold; with another request it is a 422.
     */
    @Transactional
    Created create(String key, long roomTypeId, LocalDate date, String guestEmail) {
        String email = guestEmail.strip().toLowerCase(Locale.ROOT);
        String hash = sha256(roomTypeId + "|" + date + "|" + email);
        Optional<Created> replay = replay(key, hash);
        if (replay.isPresent()) {
            return replay.get();
        }
        // Clearer in two steps: is a room free? Then take it.
        record Night(int total, int held) {
        }
        Night night = jdbc.sql("SELECT total, held FROM room_nights WHERE room_type_id = ? AND stay_date = ?").params(roomTypeId, date)
                .query(Night.class).optional().orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "No such room type or night."));
        if (night.held() >= night.total()) {
            throw problem(HttpStatus.CONFLICT, "No room of this type is free that night.");
        }
        jdbc.sql("UPDATE room_nights SET held = held + 1 WHERE room_type_id = ? AND stay_date = ?").params(roomTypeId, date).update();
        OffsetDateTime now = now();
        long id = jdbc.sql("""
                        INSERT INTO holds (idempotency_key, request_hash, room_type_id, stay_date, guest_email, created_at, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id""")
                .params(key, hash, roomTypeId, date, email, now, now.plus(ttl)).query(Long.class).single();
        return new Created(find(id).orElseThrow(), false);
    }

    /** The first hold made with this key, if any. */
    Optional<Created> replay(String key, String hash) {
        record Stored(long id, String requestHash) {
        }
        return jdbc.sql("SELECT id, request_hash FROM holds WHERE idempotency_key = ?").param(key).query(Stored.class).optional().map(s -> {
            if (!s.requestHash().equals(hash)) {
                throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "This Idempotency-Key was already used for a different hold.");
            }
            return new Created(find(s.id()).orElseThrow(), true);
        });
    }

    Optional<Hold> find(long id) {
        return jdbc.sql(HOLD + " WHERE id = ?").param(id).query(Hold.class).optional();
    }

    /** Expires every hold that is due and gives its room back. synchronized, so it never runs twice at once. */
    @Transactional
    synchronized int expireDue() {
        record Due(long id, long roomTypeId, LocalDate stayDate) {
        }
        OffsetDateTime now = now();
        List<Due> due = jdbc.sql("SELECT id, room_type_id, stay_date FROM holds WHERE status = 'HELD' AND expires_at <= ?")
                .param(now).query(Due.class).list();
        for (Due d : due) {
            jdbc.sql("UPDATE room_nights SET held = held - 1 WHERE room_type_id = ? AND stay_date = ?").params(d.roomTypeId(), d.stayDate()).update();
            jdbc.sql("UPDATE holds SET status = 'EXPIRED', expired_at = ? WHERE id = ?").params(now, d.id()).update();
        }
        return due.size();
    }

    static ErrorResponseException problem(HttpStatus status, String detail) {
        return new ErrorResponseException(status, ProblemDetail.forStatusAndDetail(status, detail), null);
    }

    static String sha256(String text) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    private OffsetDateTime now() {
        return OffsetDateTime.now(clock).withOffsetSameInstant(ZoneOffset.UTC).truncatedTo(ChronoUnit.MICROS);
    }
}
```

## Findings

1Check, then take

"Clearer in two steps": twenty guests read "4 held of 5" at the same moment and all add one. The database's CHECK stops the count passing 5, so the extra guests get an error instead of a clean 409; without that CHECK the hotel would be overbooked. Taking must be the condition: `held = held + 1 WHERE held < total`.

**Test evidence:** `twentyGuestsAtOnceForFiveRoomsGetExactlyFive` fails: some of the twenty requests end in an error instead of a `409`. Printing the cause while building showed the database's `room_nights_held_range` refusing them: the constraint kept the hotel from being overbooked.

2synchronized is one server's lock

"So it never runs twice at once": on this server. The second server has its own lock, and the job reads, then gives back: the trap's shape, with a lock that does not reach the other server.

**Test evidence:** None on one JVM, and that is the lesson: the four-runs-at-once test passes on the flawed version, because `synchronized` does line up threads in one process. `theOldJobOnTwoServersGivesOneRoomBackTwiceAndTheHotelIsOverbooked` runs this read-then-give-back shape as two servers would, and overbooks. A test that runs everything in one JVM cannot show a one-server lock failing; review has to.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class             | Fixed version | Flawed version |
|------------------------|---------------|----------------|
| `DoubleExpiryTrapTest` | 2 / 2         | 2 / 2          |
| `HoldContractTest`     | 3 / 3         | 3 / 3          |
| `HoldDatabaseTest`     | 3 / 3         | 3 / 3          |
| `HoldReplayTest`       | 2 / 2         | 2 / 2          |
| `ScheduledExpiryTest`  | 1 / 1         | 1 / 1          |
| `HoldConcurrencyTest`  | 2 / 2         | 1 / 2          |

Only one test fails, and that is worth a moment: the worse flaw, the job, passes every test in this suite. One guest at a time, on one server, the flawed version is correct. Christmas Eve brings both: many guests at once, and more than one server.
