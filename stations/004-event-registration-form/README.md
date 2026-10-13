# Station 004 · Event registration form

Foundations · 0–1 years · Core · Events · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · Bean Validation · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Registrations are kept in the app's memory and lost on restart. Two events are fixed in the code. No email is sent.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 20 tests.

# 1 · Understand

## The problem in real life

1.  **Registrations open for a tech summit**

    SeatSure's form collects name, email, phone and number of tickets.

2.  **Garbage gets in**

    A browser plugin, an old app version and a script all skip the form's checks. The server saves empty names, emails like "asha" and orders for 0 tickets.

3.  **The organiser exports a mess**

    Badges print blank, confirmation emails bounce, seat counts are wrong. The fix: the server checks every registration itself, and refuses bad ones with a clear list of what to fix.

Checks in the form are a convenience for the user. Checks on the server are the only ones you can rely on, because anyone can send a request without your form.

## What are we building?

Two endpoints: `POST /events/{eventId}/registrations` creates a registration after checking every field; `GET /events/{eventId}/registrations/{id}` reads it back. A valid registration gets `201` and its address; an invalid one gets `400` listing each mistake, and nothing is saved.

## An everyday analogy

At a passport office, the clerk checks your form before filing it: name filled in, photo attached, signature present. If something is missing, the form comes back with each problem marked, and nothing is filed. If it is fine, you get a receipt with a reference number. That receipt is `201 Created` with a `Location`.

## How it works in 4 steps

1.  **The form sends JSON** to `POST /events/pune-tech-summit-2026/registrations`.
2.  **Spring turns it into a record**, trims spaces, and checks every rule on it. Any broken rule: `400` with one message per field.
3.  **The server checks the event exists** (`404` if not), then saves the registration with its own id and time.
4.  **The answer** is `201 Created`, a `Location` to read it back, and the saved registration.

Check yourself: the form in the browser already refuses 0 tickets. Why check again on the server?

Because the browser form is not the only way to reach the server. Anyone can send the same request with curl, a script, or an old version of the app. The server is the last place every request passes through, so that is where the rules must hold.

## What this station is not

- **No database.** Registrations live in memory and vanish on restart.
- **No duplicate check.** The same email can register twice; Practice challenge 1 adds the rule.
- **No seat limit and no payment.** Tickets are a number, nothing more.
- **No confirmation email.** `@Email` checks the shape of an address, not that it exists.

## Key terms

| Term                | Simple meaning                                                 | Everyday example                                | In this project                         |
|---------------------|----------------------------------------------------------------|-------------------------------------------------|-----------------------------------------|
| **Request body**    | The data sent with a `POST`, here as JSON.                     | The filled-in form you hand over.               | `{"name":"Asha","tickets":2,…}`         |
| **DTO record**      | A small class that only describes the shape of incoming data.  | The blank form itself: which boxes exist.       | `RegistrationRequest`                   |
| **Bean Validation** | Rules written as annotations on fields, checked automatically. | "Required" stars on a form.                     | `@NotBlank`, `@Email`, `@Min(1)`        |
| **`@Valid`**        | Tells Spring to check those rules before your method runs.     | The clerk who checks the form before filing it. | On the request body in the controller.  |
| **201 Created**     | "I made something new."                                        | A receipt with a reference number.              | A new registration.                     |
| **Location header** | Where the new thing can be read.                               | "Your file is in cabinet 3, drawer 2."          | `/events/…/registrations/{id}`          |
| **400 Bad Request** | "Your request is wrong; fix it and send again."                | A form returned with the mistakes circled.      | Empty name, 0 tickets, malformed email. |

# 2 · Build: Spec

## Business problem

**SeatSure** (a fictional event-ticketing platform) runs registrations for conferences and festivals. Its API saves whatever it receives. The organiser of the Pune Tech Summit exported registrations and found blank names, emails without an `@`, and orders for 0 tickets. Badges could not be printed, confirmation emails bounced, and the headcount was wrong.

The web form had checks, but the mobile app's old version did not, and some registrations came from a partner's script. The server was trusting every client to have checked.

## Acceptance criteria

1.  **Given** a name, a valid email and 1 to 10 tickets, **when** the form is sent, **then** `201 Created` with a `Location` header and the saved registration.
2.  **Given** the `Location`, **when** it is read, **then** the same registration comes back.
3.  **Given** a blank name, a malformed email, 0 or 11 tickets, or a wrong phone, **then** `400` listing every bad field, and nothing is saved.
4.  **Given** `"tickets": 2.5` or `"tickets": "two"`, **then** `400`: never rounded to 2.
5.  **Given** an `id` or `registeredAt` in the body, **then** they are ignored; the server sets both.
6.  **Given** an unknown event, **then** `404`. **Given** a registration id from another event, **then** `404`.

## Requirements

- `name`: required, 1–100 characters after trimming.
- `email`: required, at most 254 characters, shaped like an email address.
- `phone`: optional; when given, 10 digits starting with 6–9 (a demo rule, not an official numbering rule). Blank means no phone.
- `tickets`: required whole number, 1 to 10 (a demo rule).
- Body must be JSON (`415` otherwise). Errors are RFC 9457 problems with an `errors` map.

## Learning objectives

- Receive a JSON body into a record with `@PostMapping` and `@RequestBody`.
- Write validation rules with Bean Validation and switch them on with `@Valid`.
- Return `201 Created` with a `Location` header.
- Explain why the server must validate even when the client does.
- Spot a silent conversion (2.5 tickets becoming 2) and turn it into a `400`.

# 2 · Build: API contract

## Endpoints

| Method | Path                                   | Purpose                |
|--------|----------------------------------------|------------------------|
| `POST` | `/events/{eventId}/registrations`      | Register for an event. |
| `GET`  | `/events/{eventId}/registrations/{id}` | Read one registration. |

## Request body

| Field     | Type    | Rule                                                               |
|-----------|---------|--------------------------------------------------------------------|
| `name`    | string  | Required. Trimmed, then 1–100 characters.                          |
| `email`   | string  | Required. Trimmed, at most 254 characters, `name@domain` shape.    |
| `phone`   | string  | Optional. 10 digits starting with 6–9. Blank is treated as absent. |
| `tickets` | integer | Required. 1 to 10. No fractions.                                   |

## Status codes

| Status | When                                                    | Body                                                    |
|--------|---------------------------------------------------------|---------------------------------------------------------|
| 201    | Registration saved                                      | The registration; `Location` header                     |
| 200    | `GET` of an existing registration                       | The registration                                        |
| 400    | Invalid field, broken or missing JSON, malformed id     | Problem with `errors` (field → message) for field rules |
| 404    | Unknown event, or no such registration under this event | Problem                                                 |
| 415    | Body is not JSON                                        | Problem                                                 |

## Captured examples

Captured with curl from the running app on 13 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: a valid registration

**Why:** every rule passes, so the server saves it with its own id and time: `201`, and `Location` says where to read it.

Request

``` code
POST /events/pune-tech-summit-2026/registrations HTTP/1.1
Content-Type: application/json

{
  "name": "Asha Kulkarni",
  "email": "asha.k@example.com",
  "phone": "9876543210",
  "tickets": 2
}
```

Response

``` code
HTTP/1.1 201 
Location: /events/pune-tech-summit-2026/registrations/8c1d489a-c290-4464-9e61-6365a9d73123
Content-Type: application/json

{
  "id": "8c1d489a-c290-4464-9e61-6365a9d73123",
  "eventId": "pune-tech-summit-2026",
  "name": "Asha Kulkarni",
  "email": "asha.k@example.com",
  "phone": "9876543210",
  "tickets": 2,
  "registeredAt": "2026-10-13T13:36:00.912Z"
}
```

### Case 2: the form the old app sent

**Why:** three rules broken, three messages, in one answer. Nothing is saved, so the organiser's export stays clean.

Request

``` code
POST /events/pune-tech-summit-2026/registrations HTTP/1.1
Content-Type: application/json

{
  "name": "   ",
  "email": "asha",
  "tickets": 0
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "The registration has invalid fields.",
  "instance": "/events/pune-tech-summit-2026/registrations",
  "status": 400,
  "title": "Bad Request",
  "errors": {
    "email": "must be an email address like name@example.com",
    "name": "must not be blank",
    "tickets": "must be greater than or equal to 1"
  }
}
```

### Case 3: 2.5 tickets

**Why:** the field is a whole number. Without a setting, Jackson would quietly store 2; here it is refused. The `400` comes from reading the JSON, before validation, so there is no `errors` map.

Request

``` code
POST /events/pune-tech-summit-2026/registrations HTTP/1.1
Content-Type: application/json

{
  "name": "Ravi",
  "email": "ravi@example.com",
  "tickets": 2.5
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Failed to read request",
  "instance": "/events/pune-tech-summit-2026/registrations",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 4: read it back

**Why:** the `Location` from case 1 returns the same registration.

Request

``` code
GET /events/pune-tech-summit-2026/registrations/8c1d489a-c290-4464-9e61-6365a9d73123 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 206

{
  "id": "8c1d489a-c290-4464-9e61-6365a9d73123",
  "eventId": "pune-tech-summit-2026",
  "name": "Asha Kulkarni",
  "email": "asha.k@example.com",
  "phone": "9876543210",
  "tickets": 2,
  "registeredAt": "2026-10-13T13:36:00.912Z"
}
```

### Case 5: unknown event

**Why:** the body is valid, but there is no such event, so `404`.

Request

``` code
POST /events/mumbai-marathon-2026/registrations HTTP/1.1
Content-Type: application/json

{
  "name": "Ravi",
  "email": "ravi@example.com",
  "tickets": 1
}
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No event has the id mumbai-marathon-2026.",
  "instance": "/events/mumbai-marathon-2026/registrations",
  "status": 404,
  "title": "Event not found"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                              | What the API does                                                        | Proved by                                                                                                |
|-------------------------------------------------------------------|--------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------|
| Valid registration                                                | `201`, `Location`, body                                                  | `validRegistrationIs201WithLocationAndBody`                                                              |
| Read back at `Location`                                           | Same registration                                                        | `theRegistrationCanBeReadBackAtItsLocation`                                                              |
| Spaces around values; blank phone                                 | Trimmed; phone `null`                                                    | `surroundingSpacesAreTrimmedAndABlankPhoneMeansNoPhone`                                                  |
| Blank name, bad email, 0 tickets                                  | `400`, one message each, nothing saved                                   | `withValidationTheSameRequestIs400AndNothingIsSaved`                                                     |
| Empty object `{}`                                                 | `400` listing name, email, tickets                                       | `everyMissingFieldIsListed`                                                                              |
| 11 tickets; 0 or negative                                         | `400`                                                                    | `moreThan10TicketsIs400`, `ticketsFrom1To10`                                                             |
| 2.5 tickets, "two" tickets                                        | `400`, never rounded                                                     | `ticketsMustBeAWholeNumber`                                                                              |
| Wrong phone, `+91` prefix                                         | `400`                                                                    | `aWrongPhoneIs400`, `phoneIsOptionalButMustBeAMobileNumberWhenGiven`                                     |
| Name of 101 characters                                            | Rejected                                                                 | `nameLongerThan100IsRejected`                                                                            |
| `asha@localhost`                                                  | Accepted: valid shape. Only a confirmation email proves an address works | `emailChecksTheShapeNotThatTheAddressExists`                                                             |
| Broken or missing JSON                                            | `400`                                                                    | `brokenOrMissingJsonIs400`                                                                               |
| Form-encoded body                                                 | `415`                                                                    | `aFormPostInsteadOfJsonIs415`                                                                            |
| Client sends `id`, `registeredAt`                                 | Ignored; the server sets them                                            | `theClientCannotChooseTheIdOrTheTime`                                                                    |
| Unknown event; unknown registration; another event's registration | `404`                                                                    | `unknownEventIs404ForPostAndGet`, `unknownRegistrationIs404`, `aRegistrationIsNotFoundUnderAnotherEvent` |
| Registration id that is not a UUID                                | `400`                                                                    | `aMalformedRegistrationIdIs400`                                                                          |

## The trap

Plausible but wrong

Trusting the client: no validation, so 0 tickets and empty names are saved.

"The form already checks it" is the reasoning. The first test sends what a script or an old app sends, to a "before" controller without `@Valid`: it is saved. The second sends the same body to the real API: `400`, three messages, nothing saved. Removing `@Valid` from the real controller was tried while building: 4 tests went red.

``` code
package com.seatsure.registrations;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * Someone submits the form with an empty name, "asha" as the email, and 0 tickets.
 */
@Import(TrustingTheClientTrapTest.NaiveRegistrationController.class)
class TrustingTheClientTrapTest extends ApiTest {

    static final String GARBAGE = """
            {"name":"   ","email":"asha","tickets":0}
            """;

    /** The "before" code: the same store, but no @Valid. It trusts that the form already checked everything. */
    @RestController
    static class NaiveRegistrationController {
        private final RegistrationStore store;

        NaiveRegistrationController(RegistrationStore store) {
            this.store = store;
        }

        @PostMapping("/naive/events/{eventId}/registrations")
        Registration register(@PathVariable String eventId, @RequestBody RegistrationRequest request) {
            return store.save(eventId, request);
        }
    }

    @Test
    void withoutValidationGarbageIsSavedAndTheOrganiserExportsIt() throws Exception {
        int before = store.count();
        mvc.perform(post("/naive/events/pune-tech-summit-2026/registrations").contentType(MediaType.APPLICATION_JSON).content(GARBAGE))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value(""))       // the bug: a nameless registration
                .andExpect(jsonPath("$.email").value("asha"))   // nobody can be emailed
                .andExpect(jsonPath("$.tickets").value(0));     // a registration for no seats
        assertThat(store.count()).isEqualTo(before + 1);
    }

    @Test
    void withValidationTheSameRequestIs400AndNothingIsSaved() throws Exception {
        int before = store.count();
        register("pune-tech-summit-2026", GARBAGE)
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.name").value("must not be blank"))
                .andExpect(jsonPath("$.errors.email").value("must be an email address like name@example.com"))
                .andExpect(jsonPath("$.errors.tickets").value("must be greater than or equal to 1"));
        assertThat(store.count()).isEqualTo(before);
    }
}
```

### A second trap the tests found

While building this station, `ticketsMustBeAWholeNumber` failed: `"tickets": 2.5` was saved as 2 tickets. Jackson converts a fraction to a whole number by default, before validation ever sees it. One setting in `application.yaml` (`accept-float-as-int: false`) makes it a `400`. The test was red before the setting and green after.

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
./mvnw test                 # all 20 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

JSON quoting differs between shells, so the bodies are files: `docs/registration.json` (valid) and `docs/registration-garbage.json` (the old app's form).

``` code
# Valid: expect 201 and a Location header
curl -i -X POST http://localhost:8080/events/pune-tech-summit-2026/registrations -H "Content-Type: application/json" -d "@docs/registration.json"

# Garbage: expect 400 with three messages under "errors"
curl -i -X POST http://localhost:8080/events/pune-tech-summit-2026/registrations -H "Content-Type: application/json" -d "@docs/registration-garbage.json"

# Read back: paste the Location from the first answer
curl -i http://localhost:8080/events/pune-tech-summit-2026/registrations/PASTE-THE-ID
```

In PowerShell, write `curl.exe` if `curl` opens a different command.

## Troubleshooting

| You see                             | Cause                                                   | Fix                                                            |
|-------------------------------------|---------------------------------------------------------|----------------------------------------------------------------|
| `415 Unsupported Media Type`        | The `Content-Type: application/json` header is missing. | Add `-H "Content-Type: application/json"`.                     |
| `400` with "Failed to read request" | The JSON is broken, often by shell quoting.             | Send the body from a file with `-d "@docs/registration.json"`. |
| `release version 25 not supported`  | Maven is using an older JDK.                            | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`.       |

## Project layout

``` tree
stations/004-event-registration-form/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/seatsure/registrations/
│   ├── RegistrationController.java   ├── RegistrationRequest.java
│   ├── Registration.java             ├── RegistrationStore.java
│   ├── ApiErrors.java                └── RegistrationsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/seatsure/registrations/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/seatsure/registrations/RegistrationController.java`

Does  
Receives the two endpoints. `@Valid` on the body makes Spring check every rule first; then it checks the event, saves, and answers `201` with `Location`.

Why  
Keeps HTTP decisions (status codes, headers) in one place.

Without it  
No endpoints. Without `@Valid`, the rules on the record are never checked (the trap).

- `ResponseEntity.created(location).body(saved)` sets the status and the header together.

#### `src/main/java/com/seatsure/registrations/RegistrationRequest.java`

Does  
The shape of the form, with every rule as an annotation. The compact constructor trims text before the rules are checked.

Why  
The rules live next to the fields they guard, and the same rules apply to every client.

Without it  
Each client would need its own checks, and one of them would forget.

- Trimming in the constructor turns `" "` into `""`, which `@NotBlank` then rejects.
- `Integer tickets`, not `int`: a missing value is `null` and `@NotNull` reports it, instead of silently becoming 0.

#### `src/main/java/com/seatsure/registrations/Registration.java`

The saved registration and the response body. Only the server sets `id`, `eventId` and `registeredAt`.

#### `src/main/java/com/seatsure/registrations/RegistrationStore.java`

Does  
Knows the two events and keeps registrations in a `ConcurrentHashMap`.

Why  
Several requests can save at the same moment on different threads; a plain `HashMap` can lose entries or break under that.

Without it  
Nowhere to keep registrations.

- `find` filters by event, so an id from one event is not found under another.

#### `src/main/java/com/seatsure/registrations/ApiErrors.java`

Does  
Adds an `errors` map (field → message) to validation failures.

Why  
The form can show each message next to its input.

Without it  
The client gets "Bad Request" and has to guess which field is wrong.

#### `src/main/resources/application.yaml`

Turns off Jackson's float-to-int conversion, so 2.5 tickets is a `400`.

#### `src/main/java/com/seatsure/registrations/RegistrationsApplication.java`

Standard Spring Boot entry point.

#### `pom.xml`

Web MVC and validation; test starters for JUnit and MockMvc.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                              | Test class                      | Result |
|---------------|------------------------------------------|---------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found | `RegistrationContractTest` (14) | pass   |
| Every station | Reproduce the failure before the fix     | `TrustingTheClientTrapTest` (2) | pass   |
| This station  | Each validation rule at its boundaries   | `RegistrationRequestTest` (4)   | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 14, Failures: 0, Errors: 0, Skipped: 0 -- in com.seatsure.registrations.RegistrationContractTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.seatsure.registrations.RegistrationRequestTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.seatsure.registrations.TrustingTheClientTrapTest
[INFO] Tests run: 20, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/seatsure/registrations/TrustingTheClientTrapTest.java`

Written first: the old app's form saved without `@Valid`, then refused with it.

#### `src/test/java/com/seatsure/registrations/RegistrationContractTest.java`

Created, read back, trimmed, and every way to be refused.

#### `src/test/java/com/seatsure/registrations/RegistrationRequestTest.java`

The rules on their own, with a plain `Validator`: 1 and 10 tickets pass, 0 and 11 do not; what `@Email` does not check.

#### `src/test/java/com/seatsure/registrations/ApiTest.java`

Shared setup: the whole app through MockMvc, and a new email for each test so tests never depend on each other.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/seatsure/registrations/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=DuplicateEmailChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 20 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 26 tests pass (20 station tests and 6 challenge tests).

Challenge 1 · Beginner-friendly · about 30 minutes

## One registration per email

The same email may register only once per event, whatever its letter case or spaces. A second attempt gets `409 Conflict` with the title *Already registered*. The same email may register for a different event.

**Done when:** both tests in `DuplicateEmailChallengeTest` pass, and the station's tests still pass.

Hints

- The request is already trimmed; lower-case the email with `Locale.ROOT` for the comparison.
- "Check, then save" lets two requests at the same moment both pass. `ConcurrentHashMap.putIfAbsent` does the check and the save in one step.
- Throw an `ErrorResponseException` with `HttpStatus.CONFLICT`; no handler needed.

#### `challenge/DuplicateEmailChallengeTest.java`

``` code
package com.seatsure.registrations;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: one registration per email per event. Letter case and spaces do not make a new person. */
class DuplicateEmailChallengeTest extends ApiTest {

    @Test
    void theSameEmailTwiceForOneEventIs409() throws Exception {
        register("pune-tech-summit-2026", """
                {"name":"Neha","email":"neha.dup@example.com","tickets":1}""").andExpect(status().isCreated());
        register("pune-tech-summit-2026", """
                {"name":"Neha S","email":"  NEHA.DUP@Example.com ","tickets":3}""")
                .andExpect(status().isConflict())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("Already registered"));
    }

    @Test
    void theSameEmailForAnotherEventIsFine() throws Exception {
        register("pune-tech-summit-2026", """
                {"name":"Kabir","email":"kabir.two@example.com","tickets":1}""").andExpect(status().isCreated());
        register("goa-food-fest-2026", """
                {"name":"Kabir","email":"kabir.two@example.com","tickets":1}""").andExpect(status().isCreated());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 40 minutes

## Export for the organiser, safely

Add `GET /events/{eventId}/registrations/export` returning `text/csv`: a header row, then one row per registration. Names with commas or quotes must stay one cell, and a name like `=HYPERLINK(…)` must not run as a formula when the file opens in a spreadsheet.

**Done when:** all four tests in `CsvExportChallengeTest` pass.

Hints

- CSV rule: wrap a field in double quotes when it contains a comma, a quote or a line break, and double any quote inside it.
- A cell starting with `=`, `+`, `-` or `@` runs as a formula (OWASP calls this CSV injection). Prefix such text with an apostrophe.
- `@GetMapping(value = "/export", produces = "text/csv")` sets the content type.

#### `challenge/CsvExportChallengeTest.java`

``` code
package com.seatsure.registrations;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: the organiser downloads registrations as CSV, and the file must open safely in a spreadsheet. */
class CsvExportChallengeTest extends ApiTest {

    @Test
    void exportIsCsvWithAHeaderRow() throws Exception {
        register("goa-food-fest-2026", """
                {"name":"Priya Nair","email":"priya.csv@example.com","phone":"9123456780","tickets":4}""");
        String csv = mvc.perform(get("/events/goa-food-fest-2026/registrations/export"))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith("text/csv"))
                .andReturn().getResponse().getContentAsString();
        assertThat(csv).startsWith("name,email,phone,tickets\r\n");
        assertThat(csv).contains("Priya Nair,priya.csv@example.com,9123456780,4\r\n");
    }

    @Test
    void commasAndQuotesAreEscaped() throws Exception {
        register("goa-food-fest-2026", """
                {"name":"Rao, Asha \\"Ash\\"","email":"ash.csv@example.com","tickets":1}""");
        String csv = mvc.perform(get("/events/goa-food-fest-2026/registrations/export")).andReturn().getResponse().getContentAsString();
        assertThat(csv).contains("\"Rao, Asha \"\"Ash\"\"\",ash.csv@example.com,,1\r\n");
    }

    @Test
    void aNameThatLooksLikeAFormulaCannotRunInTheSpreadsheet() throws Exception {
        register("goa-food-fest-2026", """
                {"name":"=HYPERLINK(\\"http://evil.example\\")","email":"formula.csv@example.com","tickets":1}""");
        String csv = mvc.perform(get("/events/goa-food-fest-2026/registrations/export")).andReturn().getResponse().getContentAsString();
        assertThat(csv).contains("\"'=HYPERLINK(\"\"http://evil.example\"\")\",formula.csv@example.com,,1\r\n");
    }

    @Test
    void unknownEventIs404() throws Exception {
        mvc.perform(get("/events/no-such-event/registrations/export")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Seat limits

The summit has 500 seats. Where would you store "seats left", and how would you stop two registrations for the last 3 seats from both succeeding? Which status code would you return when it is full, and what should the app show? (Station 082, movie seat holds, builds this with a real concurrency test.)

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: without `@Valid`, garbage is saved.
2.  Write `RegistrationRequest` with one annotation per rule, and trimming in its constructor.
3.  Add `@Valid` and the `errors` map; check the event; save; answer `201` with `Location`.
4.  Add `GET` by id, scoped to its event.
5.  Test each boundary, and the odd inputs: fractions, extra fields, wrong content type.

## Design alternatives and trade-offs

| Approach                                    | What it costs                                                                | Verdict  |
|---------------------------------------------|------------------------------------------------------------------------------|----------|
| Bean Validation annotations + `@Valid`      | Rules are declarative and reused by every endpoint that takes this record.   | Chosen   |
| `if` checks in the controller               | Works, but rules spread across methods and drift apart.                      | Possible |
| Trust the client's checks                   | Garbage in the export; the trap.                                             | Wrong    |
| Return `200` for a create                   | The client cannot tell "made something" from "did something"; no `Location`. | Wrong    |
| Return the first error only                 | The user fixes one field, submits, and meets the next error.                 | Wrong    |
| Let the client send `id` and `registeredAt` | Clients could overwrite or back-date records.                                | Wrong    |

## Database design

None in this station: registrations live in a `ConcurrentHashMap`. When a database arrives, the same rules become column constraints too (`NOT NULL`, `CHECK (tickets BETWEEN 1 AND 10)`), so a script that skips the API still cannot store garbage.

# 3 · Go deeper: Production

Security  
Every field has a maximum length, so nobody can store a 10 MB name. Names are stored as text and returned as JSON; showing them in HTML safely is station 007's topic, and exporting them safely is Challenge 2. Emails and phones are personal data: do not log them in full.

Reliability  
Memory storage loses everything on restart. Acceptable for a lesson, never for real registrations.

Maintainability  
Demo limits (10 tickets, the phone pattern) are constants in one record; changing them is one line, and the tests show what else depends on them.

Privacy  
Collect only what the event needs. Phone is optional for that reason.

# 3 · Go deeper: Interview

## Interview takeaways

Why validate on the server if the form already validates?

Anyone can send a request without your form: curl, a script, an old app version. Client checks are for user experience; server checks are for correctness.

What does @Valid do, and what happens when a rule fails?

It makes Spring run the Bean Validation rules on the argument before calling your method. A failure throws MethodArgumentNotValidException, which becomes a 400; your method never runs.

Why 201 and not 200 for a create?

201 says a new resource was created, and the Location header says where it lives. Clients can read it back without guessing the URL.

Integer or int for a required number in a request?

Integer. A missing field becomes null, which @NotNull reports. An int would silently become 0, and the error message would be about the minimum instead of the missing value.

A client sends 2.5 for an integer field. What happens?

By default Jackson truncates it to 2 and nobody notices. Turn off accept-float-as-int so it becomes a 400.

## Self-check rubric

| Area        | Meets the bar                                 | Above the bar                                                |
|-------------|-----------------------------------------------|--------------------------------------------------------------|
| Correctness | All 20 tests pass.                            | You can predict which tests fail without `@Valid`.           |
| Robustness  | Every rule has a boundary test.               | You found an odd input the tests do not cover, and added it. |
| Design      | `201` + `Location`; all errors in one answer. | You can explain why the client must not choose the id.       |
| Explanation | You can say what `@Valid` does.               | You can explain the 2.5-tickets bug and its fix.             |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on your own code instead:

- Does every `@RequestBody` that has rules also have `@Valid`?
- Does every text field have a maximum length?
- Can a client set a field only the server should set?
- Does a create return `201` with `Location`?
