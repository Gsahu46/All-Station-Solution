# Station 048 · Product reviews and ratings

Foundations · 0–1 years · Core · E-commerce · Types: Database

Spring Boot 4.1.1 · Java 25 · Spring Data JPA (Hibernate 7) · @ManyToOne · @Modifying JPQL update · Slice paging · PostgreSQL 17 · Flyway · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Products, customers, purchases and reviews are demo data, not Kartwala's. "Delivered" is a date in the purchases table; no courier or order system is called. The customer is named in the request body because this station has no login.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 12 tests.

# 1 · Understand

## The problem in real life

1.  **Forty five-star reviews**

    One customer posted 40 five-star reviews of a phone case they never bought. The page showed 4.9 stars.

2.  **Two million rows per view**

    A bestseller's page recomputed the average from 2 million reviews on every view. During a sale, the database spent most of its time on that one query.

3.  **The fix**

    One review per customer per product, only after delivery, both enforced by the database; and the rating kept in its own row, updated with each review.

A number read on every page view should be stored, not recomputed; and the rule for who may add to it belongs in the database too.

## What are we building?

A buyer posts one review (`POST /products/{id}/reviews`); anyone reads the reviews ten at a time (`GET /products/{id}/reviews`) and the rating (`GET /products/{id}/rating`). The rating is one stored row, kept in step with every review.

## An everyday analogy

A cricket scoreboard. Nobody re-adds every ball to show the score; the scorer adds each run as it happens. The board stays right only if every run goes on it, and two scorers never write over each other.

## How it works in 4 steps

1.  **Check** the product exists and the customer has a delivered order of it.
2.  **Insert** the review; the unique index refuses a second one from the same customer.
3.  **Add** one to the count and the stars to the total, in one SQL statement, in the same transaction.
4.  **Read** the rating from that one row; the average is total ÷ count.

Check yourself: why store a total of stars instead of the average?

An average cannot be updated alone: adding a review needs the old count anyway. Count and total update by simple addition, never lose precision, and give the average with one division.

## What this station is not

- **No login.** The customer is named in the body.
- **No moderation or photos.** Text and stars only.
- **No editing or deleting.** Editing is challenge 1.

## Key terms

| Term                  | Simple meaning                                                                       | Everyday example                                            | In this project                   |
|-----------------------|--------------------------------------------------------------------------------------|-------------------------------------------------------------|-----------------------------------|
| **Verified purchase** | A review allowed only from someone whose order of that product was delivered.        | Only guests who stayed can review the hotel.                | `purchases.delivered_on`          |
| **Unique constraint** | The database refuses a second row with the same values.                              | One vote per voter ID.                                      | `reviews_one_per_customer`        |
| **Aggregate**         | A number summarising many rows: a count, a sum, an average.                          | A cricket team's run total.                                 | Count and star total              |
| **Stored aggregate**  | The summary kept in its own row and updated with each change.                        | The scoreboard, updated each ball.                          | `product_ratings`                 |
| **Recompute**         | Working the summary out again from every row when asked.                             | Re-adding every ball of the match to show the score.        | The old rating query              |
| **Atomic update**     | A change the database makes in one step, so two at once cannot overwrite each other. | Two scorers adding runs on one shared board, one at a time. | `review_count = review_count + 1` |

# 2 · Build: Spec

## Business problem

**Kartwala** (a fictional marketplace) showed ratings that one customer could inflate, and computed them so expensively that product pages slowed down during sales.

## Acceptance criteria

1.  **Given** Asha (delivered) gives 5 stars and Vikram (delivered) 3, **then** the rating is 2 reviews, 4.0.
2.  **Given** Asha posts again, **then** `409`; ten posts from her at the same moment make one review.
3.  **Given** Neha (not delivered yet), Imran (never bought) or a buyer of another product, **then** `422`.
4.  **Given** 20 buyers post at the same moment, **then** all 20 are counted and the stored total equals a recount.
5.  **Given** 0 or 6 stars, 4.5 stars, blank text, or page −1 or 100, **then** `400`; an unknown product, `404`.
6.  **Given** 200,000 reviews, **then** the rating is read from one row.

## Requirements

- One review per customer per product, enforced by a unique constraint.
- The review's purchase must be that customer's purchase of that product (a composite foreign key). Delivery is checked in Java.
- The review and the stored totals change in one transaction, by an atomic update.
- The average is total ÷ count, rounded half up to one decimal; no reviews means no average (`null`).

## Learning objectives

- Enforce "one per customer" and "only buyers" in the database, and map the violation to `409`.
- Choose between a stored aggregate and a recompute, and keep a stored one correct.
- Update a counter with one atomic statement instead of read, change, write.
- Page without counting every row (a `Slice`).

# 2 · Build: API contract

## Endpoints

| Method | Path                            | Purpose                                                                                            |
|--------|---------------------------------|----------------------------------------------------------------------------------------------------|
| `POST` | `/products/{id}/reviews`        | Post a review: `customerId`, `stars` (1 to 5), `text` (1 to 2,000 characters).                     |
| `GET`  | `/products/{id}/reviews?page=0` | Ten reviews, newest first; `hasNext` says whether another page exists. Pages 0 to 99 (demo limit). |
| `GET`  | `/products/{id}/rating`         | Review count and average stars.                                                                    |

## Status codes

| Status | When                                                                                           |
|--------|------------------------------------------------------------------------------------------------|
| 201    | Review posted                                                                                  |
| 200    | A page of reviews; the rating                                                                  |
| 400    | Stars outside 1 to 5 or not whole, text blank or too long, customer missing, page out of range |
| 404    | No such product                                                                                |
| 409    | This customer already reviewed this product                                                    |
| 422    | No delivered purchase of this product by this customer                                         |

## Captured examples

Captured with curl from the running app on 15 Oct 2026, in this order, against one fresh database. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: Asha, delivered, 5 stars

**Why:** a verified purchase: `201`.

Request

``` code
POST /products/1/reviews HTTP/1.1
Content-Type: application/json

{
  "customerId": 1,
  "stars": 5,
  "text": "Good bass, and the battery really lasts a week."
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 169

{
  "id": 1,
  "customerName": "Asha Verma",
  "stars": 5,
  "text": "Good bass, and the battery really lasts a week.",
  "verifiedPurchase": true,
  "createdAt": "2026-10-15T11:18:36.541285Z"
}
```

### Case 2: Vikram, delivered, 3 stars

**Why:** `201`.

Request

``` code
POST /products/1/reviews HTTP/1.1
Content-Type: application/json

{
  "customerId": 2,
  "stars": 3,
  "text": "Comfortable, but the case feels cheap."
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 160

{
  "id": 2,
  "customerName": "Vikram Rao",
  "stars": 3,
  "text": "Comfortable, but the case feels cheap.",
  "verifiedPurchase": true,
  "createdAt": "2026-10-15T11:18:36.630827Z"
}
```

### Case 3: the rating

**Why:** (5 + 3) ÷ 2 = 4.0, read from the stored row.

Request

``` code
GET /products/1/rating HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 50

{
  "productId": 1,
  "reviewCount": 2,
  "averageStars": 4.0
}
```

### Case 4: Asha posts again

**Why:** one review per customer: `409`.

Request

``` code
POST /products/1/reviews HTTP/1.1
Content-Type: application/json

{
  "customerId": 1,
  "stars": 5,
  "text": "Still love them!"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Customer 1 has already reviewed product 1.",
  "instance": "/products/1/reviews",
  "status": 409,
  "title": "Already reviewed"
}
```

### Case 5: Neha, order not delivered

**Why:** not verified yet: `422`.

Request

``` code
POST /products/1/reviews HTTP/1.1
Content-Type: application/json

{
  "customerId": 3,
  "stars": 1,
  "text": "Not here yet."
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "Customer 3 has no delivered order of product 1.",
  "instance": "/products/1/reviews",
  "status": 422,
  "title": "Not a verified purchase"
}
```

### Case 6: the first page

**Why:** newest first; the count comes from the stored row, not a count query.

Request

``` code
GET /products/1/reviews?page=0 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 399

{
  "productId": 1,
  "page": 0,
  "reviewCount": 2,
  "reviews": [
    {
      "id": 2,
      "customerName": "Vikram Rao",
      "stars": 3,
      "text": "Comfortable, but the case feels cheap.",
      "verifiedPurchase": true,
      "createdAt": "2026-10-15T11:18:36.630827Z"
    },
    {
      "id": 1,
      "customerName": "Asha Verma",
      "stars": 5,
      "text": "Good bass, and the battery really lasts a week.",
      "verifiedPurchase": true,
      "createdAt": "2026-10-15T11:18:36.541285Z"
    }
  ],
  "hasNext": false
}
```

### Case 7: product 99

**Why:** `404`.

Request

``` code
GET /products/99/rating HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No product 99.",
  "instance": "/products/99/rating",
  "status": 404,
  "title": "Product not found"
}
```

### Case 8: the water bottle, after 200,000 reviews

**Why:** the same one-row read, however many reviews; plans below.

Request

``` code
GET /products/2/rating HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 55

{
  "productId": 2,
  "reviewCount": 200000,
  "averageStars": 4.1
}
```

## Two ways to get the bottle's rating

After the requests above, 200,000 reviews of the water bottle were written straight to the tables and its stored totals backfilled from them once. Then PostgreSQL ran both queries with `EXPLAIN ANALYZE` (`docs/captures/plans.txt`). Timings are from this one run on the build machine.

``` code
-- The old rating: recomputed from every review, on every product page view
                                           QUERY PLAN                                           
------------------------------------------------------------------------------------------------
 Finalize Aggregate (actual time=26.421..32.551 rows=1 loops=1)
   ->  Gather (actual time=26.193..32.528 rows=2 loops=1)
         Workers Planned: 1
         Workers Launched: 1
         ->  Partial Aggregate (actual time=22.675..22.676 rows=1 loops=2)
               ->  Parallel Seq Scan on reviews (actual time=0.021..13.737 rows=100000 loops=2)
                     Filter: (product_id = 2)
                     Rows Removed by Filter: 1
 Planning Time: 1.281 ms
 Execution Time: 32.708 ms
(10 rows)

-- The stored rating: one row by primary key
                                             QUERY PLAN                                             
----------------------------------------------------------------------------------------------------
 Index Scan using product_ratings_pkey on product_ratings (actual time=0.045..0.045 rows=1 loops=1)
   Index Cond: (product_id = 2)
 Planning Time: 0.603 ms
 Execution Time: 0.150 ms
(4 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                               | What happens                            | Proved by                                               |
|------------------------------------------------------------------------------------|-----------------------------------------|---------------------------------------------------------|
| Two verified buyers review                                                         | Count 2, average 3.5 for 5 and 2 stars  | `aVerifiedBuyerReviewsOnceAndTheRatingMoves`            |
| The same customer again                                                            | `409`, still one review                 | `theSameCustomerCannotReviewTwice`                      |
| Not delivered, never bought, bought another product                                | `422`, rating untouched                 | `onlyDeliveredPurchasesCount`                           |
| 11 reviews                                                                         | 10 on page 0, 1 on page 1, newest first | `reviewsComeNewestFirstTenAPage`                        |
| Bad stars, text, customer, page                                                    | `400`                                   | `badReviewsAndPagesAre400`                              |
| Unknown product                                                                    | `404` on all three endpoints            | `unknownProductsAre404`                                 |
| Duplicate, bad stars, someone else's purchase, impossible totals, written directly | Refused by named constraints            | `namedConstraintsHoldWithoutJava`                       |
| The totals row cannot be updated                                                   | The review is not saved either          | `whenTheTotalsCannotBeUpdatedTheReviewIsNotSavedEither` |
| 20 buyers at the same moment                                                       | All 20 counted; stored equals a recount | `twentyBuyersPostingAtOnceAreAllCounted`                |
| One buyer 10 times at the same moment                                              | One `201`, nine `409`                   | `oneCustomerPostingTenTimesAtOnceGetsOneReview`         |

## The trap

Plausible but wrong

Recomputing the average over millions of rows on every page view.

The test writes 50,000 reviews of one product straight to the tables, then asks PostgreSQL itself, with `EXPLAIN ANALYZE`, how many rows each way reads. The old JPQL average reads every review of the product; the stored rating reads one row. Both give 4.1. The test counts rows, not milliseconds, so it does not depend on the machine.

The second test checks the price of storing: after posts through the API, the stored totals must equal a recount. A stored aggregate is only worth having while every write keeps it right.

While building, each part was undone once. Without the stored-total update, 7 tests turned red; without the "delivered" condition, 1; without turning the unique violation into `409`, 1 (ten posts at once gave `500`s). Removing the "already reviewed?" check before the insert turned none red: the unique index already answers `409`; the check only saves a failed insert. The trap's own cleanup found a missing index: deleting 200,000 test customers took 76 seconds because each foreign-key check scanned the purchases table.

``` code
package com.kartwala.reviews;

import jakarta.persistence.EntityManager;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * The first test written for this station: the old rating, an average over every review row, recomputed on every
 * product page view. 50,000 reviews of the water bottle (product 2) are written straight to the tables, and
 * PostgreSQL's own EXPLAIN ANALYZE counts the rows each way reads. Row counts, not timings, so the test is stable.
 */
class RecomputedAverageTrapTest extends ApiTest {

    static final int REVIEWS = 50_000;   // enough to see the shape; docs/captures/plans.txt runs 200,000

    @Autowired
    EntityManager entities;
    @Autowired
    TransactionTemplate transaction;
    @Autowired
    JsonMapper json;

    void fiftyThousandReviews() {
        jdbc.sql("INSERT INTO customers (id, name) SELECT 1000 + g, 'Buyer ' || g FROM generate_series(1, ?) g").param(REVIEWS).update();
        jdbc.sql("INSERT INTO purchases (id, customer_id, product_id, delivered_on) SELECT 1000 + g, 1000 + g, 2, DATE '2026-01-01' FROM generate_series(1, ?) g").param(REVIEWS).update();
        // Half five stars, 30% four, 20% two: an average of exactly 4.1.
        jdbc.sql("""
                INSERT INTO reviews (product_id, customer_id, purchase_id, stars, text, created_at)
                SELECT 2, 1000 + g, 1000 + g, CASE WHEN g % 10 < 5 THEN 5 WHEN g % 10 < 8 THEN 4 ELSE 2 END, 'Keeps water cold', now()
                FROM generate_series(1, ?) g""").param(REVIEWS).update();
        // The stored aggregate, backfilled once from the rows, as a migration would when the fix ships.
        jdbc.sql("UPDATE product_ratings SET (review_count, star_total) = (SELECT count(*), sum(stars) FROM reviews WHERE product_id = 2) WHERE product_id = 2").update();
        jdbc.sql("ANALYZE reviews").update();
    }

    /** Rows every scan in the plan really read, one process only (no parallel workers), from EXPLAIN ANALYZE. */
    long rowsRead(String sql) {
        return transaction.execute(status -> {
            jdbc.sql("SET LOCAL max_parallel_workers_per_gather = 0").update();
            String plan = jdbc.sql("EXPLAIN (ANALYZE, FORMAT JSON) " + sql).query(String.class).single();
            return scanned(json.readTree(plan).get(0).get("Plan"));
        });
    }

    static long scanned(JsonNode node) {
        long rows = node.get("Node Type").asString().contains("Scan") ? node.get("Actual Rows").asLong() * node.get("Actual Loops").asLong() : 0;
        if (node.has("Plans")) {
            for (JsonNode child : node.get("Plans")) {
                rows += scanned(child);
            }
        }
        return rows;
    }

    @Test
    void theOldAverageReadsEveryReviewTheStoredOneReadsOneRow() throws Exception {
        fiftyThousandReviews();
        // The old product page: JPQL average and count over the reviews, on every view.
        Object[] old = transaction.execute(status -> (Object[]) entities.createQuery(
                "SELECT avg(r.stars), count(r) FROM Review r WHERE r.product.id = 2").getSingleResult());
        assertThat((Double) old[0]).isEqualTo(4.1, org.assertj.core.data.Offset.offset(1e-9));
        assertThat(rowsRead("SELECT avg(stars), count(*) FROM reviews WHERE product_id = 2")).isEqualTo(REVIEWS);

        // The fix: the same answer, from one row.
        mvc.perform(get("/products/2/rating")).andExpect(jsonPath("$.reviewCount").value(REVIEWS)).andExpect(jsonPath("$.averageStars").value(4.1));
        assertThat(rowsRead("SELECT review_count, star_total FROM product_ratings WHERE product_id = 2")).isEqualTo(1);
    }

    @Test
    void storedAndRecomputedAgreeAfterPostsThroughTheApi() throws Exception {
        review(1, 1, 5);
        review(1, 2, 4);
        Object[] recount = transaction.execute(status -> (Object[]) entities.createQuery(
                "SELECT count(r), sum(r.stars) FROM Review r WHERE r.product.id = 1").getSingleResult());
        assertThat(recount).containsExactly(2L, 9L);
        mvc.perform(get("/products/1/rating")).andExpect(jsonPath("$.reviewCount").value(2)).andExpect(jsonPath("$.averageStars").value(4.5));
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
./mvnw test                 # all 12 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Load the 200,000 reviews from `docs/capture.sh` into your local database (the `psql` block), then compare the two plans:

``` code
docker compose exec postgres psql -U kartwala -d kartwala -c "EXPLAIN ANALYZE SELECT avg(stars), count(*) FROM reviews WHERE product_id = 2"
docker compose exec postgres psql -U kartwala -d kartwala -c "EXPLAIN ANALYZE SELECT * FROM product_ratings WHERE product_id = 2"
```

The first reads every review of the bottle; the second reads one row, and stays one row however many reviews arrive.

## Troubleshooting

| You see                                            | Cause                                                                           | Fix                                                                                      |
|----------------------------------------------------|---------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| `500` when the same review is posted twice at once | The unique violation is not mapped.                                             | Catch `DataIntegrityViolationException` for `reviews_one_per_customer` and answer `409`. |
| The stored count is lower than the rows            | A read, change, write update, or a write path that skips the totals.            | One atomic UPDATE in the same transaction; compare with a recount (challenge 2).         |
| Deleting many rows is very slow                    | A foreign key column without an index: each delete scans the referencing table. | Index the foreign key columns.                                                           |
| Paging shows a total but is slow                   | `Page` runs a `count(*)` per request.                                           | `Slice`, with the count from the stored row.                                             |
| `The column name stored_count was not found`       | `JdbcClient` maps columns to record fields by name.                             | Alias each column to the field name in snake case.                                       |

## Project layout

``` tree
stations/048-product-reviews-and-ratings/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/reviews/
│   ├── ReviewController.java   ├── ReviewDesk.java   ├── Repositories.java   ├── ProductRating.java
│   ├── Review.java   ├── Purchase.java   ├── Product.java   ├── Customer.java   └── ReviewsApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__products_purchases_reviews.sql, V2__demo_catalogue.sql
├── src/test/java/com/kartwala/reviews/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures (with query plans), saved runs
```

## Code walkthrough

In the order a request travels, then the entities and the database.

#### `src/main/java/com/kartwala/reviews/ReviewController.java`

Does  
Validates the review and the page number.

Why  
HTTP only.

Without it  
Stars or pages the database would have to refuse.

#### `src/main/java/com/kartwala/reviews/ReviewDesk.java`

Does  
Posts reviews with their totals; reads pages and ratings.

Why  
One transaction per post: the review and the totals, both or neither.

Without it  
A review without its stars counted, or counted twice.

- The "already reviewed?" check is a fast path; the unique index is the guarantee, and its violation becomes `409`.
- A page is a `Slice`: no `count(*)`; the count comes from the stored row.

#### `src/main/java/com/kartwala/reviews/Repositories.java`

Does  
The five repositories.

Why  
`addReview` is one atomic JPQL UPDATE.

Without it  
Read, add one, write back: two posts at once would both write the same new count.

#### `src/main/java/com/kartwala/reviews/ProductRating.java`

Does  
The stored aggregate: count and star total.

Why  
The average is computed when read, half up, one decimal.

Without it  
Floating-point averages stored and drifting.

#### `src/main/java/com/kartwala/reviews/Review.java`

A review, `@ManyToOne` to its product and customer (both LAZY).

#### `src/main/java/com/kartwala/reviews/Purchase.java`

A purchase; `deliveredOn` decides whether it counts.

#### `src/main/java/com/kartwala/reviews/Product.java`

A product.

#### `src/main/java/com/kartwala/reviews/Customer.java`

A customer.

#### `src/main/resources/db/migration/V1__products_purchases_reviews.sql`

All tables and named constraints, including the composite foreign key from a review to its purchase.

#### `src/main/resources/db/migration/V2__demo_catalogue.sql`

Three products, four customers, their purchases.

#### `src/main/resources/application.yaml`

open-in-view off; schema validation; decimals refused for whole-number fields.

#### `src/main/java/com/kartwala/reviews/ReviewsApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                      | Result |
|---------------|-------------------------------------------------------|---------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `ReviewContractTest` (6)        | pass   |
| Every station | Reproduce the failure before the fix                  | `RecomputedAverageTrapTest` (2) | pass   |
| Database      | Rollback and constraint tests against a real database | `ReviewDatabaseTest` (4)        | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.reviews.RecomputedAverageTrapTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.reviews.ReviewDatabaseTest
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.reviews.ReviewContractTest
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/kartwala/reviews/RecomputedAverageTrapTest.java`

Written first: rows read by the old and the stored rating, measured by PostgreSQL; stored equals recount.

#### `src/test/java/com/kartwala/reviews/ReviewContractTest.java`

Posting, paging, ratings, and every refusal.

#### `src/test/java/com/kartwala/reviews/ReviewDatabaseTest.java`

Named constraints, a review rolled back with its totals, and posts in parallel (virtual threads and a start latch).

#### `src/test/java/com/kartwala/reviews/ApiTest.java`

Shared setup: no reviews before each test; helpers for buyers and parallel calls.

#### `src/test/java/com/kartwala/reviews/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/kartwala/reviews/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=EditReviewChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 12 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 16 tests pass (12 station tests and 4 challenge tests). Without the row lock in the solution, the parallel edit test failed in both of two runs.

Challenge 1 · Go deeper · about 35 minutes

## Edit a review

Add `PUT /products/{id}/reviews/{reviewId}`: the author changes stars and text, and the stored total moves by the difference. Someone else's review is `403`; a missing one, or one of another product, `404`. Ten edits at once must leave the total equal to the review's final stars.

**Done when:** the three tests in `EditReviewChallengeTest` pass.

Hints

- `starTotal = starTotal + :delta`, where delta = new − old.
- Read the old stars under a row lock (`@Lock(PESSIMISTIC_WRITE)`), or two edits compute their deltas from the same old value.

#### `challenge/EditReviewChallengeTest.java`

``` code
package com.kartwala.reviews;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: PUT /products/{id}/reviews/{reviewId} with {"customerId", "stars", "text"} lets the author change their
 * review. The stored totals move by the difference in stars, in the same transaction. Someone else's review is 403;
 * a review that does not exist, or belongs to another product, is 404. Edits at the same moment must not drift.
 */
class EditReviewChallengeTest extends ApiTest {

    ResultActions edit(long product, long review, long customer, int stars) throws Exception {
        return mvc.perform(put("/products/{id}/reviews/{reviewId}", product, review).contentType(MediaType.APPLICATION_JSON)
                .content("{\"customerId\":%d,\"stars\":%d,\"text\":\"Changed my mind after a month.\"}".formatted(customer, stars)));
    }

    @Test
    void theAuthorChangesStarsAndTheAverageFollows() throws Exception {
        review(1, 1, 5);
        review(1, 2, 4);
        edit(1, 1, 1, 2).andExpect(status().isOk()).andExpect(jsonPath("$.stars").value(2));
        mvc.perform(get("/products/1/rating")).andExpect(content().json("{\"reviewCount\":2,\"averageStars\":3.0}"));
    }

    @Test
    void onlyTheAuthorAndOnlyThatProduct() throws Exception {
        review(1, 1, 5);
        edit(1, 1, 2, 1).andExpect(status().isForbidden());
        edit(2, 1, 1, 1).andExpect(status().isNotFound());
        edit(1, 99, 1, 1).andExpect(status().isNotFound());
        mvc.perform(get("/products/1/rating")).andExpect(jsonPath("$.averageStars").value(5.0));
    }

    @Test
    void editsAtTheSameMomentLeaveTotalsMatchingTheReview() throws Exception {
        review(1, 1, 5);
        List<Integer> statuses = together(10, () -> edit(1, 1, 1, 1 + (int) (Math.random() * 5)).andReturn().getResponse().getStatus());
        assertThat(statuses).containsOnly(200);
        assertThat(jdbc.sql("SELECT star_total FROM product_ratings WHERE product_id = 1").query(Long.class).single())
                .isEqualTo(jdbc.sql("SELECT stars FROM reviews WHERE id = 1").query(Long.class).single());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Beginner-friendly · about 25 minutes

## A drift report

Add `GET /admin/rating-drift`: every product whose stored count or total differs from a recount of its reviews, with both values. All is well when the list is empty.

**Done when:** the test in `RatingDriftChallengeTest` passes.

Hints

- One query: a `LEFT JOIN` from `product_ratings` to a grouped recount, keeping rows that differ.
- `coalesce` turns "no reviews" into 0.

#### `challenge/RatingDriftChallengeTest.java`

``` code
package com.kartwala.reviews;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /admin/rating-drift lists every product whose stored totals differ from a recount of its reviews:
 * productId, storedCount, storedTotal, actualCount, actualTotal, by product id. An empty list means all is well. It
 * reads every review, once, on purpose: a nightly check, not a page view.
 */
class RatingDriftChallengeTest extends ApiTest {

    @Test
    void storedTotalsThatDisagreeWithTheRowsAreListed() throws Exception {
        review(1, 1, 5);
        review(1, 2, 3);
        mvc.perform(get("/admin/rating-drift")).andExpect(status().isOk()).andExpect(content().json("[]", true));
        jdbc.sql("UPDATE product_ratings SET review_count = 3, star_total = 12 WHERE product_id = 1").update();   // a bad manual fix
        jdbc.sql("DELETE FROM reviews WHERE customer_id = 2").update();                                           // and a deleted row
        mvc.perform(get("/admin/rating-drift")).andExpect(content().json("""
                [{"productId":1,"storedCount":3,"storedTotal":12,"actualCount":1,"actualTotal":5}]""", true));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Where should the rating live?

Compare four places for the rating of a product with 2 million reviews: recomputed per view, a stored row updated per review (this station), a materialized view refreshed every 10 minutes, and a cache in front of the recompute. For each: how stale can it be, what does a write cost, and what happens when it is wrong?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: many rows, and the rows each way reads, measured by the database.
2.  Put both rules in the schema: a unique constraint, and a foreign key to the customer's purchase of the product.
3.  Store count and total; update them atomically in the review's transaction; backfill once from the rows.
4.  Prove stored equals recount, including under parallel posts.

## Design alternatives and trade-offs

| Approach                                         | What it costs                                                         | Verdict     |
|--------------------------------------------------|-----------------------------------------------------------------------|-------------|
| Stored count and total, atomic update per review | Every write path must update it.                                      | Chosen      |
| Recompute on every view                          | Reads every review per page view.                                     | The trap    |
| Read the row in Java, add, save                  | Two posts at once both save the same new count: a lost update.        | No          |
| A database trigger on `reviews`                  | Always in step, even for SQL writes; logic hidden from the Java code. | Valid       |
| Materialized view, refreshed on a schedule       | Stale between refreshes; a refresh still reads everything.            | For reports |

## Database design

| Table             | Constraints                                                                                                                               | Mapped as                                            |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------|
| `reviews`         | `reviews_one_per_customer`, `reviews_stars_range`, `reviews_text_not_blank`, `reviews_purchase_fk` (purchase, customer, product together) | `Review`, `@ManyToOne(LAZY)` to product and customer |
| `product_ratings` | `product_ratings_product_fk`, `product_ratings_totals_consistent` (count ≥ 0, count ≤ total ≤ 5 × count)                                  | `ProductRating`                                      |
| `purchases`       | `purchases_customer_fk`, `purchases_product_fk`, `purchases_id_customer_product_unique`; index on customer and product                    | `Purchase`                                           |

``` code
-- Kartwala reviews: only a customer with a purchase of the product may review it, once.
CREATE TABLE products (
    id   BIGINT PRIMARY KEY,
    name VARCHAR(120) NOT NULL
);

CREATE TABLE customers (
    id   BIGINT PRIMARY KEY,
    name VARCHAR(80) NOT NULL
);

CREATE TABLE purchases (
    id           BIGINT PRIMARY KEY,
    customer_id  BIGINT NOT NULL,
    product_id   BIGINT NOT NULL,
    delivered_on DATE,
    CONSTRAINT purchases_customer_fk FOREIGN KEY (customer_id) REFERENCES customers (id),
    CONSTRAINT purchases_product_fk FOREIGN KEY (product_id) REFERENCES products (id),
    CONSTRAINT purchases_id_customer_product_unique UNIQUE (id, customer_id, product_id)   -- target of reviews_purchase_fk
);

-- Serves the verified-purchase lookup, and the foreign key check when a customer row is deleted (without it, each
-- deleted customer scans the whole table: found when the trap test's cleanup took over a minute).
CREATE INDEX purchases_customer_product ON purchases (customer_id, product_id);

CREATE TABLE reviews (
    id          BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    product_id  BIGINT        NOT NULL,
    customer_id BIGINT        NOT NULL,
    purchase_id BIGINT        NOT NULL,
    stars       INT           NOT NULL,
    text        VARCHAR(2000) NOT NULL,
    created_at  TIMESTAMPTZ   NOT NULL,
    CONSTRAINT reviews_one_per_customer UNIQUE (product_id, customer_id),
    CONSTRAINT reviews_stars_range CHECK (stars BETWEEN 1 AND 5),
    CONSTRAINT reviews_text_not_blank CHECK (btrim(text) <> ''),
    -- The purchase must be this customer's purchase of this product. "Delivered" is checked in Java only.
    CONSTRAINT reviews_purchase_fk FOREIGN KEY (purchase_id, customer_id, product_id) REFERENCES purchases (id, customer_id, product_id)
);

CREATE INDEX reviews_product_newest ON reviews (product_id, id DESC);

-- The stored aggregate: one row per product, updated in the same transaction as each review.
CREATE TABLE product_ratings (
    product_id   BIGINT PRIMARY KEY,
    review_count INT    NOT NULL DEFAULT 0,
    star_total   BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT product_ratings_product_fk FOREIGN KEY (product_id) REFERENCES products (id),
    CONSTRAINT product_ratings_totals_consistent CHECK (review_count >= 0 AND star_total BETWEEN review_count AND 5 * review_count)
);
```

# 3 · Go deeper: Production

Backfill on release  
When the stored row ships, fill it once from the existing reviews, in a migration or a script, before the page starts reading it.

Check for drift  
Run a recount nightly (challenge 2) and alert when stored and actual differ. Manual SQL fixes and deleted rows are the usual causes.

Hot rows  
Every review of a bestseller updates one row. Thousands per second would queue on that row's lock; then count in shards or batch the updates.

Fake reviews  
Verified purchase and one per customer stop the obvious abuse, not paid reviewers with real orders. Moderation is a separate system.

Deep pages  
OFFSET pages slow down as the offset grows. For "load more", page by "reviews older than id X" instead.

# 3 · Go deeper: Interview

## Interview takeaways

When do you store an aggregate instead of computing it?

When it is read far more often than the rows change and computing it reads many rows. The cost moves to writes, and you must keep it correct: same transaction, atomic updates, and a recount check.

Why update the counter in SQL instead of in Java?

UPDATE ... SET n = n + 1 is atomic: PostgreSQL locks the row, so concurrent updates queue. Reading the entity, adding one and saving lets two transactions read the same value and both write it.

How do you enforce one review per customer?

A unique constraint on (product_id, customer_id). A check in Java first gives a clear message, but only the constraint holds under concurrency; map its violation to 409.

How can a foreign key enforce "only buyers review"?

Reference the purchase with (purchase_id, customer_id, product_id) against a unique key on the same three columns of purchases: the purchase must be that customer's purchase of that product.

Page or Slice in Spring Data?

Page runs an extra count query for the total; Slice fetches one extra row to know whether there is a next page. Use Slice when the total is known elsewhere or not needed.

## Self-check rubric

| Area        | Meets the bar                                   | Above the bar                                              |
|-------------|-------------------------------------------------|------------------------------------------------------------|
| Correctness | All 12 tests pass.                              | You compared the two plans yourself.                       |
| Integrity   | Unique constraint and purchase foreign key.     | You can explain what the database cannot check (delivery). |
| Aggregates  | Stored, updated atomically, in one transaction. | Backfill and drift check planned.                          |
| Concurrency | Parallel posts all counted.                     | You know when one hot row becomes the bottleneck.          |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any counter or summary:

- How many rows does the hottest read touch, measured, not guessed?
- Does every write path update the stored number, in the same transaction?
- Is the update one atomic statement, or read, change, write?
- Is there a recount that would notice drift?
