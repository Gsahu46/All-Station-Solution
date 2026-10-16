# Station 065 · Seller catalog pages

Working Systems · 0–2 years · Core · E-commerce · Types: Database

Spring Boot 4.1.1 · Java 25 · Spring Data JPA Pageable, Page, Slice · PagedModel · DTO projections · PostgreSQL 17 · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Sellers and products are demo data, not Kartwala's. The seller comes from a request header instead of a login.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 11 tests.

# 1 · Understand

## The problem in real life

1.  **A seller checks their catalog**

    Sharma Electronics has 2,000 products, many at the same price. They page through, cheapest first.

2.  **Repeats and gaps**

    A product seen on page 3 shows up again on page 7; another never shows at all. Nothing changed in the data: the database was free to order products with the same price any way it liked, and did so differently for each page.

3.  **The fix**

    Always end the sort with the product id. Then every product has one place, and each page continues exactly where the last one stopped.

A page is only well defined if the order is. End every sort with a unique column.

## What are we building?

`GET /seller/products?page=0&size=20&sort=pricePaise`: one page of the seller's own products, with the totals the screen shows.

## An everyday analogy

A class register sorted by surname. Three students are called Sharma; if the teacher lines them up differently every morning, "the fifth student" is a different child each day. Sort by surname, then roll number, and the fifth student is always the same one.

## How it works in 4 steps

1.  **Read page, size and sort** from the query string; a size above 100 becomes 100.
2.  **Check the sort** is one the catalog allows; add the id at the end.
3.  **Fetch the page** (`LIMIT`/`OFFSET`) and count all the seller's products.
4.  **Answer** with the rows and the page facts: number, size, total, pages.

Check yourself: nothing in the data changes between two page requests. How can a product still appear twice?

When many rows tie on the sort value, SQL allows them in any order, and PostgreSQL's choice depends on how many rows the query needs. Page 1 and page 2 are separate queries with different `OFFSET`s, so the ties can be ordered differently in each.

## What this station is not

- **No login.** The seller is a header; a real app takes it from the session.
- **No changing data.** Pages over a list that changes while you read are station 066 (keyset paging).
- **No editing.** Products are read only.

## Key terms

| Term                  | Simple meaning                                                                             | Everyday example                                         | In this project                 |
|-----------------------|--------------------------------------------------------------------------------------------|----------------------------------------------------------|---------------------------------|
| **Page**              | One slice of a long list, by number and size.                                              | Page 3 of a catalogue, 20 items a page.                  | `?page=2&size=20`               |
| **Pageable**          | Spring Data's page number, size and sort, built from the query string.                     | "Page 3, 20 per page, cheapest first."                   | the controller's parameter      |
| **Page vs Slice**     | A Page also counts all rows (for "page 3 of 100"); a Slice only knows whether more follow. | A book's page numbers against a scroll that keeps going. | `Page<ProductCard>`; Practice 1 |
| **Tie**               | Two rows with the same value in the sort column.                                           | Two products at Rs 499.                                  | 200 products per price          |
| **Stable order**      | Every row has exactly one position, every time.                                            | Sort by price, then by product number.                   | `…, id` appended to every sort  |
| **Maximum page size** | The largest page the server will build.                                                    | "At most 100 per page."                                  | `max-page-size: 100`            |

# 2 · Build: Spec

## Business problem

**Kartwala** (a fictional marketplace) has sellers with 80,000 products. While paging, items repeated and vanished.

## Acceptance criteria

Demo data: seller 7 has 2,000 products at 10 prices (200 each); seller 8 has 30.

1.  **Given** no parameters, **then** 20 products by name, with `totalElements` 2000 and `totalPages` 100.
2.  **Given** every page of 20 sorted by price, **then** every product exactly once.
3.  **Given** `size=5000`, **then** 100 products, and the response says the size was 100.
4.  **Given** a page past the end, **then** an empty page, still with the totals.
5.  **Given** a sort by any other field, or no seller header, **then** `400`; an unknown seller `404`.

## Requirements

- Every sort ends with `id`.
- Only whitelisted fields can be sorted on, each backed by an index ending in `id`.
- A page never holds more than 100 products.
- A seller only ever sees their own products.

## Learning objectives

- Use Spring Data's `Pageable`, `Page` and `PagedModel`.
- Explain why a sort on a non-unique column breaks paging, and fix it.
- Choose between `Page` and `Slice`.
- Know what Spring Data does silently: the size cap and annotation defaults.

# 2 · Build: API contract

## Endpoint

| Parameter            | Form                                                     | Notes                                       |
|----------------------|----------------------------------------------------------|---------------------------------------------|
| `X-Seller-Id` header | `7`                                                      | demo stand-in for the logged-in seller      |
| `page`               | 0, 1, 2, …                                               | counted from 0                              |
| `size`               | 1 to 100, default 20                                     | more than 100 becomes 100                   |
| `sort`               | `name` (default), `pricePaise`, `createdOn`; add `,desc` | others are `400`; `id` is always added last |

Response: `{content: [{id, name, pricePaise, createdOn}], page: {size, number, totalElements, totalPages}}`.

## Status codes

| Status | When                                                                    |
|--------|-------------------------------------------------------------------------|
| 200    | A page, possibly empty                                                  |
| 400    | A sort field not on the list; the seller header missing or not a number |
| 404    | No such seller                                                          |

## Captured examples

Captured with curl from the running app on 16 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: seller 8, three per page

**Why:** the page facts next to the rows.

Request

``` code
GET /seller/products?size=3 HTTP/1.1
X-Seller-Id: 8
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 302

{
  "content": [
    {
      "id": 2001,
      "name": "Saree 01",
      "pricePaise": 251000,
      "createdOn": "2026-02-02"
    },
    {
      "id": 2002,
      "name": "Saree 02",
      "pricePaise": 252000,
      "createdOn": "2026-02-03"
    },
    {
      "id": 2003,
      "name": "Saree 03",
      "pricePaise": 253000,
      "createdOn": "2026-02-04"
    }
  ],
  "page": {
    "size": 3,
    "number": 0,
    "totalElements": 30,
    "totalPages": 10
  }
}
```

### Case 2: seller 7, dearest first, page 1

**Why:** 200 products tie at the top price; id decides their order.

Request

``` code
GET /seller/products?sort=pricePaise,desc&size=3&page=1 HTTP/1.1
X-Seller-Id: 7
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 308

{
  "content": [
    {
      "id": 37,
      "name": "Product 0037",
      "pricePaise": 19000,
      "createdOn": "2026-02-07"
    },
    {
      "id": 47,
      "name": "Product 0047",
      "pricePaise": 19000,
      "createdOn": "2026-02-17"
    },
    {
      "id": 57,
      "name": "Product 0057",
      "pricePaise": 19000,
      "createdOn": "2026-01-08"
    }
  ],
  "page": {
    "size": 3,
    "number": 1,
    "totalElements": 2000,
    "totalPages": 667
  }
}
```

### Case 3: `size=5000`

**Why:** cut to 100 without an error; `page.size` tells the client.

Request

``` code
GET /seller/products?size=5000 HTTP/1.1
X-Seller-Id: 8
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 2328

{
  "content": [
    {
      "id": 2001,
      "name": "Saree 01",
      "pricePaise": 251000,
      "createdOn": "2026-02-02"
    },
    {
      "id": 2002,
      "name": "Saree 02",
      "pricePaise": 252000,
      "createdOn": "2026-02-03"
    },
    {
      "id": 2003,
      "name": "Saree 03",
      "pricePaise": 253000,
      "createdOn": "2026-02-04"
    },
    {
      "id": 2004,
      "name": "Saree 04",
      "pricePaise": 254000,
      "createdOn": "2026-02-05"
    },
    {
      "id": 2005,
      "name": "Saree 05",
      "pricePaise": 255000,
      "createdOn": "2026-02-06"
    },
    {
      "id": 2006,
      "name": "Saree 06",
      "pricePaise": 256000,
      "createdOn": "2026-02-07"
    },
    {
      "id": 2007,
      "name": "Saree 07",
      "pricePaise": 257000,
      "createdOn": "2026-02-08"
    },
    {
      "id": 2008,
      "name": "Saree 08",
      "pricePaise": 258000,
      "createdOn": "2026-02-09"
    },
    {
      "id": 2009,
      "name": "Saree 09",
      "pricePaise": 259000,
      "createdOn": "2026-02-10"
    },
    {
      "id": 2010,
      "name": "Saree 10",
      "pricePaise": 260000,
      "createdOn": "2026-02-11"
    },
    {
      "id": 2011,
      "name": "Saree 11",
      "pricePaise": 261000,
      "createdOn": "2026-02-12"
    },
    {
      "id": 2012,
      "name": "Saree 12",
      "pricePaise": 262000,
      "createdOn": "2026-02-13"
    },
    {
      "id": 2013,
      "name": "Saree 13",
      "pricePaise": 263000,
      "createdOn": "2026-02-14"
    },
    {
      "id": 2014,
      "name": "Saree 14",
      "pricePaise": 264000,
      "createdOn": "2026-02-15"
    },
    {
      "id": 2015,
      "name": "Saree 15",
      "pricePaise": 265000,
      "createdOn": "2026-02-16"
    },
    {
      "id": 2016,
      "name": "Saree 16",
      "pricePaise": 266000,
      "createdOn": "2026-02-17"
    },
    {
      "id": 2017,
      "name": "Saree 17",
      "pricePaise": 267000,
      "createdOn": "2026-02-18"
    },
    {
      "id": 2018,
      "name": "Saree 18",
      "pricePaise": 268000,
      "createdOn": "2026-02-19"
    },
    {
      "id": 2019,
      "name": "Saree 19",
      "pricePaise": 269000,
      "createdOn": "2026-02-20"
    },
    {
      "id": 2020,
      "name": "Saree 20",
      "pricePaise": 270000,
      "createdOn": "2026-02-21"
    },
    {
      "id": 2021,
      "name": "Saree 21",
      "pricePaise": 271000,
      "createdOn": "2026-02-22"
    },
    {
      "id": 2022,
      "name": "Saree 22",
      "pricePaise": 272000,
      "createdOn": "2026-02-23"
    },
    {
      "id": 2023,
      "name": "Saree 23",
      "pricePaise": 273000,
      "createdOn": "2026-02-24"
    },
    {
      "id": 2024,
      "name": "Saree 24",
      "pricePaise": 274000,
      "createdOn": "2026-02-25"
    },
    {
      "id": 2025,
      "name": "Saree 25",
      "pricePaise": 275000,
      "createdOn": "2026-02-26"
    },
    {
      "id": 2026,
      "name": "Saree 26",
      "pricePaise": 276000,
      "createdOn": "2026-02-27"
    },
    {
      "id": 2027,
      "name": "Saree 27",
      "pricePaise": 277000,
      "createdOn": "2026-02-28"
    },
    {
      "id": 2028,
      "name": "Saree 28",
      "pricePaise": 278000,
      "createdOn": "2026-03-01"
    },
    {
      "id": 2029,
      "name": "Saree 29",
      "pricePaise": 279000,
      "createdOn": "2026-03-02"
    },
    {
      "id": 2030,
      "name": "Saree 30",
      "pricePaise": 280000,
      "createdOn": "2026-03-03"
    }
  ],
  "page": {
    "size": 100,
    "number": 0,
    "totalElements": 30,
    "totalPages": 1
  }
}
```

### Case 4: `sort=sellerId`

**Why:** not on the list: `400`.

Request

``` code
GET /seller/products?sort=sellerId HTTP/1.1
X-Seller-Id: 7
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Sort by one of [createdOn, name, pricePaise]",
  "instance": "/seller/products",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 5: seller 99

**Why:** `404`.

Request

``` code
GET /seller/products HTTP/1.1
X-Seller-Id: 99
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No seller 99",
  "instance": "/seller/products",
  "status": 404,
  "title": "Not Found"
}
```

## The paging experiment

From `docs/capture.sh`: all 100 pages of 20 for seller 7, fetched with each `ORDER BY`, in `psql`, once with index scans switched off (PostgreSQL sorts) and once with them on (`docs/captures/paging-experiment.txt`). The two plans for page 4 come first.

``` code
                         QUERY PLAN                          
-------------------------------------------------------------
 Limit (actual rows=20 loops=1)
   ->  Sort (actual rows=80 loops=1)
         Sort Key: price_paise
         Sort Method: top-N heapsort  Memory: 30kB
         ->  Seq Scan on products (actual rows=2000 loops=1)
               Filter: (seller_id = 7)
               Rows Removed by Filter: 30
(7 rows)

                                       QUERY PLAN                                       
----------------------------------------------------------------------------------------
 Limit (actual rows=20 loops=1)
   ->  Index Only Scan using products_seller_price on products (actual rows=80 loops=1)
         Index Cond: (seller_id = 7)
         Heap Fetches: 80
(4 rows)

         plan: ORDER BY         | rows_shown | different_products | never_shown 
--------------------------------+------------+--------------------+-------------
 sorted: price, then id         |       2000 |               2000 |           0
 sorted: price only             |       2000 |               1616 |         384
 from the index: price, then id |       2000 |               2000 |           0
 from the index: price only     |       2000 |               2000 |           0
(4 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                     | What happens                      | Proved by                                                  |
|------------------------------------------|-----------------------------------|------------------------------------------------------------|
| No parameters                            | Page 0 of 20 by name, with totals | `theFirstPageByName`                                       |
| 200 products at one price                | Ordered by id within the price    | `sortedByPriceDearestFirstTiesByIdOnPageTwo`               |
| `size=5000`                              | 100, and the response says so     | `aSizeAbove100IsCutTo100AndTheResponseSaysSo`              |
| Past the last page; another seller       | Empty; only their own products    | `aPagePastTheEndIsEmptyAndAnotherSellersProductsNeverShow` |
| Unknown seller                           | `404`                             | `anUnknownSellerIs404`                                     |
| Unknown sort, SQL in the sort, no header | `400`                             | `aSortOutsideTheListOrNoSellerIs400`                       |
| Every page by price                      | Each product exactly once         | `withIdAsTheTieBreakerEveryProductAppearsExactlyOnce`      |
| Bad rows; a half-done upload             | Refused; rolled back              | `ProductDatabaseTest`                                      |

## The trap

Plausible but wrong

Sorting by a non-unique column, so items repeat or vanish between pages.

In the experiment above, when PostgreSQL sorted the rows, price alone showed 2000 rows but only 1616 different products: 384 were never shown. With `, id` added: 2000 different products, 0 missing.

Why: SQL leaves the order of tied rows undefined. When PostgreSQL sorts for `ORDER BY … LIMIT`, it keeps only the top rows it needs in a heap ("top-N heapsort" in the plan), and which tied rows make the top 20 depends on `LIMIT` plus `OFFSET`, so it differs per page. The data never changed.

**The trap within the trap.** With fresh statistics, PostgreSQL read the `(seller_id, price_paise, id)` index instead, and price alone showed 2000 different products, 0 missing: correct by luck of the plan. Found while building: a run without statistics lost products, a run with them did not. The trap test therefore switches index scans off inside its transaction, so the sort plan is used every time, and the fix must hold under any plan.

While building, each fix was undone once: no tie-breaker turned 2 tests red; no sort whitelist 1; no seller check 2; no maximum page size 1; `@PageableDefault` without a size 2.

``` code
package com.kartwala.sellerpages;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Slice;
import org.springframework.data.domain.Sort;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** Written first. Every page of seller 7's 2,000 products, sorted the old way and the new way. */
class UnstableSortTrapTest extends ApiTest {

    @Autowired
    ProductRepository products;
    @Autowired
    SellerCatalog catalog;
    @Autowired
    OldProducts old;
    @Autowired
    TransactionTemplate transaction;

    /**
     * Every page, as a seller would click through them, inside one transaction where PostgreSQL must sort rather
     * than read an index: the plan it picks whenever the statistics say so. With an index in (price, id) order the
     * ties happen to come out stable; nothing in SQL promises that.
     */
    private List<Long> everyPageSorted(java.util.function.IntFunction<Iterable<ProductCard>> page) {
        return transaction.execute(tx -> {
            jdbc.sql("SET LOCAL enable_indexscan = off").update();
            jdbc.sql("SET LOCAL enable_indexonlyscan = off").update();
            jdbc.sql("SET LOCAL enable_bitmapscan = off").update();
            List<Long> seen = new ArrayList<>();
            for (int p = 0; p < 100; p++) {
                page.apply(p).forEach(card -> seen.add(card.id()));
            }
            return seen;
        });
    }

    @Test
    void sortingByPriceAloneRepeatsSomeProductsAndNeverShowsOthers() {
        List<Long> seen = everyPageSorted(p -> products.findBySellerId(7, PageRequest.of(p, 20, Sort.by("pricePaise"))));   // the old code
        assertThat(seen).hasSize(2000);
        assertThat(new HashSet<>(seen)).hasSizeLessThan(2000);   // 2,000 rows shown, fewer distinct products: repeats, so others vanished
    }

    @Test
    void withIdAsTheTieBreakerEveryProductAppearsExactlyOnce() {
        List<Long> seen = everyPageSorted(p -> catalog.page(7, PageRequest.of(p, 20, Sort.by("pricePaise"))));
        assertThat(seen).hasSize(2000).doesNotHaveDuplicates();
    }

    @Test
    void aPageCountsEveryTimeASliceOnlyLooksOneRowAhead() {
        Counted<Page<ProductCard>> page = counting(() -> catalog.page(7, PageRequest.of(3, 20, Sort.by("name"))));
        Counted<Slice<ProductCard>> slice = counting(() -> old.findSliceBySellerId(7, PageRequest.of(3, 20, Sort.by("name", "id"))));
        assertThat(page.queries()).isEqualTo(3);    // does the seller exist, the rows, and the count
        assertThat(slice.queries()).isEqualTo(1);   // the rows only (21 of them, to know about a next page)
        assertThat(slice.result().getContent()).isEqualTo(page.result().getContent());
        assertThat(slice.result().hasNext()).isTrue();
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
./mvnw test                 # all 11 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Run the same page twice with different limits in `psql` and compare the tied rows:

``` code
docker compose exec postgres psql -U kartwala -d kartwala
SELECT id FROM products WHERE seller_id = 7 ORDER BY price_paise LIMIT 5 OFFSET 20;
SELECT id FROM products WHERE seller_id = 7 ORDER BY price_paise LIMIT 25;   -- are rows 21 to 25 the same five?
SELECT id FROM products WHERE seller_id = 7 ORDER BY price_paise, id LIMIT 5 OFFSET 20;
```

## Troubleshooting

| You see                                | Cause                                          | Fix                                                        |
|----------------------------------------|------------------------------------------------|------------------------------------------------------------|
| Pages of 10 although the default is 20 | `@PageableDefault` without `size` uses 10.     | Write the size in the annotation.                          |
| `size=500` returns 100 rows            | `max-page-size` caps it silently.              | Expected; read `page.size` in the response.                |
| A warning about serialising `PageImpl` | Returning a `Page` directly from a controller. | Return `PagedModel`, or set `serialization-mode: via-dto`. |
| `page=-1` gives page 0                 | Spring Data treats a negative page as 0.       | Expected; validate yourself if it must be a 400.           |

## Project layout

``` tree
stations/065-seller-catalog-pages/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/sellerpages/
│   ├── SellerProductController.java   ├── SellerCatalog.java   ├── ProductRepository.java   ├── ProductCard.java
│   ├── Product.java   ├── Seller.java   ├── SellerRepository.java   └── SellerPagesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__products.sql, V2__demo_products.sql
├── src/test/java/com/kartwala/sellerpages/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/kartwala/sellerpages/SellerProductController.java`

Does  
Takes the seller and a `Pageable`; answers a `PagedModel`.

Why  
Spring Data parses `page`, `size` and `sort`, and caps the size.

Without it  
Hand-parsed paging, and a `PageImpl` serialised as whatever its internals are.

- `@PageableDefault` has its own size, 10, which beats the configured default: the size is written out. Found while building this station.

#### `src/main/java/com/kartwala/sellerpages/SellerCatalog.java`

Does  
Checks the sort against the whitelist and the seller, then adds `id` to the sort.

Why  
One place where every page query gets its tie-breaker.

Without it  
Repeats and gaps; sorting on any field a caller names.

#### `src/main/java/com/kartwala/sellerpages/ProductRepository.java`

Does  
A derived query returning a `Page` of projections.

Why  
Spring Data writes the page query and the count query.

Without it  
Two hand-written queries that drift apart.

#### `src/main/java/com/kartwala/sellerpages/ProductCard.java`

The row as the catalog shows it: a DTO projection.

#### `src/main/java/com/kartwala/sellerpages/Product.java`

The entity behind the projection.

#### `src/main/java/com/kartwala/sellerpages/Seller.java`

A seller.

#### `src/main/java/com/kartwala/sellerpages/SellerRepository.java`

"Does this seller exist".

#### `src/main/resources/application.yaml`

Does  
The page size cap and the JSON shape of pages.

Why  
`max-page-size` protects the database; `via-dto` gives a stable response shape.

Without it  
`size=1000000` reading a whole catalog.

#### `src/main/resources/db/migration/V1__products.sql`

Does  
Tables, named constraints and one index per sort, each ending in `id`.

Why  
The page query reads the index in order and stops after the page.

Without it  
Sorting all of a seller's products for every page.

#### `src/main/resources/db/migration/V2__demo_products.sql`

Seller 7: 2,000 products at 10 prices. Seller 8: 30 sarees.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/kartwala/sellerpages/SellerPagesApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                   | Result |
|---------------|-------------------------------------------------------|------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `SellerPageContractTest` (6) | pass   |
| Every station | Reproduce the failure before the fix                  | `UnstableSortTrapTest` (3)   | pass   |
| Database      | Rollback and constraint tests against a real database | `ProductDatabaseTest` (2)    | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Hibernate 7.4, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.sellerpages.ProductDatabaseTest
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.sellerpages.SellerPageContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.sellerpages.UnstableSortTrapTest
[INFO] Tests run: 11, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/kartwala/sellerpages/UnstableSortTrapTest.java`

Written first: all 100 pages both ways, and a Page against a Slice, queries counted.

#### `src/test/java/com/kartwala/sellerpages/ProductDatabaseTest.java`

Named constraints and a rolled-back upload.

#### `src/test/java/com/kartwala/sellerpages/SellerPageContractTest.java`

The endpoint through HTTP.

#### `src/test/java/com/kartwala/sellerpages/OldProducts.java`

The same rows as a Slice, for the comparison.

#### `src/test/java/com/kartwala/sellerpages/ApiTest.java`

Shared setup and the query counter.

#### `src/test/java/com/kartwala/sellerpages/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/kartwala/sellerpages/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=InfiniteScrollChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 11 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 15 tests pass (11 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## A feed for endless scrolling

Add `GET /seller/products/feed`: `{content, number, size, hasNext}`, no totals, no count query, same sort rules.

**Done when:** both tests in `InfiniteScrollChallengeTest` pass.

Hints

- A repository method returning `Slice` fetches one extra row to know about `hasNext`.
- Move the sort checks into one private method both endpoints use.

#### `challenge/InfiniteScrollChallengeTest.java`

``` code
package com.kartwala.sellerpages;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /seller/products/feed?page&size&sort for the mobile app's endless list: {content, number, size,
 * hasNext}, no totals, so no count query. Same sort rules and the same stable order as the catalog.
 */
class InfiniteScrollChallengeTest extends ApiTest {

    @Test
    void aSliceKnowsOnlyWhetherMoreFollows() throws Exception {
        mvc.perform(get("/seller/products/feed").header("X-Seller-Id", 8).param("size", "20")).andExpect(status().isOk())
                .andExpect(jsonPath("$.content", hasSize(20))).andExpect(jsonPath("$.hasNext").value(true)).andExpect(jsonPath("$.totalElements").doesNotExist());
        mvc.perform(get("/seller/products/feed").header("X-Seller-Id", 8).param("size", "20").param("page", "1")).andExpect(status().isOk())
                .andExpect(jsonPath("$.content", hasSize(10))).andExpect(jsonPath("$.hasNext").value(false));
        mvc.perform(get("/seller/products/feed").header("X-Seller-Id", 8).param("sort", "sellerId")).andExpect(status().isBadRequest());
    }

    @Test
    void noCountQuery() {
        Counted<Long> counted = counting(() -> {
            try {
                mvc.perform(get("/seller/products/feed").header("X-Seller-Id", 7).param("page", "5")).andExpect(status().isOk());
            } catch (Exception e) {
                throw new IllegalStateException(e);
            }
            return 0L;
        });
        assertThat(counted.queries()).isEqualTo(2);   // does the seller exist, and the rows
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Back to the right page

Add `GET /seller/products/{id}/page?size&sort=pricePaise`: which page that product is on, so "edit, then back" returns there.

**Done when:** both tests in `WhichPageChallengeTest` pass.

Hints

- Count the rows before it in the same stable order: `price < p OR (price = p AND id < id)`; for descending, flip the price comparison.
- The page is that count divided by the size.

#### `challenge/WhichPageChallengeTest.java`

``` code
package com.kartwala.sellerpages;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /seller/products/{id}/page?size&sort=pricePaise (or pricePaise,desc) answers {productId, page}:
 * the page that product is on in the catalog's stable order, so "edit, then back to the list" returns to the right
 * page. Count the rows before it in SQL, never by reading the pages. Another seller's product is 404.
 */
class WhichPageChallengeTest extends ApiTest {

    @Test
    void thePageAProductIsOn() throws Exception {
        // Product 1 costs Rs 170: 1,400 products are cheaper, none of them cost the same with a smaller id.
        mvc.perform(get("/seller/products/1/page").header("X-Seller-Id", 7).param("size", "20").param("sort", "pricePaise")).andExpect(status().isOk())
                .andExpect(jsonPath("$.productId").value(1)).andExpect(jsonPath("$.page").value(70));
        mvc.perform(get("/seller/products/1/page").header("X-Seller-Id", 7).param("size", "20").param("sort", "pricePaise,desc")).andExpect(status().isOk())
                .andExpect(jsonPath("$.page").value(20));
        mvc.perform(get("/seller/products/507/page").header("X-Seller-Id", 7).param("size", "50").param("sort", "pricePaise,desc")).andExpect(status().isOk())
                .andExpect(jsonPath("$.page").value(1));
    }

    @Test
    void anotherSellersProductIs404() throws Exception {
        mvc.perform(get("/seller/products/2001/page").header("X-Seller-Id", 7).param("sort", "pricePaise")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## "Page 3 of 4,000" on 80,000 products

Every Page runs a `count(*)` over the seller's products. Compare: keeping the exact count (and how it grows with the catalog), PostgreSQL's estimate from `EXPLAIN` or `pg_class.reltuples`, a count cached per seller and updated on change, and a Slice that shows "more" instead of a total. What does the screen really need?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: every page, sorted by price only.
2.  Append `id` to every sort in one place.
3.  Whitelist sort fields, each with an index ending in `id`.
4.  Cap the page size, and return `PagedModel` for a stable JSON shape.

## Design alternatives and trade-offs

| Approach                                     | What it costs                                             | Verdict                |
|----------------------------------------------|-----------------------------------------------------------|------------------------|
| Pageable + whitelist + id tie-breaker + Page | A count query per page.                                   | Chosen                 |
| Sort by the requested column only            | Repeats and gaps.                                         | The trap               |
| Slice instead of Page                        | No totals; one query.                                     | For feeds (Practice 1) |
| Keyset (seek) paging                         | No page numbers; fast at any depth; stable under inserts. | Station 066            |
| Fetch everything, page in Java               | Reads the whole catalog per page.                         | Never                  |

## Database design

| Object                                                                  | What                                                       | Why                                                    |
|-------------------------------------------------------------------------|------------------------------------------------------------|--------------------------------------------------------|
| `products_name_per_seller`                                              | UNIQUE (seller_id, name); also the index for the name sort | Names are unique per seller, so this sort has no ties. |
| `products_seller_price`                                                 | (seller_id, price_paise, id)                               | The price sort, ties included.                         |
| `products_seller_created`                                               | (seller_id, created_on, id)                                | The date sort.                                         |
| `products_price_range`, `products_name_not_blank`, `products_seller_fk` | CHECKs and a foreign key                                   | No impossible rows.                                    |

``` code
CREATE TABLE sellers (
    id   BIGINT       PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE products (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    seller_id   BIGINT       NOT NULL CONSTRAINT products_seller_fk REFERENCES sellers (id),
    name        VARCHAR(120) NOT NULL CONSTRAINT products_name_not_blank CHECK (btrim(name) <> ''),
    price_paise INTEGER      NOT NULL CONSTRAINT products_price_range CHECK (price_paise BETWEEN 100 AND 10000000),
    created_on  DATE         NOT NULL,
    CONSTRAINT products_name_per_seller UNIQUE (seller_id, name)
);
-- One index per allowed sort, each ending in id: the order the page query asks for, already sorted.
CREATE INDEX products_seller_price ON products (seller_id, price_paise, id);
CREATE INDEX products_seller_created ON products (seller_id, created_on, id);
-- (seller_id, name) is already indexed by products_name_per_seller, and names are unique per seller.
```

# 3 · Go deeper: Production

Deep pages  
`OFFSET 79000` still reads 79,000 index entries before the page. Fine for sellers who page a little; for deep or endless paging use keyset (station 066).

The count  
`count(*)` for 80,000 rows on every page adds up. Cache it, estimate it, or use a Slice where the total is not needed.

Clients  
Clients must read `page.size` from the response, not assume the size they asked for was used.

Changing data  
An insert or delete between two requests still shifts every later page by one. A stable order fixes ties, not that.

# 3 · Go deeper: Interview

## Interview takeaways

Why do items repeat or vanish between pages?

Rows that tie on the sort value have no defined order; each page is a separate query, and the database may order the ties differently each time.

How do you make paging stable?

End every sort with a unique column, usually the id, and index the sort columns plus the id.

Page or Slice?

A Page runs a count to know the total and the number of pages; a Slice fetches one extra row to know whether more follow, and nothing else.

What does Spring Data do with size=5000?

Caps it at max-page-size (2000 by default; 100 here) without an error; the response's page size shows what was used.

Why not return a Page from a controller?

PageImpl's JSON is not a stable contract; PagedModel (or serialization-mode via-dto) gives a fixed {content, page} shape.

## Self-check rubric

| Area        | Meets the bar               | Above the bar                                   |
|-------------|-----------------------------|-------------------------------------------------|
| Correctness | All 11 tests pass.          | You ran the psql experiment yourself.           |
| Paging      | Id as the tie-breaker.      | Why top-N heapsort makes ties move.             |
| Spring Data | Pageable, Page, PagedModel. | The silent size cap and the annotation default. |
| Cost        | Knows a Page counts.        | When a Slice or keyset is better.               |

# 3 · Go deeper: Review

## No reviewer view for this station

This station has no flawed version to review. Use this checklist on any paged endpoint:

- Does every sort end with a unique column?
- Is there a maximum page size, and does the client learn the size used?
- Is each sortable field on a whitelist and in an index?
- Does the screen need the total, or would a Slice do?
