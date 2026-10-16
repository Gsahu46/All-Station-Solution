# Station 069 · Scheduled price changes

Working Systems · 0–2 years · Core · E-commerce · Types: Database

Spring Boot 4.1.1 · Java 25 · JdbcClient · effective dating · timestamptz and time zones · PostgreSQL 17 EXCLUDE with tstzrange · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Products and prices are demo data, not Kartwala's. A price is a record; no order or payment is made.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 14 tests.

# 1 · Understand

## The problem in real life

1.  **Diwali pricing**

    A seller sets Rangoli Colours to Rs 149 from midnight on 8 November.

2.  **Noon, not midnight**

    A job checked for due price changes twice a day and overwrote the price when it ran: the sale went live at noon. The times had no time zone either, so a server on UTC read "midnight" as 05:30 in India. And when a flash sale was added inside the Diwali sale, both applied, and checkout took whichever the database returned first.

3.  **The fix**

    Store every price with its window as instants. "The price now" is just the window containing now: nothing has to run at midnight. The database refuses two windows that overlap.

Do not change data at a scheduled time. Store data that is valid from a time, and read it as of now.

## What are we building?

`POST /products/2/prices` schedules a price for a window; `GET /products/2/price?at=…` answers the price at any instant, past or future.

## An everyday analogy

A railway timetable. Nobody repaints the board at midnight to show tomorrow's trains; the timetable lists each train with its days, and you read the line for today. Two trains on one platform at the same time cannot both be printed.

## How it works in 4 steps

1.  **Read the seller's local times** in the shop's zone, India, and turn them into instants.
2.  **Make room**: windows inside the new one go, the one covering its start is cut there, and the old price resumes after it.
3.  **Insert** the new window. The database checks nothing overlaps.
4.  **Answer "price at"** with the one window containing that instant.

Check yourself: the sale ends "at midnight on 11 November". What does a customer pay at exactly 00:00:00 that night?

The normal price. Windows are half-open: the sale includes its start and excludes its end, so at midnight the next window has begun. The test checks both edges.

## What this station is not

- **No checkout.** Freezing the price on an order line is Practice 3.
- **No currencies or taxes.** One price in paise.
- **No several shop zones.** One zone, set in configuration.

## Key terms

| Term                     | Simple meaning                                                     | Everyday example                               | In this project                       |
|--------------------------|--------------------------------------------------------------------|------------------------------------------------|---------------------------------------|
| **Effective dating**     | Each value is stored with the time it is valid from and to.        | A rate card with "valid until" printed on it.  | `valid_from`, `valid_to`              |
| **Half-open window**     | Start included, end excluded: \[from, to).                         | A sale until midnight ends as midnight starts. | `tstzrange(…, '[)')`                  |
| **Price as of**          | The price that was, is or will be valid at a given instant.        | "What did it cost at 9 pm yesterday?"          | `GET …/price?at=…`                    |
| **Instant**              | One moment, the same everywhere on Earth.                          | The moment a rocket launches.                  | `timestamptz`                         |
| **Local time**           | A wall-clock reading in some place.                                | "Midnight" in Delhi is 18:30 in London.        | what sellers type: `2026-11-08T00:00` |
| **Exclusion constraint** | No two rows may conflict, here: same product, overlapping windows. | One price tag per product at any moment.       | `prices_no_overlap`                   |

# 2 · Build: Spec

## Business problem

**Kartwala** (a fictional marketplace): a Diwali price set for midnight went live at noon, and two overlapping prices made checkout pick one at random.

## Acceptance criteria

Demo data: Rangoli Colours is Rs 199, Rs 149 from midnight 8 November to midnight 11 November, then Rs 199 again. Tests fix "now" at 16 October 2026, 11:30 in India.

1.  **Given** 23:59:59 on 7 November in India, **then** Rs 199; at 00:00:00 on 8 November, Rs 149, asked in IST or in UTC.
2.  **Given** 00:00 on 11 November, **then** Rs 199 again.
3.  **Given** a past instant, **then** the price that was valid then.
4.  **Given** a sale inside the base price, **then** three windows: base, sale, base.
5.  **Given** a change in the past, **then** `422`; an end before the start, `400`; an unknown product, `404`.
6.  **Given** an overlapping window written directly, **then** the database refuses it.

## Requirements

- Prices are never overwritten; each has a window.
- Windows are half-open and stored as instants (`timestamptz`).
- Seller times are read in the shop's zone; questions may use any offset.
- At most one price per product at any instant, enforced by the database.
- One schedule change per product at a time.

## Learning objectives

- Model effective-dated data with half-open windows.
- Write "as of" queries.
- Handle local times, zones and instants without surprises.
- Enforce "no overlap" with an exclusion constraint.

# 2 · Build: API contract

## Endpoints

| Method | Path                        | Purpose                                                                                |
|--------|-----------------------------|----------------------------------------------------------------------------------------|
| `POST` | `/products/{id}/prices`     | `{pricePaise, from, to?}` in shop time (no offset); `201` with the product's schedule. |
| `GET`  | `/products/{id}/price?at=…` | The price at an instant (ISO, with offset); now if absent.                             |

## Status codes

| Status    | When                                                                                              |
|-----------|---------------------------------------------------------------------------------------------------|
| 200 / 201 | A price / the new schedule                                                                        |
| 400       | End not after start; price outside Rs 1 to Rs 1 lakh; a malformed time                            |
| 404       | No such product, or no price at that instant                                                      |
| 409       | The schedule changed under the request (an overlap from another writer); not reproduced by a test |
| 422       | A window starting in the past                                                                     |

## Captured examples

Captured with curl from the running app on 16 Oct 2026, on the real clock. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: 23:59:59 on 7 November, India

**Why:** still Rs 199.

Request

``` code
GET /products/2/price HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 145

{
  "productId": 2,
  "at": "2026-11-07T23:59:59+05:30",
  "pricePaise": 19900,
  "validFrom": "2026-01-01T00:00:00+05:30",
  "validTo": "2026-11-08T00:00:00+05:30"
}
```

### Case 2: 00:00 on 8 November, India

**Why:** the sale, exactly at midnight.

Request

``` code
GET /products/2/price HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 145

{
  "productId": 2,
  "at": "2026-11-08T00:00:00+05:30",
  "pricePaise": 14900,
  "validFrom": "2026-11-08T00:00:00+05:30",
  "validTo": "2026-11-11T00:00:00+05:30"
}
```

### Case 3: 18:30 on 7 November, UTC

**Why:** the same instant as case 2, so the same price; answered in shop time.

Request

``` code
GET /products/2/price HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 145

{
  "productId": 2,
  "at": "2026-11-08T00:00:00+05:30",
  "pricePaise": 14900,
  "validFrom": "2026-11-08T00:00:00+05:30",
  "validTo": "2026-11-11T00:00:00+05:30"
}
```

### Case 4: a sale for the Diya Lamp Set

**Why:** the open-ended base price is cut in two around the sale.

Request

``` code
POST /products/1/prices HTTP/1.1
Content-Type: application/json

{
  "pricePaise": 39900,
  "from": "2026-11-08T00:00",
  "to": "2026-11-11T00:00"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 271

{
  "productId": 1,
  "windows": [
    {
      "pricePaise": 49900,
      "from": "2026-01-01T00:00:00+05:30",
      "to": "2026-11-08T00:00:00+05:30"
    },
    {
      "pricePaise": 39900,
      "from": "2026-11-08T00:00:00+05:30",
      "to": "2026-11-11T00:00:00+05:30"
    },
    {
      "pricePaise": 49900,
      "from": "2026-11-11T00:00:00+05:30",
      "to": null
    }
  ]
}
```

### Case 5: a new price from 1 March

**Why:** `422`: history does not change.

Request

``` code
POST /products/3/prices HTTP/1.1
Content-Type: application/json

{
  "pricePaise": 59900,
  "from": "2026-03-01T00:00"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "Prices in the past are history and cannot change",
  "instance": "/products/3/prices",
  "status": 422,
  "title": "Unprocessable Content"
}
```

## Midnight, with and without a zone

Asked in `psql` with the session in UTC, as on many servers (`docs/captures/midnight.txt`).

``` code
    without_zone     | with_zone_shown_in_utc 
---------------------+------------------------
 2026-11-08 00:00:00 | 2026-11-07 18:30:00+00
(1 row)
```

The value without a zone stays "midnight" and is compared with whatever the server's clock says; the instant is 18:30 UTC on the 7th.

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                            | What happens                               | Proved by                                                     |
|---------------------------------------------------------------------------------|--------------------------------------------|---------------------------------------------------------------|
| Now                                                                             | The current window, in shop time           | `thePriceNow`                                                 |
| One second before, at, and at the end of the sale                               | Half-open: in at the start, out at the end | `theSaleStartsAtMidnightInIndiaWhateverOffsetTheQuestionUses` |
| A past instant                                                                  | The price then                             | `pastPricesAreKept`                                           |
| A sale inside an open-ended price                                               | Base, sale, base                           | `aSaleCutsTheBasePriceInTwo`                                  |
| A flash sale inside a sale                                                      | Five windows                               | `aFlashSaleInsideTheSale`                                     |
| A window covering a whole sale                                                  | The sale goes                              | `aWindowCoveringTheWholeSaleReplacesIt`                       |
| A new price from then on                                                        | Later windows replaced                     | `aNewPriceFromThenOnReplacesEverythingAfter`                  |
| Past, empty window, bad price, unknown product, no price yet, bad time          | `422`, `400`, `404`                        | `thePastCannotChangeAndOtherMistakes`                         |
| Overlap, orphan, bad price, backwards window written directly; windows touching | Refused; allowed                           | `PriceDatabaseTest`                                           |

## The trap

Plausible but wrong

Overwriting the price at a scheduled time instead of storing dated prices.

The old design kept one current price and a table of planned changes with `timestamp` (no zone) and no rule against overlaps. A job applied them when it ran, and lost each old price as it did. The test recreates the planned-changes table and reads it as the UTC server did:

- **Midnight in the wrong place.** At 00:30 in India on 8 November, the old query finds no sale; at 05:30 in India (midnight UTC) it does. The new API answers Rs 149 at 00:30.
- **Two prices at once.** A flash sale added inside the Diwali sale: at noon on the 9th, both rows match. Checkout's `LIMIT 1` took one; which, depended on the plan.
- **The real table refuses the overlap**: `prices_no_overlap`.

While building, each fix was undone once: reading seller times as UTC turned 3 tests red; dropping the exclusion constraint 3; not resuming the old price after a window 2; a closed end (`valid_to >= at`) 1; not shifting a window that starts inside 1; no past check 1.

``` code
package com.kartwala.prices;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.catchThrowable;

/**
 * Written first. The old schedule table: local times without a time zone, no rule against overlaps, read by a server
 * whose clock runs in UTC.
 */
class OverwrittenPriceTrapTest extends ApiTest {

    /** The old checkout query: the price change in force "now", as the UTC server's local time saw it. */
    static final String OLD = """
            SELECT price_paise FROM old_price_changes WHERE product_id = 2
            AND starts_at <= (CAST(:at AS timestamptz) AT TIME ZONE 'UTC') AND ends_at > (CAST(:at AS timestamptz) AT TIME ZONE 'UTC')""";

    @BeforeEach
    void oldTable() {
        jdbc.sql("CREATE TABLE old_price_changes (product_id BIGINT, price_paise INTEGER, starts_at TIMESTAMP, ends_at TIMESTAMP)").update();
        // The seller typed midnight, meaning midnight in India.
        jdbc.sql("INSERT INTO old_price_changes VALUES (2, 14900, '2026-11-08 00:00', '2026-11-11 00:00')").update();
    }

    @AfterEach
    void dropOldTable() {
        jdbc.sql("DROP TABLE old_price_changes").update();
    }

    private List<Integer> old(String at) {
        return jdbc.sql(OLD).param("at", at).query(Integer.class).list();
    }

    @Test
    void localTimesWentLiveAtTheServersMidnightNotTheShops() throws Exception {
        assertThat(old("2026-11-08T00:30:00+05:30")).isEmpty();                 // half an hour into Diwali in India: no sale yet
        assertThat(old("2026-11-08T05:30:00+05:30")).containsExactly(14900);    // midnight in UTC
        priceAt(2, "2026-11-08T00:30:00+05:30").andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath("$.pricePaise").value(14900));
    }

    @Test
    void twoOverlappingChangesBothApplyAndCheckoutPicksOne() {
        jdbc.sql("INSERT INTO old_price_changes VALUES (2, 12900, '2026-11-09 00:00', '2026-11-10 00:00')").update();   // a flash sale, added later
        assertThat(old("2026-11-09T12:00:00+05:30")).containsExactlyInAnyOrder(14900, 12900);   // which one checkout took depended on the plan
    }

    @Test
    void theRealTableRefusesTheOverlap() {
        Throwable refused = catchThrowable(() -> jdbc.sql("INSERT INTO prices (product_id, price_paise, valid_from, valid_to) VALUES (2, 12900, '2026-11-09 00:00+05:30', '2026-11-10 00:00+05:30')").update());
        assertThat(refused).hasMessageContaining("prices_no_overlap");
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
./mvnw test                 # all 14 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Ask for the price at instants around the sale; `--data-urlencode` keeps the `+` of the offset intact:

``` code
curl -G http://localhost:8080/products/2/price --data-urlencode 'at=2026-11-08T00:00:00+05:30'
curl -G http://localhost:8080/products/2/price --data-urlencode 'at=2026-11-11T00:00:00+05:30'
```

## Troubleshooting

| You see                                                                   | Cause                                                     | Fix                                                               |
|---------------------------------------------------------------------------|-----------------------------------------------------------|-------------------------------------------------------------------|
| `400` for `at=2026-11-08T00:00:00+05:30` in a browser                     | An unencoded `+` in a URL is a space.                     | Encode it as `%2B`, or use `Z` times.                             |
| `conflicting key value violates exclusion constraint "prices_no_overlap"` | Two windows for one product overlap.                      | Fit the window into the schedule, as `PriceSchedule.set` does.    |
| `data type bigint has no default operator class for access method "gist"` | `btree_gist` is not installed.                            | The migration creates it; a managed database may need it allowed. |
| Prices change at 05:30 instead of midnight                                | Times stored or compared without a zone, on a UTC server. | `timestamptz`, and read local times in the shop's zone.           |

## Project layout

``` tree
stations/069-scheduled-price-changes/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/prices/
│   ├── PriceController.java   ├── PriceSchedule.java   └── PricesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__prices.sql, V2__demo_prices.sql
├── src/test/java/com/kartwala/prices/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/kartwala/prices/PriceController.java`

Does  
Takes local times for schedules and instants for questions.

Why  
Sellers think in shop time; clients asking "price at" may be anywhere, so they send an offset.

Without it  
A bare "00:00" read in the server's zone.

#### `src/main/java/com/kartwala/prices/PriceSchedule.java`

Does  
Answers "price at" and fits a new window into the schedule.

Why  
One transaction, the product row locked, neighbours trimmed or continued, then the insert.

Without it  
Overlaps refused by the database instead of fitted, or prices overwritten.

- Instants are bound as `OffsetDateTime` in UTC: the database session's zone never matters.
- The shop zone comes from `shop.zone`, and `Clock` is a bean so tests fix "now".

#### `src/main/resources/db/migration/V1__prices.sql`

Does  
Products, dated prices, and the constraints.

Why  
`prices_no_overlap` makes "one price at any instant" true for every writer.

Without it  
Two matching rows, and a checkout that picks one.

#### `src/main/resources/db/migration/V2__demo_prices.sql`

Three products; the Diwali sale on Rangoli Colours.

#### `src/main/resources/application.yaml`

The shop's zone and whole paise.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/kartwala/prices/PricesApplication.java`

Entry point and the clock.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                     | Result |
|---------------|-------------------------------------------------------|--------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `PriceContractTest` (8)        | pass   |
| Every station | Reproduce the failure before the fix                  | `OverwrittenPriceTrapTest` (3) | pass   |
| Database      | Rollback and constraint tests against a real database | `PriceDatabaseTest` (3)        | pass   |

Not tested: two schedule changes for one product at the same moment. The product row lock makes them take turns, and the exclusion constraint is the backstop (answered `409`); no parallel test proves it here.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.prices.PriceDatabaseTest
[INFO] Tests run: 8, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.prices.PriceContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.prices.OverwrittenPriceTrapTest
[INFO] Tests run: 14, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/kartwala/prices/OverwrittenPriceTrapTest.java`

Written first: the old table's midnight, its overlaps, and the refusal.

#### `src/test/java/com/kartwala/prices/PriceDatabaseTest.java`

Named constraints, touching windows, and a rolled-back batch.

#### `src/test/java/com/kartwala/prices/PriceContractTest.java`

Both endpoints through HTTP, with "now" fixed.

#### `src/test/java/com/kartwala/prices/ApiTest.java`

Shared setup: the fixed clock and the demo schedule before each test.

#### `src/test/java/com/kartwala/prices/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/kartwala/prices/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=ScheduleChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 14 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 17 tests pass (14 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 15 minutes

## Show the schedule

Add `GET /products/{id}/prices`: every window, oldest first, in shop time.

**Done when:** the test in `ScheduleChallengeTest` passes.

Hints

- `PriceSchedule.schedule` already builds it.
- Check the product exists first, for the `404`.

#### `challenge/ScheduleChallengeTest.java`

``` code
package com.kartwala.prices;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: GET /products/{id}/prices returns the whole schedule, oldest first, in shop time. Unknown product: 404. */
class ScheduleChallengeTest extends ApiTest {

    @Test
    void theWholeSchedule() throws Exception {
        mvc.perform(get("/products/2/prices")).andExpect(status().isOk())
                .andExpect(jsonPath("$.windows[*].pricePaise", contains(19900, 14900, 19900)))
                .andExpect(jsonPath("$.windows[1].from").value("2026-11-08T00:00:00+05:30"));
        mvc.perform(get("/products/99/prices")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Cancel a sale

Add `DELETE /products/{id}/prices?from=…`: remove the future window starting then; the price before it carries on, and equal neighbours become one window.

**Done when:** both tests in `CancelSaleChallengeTest` pass.

Hints

- Find the windows before (ending at its start) and after (starting at its end).
- If they have the same price, delete the one after and stretch the one before over both; otherwise stretch the one before over the gap.
- A window that has started is history: `422`.

#### `challenge/CancelSaleChallengeTest.java`

``` code
package com.kartwala.prices;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: DELETE /products/{id}/prices?from=2026-11-08T00:00 cancels the future window starting then (shop
 * time). The price before it simply carries on: neighbours with the same price become one window. A window that has
 * already started is history: 422. No window starts then: 404.
 */
class CancelSaleChallengeTest extends ApiTest {

    @Test
    void cancellingTheSaleLeavesOneUnbrokenPrice() throws Exception {
        mvc.perform(delete("/products/2/prices").param("from", "2026-11-08T00:00")).andExpect(status().isOk())
                .andExpect(jsonPath("$.windows[*].pricePaise", contains(19900)))
                .andExpect(jsonPath("$.windows[0].from").value("2026-01-01T00:00:00+05:30")).andExpect(jsonPath("$.windows[0].to").doesNotExist());
    }

    @Test
    void historyCannotBeCancelledAndNothingIsNotFound() throws Exception {
        mvc.perform(delete("/products/2/prices").param("from", "2026-01-01T00:00")).andExpect(status().isUnprocessableContent());
        mvc.perform(delete("/products/2/prices").param("from", "2026-11-09T00:00")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## The price on the order, and shops in other zones

A customer adds a lamp to the cart at 23:58 on 7 November and pays at 00:02. Which price applies, and where is it stored so a refund next month pays back the right amount? Then: Kartwala opens in Dubai (+04:00). Is the Diwali sale "midnight in India" everywhere, or midnight in each country? What changes in `shop.zone`, in the API, and in the data?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the zone-less, overlapping old table.
2.  Store dated prices as half-open `timestamptz` windows, with an exclusion constraint.
3.  Write the "as of" query, and convert local times at the edge, in the shop's zone.
4.  Fit new windows into the schedule inside one transaction, with the product row locked.

## Design alternatives and trade-offs

| Approach                                                      | What it costs                                                            | Verdict                     |
|---------------------------------------------------------------|--------------------------------------------------------------------------|-----------------------------|
| Dated windows + exclusion constraint + "as of" reads          | Writes must fit windows; reads are one indexed query.                    | Chosen                      |
| Overwrite the price from a scheduled job                      | Late changes; history lost; a missed run is a wrong price.               | The trap                    |
| Dated rows with only a start ("from"), the latest start wins  | No overlaps possible; ending a sale means inserting the old price again. | Simpler, less expressive    |
| A base price plus a separate promotions table with priorities | Clear for marketing; checkout must resolve priorities.                   | For many overlapping offers |
| Times as `timestamp` plus a zone column                       | Correct if every query applies the zone.                                 | Easy to get wrong           |

## Database design

| Object                                    | What                                                                                   | Why                                                                                     |
|-------------------------------------------|----------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| `prices_no_overlap`                       | EXCLUDE USING gist (product_id WITH =, tstzrange(valid_from, valid_to, '\[)') WITH &&) | One price per product at any instant; its GiST index can also serve the product lookup. |
| `prices_window_order`                     | CHECK valid_to IS NULL OR valid_to \> valid_from                                       | No empty or backwards windows.                                                          |
| `prices_price_range`, `prices_product_fk` | CHECK and foreign key                                                                  | No impossible prices.                                                                   |
| `valid_from`, `valid_to`                  | `timestamptz`                                                                          | Instants, not wall-clock readings.                                                      |

**Transaction boundary:** one schedule change, from locking the product row to the last insert.

``` code
CREATE EXTENSION IF NOT EXISTS btree_gist;   -- lets a GiST exclusion constraint compare product_id with =

CREATE TABLE products (
    id   BIGINT       PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

-- Every price a product has had or will have, each valid for a half-open stretch of time [valid_from, valid_to).
-- valid_to NULL means "until further notice". Nothing is overwritten, so "what did it cost at 21:04 yesterday" has an answer.
CREATE TABLE prices (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id  BIGINT      NOT NULL CONSTRAINT prices_product_fk REFERENCES products (id),
    price_paise INTEGER     NOT NULL CONSTRAINT prices_price_range CHECK (price_paise BETWEEN 100 AND 10000000),
    valid_from  TIMESTAMPTZ NOT NULL,
    valid_to    TIMESTAMPTZ,
    CONSTRAINT prices_window_order CHECK (valid_to IS NULL OR valid_to > valid_from),
    -- At any instant, at most one price per product: checkout can never find two.
    CONSTRAINT prices_no_overlap EXCLUDE USING gist (product_id WITH =, tstzrange(valid_from, valid_to, '[)') WITH &&)
);
```

# 3 · Go deeper: Production

Caches  
A cached "current price" must expire at the next window boundary, not after a fixed time, or the sale starts late again.

Orders  
An order stores the price it was sold at; never recompute it from the schedule later.

Time-zone rules change  
Store instants; convert with the JDK's zone rules at the edge, and keep the JDK updated.

Audit  
Who scheduled each window and when is worth a column; disputes ask.

# 3 · Go deeper: Interview

## Interview takeaways

What is effective dating?

Storing each value with the period it is valid for, so the value at any instant (past, present or future) can be read without anything changing at that instant.

Why half-open windows?

Consecutive windows can share a boundary without overlapping, and each instant belongs to exactly one.

timestamp or timestamptz?

timestamptz for instants: it stores a moment; timestamp is a wall-clock reading with no zone, interpreted by whoever reads it.

How do you stop two prices applying at once?

An exclusion constraint on product and overlapping time range, so the database refuses the second, from any writer.

Where should time zones be handled?

At the edges: read the user's local time in their zone, store instants, and convert back for display.

## Self-check rubric

| Area        | Meets the bar                       | Above the bar                         |
|-------------|-------------------------------------|---------------------------------------|
| Correctness | All 14 tests pass.                  | You traced each window split by hand. |
| Time        | Instants stored, zones at the edge. | Why 05:30 in India is midnight UTC.   |
| Integrity   | The exclusion constraint.           | Why the row lock is still needed.     |
| Design      | No overwrites.                      | The price frozen on the order.        |

# 3 · Go deeper: Review

## No reviewer view for this station

This station has no flawed version to review. Use this checklist on any scheduled change:

- Does anything overwrite data at a scheduled time?
- Is every time column an instant (`timestamptz`), and in which zone are inputs read?
- Can two values be valid at once, and who would stop it?
- Are window ends included or excluded, and is that tested?
