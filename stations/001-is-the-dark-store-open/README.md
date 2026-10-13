# Station 001 · Is the dark store open?

Foundations · 0–1 years · Core · Quick commerce · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Store statuses are a fixed list inside the app. Nothing reads a real store-operations system.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 8 tests.

# 1 · Understand

## The problem in real life

1.  **Priya opens the app**

    She lives near the Indiranagar dark store and the app says *Delivering in 10 minutes*.

2.  **The store is closed**

    Staff are counting stock. Her order is accepted, then cancelled 15 minutes later.

3.  **The fix**

    Before promising anything, the app asks the server: is this store open? The server answers clearly: open with a promise, closed with a reason, or "no such store".

An API that answers vaguely is as bad as no API: the app guesses, and the guess shows up as a broken promise to a customer.

## What are we building?

One read-only endpoint, `GET /stores/{storeId}/status`. It says whether a dark store is open, why it is closed, and how fast it can deliver. For a store that does not exist it says so, with `404`.

## An everyday analogy

You call a shop. Three answers are useful: "Yes, we're open, come in 10 minutes", "We're closed today for stock-taking", or "Wrong number, there's no shop here." The useless answer is silence: the line picks up and nobody speaks. That silence is what an empty `200` response is.

## How it works in 4 steps

1.  **The app sends** `GET /stores/BLR-IND-01/status`.
2.  **The server checks the id's shape.** If it does not look like `BLR-KOR-01`, it answers `400`.
3.  **The server looks the store up.** Not found: `404` with a problem body.
4.  **Found:** `200` with the status. A closed store has a reason and no delivery promise.

Check yourself: Indiranagar is closed for stock-taking. Should the API answer 404?

No. The store exists; being closed is its current state. The answer is `200` with `"open": false` and a reason. `404` means "there is no such store", which is a different fact the app handles differently (for example, by asking the customer to pick a store again).

## What this station is not

- **Not connected to real stores.** Four stores are fixed in the code. Reading live status from a database comes in later stations.
- **No opening hours or time zones.** A store is open or closed because the list says so.
- **No login.** Store status is public information here, so no authentication is needed.

## Key terms

| Term              | Simple meaning                                                                                | Everyday example                                 | In this project                                              |
|-------------------|-----------------------------------------------------------------------------------------------|--------------------------------------------------|--------------------------------------------------------------|
| **Endpoint**      | One address the app can call, such as `GET /stores/{id}/status`.                              | A counter in a bank: each one does one job.      | The only endpoint in this station.                           |
| **Path variable** | A part of the URL that changes from call to call.                                             | The flat number in an address.                   | `BLR-KOR-01` in `/stores/BLR-KOR-01/status`.                 |
| **Status code**   | A three-digit number that says how the request went, before you read the body.                | A green or red light at a gate.                  | `200` found, `404` no such store, `400` the id is malformed. |
| **JSON**          | Text the app can read as named fields.                                                        | A form with labelled boxes.                      | `{"open":false,"reason":"Closed for stock-taking"}`          |
| **Record**        | A Java class that just carries data; Spring turns it into JSON.                               | A printed receipt: fixed fields, no surprises.   | `StoreStatus`.                                               |
| **Problem body**  | A standard JSON shape for errors (RFC 9457): `type`, `title`, `status`, `detail`, `instance`. | A rejection slip that says which rule you broke. | The `404` and `400` answers.                                 |
| **MockMvc**       | A test tool that sends requests to your controllers without starting a real server.           | A flight simulator for the API.                  | Every test in this station.                                  |

# 2 · Build: Spec

## Business problem

**Basketo** (a fictional quick-commerce app) delivers groceries from small "dark stores" in about 10 minutes. The home screen shows a delivery promise for the customer's nearest store. Today the promise is shown even when that store is closed for stock-taking, so orders are accepted and then cancelled. Customers lose trust; support handles the complaints.

The app's developers say they call the status API, but for a store id that does not exist it answers `200` with an empty body, which their code reads as "no problem", and nothing stops it from showing the default promise.

## Acceptance criteria

1.  **Given** an open store, **when** the app asks for its status, **then** the API returns `200` with `open: true` and a delivery promise in minutes.
2.  **Given** a closed store, **then** `200` with `open: false`, a reason, and no delivery promise.
3.  **Given** a well-formed id that matches no store, **then** `404` with a problem body.
4.  **Given** an id that is not shaped like `BLR-KOR-01`, **then** `400` with a problem body.

## Requirements

- Store ids are three capital letters, a dash, three capital letters, a dash, two digits.
- Every error is an RFC 9457 `application/problem+json` body.
- A closed store has `deliveryPromiseMinutes: null`, never a number.
- The endpoint only reads; other methods get `405`.

## Learning objectives

- Read a Maven project: `pom.xml`, `src/main`, `src/test`, the wrapper.
- Write a `@RestController` with `@GetMapping` and `@PathVariable`.
- Return a record as JSON, and choose `200`, `400` or `404` with `ResponseEntity`.
- Explain the difference between "exists but closed" and "does not exist".
- Write your first MockMvc test.

# 2 · Build: API contract

## Endpoint

| Method | Path                       | Purpose                                               |
|--------|----------------------------|-------------------------------------------------------|
| `GET`  | `/stores/{storeId}/status` | Is this dark store open, and how fast can it deliver? |

## Response fields

| Field                    | Type            | Meaning                                 |
|--------------------------|-----------------|-----------------------------------------|
| `storeId`                | string          | The store's id, e.g. `BLR-KOR-01`.      |
| `name`                   | string          | Area name for display.                  |
| `open`                   | boolean         | Whether the store takes orders now.     |
| `reason`                 | string or null  | Why it is closed; `null` when open.     |
| `deliveryPromiseMinutes` | integer or null | Minutes to promise; `null` when closed. |

## Status codes

| Status | When                                   | Body                        |
|--------|----------------------------------------|-----------------------------|
| 200    | The store exists (open or closed)      | The status                  |
| 400    | The id is not shaped like `BLR-KOR-01` | Problem: *Invalid store id* |
| 404    | No store has this id                   | Problem: *Store not found*  |
| 405    | Any method other than `GET`            | Problem                     |

## Captured examples

Captured with curl from the running app on 13 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: an open store

**Why:** the store exists and is open, so `200` with a 10-minute promise.

Request

``` code
GET /stores/BLR-KOR-01/status HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json

{
  "storeId": "BLR-KOR-01",
  "name": "Koramangala",
  "open": true,
  "reason": null,
  "deliveryPromiseMinutes": 10
}
```

### Case 2: a closed store

**Why:** the store exists, so still `200`. `open` is false, the reason is given, and there is no promise for the app to show.

Request

``` code
GET /stores/BLR-IND-01/status HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json

{
  "storeId": "BLR-IND-01",
  "name": "Indiranagar",
  "open": false,
  "reason": "Closed for stock-taking",
  "deliveryPromiseMinutes": null
}
```

### Case 3: a store that does not exist

**Why:** the id is well-formed but matches no store, so `404` with a problem body the app can act on.

Request

``` code
GET /stores/BLR-XYZ-99/status HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No dark store has the id BLR-XYZ-99.",
  "instance": "/stores/BLR-XYZ-99/status",
  "status": 404,
  "title": "Store not found"
}
```

### Case 4: a malformed id

**Why:** `koramangala` is an area name, not a store id, so `400`: the request itself is wrong.

Request

``` code
GET /stores/koramangala/status HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Store ids look like BLR-KOR-01: three capital letters, three capital letters, two digits.",
  "instance": "/stores/koramangala/status",
  "status": 400,
  "title": "Invalid store id"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                          | What the API does                                      | Proved by                                         |
|-------------------------------|--------------------------------------------------------|---------------------------------------------------|
| Open store                    | `200`, promise in minutes                              | `openStoreIs200WithADeliveryPromise`              |
| Closed store                  | `200`, reason, promise `null`                          | `closedStoreIs200WithAReasonAndNoDeliveryPromise` |
| Well-formed id, no such store | `404` problem with the path in `instance`              | `unknownStoreIs404Problem`                        |
| Area name instead of an id    | `400` problem                                          | `malformedStoreIdIs400Problem`                    |
| Lower-case id                 | `400` in this version; Practice challenge 1 accepts it | `CaseInsensitiveIdChallengeTest` (Practice)       |
| Wrong path or trailing slash  | `404`                                                  | `anotherPathUnderStoresIs404`                     |
| `POST` to the status          | `405`                                                  | `postIsNotAllowedOnTheStatus`                     |

## The trap

Plausible but wrong

Returning null for an unknown store, which Spring sends as `200` with an empty body.

It looks harmless: the lookup found nothing, so return nothing. But `200` tells the app "all good". The app has no field to read, falls back to its default, and shows "Delivering in 10 minutes". The first test reproduces this with a "before" controller kept only in the tests, then shows the fixed API answering `404`.

``` code
package com.basketo.stores;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * The app asks about a store id that does not exist (a typo, a store that was shut down, an old app version).
 */
@Import(UnknownStoreTrapTest.NaiveStoreController.class)
class UnknownStoreTrapTest extends ApiTest {

    /** The "before" code: returns whatever the lookup gives, even null. Kept only in tests, to show the trap. */
    @RestController
    static class NaiveStoreController {
        private final StoreDirectory directory;

        NaiveStoreController(StoreDirectory directory) {
            this.directory = directory;
        }

        @GetMapping("/naive/stores/{storeId}/status")
        StoreStatus status(@PathVariable String storeId) {
            return directory.find(storeId).orElse(null);
        }
    }

    @Test
    void naiveVersionAnswers200WithAnEmptyBodyForAStoreThatDoesNotExist() throws Exception {
        mvc.perform(get("/naive/stores/BLR-XYZ-99/status"))
                .andExpect(status().isOk())                 // the bug: "OK" for a store that does not exist
                .andExpect(content().string(""));           // and nothing the app can read
    }

    @Test
    void fixedVersionAnswers404WithAProblemBody() throws Exception {
        mvc.perform(get("/stores/BLR-XYZ-99/status"))
                .andExpect(status().isNotFound())
                .andExpect(content().contentType("application/problem+json"));
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                         | Check with       |
|----------|-------------------------------------------------|------------------|
| JDK      | 25 (recommended). JDK 21 also works, see below  | `java -version`  |
| Maven    | Not needed: the project ships the Maven wrapper |                  |
| Docker   | Not needed for this station                     |                  |
| curl     | Built into Windows 10+, macOS and Linux         | `curl --version` |

**macOS / Linux**

``` code
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 8 tests, no server needed
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`, for example `./mvnw -Djava.version=21 test`. Nothing here needs a Java 25 feature.

## Try it yourself

``` code
# Open store: expect 200 and "deliveryPromiseMinutes":10
curl -i http://localhost:8080/stores/BLR-KOR-01/status

# Closed store: expect 200, "open":false and a reason
curl -i http://localhost:8080/stores/BLR-IND-01/status

# No such store: expect 404 and Content-Type: application/problem+json
curl -i http://localhost:8080/stores/BLR-XYZ-99/status
```

In PowerShell, write `curl.exe` if `curl` opens a different command.

## Troubleshooting

| You see                            | Cause                             | Fix                                                                                      |
|------------------------------------|-----------------------------------|------------------------------------------------------------------------------------------|
| `release version 25 not supported` | Maven is using an older JDK.      | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`.                                 |
| `Port 8080 was already in use`     | Another app uses the port.        | Stop it, or run `./mvnw spring-boot:run -Dspring-boot.run.arguments=--server.port=8081`. |
| `'./mvnw' is not recognized`       | PowerShell needs the `.cmd` file. | Use `.\mvnw.cmd`.                                                                        |

## Project layout

``` tree
stations/001-is-the-dark-store-open/
├── pom.xml                 what to build and with which libraries
├── mvnw, mvnw.cmd, .mvn/   the Maven wrapper: downloads Maven on first run
├── src/main/java/com/basketo/stores/
│   ├── StoresApplication.java   ├── StoreController.java
│   ├── StoreStatus.java         └── StoreDirectory.java
├── src/main/resources/application.yaml
├── src/test/java/com/basketo/stores/   the tests (see Tests)
├── challenge/              Practice tests; solutions ship in a separate pack
└── docs/                   capture script, captures, saved test runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/basketo/stores/StoreController.java`

Does  
Receives `GET /stores/{storeId}/status`, checks the id's shape, and picks `200`, `400` or `404`.

Why  
HTTP decisions (status codes, error bodies) live in one place.

Without it  
No endpoint at all.

- `ResponseEntity` lets one method return a status with a body or a problem.
- `Optional.map(...).orElseGet(...)` forces both cases, found and not found, to be handled.

#### `src/main/java/com/basketo/stores/StoreStatus.java`

Does  
The response shape, as a record. Two factory methods make an open or a closed status.

Why  
`closed(...)` cannot take a delivery promise, so a closed store with "10 minutes" cannot be built by mistake.

Without it  
Each caller builds the JSON differently, and one forgets to clear the promise.

#### `src/main/java/com/basketo/stores/StoreDirectory.java`

Does  
Holds the four stores and finds one by id, returning `Optional`.

Why  
The controller should not know where data comes from; a later station swaps this for a database.

Without it  
The store list ends up inside the controller.

#### `src/main/java/com/basketo/stores/StoresApplication.java`

Standard Spring Boot entry point: `main` starts the embedded server on port 8080.

#### `src/main/resources/application.yaml`

Only the application name. Nothing else to configure.

#### `pom.xml`

The parent pins Spring Boot 4.1.1 and every library version. `spring-boot-starter-webmvc` brings Spring MVC, Jackson and Tomcat; the two test starters bring JUnit, AssertJ and MockMvc.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                              | Test class                    | Result |
|---------------|------------------------------------------|-------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found | `StoreStatusContractTest` (6) | pass   |
| Every station | Reproduce the failure before the fix     | `UnknownStoreTrapTest` (2)    | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.basketo.stores.StoreStatusContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.basketo.stores.UnknownStoreTrapTest
[INFO] Tests run: 8, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/basketo/stores/UnknownStoreTrapTest.java`

Written first: the empty `200`, then the `404` fix.

#### `src/test/java/com/basketo/stores/StoreStatusContractTest.java`

Open, closed, unknown, malformed, wrong path, wrong method.

#### `src/test/java/com/basketo/stores/ApiTest.java`

Shared setup: the whole app, called through MockMvc. `perform` sends a request; each `andExpect` checks one thing about the answer.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/basketo/stores/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=CaseInsensitiveIdChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 8 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 14 tests pass (8 station tests and 6 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Accept ids in any letter case

Customers type `blr-kor-01`. Accept any letter case, answer with the canonical upper-case id, and make sure a server running in a Turkish locale still works.

**Done when:** all three tests in `CaseInsensitiveIdChallengeTest` pass.

Hints

- Normalise once, at the start of the method, then use the normalised id everywhere.
- `"i".toUpperCase()` on a Turkish server gives `İ`, not `I`. Pass a fixed locale.

#### `challenge/CaseInsensitiveIdChallengeTest.java`

``` code
package com.basketo.stores;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.util.Locale;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: accept store ids in any letter case, on a server in any locale. */
class CaseInsensitiveIdChallengeTest extends ApiTest {

    private final Locale original = Locale.getDefault();

    @AfterEach
    void restoreLocale() {
        Locale.setDefault(original);
    }

    @Test
    void lowerCaseIdFindsTheStoreAndAnswersWithTheCanonicalId() throws Exception {
        mvc.perform(get("/stores/blr-kor-01/status"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.storeId").value("BLR-KOR-01"));
    }

    @Test
    void aTurkishServerLocaleDoesNotBreakIdsContainingI() throws Exception {
        Locale.setDefault(Locale.forLanguageTag("tr-TR")); // "i".toUpperCase() is now a dotted capital İ
        mvc.perform(get("/stores/blr-ind-01/status"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.storeId").value("BLR-IND-01"));
    }

    @Test
    void stillA400WhenTheShapeIsWrong() throws Exception {
        mvc.perform(get("/stores/koramangala/status")).andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Beginner-friendly · about 30 minutes

## List the stores in a city

Add `GET /stores?city=BLR`: every store in the city, open or closed, sorted by id. A city with no stores is an empty list.

**Done when:** all three tests in `CityStoresChallengeTest` pass.

Hints

- `@RequestParam String city` is required by default: Spring answers `400` when it is missing.
- `Map.of` has no fixed order. Sort, or the same request can give a different list.
- An empty list is `200 []`. `404` is for one thing that does not exist.

#### `challenge/CityStoresChallengeTest.java`

``` code
package com.basketo.stores;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: GET /stores?city=BLR lists every store in a city, open or closed, sorted by id. */
class CityStoresChallengeTest extends ApiTest {

    @Test
    void listsEveryStoreInTheCitySortedById() throws Exception {
        mvc.perform(get("/stores").param("city", "BLR"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(3)))
                .andExpect(jsonPath("$[0].storeId").value("BLR-HSR-02"))
                .andExpect(jsonPath("$[1].storeId").value("BLR-IND-01"))
                .andExpect(jsonPath("$[1].open").value(false))
                .andExpect(jsonPath("$[2].storeId").value("BLR-KOR-01"));
    }

    @Test
    void aCityWithNoStoresIsAnEmptyListNotA404() throws Exception {
        // A collection always exists; it can be empty. 404 is for one resource that does not exist.
        mvc.perform(get("/stores").param("city", "PNQ"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(0)));
    }

    @Test
    void missingCityIs400() throws Exception {
        mvc.perform(get("/stores")).andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Closing time is 1 a.m.

Stores now open at 6 a.m. and close at 1 a.m. the next day. Sketch how the status is worked out. Where does "now" come from, and how would you test 00:59 and 01:00 without waiting for the clock? Which time zone is "1 a.m." in when a store is in Delhi and the server runs in UTC?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test first: an unknown store must not be a silent `200`.
2.  Model the answer as a record with two factory methods, open and closed.
3.  Keep the data behind a small class that returns `Optional`.
4.  In the controller: check the id's shape (`400`), look it up (`404`), answer (`200`).
5.  Write the contract tests for each status code.

## Design alternatives and trade-offs

| Approach                                               | What it costs                                                                                          | Verdict |
|--------------------------------------------------------|--------------------------------------------------------------------------------------------------------|---------|
| `200` with the status; `404` problem for no such store | Two code paths in the app, both clear.                                                                 | Chosen  |
| Return `null` (empty `200`)                            | The app cannot tell "missing" from "fine".                                                             | Wrong   |
| `404` for a closed store                               | Mixes "does not exist" with "exists but closed"; the app would ask the customer to pick a store again. | Wrong   |
| `200` with `{"error":"not found"}`                     | Every client must parse the body to learn it failed; caches and monitoring see success.                | Wrong   |
| Throw an exception and map it to `404` in a handler    | Scales better when many endpoints share errors. Station 006 does this.                                 | Later   |

## Database design

None: four stores are fixed in `StoreDirectory`. Because the controller only sees `find(id)`, swapping in a database later changes one class.

# 3 · Go deeper: Production

Security  
Store status is public, so no login. The error body never echoes anything except the id you sent, and nothing about the server's internals.

Performance  
A map lookup: microseconds. The home screen calls this on every open, so in production it would be cached for a few seconds.

Reliability  
If the status source is down, answering "open" by default is the dangerous choice: it brings back the broken promise. Prefer an error the app can show as "status unavailable".

Maintainability  
The id rule lives in one regular expression. Change it in one place when Basketo adds 3-digit store numbers.

# 3 · Go deeper: Interview

## Interview takeaways

When do you return 404 and when 200 with an empty list?

404 when one specific resource does not exist, like store BLR-XYZ-99. A collection, like 'stores in Pune', always exists; when it has nothing in it, the answer is 200 with \[\].

Why not return null from a controller?

Spring sends null as 200 with an empty body. The client sees success, has nothing to read, and has to guess. A 404 with a problem body says exactly what happened.

What is the difference between 400 and 404 here?

400 means the request itself is wrong: the id is not even shaped like a store id, so asking again will never work. 404 means the request is fine but nothing matches it.

What does @RestController add over @Controller?

@ResponseBody on every method: return values are written to the response body as JSON instead of being treated as view names.

What does MockMvc test, and what does it skip?

It runs the real Spring MVC stack (routing, JSON, status codes) without a network or a server port. It skips the servlet container itself, so things like real ports or TLS are not tested.

## Self-check rubric

| Area        | Meets the bar                                  | Above the bar                                               |
|-------------|------------------------------------------------|-------------------------------------------------------------|
| Correctness | All 8 tests pass.                              | You can say which test fails if you return `null` again.    |
| Design      | Closed is `200`, unknown is `404`.             | You can explain why `404` for closed would hurt the app.    |
| Tests       | Contract tests for every status code.          | You wrote the trap test before the fix and watched it fail. |
| Explanation | You can walk a request through the controller. | You can explain what MockMvc does and does not test.        |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on your own code instead, the way a reviewer would:

- Can any path return `200` with an empty body?
- Does a closed store ever carry a delivery promise?
- Is every error `application/problem+json`?
- Is there a test for every status code the endpoint can return?
