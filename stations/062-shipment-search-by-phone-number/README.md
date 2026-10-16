# Station 062 · Shipment search by phone number

Working Systems · 0–2 years · Core · Logistics · Types: Database

Spring Boot 4.1.1 · Java 25 · JdbcClient · PostgreSQL 17 B-tree indexes · EXPLAIN (ANALYZE, BUFFERS) · Flyway · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Shipments, phone numbers and airway bills are generated demo data (300,003 rows), not Dakroute's. Nothing is shipped or tracked.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 10 tests.

# 1 · Understand

## The problem in real life

1.  **A customer calls**

    "Where is my parcel? My number is +91 98765 43210, I sent it in March." Support searches by phone and dates.

2.  **Nine seconds**

    Phones were stored as typed, so the search cleaned them in SQL before comparing. Someone added an index on phone; the search stayed slow, because it compared a cleaned value, not the column.

3.  **The fix**

    Store phones as 10 digits, clean what support types in Java, and index (phone, booked_on) in that order. The same search touches 14 pages instead of 3014.

An index helps only a query that compares the indexed column itself. Check with EXPLAIN, not by hope.

## What are we building?

`GET /shipments/search?phone=…&from=…&to=…` returns a customer's shipments in a date range, newest first, from an index.

## An everyday analogy

A ledger sorted by phone number, and within each number by date. Finding "98765 43210 in March" is opening at that number and reading a few lines. A ledger sorted by date first means reading every line of March to find one number.

## How it works in 4 steps

1.  **Clean the phone** as support typed it: `+91 98765 43210` becomes `9876543210`.
2.  **Check the dates**: forwards, at most 366 days.
3.  **Search** the stored column: the index goes straight to that phone, then to the dates.
4.  **Return** at most 50, newest first.

Check yourself: the index is on (booked_on, phone). Why is "one phone, January to September" slow?

The index is sorted by date first. Every entry from January to September, for every phone, sits between the first and the last match, so PostgreSQL walks all of them to find the 3 that match: 1073 pages in the capture, against 14 for the right order.

## What this station is not

- **No tracking.** A shipment's status is a stored value.
- **No 30 million rows.** 300,003 demo rows show the same plans; the gap only grows with size.
- **No partial-number search.** "Last four digits" is Practice 3, on paper.

## Key terms

| Term                | Simple meaning                                                                | Everyday example                              | In this project                |
|---------------------|-------------------------------------------------------------------------------|-----------------------------------------------|--------------------------------|
| **Index**           | A sorted copy of some columns, pointing at the rows.                          | The index at the back of a book.              | `shipments_phone_booked_on`    |
| **B-tree**          | PostgreSQL's default index: sorted, so it finds one value or a range quickly. | A phone book sorted by name.                  | every index here               |
| **Composite index** | An index on several columns, sorted by the first, then the second.            | Sorted by surname, then first name.           | `(phone, booked_on)`           |
| **Sequential scan** | Reading every row of the table.                                               | Reading the whole book to find one word.      | the old search                 |
| **EXPLAIN ANALYZE** | Runs a query and shows the plan PostgreSQL chose and what it really did.      | A route with the actual traffic, not the map. | the tests and captures         |
| **Page**            | PostgreSQL reads and caches data 8 kB at a time.                              | One page of the book.                         | `Buffers: shared hit=… read=…` |

# 2 · Build: Spec

## Business problem

**Dakroute** (a fictional courier) has 30 million shipments. Support's search by phone and date took 9 seconds, with an index in place.

## Acceptance criteria

Demo data: 9876543210 has shipments on 2 March, 15 March and 20 May; seller 9123456789 has 30,000; 90,000 other customers have 3 each.

1.  **Given** 9876543210 and March, **then** the 15 March and 2 March shipments, in that order.
2.  **Given** `+91 98765 43210`, `098765-43210` or `(98765) 43210`, **then** the same customer.
3.  **Given** the seller and nine months, **then** the newest 50.
4.  **Given** no match, **then** `200` with an empty list.
5.  **Given** a number that is not an Indian mobile, dates backwards or over 366 days, a non-ISO date or a missing parameter, **then** `400`.
6.  **Given** the search's plan, **then** an index scan on `shipments_phone_booked_on` touching at most 10 pages.

## Requirements

- Phones are stored as 10 digits; a CHECK constraint refuses anything else.
- Typed phones are cleaned in Java, never in the `WHERE` clause.
- The index puts the equality column first, the range column second.
- No index without a query that uses it: each one slows every insert.

## Learning objectives

- Read `EXPLAIN (ANALYZE, BUFFERS)`: node types, index conditions, pages.
- Choose the column order of a composite index.
- Recognise a query that cannot use an index.
- Measure what an index costs on writes.

# 2 · Build: API contract

## Endpoint

| Method | Path                                                      | Purpose                                                                              |
|--------|-----------------------------------------------------------|--------------------------------------------------------------------------------------|
| `GET`  | `/shipments/search?phone=…&from=YYYY-MM-DD&to=YYYY-MM-DD` | `{phone, from, to, shipments: [{awb, bookedOn, status}]}`, newest first, at most 50. |

## Status codes

| Status | When                                                                                                                                              |
|--------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| 200    | Results, possibly an empty list                                                                                                                   |
| 400    | Not a 10-digit Indian mobile after cleaning, dates backwards or more than 366 days apart (demo rule), a date not in ISO form, a missing parameter |

## Captured examples

Captured with curl from the running app on 16 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: one customer, March

**Why:** two shipments, newest first.

Request

``` code
POST /shipments/search HTTP/1.1

to=2026-03-31
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 209

{
  "phone": "9876543210",
  "from": "2026-03-01",
  "to": "2026-03-31",
  "shipments": [
    {
      "awb": "DR1000000002",
      "bookedOn": "2026-03-15",
      "status": "RETURNED"
    },
    {
      "awb": "DR1000000001",
      "bookedOn": "2026-03-02",
      "status": "DELIVERED"
    }
  ]
}
```

### Case 2: `+91 98765 43210`, the whole year

**Why:** cleaned to the stored form; all three shipments.

Request

``` code
POST /shipments/search HTTP/1.1

to=2026-12-31
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 278

{
  "phone": "9876543210",
  "from": "2026-01-01",
  "to": "2026-12-31",
  "shipments": [
    {
      "awb": "DR1000000003",
      "bookedOn": "2026-05-20",
      "status": "IN_TRANSIT"
    },
    {
      "awb": "DR1000000002",
      "bookedOn": "2026-03-15",
      "status": "RETURNED"
    },
    {
      "awb": "DR1000000001",
      "bookedOn": "2026-03-02",
      "status": "DELIVERED"
    }
  ]
}
```

### Case 3: April

**Why:** no shipment: an empty list, not a 404.

Request

``` code
POST /shipments/search HTTP/1.1

to=2026-04-30
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 75

{
  "phone": "9876543210",
  "from": "2026-04-01",
  "to": "2026-04-30",
  "shipments": []
}
```

### Case 4: `12345`

**Why:** `400` before any query.

Request

``` code
POST /shipments/search HTTP/1.1

to=2026-03-31
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Not an Indian mobile number: 12345",
  "instance": "/shipments/search",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 5: 31 March to 1 March

**Why:** `400`.

Request

``` code
POST /shipments/search HTTP/1.1

to=2026-03-01
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "The dates must run forwards, at most 366 days",
  "instance": "/shipments/search",
  "status": 400,
  "title": "Bad Request"
}
```

## The search's plan

From `docs/capture.sh`: `EXPLAIN (ANALYZE, BUFFERS)` of the app's query in `psql`, against the demo data (`docs/captures/explain-the-search.txt`).

``` code
                                                                  QUERY PLAN                                                                  
----------------------------------------------------------------------------------------------------------------------------------------------
 Limit (actual rows=2 loops=1)
   Buffers: shared hit=14
   ->  Incremental Sort (actual rows=2 loops=1)
         Sort Key: booked_on DESC, id DESC
         Presorted Key: booked_on
         Full-sort Groups: 1  Sort Method: quicksort  Average Memory: 25kB  Peak Memory: 25kB
         Buffers: shared hit=14
         ->  Index Scan Backward using shipments_phone_booked_on on shipments (actual rows=2 loops=1)
               Index Cond: (((phone)::text = '9876543210'::text) AND (booked_on >= '2026-03-01'::date) AND (booked_on <= '2026-03-31'::date))
               Buffers: shared hit=5
 Planning:
   Buffers: shared hit=148
(12 rows)
```

`Index Scan Backward`: the index already holds the phone's shipments in date order, so PostgreSQL reads it from the end for "newest first". `Buffers: shared hit=14`: 14 pages, all in memory.

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                      | What happens                    | Proved by                                                |
|-----------------------------------------------------------|---------------------------------|----------------------------------------------------------|
| Three ways of typing one number                           | One customer                    | `thePhoneCanBeTypedTheWaysCustomersSayIt`                |
| A seller with 30,000 shipments                            | The newest 50                   | `theBusySellerGetsTheNewestFifty`                        |
| No shipment, or none in the range                         | Empty list                      | `noShipmentIsAnEmptyList`                                |
| Bad phone, dates, missing parameter, SQL in the phone     | `400`                           | `badSearchesAre400`                                      |
| The old cleaned-in-SQL search                             | Seq Scan; the index is ignored  | `theOldSearchCleanedThePhoneInSqlSoItsIndexWasNeverUsed` |
| No index, phone only, date first, phone then date         | Measured against each other     | `theColumnOrderOfTheIndexDecidesHowMuchIsRead`           |
| A typed phone or a duplicate airway bill written directly | Refused by named constraints    | `namedConstraintsHoldWithoutJava`                        |
| Indexes and inserts                                       | More WAL per row for each index | `everyIndexIsMoreWorkForEveryInsert`                     |

## The trap

Plausible but wrong

Adding an index without checking EXPLAIN, or in the wrong column order.

**The index nobody used.** The old query compared `right(regexp_replace(phone, '[^0-9]', '', 'g'), 10)`, a value computed from each row. A B-tree on `phone` is sorted by the stored text, not by that value, so PostgreSQL read all 300,003 rows (`Rows Removed by Filter: 300001`), 3014 pages:

``` code
                                                                                                 QUERY PLAN                                                                                                 
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
 Limit (actual rows=2 loops=1)
   Buffers: shared hit=3014
   ->  Sort (actual rows=2 loops=1)
         Sort Key: booked_on DESC, id DESC
         Sort Method: quicksort  Memory: 25kB
         Buffers: shared hit=3014
         ->  Seq Scan on old_shipments (actual rows=2 loops=1)
               Filter: ((booked_on >= '2026-03-01'::date) AND (booked_on <= '2026-03-31'::date) AND ("right"(regexp_replace((phone)::text, '[^0-9]'::text, ''::text, 'g'::text), 10) = '9876543210'::text))
               Rows Removed by Filter: 300001
               Buffers: shared hit=3008
 Planning:
   Buffers: shared hit=103 read=1
(12 rows)
```

**The wrong order.** With `(booked_on, phone)`, the search for one customer over nine months returned 3 entries but walked every entry in those dates: 1073 pages.

``` code
                                                                  QUERY PLAN                                                                  
----------------------------------------------------------------------------------------------------------------------------------------------
 Limit (actual rows=3 loops=1)
   Buffers: shared hit=17 read=1056
   ->  Incremental Sort (actual rows=3 loops=1)
         Sort Key: booked_on DESC, id DESC
         Presorted Key: booked_on
         Full-sort Groups: 1  Sort Method: quicksort  Average Memory: 25kB  Peak Memory: 25kB
         Buffers: shared hit=17 read=1056
         ->  Index Scan Backward using copy_date_phone on shipments_copy (actual rows=3 loops=1)
               Index Cond: ((booked_on >= '2026-01-01'::date) AND (booked_on <= '2026-09-30'::date) AND ((phone)::text = '9876543210'::text))
               Buffers: shared hit=8 read=1056
 Planning:
   Buffers: shared hit=117 read=6
(12 rows)
```

**Phone only.** `(phone)` is fine for most customers, who have a few shipments. For the seller, a week's search reads all 30,000 of their index entries, then filters and sorts; `(phone, booked_on)` reads fewer than 300. The test asserts both.

While building, each fix was undone once: no index turned 1 test red; the date-first index 1; no `+91` handling 1; no `LIMIT` 2; oldest first 2; no range check 1.

``` code
package com.dakroute.shipments;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Written first. The old search and the indexes people try first, measured with EXPLAIN (ANALYZE, BUFFERS) on copies
 * of the 300,003 demo shipments. Pages are 8 kB blocks PostgreSQL touched; fewer pages is less work.
 */
class PhoneSearchTrapTest extends ApiTest {

    static final LocalDate MARCH_1 = LocalDate.of(2026, 3, 1), MARCH_7 = LocalDate.of(2026, 3, 7), MARCH_31 = LocalDate.of(2026, 3, 31);
    static final LocalDate JAN_1 = LocalDate.of(2026, 1, 1), SEP_30 = LocalDate.of(2026, 9, 30);

    @AfterEach
    void dropCopies() {
        jdbc.sql("DROP TABLE IF EXISTS old_shipments, shipments_copy").update();
    }

    @Test
    void theOldSearchCleanedThePhoneInSqlSoItsIndexWasNeverUsed() {
        // The old table kept phones as typed, in three formats, with an index on phone that someone added.
        jdbc.sql("""
                CREATE TABLE old_shipments AS SELECT id, awb, CASE id % 3 WHEN 0 THEN '+91 ' || substr(phone, 1, 5) || ' ' || substr(phone, 6)
                    WHEN 1 THEN '0' || phone ELSE phone END AS phone, booked_on, status FROM shipments""").update();
        jdbc.sql("CREATE INDEX old_shipments_phone ON old_shipments (phone)").update();
        jdbc.sql("ANALYZE old_shipments").update();
        String old = ShipmentSearch.SQL.replace("FROM shipments", "FROM old_shipments")
                .replace("phone = :phone", "right(regexp_replace(phone, '[^0-9]', '', 'g'), 10) = :phone");
        assertThat(jdbc.sql(old).param("phone", CUSTOMER).param("from", MARCH_1).param("to", MARCH_31).param("limit", 50).query().listOfRows()).hasSize(2);

        Plan before = explain(old, CUSTOMER, MARCH_1, MARCH_31);
        Plan after = explainSearch("shipments", CUSTOMER, MARCH_1, MARCH_31);
        assertThat(before.nodes()).contains("Seq Scan");   // a function around the column: the index on phone cannot help
        assertThat(before.indexes()).isEmpty();
        assertThat(after.indexes()).containsOnly("shipments_phone_booked_on");
        assertThat(after.pages()).isLessThanOrEqualTo(10);
        assertThat(before.pages()).isGreaterThan(100 * after.pages());
    }

    @Test
    void theColumnOrderOfTheIndexDecidesHowMuchIsRead() {
        jdbc.sql("CREATE TABLE shipments_copy AS SELECT * FROM shipments").update();
        jdbc.sql("ANALYZE shipments_copy").update();
        Plan noIndex = explainSearch("shipments_copy", SELLER, MARCH_1, MARCH_7);

        jdbc.sql("CREATE INDEX copy_phone ON shipments_copy (phone)").update();   // phone only: all 30,000 of the seller's rows
        jdbc.sql("ANALYZE shipments_copy").update();
        Plan phoneOnly = explainSearch("shipments_copy", SELLER, MARCH_1, MARCH_7);
        jdbc.sql("DROP INDEX copy_phone").update();

        jdbc.sql("CREATE INDEX copy_date_phone ON shipments_copy (booked_on, phone)").update();   // range first: every phone in those dates
        jdbc.sql("ANALYZE shipments_copy").update();
        Plan dateFirst = explainSearch("shipments_copy", CUSTOMER, JAN_1, SEP_30);
        jdbc.sql("DROP INDEX copy_date_phone").update();

        jdbc.sql("CREATE INDEX copy_phone_date ON shipments_copy (phone, booked_on)").update();   // equality first, then range
        jdbc.sql("ANALYZE shipments_copy").update();
        Plan sellerWeek = explainSearch("shipments_copy", SELLER, MARCH_1, MARCH_7);
        Plan customerYear = explainSearch("shipments_copy", CUSTOMER, JAN_1, SEP_30);

        assertThat(noIndex.nodes()).contains("Seq Scan");
        assertThat(sellerWeek.indexes()).containsOnly("copy_phone_date");
        assertThat(customerYear.indexes()).containsOnly("copy_phone_date");
        assertThat(phoneOnly.indexRows()).isEqualTo(30_000);   // every one of the seller's entries, then filtered by date and sorted
        assertThat(sellerWeek.indexRows()).isLessThan(300);    // from 7 March backwards, stopping once 50 are certain
        assertThat(phoneOnly.pages()).isGreaterThan(2 * sellerWeek.pages());
        assertThat(dateFirst.pages()).isGreaterThan(10 * customerYear.pages());
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
./mvnw spring-boot:run      # the API on http://localhost:8080; the first start loads 300,003 shipments
./mvnw test                 # all 10 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Ask PostgreSQL for the plan, then drop the index and ask again:

``` code
docker compose exec postgres psql -U dakroute -d dakroute
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM shipments WHERE phone = '9876543210' AND booked_on BETWEEN '2026-03-01' AND '2026-03-31';
BEGIN; DROP INDEX shipments_phone_booked_on;
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM shipments WHERE phone = '9876543210' AND booked_on BETWEEN '2026-03-01' AND '2026-03-31';
ROLLBACK;
```

Index sizes from the capture (`docs/captures/sizes.txt`): each index is a sorted copy of its columns, and every insert writes to each one.

``` code
           name            | kind  |  size   
---------------------------+-------+---------
 shipments                 | table | 22 MB
 shipments_awb_unique      | index | 9264 kB
 shipments_phone_booked_on | index | 8560 kB
 shipments_pkey            | index | 6600 kB
(4 rows)
```

## Troubleshooting

| You see                                         | Cause                                                                                       | Fix                                                                                         |
|-------------------------------------------------|---------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| `Seq Scan` although an index exists             | The query wraps the column in a function or cast, or the table is tiny, or most rows match. | Compare the column as stored; for a function, an expression index on exactly that function. |
| `value too long for type character varying(10)` | A typed phone reached the database; the length check fires before the named CHECK.          | Clean in Java first. Found while building this station.                                     |
| Different plans on your laptop                  | Small tables, other statistics, other settings.                                             | Run `ANALYZE`, and test plans on realistic data volumes.                                    |
| Parallel workers in the plan                    | PostgreSQL split a big scan across processes.                                               | The tests set `max_parallel_workers_per_gather = 0` so pages are counted in one process.    |

## Project layout

``` tree
stations/062-shipment-search-by-phone-number/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/dakroute/shipments/
│   ├── ShipmentController.java   ├── PhoneNumber.java   ├── ShipmentSearch.java   └── ShipmentsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__shipments.sql, V2__demo_shipments.sql, V3__search_index.sql
├── src/test/java/com/dakroute/shipments/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/dakroute/shipments/ShipmentController.java`

Does  
Parses the dates and checks the range, then cleans the phone.

Why  
Every bad input is a `400` before the database.

Without it  
A two-year search walking a seller's whole history.

#### `src/main/java/com/dakroute/shipments/PhoneNumber.java`

Does  
Turns what support typed into the 10 digits the table stores.

Why  
The cleaning happens once, in Java, so SQL compares the column as stored.

Without it  
`regexp_replace` in the `WHERE` clause, and a sequential scan.

#### `src/main/java/com/dakroute/shipments/ShipmentSearch.java`

Does  
The search: equality on phone, a range on dates, newest 50.

Why  
Its shape matches the index, so the plan is an index scan read backwards.

Without it  
A sort of every matching row for the seller.

#### `src/main/resources/db/migration/V1__shipments.sql`

Does  
The table and its named constraints.

Why  
`shipments_phone_shape` keeps typed phones out for every writer.

Without it  
Old formats creeping back in from an import script.

#### `src/main/resources/db/migration/V2__demo_shipments.sql`

3 hand-written shipments and 300,000 generated ones.

#### `src/main/resources/db/migration/V3__search_index.sql`

Does  
The search index, built after the data, then `ANALYZE`.

Why  
Equality column first, range column second.

Without it  
A plan that reads every row.

#### `src/main/resources/application.yaml`

Problem details on.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/dakroute/shipments/ShipmentsApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                 | Result |
|---------------|-------------------------------------------------------|----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found (empty)      | `ShipmentContractTest` (5) | pass   |
| Every station | Reproduce the failure before the fix                  | `PhoneSearchTrapTest` (2)  | pass   |
| Database      | Rollback and constraint tests against a real database | `ShipmentDatabaseTest` (3) | pass   |

## How plans are tested

Timings vary from machine to machine; plans and page counts do not, for the same data. The tests run `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` without parallel workers and assert node types, index names, index entries returned and pages touched, always as comparisons ("more than 10 times") rather than exact page numbers. The write-cost test counts WAL records with `EXPLAIN (ANALYZE, WAL)`, inside a transaction that is rolled back.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.dakroute.shipments.ShipmentDatabaseTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.dakroute.shipments.ShipmentContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.dakroute.shipments.PhoneSearchTrapTest
[INFO] Tests run: 10, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/dakroute/shipments/PhoneSearchTrapTest.java`

Written first: the old search, and four index choices on a copy of the data.

#### `src/test/java/com/dakroute/shipments/ShipmentDatabaseTest.java`

Named constraints, a rolled-back batch, and WAL records per index.

#### `src/test/java/com/dakroute/shipments/ShipmentContractTest.java`

The endpoint through HTTP.

#### `src/test/java/com/dakroute/shipments/ApiTest.java`

Shared setup and the EXPLAIN reader.

#### `src/test/java/com/dakroute/shipments/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/dakroute/shipments/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=TrackByAwbChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 10 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 14 tests pass (10 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Track by airway bill

Add `GET /shipments/{awb}`: one shipment, the number in any case. Unknown is `404`; not `DR` plus 10 digits is `400`.

**Done when:** both tests in `TrackByAwbChallengeTest` pass.

Hints

- No new index: `shipments_awb_unique` is one.
- Upper-case with `Locale.ROOT`, then compare the column as stored.

#### `challenge/TrackByAwbChallengeTest.java`

``` code
package com.dakroute.shipments;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /shipments/{awb} returns {awb, bookedOn, status} for one airway bill number, in any case
 * ("dr1000000002" finds DR1000000002). An unknown number is 404; one that is not DR + 10 digits is 400.
 */
class TrackByAwbChallengeTest extends ApiTest {

    @Test
    void oneShipmentByItsNumber() throws Exception {
        mvc.perform(get("/shipments/dr1000000002")).andExpect(status().isOk())
                .andExpect(jsonPath("$.awb").value("DR1000000002")).andExpect(jsonPath("$.bookedOn").value("2026-03-15")).andExpect(jsonPath("$.status").value("RETURNED"));
    }

    @Test
    void unknownIs404AndMalformedIs400() throws Exception {
        mvc.perform(get("/shipments/DR0000000000")).andExpect(status().isNotFound());
        mvc.perform(get("/shipments/DR12")).andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Counts from the index alone

Add `GET /shipments/summary?phone&from&to`: shipments per status. The seller's month must be counted with an `Index Only Scan`.

**Done when:** both tests in `StatusSummaryChallengeTest` pass. After a stale build, run `./mvnw clean test`: a deleted migration can linger in `target/`.

Hints

- The count needs `status`; put it in the index's leaf entries with `INCLUDE (status)`, in a new migration.
- Replace the index under the same name, so nothing that refers to it changes.
- An index-only scan also needs the visibility map: the test runs `VACUUM` first, as autovacuum would.

#### `challenge/StatusSummaryChallengeTest.java`

``` code
package com.dakroute.shipments;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /shipments/summary?phone&from&to counts a phone's shipments per status, e.g. {"DELIVERED": 2}.
 * The busy seller asks for whole months, so the count must be answered from the index alone: an Index Only Scan,
 * never a visit to the table rows.
 */
class StatusSummaryChallengeTest extends ApiTest {

    @Test
    void countsPerStatus() throws Exception {
        mvc.perform(get("/shipments/summary").param("phone", "+91 98765 43210").param("from", "2026-01-01").param("to", "2026-12-31")).andExpect(status().isOk())
                .andExpect(jsonPath("$.DELIVERED").value(1)).andExpect(jsonPath("$.RETURNED").value(1)).andExpect(jsonPath("$.IN_TRANSIT").value(1));
    }

    @Test
    void theSellersMonthIsCountedFromTheIndexAlone() {
        jdbc.sql("VACUUM shipments").update();   // marks pages all-visible, which an index-only scan relies on
        Plan plan = explain("SELECT status, count(*) FROM shipments WHERE phone = :phone AND booked_on BETWEEN :from AND :to GROUP BY status",
                SELLER, LocalDate.of(2026, 3, 1), LocalDate.of(2026, 3, 31));
        assertThat(plan.nodes()).contains("Index Only Scan");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## "The last four digits are 3210"

Customers often remember only the end of their number. `phone LIKE '%3210'` cannot use a B-tree on `phone`. Compare: a stored `phone_last4` column with its own index (or an expression index on `right(phone, 4)`), a `pg_trgm` GIN index, and asking for the date and pin code too. How many rows does "3210" match in 30 million? Which option still needs another filter to be useful?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old query and its plan.
2.  Store phones in one form, guarded by a CHECK; clean input in Java.
3.  Try index orders on a copy of the data, and keep the one EXPLAIN prefers.
4.  Measure the write cost, and keep only indexes a query uses.

## Column order, the rule

Columns compared with `=` first, then at most one range column, then columns only needed for order. A B-tree is sorted by its first column: the entries for one phone sit together, and within them the dates are in order. With the range column first, the matches for one phone are scattered across every date in the range.

## Design alternatives and trade-offs

| Approach                                                   | What it costs                                                                                                                                  | Verdict     |
|------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------|-------------|
| Clean in Java, store 10 digits, index `(phone, booked_on)` | A CHECK constraint and a cleaning step.                                                                                                        | Chosen      |
| Clean in SQL with an index on `phone`                      | The index is never used.                                                                                                                       | The trap    |
| Index `(booked_on, phone)`                                 | Walks every entry in the date range.                                                                                                           | Wrong order |
| Index `(phone)` only                                       | Fine for most customers; reads a busy seller's whole history.                                                                                  | Almost      |
| Expression index on `right(regexp_replace(phone, …), 10)`  | Fixes the old query without cleaning the data; every query must repeat the exact expression.                                                   | A patch     |
| Two indexes, `(phone)` and `(booked_on)`                   | PostgreSQL can combine them with a bitmap AND, but reads more than one composite index would, and every insert writes both. Not measured here. | Not better  |

## Database design

| Object                                          | What                        | Why                                                      |
|-------------------------------------------------|-----------------------------|----------------------------------------------------------|
| `shipments_phone_shape`                         | CHECK `^[6-9][0-9]{9}$`     | One stored form, so the column can be compared directly. |
| `shipments_awb_unique`                          | UNIQUE (an index too)       | One shipment per airway bill; also Practice 1's lookup.  |
| `shipments_awb_shape`, `shipments_status_known` | CHECKs                      | No impossible values from any writer.                    |
| `shipments_phone_booked_on`                     | B-tree `(phone, booked_on)` | The search, read backwards for newest first.             |

``` code
CREATE TABLE shipments (
    id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    awb       VARCHAR(12) NOT NULL CONSTRAINT shipments_awb_unique UNIQUE
                                   CONSTRAINT shipments_awb_shape CHECK (awb ~ '^DR[0-9]{10}$'),
    -- Stored as 10 digits only, so a search compares the column itself and can use an index.
    phone     VARCHAR(10) NOT NULL CONSTRAINT shipments_phone_shape CHECK (phone ~ '^[6-9][0-9]{9}$'),
    booked_on DATE        NOT NULL,
    status    VARCHAR(20) NOT NULL CONSTRAINT shipments_status_known CHECK (status IN ('BOOKED', 'IN_TRANSIT', 'DELIVERED', 'RETURNED'))
);
```

``` code
-- Equality column first, range column second: one phone's shipments sit together, in date order.
-- Built after the data is loaded; on a live table use CREATE INDEX CONCURRENTLY (see Production).
CREATE INDEX shipments_phone_booked_on ON shipments (phone, booked_on);
ANALYZE shipments;
```

# 3 · Go deeper: Production

Building an index on a live table  
Plain `CREATE INDEX` blocks writes until it finishes. On a busy table use `CREATE INDEX CONCURRENTLY`, which cannot run inside a transaction: Flyway needs that migration marked to run outside one.

Cleaning old data  
Before the CHECK constraint, existing rows must be cleaned in batches; add the constraint `NOT VALID`, then `VALIDATE CONSTRAINT`, to avoid a long lock.

Unused indexes  
`pg_stat_user_indexes.idx_scan` shows how often each index is used. An index at 0 for months still costs every insert.

Phone numbers are personal data  
Support search should be logged and limited to support staff.

# 3 · Go deeper: Interview

## Interview takeaways

How do you check whether a query uses an index?

EXPLAIN shows the plan; EXPLAIN (ANALYZE, BUFFERS) runs it and shows the rows and pages each step really touched.

Why would PostgreSQL ignore an index?

The query compares a function of the column, a cast or a different type; most rows match anyway; the table is tiny; or the statistics are stale.

How do you order columns in a composite index?

Equality columns first, then one range column, then columns only used for ordering; the index is sorted by the first column.

What does an index cost?

Space, and work on every insert and on updates of its columns: each one is written and WAL-logged too.

Index scan, bitmap scan, index-only scan?

Index scan: walk the index, visit each row. Bitmap: collect row locations, then read pages in order. Index-only: every needed column is in the index and the pages are all-visible, so the table is not read.

## Self-check rubric

| Area         | Meets the bar                                  | Above the bar                          |
|--------------|------------------------------------------------|----------------------------------------|
| Correctness  | All 10 tests pass.                             | You read each saved plan line by line. |
| EXPLAIN      | Can tell a sequential scan from an index scan. | Uses BUFFERS to compare plans.         |
| Index design | Equality first, range second.                  | Knows when phone-only is enough.       |
| Write cost   | Knows each index slows inserts.                | Has measured it.                       |

# 3 · Go deeper: Review

## No reviewer view for this station

This station has no flawed version to review. Use this checklist on any new index or search query:

- Is there an EXPLAIN (ANALYZE, BUFFERS) of the query, on realistic data, in the pull request?
- Does the `WHERE` compare columns as stored, with no function or cast around them?
- Are equality columns before the range column in the index?
- Which query uses each index, and is that worth its write cost?
