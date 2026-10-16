# Station 063 · Hotel search with optional filters

Working Systems · 0–2 years · Core · Travel · Types: Database

Spring Boot 4.1.1 · Java 25 · Spring Data JPA Specifications · Criteria API · bound parameters · sort whitelist · PostgreSQL 17 · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Hotels, prices and amenities are demo data, not Ghoomo's. Nothing is booked.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 14 tests.

# 1 · Understand

## The problem in real life

1.  **Twelve filters**

    City, price, stars, amenities, sort and more, each optional. The old code added a piece of SQL text for each one the user set.

2.  **Two kinds of bug**

    A city of `goa' OR '1'='1` returned every hotel in India; a sort parameter could run an `UPDATE`. And "Wi-Fi and breakfast" listed hotels with only Wi-Fi, some of them twice.

3.  **The fix**

    Each filter is a Specification with its value bound as a parameter; amenities are "exists" checks; sort is chosen from a fixed list.

User input is a value, never SQL. Where a value cannot be bound (a column to sort by), choose from a list.

## What are we building?

`GET /hotels` with any mix of city, price range, stars, amenities and sort, returning a page of hotels.

## An everyday analogy

A travel agent with a printed form: tick boxes and fill blanks. Whatever you write in the "city" blank, the agent only ever looks it up as a city. The old system let customers write on the agent's instructions instead.

## How it works in 4 steps

1.  **Check each parameter**: shape, range, known amenity, sort on the list.
2.  **Collect one Specification per filter set**; skip the ones not given.
3.  **Run them together**: one query with bound parameters (Spring Data adds a count query only when it cannot tell the total from the page itself).
4.  **Return the page** with each hotel once.

Check yourself: why can't the sort column be a bound parameter like the city?

A parameter is a value. `ORDER BY ?` would sort by a constant, the same for every row. Column names are part of the SQL text, so the only safe way is to map allowed words (`price`, `-stars`) to columns you chose yourself.

## What this station is not

- **No booking or availability.** That is station 044's calendar.
- **No text search.** Practice 1 adds a name filter; full-text is station 064.
- **No ranking.** Sorts are plain columns.

## Key terms

| Term                | Simple meaning                                                                            | Everyday example                                                            | In this project              |
|---------------------|-------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|------------------------------|
| **Optional filter** | A condition applied only when the user sets it.                                           | "Pool: yes" ticked or not.                                                  | every query parameter        |
| **SQL injection**   | User text that becomes part of the SQL itself and changes what it does.                   | A form where writing "and also give me the safe key" in the name box works. | the old search               |
| **Bound parameter** | A value sent separately from the SQL text, so it can only ever be a value.                | Filling a blank on a printed form; you cannot change the form.              | every `?` in the SQL capture |
| **Specification**   | Spring Data JPA's small, combinable piece of a WHERE clause, built with the Criteria API. | One rule card per filter, clipped together.                                 | `HotelSpecs`                 |
| **Whitelist**       | Only values on a fixed list are accepted.                                                 | A menu: you order what is on it.                                            | `HotelSearch.SORTS`          |
| **EXISTS subquery** | "There is at least one matching row", without joining rows in.                            | "Has a pool?" yes or no, not one line per pool.                             | `hasAmenity`                 |

# 2 · Build: Spec

## Business problem

**Ghoomo** (a fictional travel site) built its hotel search by string concatenation. It was open to SQL injection and gave wrong results for amenities.

## Acceptance criteria

Demo data: six hotels in Goa, three in Jaipur, five amenities.

1.  **Given** no filters, **then** all 9, cheapest first.
2.  **Given** Goa, Wi-Fi and pool, at most Rs 5,000, **then** Calangute Sands and Candolim Palms.
3.  **Given** Wi-Fi and breakfast, **then** only hotels with both, each once.
4.  **Given** a sort not on the list, an unknown amenity, stars outside 1 to 5, or minPrice above maxPrice, **then** `400`.
5.  **Given** SQL in any parameter, **then** `400` or no match, and nothing in the database changes.
6.  **Given** no match, **then** `200` with `total: 0`.

## Requirements

- No user input is ever part of the SQL text.
- Sort fields come from a whitelist; the API's names (`price`) are not the entity's (`pricePerNightPaise`).
- Every sort ends with the id, so equal values keep one order across pages.
- Prices are paise inside the system; the query string takes whole rupees.

## Learning objectives

- Show SQL injection in a concatenated query, and why bound parameters stop it.
- Build optional filters with JPA Specifications.
- Filter on a collection with EXISTS, not a join.
- Whitelist sort fields.

# 2 · Build: API contract

## Endpoint

| Parameter              | Form                                                   | Notes                                          |
|------------------------|--------------------------------------------------------|------------------------------------------------|
| `city`                 | `goa`                                                  | 3 to 30 letters or hyphens; any case           |
| `minPrice`, `maxPrice` | whole rupees per night                                 | 0 to 1,00,000 (demo limit); converted to paise |
| `stars`                | `4,5`                                                  | any of these ratings, 1 to 5                   |
| `amenities`            | `wifi,pool`                                            | up to 5; the hotel must have all of them       |
| `sort`                 | `price` (default), `-price`, `stars`, `-stars`, `name` | anything else is `400`                         |
| `page`, `size`         | 0 to 100; 1 to 50, default 20                          |                                                |

Response: `{total, page, sort, hotels: [{id, name, city, stars, pricePerNightPaise, amenities}]}`.

## Status codes

| Status | When                                                                                                       |
|--------|------------------------------------------------------------------------------------------------------------|
| 200    | A page, possibly empty                                                                                     |
| 400    | Any parameter outside the rules above, an unknown amenity, a sort not on the list, minPrice above maxPrice |

## Captured examples

Captured with curl from the running app on 16 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: Goa, Wi-Fi and pool, up to Rs 5,000

**Why:** three filters; each hotel once, with all its amenities.

Request

``` code
GET /hotels?city=goa&amenities=wifi,pool&maxPrice=5000 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 283

{
  "total": 2,
  "page": 0,
  "sort": "price",
  "hotels": [
    {
      "id": 1,
      "name": "Calangute Sands",
      "city": "goa",
      "stars": 3,
      "pricePerNightPaise": 350000,
      "amenities": [
        "breakfast",
        "pool",
        "wifi"
      ]
    },
    {
      "id": 4,
      "name": "Candolim Palms",
      "city": "goa",
      "stars": 4,
      "pricePerNightPaise": 480000,
      "amenities": [
        "pool",
        "wifi"
      ]
    }
  ]
}
```

### Case 2: Jaipur, 4 or 5 stars, dearest first

**Why:** a list filter and a descending sort.

Request

``` code
GET /hotels?city=jaipur&stars=4,5&sort=-price HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 290

{
  "total": 2,
  "page": 0,
  "sort": "-price",
  "hotels": [
    {
      "id": 9,
      "name": "Rambagh Court",
      "city": "jaipur",
      "stars": 5,
      "pricePerNightPaise": 2100000,
      "amenities": [
        "pool",
        "spa",
        "wifi"
      ]
    },
    {
      "id": 7,
      "name": "Pink City Haveli",
      "city": "jaipur",
      "stars": 4,
      "pricePerNightPaise": 550000,
      "amenities": [
        "breakfast",
        "wifi"
      ]
    }
  ]
}
```

### Case 3: `sort=name; DELETE FROM hotel_amenities`

**Why:** not on the list: `400`, and nothing runs.

Request

``` code
GET /hotels HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Sort by one of [-price, -stars, name, price, stars]",
  "instance": "/hotels",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 4: Wi-Fi and sauna

**Why:** `400` naming the unknown one, instead of silently ignoring it.

Request

``` code
GET /hotels?amenities=wifi,sauna HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Unknown amenities [sauna]",
  "instance": "/hotels",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 5: Shimla

**Why:** no match: `total: 0`.

Request

``` code
GET /hotels?city=shimla HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 47

{
  "total": 0,
  "page": 0,
  "sort": "price",
  "hotels": []
}
```

## The SQL behind case 1

From `docs/capture.sh`: a second copy of the app with Hibernate's SQL log on, one request (`docs/captures/sql.txt`). Every value is a `?`; the city, price and amenity codes are sent separately.

``` code
select a1_0.code,a1_0.name from amenities a1_0 where a1_0.code in (?,?)

select h1_0.id,a1_0.hotel_id,a1_1.code,a1_1.name,h1_0.city,h1_0.name,h1_0.price_per_night_paise,h1_0.stars from (select h1_0.id,h1_0.city,h1_0.name,h1_0.price_per_night_paise,h1_0.stars from hotels h1_0 where h1_0.city=? and h1_0.price_per_night_paise<=? and exists(select h2_0.id from hotels h2_0 join hotel_amenities a2_0 on h2_0.id=a2_0.hotel_id where h2_0.id=h1_0.id and a2_0.amenity_code=?) and exists(select h3_0.id from hotels h3_0 join hotel_amenities a3_0 on h3_0.id=a3_0.hotel_id where h3_0.id=h1_0.id and a3_0.amenity_code=?) order by h1_0.price_per_night_paise,h1_0.id offset ? rows fetch first ? rows only) h1_0(id,city,name,price_per_night_paise,stars) left join hotel_amenities a1_0 on h1_0.id=a1_0.hotel_id left join amenities a1_1 on a1_1.code=a1_0.amenity_code order by h1_0.price_per_night_paise,h1_0.id
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                      | What happens                 | Proved by                                      |
|-----------------------------------------------------------|------------------------------|------------------------------------------------|
| No filters                                                | All 9, cheapest first        | `noFiltersListsEveryHotelCheapestFirst`        |
| `Goa`, `POOL`                                             | Matched in any case          | `goaWithWifiAndPoolUnderRs5000`                |
| Two amenities                                             | Hotels with both, each once  | `everyAmenityMustMatchAndEachHotelAppearsOnce` |
| A list of stars, a price range, a sort                    | Combined                     | `starsPriceRangeAndSort`                       |
| Page 2 of size 2                                          | The next two in sort order   | `pagesFollowTheSortWithoutGapsOrRepeats`       |
| Unknown sort or amenity, bad numbers, a quote in the city | `400`                        | `anythingOutsideTheRulesIs400`                 |
| A sort carrying a `DELETE`                                | `400`, no row removed        | `aSortThatLooksLikeSqlIsRefusedAndRunsNothing` |
| Bad rows written directly                                 | Refused by named constraints | `HotelDatabaseTest`                            |

## The trap

Plausible but wrong

Concatenating optional filters and sort fields into SQL.

The old search is kept in the tests as `OldHotelSearch`, run against the same data:

- **A quote in the city.** `goa' OR '1'='1` closes the string and adds a condition that is always true: 9 hotels instead of 6. The new search binds the same text as a value: no city has that name, 0 hotels.
- **A second statement in the sort.** `h.name; UPDATE hotels SET price_per_night_paise = 50000 --` ran the `UPDATE` on every hotel; the `--` turned the appended `LIMIT 20` into a comment. The caller only saw an error, "Multiple ResultSets were returned by the query." The test runs it in a transaction and rolls it back.
- **Amenities by join.** `JOIN hotel_amenities … IN ('wifi', 'breakfast')` returns a row per matching amenity (Calangute Sands twice) and hotels with either one (Baga Beach Inn, Wi-Fi only). The new search asks "exists" once per amenity.

Passing the user's sort straight to `Sort.by(…)` was tried too: Spring Data refused `name; DELETE …` itself ("must only contain property references"), but as a `500`, and `price` failed as a `500` because the field is `pricePerNightPaise`. The whitelist answers both with a `400` that lists the choices.

While building, each fix was undone once: amenities as "any of" turned 3 tests red; the sort straight to `Sort.by` 2; rupees used as paise 2; no lower-casing, no min/max check and no amenity check 1 each. Removing the entity graph turned nothing red: no test here counts queries (station 061 does).

``` code
package com.ghoomo.hotels;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.catchThrowable;

/** Written first. The old string-built search against the same data, then the Specification search given the same input. */
class ConcatenatedSqlTrapTest extends ApiTest {

    @Autowired
    OldHotelSearch old;
    @Autowired
    HotelSearch search;
    @Autowired
    TransactionTemplate transaction;

    private HotelSearch.Filters city(String city) {
        return new HotelSearch.Filters(city, null, null, List.of(), Set.of());
    }

    @Test
    void aQuoteInTheCityTurnsTheFilterOff() {
        assertThat(old.search("goa", null, List.of(), "h.name")).hasSize(6);
        assertThat(old.search("goa' OR '1'='1", null, List.of(), "h.name")).hasSize(9);   // Jaipur too: the filter became always true
        assertThat(search.search(city("goa' OR '1'='1"), "price", 0, 20).total()).isZero();   // bound as a value: no city has that name
    }

    @Test
    void theSortParameterCanRunAnotherStatement() {
        transaction.executeWithoutResult(tx -> {
            Throwable thrown = catchThrowable(() -> old.search("goa", null, List.of(), "h.name; UPDATE hotels SET price_per_night_paise = 50000 --"));
            assertThat(jdbc.sql("SELECT count(*) FROM hotels WHERE price_per_night_paise = 50000").query(Long.class).single())
                    .as("the UPDATE ran (%s)", thrown).isEqualTo(9);
            tx.setRollbackOnly();   // undo it: this test must not leave every hotel at Rs 500
        });
        assertThat(jdbc.sql("SELECT count(*) FROM hotels WHERE price_per_night_paise = 50000").query(Long.class).single()).isZero();
    }

    @Test
    void joiningAmenitiesGaveDuplicatesAndAnyInsteadOfAll() {
        List<String> oldResult = old.search(null, null, List.of("wifi", "breakfast"), "h.name");
        assertThat(oldResult).containsSubsequence("Calangute Sands", "Calangute Sands");   // once per matching amenity
        assertThat(oldResult).contains("Baga Beach Inn");                                  // wifi only: "any of", not "all of"
        assertThat(search.search(new HotelSearch.Filters(null, null, null, List.of(), Set.of("wifi", "breakfast")), "name", 0, 20).hotels())
                .extracting(HotelSearch.Card::name).containsExactly("Calangute Sands", "Fort Aguada Resort", "Panjim Heritage", "Pink City Haveli");
    }
}
```

``` code
package com.ghoomo.hotels;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.util.List;

/** The search as it was, kept in the tests only: optional filters glued into one SQL string. */
@Component
class OldHotelSearch {

    private final JdbcTemplate jdbc;

    OldHotelSearch(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    List<String> search(String city, Long minPrice, List<String> amenities, String sort) {
        String sql = "SELECT h.name FROM hotels h";
        if (!amenities.isEmpty()) {
            sql += " JOIN hotel_amenities a ON a.hotel_id = h.id";
        }
        sql += " WHERE 1=1";
        if (city != null) {
            sql += " AND h.city = '" + city + "'";
        }
        if (minPrice != null) {
            sql += " AND h.price_per_night_paise >= " + minPrice * 100;
        }
        if (!amenities.isEmpty()) {
            sql += " AND a.amenity_code IN ('" + String.join("', '", amenities) + "')";
        }
        sql += " ORDER BY " + sort + " LIMIT 20";
        return jdbc.queryForList(sql, String.class);
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

Send the attack yourself; `-G --data-urlencode` encodes the spaces and quotes for you:

``` code
curl -G 'http://localhost:8080/hotels' --data-urlencode "city=goa' OR '1'='1"
curl -G 'http://localhost:8080/hotels' --data-urlencode "sort=name; DELETE FROM hotel_amenities"
```

Both are `400`. Then open `OldHotelSearch` in the tests and see why the same text was dangerous there.

## Troubleshooting

| You see                                                     | Cause                                               | Fix                                                      |
|-------------------------------------------------------------|-----------------------------------------------------|----------------------------------------------------------|
| `No property 'price' found for type 'Hotel'`                | An API sort name passed straight to `Sort.by`.      | Map API names to fields in a whitelist.                  |
| `Sort expression '…' must only contain property references` | Spring Data refusing an unsafe sort string.         | Never pass user text to `Sort`; it is a 500, not a 400.  |
| `Multiple ResultSets were returned by the query.`           | A second statement ran inside a concatenated query. | Treat it as an attack in progress; use bound parameters. |
| The same hotel twice                                        | A join on a collection used as a filter.            | `EXISTS` subqueries, as in `hasAmenity`.                 |

## Project layout

``` tree
stations/063-hotel-search-with-optional-filters/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/ghoomo/hotels/
│   ├── HotelController.java   ├── HotelSearch.java   ├── HotelSpecs.java   ├── HotelRepository.java
│   ├── Hotel.java   ├── Amenity.java   ├── AmenityRepository.java   └── HotelsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__hotels.sql, V2__demo_hotels.sql
├── src/test/java/com/ghoomo/hotels/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/ghoomo/hotels/HotelController.java`

Does  
Validates every parameter, lower-cases city and amenities, turns rupees into paise.

Why  
Bad input is a `400` before any query.

Without it  
Typos becoming silent "no filter"s.

#### `src/main/java/com/ghoomo/hotels/HotelSearch.java`

Does  
Checks sort and amenities, collects one Specification per filter, runs the page.

Why  
Only set filters become conditions; the sort comes from `SORTS`.

Without it  
Text built from input, and a sort on any column a caller names.

#### `src/main/java/com/ghoomo/hotels/HotelSpecs.java`

Does  
One Specification per filter.

Why  
Each is tiny, combinable and bound; amenities use `EXISTS`.

Without it  
Joined amenities: duplicates and "any of".

#### `src/main/java/com/ghoomo/hotels/HotelRepository.java`

Does  
`JpaSpecificationExecutor`, with the amenities loaded in the same query.

Why  
`findAll(spec, pageable)` runs the page and a count.

Without it  
A lazy load of amenities per hotel.

#### `src/main/java/com/ghoomo/hotels/Hotel.java`

A hotel, with its amenities.

#### `src/main/java/com/ghoomo/hotels/Amenity.java`

An amenity code.

#### `src/main/java/com/ghoomo/hotels/AmenityRepository.java`

Known amenities, to refuse unknown ones.

#### `src/main/resources/db/migration/V1__hotels.sql`

Does  
Tables, named constraints and two indexes.

Why  
`hotel_amenities_amenity` serves the EXISTS check.

Without it  
Hotels with impossible stars or prices from any writer.

#### `src/main/resources/db/migration/V2__demo_hotels.sql`

Nine hotels and their amenities.

#### `src/main/resources/application.yaml`

open-in-view off, schema validation.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/ghoomo/hotels/HotelsApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                    | Result |
|---------------|-------------------------------------------------------|-------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found (empty)      | `HotelContractTest` (8)       | pass   |
| Every station | Reproduce the failure before the fix                  | `ConcatenatedSqlTrapTest` (3) | pass   |
| Database      | Rollback and constraint tests against a real database | `HotelDatabaseTest` (3)       | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Hibernate 7.4, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.ghoomo.hotels.ConcatenatedSqlTrapTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.ghoomo.hotels.HotelDatabaseTest
[INFO] Tests run: 8, Failures: 0, Errors: 0, Skipped: 0 -- in com.ghoomo.hotels.HotelContractTest
[INFO] Tests run: 14, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/ghoomo/hotels/ConcatenatedSqlTrapTest.java`

Written first: two injections and the amenity join, old against new.

#### `src/test/java/com/ghoomo/hotels/HotelDatabaseTest.java`

Named constraints, a rolled-back hotel, and the cascade.

#### `src/test/java/com/ghoomo/hotels/HotelContractTest.java`

The endpoint through HTTP.

#### `src/test/java/com/ghoomo/hotels/OldHotelSearch.java`

The concatenated search, kept in the tests only.

#### `src/test/java/com/ghoomo/hotels/ApiTest.java`

Shared setup.

#### `src/test/java/com/ghoomo/hotels/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/ghoomo/hotels/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=NameSearchChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 14 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 17 tests pass (14 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Search by name

Add `q=…`: hotels whose name contains the text, any case, with the other filters. `%`, `_` and quotes are just characters.

**Done when:** both tests in `NameSearchChallengeTest` pass.

Hints

- A bound value is safe from injection, but inside `LIKE` it is still a *pattern*: escape `\`, `%` and `_`, and pass the escape character to `cb.like`.
- Keep the old five-value `Filters` constructor working: a record can have a second constructor.

#### `challenge/NameSearchChallengeTest.java`

``` code
package com.ghoomo.hotels;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.empty;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: q=palm finds hotels whose name contains the text, in any case, combined with the other filters.
 * The text is a value, never a pattern: "%" and "_" match only themselves, and a quote is just a quote.
 */
class NameSearchChallengeTest extends ApiTest {

    @Test
    void partOfTheNameInAnyCase() throws Exception {
        mvc.perform(get("/hotels").param("q", "PALM")).andExpect(status().isOk()).andExpect(jsonPath("$.hotels[*].name", contains("Candolim Palms")));
        mvc.perform(get("/hotels").param("q", "a").param("city", "jaipur").param("sort", "name")).andExpect(status().isOk())
                .andExpect(jsonPath("$.hotels[*].name", contains("Amber View", "Pink City Haveli", "Rambagh Court")));
    }

    @Test
    void wildcardsAndQuotesAreJustText() throws Exception {
        mvc.perform(get("/hotels").param("q", "%")).andExpect(status().isOk()).andExpect(jsonPath("$.hotels", empty()));
        mvc.perform(get("/hotels").param("q", "_")).andExpect(status().isOk()).andExpect(jsonPath("$.hotels", empty()));
        mvc.perform(get("/hotels").param("q", "' OR '1'='1")).andExpect(status().isOk()).andExpect(jsonPath("$.hotels", empty()));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Counts per star rating

Add `starsFacet` to every result: hotels per star rating with all filters except stars, for the "4 stars (2)" boxes.

**Done when:** the test in `StarsFacetChallengeTest` passes.

Hints

- Build the list of Specifications without stars, count with it, then add stars and search.
- A Specification is just `toPredicate(root, query, cb)`: use it in your own Criteria query with `groupBy`.

#### `challenge/StarsFacetChallengeTest.java`

``` code
package com.ghoomo.hotels;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: every result carries "starsFacet": how many hotels each star rating would give with all the other
 * filters applied, but not the stars filter itself, so the page can show "4 stars (2)" next to each box.
 */
class StarsFacetChallengeTest extends ApiTest {

    @Test
    void countsIgnoreOnlyTheStarsFilter() throws Exception {
        mvc.perform(get("/hotels").param("city", "goa").param("stars", "4")).andExpect(status().isOk())
                .andExpect(jsonPath("$.total").value(2))
                .andExpect(jsonPath("$.starsFacet.1").value(1)).andExpect(jsonPath("$.starsFacet.2").value(1)).andExpect(jsonPath("$.starsFacet.3").value(1))
                .andExpect(jsonPath("$.starsFacet.4").value(2)).andExpect(jsonPath("$.starsFacet.5").value(1));
        mvc.perform(get("/hotels").param("amenities", "pool")).andExpect(status().isOk())
                .andExpect(jsonPath("$.starsFacet.3").value(1)).andExpect(jsonPath("$.starsFacet.4").value(1)).andExpect(jsonPath("$.starsFacet.5").value(2))
                .andExpect(jsonPath("$.starsFacet.1").doesNotExist());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## When Specifications are not enough

Product wants "near the beach", typo-tolerant names, "popular first" and facets on every filter, on 2 lakh hotels. Which of these can PostgreSQL do well (indexes, full-text, PostGIS), and at what point does a search engine (OpenSearch, Elasticsearch) earn its cost: a second copy of the data, kept in sync, that can be minutes behind?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test with the old search: both injections and the amenity join.
2.  One Specification per filter, each with its value bound.
3.  Amenities as EXISTS; sorts from a whitelist ending in the id.
4.  Validate everything at the controller; check unknown amenities against the table.

## Design alternatives and trade-offs

| Approach                                                | What it costs                                                   | Verdict                |
|---------------------------------------------------------|-----------------------------------------------------------------|------------------------|
| Specifications + bound values + sort whitelist          | A class of small methods.                                       | Chosen                 |
| Concatenated SQL                                        | Injection; quoting bugs; joins that duplicate.                  | The trap               |
| Concatenated SQL with escaping                          | Every value escaped correctly, forever; the sort is still open. | Fragile                |
| One JPQL query with `(:city IS NULL OR h.city = :city)` | Safe; one plan for all combinations, often a poor one.          | Small cases only       |
| Querydsl or jOOQ                                        | A code generator and a dependency; type-safe.                   | Good at scale          |
| A search engine                                         | A second store to keep in sync.                                 | For text and relevance |

## Database design

| Table             | Constraints                                                                                                                                                | Why                                 |
|-------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------|
| `hotels`          | `hotels_city_shape`, `hotels_stars_range`, `hotels_price_range` (demo: Rs 500 to Rs 1 lakh), `hotels_name_per_city`; index `(city, price_per_night_paise)` | The common search: a city by price. |
| `amenities`       | `amenities_code_shape`                                                                                                                                     | Lower-case codes.                   |
| `hotel_amenities` | `hotel_amenities_pk`, two foreign keys; index `(amenity_code, hotel_id)`                                                                                   | The EXISTS check per amenity.       |

``` code
CREATE TABLE amenities (
    code VARCHAR(20) PRIMARY KEY CONSTRAINT amenities_code_shape CHECK (code ~ '^[a-z]{2,20}$'),
    name VARCHAR(50) NOT NULL
);

CREATE TABLE hotels (
    id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                  VARCHAR(100) NOT NULL,
    city                  VARCHAR(30)  NOT NULL CONSTRAINT hotels_city_shape CHECK (city ~ '^[a-z-]{3,30}$'),
    stars                 SMALLINT     NOT NULL CONSTRAINT hotels_stars_range CHECK (stars BETWEEN 1 AND 5),
    price_per_night_paise BIGINT       NOT NULL CONSTRAINT hotels_price_range CHECK (price_per_night_paise BETWEEN 50000 AND 10000000),
    CONSTRAINT hotels_name_per_city UNIQUE (city, name)
);
CREATE INDEX hotels_city_price ON hotels (city, price_per_night_paise);

CREATE TABLE hotel_amenities (
    hotel_id     BIGINT      NOT NULL CONSTRAINT hotel_amenities_hotel_fk REFERENCES hotels (id) ON DELETE CASCADE,
    amenity_code VARCHAR(20) NOT NULL CONSTRAINT hotel_amenities_amenity_fk REFERENCES amenities (code),
    CONSTRAINT hotel_amenities_pk PRIMARY KEY (hotel_id, amenity_code)
);
CREATE INDEX hotel_amenities_amenity ON hotel_amenities (amenity_code, hotel_id);
```

# 3 · Go deeper: Production

Least privilege  
The app's database user needs `SELECT` on these tables, not `UPDATE` or `DELETE`. The injected `UPDATE` in the trap would then have failed.

Multiple statements  
The injection worked because the PostgreSQL driver ran two statements sent as one string through a plain `Statement`. Prepared statements never do.

Filter combinations  
Twelve optional filters are 4,096 combinations. Index the common ones (city plus price); watch slow queries for the rest.

Logs  
Log the parameters of a search, not a SQL string with them inside: one is data, the other is a template for the next attack.

# 3 · Go deeper: Interview

## Interview takeaways

What is SQL injection?

User input that becomes part of the SQL text, so it can change the query: add conditions, run other statements, read other tables.

Why do bound parameters prevent it?

The SQL text is fixed and sent first; values travel separately and are only ever used as values, never parsed as SQL.

How do you sort by a user-chosen column safely?

Map a fixed set of API names to columns you chose; refuse everything else. A column name cannot be a parameter.

What is a JPA Specification?

A function (root, query, criteriaBuilder) → Predicate. Small ones combine with and/or into a query, each value bound.

Why EXISTS instead of a join for "has amenity"?

A join returns a row per matching amenity, duplicating hotels; EXISTS asks one yes/no question per hotel.

## Self-check rubric

| Area        | Meets the bar                            | Above the bar                                   |
|-------------|------------------------------------------|-------------------------------------------------|
| Correctness | All 14 tests pass.                       | You ran both injections against the old search. |
| Security    | No input in SQL text; a sort whitelist.  | Least privilege for the app's database user.    |
| JPA         | One Specification per filter.            | Reusing them for counts (Practice 2).           |
| Results     | Each hotel once; all amenities required. | Why the join duplicated.                        |

# 3 · Go deeper: Review

## No reviewer view for this station

This station has no flawed version to review. Use this checklist on any search endpoint:

- Is any request value concatenated into SQL, JPQL or a `Sort`?
- Is the sort chosen from a fixed list, ending in a unique column?
- Can a filter on a collection return the same row twice?
- Is `LIKE` input escaped?
