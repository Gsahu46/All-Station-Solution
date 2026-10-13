# Station 005 · Designing REST resources for gym classes

Foundations · 0–1 years · Core · Fitness · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · Bean Validation · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Four classes and three members are fixed in the code; bookings live in memory and are lost on restart. No login: the member id is sent in the body.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 14 tests.

# 1 · Understand

## The problem in real life

1.  **Rohan books a 6:30 yoga class**

    The FitNest app calls `/bookClass`. The answer is `200`, with `{"success": false}`.

2.  **The app shows "Something went wrong"**

    Was the class full? Had he already booked it? Did the class exist? The answer was the same in all three cases, so the app could only guess.

3.  **The fix**

    Name things, not actions: `POST /classes/1/bookings`. Answer each outcome with its own status: `201` booked, `409` full or already yours, `404` no such class.

A status code is the first thing a client reads. When every answer is `200`, every client has to dig through the body and guess.

## What are we building?

A small class-booking API designed around resources: list classes by date, book a class, cancel a booking, list a member's bookings. Every outcome has the status code that means it.

## An everyday analogy

A library does not have a counter called "doBorrowBook". It has books (things), and you borrow, return or renew them (actions). When something fails, the librarian says why: "someone has it" is different from "we don't have that book". URLs are the things; HTTP methods are the actions; status codes are the librarian's reasons.

## How it works in 4 steps

1.  **See the timetable**: `GET /classes?date=2026-10-19`. The date filters the collection, so it is a query parameter.
2.  **Book**: `POST /classes/1/bookings` with your member id. A booking belongs to a class, so it is created under the class.
3.  **The answer says what happened**: `201` with the new booking's address, or `409` (full, already booked), or `404` (no such class).
4.  **Cancel**: `DELETE /bookings/{id}`. The booking has its own address now; the answer is `204`.

Check yourself: the class is full. Why 409 and not 404 or 400?

404 would mean the class does not exist, but it does. 400 would mean the request is malformed, but it is fine; the same request would have worked an hour ago. 409 says the request conflicts with the current state: the class is full right now.

## What this station is not

- **No login.** The member id is sent in the body, so anyone could book for anyone. Real APIs take the member from the signed-in user (security stations).
- **No database.** Bookings live in memory.
- **No waitlist and no cancellation deadline.** The deadline is a design task in Practice.

## Key terms

| Term                | Simple meaning                                                | Everyday example                                         | In this project                                    |
|---------------------|---------------------------------------------------------------|----------------------------------------------------------|----------------------------------------------------|
| **Resource**        | A thing the API lets you work with, named by a noun.          | A book in a library.                                     | A class, a booking, a member's bookings.           |
| **URL path**        | The address of one resource or one collection.                | Shelf 4, row 2.                                          | `/bookings/{id}`                                   |
| **HTTP method**     | The action: read (`GET`), create (`POST`), remove (`DELETE`). | Borrow, return, renew: the same book, different actions. | `DELETE /bookings/{id}` cancels.                   |
| **Nested resource** | A collection that only makes sense inside its parent.         | The chapters of one book.                                | `/classes/{id}/bookings`, `/members/{id}/bookings` |
| **Query parameter** | A filter or option on a collection, after `?`.                | "Only books by this author."                             | `/classes?date=2026-10-19`                         |
| **204 No Content**  | "Done. Nothing to send back."                                 | A nod instead of a letter.                               | A cancelled booking.                               |
| **409 Conflict**    | "Your request clashes with how things are right now."         | Trying to borrow a book someone else has.                | The class is full, or you already booked it.       |

# 2 · Build: Spec

## Business problem

**FitNest** (a fictional chain of gyms) has a class-booking API with URLs like `/bookClass`, `/cancelBooking` and `/getMemberBookings`, and it answers `200` to everything, with `{"success": false, "message": …}` on failure. The app team cannot show members why a booking failed, monitoring cannot count errors (every request "succeeded"), and each new feature adds another verb URL.

## Acceptance criteria

1.  **Given** a date, **when** the app asks for classes, **then** `200` with that day's classes in start-time order, each with spots left.
2.  **Given** a class with space, **when** a member books, **then** `201` with `Location: /bookings/{id}`, and that URL returns the booking.
3.  **Given** a full class, **then** `409` *Class is full*. **Given** the member already booked it, **then** `409` *Already booked*, naming the existing booking.
4.  **Given** an unknown class, **then** `404`. **Given** an unknown or missing member id, **then** `400`.
5.  **Given** a booking, **when** it is cancelled, **then** `204` with no body, the spot is free again, and the booking's URL returns `404`.
6.  **Given** a member, **then** `GET /members/{id}/bookings` lists their bookings; an unknown member is `404`.

## Requirements

- URLs are nouns. Methods are the verbs. No `/bookClass`, no `/cancelBooking`.
- Path parameters identify a resource; query parameters filter a collection.
- Status codes by meaning: `200` read, `201` created, `204` done with no body, `400` bad request, `404` no such resource, `409` conflicts with current state.
- Dates are ISO (`2026-10-19`); times are the gym's local time.
- Errors are RFC 9457 problems.

## Learning objectives

- Name resources with nouns and choose between nested and top-level URLs.
- Choose a path or a query parameter.
- Pick 200, 201, 204, 400, 404 or 409 by what happened.
- Return `Location` on create and `204` on delete.
- Keep "what happened" (the outcome) separate from "which status code" (the HTTP answer).

# 2 · Build: API contract

## Endpoints

| Method   | Path                           | Purpose                                 | Success            |
|----------|--------------------------------|-----------------------------------------|--------------------|
| `GET`    | `/classes?date={yyyy-mm-dd}`   | That day's classes, with spots left     | `200`              |
| `POST`   | `/classes/{classId}/bookings`  | Book a class. Body: `{"memberId": 101}` | `201` + `Location` |
| `GET`    | `/bookings/{id}`               | Read one booking                        | `200`              |
| `DELETE` | `/bookings/{id}`               | Cancel a booking                        | `204`              |
| `GET`    | `/members/{memberId}/bookings` | A member's bookings                     | `200`              |

## Why these URLs

| Choice                                                | Reason                                                                                       |
|-------------------------------------------------------|----------------------------------------------------------------------------------------------|
| Bookings are *created* under `/classes/{id}/bookings` | You cannot book without a class; the class is part of the address, not repeated in the body. |
| Bookings are *read and cancelled* at `/bookings/{id}` | Once it exists, a booking has its own id. The app should not need the class id to cancel it. |
| `/members/{id}/bookings`                              | "My bookings" is the member's collection, so it is nested under the member.                  |
| `date` is a query parameter                           | It filters the collection of classes; it does not name one thing.                            |

## Status codes

| Status | Meaning here                                                                   |
|--------|--------------------------------------------------------------------------------|
| 200    | Here is what you asked to read.                                                |
| 201    | Booking created; `Location` says where.                                        |
| 204    | Booking cancelled; nothing to return.                                          |
| 400    | The request is wrong: missing or malformed date, missing or unknown member id. |
| 404    | No such class, booking or member.                                              |
| 405    | That method is not allowed on that URL.                                        |
| 409    | Class is full, or this member already booked it.                               |

## Captured examples

Captured with curl from the running app on 13 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: Monday's timetable

**Why:** a filtered read of a collection: `200`, ordered by start time, each class with its spots left.

Request

``` code
GET /classes?date=2026-10-19 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 353

[
  {
    "id": 1,
    "name": "Morning Yoga",
    "trainer": "Kavya",
    "date": "2026-10-19",
    "startTime": "06:30:00",
    "capacity": 2,
    "spotsLeft": 2
  },
  {
    "id": 2,
    "name": "HIIT Blast",
    "trainer": "Arjun",
    "date": "2026-10-19",
    "startTime": "07:30:00",
    "capacity": 20,
    "spotsLeft": 20
  },
  {
    "id": 3,
    "name": "Zumba",
    "trainer": "Kavya",
    "date": "2026-10-19",
    "startTime": "18:00:00",
    "capacity": 15,
    "spotsLeft": 15
  }
]
```

### Case 2: Rohan (member 101) books Morning Yoga

**Why:** a new booking, so `201`; `Location` is the booking's own address.

Request

``` code
POST /classes/1/bookings HTTP/1.1
Content-Type: application/json

{
  "memberId": 101
}
```

Response

``` code
HTTP/1.1 201 
Location: /bookings/77c720f8-40ca-41ef-af02-39aa3f4444b2
Content-Type: application/json

{
  "id": "77c720f8-40ca-41ef-af02-39aa3f4444b2",
  "classId": 1,
  "memberId": 101,
  "bookedAt": "2026-10-13T13:41:50.187Z"
}
```

### Case 3: a third member tries the same class

**Why:** Morning Yoga has 2 spots and both are taken. The request is fine, the class is not: `409`.

Request

``` code
POST /classes/1/bookings HTTP/1.1
Content-Type: application/json

{
  "memberId": 103
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Every spot in this class is taken.",
  "instance": "/classes/1/bookings",
  "status": 409,
  "title": "Class is full"
}
```

### Case 4: Rohan taps Book again

**Why:** also `409`, with a different title, and the detail names his existing booking so the app can show it.

Request

``` code
POST /classes/1/bookings HTTP/1.1
Content-Type: application/json

{
  "memberId": 101
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "This member already has booking 77c720f8-40ca-41ef-af02-39aa3f4444b2 for this class.",
  "instance": "/classes/1/bookings",
  "status": 409,
  "title": "Already booked"
}
```

### Case 5: an old timetable

**Why:** class 999 does not exist: `404`. The app should refresh its timetable.

Request

``` code
POST /classes/999/bookings HTTP/1.1
Content-Type: application/json

{
  "memberId": 101
}
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No class has the id 999.",
  "instance": "/classes/999/bookings",
  "status": 404,
  "title": "Class not found"
}
```

### Case 6: Rohan's bookings

**Why:** the member's own collection, nested under the member.

Request

``` code
GET /members/101/bookings HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 112

[
  {
    "id": "77c720f8-40ca-41ef-af02-39aa3f4444b2",
    "classId": 1,
    "memberId": 101,
    "bookedAt": "2026-10-13T13:41:50.187Z"
  }
]
```

### Case 7: Rohan cancels

**Why:** `204`: the booking is gone and there is nothing to return.

Request

``` code
DELETE /bookings/77c720f8-40ca-41ef-af02-39aa3f4444b2 HTTP/1.1
```

Response

``` code
HTTP/1.1 204
```

### Case 8: cancel the same booking again

**Why:** the booking no longer exists, so `404`. Whether a repeat delete should be `404` or `204` is station 008's topic.

Request

``` code
DELETE /bookings/77c720f8-40ca-41ef-af02-39aa3f4444b2 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No booking has the id 77c720f8-40ca-41ef-af02-39aa3f4444b2.",
  "instance": "/bookings/77c720f8-40ca-41ef-af02-39aa3f4444b2",
  "status": 404,
  "title": "Booking not found"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                      | What the API does                         | Proved by                                                 |
|-------------------------------------------|-------------------------------------------|-----------------------------------------------------------|
| Timetable for a date                      | `200`, by start time, spots left          | `classesForADateAreListedByStartTimeWithSpotsLeft`        |
| A date with no classes                    | `200`, empty list                         | `aDateWithNoClassesIsAnEmptyList`                         |
| Missing date, or `19-10-2026`             | `400`                                     | `theDateIsRequiredAndMustBeIso`                           |
| Booking                                   | `201` + readable `Location`               | `bookingIs201WithALocationThatCanBeRead`                  |
| Full class                                | `409` *Class is full*                     | `aFullClassIs409`                                         |
| Booking the same class twice              | `409` *Already booked*, names the booking | `bookingTheSameClassTwiceIs409AndNamesTheExistingBooking` |
| Unknown class                             | `404`                                     | `anUnknownClassIs404`                                     |
| Unknown or missing member                 | `400`                                     | `anUnknownOrMissingMemberIs400`                           |
| Cancel                                    | `204`, empty body, spot freed             | `cancellingIs204WithNoBodyAndFreesTheSpot`                |
| Read or cancel a cancelled booking        | `404`                                     | `aCancelledBookingIsGone`                                 |
| A member's bookings; none; unknown member | `200` list; `200 []`; `404`               | `aMembersBookingsAreANestedCollection`                    |
| Old verb URLs; `PUT` on a booking         | `404`; `405`                              | `theOldVerbUrlsAndWrongMethodsAreNotPartOfTheApi`         |

## The trap

Plausible but wrong

Verbs in URLs and `200` for every outcome, so clients cannot tell what happened.

It feels natural to name endpoints after actions, and `{"success": false}` looks informative. The first test shows the cost: a full class, a double booking and a class that does not exist all come back as the same `200` with the same message. The second test sends the same three requests to the resource API and gets `409`, `409` (with a different title) and `404`. Removing the capacity check was tried while building: 3 tests went red.

``` code
package com.fitnest.classes;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: it reproduces the problem before the fix.
 * Three different things go wrong; the old API answers all three the same way.
 */
@Import(VerbsAndAlways200TrapTest.OldBookingController.class)
class VerbsAndAlways200TrapTest extends ApiTest {

    /** The "before" API: verbs in the URL, everything in query parameters, and 200 whatever happens. */
    @RestController
    static class OldBookingController {
        private final ClassSchedule schedule;

        OldBookingController(ClassSchedule schedule) {
            this.schedule = schedule;
        }

        @PostMapping("/bookClass")
        Map<String, Object> bookClass(@RequestParam long classId, @RequestParam long memberId) {
            return switch (schedule.book(classId, memberId)) {
                case BookingOutcome.Booked b -> Map.of("success", true, "message", "Booked");
                default -> Map.of("success", false, "message", "Could not book");
            };
        }
    }

    @Test
    void theOldApiAnswers200ForAFullClassAnUnknownClassAndADoubleBooking() throws Exception {
        mvc.perform(post("/bookClass").param("classId", "1").param("memberId", "101")).andExpect(status().isOk());
        mvc.perform(post("/bookClass").param("classId", "1").param("memberId", "102")).andExpect(status().isOk());

        // Three different problems, one answer. The app cannot tell "full" (try another class)
        // from "already yours" (nothing to do) from "no such class" (refresh the timetable).
        for (String[] attempt : new String[][]{{"1", "103"}, {"1", "101"}, {"999", "101"}}) {
            mvc.perform(post("/bookClass").param("classId", attempt[0]).param("memberId", attempt[1]))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.success").value(false))
                    .andExpect(jsonPath("$.message").value("Could not book"));
        }
    }

    @Test
    void theResourceApiGivesEachOutcomeItsOwnStatus() throws Exception {
        book(1, 101).andExpect(status().isCreated());
        book(1, 102).andExpect(status().isCreated());

        book(1, 103).andExpect(status().isConflict()).andExpect(jsonPath("$.title").value("Class is full"));
        book(1, 101).andExpect(status().isConflict()).andExpect(jsonPath("$.title").value("Already booked"));
        book(999, 101).andExpect(status().isNotFound()).andExpect(jsonPath("$.title").value("Class not found"));
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                         | Check with      |
|----------|-------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below  | `java -version` |
| Maven    | Not needed: the project ships the Maven wrapper |                 |
| Docker   | Not needed for this station                     |                 |

**macOS / Linux**

``` code
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 14 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

The booking body is in `docs/booking.json` (`{"memberId":101}`), so the commands work in every shell.

``` code
curl "http://localhost:8080/classes?date=2026-10-19"

# Book Morning Yoga twice: expect 201, then 409 "Already booked"
curl -i -X POST http://localhost:8080/classes/1/bookings -H "Content-Type: application/json" -d "@docs/booking.json"
curl -i -X POST http://localhost:8080/classes/1/bookings -H "Content-Type: application/json" -d "@docs/booking.json"

# Cancel: paste the Location from the first answer; expect 204
curl -i -X DELETE http://localhost:8080/bookings/PASTE-THE-ID
```

## Troubleshooting

| You see                              | Cause                        | Fix                                                      |
|--------------------------------------|------------------------------|----------------------------------------------------------|
| `400` for `/classes?date=19/10/2026` | Only ISO dates are accepted. | Use `2026-10-19`.                                        |
| `415 Unsupported Media Type`         | The JSON header is missing.  | Add `-H "Content-Type: application/json"`.               |
| `release version 25 not supported`   | Maven is using an older JDK. | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`. |

## Project layout

``` tree
stations/005-designing-rest-resources-for-gym-classes/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/fitnest/classes/
│   ├── ClassController.java   ├── BookingOutcome.java   ├── ClassSchedule.java
│   ├── GymClass.java          ├── Booking.java          ├── BookingRequest.java
│   ├── ApiErrors.java         └── ClassesApplication.java
├── src/test/java/com/fitnest/classes/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/fitnest/classes/ClassController.java`

Does  
Defines the five endpoints and turns each booking outcome into its status code.

Why  
All the HTTP decisions (URLs, methods, codes) are in one readable place.

Without it  
No API.

- The `switch` over `BookingOutcome` must handle every outcome: the compiler refuses to build if one is missing.
- `@DateTimeFormat(iso = DATE)` makes `2026-10-19` the only accepted date format.

#### `src/main/java/com/fitnest/classes/BookingOutcome.java`

Does  
Lists everything that can happen when booking: booked, class not found, class full, already booked.

Why  
The schedule reports *what happened*; only the controller knows HTTP. Each outcome can then get its own code.

Without it  
The schedule would return `true`/`false`, and the reason for a failure would be lost (the trap).

#### `src/main/java/com/fitnest/classes/ClassSchedule.java`

Does  
Holds classes, members and bookings; books, cancels and lists.

Why  
One place owns the rules: capacity and one booking per member per class.

Without it  
Rules scattered across endpoints.

- `synchronized`: "count, then add" cannot interleave with another request, so a class of 2 never gets 3.
- `clearBookings` exists for tests only, so each test starts empty.

#### `src/main/java/com/fitnest/classes/GymClass.java`

A class with its date, start time, capacity and spots left.

#### `src/main/java/com/fitnest/classes/Booking.java`

A booking: its own id, the class, the member and when it was made.

#### `src/main/java/com/fitnest/classes/BookingRequest.java`

The body of a booking: only the member id. The class is in the URL.

#### `src/main/java/com/fitnest/classes/ApiErrors.java`

Does  
Adds an `errors` map (field → message) to validation failures.

Why  
The app learns which field was wrong.

Without it  
A bare "Bad Request".

#### `src/main/java/com/fitnest/classes/ClassesApplication.java`

Standard Spring Boot entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                              | Test class                      | Result |
|---------------|------------------------------------------|---------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found | `BookingContractTest` (12)      | pass   |
| Every station | Reproduce the failure before the fix     | `VerbsAndAlways200TrapTest` (2) | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.fitnest.classes.VerbsAndAlways200TrapTest
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0 -- in com.fitnest.classes.BookingContractTest
[INFO] Tests run: 14, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/fitnest/classes/VerbsAndAlways200TrapTest.java`

Written first: three different failures, one `200` from the old API; three distinct answers from the new one.

#### `src/test/java/com/fitnest/classes/BookingContractTest.java`

Every endpoint and every status code, each for its own reason.

#### `src/test/java/com/fitnest/classes/ApiTest.java`

Shared setup: the whole app through MockMvc, and an empty booking list before each test.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/fitnest/classes/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=ClassRosterChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 14 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 21 tests pass (14 station tests and 7 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## The trainer's roster

Trainers want to see who booked their class. Add `GET /classes/{classId}/bookings`: the class's bookings in the order they were made; an empty list for nobody; `404` for an unknown class.

**Done when:** all three tests in `ClassRosterChallengeTest` pass.

Hints

- Same URL as booking, different method: `GET` reads the collection, `POST` adds to it.
- Return an `Optional` from the schedule so "no such class" and "no bookings" stay different.

#### `challenge/ClassRosterChallengeTest.java`

``` code
package com.fitnest.classes;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: the trainer's roster, GET /classes/{id}/bookings: who booked this class, in booking order. */
class ClassRosterChallengeTest extends ApiTest {

    @Test
    void theRosterListsTheClassBookingsInTheOrderTheyWereMade() throws Exception {
        book(3, 102);
        book(2, 101);
        book(3, 101);
        mvc.perform(get("/classes/3/bookings"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[*].memberId", contains(102, 101)));
    }

    @Test
    void aClassNobodyBookedHasAnEmptyRoster() throws Exception {
        mvc.perform(get("/classes/4/bookings")).andExpect(status().isOk()).andExpect(jsonPath("$", hasSize(0)));
    }

    @Test
    void anUnknownClassIs404() throws Exception {
        mvc.perform(get("/classes/999/bookings")).andExpect(status().isNotFound())
                .andExpect(jsonPath("$.title").value("Class not found"));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Change a class's capacity

Add `PATCH /classes/{classId}` with `{"capacity": 12}`: 1 to 50. Lowering capacity below the bookings already made is a `409`, and nothing changes.

**Done when:** all four tests in `CapacityChangeChallengeTest` pass.

Hints

- `PATCH` changes part of a resource; the body holds only what changes.
- The class map was built with `Map.of`, which cannot change. Copy it into a `HashMap`.
- Return an outcome from the schedule (updated, not found, below bookings) and let the controller pick the status, as booking does.

#### `challenge/CapacityChangeChallengeTest.java`

``` code
package com.fitnest.classes;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: a trainer changes a class's capacity with PATCH /classes/{id}. */
class CapacityChangeChallengeTest extends ApiTest {

    ResultActions setCapacity(long classId, String json) throws Exception {
        return mvc.perform(patch("/classes/{id}", classId).contentType(MediaType.APPLICATION_JSON).content(json));
    }

    @AfterEach
    void restoreZumba() throws Exception {
        schedule.clearBookings();
        setCapacity(3, "{\"capacity\":15}");
    }

    @Test
    void raisingOrLoweringCapacityIs200WithTheUpdatedClass() throws Exception {
        book(3, 101);
        setCapacity(3, "{\"capacity\":5}")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.capacity").value(5))
                .andExpect(jsonPath("$.spotsLeft").value(4));
    }

    @Test
    void capacityBelowTheCurrentBookingsIs409AndNothingChanges() throws Exception {
        book(3, 101);
        book(3, 102);
        setCapacity(3, "{\"capacity\":1}")
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.title").value("Capacity below bookings"));
        setCapacity(3, "{\"capacity\":15}").andExpect(jsonPath("$.spotsLeft").value(13));
    }

    @Test
    void capacityOutsideOneToFiftyIs400() throws Exception {
        setCapacity(3, "{\"capacity\":0}").andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.capacity").exists());
        setCapacity(3, "{\"capacity\":51}").andExpect(status().isBadRequest());
        setCapacity(3, "{}").andExpect(status().isBadRequest());
    }

    @Test
    void anUnknownClassIs404() throws Exception {
        setCapacity(999, "{\"capacity\":10}").andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## No cancelling in the last 2 hours

FitNest wants a rule: a booking cannot be cancelled less than 2 hours before the class. Which status code would you return, and what would the problem body say? The class time is in India Standard Time and the server runs in UTC; how do you compare them? How would you test "1 hour 59 minutes before" without waiting for the clock? (Hint: give the schedule a `java.time.Clock` and fix it in tests.)

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: three different failures, one answer.
2.  List the resources (classes, bookings, members' bookings) and give each a noun URL.
3.  Write `BookingOutcome`: every way booking can end.
4.  Map each outcome to the status code that means it.
5.  Return `Location` on create and `204` on cancel.

## Design alternatives and trade-offs

| Approach                                           | What it costs                                                                                                               | Verdict    |
|----------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|------------|
| Nouns in URLs, methods as verbs, status by meaning | Takes a little design up front.                                                                                             | Chosen     |
| Verb URLs, `200` + `success` flag                  | Clients parse every body; monitoring sees no errors; one URL per action.                                                    | Wrong      |
| `DELETE /classes/{classId}/bookings/{id}`          | Also valid, but every caller must know the class id to cancel.                                                              | Possible   |
| `POST /bookings` with `classId` in the body        | Also valid and common. Nesting makes "a booking needs a class" visible in the URL.                                          | Possible   |
| `422` for a full class                             | 422 is for a request that cannot be processed as written. A full class is about the current state, which is what 409 means. | Debatable  |
| `404` for an unknown member in the body            | 404 is about the URL. The URL exists; the body is wrong, so 400 (some APIs choose 422).                                     | Misleading |

## Database design

None in this station. With a database, "one booking per member per class" becomes a unique constraint on `(class_id, member_id)`, and capacity is checked inside a transaction.

# 3 · Go deeper: Production

Security  
Anyone can book or cancel for any member id: there is no login. Real systems take the member from the signed-in user and check that a booking belongs to the caller before cancelling it.

Reliability  
Correct status codes let monitoring count real failures: a spike in `409` means classes are filling up, a spike in `404` means an app is showing an old timetable.

Concurrency  
One lock around the schedule keeps capacity correct for one server. With several servers, the database must enforce it.

Maintainability  
A new feature is a new resource or method, not a new verb URL.

# 3 · Go deeper: Interview

## Interview takeaways

Why are verbs in URLs a problem?

The HTTP method already is the verb. Verb URLs multiply (one per action), hide which resource is affected, and lose the built-in meaning of methods: caches, proxies and clients know GET is safe and DELETE removes, but nothing knows what /cancelBooking does.

Nested or top-level: /classes/{id}/bookings or /bookings?

Nest when the child only makes sense inside its parent and you create or list it there. Give it a top-level address once it has its own id, so callers do not need the parent's id to read or cancel it. This station does both.

Path parameter or query parameter?

A path parameter identifies a resource (/bookings/{id}). A query parameter filters, sorts or pages a collection (/classes?date=...).

409 or 400 for a full class?

400 means the request itself is wrong. A full class is a conflict with the current state: the same request would succeed with a free spot. That is 409.

What should DELETE return?

204 No Content when it succeeds and there is nothing useful to send. Here, a repeat DELETE is 404 because the booking is gone; station 008 discusses when 204 for both is the better contract.

## Self-check rubric

| Area        | Meets the bar                              | Above the bar                                                        |
|-------------|--------------------------------------------|----------------------------------------------------------------------|
| Correctness | All 14 tests pass.                         | You can say which test fails if the capacity check goes.             |
| Design      | Noun URLs; every outcome has its own code. | You can defend nested-then-top-level for bookings.                   |
| Tests       | A test for each status code.               | You wrote the trap test before designing the URLs.                   |
| Explanation | You can explain 409 against 400 and 404.   | You can explain why the outcome type keeps HTTP out of the schedule. |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any API design you are asked to review:

- Is there a verb in any URL?
- Does any failure come back as `200`?
- Does every create return `201` and a `Location` that can be read?
- Can two different failures be told apart by status code (or at least by problem title)?
