# Station 050 · Hotel booking request validation

Foundations · 0–1 years · Core · Travel · Types: none

Spring Boot 4.1.1 · Java 25 · Jakarta Bean Validation (Hibernate Validator) · custom ConstraintValidator · validation groups · RFC 9457 problem details. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Hotels, room types and guests are demo data, not Ghoomo's. A booking request is a record kept in memory: no room is held, nothing is paid, and it is gone when the app restarts. Stay limits (30 nights, 365 days ahead) are demo rules.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 12 tests.

# 1 · Understand

## The problem in real life

1.  **Careful field checks**

    Ghoomo's booking API checked every field: dates required and in the future, 1 to 10 adults, 0 to 10 children, a valid phone.

2.  **Impossible bookings got through**

    Support found requests with check-out before check-in, and 6 guests in a room for 2. Every field was valid on its own; nothing compared them.

3.  **The fix**

    Rules that look at the whole request, written as custom validators, run only once each field has passed, and answered with 422 instead of 400.

Valid parts do not make a valid whole. Some rules can only be checked by looking at two fields at once.

## What are we building?

`POST /hotel-bookings` takes a booking request and either records it (`201`), says a field is broken (`400`), or says the fields do not add up (`422`), naming each field with its message. `GET /hotel-bookings/{id}` reads a recorded request back.

## An everyday analogy

A hotel front desk. First the clerk checks the form is filled in properly: dates written as dates, a phone number with 10 digits. Only then do they check it makes sense: leaving after arriving, and a room big enough for everyone. A form with an empty box goes back for the box, not for a lecture on room sizes.

## How it works in 4 steps

1.  **Read** the JSON; unreadable bodies and wrong types are `400`.
2.  **Field rules** (the Default group) run on `@Valid`; any failure is `400`, with every broken field named.
3.  **Cross-field rules** (the `Consistency` group) run next; any failure is `422`, again naming fields.
4.  **Record** the request and answer `201` with its `Location`.

Check yourself: why not run all the rules at once?

A cross-field rule needs its fields. With check-in missing, "the stay is impossible" would be a confusing second error about the same mistake. Running the groups in order reports the missing date alone.

## What this station is not

- **No availability.** Whether the room is free is station 044.
- **No database.** Hotels and requests live in memory.
- **No payment.** A request record, not a confirmed booking.

## Key terms

| Term                          | Simple meaning                                                            | Everyday example                                              | In this project                     |
|-------------------------------|---------------------------------------------------------------------------|---------------------------------------------------------------|-------------------------------------|
| **Field validation**          | A rule about one value on its own.                                        | "The date must be a real date."                               | `@NotNull`, `@Min`, `@IndianMobile` |
| **Cross-field validation**    | A rule that compares two or more values.                                  | "Check-out comes after check-in."                             | `@ValidStay`, `@RoomFitsGuests`     |
| **ConstraintValidator**       | A class you write to check a rule Bean Validation does not have built in. | A custom stamp at the counter.                                | `ValidStay.Validator`               |
| **Validation group**          | A named set of rules you run at a chosen moment.                          | Checking the form is filled in, then checking it makes sense. | `Consistency`                       |
| **400 Bad Request**           | The request is broken: unreadable, or a field breaks its own rule.        | A form with the phone box empty.                              | Default group                       |
| **422 Unprocessable Content** | Every field is fine, but together they describe something impossible.     | A neat form asking to leave before arriving.                  | Consistency group                   |

# 2 · Build: Spec

## Business problem

**Ghoomo** (a fictional travel app) accepted booking requests that could never be honoured, because each field was checked alone. Staff had to call guests back to sort them out.

## Acceptance criteria

1.  **Given** 2 adults, a STANDARD room, 3 nights starting in 30 days, **then** `201`, 3 nights, the phone as 10 digits, and `GET` returns it.
2.  **Given** check-out before check-in, or on the same day, **then** `422` naming `checkOut`.
3.  **Given** 4 adults and 2 children in a STANDARD room (sleeps 2), **then** `422` naming `guests`.
4.  **Given** check-in yesterday, over 365 days ahead, a stay over 30 nights, an unknown hotel or room type, **then** `422` naming the field.
5.  **Given** 0 adults, a phone of 5 digits, no room type, a date as 30-11-2026, 2.5 adults, or broken JSON, **then** `400`.
6.  **Given** a missing check-in and 6 guests, **then** only the `400` for check-in.
7.  **Given** an unknown booking id, **then** `404`.

## Requirements

- A rule about one field is a field constraint; a rule about several is a class-level constraint.
- Field failures are `400`, cross-field failures `422`, both RFC 9457 problems with an `errors` map, field to message.
- "Today" is today in India (`Asia/Kolkata`).
- Room types are identifiers, normalised with `Locale.ROOT`.

## Learning objectives

- Write a custom `ConstraintValidator` for one field and for a whole object.
- Use validation groups to order checks and to separate `400` from `422`.
- Give a validator Spring beans (a `Clock`, a catalogue).
- Report every error on the field it concerns.

# 2 · Build: API contract

## Endpoints

| Method | Path                   | Purpose                                                                                                                                    |
|--------|------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| `POST` | `/hotel-bookings`      | Request a booking: `hotelId`, `roomType`, `checkIn`, `checkOut`, `adults` (1 to 10), `children` (0 to 10, optional), `guestName`, `phone`. |
| `GET`  | `/hotel-bookings/{id}` | Read a recorded request back (added so "not found" has something to miss).                                                                 |

## Status codes

| Status | When                                                                                                  |
|--------|-------------------------------------------------------------------------------------------------------|
| 201    | Recorded; `Location` points at it                                                                     |
| 200    | The request, read back                                                                                |
| 400    | Unreadable JSON, a wrong type, or a field that breaks its own rule                                    |
| 404    | No such booking request                                                                               |
| 422    | Every field is fine, but together they are impossible: dates, stay length, hotel, room type or guests |

## Captured examples

Captured with curl from the running app on 15 Oct 2026, in this order. Dates are relative to that day (check-in in 30 days). JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: a valid request

**Why:** every field fine, and they add up: recorded.

Request

``` code
POST /hotel-bookings HTTP/1.1
Content-Type: application/json

{
  "hotelId": 1,
  "roomType": "STANDARD",
  "checkIn": "2026-11-14",
  "checkOut": "2026-11-17",
  "adults": 2,
  "children": 0,
  "guestName": "Asha Verma",
  "phone": "98765 43210"
}
```

Response

``` code
HTTP/1.1 201 
Location: /hotel-bookings/1
Content-Type: application/json

{
  "id": 1,
  "hotelId": 1,
  "hotelName": "Ghoomo Inn, Jaipur",
  "roomType": "STANDARD",
  "checkIn": "2026-11-14",
  "checkOut": "2026-11-17",
  "nights": 3,
  "adults": 2,
  "children": 0,
  "guestName": "Asha Verma",
  "phone": "9876543210",
  "status": "REQUESTED"
}
```

### Case 2: read it back

**Why:** `200`.

Request

``` code
GET /hotel-bookings/1 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 224

{
  "id": 1,
  "hotelId": 1,
  "hotelName": "Ghoomo Inn, Jaipur",
  "roomType": "STANDARD",
  "checkIn": "2026-11-14",
  "checkOut": "2026-11-17",
  "nights": 3,
  "adults": 2,
  "children": 0,
  "guestName": "Asha Verma",
  "phone": "9876543210",
  "status": "REQUESTED"
}
```

### Case 3: check-out before check-in

**Why:** the first support ticket: `422` on `checkOut`.

Request

``` code
POST /hotel-bookings HTTP/1.1
Content-Type: application/json

{
  "hotelId": 1,
  "roomType": "STANDARD",
  "checkIn": "2026-11-17",
  "checkOut": "2026-11-14",
  "adults": 2,
  "children": 0,
  "guestName": "Asha Verma",
  "phone": "98765 43210"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "Each field is valid, but together they are not a possible booking.",
  "instance": "/hotel-bookings",
  "status": 422,
  "title": "Booking does not add up",
  "errors": {
    "checkOut": "must be after checkIn: a stay is at least one night"
  }
}
```

### Case 4: 4 adults and 2 children in a STANDARD room

**Why:** the second ticket: `422` on `guests`.

Request

``` code
POST /hotel-bookings HTTP/1.1
Content-Type: application/json

{
  "hotelId": 1,
  "roomType": "STANDARD",
  "checkIn": "2026-11-14",
  "checkOut": "2026-11-17",
  "adults": 4,
  "children": 2,
  "guestName": "Asha Verma",
  "phone": "98765 43210"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "Each field is valid, but together they are not a possible booking.",
  "instance": "/hotel-bookings",
  "status": 422,
  "title": "Booking does not add up",
  "errors": {
    "guests": "6 guests do not fit a STANDARD room, which sleeps 2"
  }
}
```

### Case 5: a 5-digit phone and 0 adults

**Why:** two broken fields, both named: `400`.

Request

``` code
POST /hotel-bookings HTTP/1.1
Content-Type: application/json

{
  "hotelId": 1,
  "roomType": "STANDARD",
  "checkIn": "2026-11-14",
  "checkOut": "2026-11-17",
  "adults": 0,
  "children": 0,
  "guestName": "Asha Verma",
  "phone": "12345"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Some fields are missing or malformed.",
  "instance": "/hotel-bookings",
  "status": 400,
  "title": "Bad Request",
  "errors": {
    "adults": "must be greater than or equal to 1",
    "phone": "must be a 10-digit Indian mobile number"
  }
}
```

### Case 6: no check-in and 6 adults

**Why:** the field error alone; the room rule waits: `400`.

Request

``` code
POST /hotel-bookings HTTP/1.1
Content-Type: application/json

{
  "hotelId": 1,
  "roomType": "STANDARD",
  "checkOut": "2026-11-17",
  "adults": 6,
  "children": 0,
  "guestName": "Asha Verma",
  "phone": "98765 43210"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Some fields are missing or malformed.",
  "instance": "/hotel-bookings",
  "status": 400,
  "title": "Bad Request",
  "errors": {
    "checkIn": "must not be null"
  }
}
```

### Case 7: booking 999

**Why:** `404`.

Request

``` code
GET /hotel-bookings/999 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No booking request 999.",
  "instance": "/hotel-bookings/999",
  "status": 404,
  "title": "Booking not found"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                           | What happens                              | Proved by                                           |
|--------------------------------------------------------------------------------|-------------------------------------------|-----------------------------------------------------|
| A valid request, read back                                                     | `201`, `200`                              | `aValidRequestIsRecordedAndCanBeReadBack`           |
| "family" and "+91 98765-43210" on a Turkish server                             | FAMILY, 9876543210                        | `phoneAndRoomTypeAreNormalisedEvenOnATurkishServer` |
| 0 adults, bad phone, no room type, non-ISO date, 2.5 adults, broken JSON       | `400`                                     | `brokenFieldsAre400AndNamed`                        |
| 0 nights, 31 nights, yesterday, 366 days ahead, unknown hotel or room          | `422`, field named                        | `fieldsThatDoNotAddUpAre422AndNamed`                |
| Tonight for one night; exactly 30 nights; 4 in a room for 4; no children field | Allowed                                   | `theEdgesAreAllowed`                                |
| A missing date and too many guests                                             | Only the `400`                            | `aBrokenFieldIsReportedAloneNotAsAnImpossibleStay`  |
| Unknown booking                                                                | `404`                                     | `unknownBookingsAre404`                             |
| Default group vs Consistency group                                             | Cross-field rules run only in their group | `BookingValidatorTest`                              |

## The trap

Plausible but wrong

Validating each field alone, so check-out before check-in passes.

The old request is kept in the tests as `OldHotelBookingRequest`: careful field rules, including `@FutureOrPresent` on both dates. The test runs the two bookings from the support tickets through the app's own validator: no violations at all. Then it sends the same bookings to the fixed API, which answers `422` and names the field.

While building, each part was undone once. Without `@ValidStay`, 3 tests turned red; without `@RoomFitsGuests`, 3; uppercasing room types with the server's locale instead of `Locale.ROOT`, 1 (the Turkish test). Moving the room rule into the Default group turned 5 red: it ran next to the field rules, so a missing date also produced a guests error, and too many guests became a `400`.

``` code
package com.ghoomo.bookings;

import jakarta.validation.Validator;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: the two bookings from the support tickets, through the old request's
 * field-by-field rules (with the app's own validator) and through the fixed API.
 */
class FieldByFieldTrapTest extends ApiTest {

    @Autowired
    Validator validator;

    @Test
    void checkOutBeforeCheckInPassesEveryFieldRule() throws Exception {
        var old = new OldHotelBookingRequest(1L, "STANDARD", today().plusDays(33), today().plusDays(30), 2, 0, "Asha Verma", "9876543210");
        assertThat(validator.validate(old)).isEmpty();   // both dates are in the future: each one is "valid"

        book(booking().replace(day(33), "OUT").replace(day(30), day(33)).replace("OUT", day(30)))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.errors.checkOut").value("must be after checkIn: a stay is at least one night"));
    }

    @Test
    void sixGuestsInATwoPersonRoomPassEveryFieldRule() throws Exception {
        var old = new OldHotelBookingRequest(1L, "STANDARD", today().plusDays(30), today().plusDays(33), 4, 2, "Asha Verma", "9876543210");
        assertThat(validator.validate(old)).isEmpty();   // 4 adults is within 1 to 10, 2 children within 0 to 10

        book(booking().replace("\"adults\":2,\"children\":0", "\"adults\":4,\"children\":2"))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.errors.guests").value("6 guests do not fit a STANDARD room, which sleeps 2"));
    }
}
```

``` code
package com.ghoomo.bookings;

import jakarta.validation.constraints.FutureOrPresent;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;

import java.time.LocalDate;

/**
 * The request as it shipped, kept only in tests: every field checked on its own, carefully, and nothing that looks
 * at two fields at once.
 */
record OldHotelBookingRequest(
        @NotNull Long hotelId,
        @NotBlank String roomType,
        @NotNull @FutureOrPresent LocalDate checkIn,
        @NotNull @FutureOrPresent LocalDate checkOut,
        @NotNull @Min(1) @Max(10) Integer adults,
        @Min(0) @Max(10) Integer children,
        @NotBlank String guestName,
        @NotBlank @Pattern(regexp = "[6-9][0-9]{9}") String phone) {
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
./mvnw test                 # all 12 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

In `HotelBookingRequest`, remove `groups = Consistency.class` from `@RoomFitsGuests` and run the contract tests.

``` code
./mvnw test -Dtest=BookingContractTest
```

Too many guests now comes back as `400`, and a request missing its check-in also gets a guests error. Put it back.

## Troubleshooting

| You see                                              | Cause                                             | Fix                                                                                                 |
|------------------------------------------------------|---------------------------------------------------|-----------------------------------------------------------------------------------------------------|
| A class-level rule never runs                        | It is in a group nobody validates.                | Validate that group (`validator.validate(r, Consistency.class)`), or list it in a `@GroupSequence`. |
| `NullPointerException` inside a validator            | A cross-field validator ran with a field missing. | Return `true` for missing values, and run after the field rules.                                    |
| A cross-field error shows at the top, not on a field | The default violation has no property path.       | `disableDefaultConstraintViolation()`, then `addPropertyNode("checkOut")`.                          |
| Constructor injection fails in a validator           | It was created outside Spring.                    | Validate with Spring's `Validator` bean, not `Validation.buildDefaultValidatorFactory()`.           |
| "FAMİLY" with a dotted İ                             | `toUpperCase()` uses the server locale.           | `toUpperCase(Locale.ROOT)` for identifiers.                                                         |

## Project layout

``` tree
stations/050-hotel-booking-request-validation/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/ghoomo/bookings/
│   ├── BookingController.java   ├── BookingDesk.java   ├── HotelBookingRequest.java   ├── Consistency.java
│   ├── ValidStay.java   ├── RoomFitsGuests.java   ├── IndianMobile.java
│   ├── ApiErrors.java   ├── HotelCatalog.java   └── BookingsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/ghoomo/bookings/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the validators.

#### `src/main/java/com/ghoomo/bookings/BookingController.java`

Does  
`@Valid` runs the field rules; then the desk; `Location` on success.

Why  
Field errors stop here with `400`.

Without it  
Cross-field checks on half-filled requests.

#### `src/main/java/com/ghoomo/bookings/BookingDesk.java`

Does  
Runs the `Consistency` group; answers `422` with an errors map, or records the request.

Why  
The second step, on purpose after the first.

Without it  
Impossible bookings recorded.

#### `src/main/java/com/ghoomo/bookings/HotelBookingRequest.java`

Does  
The request: field rules on components, two class-level rules in the `Consistency` group.

Why  
Which rule is which, visible in one place.

Without it  
Rules scattered through the service.

#### `src/main/java/com/ghoomo/bookings/ValidStay.java`

Does  
Dates: today or later (India), within a year, check-out after check-in, at most 30 nights.

Why  
A class-level validator, made by Spring so it gets the `Clock`.

Without it  
"Today" in UTC, and a check-out before check-in.

- Each failure is put on its field (`addPropertyNode`), so the form can show it in the right place.
- Missing dates return `true`: they are `@NotNull`'s errors, already reported.

#### `src/main/java/com/ghoomo/bookings/RoomFitsGuests.java`

Does  
Hotel, room type, and adults + children within what the room sleeps.

Why  
Gets the catalogue bean injected.

Without it  
6 guests in a room for 2.

#### `src/main/java/com/ghoomo/bookings/IndianMobile.java`

Does  
A field-level validator: 10 digits starting 6 to 9, with +91, 0, spaces or hyphens allowed.

Why  
One reusable annotation.

Without it  
A regex copied into every request.

#### `src/main/java/com/ghoomo/bookings/Consistency.java`

The validation group: an empty interface used as a name.

#### `src/main/java/com/ghoomo/bookings/ApiErrors.java`

Adds the `errors` map to Spring's `400` problem.

#### `src/main/java/com/ghoomo/bookings/HotelCatalog.java`

Demo hotels and what each room type sleeps; room types normalised with `Locale.ROOT`.

#### `src/main/java/com/ghoomo/bookings/BookingsApplication.java`

Entry point; a `Clock` in India time.

#### `src/main/resources/application.yaml`

Problem details on; decimals refused for whole-number fields.

# 2 · Build: Tests

## Required tests for this station

| Required by             | Requirement                              | Test class                 | Result |
|-------------------------|------------------------------------------|----------------------------|--------|
| Every station           | HTTP contract: valid, invalid, not found | `BookingContractTest` (7)  | pass   |
| Every station           | Reproduce the failure before the fix     | `FieldByFieldTrapTest` (2) | pass   |
| This station's concepts | Groups and validators on their own       | `BookingValidatorTest` (3) | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Hibernate Validator. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.ghoomo.bookings.FieldByFieldTrapTest
[INFO] Tests run: 7, Failures: 0, Errors: 0, Skipped: 0 -- in com.ghoomo.bookings.BookingContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.ghoomo.bookings.BookingValidatorTest
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/ghoomo/bookings/FieldByFieldTrapTest.java`

Written first: both support tickets pass the old rules, and fail the new API with `422`.

#### `src/test/java/com/ghoomo/bookings/BookingContractTest.java`

Valid, `400`, `422`, edges, the order of checks, `404`.

#### `src/test/java/com/ghoomo/bookings/BookingValidatorTest.java`

Which group runs which rule; the mobile formats accepted and refused.

#### `src/test/java/com/ghoomo/bookings/OldHotelBookingRequest.java`

The old request, kept only in tests.

#### `src/test/java/com/ghoomo/bookings/ApiTest.java`

Shared setup: a valid request with dates relative to today in India.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/ghoomo/bookings/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=ChildAgesChallengeTest`.
3.  Change the code until it passes, then run `./mvnw test` to check the other 12 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 16 tests pass (12 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## One age per child

Add `childAges`: one age, 0 to 17, per child. An age out of range is a broken field (`400`); a list that does not match `children` is a request that does not add up (`422`).

**Done when:** both tests in `ChildAgesChallengeTest` pass.

Hints

- Field rules on list elements: `List<@NotNull @Min(0) @Max(17) Integer>`.
- A new class-level constraint in the `Consistency` group compares the list's size with `children`.
- Keep an eight-argument constructor so existing code still compiles.

#### `challenge/ChildAgesChallengeTest.java`

``` code
package com.ghoomo.bookings;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: with children, the request carries "childAges", one age (0 to 17) per child. An age out of range is a
 * broken field (400, under "childAges[1]"); a list that does not match the number of children is a request that does
 * not add up (422, under "childAges"). No children: the list may be absent or empty.
 */
class ChildAgesChallengeTest extends ApiTest {

    String family(String children, String ages) {
        return booking().replace("STANDARD", "FAMILY").replace("\"children\":0", "\"children\":" + children + (ages == null ? "" : ",\"childAges\":" + ages));
    }

    @Test
    void oneAgePerChild() throws Exception {
        book(family("2", "[4,11]")).andExpect(status().isCreated());
        book(family("0", null)).andExpect(status().isCreated());
        book(family("2", "[4]")).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.errors.childAges").value("give one age for each of the 2 children"));
        book(family("2", null)).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.errors.childAges").exists());
    }

    @Test
    void anAgeOutOfRangeIsABrokenField() throws Exception {
        book(family("2", "[4,18]")).andExpect(status().isBadRequest()).andExpect(jsonPath("$.errors['childAges[1]']").exists());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## A GSTIN for the invoice

Add an optional `gstin` with a field-level validator: the 15-character shape and the published check character. Show it upper case. A format check only: it does not prove the GSTIN is registered.

**Done when:** both tests in `GstinChallengeTest` pass.

Hints

- Check character: for the first 14 characters (digits 0 to 9, letters 10 to 35), multiply by 1 and 2 alternately, add each product's quotient and remainder by 36, and the check is (36 − sum mod 36) mod 36.
- `null` is valid: optional means the validator says yes to nothing.

#### `challenge/GstinChallengeTest.java`

``` code
package com.ghoomo.bookings;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: a company may add an optional "gstin" for its invoice. Write a field-level ConstraintValidator: 15
 * characters (2-digit state code, 10-character PAN, entity code, "Z", check character) and the published check
 * character method. Lower case is accepted; the booking shows it upper case. A wrong one is 400. A format check only:
 * it does not prove the GSTIN is registered.
 */
class GstinChallengeTest extends ApiTest {

    String withGstin(String gstin) {
        return booking().replace("\"guestName\"", "\"gstin\":\"" + gstin + "\",\"guestName\"");
    }

    @Test
    void aWellFormedGstinIsKeptUpperCase() throws Exception {
        book(withGstin("27aapfu0939f1zv")).andExpect(status().isCreated()).andExpect(jsonPath("$.gstin").value("27AAPFU0939F1ZV"));
        book(booking()).andExpect(status().isCreated()).andExpect(jsonPath("$.gstin").doesNotExist());
    }

    @Test
    void aWrongCheckCharacterOrShapeIs400() throws Exception {
        book(withGstin("27AAPFU0939F1ZW")).andExpect(status().isBadRequest()).andExpect(jsonPath("$.errors.gstin").exists());
        book(withGstin("27AAPFU0939F1V")).andExpect(status().isBadRequest());
        book(withGstin("2AAAPFU0939F1ZV")).andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Where does each check belong?

For each rule here (date format, check-out after check-in, room sleeps everyone, room free on those nights, phone is real), decide where it is checked: in the app's form, in the request (400), in the service (422), in the database, or by calling someone else. Which ones must be repeated on the server even if the app checks them?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the support tickets through the old rules.
2.  Sort every rule: about one field, or about several (or about the catalogue)?
3.  Write the cross-field rules as class-level constraints in their own group; put each violation on its field.
4.  Run the groups in order and map them to `400` and `422`.

## Design alternatives and trade-offs

| Approach                                               | What it costs                                                              | Verdict                  |
|--------------------------------------------------------|----------------------------------------------------------------------------|--------------------------|
| Class-level constraints in a group, run after `@Valid` | Two small annotations and validators.                                      | Chosen                   |
| Field rules only                                       | Impossible combinations pass.                                              | The trap                 |
| `if` checks in the service                             | Works, but rules scatter and errors take ad-hoc shapes.                    | Fine for one rule        |
| A `@GroupSequence` on the request                      | One `@Valid` runs both in order, but both failures become the same status. | When 400 for all is fine |
| `400` for everything                                   | Clients cannot tell "fix this field" from "rethink the booking".           | Common, less helpful     |

## Database design

None in this station: requests live in a `ConcurrentHashMap`. When they move to a table, the stay rule becomes a constraint too (`CHECK (check_out > check_in)`), so a script that skips the API still cannot store one.

# 3 · Go deeper: Production

Time zones  
"Check-in today" depends on whose today. The app uses India time; a hotel abroad would use the hotel's zone.

Clients read your errors  
The `errors` map lets a form put each message beside its field. Changing a key breaks every client that reads it.

Rules change  
30 nights and 365 days are business numbers. Keep them in one place, and test the edges so a change is a one-line diff.

Validation is not authorisation  
A valid request from the wrong user is still wrong; that check is separate.

# 3 · Go deeper: Interview

## Interview takeaways

How do you validate that one field depends on another?

A class-level constraint: an annotation on the type and a ConstraintValidator that receives the whole object. Put the violation on the relevant field with addPropertyNode.

What are validation groups for?

To run subsets of rules at chosen moments: here, field rules first and cross-field rules only once the fields are valid. Groups can also differ between create and update.

400 or 422?

400 when the request is malformed or a field breaks its own rule; 422 when it is well-formed but describes something the server cannot do. Many APIs use 400 for both; the split helps clients know what to fix.

Can a ConstraintValidator use Spring beans?

Yes, when validation goes through Spring's Validator: Spring creates the validator and injects its constructor arguments, such as a Clock or a repository.

Why return true for null in a custom validator?

Each constraint checks one thing. Whether a value is required is @NotNull's job; returning false for null would report the same mistake twice.

## Self-check rubric

| Area        | Meets the bar                           | Above the bar                                             |
|-------------|-----------------------------------------|-----------------------------------------------------------|
| Correctness | All 12 tests pass.                      | You moved a rule between groups and explained the result. |
| Validators  | A field and a class-level validator.    | A validator using Spring beans.                           |
| Errors      | Every error on its field.               | A clear rule for 400 vs 422 you can defend.               |
| Edges       | Zero nights refused, one night allowed. | Time zone and locale considered.                          |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any request validation:

- Which rules compare two fields, and where are they checked?
- Can a cross-field rule run on a half-filled request?
- Does each error name the field the user must change?
- Are the edges (zero, one, the maximum) tested on both sides?
