# Station 044 · Hotel room availability calendar

Foundations · 0–1 years · Core · Travel · Types: Database, Concurrency

Spring Boot 4.1.1 · Java 25 · Spring Data JPA date query methods · half-open ranges · PostgreSQL 17 EXCLUDE with daterange · virtual threads · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Hotels, rooms and guests are demo data, not Ghoomo's. A block is a hold record; no payment is taken and no confirmation is sent.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 18 tests.

# 1 · Understand

## The problem in real life

1.  **Asha books 10 to 12 June**

    Room 101, two nights: the 10th and the 11th.

2.  **Kabir books 11 to 13 June**

    The system checks whether another stay starts on the 11th. None does, so Kabir gets the room too. On the 11th, two families arrive with keys to the same room.

3.  **The fix**

    Two stays clash when each starts before the other ends. That rule is checked in Java for a clear message and enforced by the database for every race.

Ranges clash when each starts before the other ends. Nothing simpler is right.

## What are we building?

`GET /rooms/{id}/availability` shows which nights a room is free; `POST /rooms/{id}/blocks` holds it for a stay, or says it is not available.

## An everyday analogy

A hotel's paper register with one column per night. Booking 10 to 12 June ticks the boxes for the 10th and 11th, not the 12th. A new booking is allowed only if none of its boxes is ticked.

## How it works in 4 steps

1.  **Check the dates**: check-out after check-in, at most 30 nights.
2.  **Look for a clash** with the overlap rule; if found, `409`.
3.  **Insert the hold.** If another desk got there in the same instant, the database refuses: also `409`.
4.  **The calendar** marks each night free unless a hold covers it.

Check yourself: Asha holds 10 to 12 June. Can Meena hold 12 to 15 June?

Yes. Asha's last night is the 11th; she leaves on the morning of the 12th. Meena's first night is the 12th. With a half-open range, 12 \< 12 is false, so they do not overlap.

## What this station is not

- **No payment or confirmation.** A hold is a record.
- **No room types or prices.** One room at a time.
- **No time zones.** Nights are local dates at the hotel.

## Key terms

| Term                   | Simple meaning                                                       | Everyday example                                                 | In this project                             |
|------------------------|----------------------------------------------------------------------|------------------------------------------------------------------|---------------------------------------------|
| **Night**              | A stay is counted in nights: the night that starts on a date.        | "10 to 12 June" is two nights: the 10th and the 11th.            | `RoomBlock.holds`                           |
| **Half-open range**    | Start included, end excluded: \[check-in, check-out).                | You leave on the morning of check-out; that night is free.       | `'[)'`                                      |
| **Overlap**            | Two stays share at least one night.                                  | Two guests given the same room on the 11th.                      | `checkIn < otherOut AND checkOut > otherIn` |
| **Back-to-back**       | One guest leaves the day the next arrives.                           | Out at 11 a.m., in at 2 p.m.                                     | allowed                                     |
| **EXCLUDE constraint** | No two rows may conflict, here: same room and overlapping dates.     | One key per room per night.                                      | `room_blocks_no_overlap`                    |
| **Deadlock**           | Two transactions each waiting for the other; the database stops one. | Two people in a doorway, each waiting for the other to go first. | found by the concurrency test               |

# 2 · Build: Spec

## Business problem

**Ghoomo** (a fictional hotel chain) sold a room booked for 10 to 12 June again for 11 to 13 June, because the overlap check compared only start dates.

## Acceptance criteria

Room 101 holds 10–12 June (Asha) and 15–16 June (Ravi).

1.  **Given** 11 to 13 June, **then** `409`: the night of the 11th is taken.
2.  **Given** 12 to 15 June, **then** `201` for 3 nights: back to back with both stays.
3.  **Given** the calendar for 9 to 17 June, **then** the 10th, 11th and 15th are taken, the others free.
4.  **Given** 20 desks holding the same nights at once, **then** one `201` and 19 `409`, never a `500`, and no night held twice.
5.  **Given** zero nights, check-out before check-in, or over 30 nights, `400`; an unknown room, `404`.

## Requirements

- Ranges are half-open everywhere: Java check, calendar, and database.
- The database guarantees no overlap (`EXCLUDE`), whoever writes and however fast.
- Every way the database refuses a clash becomes `409`.
- Dates are ISO local dates.

## Learning objectives

- Model stays as half-open ranges.
- Write the overlap condition, and test it on every shape.
- Express it as a Spring Data JPA query method with dates.
- Back a Java check with a database constraint for concurrency.

# 2 · Build: API contract

## Endpoints

| Method | Path                                   | Purpose                                                                          |
|--------|----------------------------------------|----------------------------------------------------------------------------------|
| `GET`  | `/rooms/{id}/availability?from=…&to=…` | Each night from `from` up to the night before `to`: free or not.                 |
| `POST` | `/rooms/{id}/blocks`                   | `{"checkIn", "checkOut", "guestName"}`: hold the nights checkIn to checkOut − 1. |

## Status codes

| Status | When                                                                               |
|--------|------------------------------------------------------------------------------------|
| 200    | A calendar                                                                         |
| 201    | The room is held                                                                   |
| 400    | Zero nights, end before start, too long a range, a missing field, an unknown field |
| 404    | No such room                                                                       |
| 409    | At least one night is already held                                                 |

## Captured examples

Captured with curl from the running app on 15 Oct 2026, in this order, against the demo data. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: room 101, 9 to 17 June

**Why:** the 10th, 11th and 15th are held.

Request

``` code
GET /rooms/101/availability?from=2026-06-09&to=2026-06-17 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 393

{
  "roomId": 101,
  "from": "2026-06-09",
  "to": "2026-06-17",
  "freeNights": 5,
  "nights": [
    {
      "date": "2026-06-09",
      "available": true
    },
    {
      "date": "2026-06-10",
      "available": false
    },
    {
      "date": "2026-06-11",
      "available": false
    },
    {
      "date": "2026-06-12",
      "available": true
    },
    {
      "date": "2026-06-13",
      "available": true
    },
    {
      "date": "2026-06-14",
      "available": true
    },
    {
      "date": "2026-06-15",
      "available": false
    },
    {
      "date": "2026-06-16",
      "available": true
    }
  ]
}
```

### Case 2: 11 to 13 June

**Why:** the original double booking, now `409`.

Request

``` code
POST /rooms/101/blocks HTTP/1.1
Content-Type: application/json

{
  "checkIn": "2026-06-11",
  "checkOut": "2026-06-13",
  "guestName": "Kabir Shah"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Room 101 is already held for a night between 2026-06-11 and 2026-06-13.",
  "instance": "/rooms/101/blocks",
  "status": 409,
  "title": "Not available"
}
```

### Case 3: 12 to 15 June

**Why:** arrives as Asha leaves, leaves as Ravi arrives: `201`.

Request

``` code
POST /rooms/101/blocks HTTP/1.1
Content-Type: application/json

{
  "checkIn": "2026-06-12",
  "checkOut": "2026-06-15",
  "guestName": "Meena Rao"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 103

{
  "id": 3,
  "roomId": 101,
  "checkIn": "2026-06-12",
  "checkOut": "2026-06-15",
  "nights": 3,
  "guestName": "Meena Rao"
}
```

### Case 4: the calendar again

**Why:** only the 9th and 16th left.

Request

``` code
GET /rooms/101/availability?from=2026-06-09&to=2026-06-17 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 396

{
  "roomId": 101,
  "from": "2026-06-09",
  "to": "2026-06-17",
  "freeNights": 2,
  "nights": [
    {
      "date": "2026-06-09",
      "available": true
    },
    {
      "date": "2026-06-10",
      "available": false
    },
    {
      "date": "2026-06-11",
      "available": false
    },
    {
      "date": "2026-06-12",
      "available": false
    },
    {
      "date": "2026-06-13",
      "available": false
    },
    {
      "date": "2026-06-14",
      "available": false
    },
    {
      "date": "2026-06-15",
      "available": false
    },
    {
      "date": "2026-06-16",
      "available": true
    }
  ]
}
```

### Case 5: in and out the same day

**Why:** no night to hold: `400`.

Request

``` code
POST /rooms/101/blocks HTTP/1.1
Content-Type: application/json

{
  "checkIn": "2026-07-02",
  "checkOut": "2026-07-02",
  "guestName": "Day Visitor"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "checkOut must be after the start: the last date is the morning you leave.",
  "instance": "/rooms/101/blocks",
  "status": 400,
  "title": "Invalid dates"
}
```

### Case 6: room 999

**Why:** `404`.

Request

``` code
GET /rooms/999/availability?from=2026-06-09&to=2026-06-17 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No room 999.",
  "instance": "/rooms/999/availability",
  "status": 404,
  "title": "Room not found"
}
```

## Twenty desks at once

From `docs/capture.sh`: 20 parallel curl requests for room 102, 1 to 4 August (`docs/captures/rush.txt`).

``` code
20 requests at once for room 102, 1 to 4 August: HTTP status counts
      1 201
     19 409
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                 | What happens                            | Proved by                                      |
|------------------------------------------------------|-----------------------------------------|------------------------------------------------|
| Eight shapes against 10–12 June                      | Overlap exactly when they share a night | `theOverlapRuleOnEveryShape`                   |
| A free gap; an overlap; another room                 | `201`; `409`; `201`                     | `aFreeStayIsHeldAndAnOverlappingOneIsNot`      |
| The calendar                                         | Each night marked                       | `theCalendarShowsEachNight`                    |
| 20 holds for the same nights at once                 | 1 held, 19 refused, no 500              | `twentyRequestsForTheSameNightsHoldItOnce`     |
| 30 staggered overlapping holds at once               | No night held twice, no 500             | `staggeredOverlappingRequestsNeverShareANight` |
| Overlap, zero nights, unknown room, written directly | Refused by named constraints            | `namedConstraintsHoldWithoutJava`              |
| A group booking with one clash                       | All or nothing                          | `aGroupBookingIsAllOrNothing`                  |
| Bad dates, missing or unknown fields; unknown room   | `400`; `404`                            | `AvailabilityContractTest`                     |

## The trap

Plausible but wrong

Comparing only start dates, so overlapping bookings are accepted.

The old checks are kept as Spring Data methods in the tests. The start-date check says 11 to 13 June is free. The first fix, with both ends included, refuses a back-to-back stay from the 12th. The real rule is then tested on eight shapes.

While building, each fix was undone once:

- Not mapping the constraint violation gave 2 errors: requests really do race past the Java check.
- Counting the check-out night in the calendar turned 1 test red.
- Dropping the `EXCLUDE` constraint turned 4 red.
- Swapping the arguments of the Java overlap check was *not* caught: the database turned every clash into the same `409`. The Java check gives a clear message without a failed insert; the constraint is the guarantee.

``` code
package com.ghoomo.rooms;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;

/** The first test written for this station. Room 101 is held 10-12 June. */
class StartDatesOnlyTrapTest extends ApiTest {

    static final LocalDate JUNE_11 = LocalDate.of(2026, 6, 11);
    static final LocalDate JUNE_12 = LocalDate.of(2026, 6, 12);
    static final LocalDate JUNE_13 = LocalDate.of(2026, 6, 13);
    static final LocalDate JUNE_14 = LocalDate.of(2026, 6, 14);

    @Autowired
    OldRoomBlockRepository old;

    @Test
    void comparingStartDatesSaysElevenToThirteenIsFree() {
        assertThat(old.existsByRoomIdAndCheckInEquals(101L, JUNE_11)).isFalse();                                  // sold again
        assertThat(blocks.existsByRoomIdAndCheckInBeforeAndCheckOutAfter(101L, JUNE_13, JUNE_11)).isTrue();  // the night of the 11th is taken
    }

    @Test
    void includingTheCheckOutDayRefusesABackToBackStay() {
        assertThat(old.existsByRoomIdAndCheckInLessThanEqualAndCheckOutGreaterThanEqual(101L, JUNE_14, JUNE_12)).isTrue();   // wrongly "taken"
        assertThat(blocks.existsByRoomIdAndCheckInBeforeAndCheckOutAfter(101L, JUNE_14, JUNE_12)).isFalse();                  // in on the 12th, as Asha leaves
    }

    @ParameterizedTest(name = "{0} to {1} against 10-12 June -> overlaps {2}")
    @CsvSource({
            "2026-06-11, 2026-06-13, true",    // starts inside
            "2026-06-08, 2026-06-11, true",    // ends inside
            "2026-06-10, 2026-06-12, true",    // the same stay
            "2026-06-10, 2026-06-11, true",    // within, same start
            "2026-06-08, 2026-06-14, true",    // covers it
            "2026-06-08, 2026-06-10, false",   // leaves the morning Asha arrives
            "2026-06-12, 2026-06-14, false",   // arrives the morning Asha leaves
            "2026-06-20, 2026-06-22, false"})  // nowhere near
    void theOverlapRuleOnEveryShape(LocalDate checkIn, LocalDate checkOut, boolean overlaps) {
        assertThat(blocks.existsByRoomIdAndCheckInBeforeAndCheckOutAfter(101L, checkOut, checkIn)).isEqualTo(overlaps);
    }
}
```

``` code
package com.ghoomo.rooms;

import org.springframework.data.repository.Repository;

import java.time.LocalDate;

/** The overlap checks the team tried before, kept only in tests (Spring Data writes their queries too). */
interface OldRoomBlockRepository extends Repository<RoomBlock, Long> {

    /** The original: a stay clashes only if it starts on the same day as another. */
    boolean existsByRoomIdAndCheckInEquals(Long roomId, LocalDate checkIn);   // "Equals": a name ending in "CheckIn" would read "In" as the IN keyword

    /** The first fix: ranges compared with both ends included, as if the check-out night were part of the stay. */
    boolean existsByRoomIdAndCheckInLessThanEqualAndCheckOutGreaterThanEqual(Long roomId, LocalDate newCheckOut, LocalDate newCheckIn);
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
./mvnw test                 # all 18 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Ask PostgreSQL about ranges directly:

``` code
docker compose exec postgres psql -U ghoomo -d ghoomo -c "SELECT daterange('2026-06-10','2026-06-12','[)') && daterange('2026-06-12','2026-06-14','[)') AS back_to_back, daterange('2026-06-10','2026-06-12','[)') && daterange('2026-06-11','2026-06-13','[)') AS eleven_to_thirteen"
```

Back to back is `f`; 11 to 13 is `t`.

## Troubleshooting

| You see                                                                        | Cause                                                                                | Fix                                                                                     |
|--------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| `No property 'check' found for type 'RoomBlock'; Did you mean 'checkIn'`       | A derived method name ending in `CheckIn`: Spring Data reads `In` as the IN keyword. | Spell the comparison: `…CheckInEquals`. Found while building this station.              |
| `conflicting key value violates exclusion constraint "room_blocks_no_overlap"` | An overlapping hold reached the database.                                            | Expected under races; the app answers `409`.                                            |
| `deadlock detected`                                                            | Two overlapping holds inserted at once, each waiting for the other.                  | PostgreSQL aborts one; the app answers `409`, because the other one holds those nights. |
| `data type bigint has no default operator class for access method "gist"`      | `btree_gist` is missing.                                                             | The migration creates it; a managed database may need it allowed.                       |

## Project layout

``` tree
stations/044-hotel-room-availability-calendar/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/ghoomo/rooms/
│   ├── RoomController.java   ├── Availability.java   ├── RoomBlockRepository.java
│   ├── RoomBlock.java   ├── Room.java   ├── RoomRepository.java   └── RoomsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__rooms_and_blocks.sql, V2__demo_rooms.sql
├── src/test/java/com/ghoomo/rooms/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/ghoomo/rooms/RoomController.java`

Does  
Checks date ranges, returns the calendar or the hold.

Why  
Zero-night and over-long ranges are refused before the database.

Without it  
A zero-night stay reaching the database's CHECK and coming back as a 500.

#### `src/main/java/com/ghoomo/rooms/Availability.java`

Does  
Builds the calendar and holds rooms.

Why  
A clear 409 from the Java check, and the same 409 when the database refuses a race.

Without it  
Races turning into 500s.

- The constraint violation and a deadlock abort are both answered `409`; see Design.
- `saveAndFlush` runs the insert now, inside the try, so a refusal is caught here.

#### `src/main/java/com/ghoomo/rooms/RoomBlockRepository.java`

Does  
The overlap rule as a derived query method.

Why  
`CheckInBefore(newCheckOut)` and `CheckOutAfter(newCheckIn)` are the two halves of the rule.

Without it  
Hand-written JPQL, or the start-date check.

#### `src/main/java/com/ghoomo/rooms/RoomBlock.java`

Does  
A hold as an entity, with `holds(night)` for the calendar.

Why  
The same half-open rule in one line.

Without it  
A calendar that marks the check-out night taken.

#### `src/main/java/com/ghoomo/rooms/Room.java`

A room.

#### `src/main/java/com/ghoomo/rooms/RoomRepository.java`

Rooms, for "does this room exist".

#### `src/main/resources/db/migration/V1__rooms_and_blocks.sql`

Does  
Rooms and holds, with the `EXCLUDE` constraint.

Why  
`daterange(check_in, check_out, '[)')` uses the same half-open rule as Java.

Without it  
Two holds for one night when two desks press "book" together.

#### `src/main/resources/db/migration/V2__demo_rooms.sql`

Two rooms and two holds.

#### `src/main/resources/application.yaml`

open-in-view off, schema validation, strict JSON.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/ghoomo/rooms/RoomsApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                             | Test class                         | Result |
|---------------|---------------------------------------------------------|------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                | `AvailabilityContractTest` (4)     | pass   |
| Every station | Reproduce the failure before the fix                    | `StartDatesOnlyTrapTest` (10 runs) | pass   |
| Database      | Rollback and constraint tests against a real database   | `BlockDatabaseTest` (2)            | pass   |
| Concurrency   | A real concurrency test that proves the invariant holds | `BlockConcurrencyTest` (2)         | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Hibernate 7, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.ghoomo.rooms.BlockConcurrencyTest
[INFO] Tests run: 10, Failures: 0, Errors: 0, Skipped: 0 -- in com.ghoomo.rooms.StartDatesOnlyTrapTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.ghoomo.rooms.AvailabilityContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.ghoomo.rooms.BlockDatabaseTest
[INFO] Tests run: 18, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/ghoomo/rooms/StartDatesOnlyTrapTest.java`

Written first: the old checks, and the rule on eight shapes.

#### `src/test/java/com/ghoomo/rooms/BlockConcurrencyTest.java`

20 identical and 30 staggered holds, released by one latch; a self-join proves no night is shared.

#### `src/test/java/com/ghoomo/rooms/BlockDatabaseTest.java`

Named constraints, back-to-back via SQL, and an all-or-nothing group.

#### `src/test/java/com/ghoomo/rooms/AvailabilityContractTest.java`

The calendar, holds, and refusals through HTTP.

#### `src/test/java/com/ghoomo/rooms/OldRoomBlockRepository.java`

The old checks as derived methods, kept only in tests.

#### `src/test/java/com/ghoomo/rooms/ApiTest.java`

Shared setup: the demo holds before each test, and the latch helper.

#### `src/test/java/com/ghoomo/rooms/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/ghoomo/rooms/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=CancelBlockChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 18 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 21 tests pass (18 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Cancel a hold

Add `DELETE /rooms/{id}/blocks/{blockId}`: `204`, and the nights are free again. A block of another room, or none, is `404`.

**Done when:** both tests in `CancelBlockChallengeTest` pass.

Hints

- `findById`, then check the room before deleting.
- A block id from another room must never delete that room's hold.

#### `challenge/CancelBlockChallengeTest.java`

``` code
package com.ghoomo.rooms;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: DELETE /rooms/{id}/blocks/{blockId} releases a hold: 204, and its nights are free again. A block that
 * does not exist, or belongs to another room, is 404.
 */
class CancelBlockChallengeTest extends ApiTest {

    @Test
    void cancellingFreesTheNights() throws Exception {
        mvc.perform(delete("/rooms/101/blocks/1")).andExpect(status().isNoContent());   // Asha's 10-12 June
        mvc.perform(get("/rooms/101/availability").param("from", "2026-06-10").param("to", "2026-06-12"))
                .andExpect(jsonPath("$.nights[*].available", contains(true, true)));
    }

    @Test
    void aBlockOfAnotherRoomOrNoneIs404() throws Exception {
        mvc.perform(delete("/rooms/102/blocks/1")).andExpect(status().isNotFound());
        mvc.perform(delete("/rooms/101/blocks/999")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Find a free room

Add `GET /rooms/free?checkIn&checkOut&guests`: rooms with enough beds and no night held in the range, by id, in one query.

**Done when:** the test in `FreeRoomsChallengeTest` passes.

Hints

- JPQL: `where r.capacity >= :guests and not exists (select b from RoomBlock b where …)`.
- Inside, the same overlap rule: `b.checkIn < :checkOut and b.checkOut > :checkIn`.

#### `challenge/FreeRoomsChallengeTest.java`

``` code
package com.ghoomo.rooms;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.empty;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 2: GET /rooms/free?checkIn&checkOut&guests: every room with enough capacity and no night held in the
 * range, by id. One query: rooms where NOT EXISTS an overlapping block, with the same half-open rule.
 */
class FreeRoomsChallengeTest extends ApiTest {

    @Test
    void roomsFreeForTheWholeStayWithEnoughBeds() throws Exception {
        mvc.perform(get("/rooms/free").param("checkIn", "2026-06-11").param("checkOut", "2026-06-13").param("guests", "2"))
                .andExpect(jsonPath("$[*].id", contains(102)));
        mvc.perform(get("/rooms/free").param("checkIn", "2026-06-12").param("checkOut", "2026-06-14").param("guests", "2"))
                .andExpect(jsonPath("$[*].id", contains(101, 102)));
        mvc.perform(get("/rooms/free").param("checkIn", "2026-06-12").param("checkOut", "2026-06-14").param("guests", "5"))
                .andExpect(jsonPath("$", empty()));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Room types instead of rooms

Guests book "a deluxe room", not room 101; the hotel assigns rooms at check-in. The rule becomes "never more deluxe stays on a night than deluxe rooms". Compare a per-night counter row per room type (with a conditional update, as in the flash sale), assigning a concrete room at booking time, and a nightly inventory table. Which one can a database constraint guard?

# 3 · Go deeper: Design

## Implementation approach

1.  Decide the range rule (half-open) and write the overlap condition.
2.  Write the trap test with the old checks and every overlap shape.
3.  Put the same rule in the database as an `EXCLUDE` constraint.
4.  Write the Java check for clear messages, and map every database refusal to `409`; prove it with parallel holds.

## Why two kinds of refusal

When two overlapping holds arrive together, both pass the Java check. Both inserts then meet the exclusion constraint. Usually one waits for the other and gets the constraint violation. Sometimes each insert waits for the other, and PostgreSQL ends the cycle by aborting one as a deadlock. That happened once while building this station, and came back as a `500`. In both cases the surviving hold commits those nights, so the refused request truly clashed, and the app answers `409`. The deadlock cannot be produced on demand, so no test claims to cover it.

## Design alternatives and trade-offs

| Approach                                                  | What it costs                                                       | Verdict           |
|-----------------------------------------------------------|---------------------------------------------------------------------|-------------------|
| Java check + `EXCLUDE` constraint                         | Two places with the same rule; refusals to map.                     | Chosen            |
| Java check only                                           | Races double-book.                                                  | Not enough        |
| Compare start dates                                       | Misses most overlaps.                                               | The trap          |
| One row per room per night with a unique key              | Simple constraint; many rows; long stays are many inserts.          | Also correct      |
| Lock the room row (`SELECT … FOR UPDATE`) before checking | Serialises holds per room; no deadlock between overlapping inserts. | Valid alternative |

## Database design

| Table         | Constraints                                                                                                       | Why                                                          |
|---------------|-------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------|
| `rooms`       | PK, capacity 1 to 10                                                                                              | What can be held.                                            |
| `room_blocks` | `room_blocks_room_fk`, `room_blocks_dates_order` (at least one night), `room_blocks_no_overlap` (EXCLUDE, `'[)'`) | The no-double-booking rule, for every writer and every race. |

``` code
CREATE TABLE rooms (
    id       BIGINT       PRIMARY KEY,
    hotel    VARCHAR(80)  NOT NULL,
    name     VARCHAR(80)  NOT NULL,
    capacity SMALLINT     NOT NULL,
    CONSTRAINT rooms_capacity_range CHECK (capacity BETWEEN 1 AND 10)
);

-- A block holds a room for the nights from check_in up to, but not including, check_out: the half-open range
-- [check_in, check_out). 10 to 12 June is the nights of the 10th and 11th; the next guest may check in on the 12th.
CREATE TABLE room_blocks (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    room_id    BIGINT      NOT NULL,
    check_in   DATE        NOT NULL,
    check_out  DATE        NOT NULL,
    guest_name VARCHAR(80) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT room_blocks_room_fk     FOREIGN KEY (room_id) REFERENCES rooms (id),
    CONSTRAINT room_blocks_dates_order CHECK (check_out > check_in)
);

-- The guarantee, for every writer and every race: no two blocks of one room share a night. '[)' is half-open, the
-- same rule as the Java check, so back-to-back stays (out on the 12th, in on the 12th) are allowed.
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE room_blocks ADD CONSTRAINT room_blocks_no_overlap
    EXCLUDE USING gist (room_id WITH =, daterange(check_in, check_out, '[)') WITH &&);
```

# 3 · Go deeper: Production

Channel managers  
Hotels sell through several sites at once; all of them must go through one inventory that a constraint guards.

Deadlocks  
Occasional deadlocks under contention are normal for exclusion constraints. Count them; a rising rate means many desks fight over the same rooms.

Time  
Check-in dates are the hotel's local dates, not UTC. A guest's phone in another time zone must not shift them.

Holds that expire  
Real holds while a guest pays expire after minutes; that needs a status or an expiry column in the constraint.

# 3 · Go deeper: Interview

## Interview takeaways

When do two date ranges overlap?

For half-open ranges \[a, b) and \[c, d): when a \< d and c \< b. Checking only starts, or using \<= with exclusive ends, gets edge cases wrong.

Why half-open ranges for stays?

The check-out day is not a night of the stay. Half-open ranges make back-to-back stays not overlap, and lengths are simply end − start.

Why is a Java overlap check not enough?

Two requests can check at the same moment, both see no clash, and both insert. Only a constraint in the database decides between them.

What is an EXCLUDE constraint?

A PostgreSQL constraint that forbids two rows for which given operators all return true, for example same room (=) and overlapping daterange (&&).

How do you write date conditions as JPA query methods?

With keywords on date fields: CheckInBefore(x) is check_in \< x, CheckOutAfter(y) is check_out \> y; Spring Data generates the query from the method name.

## Self-check rubric

| Area        | Meets the bar                       | Above the bar                                          |
|-------------|-------------------------------------|--------------------------------------------------------|
| Correctness | All 18 tests pass.                  | You ran the flawed version and explained each failure. |
| Ranges      | Half-open, everywhere.              | Every overlap shape from memory.                       |
| Concurrency | A constraint behind the Java check. | Why a deadlock abort is also a 409 here.               |
| JPA         | Date query methods.                 | Why a name ending in CheckIn breaks.                   |

# 3 · Go deeper: Review

## The pull request

A teammate simplifies the room code. The clash check becomes "a stay already starts that day". The try/catch around the insert goes. The calendar is "inclusive on both ends", and same-day stays are allowed for day rooms. Read the three files and list every problem before opening the findings.

#### `review/Availability.java`

``` code
package com.ghoomo.rooms;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.ErrorResponseException;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Service
class Availability {

    record Night(LocalDate date, boolean available) {
    }

    record Calendar(long roomId, LocalDate from, LocalDate to, int freeNights, List<Night> nights) {
    }

    record BlockView(long id, long roomId, LocalDate checkIn, LocalDate checkOut, long nights, String guestName) {
        static BlockView of(RoomBlock b) {
            return new BlockView(b.getId(), b.getRoomId(), b.getCheckIn(), b.getCheckOut(),
                    b.getCheckIn().datesUntil(b.getCheckOut()).count(), b.getGuestName());
        }
    }

    private final RoomRepository rooms;
    private final RoomBlockRepository blocks;

    Availability(RoomRepository rooms, RoomBlockRepository blocks) {
        this.rooms = rooms;
        this.blocks = blocks;
    }

    /** The nights from `from` up to, not including, `to`: the same half-open rule as a stay. */
    @Transactional(readOnly = true)
    Calendar calendar(long roomId, LocalDate from, LocalDate to) {
        requireRoom(roomId);
        List<RoomBlock> overlapping = blocks.findByRoomIdAndCheckInBeforeAndCheckOutAfterOrderByCheckIn(roomId, to, from);
        List<Night> nights = new ArrayList<>();
        for (LocalDate night = from; night.isBefore(to); night = night.plusDays(1)) {
            LocalDate n = night;
            nights.add(new Night(n, overlapping.stream().noneMatch(b -> b.holds(n))));
        }
        return new Calendar(roomId, from, to, (int) nights.stream().filter(Night::available).count(), nights);
    }

    /** PR: "Simpler clash check: a room is taken if a stay already starts that day. Saves a query shape." */
    @Transactional
    BlockView block(long roomId, LocalDate checkIn, LocalDate checkOut, String guestName) {
        requireRoom(roomId);
        boolean clash = blocks.findAll().stream().anyMatch(b -> b.getRoomId() == roomId && b.getCheckIn().equals(checkIn));
        if (clash) {
            throw taken(roomId, checkIn, checkOut);
        }
        return BlockView.of(blocks.saveAndFlush(new RoomBlock(roomId, checkIn, checkOut, guestName)));
    }

    private void requireRoom(long roomId) {
        if (!rooms.existsById(roomId)) {
            throw problem(HttpStatus.NOT_FOUND, "Room not found", "No room " + roomId + ".");
        }
    }

    private static ErrorResponseException taken(long roomId, LocalDate checkIn, LocalDate checkOut) {
        return problem(HttpStatus.CONFLICT, "Not available", "Room " + roomId + " is already held for a night between " + checkIn + " and " + checkOut + ".");
    }

    static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
```

#### `review/RoomBlock.java`

``` code
package com.ghoomo.rooms;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.LocalDate;

/** A room held for the nights checkIn up to, not including, checkOut. */
@Entity
@Table(name = "room_blocks")
public class RoomBlock {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private Long roomId;
    private LocalDate checkIn;
    private LocalDate checkOut;
    private String guestName;

    protected RoomBlock() {   // for JPA
    }

    RoomBlock(Long roomId, LocalDate checkIn, LocalDate checkOut, String guestName) {
        this.roomId = roomId;
        this.checkIn = checkIn;
        this.checkOut = checkOut;
        this.guestName = guestName;
    }

    public Long getId() {
        return id;
    }

    public Long getRoomId() {
        return roomId;
    }

    public LocalDate getCheckIn() {
        return checkIn;
    }

    public LocalDate getCheckOut() {
        return checkOut;
    }

    public String getGuestName() {
        return guestName;
    }

    /** PR: "Inclusive on both ends, like the dates on the booking." */
    boolean holds(LocalDate night) {
        return !night.isBefore(checkIn) && !night.isAfter(checkOut);
    }
}
```

#### `review/RoomController.java`

``` code
package com.ghoomo.rooms;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;

@RestController
class RoomController {

    /** Demo limits: a calendar shows up to 62 nights, a stay is up to 30 nights. */
    static final int MAX_CALENDAR_NIGHTS = 62;
    static final int MAX_STAY_NIGHTS = 30;

    record NewBlock(@NotNull LocalDate checkIn, @NotNull LocalDate checkOut, @NotBlank @Size(max = 80) String guestName) {
    }

    private final Availability availability;

    RoomController(Availability availability) {
        this.availability = availability;
    }

    @GetMapping("/rooms/{id}/availability")
    Availability.Calendar availability(@PathVariable long id,
                                       @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
                                       @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to) {
        requireRange(from, to, MAX_CALENDAR_NIGHTS, "to");
        return availability.calendar(id, from, to);
    }

    /** Holds a room for a stay (a demo hold record; no payment, no confirmation sent). */
    @PostMapping("/rooms/{id}/blocks")
    @ResponseStatus(HttpStatus.CREATED)
    Availability.BlockView block(@PathVariable long id, @Valid @RequestBody NewBlock request) {
        requireRange(request.checkIn(), request.checkOut(), MAX_STAY_NIGHTS, "checkOut");
        return availability.block(id, request.checkIn(), request.checkOut(), request.guestName().strip());
    }

    private static void requireRange(LocalDate start, LocalDate end, int maxNights, String endName) {
        if (end.isBefore(start)) {   // PR: "allow same-day stays for day rooms"
            throw Availability.problem(HttpStatus.BAD_REQUEST, "Invalid dates", endName + " must be after the start: the last date is the morning you leave.");
        }
        if (ChronoUnit.DAYS.between(start, end) > maxNights) {
            throw Availability.problem(HttpStatus.BAD_REQUEST, "Invalid dates", "At most " + maxNights + " nights.");
        }
    }
}
```

## Findings

1The clash check compares start dates only

The original bug again, as a stream over every block. On its own it would be masked: the database refuses the overlap anyway.

**Test evidence:** With finding 2, an ordinary overlapping hold becomes a `500`: `aFreeStayIsHeldAndAnOverlappingOneIsNot` errors.

2The database's refusal is not mapped

Without the catch, every clash the database stops, including every race, is a `500`.

**Test evidence:** `twentyRequestsForTheSameNightsHoldItOnce` and `staggeredOverlappingRequestsNeverShareANight` error.

3The calendar includes the check-out night

"Inclusive on both ends, like the dates on the booking" marks the morning-of-departure night as taken: the 12th looks booked when it is free.

**Test evidence:** `theCalendarShowsEachNight` fails.

4Same-day stays allowed

"Day rooms" are a different product. A stay with no night reaches the database's `room_blocks_dates_order` and comes back as a `500`.

**Test evidence:** `impossibleDatesAre400` errors.

## Same tests, flawed version

From `docs/review-run.txt`: the three flawed files copied over the real ones, then the full suite run.

| Test class                 | Fixed version | Flawed version |
|----------------------------|---------------|----------------|
| `BlockDatabaseTest`        | 2 / 2         | 2 / 2          |
| `StartDatesOnlyTrapTest`   | 10 / 10       | 10 / 10        |
| `AvailabilityContractTest` | 4 / 4         | 1 / 4          |
| `BlockConcurrencyTest`     | 2 / 2         | 0 / 2          |

No double booking got through: the constraint refused every one. What the flaws broke is how the app answers, which is why the database rule and the Java rule both matter.
