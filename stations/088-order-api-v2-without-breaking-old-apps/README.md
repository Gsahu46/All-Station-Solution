# Station 088 · Order API v2 without breaking old apps

Working Systems · 0–2 years · Core · E-commerce · Types: none

Spring Boot 4.1.1 · Java 25 · Spring Framework 7 API versioning · Deprecation (RFC 9745) and Sunset (RFC 8594) headers · Jackson 3. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The orders are two demo orders kept in memory, not Kartwala's; the "old app" is a model class in the tests that reads JSON the way an app release would. The migration guide link is an example address.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 7 tests.

# 1 · Understand

## The problem in real life

1.  **A tidy rename**

    Kartwala's team cleaned up the order API: customerName became customer.name, qty became quantity, the total moved to paise. The new app used the new names. It shipped on a Friday.

2.  **Two days of broken orders**

    30% of users still had app 5.x. Its order screen read the old names, found nothing, and crashed. Users cannot be forced to update, and app store reviews take days.

3.  **The fix**

    The old shape comes back as v1, frozen, and the new shape is v2 beside it. v1 tells clients it is deprecated and when it ends. Old apps keep working until that date.

You cannot update the apps in people's pockets. Never rename, remove or change the meaning of a field in place: add a version.

## What are we building?

One order, two shapes: `/v1` exactly as old apps read it, `/v2` with the new names, side by side, with v1 announcing its end date.

## An everyday analogy

A city changes its bus numbers. It does not repaint every stop overnight: old and new numbers are shown together for months, with a notice saying when the old ones go.

## How it works in 4 steps

1.  **Freeze v1**: its names, types and values stay as old apps read them.
2.  **Add v2** beside it with the new shape; both read the same order.
3.  **Announce** on every v1 answer: deprecated since, ends on, where to read how to move.
4.  **Only add** to a version afterwards, never rename or remove; clients ignore what they do not know.

Check yourself: v1 sends total as rupees (1299.50). Is sending it in paise (129950) under the same name a compatible change?

No. The name and the type look the same, but the meaning changed: old apps would show ₹1,29,950 without any error. That is the flawed version in the Review tab.

## What this station is not

- **No database.** Two demo orders in memory: this station is about the API's shape.
- **No writes.** Only reading orders; versioning a write is challenge 3.
- **No real app.** The "old app" is a model class in the tests that reads JSON like the app did.

## Key terms

| Term                  | Simple meaning                                                                                                  | Everyday example                             | In this project                               |
|-----------------------|-----------------------------------------------------------------------------------------------------------------|----------------------------------------------|-----------------------------------------------|
| **API version**       | A fixed shape of answers that clients can rely on.                                                              | An edition of a timetable.                   | `/v1`, `/v2`                                  |
| **Breaking change**   | A change that makes an existing client fail or show wrong data: renaming, removing, changing a type or meaning. | Renumbering every bus route overnight.       | `customerName` to `customer.name`             |
| **Compatible change** | A change existing clients do not notice, such as a new field, if they ignore fields they do not know.           | A new bus stop on the route.                 | `trackingUrl` added to v1                     |
| **Tolerant reader**   | A client that reads only the fields it needs and ignores the rest.                                              | Reading only your own stop on the timetable. | `@JsonIgnoreProperties(ignoreUnknown = true)` |
| **Deprecation**       | A notice that a version will go away; it still works.                                                           | "This timetable ends in April."              | `Deprecation` header                          |
| **Sunset**            | The date a version stops working.                                                                               | The last day the old timetable runs.         | `Sunset` header                               |

# 2 · Build: Spec

## Business problem

**Kartwala** (a fictional shopping app): renaming a field broke 30% of users on old app versions for two days.

## Acceptance criteria

Demo dates: v1 deprecated from 1 Oct 2026 and ends on 1 Apr 2027 (midnight IST).

1.  **Given** `/v1/orders/{id}`, **then** exactly the fields, types and values app 5.x reads, plus fields added since.
2.  **Given** `/v2/orders/{id}`, **then** the new shape: customer object, paise, lower-case states.
3.  **Given** any v1 answer, **then** `Deprecation`, `Sunset` and a `Link` to the migration guide; v2 has none.
4.  **Given** an unknown order, **then** `404`; a non-numeric id or an unknown version, `400`.

## Requirements

- One order model; one response shape per version, built from it.
- A test reads v1 the way the old app does.
- Money in v1 stays an exact decimal of rupees, from paise, never through a `double`.

## Learning objectives

- Tell breaking changes from compatible ones, including changes of meaning.
- Use Spring Framework 7's API versioning on paths.
- Announce deprecation and sunset with standard headers, citing their status.
- Write clients and tests as tolerant readers.

# 2 · Build: API contract

## Endpoints

| Method | Path              | Purpose                                             |
|--------|-------------------|-----------------------------------------------------|
| `GET`  | `/v1/orders/{id}` | The frozen v1 shape, deprecated, with its end date. |
| `GET`  | `/v2/orders/{id}` | The new shape.                                      |

## Headers on v1

| Header                                  | Meaning                                                                   | Standard                           |
|-----------------------------------------|---------------------------------------------------------------------------|------------------------------------|
| `Deprecation: @1790793000`              | Deprecated since this moment (seconds since 1970: 1 Oct 2026, 00:00 IST). | RFC 9745, Proposed Standard (2025) |
| `Sunset: Wed, 31 Mar 2027 18:30:00 GMT` | Stops working at this moment (1 Apr 2027, 00:00 IST).                     | RFC 8594, Informational (2019)     |
| `Link: <...>; rel="deprecation"`        | Where to read how to move to v2.                                          | RFC 9745                           |

## Status codes

| Status | When                                                      |
|--------|-----------------------------------------------------------|
| 200    | The order, in the version asked for                       |
| 400    | An id that is not a number; a version that does not exist |
| 404    | No such order; a path that does not exist                 |

## Captured examples

Captured with curl from the running app on 22 Oct 2026, in this order. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: v1

**Why:** the old names, rupees as an exact decimal, and the three deprecation headers.

Request

``` code
GET /v1/orders/1001 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Deprecation: @1790793000
Link: <https://developer.kartwala.example/orders/v1-to-v2>; rel="deprecation"; type="text/html"
Sunset: Wed, 31 Mar 2027 18:30:00 GMT
Content-Type: application/json
Content-Length: 215

{
  "id": 1001,
  "customerName": "Meera Iyer",
  "total": 1299.5,
  "status": "SHIPPED",
  "items": [
    {
      "sku": "KW-TEE-01",
      "qty": 2,
      "price": 499.75
    },
    {
      "sku": "KW-CAP-07",
      "qty": 1,
      "price": 300.0
    }
  ],
  "trackingUrl": "https://track.example/KW1001"
}
```

### Case 2: v2

**Why:** the same order in the new shape; no deprecation headers.

Request

``` code
GET /v2/orders/1001 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 325

{
  "id": 1001,
  "customer": {
    "name": "Meera Iyer",
    "phone": "+919800000001"
  },
  "items": [
    {
      "sku": "KW-TEE-01",
      "quantity": 2,
      "unitPricePaise": 49975
    },
    {
      "sku": "KW-CAP-07",
      "quantity": 1,
      "unitPricePaise": 30000
    }
  ],
  "totalPaise": 129950,
  "currency": "INR",
  "status": "shipped",
  "placedAt": "2026-10-20T09:15:00Z",
  "trackingUrl": "https://track.example/KW1001"
}
```

### Case 3: v2, an order not shipped yet

**Why:** `trackingUrl` is `null`: present, so clients can rely on the field.

Request

``` code
GET /v2/orders/1002 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 240

{
  "id": 1002,
  "customer": {
    "name": "Arjun Rao",
    "phone": "+919800000002"
  },
  "items": [
    {
      "sku": "KW-MUG-03",
      "quantity": 4,
      "unitPricePaise": 24900
    }
  ],
  "totalPaise": 99600,
  "currency": "INR",
  "status": "placed",
  "placedAt": "2026-10-21T14:40:00Z",
  "trackingUrl": null
}
```

### Case 4: /v3

**Why:** Spring answers `400` for a version no endpoint has.

Request

``` code
GET /v3/orders/1001 HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid API version: '3.0.0'.",
  "instance": "/v3/orders/1001",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 5: v1, an unknown order

**Why:** `404`, still with the deprecation headers.

Request

``` code
GET /v1/orders/9 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Deprecation: @1790793000
Link: <https://developer.kartwala.example/orders/v1-to-v2>; rel="deprecation"; type="text/html"
Sunset: Wed, 31 Mar 2027 18:30:00 GMT
Content-Type: application/problem+json

{
  "detail": "No such order",
  "instance": "/v1/orders/9",
  "status": 404,
  "title": "Not Found"
}
```

### Case 6: v2, a non-numeric id

**Why:** `400`.

Request

``` code
GET /v2/orders/abc HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Failed to convert 'id' with value: 'abc'",
  "instance": "/v2/orders/abc",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 7: /v1.0

**Why:** Spring's version parser reads `v1`, `1` and `v1.0` as the same version.

Request

``` code
GET /v1.0/orders/1001 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Deprecation: @1790793000
Link: <https://developer.kartwala.example/orders/v1-to-v2>; rel="deprecation"; type="text/html"
Sunset: Wed, 31 Mar 2027 18:30:00 GMT
Content-Type: application/json
Content-Length: 215

{
  "id": 1001,
  "customerName": "Meera Iyer",
  "total": 1299.5,
  "status": "SHIPPED",
  "items": [
    {
      "sku": "KW-TEE-01",
      "qty": 2,
      "price": 499.75
    },
    {
      "sku": "KW-CAP-07",
      "qty": 1,
      "price": 300.0
    }
  ],
  "trackingUrl": "https://track.example/KW1001"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                         | What happens                                           | Proved by                                        |
|----------------------------------------------|--------------------------------------------------------|--------------------------------------------------|
| v1, field by field                           | Exactly the old shape                                  | `v1KeepsTheShapeOldAppsParse`                    |
| v2, field by field; an order not shipped     | The new shape; `trackingUrl` null                      | `v2HasTheNewShape`                               |
| Deprecation headers                          | On v1 only, with the dates in standard form            | `v1IsMarkedDeprecatedWithItsEndDateAndV2IsNot`   |
| Unknown order, bad id, /v3, a trailing slash | `404`, `400`, `400`, `404`                             | `unknownOrdersAre404AndBadIdsOrVersionsAre400`   |
| The old app reads the renamed shape          | It fails; a lenient reader shows no customer, no total | `theRenamedShapeIsWhatBrokeTheOldApp`            |
| The old app reads v1                         | Every field it knows, exactly                          | `theOldAppStillReadsV1Completely`                |
| A field added to v1                          | Fine for a tolerant reader, fatal for a strict one     | `anAddedFieldIsCompatibleOnlyForATolerantReader` |

## The trap

Plausible but wrong

Renaming or removing fields in place, breaking old app versions.

- **The rename.** The test reads the new shape with app 5.x's own model. Jackson 3 refuses it: `qty` became `quantity`, and a missing `int` is an error. That is the crash. Even a reader that lets it pass shows an order with no customer and no total.
- **v1 today.** The same model reads `/v1` completely, value for value.
- **Adding is compatible, for tolerant readers.** `trackingUrl` was added to v1 later. A model that ignores unknown fields reads it; a strict one fails. Write clients the first way.

While building, each part was undone once: a v1 field renamed turned 3 tests red; v1's total in paise 2; v1's status in lower case 2; a v1 field removed 1; no deprecation headers 1; the Sunset date in IST 1; v2's status in upper case 1.

``` code
package com.kartwala.orders;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.databind.exc.MismatchedInputException;
import tools.jackson.databind.exc.UnrecognizedPropertyException;
import tools.jackson.databind.json.JsonMapper;

import java.math.BigDecimal;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/**
 * Written first. The old release renamed customerName to customer.name in place. Apps up to 5.x read orders with
 * the model below: reading the new shape failed and the order screen crashed for 30% of users. These tests read today's
 * answers the way that app does.
 */
@SpringBootTest
@AutoConfigureMockMvc
class RenameInPlaceTrapTest {

    /** What app 5.x reads, written like its own model class. It knows nothing of fields added later. */
    @JsonIgnoreProperties(ignoreUnknown = true)
    record OldAppOrder(long id, String customerName, BigDecimal total, String status, List<OldAppItem> items) {
    }

    record OldAppItem(String sku, int qty, BigDecimal price) {
    }

    /** The same model without ignoreUnknown, for a mapper that fails on unknown fields. */
    record StrictOldAppOrder(long id, String customerName, BigDecimal total, String status, List<OldAppItem> items) {
    }

    @Autowired
    MockMvc mvc;

    final JsonMapper json = JsonMapper.builder().build();

    String body(String path) throws Exception {
        return mvc.perform(get(path)).andReturn().getResponse().getContentAsString();
    }

    @Test
    void theRenamedShapeIsWhatBrokeTheOldApp() throws Exception {
        String renamed = body("/v2/orders/1001");   // the new shape, as if served where v1 was
        // Jackson 3 refuses a missing int (qty was renamed to quantity): the old app's screen crashes.
        assertThatThrownBy(() -> json.readValue(renamed, OldAppOrder.class)).isInstanceOf(MismatchedInputException.class)
                .hasMessageContaining("Cannot map `null` into type `int`");
        // Even a reader that lets that pass shows an order with no customer and no total.
        OldAppOrder seen = JsonMapper.builder().disable(DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES).build().readValue(renamed, OldAppOrder.class);
        assertThat(seen.customerName()).isNull();
        assertThat(seen.total()).isNull();
    }

    @Test
    void theOldAppStillReadsV1Completely() throws Exception {
        OldAppOrder seen = json.readValue(body("/v1/orders/1001"), OldAppOrder.class);
        assertThat(seen).isEqualTo(new OldAppOrder(1001, "Meera Iyer", new BigDecimal("1299.50"), "SHIPPED",
                List.of(new OldAppItem("KW-TEE-01", 2, new BigDecimal("499.75")), new OldAppItem("KW-CAP-07", 1, new BigDecimal("300.00")))));
    }

    @Test
    void anAddedFieldIsCompatibleOnlyForATolerantReader() throws Exception {
        String v1 = body("/v1/orders/1001");   // trackingUrl was added to v1 after app 5.x shipped
        JsonMapper strict = JsonMapper.builder().enable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES).build();
        assertThatThrownBy(() -> strict.readValue(v1, StrictOldAppOrder.class)).isInstanceOf(UnrecognizedPropertyException.class);
        assertThat(json.readValue(v1, OldAppOrder.class).customerName()).isEqualTo("Meera Iyer");
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                         | Check with      |
|----------|-------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below  | `java -version` |
| Maven    | Not needed: the project ships the Maven wrapper |                 |

**macOS / Linux**

``` code
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 7 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Ask for the same order in both versions and compare:

``` code
curl -s http://localhost:8080/v1/orders/1002; echo
curl -s http://localhost:8080/v2/orders/1002; echo
```

The answers, as `docs/capture.sh` saved them: the same order, the old names and rupees in v1, the new shape in v2.

``` code
v1 says: {"id":1002,"customerName":"Arjun Rao","total":996.00,"status":"PLACED","items":[{"sku":"KW-MUG-03","qty":4,"price":249.00}],"trackingUrl":null}
v2 says: {"id":1002,"customer":{"name":"Arjun Rao","phone":"+919800000002"},"items":[{"sku":"KW-MUG-03","quantity":4,"unitPricePaise":24900}],"totalPaise":99600,"currency":"INR","status":"placed","placedAt":"2026-10-21T14:40:00Z","trackingUrl":null}
```

## Troubleshooting

| You see                            | Cause                                                                 | Fix                                                                               |
|------------------------------------|-----------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| `Invalid API version: '3.0.0'.`    | No endpoint declares that version.                                    | Use `/v1` or `/v2`.                                                               |
| `Sunset` with `+0530` in it        | The sunset date was given with a time zone; Spring prints its offset. | Give the date in UTC, as `ApiVersions` does.                                      |
| An old client fails on a new field | It is a strict reader.                                                | Ignore unknown fields in clients (`@JsonIgnoreProperties(ignoreUnknown = true)`). |

## Project layout

``` tree
stations/088-order-api-v2-without-breaking-old-apps/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/kartwala/orders/
│   ├── ApiVersions.java   ├── OrderController.java   ├── Orders.java   └── OrdersApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/kartwala/orders/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

Configuration first, then the request's path.

#### `src/main/java/com/kartwala/orders/ApiVersions.java`

Does  
Versioning and deprecation, in one place.

Why  
The version is the first path segment; v1 gets Deprecation, Sunset and Link headers from Spring's `StandardApiVersionDeprecationHandler`.

Without it  
Version checks spread through controllers; deprecation only in a blog post.

The Sunset date is configured in UTC. Given in IST, Spring wrote `+0530` into the header, but an HTTP date is written in GMT. Found while building.

#### `src/main/java/com/kartwala/orders/OrderController.java`

Does  
One record per version, built from one order.

Why  
`@GetMapping(..., version = "1")` and `version = "2"` on the same path pattern.

Without it  
One shape changed for everyone at once.

- v1 is frozen: it may gain fields, never lose, rename or change one.
- v1's rupees are `BigDecimal.valueOf(paise, 2)`: exact.

#### `src/main/java/com/kartwala/orders/Orders.java`

The order model and two demo orders, shared by both versions.

#### `src/main/resources/application.yaml`

Problem details for errors.

#### `src/main/java/com/kartwala/orders/OrdersApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                              | Test class                  | Result |
|---------------|------------------------------------------|-----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found | `OrderContractTest` (4)     | pass   |
| Every station | Reproduce the failure before the fix     | `RenameInPlaceTrapTest` (3) | pass   |

The contract tests compare whole bodies in strict mode, so a removed or renamed field fails them. The trap test was first written expecting an empty name; the real old-app model failed harder, on the renamed `qty`, and the test now checks that. Found while building.

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.orders.OrderContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.orders.RenameInPlaceTrapTest
[INFO] Tests run: 7, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/kartwala/orders/RenameInPlaceTrapTest.java`

Written first: the old app's model reading the renamed shape, v1, and a field added later.

#### `src/test/java/com/kartwala/orders/OrderContractTest.java`

Both versions field by field, the deprecation headers, errors.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/kartwala/orders/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=SunsetChallengeTest`.
3.  Change the code until it passes, then run `./mvnw test` to check the other 7 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 10 tests pass (7 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## After the sunset

From 1 Apr 2027, 00:00 IST, `/v1` answers `410 Gone` with a link to the migration guide; `/v2` carries on.

**Done when:** the test in `SunsetChallengeTest` passes.

Hints

- Add a `Clock` bean and compare with `ApiVersions.V1_SUNSET`.
- The deprecation handler still adds its `Link` header to the `410`.

#### `challenge/SunsetChallengeTest.java`

``` code
package com.kartwala.orders;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.bean.override.convention.TestBean;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: from the sunset date (1 Apr 2027, IST), v1 answers 410 Gone with a link to the migration guide. v2 is unaffected. */
@SpringBootTest
@AutoConfigureMockMvc
class SunsetChallengeTest {

    static volatile Instant now = Instant.parse("2027-03-31T18:29:59Z");   // 23:59:59 IST on 31 Mar 2027

    @TestBean
    Clock clock;

    static Clock clock() {
        return new Clock() {
            public java.time.ZoneId getZone() {
                return ZoneOffset.UTC;
            }

            public Clock withZone(java.time.ZoneId zone) {
                return this;
            }

            public Instant instant() {
                return now;
            }
        };
    }

    @Autowired
    MockMvc mvc;

    @Test
    void v1WorksUntilItsSunsetAndIsGoneFromThen() throws Exception {
        now = Instant.parse("2027-03-31T18:29:59Z");
        mvc.perform(get("/v1/orders/1001")).andExpect(status().isOk());
        now = Instant.parse("2027-03-31T18:30:00Z");   // 00:00 IST on 1 Apr 2027
        mvc.perform(get("/v1/orders/1001")).andExpect(status().isGone())
                .andExpect(jsonPath("$.detail").value("Orders API v1 ended on 1 Apr 2027. Use v2: https://developer.kartwala.example/orders/v1-to-v2"))
                .andExpect(header().string("Link", "<https://developer.kartwala.example/orders/v1-to-v2>; rel=\"deprecation\"; type=\"text/html\""));
        mvc.perform(get("/v2/orders/1001")).andExpect(status().isOk());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Dated versions

`GET /orders/{id}` with `Kartwala-Version: 2026-10-01`: the shape current on that date, as Stripe names its versions. Before 1 Oct 2026, the v1 shape; from then, v2. No date, or not a date, `400`.

**Done when:** both tests in `DatedVersionChallengeTest` pass.

Hints

- The path versioning must now apply only to paths starting with `/v`: `usePathSegment(0, predicate)`, and a version is no longer required everywhere.
- Reuse the v1 and v2 shapes; the date only picks one.

#### `challenge/DatedVersionChallengeTest.java`

``` code
package com.kartwala.orders;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: dated versions, the way Stripe names them. GET /orders/{id} with a Kartwala-Version header holding a
 * date: the answer has the shape that was current on that date. The v2 shape was released on 2026-10-01.
 * The /v1 and /v2 paths keep working.
 */
@SpringBootTest
@AutoConfigureMockMvc
class DatedVersionChallengeTest {

    @Autowired
    MockMvc mvc;

    @Test
    void theDateChoosesTheShape() throws Exception {
        mvc.perform(get("/orders/1001").header("Kartwala-Version", "2025-06-01")).andExpect(status().isOk())
                .andExpect(jsonPath("$.customerName").value("Meera Iyer")).andExpect(jsonPath("$.total").value(1299.50));
        mvc.perform(get("/orders/1001").header("Kartwala-Version", "2026-09-30")).andExpect(jsonPath("$.customerName").value("Meera Iyer"));
        mvc.perform(get("/orders/1001").header("Kartwala-Version", "2026-10-01")).andExpect(jsonPath("$.customer.name").value("Meera Iyer"))
                .andExpect(jsonPath("$.totalPaise").value(129950));
        mvc.perform(get("/v2/orders/1001")).andExpect(jsonPath("$.totalPaise").value(129950));
    }

    @Test
    void aMissingOrBadDateIs400() throws Exception {
        mvc.perform(get("/orders/1001")).andExpect(status().isBadRequest());
        mvc.perform(get("/orders/1001").header("Kartwala-Version", "yesterday")).andExpect(status().isBadRequest());
        mvc.perform(get("/orders/1001").header("Kartwala-Version", "2026-13-01")).andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Writes, and the end of v1

Add `POST /v2/orders`. What does an old app sending a v1-shaped body need: a separate v1 endpoint, or a translation into the one model? Then plan v1's end: how do you learn who still calls it (logs by app version), when is it safe to switch it off, and what should the app show users who never update?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old app's model against the renamed shape and against v1.
2.  Configure path-segment versioning and the deprecation handler.
3.  Write one record per version, both built from the same order.
4.  Compare whole bodies strictly in contract tests, so any rename shows.

## Design alternatives and trade-offs

| Approach                                           | What it costs                                                      | Verdict         |
|----------------------------------------------------|--------------------------------------------------------------------|-----------------|
| Version in the path (`/v1`, `/v2`)                 | Visible, easy to cache and log; URLs change between versions.      | Chosen          |
| Version in a header (`API-Version: 2`)             | Clean URLs; easy to forget, harder to see in logs.                 | Also fine       |
| Version in the media type (`application/json;v=2`) | Fits HTTP content negotiation; clumsy for most clients.            | Rarely worth it |
| Dated versions (Stripe)                            | Many small changes, each with a date; a translation layer to keep. | Challenge 2     |
| Rename in place                                    | Old apps break the day it ships.                                   | The trap        |

## Database design

This station has no database: the versions are a question of the API's shape, not of storage. The point that carries over: a database column can be renamed in one migration; an API field cannot, because its readers are outside your control.

# 3 · Go deeper: Production

Who still calls v1  
Log requests by version and app version; switch v1 off when its traffic is small enough to accept, not on a date alone.

Force updates carefully  
A minimum supported app version (station 089) lets the app tell users to update before v1 ends.

Contract tests  
Keep a copy of what each released app reads, and test v1 against it on every build.

Standards  
RFC 9745 (Deprecation, Proposed Standard, 2025) and RFC 8594 (Sunset, Informational, 2019). Many clients ignore these headers: they help tools and partners, not users.

# 3 · Go deeper: Interview

## Interview takeaways

Which changes are breaking?

Renaming or removing a field, changing its type, changing its meaning (rupees to paise under one name), changing allowed values, and making an optional input required.

Is adding a field safe for every client?

Only for tolerant readers that ignore unknown fields. A strict client fails on it, which is why clients should be tolerant.

How does Spring Framework 7 version APIs?

A version attribute on mappings and an ApiVersionConfigurer that reads the version from a path segment, a header, a query parameter or a media type, with a deprecation handler for headers.

What do Deprecation and Sunset say?

Deprecation: since when the version is deprecated (RFC 9745). Sunset: when it stops working (RFC 8594). A Link with rel="deprecation" points to the guide.

How long do you keep v1?

Until the apps and partners that use it have moved, measured by traffic, with a date announced well ahead.

## Self-check rubric

| Area          | Meets the bar     | Above the bar                                               |
|---------------|-------------------|-------------------------------------------------------------|
| Correctness   | All 7 tests pass. | You ran the flawed version and explained each failure.      |
| Compatibility | v1 unchanged.     | You can name changes of meaning that look compatible.       |
| Deprecation   | Headers on v1.    | Dates in the right format, the standards with their status. |
| Tests         | Contract tests.   | A test that reads answers the way an old app does.          |

# 3 · Go deeper: Review

## The pull request

A teammate makes the versions consistent: money as integer paise in both, and states written in lower case in both, "so we have one rule". No field is renamed or removed. Read the file and list every problem before opening the findings.

#### `review/OrderController.java`

``` code
package com.kartwala.orders;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.List;
import java.util.Locale;

/**
 * Two versions of one resource, side by side. v1 is frozen: its field names, types and values are what old app
 * versions parse, so it only ever gains fields. v2 is where the new shape lives. Both read the same Order.
 */
@RestController
class OrderController {

    /** The shape apps up to 5.x parse. Do not rename, retype or remove anything here. */
    record OrderV1(long id, String customerName, long total, String status, List<ItemV1> items, String trackingUrl) {
    }

    record ItemV1(String sku, int qty, long price) {
    }

    /** The new shape: money in paise, the customer as an object, lower-case states. */
    record OrderV2(long id, CustomerV2 customer, List<ItemV2> items, long totalPaise, String currency, String status, Instant placedAt, String trackingUrl) {
    }

    record CustomerV2(String name, String phone) {
    }

    record ItemV2(String sku, int quantity, long unitPricePaise) {
    }

    private final Orders orders;

    OrderController(Orders orders) {
        this.orders = orders;
    }

    @GetMapping(path = "/{version}/orders/{id}", version = "1")
    OrderV1 v1(@PathVariable long id) {
        Orders.Order o = orders.get(id);
        // Money is integer paise everywhere now, and states are written one way in every version: no more decimals.
        return new OrderV1(o.id(), o.customerName(), o.totalPaise(), status(o),
                o.lines().stream().map(l -> new ItemV1(l.sku(), l.quantity(), l.unitPricePaise())).toList(),
                o.trackingUrl());
    }

    @GetMapping(path = "/{version}/orders/{id}", version = "2")
    OrderV2 v2(@PathVariable long id) {
        Orders.Order o = orders.get(id);
        return new OrderV2(o.id(), new CustomerV2(o.customerName(), o.customerPhone()),
                o.lines().stream().map(l -> new ItemV2(l.sku(), l.quantity(), l.unitPricePaise())).toList(),
                o.totalPaise(), "INR", status(o), o.placedAt(), o.trackingUrl());
    }

    private static String status(Orders.Order o) {
        return o.status().name().toLowerCase(Locale.ROOT);
    }
}
```

## Findings

1v1's total in paise, under the same name

"Money is integer paise everywhere" is right for new APIs, wrong for a frozen one. The name and the JSON type (a number) are unchanged, so nothing fails: app 5.x shows ₹1,29,950 for a ₹1,299.50 order. Item prices too.

**Test evidence:** `v1KeepsTheShapeOldAppsParse` and `theOldAppStillReadsV1Completely` fail.

2v1's states in lower case

"One way to write states": app 5.x compares `status` with `SHIPPED`, so every order now looks like an unknown state.

**Test evidence:** The same two tests fail on `status` as well.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class              | Fixed version | Flawed version |
|-------------------------|---------------|----------------|
| `OrderContractTest`     | 4 / 4         | 3 / 4          |
| `RenameInPlaceTrapTest` | 3 / 3         | 2 / 3          |

No field was renamed, so a check of names alone passes. The breakage is in the values: worse than a crash, because the old app shows a wrong price without any error.
