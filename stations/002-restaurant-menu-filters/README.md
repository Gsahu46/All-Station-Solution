# Station 002 · Restaurant menu filters

Foundations · 0–1 years · Core · Food delivery · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · Bean Validation · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Two restaurants and their dishes are a fixed list inside the app. Nothing reads a real restaurant database.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 16 tests.

# 1 · Understand

## The problem in real life

1.  **Meera is hungry and has ₹200**

    She opens Annapoorna Mess on Tiffino and wants a veg dish she can afford.

2.  **The menu is a wall of 140 dishes**

    Every dish, unsorted, veg and non-veg mixed. She scrolls, gives up, and orders elsewhere.

3.  **The fix**

    The app sends her choices to the server, *veg, at most ₹200, cheapest first, 5 dishes*, and gets exactly those back.

The order of the steps changes the answer. "The cheapest 5" means sort everything, then take 5. Take 5 first and you get 5 random dishes that only *look* sorted.

## What are we building?

One endpoint, `GET /restaurants/{id}/menu`, with four optional query parameters: `veg`, `maxPrice`, `sort` and `limit`. Bad values get a clear `400`, an unknown restaurant gets `404`.

## An everyday analogy

At a sweet shop you ask: "Your five cheapest sweets, please." The shopkeeper who does it right looks at every tray, then picks the five lowest prices. The careless one grabs the first five boxes on the counter and arranges them by price. Both hand you five sweets in price order; only one answered your question.

## How it works in 4 steps

1.  **Read the choices** from the URL, with defaults for any left out.
2.  **Check them**: limit from 1 to 50, a known sort, a positive price. Anything else: `400`.
3.  **Filter** the restaurant's dishes (veg, price), then **sort** them, then **limit**.
4.  **Answer** with the dishes. No match is an empty list, not an error.

Check yourself: the kitchen added a ₹60 Idli at the end of the menu. Would "limit, then sort" ever show it as one of the cheapest 5?

No. "Limit, then sort" only ever looks at the first 5 dishes typed in, so a cheap dish added at the end can never appear. "Sort, then limit" looks at all dishes first, so the ₹60 Idli comes first.

## What this station is not

- **Not a real restaurant database.** Two restaurants are fixed in the code; databases come in later stations.
- **No paging.** `limit` caps the list; "next page" is a later station.
- **No search by name.** That is Practice challenge 1.

## Key terms

| Term                | Simple meaning                                                               | Everyday example                               | In this project                         |
|---------------------|------------------------------------------------------------------------------|------------------------------------------------|-----------------------------------------|
| **Query parameter** | An optional setting after `?` in a URL, as `name=value` pairs joined by `&`. | Ticking boxes on a paper order form.           | `?veg=true&maxPrice=200`                |
| **Default value**   | The value used when the client leaves a parameter out.                       | "Regular" size when you do not say which.      | `limit` is 20, `sort` is `recommended`. |
| **Filter**          | Keep only the items that pass a test.                                        | Picking only the green chillies from a basket. | Veg only; at most ₹200.                 |
| **Sort**            | Put items in an order.                                                       | Lining up by height.                           | Cheapest first.                         |
| **Limit**           | Keep only the first N items.                                                 | "Show me five."                                | `limit=5`                               |
| **Stream**          | Java's way to run a list through steps: filter, sort, limit, collect.        | A conveyor belt with stations along it.        | `MenuQuery.apply`                       |
| **Comparator**      | A rule that says which of two items comes first.                             | "Shorter person stands in front."              | By price, then by name.                 |
| **Validation**      | Checking a value is allowed before using it.                                 | A form that will not take 0 as your age.       | `limit` must be 1 to 50.                |

# 2 · Build: Spec

## Business problem

**Tiffino** (a fictional food-delivery app) shows each restaurant's full menu in the order the kitchen typed it in. Customers with a budget or a diet scroll through up to 140 dishes. The product team added "Veg only", "Under ₹200" and "Cheapest first" buttons to the app, but the API ignores them and returns everything.

A first attempt returned the "cheapest 5" by taking the first 5 dishes and sorting those. In a demo with a 6-dish menu nobody noticed. On a real menu it showed a ₹360 dish as "cheap" and hid a ₹60 one.

## Acceptance criteria

1.  **Given** `veg=true&maxPrice=200&sort=price_asc&limit=5`, **then** the 5 cheapest veg dishes priced at most ₹200 are returned, cheapest first.
2.  **Given** no parameters, **then** up to 20 dishes are returned, most ordered last week first.
3.  **Given** two dishes at the same price, **then** they are ordered by name, so the same request always gives the same list.
4.  **Given** filters that match nothing, **then** `200` with an empty `dishes` list.
5.  **Given** `limit=0`, `limit=500`, `maxPrice=-5`, `sort=cheapest` or `veg=maybe`, **then** `400` with a problem body naming each bad parameter.
6.  **Given** an unknown restaurant, **then** `404`.

## Requirements

- `veg`: optional. `true` veg only, `false` non-veg only, left out means both.
- `maxPrice`: optional, whole rupees, 1 to 1,00,000, inclusive. Dish prices are stored in paise.
- `sort`: `recommended` (default, most ordered first), `price_asc` or `price_desc`. Ties by name.
- `limit`: 1 to 50, default 20.
- Steps run in this order: filter, sort, limit.
- Errors are RFC 9457 `application/problem+json`, with an `errors` map for bad parameters.

## Learning objectives

- Read optional query parameters with `@RequestParam`, `required = false` and `defaultValue`.
- Validate them with `@Min`, `@Max` and `@Pattern`.
- Write a stream pipeline: `filter`, `sorted`, `limit`, `toList`.
- Build a `Comparator` with `reversed()` and `thenComparing()`.
- Explain why the order of `sorted` and `limit` matters.

# 2 · Build: API contract

## Endpoint

| Method | Path                     | Purpose                                              |
|--------|--------------------------|------------------------------------------------------|
| `GET`  | `/restaurants/{id}/menu` | A restaurant's dishes, filtered, sorted and limited. |

## Query parameters

| Parameter  | Type            | Default       | Rule                                                |
|------------|-----------------|---------------|-----------------------------------------------------|
| `veg`      | boolean         | both          | `true` or `false`.                                  |
| `maxPrice` | integer, rupees | no limit      | 1 to 100000. Inclusive: `200` keeps a ₹200.00 dish. |
| `sort`     | string          | `recommended` | `recommended`, `price_asc` or `price_desc`.         |
| `limit`    | integer         | 20            | 1 to 50.                                            |

## Status codes

| Status | When                                                    | Body                                                                  |
|--------|---------------------------------------------------------|-----------------------------------------------------------------------|
| 200    | The restaurant exists (even if nothing matches)         | `restaurantId`, `restaurantName`, `dishes`                            |
| 400    | A parameter is out of range, unknown, or the wrong type | Problem with `errors` (parameter → message) for range and sort errors |
| 404    | No restaurant has this id                               | Problem: *Restaurant not found*                                       |

## Captured examples

Captured with curl from the running app on 13 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: Meera's question

**Why:** every veg dish at most ₹200 is found first, then sorted by price, then cut to 5. ₹80 Curd Rice comes before ₹80 Lemon Rice because ties are ordered by name.

Request

``` code
GET /restaurants/101/menu?veg=true&maxPrice=200&sort=price_asc&limit=5 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 474

{
  "restaurantId": 101,
  "restaurantName": "Annapoorna Mess",
  "dishes": [
    {
      "id": 7,
      "name": "Idli Sambar",
      "veg": true,
      "pricePaise": 6000,
      "ordersLastWeek": 640
    },
    {
      "id": 12,
      "name": "Gulab Jamun (2 pcs)",
      "veg": true,
      "pricePaise": 7000,
      "ordersLastWeek": 330
    },
    {
      "id": 10,
      "name": "Curd Rice",
      "veg": true,
      "pricePaise": 8000,
      "ordersLastWeek": 260
    },
    {
      "id": 14,
      "name": "Lemon Rice",
      "veg": true,
      "pricePaise": 8000,
      "ordersLastWeek": 120
    },
    {
      "id": 3,
      "name": "Masala Dosa",
      "veg": true,
      "pricePaise": 9000,
      "ordersLastWeek": 760
    }
  ]
}
```

### Case 2: no filters, 3 dishes

**Why:** the default sort is `recommended`: most ordered last week first.

Request

``` code
GET /restaurants/101/menu?limit=3 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 312

{
  "restaurantId": 101,
  "restaurantName": "Annapoorna Mess",
  "dishes": [
    {
      "id": 2,
      "name": "Chicken Biryani",
      "veg": false,
      "pricePaise": 28000,
      "ordersLastWeek": 980
    },
    {
      "id": 3,
      "name": "Masala Dosa",
      "veg": true,
      "pricePaise": 9000,
      "ordersLastWeek": 760
    },
    {
      "id": 7,
      "name": "Idli Sambar",
      "veg": true,
      "pricePaise": 6000,
      "ordersLastWeek": 640
    }
  ]
}
```

### Case 3: no veg dishes at a grill

**Why:** the restaurant exists, so `200`; nothing matched, so the list is empty. Not a `404`.

Request

``` code
GET /restaurants/102/menu?veg=true HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 65

{
  "restaurantId": 102,
  "restaurantName": "Coastal Grill",
  "dishes": []
}
```

### Case 4: impossible filters

**Why:** `limit=0` and an unknown sort are both rejected in one answer, each with its own message, before any dish is read.

Request

``` code
GET /restaurants/101/menu?limit=0&sort=cheapest HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Some menu filters are invalid.",
  "instance": "/restaurants/101/menu",
  "status": 400,
  "title": "Bad Request",
  "errors": {
    "limit": "must be greater than or equal to 1",
    "sort": "must be recommended, price_asc or price_desc"
  }
}
```

### Case 5: unknown restaurant

**Why:** no restaurant 999, so `404` with a problem body.

Request

``` code
GET /restaurants/999/menu HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No restaurant has the id 999.",
  "instance": "/restaurants/999/menu",
  "status": 404,
  "title": "Restaurant not found"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                | What the API does                            | Proved by                                                                              |
|-----------------------------------------------------|----------------------------------------------|----------------------------------------------------------------------------------------|
| "Cheapest 5"                                        | Sort all, then take 5                        | `sortBeforeLimitReturnsTheFiveCheapestDishes`                                          |
| Veg, at most ₹200, cheapest 5                       | Only veg, only ≤ 20000 paise, in price order | `vegUnder200CheapestFirstIsTheCustomersQuestion`                                       |
| A dish priced exactly at `maxPrice`                 | Included                                     | `maxPriceIsInclusiveAndInRupees`, `maxPriceComparesRupeesWithPaiseExactly`             |
| `veg=false`                                         | Non-veg only (not "ignore the filter")       | `vegFalseMeansNonVegOnly`                                                              |
| Two dishes at the same price                        | Ordered by name, every time                  | `equalPricesAreOrderedByNameSoTheAnswerNeverChanges`, `recommendedTiesAreBrokenByName` |
| Nothing matches                                     | `200`, empty list                            | `noMatchingDishIsAnEmptyListNotAnError`                                                |
| `limit=0`, `limit=500`, `maxPrice=-5`, unknown sort | `400`, one message per parameter             | `outOfRangeFiltersAre400WithOneMessagePerParameter`, `limitAbove50Is400`               |
| `veg=maybe`, `limit=five`, restaurant `abc`         | `400` problem                                | `valuesOfTheWrongTypeAre400`                                                           |
| Unknown restaurant                                  | `404` problem                                | `unknownRestaurantIs404Problem`                                                        |
| The catalogue list itself                           | Never re-ordered by a request                | `theInputListIsNotChanged`                                                             |

## The trap

Plausible but wrong

Applying `limit` before `sort`, so "cheapest 5" returns 5 arbitrary dishes, neatly sorted.

The result looks right: five dishes in price order. A quick manual test with a short menu passes. The first test in this station proves the bug with a "before" controller: its "cheapest 5" includes a ₹360 dish and misses the ₹60 one. The second test runs the real API and gets the true five. Moving `limit` above `sorted` in `MenuQuery` turns 4 tests red; that was checked while building the station.

``` code
package com.tiffino.menu;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.util.Comparator;
import java.util.List;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * The customer taps "cheapest first" and the app asks for 5 dishes.
 */
@Import(LimitBeforeSortTrapTest.NaiveMenuController.class)
class LimitBeforeSortTrapTest extends ApiTest {

    /** The "before" code: takes the first 5 dishes as typed in by the kitchen, then sorts those 5. Kept only in tests. */
    @RestController
    static class NaiveMenuController {
        private final MenuCatalog catalog;

        NaiveMenuController(MenuCatalog catalog) {
            this.catalog = catalog;
        }

        @GetMapping("/naive/restaurants/{id}/cheapest5")
        List<Dish> cheapest5(@PathVariable long id) {
            return catalog.find(id).orElseThrow().dishes().stream()
                    .limit(5)
                    .sorted(Comparator.comparingInt(Dish::pricePaise))
                    .toList();
        }
    }

    @Test
    void limitBeforeSortReturnsFiveArbitraryDishesNeatlySorted() throws Exception {
        mvc.perform(get("/naive/restaurants/101/cheapest5"))
                .andExpect(status().isOk())
                // the bug: sorted, so it looks right, but these are just the first 5 rows; Rs 360 Mutton Rogan Josh is "cheap"
                .andExpect(jsonPath("$[*].name", contains(
                        "Masala Dosa", "Veg Hakka Noodles", "Paneer Butter Masala", "Chicken Biryani", "Mutton Rogan Josh")));
    }

    @Test
    void sortBeforeLimitReturnsTheFiveCheapestDishes() throws Exception {
        mvc.perform(get("/restaurants/101/menu").param("sort", "price_asc").param("limit", "5"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.dishes[*].name", contains(
                        "Idli Sambar", "Gulab Jamun (2 pcs)", "Curd Rice", "Lemon Rice", "Masala Dosa")));
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
./mvnw test                 # all 16 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Quote the URL: `&` means something else to the shell.

``` code
# Veg, at most Rs 200, cheapest first, 5 dishes: expect Idli Sambar first
curl -i "http://localhost:8080/restaurants/101/menu?veg=true&maxPrice=200&sort=price_asc&limit=5"

# The same without sort: most ordered first
curl -i "http://localhost:8080/restaurants/101/menu?veg=true&maxPrice=200&limit=5"

# A bad limit: expect 400 with "errors": {"limit": ...}
curl -i "http://localhost:8080/restaurants/101/menu?limit=0"
```

## Troubleshooting

| You see                             | Cause                         | Fix                                                      |
|-------------------------------------|-------------------------------|----------------------------------------------------------|
| Only the first filter seems to work | The shell cut the URL at `&`. | Put the whole URL in double quotes.                      |
| `release version 25 not supported`  | Maven is using an older JDK.  | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`. |
| `Port 8080 was already in use`      | Another app uses the port.    | Stop it, or add `--server.port=8081` as an app argument. |

## Project layout

``` tree
stations/002-restaurant-menu-filters/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tiffino/menu/
│   ├── MenuController.java   ├── MenuQuery.java     ├── MenuCatalog.java
│   ├── Dish.java             ├── Menu.java          ├── Restaurant.java
│   ├── ApiErrors.java        └── MenuApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/tiffino/menu/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/tiffino/menu/MenuController.java`

Does  
Reads the four query parameters with their defaults and limits, finds the restaurant, and returns the menu.

Why  
The constraint annotations sit next to the parameters they guard, so the rules are visible at the door.

Without it  
No endpoint; and without the annotations, `limit=0` or `limit=1000000` reaches the stream.

- `Boolean veg` (capital B) can be `null`, which means "no filter". A `boolean` could not say that.
- An unknown restaurant throws `ErrorResponseException`; Spring turns it into a `404` problem body.

#### `src/main/java/com/tiffino/menu/MenuQuery.java`

Does  
Runs the dishes through filter, sort, limit, in that order.

Why  
One small class holds the whole rule, so it is easy to unit-test without Spring.

Without it  
The pipeline ends up in the controller, and the trap is easy to re-introduce unnoticed.

- `thenComparing(Dish::name)` breaks ties, so equal prices never swap places between requests.
- `maxPrice * 100` converts rupees to paise once, with integers only.

#### `src/main/java/com/tiffino/menu/MenuCatalog.java`

Does  
Holds two restaurants and their dishes, in the order a kitchen typed them.

Why  
Keeps data out of the controller; a database replaces it later.

Without it  
The test data would live inside the controller.

#### `src/main/java/com/tiffino/menu/Dish.java`

One dish. `pricePaise` is an `int` of paise, never a `double`.

#### `src/main/java/com/tiffino/menu/Menu.java`

The response body: restaurant id and name, and the dishes.

#### `src/main/java/com/tiffino/menu/Restaurant.java`

A restaurant and its dishes, used inside the app only.

#### `src/main/java/com/tiffino/menu/ApiErrors.java`

Does  
Adds an `errors` map (parameter → message) to validation failures.

Why  
Spring's default 400 body says "Validation failure"; the app needs to know which filter was wrong.

Without it  
The app gets a 400 with no hint which parameter to fix.

#### `src/main/java/com/tiffino/menu/MenuApplication.java`

Standard Spring Boot entry point.

#### `pom.xml`

Adds `spring-boot-starter-validation` to station 001's set; it brings the validator that checks `@Min`, `@Max` and `@Pattern`.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                              | Test class                    | Result |
|---------------|------------------------------------------|-------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found | `MenuContractTest` (10)       | pass   |
| Every station | Reproduce the failure before the fix     | `LimitBeforeSortTrapTest` (2) | pass   |
| This station  | The pipeline on its own, without Spring  | `MenuQueryTest` (4)           | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.menu.LimitBeforeSortTrapTest
[INFO] Tests run: 10, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.menu.MenuContractTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.menu.MenuQueryTest
[INFO] Tests run: 16, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tiffino/menu/LimitBeforeSortTrapTest.java`

Written first: "limit, then sort" against "sort, then limit".

#### `src/test/java/com/tiffino/menu/MenuContractTest.java`

Defaults, each filter, ties, empty results, and every kind of bad parameter.

#### `src/test/java/com/tiffino/menu/MenuQueryTest.java`

The stream pipeline as plain Java: order of steps, ties, rupees against paise, and the input list left untouched.

#### `src/test/java/com/tiffino/menu/ApiTest.java`

Shared setup: the whole app, called through MockMvc.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tiffino/menu/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=NameSearchChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 16 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 22 tests pass (16 station tests and 6 challenge tests).

Challenge 1 · Beginner-friendly · about 30 minutes

## Search dishes by name

Add an optional `q` parameter: keep only dishes whose name contains it, ignoring letter case and surrounding spaces. At most 40 characters. It must work on a server running in a Turkish locale.

**Done when:** all four tests in `NameSearchChallengeTest` pass, and the station's tests still pass.

Hints

- Add the filter before `sorted`, next to the other two.
- `strip()` removes surrounding spaces; `toLowerCase(Locale.ROOT)` on both sides makes the match case-insensitive everywhere.
- `@Size(max = 40)` on the parameter gives the `400`.
- The station's `MenuQueryTest` builds a query with 4 arguments; keep that constructor working.

#### `challenge/NameSearchChallengeTest.java`

``` code
package com.tiffino.menu;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.util.Locale;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: a q parameter that finds dishes by part of their name, in any letter case. */
class NameSearchChallengeTest extends ApiTest {

    private final Locale original = Locale.getDefault();

    @AfterEach
    void restoreLocale() {
        Locale.setDefault(original);
    }

    @Test
    void findsDishesContainingTheWordInAnyCase() throws Exception {
        mvc.perform(get("/restaurants/101/menu").param("q", "RICE").param("sort", "price_asc"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.dishes[*].name", contains("Curd Rice", "Lemon Rice")));
    }

    @Test
    void surroundingSpacesAreIgnoredAndOtherFiltersStillApply() throws Exception {
        mvc.perform(get("/restaurants/101/menu").param("q", "  masala ").param("veg", "true"))
                .andExpect(jsonPath("$.dishes[*].name", contains("Masala Dosa", "Paneer Butter Masala")));
    }

    @Test
    void aTurkishServerLocaleStillFindsIdli() throws Exception {
        Locale.setDefault(Locale.forLanguageTag("tr-TR")); // "IDLI".toLowerCase() would give "ıdlı"
        mvc.perform(get("/restaurants/101/menu").param("q", "IDLI"))
                .andExpect(jsonPath("$.dishes[*].name", contains("Idli Sambar")));
    }

    @Test
    void aSearchLongerThan40CharactersIs400() throws Exception {
        mvc.perform(get("/restaurants/101/menu").param("q", "x".repeat(41)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.q").exists());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Beginner-friendly · about 20 minutes

## Show "5 of 9"

Add `totalMatching` to the response: how many dishes passed the filters, before the limit. The app uses it to show "Showing 5 of 9".

**Done when:** both tests in `MatchCountChallengeTest` pass.

Hints

- Count after the filters and before `limit`; that is the same question as the trap, the other way round.
- Put the filters in one private method that both the list and the count use, so they can never disagree.

#### `challenge/MatchCountChallengeTest.java`

``` code
package com.tiffino.menu;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** Challenge 2: tell the app how many dishes matched in total, so it can show "Showing 5 of 9". */
class MatchCountChallengeTest extends ApiTest {

    @Test
    void totalMatchingCountsBeforeTheLimit() throws Exception {
        mvc.perform(get("/restaurants/101/menu").param("veg", "true").param("maxPrice", "200").param("limit", "5"))
                .andExpect(jsonPath("$.dishes", hasSize(5)))
                .andExpect(jsonPath("$.totalMatching").value(9));
    }

    @Test
    void totalMatchingIsZeroWhenNothingMatches() throws Exception {
        mvc.perform(get("/restaurants/102/menu").param("veg", "true"))
                .andExpect(jsonPath("$.totalMatching").value(0));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## 140 dishes become 14,000 rows

All Tiffino restaurants now share one database table of dishes. Where should filtering, sorting and limiting happen: in Java after loading everything, or in SQL (`WHERE`, `ORDER BY`, `LIMIT`)? What does each choice cost in memory and time? Which index would make "veg dishes of restaurant 101, cheapest first" fast?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: "cheapest 5" must not be "first 5, sorted".
2.  Declare the four parameters with defaults and limits on the controller method.
3.  Put the pipeline in `MenuQuery`: filter, sort with a tie-breaker, limit.
4.  Answer an unknown restaurant with `404`, an empty match with `200 []`.
5.  Add the `errors` map so each bad parameter is named.

## Design alternatives and trade-offs

| Approach                                                     | What it costs                                                                                                        | Verdict        |
|--------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|----------------|
| Filter, sort, limit in a stream over the restaurant's dishes | Loads every dish of one restaurant (at most a few hundred). Simple and fast enough.                                  | Chosen         |
| Limit, then sort                                             | Wrong answers that look right.                                                                                       | Wrong          |
| Sort without a tie-breaker                                   | Equal prices can swap between requests; paging later shows a dish twice or never.                                    | Wrong          |
| `sort` as a Java enum                                        | Spring converts it for you, but enum names are upper case (`PRICE_ASC`) unless you add a converter.                  | Possible       |
| Do it in SQL (`WHERE`, `ORDER BY`, `LIMIT`)                  | The right choice once dishes live in a database and menus are large. Same rule: the database sorts before it limits. | Later stations |
| Return everything and let the app filter                     | Sends 140 dishes to every phone on every visit; the app's logic drifts from the server's.                            | Wrong          |

## Database design

None in this station: dishes are a fixed list in `MenuCatalog`. Challenge 3 asks you to think about the SQL version.

# 3 · Go deeper: Production

Security  
Every parameter has a range, so a request cannot ask for a million rows. The `400` body names the parameter but never echoes a stack trace.

Performance  
Sorting a few hundred dishes takes microseconds. The `limit` cap of 50 keeps responses small for phones on slow networks.

Reliability  
The tie-breaker makes answers deterministic, which matters as soon as results are cached or paged.

Maintainability  
Adding a filter means one parameter and one `filter` line, before the sort.

# 3 · Go deeper: Interview

## Interview takeaways

Why does the order of sorted() and limit() matter?

limit keeps the first N items of whatever reaches it. Before sorting, those are just the first N in storage order; after sorting, they are the N smallest. Same code, different question answered.

Why break ties by name?

Without a tie-breaker, two items that compare equal can come back in either order. Clients see the list change between identical requests, and paging can skip or repeat items.

Boolean or boolean for an optional filter?

Boolean, because it can be null, which means 'not given'. A primitive boolean defaults to false, so 'veg not given' and 'non-veg only' would look the same.

What happens when a query parameter fails @Min?

Spring validates the method's parameters before calling it and throws HandlerMethodValidationException, which becomes a 400. The method body never runs.

No dishes match: 200 or 404?

200 with an empty list. The restaurant exists and the query was valid; 'no results' is a valid answer. 404 would tell the app the restaurant does not exist.

## Self-check rubric

| Area        | Meets the bar                                 | Above the bar                                                           |
|-------------|-----------------------------------------------|-------------------------------------------------------------------------|
| Correctness | All 16 tests pass.                            | You can predict which tests fail if `limit` moves above `sorted`.       |
| Robustness  | Every bad parameter gets a `400` naming it.   | You found a parameter combination the tests do not cover, and added it. |
| Design      | Filter, sort, limit; ties broken.             | You can explain where this belongs once dishes are in a database.       |
| Explanation | You can walk through the stream line by line. | You can explain `Boolean` against `boolean` for optional filters.       |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on your own code instead:

- Is `limit` the last step, after every filter and the sort?
- Does every sort have a tie-breaker?
- Does every numeric parameter have both a minimum and a maximum?
- Is "nothing matched" a `200` with an empty list?
