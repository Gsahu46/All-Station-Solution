# Station 037 · Bus ticket booking in one transaction

Foundations · 0–1 years · Core · Travel · Types: Database

Spring Boot 4.1.1 · Java 25 · plain JDBC transactions: auto-commit, commit, rollback · generated keys · batch insert · PostgreSQL 17 · Flyway · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Trips and fares are demo data, not Safarbus's. A booking is a record in this app's database; no payment is taken and no ticket is issued.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 15 tests.

# 1 · Understand

## The problem in real life

1.  **A family books two seats**

    The app saves the booking, then each passenger. Each insert is saved the moment it runs.

2.  **Something fails in between**

    The server restarts after the booking row, or seat 12 was taken a second earlier. The booking stays, charged for two seats, with one passenger or none. Support finds bookings no conductor can match to anyone.

3.  **The fix**

    Booking and passengers in one transaction: all rows are committed together, or a rollback removes them all.

Rows that only make sense together are saved together.

## What are we building?

`POST /bookings` books up to six seats on a trip, one passenger per seat, and returns the booking id and total. If any seat is taken, nothing is booked.

## An everyday analogy

A railway reservation form for a family: the clerk enters every name, and only then presses "confirm". If one berth is gone, the whole form comes back. Nobody gets a ticket for half a family.

## How it works in 4 steps

1.  **Check the request**: the trip exists, seats are on the bus and different.
2.  **Begin**: switch auto-commit off.
3.  **Insert** the booking (the database returns its id), then all passengers in one batch.
4.  **Commit**, or on any failure **roll back**: no half-booking either way.

Check yourself: why can't a CHECK constraint stop a booking with no passengers?

A CHECK looks at one row at a time. "This booking has at least one passenger" is about rows in another table, which are inserted after the booking. Only a transaction makes them appear together.

## What this station is not

- **No payment.** A confirmed booking is a record.
- **No seat hold.** A seat is free or booked; holding it while someone pays is challenge 3.
- **No Spring `@Transactional`.** Plain JDBC, so every step is visible; Spring does the same for you later.

## Key terms

| Term              | Simple meaning                                                                    | Everyday example                                        | In this project             |
|-------------------|-----------------------------------------------------------------------------------|---------------------------------------------------------|-----------------------------|
| **Transaction**   | A group of changes that become visible together, or not at all.                   | A cheque: either the whole amount moves, or none of it. | `BookingStore.save`         |
| **Auto-commit**   | JDBC's default: every statement is its own transaction, saved the moment it runs. | Posting each page of a letter separately.               | the trap                    |
| **Commit**        | Make the transaction's changes permanent and visible.                             | Signing the form.                                       | `c.commit()`                |
| **Rollback**      | Throw away every change since the transaction began.                              | Tearing up the unsigned form.                           | `c.rollback()`              |
| **Generated key** | An id the database creates on insert and hands back.                              | The token number the counter gives you.                 | `new String[]{"id"}`        |
| **Batch**         | Many rows for one statement sent together.                                        | Handing over a stack of forms at once.                  | `addBatch` / `executeBatch` |

# 2 · Build: Spec

## Business problem

**Safarbus** (a fictional bus operator) found bookings with no passengers: a crash between saving the booking and its passengers left half-saved bookings.

## Acceptance criteria

1.  **Given** two passengers for seats 12 and 13 on trip 101, **then** `201`, a new booking id, total ₹2,500.00, and two passenger rows.
2.  **Given** seats 11 and 12 when 12 is already booked, **then** `409` naming seat 12, and no new rows at all; seat 11 can be booked straight after.
3.  **Given** a failure after the booking row (a crash, a refused passenger, a Java error), **then** no booking row remains.
4.  **Given** seat 41 on a 40-seat bus, or the same seat twice, **then** `422`; an unknown trip, `404`.
5.  **Given** a bad phone, an age over 120, seat 0, no passengers, seven passengers, or an extra field, **then** `400`.

## Requirements

- The booking and its passengers are written in one transaction.
- One seat on one trip belongs to one booking: a database constraint decides, so two people racing for it cannot both win.
- A passenger's trip is always its booking's trip (a composite foreign key).
- Money in integer paise; the total is fare × passengers.

## Learning objectives

- Turn auto-commit off, commit, and roll back with plain JDBC.
- Read a generated key after an insert.
- Insert many rows with a JDBC batch.
- Turn a constraint violation into a clear `409`.

# 2 · Build: API contract

## Endpoint

| Method | Path        | Body                                                                                        |
|--------|-------------|---------------------------------------------------------------------------------------------|
| `POST` | `/bookings` | `{"tripId", "contactPhone", "passengers": [{"name", "age", "seatNo"}]}`, 1 to 6 passengers. |

## Status codes

| Status | When                                                                                 |
|--------|--------------------------------------------------------------------------------------|
| 201    | Booked: every passenger saved                                                        |
| 400    | A bad phone, name, age or seat number; 0 or more than 6 passengers; an unknown field |
| 404    | No such trip                                                                         |
| 409    | A seat is already booked; nothing was saved                                          |
| 422    | A seat the bus does not have, or the same seat twice                                 |

## Captured examples

Captured with curl from the running app on 15 Oct 2026, in this order, against one fresh database. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: seats 12 and 13

**Why:** one transaction: booking, then both passengers, then commit.

Request

``` code
POST /bookings HTTP/1.1
Content-Type: application/json

{
  "tripId": 101,
  "contactPhone": "9876543210",
  "passengers": [
    {
      "name": "Asha Verma",
      "age": 34,
      "seatNo": 12
    },
    {
      "name": "Kabir Verma",
      "age": 8,
      "seatNo": 13
    }
  ]
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 85

{
  "bookingId": 1,
  "tripId": 101,
  "seats": [
    12,
    13
  ],
  "totalPaise": 250000,
  "status": "CONFIRMED"
}
```

### Case 2: seats 11 and 12

**Why:** seat 12 is taken; the whole transaction is rolled back.

Request

``` code
POST /bookings HTTP/1.1
Content-Type: application/json

{
  "tripId": 101,
  "contactPhone": "9123456780",
  "passengers": [
    {
      "name": "Ravi Iyer",
      "age": 41,
      "seatNo": 11
    },
    {
      "name": "Meena Iyer",
      "age": 39,
      "seatNo": 12
    }
  ]
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Seat 12 is already booked on trip 101. Nothing was booked.",
  "instance": "/bookings",
  "status": 409,
  "title": "Seat already booked"
}
```

### Case 3: seat 11 alone

**Why:** the failed attempt left nothing behind, so seat 11 is free.

Request

``` code
POST /bookings HTTP/1.1
Content-Type: application/json

{
  "tripId": 101,
  "contactPhone": "9123456780",
  "passengers": [
    {
      "name": "Ravi Iyer",
      "age": 41,
      "seatNo": 11
    }
  ]
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 82

{
  "bookingId": 3,
  "tripId": 101,
  "seats": [
    11
  ],
  "totalPaise": 125000,
  "status": "CONFIRMED"
}
```

### Case 4: seat 41

**Why:** the bus has 40 seats: `422`.

Request

``` code
POST /bookings HTTP/1.1
Content-Type: application/json

{
  "tripId": 101,
  "contactPhone": "9123456780",
  "passengers": [
    {
      "name": "Ravi Iyer",
      "age": 41,
      "seatNo": 41
    }
  ]
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "Trip 101 has seats 1 to 40.",
  "instance": "/bookings",
  "status": 422,
  "title": "No such seat"
}
```

### Case 5: trip 999

**Why:** `404`.

Request

``` code
POST /bookings HTTP/1.1
Content-Type: application/json

{
  "tripId": 999,
  "contactPhone": "9123456780",
  "passengers": [
    {
      "name": "Ravi Iyer",
      "age": 41,
      "seatNo": 1
    }
  ]
}
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No trip 999.",
  "instance": "/bookings",
  "status": 404,
  "title": "Trip not found"
}
```

### Case 6: phone 12345

**Why:** `400`, before the database is touched.

Request

``` code
POST /bookings HTTP/1.1
Content-Type: application/json

{
  "tripId": 101,
  "contactPhone": "12345",
  "passengers": [
    {
      "name": "Ravi Iyer",
      "age": 41,
      "seatNo": 1
    }
  ]
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/bookings",
  "status": 400,
  "title": "Bad Request"
}
```

## The database after these six requests

Queried with psql right after the captures (`docs/captures/db-after.txt`). Two bookings, each with all its passengers; nothing from the refused attempt. There is no booking 2: the refused attempt took that id before it was rolled back, and sequences never roll back, so ids can have gaps. Never use them to count bookings.

``` code
 booking | total_paise | passengers | seats  
---------+-------------+------------+--------
       1 |      250000 |          2 | 12, 13
       3 |      125000 |          1 | 11
(2 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                              | What happens                                    | Proved by                                                                    |
|-------------------------------------------------------------------|-------------------------------------------------|------------------------------------------------------------------------------|
| Two passengers                                                    | `201`, id 1, both rows                          | `aBookingSavesEveryPassengerAndReturnsTheNewId`                              |
| One of two seats taken                                            | `409`, nothing saved, the other seat stays free | `aTakenSeatIs409AndNothingIsSaved`                                           |
| The same seat on another trip                                     | Allowed                                         | `theSameSeatOnAnotherTripIsFine`                                             |
| A passenger the database refuses                                  | The booking row is rolled back                  | `aRefusedPassengerRollsBackTheWholeBooking`                                  |
| A Java error after the booking row                                | The booking row is rolled back                  | `aJavaErrorMidwayRollsBackToo`                                               |
| The process dies before commit                                    | Nothing is committed                            | `aDeadConnectionCommitsNothing`                                              |
| Phone, age, a passenger on another trip; a seat twice on one trip | Refused by named constraints                    | `namedConstraintsHoldWithoutJava`, `oneSeatOnOneTripBelongsToOneBookingOnly` |
| Seat 41; the same seat twice                                      | `422`                                           | `seatsThatCannotBeBookedAre422`                                              |
| Bad fields, 0 or 7 passengers, an extra field                     | `400`                                           | `badBodiesAre400`                                                            |

## The trap

Plausible but wrong

Auto-commit on: a crash leaves a booking without its passengers.

The old code runs against the real PostgreSQL. A crash between the two inserts leaves a booking with no passengers. A taken seat halfway leaves a booking charged for two seats with one passenger. The real store, given the same failure, leaves nothing. While building, each fix was undone once. Leaving auto-commit on turned 8 tests red. Removing the rollback turned only 1 red, and only after a test was added for a Java error midway. PostgreSQL will not commit a transaction in which a statement failed, but `setAutoCommit(true)` in the `finally` block commits a transaction that had no database error. Not restoring auto-commit was not caught, because HikariCP resets it when the connection returns to the pool. The line stays, so the code does not depend on the pool.

``` code
package com.safarbus.bookings;

import org.junit.jupiter.api.Test;

import java.sql.SQLException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The first test written for this station: the old code's half-saved bookings, on the real database. */
class AutoCommitTrapTest extends ApiTest {

    @Test
    void aCrashAfterTheBookingRowLeavesABookingWithNoPassengers() throws Exception {
        assertThatThrownBy(() -> OldBookingStore.save(dataSource, trip101(), "9876543210", seats(4, 5),
                () -> { throw new IllegalStateException("crash between the two inserts"); }))
                .hasMessage("crash between the two inserts");
        assertThat(bookingsWithoutPassengers()).isEqualTo(1);
    }

    @Test
    void aTakenSeatHalfwayLeavesHalfABooking() throws Exception {
        store.save(trip101(), "9876543210", seats(5));
        assertThatThrownBy(() -> OldBookingStore.save(dataSource, trip101(), "9123456780", seats(4, 5), () -> { }))
                .isInstanceOf(SQLException.class);
        // The second booking exists, charged for two seats, with seat 4 only.
        assertThat(bookings()).isEqualTo(2);
        assertThat(jdbc.sql("SELECT count(*) FROM booking_passengers WHERE booking_id = 2").query(Long.class).single()).isEqualTo(1);
    }

    @Test
    void inOneTransactionTheSameFailureLeavesNothing() throws Exception {
        store.save(trip101(), "9876543210", seats(5));
        assertThatThrownBy(() -> store.save(trip101(), "9123456780", seats(4, 5))).isInstanceOf(SQLException.class);
        assertThat(bookings()).isEqualTo(1);
        assertThat(passengers()).isEqualTo(1);
        assertThat(bookingsWithoutPassengers()).isZero();
    }
}
```

``` code
package com.safarbus.bookings;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;

/** The booking code before the fix, kept only in tests: auto-commit on, so every statement commits by itself. */
final class OldBookingStore {

    private OldBookingStore() {
    }

    /** afterBooking runs between the two inserts: the moment a crash or a timeout would hit. */
    static long save(DataSource dataSource, Trip trip, String phone, List<Passenger> passengers, Runnable afterBooking) throws SQLException {
        try (Connection c = dataSource.getConnection()) {
            long bookingId;
            try (PreparedStatement s = c.prepareStatement("INSERT INTO bookings (trip_id, contact_phone, total_paise) VALUES (?, ?, ?)", new String[]{"id"})) {
                s.setLong(1, trip.id());
                s.setString(2, phone);
                s.setLong(3, trip.farePaise() * passengers.size());
                s.executeUpdate();   // committed now
                try (ResultSet keys = s.getGeneratedKeys()) {
                    keys.next();
                    bookingId = keys.getLong(1);
                }
            }
            afterBooking.run();
            for (Passenger p : passengers) {
                try (PreparedStatement s = c.prepareStatement(
                        "INSERT INTO booking_passengers (booking_id, trip_id, seat_no, name, age, fare_paise) VALUES (?, ?, ?, ?, ?, ?)")) {
                    s.setLong(1, bookingId);
                    s.setLong(2, trip.id());
                    s.setInt(3, p.seatNo());
                    s.setString(4, p.name());
                    s.setInt(5, p.age());
                    s.setLong(6, trip.farePaise());
                    s.executeUpdate();   // each passenger committed on its own
                }
            }
            return bookingId;
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

Watch a transaction from outside. In one terminal, open psql and start a transaction by hand:

``` code
docker compose exec postgres psql -U safarbus -d safarbus
BEGIN;
INSERT INTO bookings (trip_id, contact_phone, total_paise) VALUES (101, '9876543210', 125000);
```

In a second terminal, count bookings with `docker compose exec postgres psql -U safarbus -d safarbus -c "SELECT count(*) FROM bookings"`: the new row is not visible. Type `ROLLBACK;` in the first, and it never will be.

## Troubleshooting

| You see                                                                           | Cause                                                                 | Fix                                                                        |
|-----------------------------------------------------------------------------------|-----------------------------------------------------------------------|----------------------------------------------------------------------------|
| `current transaction is aborted, commands ignored until end of transaction block` | A statement failed inside a transaction; PostgreSQL refuses the rest. | Roll back, then start again.                                               |
| `Batch entry 1 … was aborted`                                                     | One row of a batch failed; the message names the constraint.          | Read the constraint name; call `getNextException()` for every failing row. |
| `Could not find a valid Docker environment`                                       | Docker is not running.                                                | Start Docker, then run the tests again.                                    |
| `Connection to localhost:5432 refused`                                            | PostgreSQL is not up yet.                                             | `docker compose up -d`, wait, start the app again.                         |

## Project layout

``` tree
stations/037-bus-ticket-booking-in-one-transaction/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/safarbus/bookings/
│   ├── BookingController.java   ├── BookingStore.java   ├── Trips.java
│   ├── Passenger.java   ├── Trip.java   └── BookingsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__trips_bookings_passengers.sql, V2__demo_trips.sql
├── src/test/java/com/safarbus/bookings/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/safarbus/bookings/BookingController.java`

Does  
Checks the request, saves the booking, and turns a taken seat into a `409`.

Why  
Request checks that need the trip (seat range, duplicates) happen before the transaction.

Without it  
Checking "is the seat free?" in Java first: two requests can both see it free. The constraint decides.

#### `src/main/java/com/safarbus/bookings/BookingStore.java`

Does  
Saves a booking and its passengers as one transaction.

Why  
Auto-commit off, two inserts, commit; rollback on any failure; auto-commit restored.

Without it  
The trap: every insert committed on its own.

- `prepareStatement(sql, new String[]{"id"})` asks the driver to return the new id.
- The passengers go as one batch: one statement, six rows, one round trip.
- Calling `setAutoCommit(true)` during a transaction commits it, which is why the rollback must come first.

#### `src/main/java/com/safarbus/bookings/Trips.java`

Reads a trip with plain JDBC.

#### `src/main/java/com/safarbus/bookings/Passenger.java`

One passenger, with validation for the request.

#### `src/main/java/com/safarbus/bookings/Trip.java`

A trip: seats and fare.

#### `src/main/resources/db/migration/V1__trips_bookings_passengers.sql`

Does  
The three tables and their named constraints.

Why  
The seat rule and the trip consistency are enforced for every writer.

Without it  
Two bookings for one seat, or a passenger on a different bus from their booking.

#### `src/main/resources/db/migration/V2__demo_trips.sql`

Two demo trips.

#### `src/main/resources/application.yaml`

The database, problem details, and unknown JSON fields refused.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/safarbus/bookings/BookingsApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                | Result |
|---------------|-------------------------------------------------------|---------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `BookingContractTest` (6) | pass   |
| Every station | Reproduce the failure before the fix                  | `AutoCommitTrapTest` (3)  | pass   |
| Database      | Rollback and constraint tests against a real database | `BookingDatabaseTest` (6) | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.safarbus.bookings.BookingDatabaseTest
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.safarbus.bookings.BookingContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.safarbus.bookings.AutoCommitTrapTest
[INFO] Tests run: 15, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/safarbus/bookings/AutoCommitTrapTest.java`

Written first: the old code's half-saved bookings, and the real store's clean failure.

#### `src/test/java/com/safarbus/bookings/BookingContractTest.java`

Bookings through HTTP, the taken seat, and every refusal, with row counts after each.

#### `src/test/java/com/safarbus/bookings/BookingDatabaseTest.java`

Constraints without Java, a dead connection, rollbacks, generated ids and the batch.

#### `src/test/java/com/safarbus/bookings/OldBookingStore.java`

The old code, kept only in tests, with a hook where a crash would hit.

#### `src/test/java/com/safarbus/bookings/ApiTest.java`

Shared setup: empty booking tables before each test, row counters.

#### `src/test/java/com/safarbus/bookings/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/safarbus/bookings/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=CancelBookingChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 15 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 19 tests pass (15 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Cancel a booking

Add `DELETE /bookings/{id}`: delete the passengers and the booking in one transaction, then the seats are free. `204`, or `404` for no such booking.

**Done when:** both tests in `CancelBookingChallengeTest` pass.

Hints

- Children first: passengers reference the booking.
- `executeUpdate()` returns how many rows it deleted: 0 means no such booking.

#### `challenge/CancelBookingChallengeTest.java`

``` code
package com.safarbus.bookings;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: DELETE /bookings/{id} cancels a booking: its passengers and the booking row go in one transaction
 * (children first, because of the foreign key), and the seats can be booked again. 204, or 404 if there is no such
 * booking.
 */
class CancelBookingChallengeTest extends ApiTest {

    @Test
    void cancellingFreesTheSeats() throws Exception {
        book(BookingContractTest.TWO).andExpect(status().isCreated());
        mvc.perform(delete("/bookings/1")).andExpect(status().isNoContent());
        assertThat(bookings()).isZero();
        assertThat(passengers()).isZero();
        book(BookingContractTest.TWO).andExpect(status().isCreated());
    }

    @Test
    void anUnknownBookingIs404() throws Exception {
        mvc.perform(delete("/bookings/999")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Senior fares

Passengers aged 60 or more pay 75% (demo rule), rounded to the nearest paisa, half up. Each passenger row stores its own fare, and the booking's total is exactly their sum.

**Done when:** both tests in `SeniorFareChallengeTest` pass.

Hints

- One method computes a passenger's fare; the total and each row both use it.
- In whole paise: `(fare × 75 + 50) / 100` rounds half up.

#### `challenge/SeniorFareChallengeTest.java`

``` code
package com.safarbus.bookings;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: passengers aged 60 or more pay 75% of the fare (demo rule), rounded to the nearest paisa, half up.
 * Each passenger row stores its own fare, and the booking's total is exactly the sum of them.
 */
class SeniorFareChallengeTest extends ApiTest {

    @Test
    void seniorsPayThreeQuartersAndTheTotalIsTheSumOfTheRows() throws Exception {
        book("""
                {"tripId":101,"contactPhone":"9876543210","passengers":[
                  {"name":"Asha Verma","age":34,"seatNo":12},{"name":"Kamala Verma","age":65,"seatNo":13}]}""")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.totalPaise").value(125_000 + 93_750));
        assertThat(jdbc.sql("SELECT fare_paise FROM booking_passengers ORDER BY seat_no").query(Long.class).list()).containsExactly(125_000L, 93_750L);
        assertThat(jdbc.sql("SELECT b.total_paise = (SELECT sum(fare_paise) FROM booking_passengers p WHERE p.booking_id = b.id) FROM bookings b")
                .query(Boolean.class).single()).isTrue();
    }

    @Test
    void halfAPaisaRoundsUp() throws Exception {
        jdbc.sql("UPDATE trips SET fare_paise = 85_001 WHERE id = 102").update();   // 75% is 63,750.75
        try {
            book("""
                    {"tripId":102,"contactPhone":"9876543210","passengers":[{"name":"Old","age":60,"seatNo":1}]}""")
                    .andExpect(jsonPath("$.totalPaise").value(63_751));
        } finally {
            jdbc.sql("UPDATE trips SET fare_paise = 85000 WHERE id = 102").update();
        }
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Holding a seat while the customer pays

Payment takes up to 5 minutes and happens at a payment gateway, outside this database. You cannot keep a transaction open that long. Design a seat hold: what is stored, when it expires, what happens when payment succeeds after the hold expired, and how the unique constraint changes.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap tests: a crash and a taken seat on the old code.
2.  Write the schema: a unique seat per trip, a composite foreign key.
3.  Write the store: auto-commit off, insert with a generated key, batch, commit, rollback.
4.  Test every failure path: a database error, a Java error, a dead connection.

## Design alternatives and trade-offs

| Approach                                   | What it costs                                                                          | Verdict                |
|--------------------------------------------|----------------------------------------------------------------------------------------|------------------------|
| One JDBC transaction around both inserts   | A few lines of commit/rollback code.                                                   | Chosen                 |
| Auto-commit and a cleanup job for orphans  | Customers see half-bookings until the job runs; the job can delete a booking mid-save. | The trap, plus a patch |
| Spring `@Transactional`                    | The same transaction, without the boilerplate.                                         | From later stations    |
| Check seats with a SELECT first            | Two requests both see the seat free.                                                   | A race                 |
| Passengers as a JSON column on the booking | One row, atomic by itself; no seat constraint per trip.                                | Loses the seat rule    |

## Database design

| Table                | Key and constraints                                                                                                                                           | Why                                                                                                     |
|----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| `trips`              | PK `id`. Seats 1 to 60, fare \> 0.                                                                                                                            | What can be booked.                                                                                     |
| `bookings`           | Identity PK. FK to trips. `bookings_phone_digits`, total \> 0, `UNIQUE (id, trip_id)`.                                                                        | The unique pair lets passengers reference booking and trip together.                                    |
| `booking_passengers` | PK `(booking_id, seat_no)`. `booking_passengers_booking_fk (booking_id, trip_id)`. `booking_passengers_seat_once (trip_id, seat_no)`. Seat, age, fare checks. | One seat on one trip, once, decided by the database; a passenger's trip always matches their booking's. |

**Transaction boundary:** `BookingStore.save`, at PostgreSQL's default `READ COMMITTED`. The seat check needs no stronger isolation: the unique constraint is checked against every committed and in-progress row, so a second booking for the same seat waits for the first and then fails.

``` code
CREATE TABLE trips (
    id          BIGINT       PRIMARY KEY,
    route       VARCHAR(100) NOT NULL,
    departs_at  TIMESTAMPTZ  NOT NULL,
    seats       SMALLINT     NOT NULL,
    fare_paise  BIGINT       NOT NULL,
    CONSTRAINT trips_seats_range   CHECK (seats BETWEEN 1 AND 60),
    CONSTRAINT trips_fare_positive CHECK (fare_paise > 0)
);

CREATE TABLE bookings (
    id            BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id       BIGINT      NOT NULL,
    contact_phone CHAR(10)    NOT NULL,
    total_paise   BIGINT      NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT bookings_trip_fk        FOREIGN KEY (trip_id) REFERENCES trips (id),
    CONSTRAINT bookings_phone_digits   CHECK (contact_phone ~ '^[6-9][0-9]{9}$'),
    CONSTRAINT bookings_total_positive CHECK (total_paise > 0),
    -- Lets passengers reference (booking, trip) together, so a passenger's trip is always its booking's trip.
    CONSTRAINT bookings_id_trip_unique UNIQUE (id, trip_id)
);

-- A booking with no passengers cannot be stopped by a CHECK on one row: the transaction is what prevents it.
CREATE TABLE booking_passengers (
    booking_id BIGINT       NOT NULL,
    trip_id    BIGINT       NOT NULL,
    seat_no    SMALLINT     NOT NULL,
    name       VARCHAR(60)  NOT NULL,
    age        SMALLINT     NOT NULL,
    fare_paise BIGINT       NOT NULL,
    PRIMARY KEY (booking_id, seat_no),
    CONSTRAINT booking_passengers_booking_fk FOREIGN KEY (booking_id, trip_id) REFERENCES bookings (id, trip_id),
    CONSTRAINT booking_passengers_seat_once  UNIQUE (trip_id, seat_no),
    CONSTRAINT booking_passengers_seat_range CHECK (seat_no BETWEEN 1 AND 60),
    CONSTRAINT booking_passengers_age_range  CHECK (age BETWEEN 0 AND 120),
    CONSTRAINT booking_passengers_fare_positive CHECK (fare_paise > 0)
);
```

# 3 · Go deeper: Production

Short transactions  
Keep only database work inside a transaction. A slow call (payment, SMS) inside it holds locks and a pooled connection.

Batches  
PostgreSQL's driver can rewrite a batch into one multi-row insert (`reWriteBatchedInserts=true`); measure before turning it on.

Finding orphans  
A query for bookings without passengers is a cheap health check; after this fix it should always return zero.

Retries  
A client that times out may retry a booking that did commit. Idempotency keys (station 085) make that safe.

# 3 · Go deeper: Interview

## Interview takeaways

What is auto-commit in JDBC?

The default mode: each statement runs in its own transaction and commits immediately. For several statements that belong together, switch it off, commit at the end, and roll back on failure.

What happens if you call setAutoCommit(true) in the middle of a transaction?

The JDBC specification says the transaction is committed. That is why the rollback must happen before auto-commit is restored.

How do you get a generated id after an insert?

prepareStatement(sql, new String\[\]{"id"}) or Statement.RETURN_GENERATED_KEYS, then getGeneratedKeys() after executeUpdate(). In PostgreSQL, INSERT ... RETURNING id does the same in SQL.

Why a batch insert?

One statement, many parameter sets, sent together: fewer round trips. Inside a transaction, a failing row fails the batch and the rollback undoes it all.

Who should decide that a seat is free, Java or the database?

The database, with a unique constraint. A Java check followed by an insert has a gap where another request can take the seat.

## Self-check rubric

| Area         | Meets the bar                           | Above the bar                                             |
|--------------|-----------------------------------------|-----------------------------------------------------------|
| Correctness  | All 15 tests pass.                      | You watched an uncommitted row from a second session.     |
| Transactions | Commit at the end, rollback on failure. | Why the rollback comes before `setAutoCommit(true)`.      |
| JDBC         | Generated keys and a batch.             | Reading every error of a failed batch.                    |
| Database     | A unique seat per trip.                 | The composite foreign key and why it needs a unique pair. |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any multi-row write:

- Which rows only make sense together? Are they in one transaction?
- Is there a rollback on every failure path, including Java exceptions?
- Is anything slow (a network call) inside the transaction?
- Is "is it free?" decided by a constraint, or by a check before the insert?
