# Station 061 · Restaurant list without N+1 queries

Working Systems · 0–2 years · Core · Food delivery · Types: Database

Spring Boot 4.1.1 · Java 25 · Spring Data JPA · Hibernate 7.4 · @EntityGraph · DTO projections · Hibernate statistics · PostgreSQL 17 · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Cities, restaurants, cuisines and ratings are demo data, not Tiffino's. Nothing is ordered or delivered.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 13 tests.

# 1 · Understand

## The problem in real life

1.  **The home screen**

    Tiffino shows 50 restaurants of a city, each with its cuisines and its star rating.

2.  **The slow part**

    The code loaded 50 restaurants, then for each one asked for its cuisines and its reviews: 101 queries for one screen. Each is fast; 101 of them on every app launch is not.

3.  **The fix**

    Three queries, whatever the page size: the page, the cuisines of those restaurants, and the ratings already averaged by the database.

Count the queries. The number should not grow with the page.

## What are we building?

`GET /restaurants?city=pune` returns a page of restaurants with their cuisines and ratings, in three queries.

## An everyday analogy

A waiter taking an order for a table of 50. The slow way: walk to the kitchen for the first plate, come back, walk again for the second. The fast way: one trip with a trolley for all the plates, one for all the drinks.

## How it works in 4 steps

1.  **Find the page**: the ids of up to 50 restaurants in the city, in name order.
2.  **Load those restaurants** with their cuisines, in one join.
3.  **Ask for the ratings**: average and count per restaurant, computed by the database in one query.
4.  **Put the cards together** in the page's order.

Check yourself: the page size goes from 20 to 50. How many queries does the new screen send? And the old one?

The new one: still 3. The old one: from 41 (1 + 20 + 20) to 101 (1 + 50 + 50). The test checks the new one at sizes 5, 20 and 50.

## What this station is not

- **No ordering or delivery.** Restaurants are read only.
- **No caching.** Fewer queries first; a cache is another station.
- **No search or ranking.** Name order; Practice 2 adds rating order.

## Key terms

| Term               | Simple meaning                                                             | Everyday example                                                   | In this project                              |
|--------------------|----------------------------------------------------------------------------|--------------------------------------------------------------------|----------------------------------------------|
| **Query**          | One question sent to the database.                                         | One trip to the storeroom.                                         | counted by Hibernate statistics in the tests |
| **Lazy loading**   | A related collection is fetched only when the code first touches it.       | The menu card stays in the drawer until someone asks for it.       | `Restaurant.cuisines`                        |
| **N+1**            | One query for the list, then one more for each item in it.                 | Fifty trips to the storeroom, one per box, instead of one trolley. | the old home screen: 1 + 50 + 50             |
| **Entity graph**   | Tells JPA which associations to load together with the entity.             | "Bring the menu card with the restaurant."                         | `@EntityGraph(attributePaths = "cuisines")`  |
| **DTO projection** | The query builds a small result object directly, without loading entities. | Asking for the total, not every receipt.                           | `RatingSummary`                              |
| **Fetch join**     | `JOIN FETCH` in JPQL: load the association in the same query.              | Like the entity graph, but an inner join unless you write `LEFT`.  | the trap's first fix                         |

# 2 · Build: Spec

## Business problem

**Tiffino** (a fictional food delivery app) opens on a list of restaurants. For 50 restaurants with their cuisines and ratings, the server ran 1 + 50 + 50 queries on every launch.

## Acceptance criteria

Demo data: Mumbai has 3 restaurants written out by hand, Pune has 60 generated ones, Nagpur none.

1.  **Given** `city=mumbai`, **then** Anand Stall, Bombay Canteen and Cafe Madras, in name order, each with its cuisines sorted and its rating rounded to one decimal.
2.  **Given** a restaurant with no reviews, **then** `average` is `null` and `count` is 0.
3.  **Given** any page of up to 50, **then** 3 queries.
4.  **Given** `city=nagpur` or a page past the end, **then** `200` with no restaurants; a city Tiffino does not serve, `404`.
5.  **Given** no city, a page size of 0 or over 50, or a negative page, **then** `400`.

## Requirements

- A fixed number of queries per page, proved by counting them in a test.
- Paging happens in the database (`LIMIT`/`OFFSET`), never in memory.
- A restaurant with no cuisines or no reviews still appears.
- City codes are lower-cased with `Locale.ROOT`.

## Learning objectives

- Spot an N+1 in code and prove it with a query count.
- Fix it with `@EntityGraph` or `JOIN FETCH`, and know the difference.
- Use a DTO projection for aggregates.
- Page safely when a collection is loaded too.

# 2 · Build: API contract

## Endpoint

| Method | Path                                 | Purpose                                                                                                                |
|--------|--------------------------------------|------------------------------------------------------------------------------------------------------------------------|
| `GET`  | `/restaurants?city=…&page=0&size=20` | A page of the city's restaurants: `{city, page, size, restaurants: [{id, name, cuisines, rating: {average, count}}]}`. |

## Status codes

| Status | When                                                                                                          |
|--------|---------------------------------------------------------------------------------------------------------------|
| 200    | A page, possibly empty                                                                                        |
| 400    | No city, a city outside `[A-Za-z-]{3,30}`, page below 0 or above 1000, size below 1 or above 50 (demo limits) |
| 404    | A city Tiffino does not serve                                                                                 |

## Captured examples

Captured with curl from the running app on 16 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: Mumbai

**Why:** every number here can be checked against the demo data; Anand Stall has no reviews yet.

Request

``` code
GET /restaurants?city=mumbai HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 361

{
  "city": "mumbai",
  "page": 0,
  "size": 20,
  "restaurants": [
    {
      "id": 2,
      "name": "Anand Stall",
      "cuisines": [
        "Street Food"
      ],
      "rating": {
        "average": null,
        "count": 0
      }
    },
    {
      "id": 1,
      "name": "Bombay Canteen",
      "cuisines": [
        "Maharashtrian",
        "North Indian"
      ],
      "rating": {
        "average": 4.3,
        "count": 3
      }
    },
    {
      "id": 3,
      "name": "Cafe Madras",
      "cuisines": [
        "Desserts",
        "South Indian"
      ],
      "rating": {
        "average": 4.0,
        "count": 2
      }
    }
  ]
}
```

### Case 2: the first five in Pune

**Why:** a page, in name order.

Request

``` code
GET /restaurants?city=pune&size=5 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 592

{
  "city": "pune",
  "page": 0,
  "size": 5,
  "restaurants": [
    {
      "id": 4,
      "name": "Pune Kitchen 01",
      "cuisines": [
        "Desserts",
        "North Indian"
      ],
      "rating": {
        "average": 2.5,
        "count": 4
      }
    },
    {
      "id": 5,
      "name": "Pune Kitchen 02",
      "cuisines": [
        "South Indian",
        "Street Food"
      ],
      "rating": {
        "average": null,
        "count": 0
      }
    },
    {
      "id": 6,
      "name": "Pune Kitchen 03",
      "cuisines": [
        "Chinese",
        "North Indian"
      ],
      "rating": {
        "average": 3.0,
        "count": 1
      }
    },
    {
      "id": 7,
      "name": "Pune Kitchen 04",
      "cuisines": [
        "Maharashtrian",
        "South Indian"
      ],
      "rating": {
        "average": 4.5,
        "count": 2
      }
    },
    {
      "id": 8,
      "name": "Pune Kitchen 05",
      "cuisines": [
        "Chinese",
        "Desserts"
      ],
      "rating": {
        "average": 2.7,
        "count": 3
      }
    }
  ]
}
```

### Case 3: Nagpur, typed with a capital

**Why:** a city Tiffino serves with no restaurants yet: an empty page, not a `404`.

Request

``` code
GET /restaurants?city=Nagpur HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 53

{
  "city": "nagpur",
  "page": 0,
  "size": 20,
  "restaurants": []
}
```

### Case 4: Jaipur

**Why:** `404`.

Request

``` code
GET /restaurants?city=jaipur HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "Tiffino does not deliver in jaipur yet",
  "instance": "/restaurants",
  "status": 404,
  "title": "Not Found"
}
```

### Case 5: size 500

**Why:** `400`; a page is at most 50.

Request

``` code
GET /restaurants?city=pune&size=500 HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Validation failure",
  "instance": "/restaurants",
  "status": 400,
  "title": "Bad Request"
}
```

## The SQL behind one page of 50

From `docs/capture.sh`: a second copy of the app with Hibernate's SQL log switched on, one request (`docs/captures/sql.txt`). 3 statements.

``` code
select r1_0.id from restaurants r1_0 where r1_0.city_code=? order by r1_0.name,r1_0.id fetch first ? rows only

select r1_0.id,r1_0.city_code,c1_0.restaurant_id,c1_1.id,c1_1.name,r1_0.name from restaurants r1_0 left join restaurant_cuisines c1_0 on r1_0.id=c1_0.restaurant_id left join cuisines c1_1 on c1_1.id=c1_0.cuisine_id where r1_0.id in (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)

select r1_0.restaurant_id,avg(r1_0.rating),count(r1_0.id) from reviews r1_0 where r1_0.restaurant_id in (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) group by r1_0.restaurant_id
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                               | What happens                   | Proved by                                                                         |
|----------------------------------------------------|--------------------------------|-----------------------------------------------------------------------------------|
| A restaurant with no reviews                       | `average: null`, `count: 0`    | `mumbaiListsItsRestaurantsWithCuisinesAndRatings`                                 |
| A restaurant with no cuisines                      | Still listed                   | `aFetchJoinPageLeavesOutRestaurantsWithNoCuisines`                                |
| Pages of 5, 20 and 50                              | 3 queries each                 | `theNewScreenSendsThreeQueriesForAnyPageSize`                                     |
| Page 2 of Pune                                     | Continues where page 1 stopped | `puneComesInPages`                                                                |
| `MUMBAI`                                           | Same as `mumbai`               | `theCityIsMatchedInAnyCase`                                                       |
| Nagpur; past the last page; Jaipur                 | Empty; empty; `404`            | `aCityWithNoRestaurantsOrAPagePastTheEndIsEmpty`, `aCityTiffinoDoesNotServeIs404` |
| Bad parameters                                     | `400`                          | `badParametersAre400`                                                             |
| Bad rows written directly; a half-added restaurant | Refused; rolled back           | `RestaurantDatabaseTest`                                                          |

## The trap

Plausible but wrong

Lazy loading inside a loop: 1 + N queries per page.

The old screen is kept in the tests as `OldHomeScreen`. Its results are right; the test proves the new screen gives exactly the same cards. Only the query count differs: 101 against 3.

The first fix people reach for is `JOIN FETCH` with the same page. Two things to know:

- **Paging.** Hibernate 5 loaded *every* matching row and cut the page in memory, with the warning HHH000104. Hibernate 7.4, used here, puts the page in a subquery instead: the test counts 1 query. Check your version's SQL before trusting either.
- **Inner join.** `JOIN FETCH` drops rows with nothing to join. A new restaurant with no cuisines yet vanishes from the page. The entity graph uses a left join, so the new screen still lists it.

While building, each fix was undone once: no entity graph turned 1 test red (the query count); an inner `JOIN FETCH` 1; losing the page order 2; no rounding 2; no `404` and no lower-casing 1 each.

``` code
package com.tiffino.restaurants;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** Written first: the old home screen counted, then the fix counted, on the same page of 50 Pune restaurants. */
class NPlusOneTrapTest extends ApiTest {

    @Autowired
    OldHomeScreen oldHomeScreen;
    @Autowired
    HomeScreen homeScreen;

    @Test
    void theOldScreenSendsOnePlusFiftyPlusFiftyQueries() {
        Counted<List<HomeScreen.Card>> old = counting(() -> oldHomeScreen.list("pune", 0, 50));
        assertThat(old.result()).hasSize(50);
        assertThat(old.queries()).isEqualTo(1 + 50 + 50);
    }

    @Test
    void theNewScreenSendsThreeQueriesForAnyPageSize() {
        for (int size : new int[]{5, 20, 50}) {
            Counted<HomeScreen.Listing> page = counting(() -> homeScreen.list("pune", 0, size));
            assertThat(page.result().restaurants()).hasSize(size);
            assertThat(page.queries()).as("page size %d", size).isEqualTo(3);
        }
    }

    @Test
    void bothGiveTheSameCards() {
        assertThat(homeScreen.list("pune", 0, 50).restaurants()).isEqualTo(oldHomeScreen.list("pune", 0, 50));
        assertThat(homeScreen.list("mumbai", 0, 20).restaurants()).isEqualTo(oldHomeScreen.list("mumbai", 0, 20));
    }

    @Test
    void aFetchJoinPageLeavesOutRestaurantsWithNoCuisines() {
        jdbc.sql("INSERT INTO cities (code, name) VALUES ('testville', 'Testville')").update();
        try {
            jdbc.sql("INSERT INTO restaurants (city_code, name) VALUES ('testville', 'Aamchi Thali'), ('testville', 'Zunka Bhakar')").update();
            jdbc.sql("INSERT INTO restaurant_cuisines SELECT id, 4 FROM restaurants WHERE name = 'Zunka Bhakar'").update();   // Aamchi Thali has none yet
            Counted<List<String>> fetchJoin = counting(() -> oldHomeScreen.fetchJoinPage("testville", 0, 20));
            assertThat(fetchJoin.queries()).isEqualTo(1);   // Hibernate 7.4 applies the page in SQL, in a subquery
            assertThat(fetchJoin.result()).containsExactly("Zunka Bhakar");
            assertThat(homeScreen.list("testville", 0, 20).restaurants()).extracting(HomeScreen.Card::name).containsExactly("Aamchi Thali", "Zunka Bhakar");
        } finally {
            jdbc.sql("DELETE FROM restaurants WHERE city_code = 'testville'").update();
            jdbc.sql("DELETE FROM cities WHERE code = 'testville'").update();
        }
    }
}
```

``` code
package com.tiffino.restaurants;

import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

/** The home screen as it was, kept in the tests only: correct results, one query per restaurant per association. */
@Component
class OldHomeScreen {

    private final OldRestaurants restaurants;
    private final OldReviews reviews;

    OldHomeScreen(OldRestaurants restaurants, OldReviews reviews) {
        this.restaurants = restaurants;
        this.reviews = reviews;
    }

    @Transactional(readOnly = true)
    List<HomeScreen.Card> list(String city, int page, int size) {
        return restaurants.findByCityCodeOrderByNameAscIdAsc(city, PageRequest.of(page, size)).stream().map(r -> {
            List<String> cuisines = r.getCuisines().stream().map(Cuisine::getName).sorted().toList();   // +1 query: the lazy set loads
            List<Review> all = reviews.findByRestaurantId(r.getId());                                  // +1 query: every review row
            HomeScreen.Rating rating = all.isEmpty() ? new HomeScreen.Rating(null, 0)
                    : new HomeScreen.Rating(BigDecimal.valueOf(all.stream().mapToInt(Review::getRating).average().orElseThrow()).setScale(1, RoundingMode.HALF_UP), all.size());
            return new HomeScreen.Card(r.getId(), r.getName(), cuisines, rating);
        }).toList();
    }

    @Transactional(readOnly = true)
    List<String> fetchJoinPage(String city, int page, int size) {
        return restaurants.findWithCuisines(city, PageRequest.of(page, size)).stream().map(Restaurant::getName).toList();
    }
}
```

``` code
package com.tiffino.restaurants;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.Repository;

import java.util.List;

/** The old queries, kept in the tests only. */
interface OldRestaurants extends Repository<Restaurant, Long> {

    List<Restaurant> findByCityCodeOrderByNameAscIdAsc(String cityCode, Pageable page);

    /** The first fix someone tries: fetch the cuisines in the same query, and keep paging. JOIN FETCH is an inner join. */
    @Query("select r from Restaurant r join fetch r.cuisines where r.cityCode = :city order by r.name, r.id")
    List<Restaurant> findWithCuisines(String city, Pageable page);
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
./mvnw test                 # all 13 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Watch the SQL yourself: start the app with Hibernate's SQL log on, call the endpoint once, and count the lines.

``` code
./mvnw spring-boot:run -Dspring-boot.run.arguments=--logging.level.org.hibernate.SQL=debug
curl 'http://localhost:8080/restaurants?city=pune&size=50'
```

The capture above did exactly this. Then remove `@EntityGraph` from `findByIdIn` and count again.

## Troubleshooting

| You see                                                                                 | Cause                                                                        | Fix                                                                            |
|-----------------------------------------------------------------------------------------|------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| `No qualifying bean of type '…OldHomeScreen$OldRestaurants'`                            | Spring Data ignores repository interfaces nested inside a class.             | Make each repository a top-level interface. Found while building this station. |
| `LazyInitializationException`                                                           | A lazy collection touched after the transaction ended (open-in-view is off). | Load it in the service: an entity graph or a fetch join.                       |
| `HHH000104: firstResult/maxResults specified with collection fetch; applying in memory` | Older Hibernate paging a fetch join in memory.                               | Page the ids first, as here, then load the page.                               |
| A restaurant missing from the page                                                      | An inner `JOIN FETCH` on an empty collection.                                | `LEFT JOIN FETCH`, or an entity graph.                                         |

## Project layout

``` tree
stations/061-restaurant-list-without-n-plus-1-queries/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/tiffino/restaurants/
│   ├── RestaurantController.java   ├── HomeScreen.java
│   ├── RestaurantRepository.java   ├── ReviewRepository.java   ├── RatingSummary.java
│   ├── Restaurant.java   ├── Review.java   ├── Cuisine.java   ├── City.java   ├── CityRepository.java
│   └── RestaurantsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__restaurants.sql, V2__demo_restaurants.sql
├── src/test/java/com/tiffino/restaurants/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/tiffino/restaurants/RestaurantController.java`

Does  
Checks the parameters and lower-cases the city.

Why  
Page size and number are limited before any query.

Without it  
`size=100000` loading a whole city.

#### `src/main/java/com/tiffino/restaurants/HomeScreen.java`

Does  
The three queries, then the cards in page order.

Why  
The number of queries stays the same for any page size.

Without it  
One query per restaurant per association.

- The city is looked up only when the page is empty, so the usual path stays at three.
- `findByIdIn` returns rows in any order; the cards follow the ids of query 1.

#### `src/main/java/com/tiffino/restaurants/RestaurantRepository.java`

Does  
Query 1 (a page of ids) and query 2 (those restaurants with cuisines).

Why  
Paging ids only lets the database apply `LIMIT`; the entity graph loads cuisines with a left join.

Without it  
A lazy load per restaurant, or a fetch join that hides restaurants without cuisines.

#### `src/main/java/com/tiffino/restaurants/ReviewRepository.java`

Does  
Query 3: average and count per restaurant, as `RatingSummary` objects.

Why  
The database averages; no review row reaches Java.

Without it  
Loading every review to average them in a loop.

#### `src/main/java/com/tiffino/restaurants/RatingSummary.java`

The projection: built by `select new …`.

#### `src/main/java/com/tiffino/restaurants/Restaurant.java`

A restaurant; its cuisines are lazy, the JPA default for collections.

#### `src/main/java/com/tiffino/restaurants/Review.java`

One rating, 1 to 5.

#### `src/main/java/com/tiffino/restaurants/Cuisine.java`

A cuisine.

#### `src/main/java/com/tiffino/restaurants/City.java`

A city Tiffino serves.

#### `src/main/java/com/tiffino/restaurants/CityRepository.java`

"Does this city exist", for empty pages only.

#### `src/main/resources/db/migration/V1__restaurants.sql`

Does  
The tables, named constraints and the page index.

Why  
`restaurants_city_name` matches the page query's filter and order.

Without it  
A sort of the whole city on every page.

#### `src/main/resources/db/migration/V2__demo_restaurants.sql`

3 Mumbai restaurants by hand, 60 in Pune generated, none in Nagpur.

#### `src/main/resources/application.yaml`

open-in-view off: a lazy association cannot load quietly while the response is written.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/tiffino/restaurants/RestaurantsApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                   | Result |
|---------------|-------------------------------------------------------|------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `RestaurantContractTest` (6) | pass   |
| Every station | Reproduce the failure before the fix                  | `NPlusOneTrapTest` (4)       | pass   |
| Database      | Rollback and constraint tests against a real database | `RestaurantDatabaseTest` (3) | pass   |

## How the queries are counted

The tests switch on Hibernate statistics (`hibernate.generate_statistics=true`, tests only) and read `getPrepareStatementCount()` around each call: every SQL statement Hibernate sends, including lazy loads.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Hibernate 7.4, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.restaurants.RestaurantContractTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.restaurants.NPlusOneTrapTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.restaurants.RestaurantDatabaseTest
[INFO] Tests run: 13, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tiffino/restaurants/NPlusOneTrapTest.java`

Written first: 101 queries old, 3 new, the same cards, and the fetch-join page.

#### `src/test/java/com/tiffino/restaurants/RestaurantDatabaseTest.java`

Named constraints with plain SQL, a rolled-back restaurant, and cascades, in a test city removed afterwards.

#### `src/test/java/com/tiffino/restaurants/RestaurantContractTest.java`

The endpoint through HTTP.

#### `src/test/java/com/tiffino/restaurants/OldHomeScreen.java`

The old screen, kept in the tests only.

#### `src/test/java/com/tiffino/restaurants/OldRestaurants.java`

The old queries, including the fetch-join page.

#### `src/test/java/com/tiffino/restaurants/OldReviews.java`

The old per-restaurant review query.

#### `src/test/java/com/tiffino/restaurants/ApiTest.java`

Shared setup and the query counter.

#### `src/test/java/com/tiffino/restaurants/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tiffino/restaurants/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=CuisineFilterChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 13 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 17 tests pass (13 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Filter by cuisine

Add `cuisine=…`: only restaurants serving it (any case), each card still with *all* its cuisines, still three queries.

**Done when:** both tests in `CuisineFilterChallengeTest` pass.

Hints

- Only query 1 changes. Filter with `exists (select 1 … join x.cuisines c where … lower(c.name) = lower(:cuisine))`.
- A join on cuisines in query 2 instead would cut the other cuisines off the card.

#### `challenge/CuisineFilterChallengeTest.java`

``` code
package com.tiffino.restaurants;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.empty;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /restaurants?city=mumbai&cuisine=south indian lists only restaurants serving that cuisine (any
 * case), each card still showing all of its cuisines, and still in three queries.
 */
class CuisineFilterChallengeTest extends ApiTest {

    @Test
    void onlyRestaurantsServingTheCuisine() throws Exception {
        mvc.perform(get("/restaurants").param("city", "mumbai").param("cuisine", "south indian")).andExpect(status().isOk())
                .andExpect(jsonPath("$.restaurants[*].name", contains("Cafe Madras")))
                .andExpect(jsonPath("$.restaurants[0].cuisines", contains("Desserts", "South Indian")));
        mvc.perform(get("/restaurants").param("city", "mumbai").param("cuisine", "Chinese")).andExpect(status().isOk())
                .andExpect(jsonPath("$.restaurants", empty()));
    }

    @Test
    void stillThreeQueries() {
        Counted<Long> counted = counting(() -> {
            try {
                mvc.perform(get("/restaurants").param("city", "pune").param("cuisine", "Chinese").param("size", "50")).andExpect(status().isOk());
            } catch (Exception e) {
                throw new IllegalStateException(e);
            }
            return 0L;
        });
        assertThat(counted.queries()).isEqualTo(3);
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Top rated first

Add `sort=rating`: best average first, unrated last, ties by name. Any other sort value is `400`, never SQL.

**Done when:** both tests in `TopRatedChallengeTest` pass.

Hints

- Order in query 1, so page 2 continues page 1: `left join Review v … group by r.id, r.name order by avg(v.rating) desc nulls last, r.name, r.id`.
- Validate `sort` against a whitelist with `@Pattern(regexp = "name|rating")`.

#### `challenge/TopRatedChallengeTest.java`

``` code
package com.tiffino.restaurants;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: sort=rating orders the city by average rating, best first; restaurants with no reviews come last, ties
 * by name. The ordering happens in the page query, so page 2 continues page 1. Default sort stays by name; any other
 * sort value is 400. Still three queries.
 */
class TopRatedChallengeTest extends ApiTest {

    @Test
    void bestRatedFirstAndUnratedLast() throws Exception {
        mvc.perform(get("/restaurants").param("city", "mumbai").param("sort", "rating")).andExpect(status().isOk())
                .andExpect(jsonPath("$.restaurants[*].name", contains("Bombay Canteen", "Cafe Madras", "Anand Stall")));
        mvc.perform(get("/restaurants").param("city", "mumbai").param("sort", "rating").param("size", "1").param("page", "1")).andExpect(status().isOk())
                .andExpect(jsonPath("$.restaurants[*].name", contains("Cafe Madras")));
        mvc.perform(get("/restaurants").param("city", "mumbai").param("sort", "name; drop table reviews")).andExpect(status().isBadRequest());
    }

    @Test
    void stillThreeQueries() {
        Counted<Long> counted = counting(() -> {
            try {
                mvc.perform(get("/restaurants").param("city", "pune").param("sort", "rating").param("size", "50")).andExpect(status().isOk());
            } catch (Exception e) {
                throw new IllegalStateException(e);
            }
            return 0L;
        });
        assertThat(counted.queries()).isEqualTo(3);
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## @BatchSize, or a cache?

Hibernate's `@BatchSize(size = 50)` on `cuisines` turns 50 lazy loads into one `… where restaurant_id in (…)` query, with no change to the service. A cache of ratings would remove query 3. For each: how many queries for a page of 50, what goes stale and when, and what a new developer must know so the N+1 does not come back somewhere else.

# 3 · Go deeper: Design

## Implementation approach

1.  Count the old screen's queries in a test: 101.
2.  Page ids only, so the database applies the limit.
3.  Load those restaurants with cuisines through an entity graph.
4.  Ask the database for ratings as a projection, then assemble in page order and compare with the old cards.

## Design alternatives and trade-offs

| Approach                                       | Queries for 50                | Verdict                                            |
|------------------------------------------------|-------------------------------|----------------------------------------------------|
| Page of ids + entity graph + rating projection | 3                             | Chosen                                             |
| Lazy loads in a loop                           | 101                           | The trap                                           |
| `JOIN FETCH` with a page                       | 1 + ratings, in Hibernate 7.4 | Inner join drops rows; Hibernate 5 paged in memory |
| `@BatchSize` on the collection                 | 1 + 1 + ratings               | Good default; hides where queries happen           |
| One native SQL query with `array_agg`          | 1                             | Fastest; no entities, PostgreSQL-only              |

## Database design

| Table                 | Constraints                                                                        | Why                                                 |
|-----------------------|------------------------------------------------------------------------------------|-----------------------------------------------------|
| `cities`              | `cities_code_shape`                                                                | Lower-case codes only, as the API sends them.       |
| `restaurants`         | `restaurants_city_fk`, `restaurants_name_per_city`; index `(city_code, name, id)`  | The index serves the page query's filter and order. |
| `restaurant_cuisines` | `restaurant_cuisines_pk`, two foreign keys                                         | A cuisine once per restaurant.                      |
| `reviews`             | `reviews_rating_range` (1 to 5), `reviews_restaurant_fk`; index on `restaurant_id` | The rating query groups by restaurant.              |

``` code
CREATE TABLE cities (
    code VARCHAR(30)  PRIMARY KEY CONSTRAINT cities_code_shape CHECK (code ~ '^[a-z-]{3,30}$'),
    name VARCHAR(100) NOT NULL
);

CREATE TABLE cuisines (
    id   BIGINT       PRIMARY KEY,
    name VARCHAR(50)  NOT NULL CONSTRAINT cuisines_name_unique UNIQUE
);

CREATE TABLE restaurants (
    id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city_code VARCHAR(30)  NOT NULL CONSTRAINT restaurants_city_fk REFERENCES cities (code),
    name      VARCHAR(100) NOT NULL,
    CONSTRAINT restaurants_name_per_city UNIQUE (city_code, name)
);
-- The home screen's query: restaurants of one city in name order.
CREATE INDEX restaurants_city_name ON restaurants (city_code, name, id);

CREATE TABLE restaurant_cuisines (
    restaurant_id BIGINT NOT NULL CONSTRAINT restaurant_cuisines_restaurant_fk REFERENCES restaurants (id) ON DELETE CASCADE,
    cuisine_id    BIGINT NOT NULL CONSTRAINT restaurant_cuisines_cuisine_fk REFERENCES cuisines (id),
    CONSTRAINT restaurant_cuisines_pk PRIMARY KEY (restaurant_id, cuisine_id)
);

CREATE TABLE reviews (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    restaurant_id BIGINT   NOT NULL CONSTRAINT reviews_restaurant_fk REFERENCES restaurants (id) ON DELETE CASCADE,
    rating        SMALLINT NOT NULL CONSTRAINT reviews_rating_range CHECK (rating BETWEEN 1 AND 5)
);
CREATE INDEX reviews_restaurant ON reviews (restaurant_id);
```

# 3 · Go deeper: Production

Find N+1 before users do  
A query-count assertion in the test of every list endpoint is cheap and catches the next lazy association someone adds.

Logs  
SQL logging is for a developer machine: it is slow and can log customer data. In production, watch query counts and times with metrics or `pg_stat_statements`.

Deep pages  
`OFFSET` gets slower page by page; station 066 replaces it with keyset paging.

Ratings at scale  
Averaging every review on every launch is fine for thousands of reviews; for millions, keep a running count and sum per restaurant.

# 3 · Go deeper: Interview

## Interview takeaways

What is the N+1 query problem?

One query loads a list; then code touches a lazy association on each item, sending one more query per item. The total grows with the list.

How do you prove you fixed it?

Count the statements in a test (Hibernate statistics, a datasource proxy) and assert the number stays the same for different page sizes.

@EntityGraph or JOIN FETCH?

Both load an association in the same query. An entity graph is declared on a repository method and uses a left join; JOIN FETCH is written in JPQL and is an inner join unless you write LEFT.

Why page ids first?

A fetch join multiplies rows (one per cuisine), so a SQL limit would cut a restaurant's cuisines. Older Hibernate therefore paged in memory; paging ids keeps the limit in the database on any version.

What is a DTO projection?

A query that builds plain objects (select new … or an interface) instead of entities: no dirty checking, no lazy associations, only the columns needed.

## Self-check rubric

| Area         | Meets the bar                          | Above the bar                                          |
|--------------|----------------------------------------|--------------------------------------------------------|
| Correctness  | All 13 tests pass.                     | You counted the queries with the entity graph removed. |
| JPA fetching | An entity graph instead of lazy loops. | Why JOIN FETCH dropped a restaurant.                   |
| Paging       | The limit runs in SQL.                 | What older Hibernate did with a fetch join and a page. |
| Projections  | Ratings averaged by the database.      | When a native query is worth it.                       |

# 3 · Go deeper: Review

## No reviewer view for this station

This station has no flawed version to review. Use this checklist on any list endpoint:

- Which associations does the response touch, and how is each one loaded?
- Is there a test that counts the queries for two different page sizes?
- Is the page limit applied in SQL? Read the SQL, not the code.
- Can a row with an empty collection disappear from the result?
