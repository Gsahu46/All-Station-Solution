# Station 060 · Inventory sync with MySQL upserts

Working Systems · 0–2 years · Core · Retail · Types: Database, Concurrency

Spring Boot 4.1.1 · Java 25 · JdbcClient · MySQL 8.4 InnoDB · INSERT … ON DUPLICATE KEY UPDATE · deadlock retry · virtual threads · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (MySQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Warehouses, SKUs and counts are demo data, not Basketo's. A sync writes stock rows; no warehouse system, scanner or order flow is involved.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 18 tests.

# 1 · Understand

## The problem in real life

1.  **The nightly job**

    Each warehouse sends its counts. For every SKU the job looks for its row: if there is none, it inserts one; otherwise it updates it.

2.  **Duplicates**

    The job timed out and was retried while the first run was still going. Both runs looked, both found nothing, both inserted: RICE-5KG twice, and the website summed them.

3.  **Deadlocks**

    A unique key and `SELECT … FOR UPDATE` stopped the duplicates. Then Bhiwandi and Hoskote synced new SKUs at the same time, and one of them failed every night with "Deadlock found".

Do not look and then write. Ask the database to write, and let its unique key decide.

## What are we building?

`PUT /warehouses/{id}/stock` takes a warehouse's counts and stores them: new SKUs get a row, known SKUs get the new count. Sending the same counts twice changes nothing.

## An everyday analogy

A shop register with one printed line per product. The old way: read the register, then walk off to write. Two clerks can both see no RICE line and both add one. The new way: hand the register "RICE: 35", and the register itself either fills the line or adds it, one clerk at a time.

## How it works in 4 steps

1.  **Check the body**: 1 to 1000 SKUs, each once, counts 0 to 1,000,000. SKUs are upper-cased.
2.  **Lock the warehouse**: a second sync of the same warehouse waits for the first.
3.  **Upsert** 500 rows per statement: insert, or on the unique key, update the count.
4.  **Commit** all of it, or none. If InnoDB still picks this sync as a deadlock victim, run it again.

Check yourself: Bhiwandi has RICE-5KG 40 and ATTA-10KG 12. It sends only RICE-5KG 35. What is stored?

RICE-5KG 35 (the count, not 40 + 35) and ATTA-10KG still 12. A snapshot only speaks for the SKUs it lists; Practice challenge 2 adds a "full" mode that zeroes the rest.

## What this station is not

- **No orders or reservations.** Counts only; selling against them is a later station.
- **No warehouse system.** The sync is a plain HTTP call with demo data.
- **No PostgreSQL code.** The PostgreSQL version is compared on paper (Design, Practice 3).

## Key terms

| Term           | Simple meaning                                                           | Everyday example                                                   | In this project                                 |
|----------------|--------------------------------------------------------------------------|--------------------------------------------------------------------|-------------------------------------------------|
| **SKU**        | Stock keeping unit: one product in one pack size.                        | Rice, 5 kg bag.                                                    | `RICE-5KG`                                      |
| **Snapshot**   | What a warehouse counted, for the SKUs it sends.                         | A stock-take sheet.                                                | the `PUT` body                                  |
| **Upsert**     | Insert the row, or update it if it is already there, in one statement.   | "Write 35 on the RICE line; add the line if there is none."        | `ON DUPLICATE KEY UPDATE`                       |
| **Unique key** | The database refuses a second row with the same values.                  | One line per product on the sheet.                                 | `stock_levels_warehouse_sku`                    |
| **Gap lock**   | InnoDB locks the space where a row would go, not just rows that exist.   | Reserving the empty shelf, not a box on it.                        | taken by `SELECT … FOR UPDATE` on a missing row |
| **Deadlock**   | Two transactions each wait for the other; InnoDB stops one (error 1213). | Two trolleys in one aisle, each waiting for the other to back out. | retried up to 3 times                           |

# 2 · Build: Spec

## Business problem

**Basketo** (a fictional grocery delivery company) syncs stock from its warehouses every night. The sync inserted duplicate rows on MySQL, and after a first fix, deadlocked when two warehouses synced together.

## Acceptance criteria

1.  **Given** a snapshot of new SKUs, **then** `200` and one row per SKU.
2.  **Given** a later snapshot with some of them, **then** those rows carry the new counts, and the others are unchanged.
3.  **Given** the same snapshot twice, **then** the same rows, never a duplicate.
4.  **Given** ten syncs of two warehouses at once on the same new SKUs, **then** all `200`, and exactly one row per SKU per warehouse.
5.  **Given** ten different snapshots of one warehouse at once, **then** every row ends up from the same snapshot.
6.  **Given** the same SKU twice in one body (in any case), **then** `422`; an unknown warehouse `404`; a malformed body `400`.

## Requirements

- One row per warehouse and SKU, guaranteed by a named unique key, not by a lookup.
- A snapshot is one transaction: a bad row anywhere leaves nothing behind.
- SKUs are normalised with `Locale.ROOT`; counts are whole units.
- A deadlock victim is run again (at most 3 attempts), and every one is logged.

## Learning objectives

- Write a multi-row `INSERT … ON DUPLICATE KEY UPDATE` with a row alias.
- Explain why select-then-insert duplicates rows, and why `FOR UPDATE` on a missing row deadlocks.
- Batch large writes in chunks, inside one transaction.
- Know where MySQL's upsert and PostgreSQL's `ON CONFLICT` differ.

# 2 · Build: API contract

## Endpoint

| Method | Path                     | Purpose                                                                                                           |
|--------|--------------------------|-------------------------------------------------------------------------------------------------------------------|
| `PUT`  | `/warehouses/{id}/stock` | `{"items": [{"sku", "quantity"}, …]}`: store these counts. Answers `{warehouseId, syncedItems, skusInWarehouse}`. |

## Status codes

| Status | When                                                                                                                           |
|--------|--------------------------------------------------------------------------------------------------------------------------------|
| 200    | The snapshot is stored                                                                                                         |
| 400    | No items or more than 1000, a SKU outside `[A-Za-z0-9-]{3,30}`, a count below 0, above 1,000,000 or not whole, a missing field |
| 404    | No such warehouse                                                                                                              |
| 422    | The same SKU twice in one snapshot                                                                                             |
| 503    | Three deadlocks in a row; the snapshot was rolled back, send it again                                                          |

## Captured examples

Captured with curl from the running app on 16 Oct 2026, in this order, against the demo warehouses (1 Bhiwandi, 2 Hoskote). JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: Bhiwandi's first snapshot

**Why:** three new rows; `dal-1kg` is stored as `DAL-1KG`.

Request

``` code
PUT /warehouses/1/stock HTTP/1.1
Content-Type: application/json

{
  "items": [
    {
      "sku": "RICE-5KG",
      "quantity": 40
    },
    {
      "sku": "ATTA-10KG",
      "quantity": 12
    },
    {
      "sku": "dal-1kg",
      "quantity": 25
    }
  ]
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 53

{
  "warehouseId": 1,
  "syncedItems": 3,
  "skusInWarehouse": 3
}
```

### Case 2: RICE-5KG recounted

**Why:** the row is updated to 35, still three SKUs.

Request

``` code
PUT /warehouses/1/stock HTTP/1.1
Content-Type: application/json

{
  "items": [
    {
      "sku": "RICE-5KG",
      "quantity": 35
    }
  ]
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 53

{
  "warehouseId": 1,
  "syncedItems": 1,
  "skusInWarehouse": 3
}
```

### Case 3: OIL-1L and oil-1l in one body

**Why:** the same SKU after upper-casing; which count is right is the sender's call: `422`.

Request

``` code
PUT /warehouses/1/stock HTTP/1.1
Content-Type: application/json

{
  "items": [
    {
      "sku": "OIL-1L",
      "quantity": 5
    },
    {
      "sku": "oil-1l",
      "quantity": 8
    }
  ]
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "SKU OIL-1L appears twice; which count is right?",
  "instance": "/warehouses/1/stock",
  "status": 422,
  "title": "Unprocessable Content"
}
```

### Case 4: warehouse 99

**Why:** `404`, checked before any write.

Request

``` code
PUT /warehouses/99/stock HTTP/1.1
Content-Type: application/json

{
  "items": [
    {
      "sku": "RICE-5KG",
      "quantity": 1
    }
  ]
}
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No warehouse 99",
  "instance": "/warehouses/99/stock",
  "status": 404,
  "title": "Not Found"
}
```

### Case 5: a count of 2.5

**Why:** `400`: whole units only.

Request

``` code
PUT /warehouses/1/stock HTTP/1.1
Content-Type: application/json

{
  "items": [
    {
      "sku": "RICE-5KG",
      "quantity": 2.5
    }
  ]
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Failed to read request",
  "instance": "/warehouses/1/stock",
  "status": 400,
  "title": "Bad Request"
}
```

## The rows afterwards

``` code
+--------------+-----------+----------+
| warehouse_id | sku       | quantity |
+--------------+-----------+----------+
|            1 | ATTA-10KG |       12 |
|            1 | DAL-1KG   |       25 |
|            1 | RICE-5KG  |       35 |
+--------------+-----------+----------+
```

## Both warehouses at once

From `docs/capture.sh`: 10 parallel curl requests, five per warehouse, each with the same 200 new SKUs (`docs/captures/rush.txt`). The last number is how many deadlocks the app logged and retried.

``` code
10 syncs at once (5 per warehouse), 200 new SKUs each: HTTP status counts
     10 200

Rows per warehouse afterwards
+--------------+------+---------------+
| warehouse_id | skus | distinct_skus |
+--------------+------+---------------+
|            1 |  200 |           200 |
|            2 |  200 |           200 |
+--------------+------+---------------+

Deadlocks the app retried (its own log lines)
0
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                            | What happens                           | Proved by                                                 |
|-----------------------------------------------------------------|----------------------------------------|-----------------------------------------------------------|
| A snapshot, then a smaller one                                  | Counts set, unlisted SKUs left alone   | `aSnapshotSetsTheCountsAndTheNextOneOverwritesThem`       |
| The same snapshot twice                                         | Same rows                              | `theSameSnapshotTwiceLeavesTheSameRows`                   |
| 1000 SKUs                                                       | Two statements of 500, one transaction | `aThousandSkusGoInTwoChunks`                              |
| A Turkish default locale                                        | `milk-1l` is still `MILK-1L`           | `skusAreUpperCasedTheSameWayInEveryLocale`                |
| A SKU twice; an unknown warehouse; bad bodies                   | `422`; `404`; `400`                    | `StockContractTest`                                       |
| A deadlock; three in a row                                      | Run again; `503`                       | `aDeadlockVictimIsRunAgain`, `threeDeadlocksInARowAre503` |
| A bad row in the second chunk                                   | The first 500 rows roll back too       | `aBadRowInTheSecondChunkRollsBackTheFirst`                |
| Duplicate, negative, lower-case or orphan rows written directly | Refused by named constraints           | `namedConstraintsHoldWithoutJava`                         |
| Ten syncs of two warehouses, five rounds                        | All `200`, 200 rows each               | `twoWarehousesSyncingTheSameNewSkusNeverFail`             |
| Ten different snapshots of one warehouse, half in reverse order | One whole snapshot wins                | `parallelSnapshotsOfOneWarehouseLeaveOneWholeSnapshot`    |

## The trap

Plausible but wrong

Select, then insert: under concurrency it duplicates rows, and with `FOR UPDATE` it deadlocks on gap locks.

The test replays both old versions step by step on two plain JDBC connections, so every statement and lock is visible:

- **Version 1, no unique key.** Both connections look for RICE-5KG, both find nothing, both insert: two rows.
- **Version 2, unique key and `FOR UPDATE`.** Warehouse 1 looks for RICE-5KG, warehouse 2 for ATTA-10KG; neither exists, so each locks the *gap* where its row would go. On an empty range it is the same gap, and gap locks do not block each other. Then both insert into that gap, each waits for the other's gap lock, and MySQL kills one with error 1213. Every time, for SKUs that never touch.
- **The upsert.** No look first: both warehouses get their row, and the retried job updates instead of inserting.

While building, each fix was undone once:

- Adding the count instead of setting it turned 5 tests red.
- No retry: 3 red, one of them the two-warehouse test hitting a real deadlock.
- No transaction: 2 red. No duplicate check, no warehouse check, `toUpperCase()` without `Locale.ROOT`: 1 each.
- No warehouse lock was green in 1 of 3 runs: the retry absorbed more than 20 deadlocks. See Design for why the lock stays.

``` code
package com.basketo.inventory;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Written first. The old nightly sync, step by step on two real MySQL connections (two warehouses' sync jobs), in the
 * order that broke it. Plain JDBC, so every statement and every lock is visible.
 */
class SelectThenInsertTrapTest extends ApiTest {

    @Autowired
    DataSource dataSource;

    @AfterEach
    void dropOldTables() {
        jdbc.sql("DROP TABLE IF EXISTS old_stock_v1, old_stock_v2").update();
    }

    private static void insert(Connection c, String table, long warehouse, String sku, int quantity) throws SQLException {
        try (PreparedStatement insert = c.prepareStatement("INSERT INTO " + table + " (warehouse_id, sku, quantity) VALUES (?, ?, ?)")) {
            insert.setLong(1, warehouse);
            insert.setString(2, sku);
            insert.setInt(3, quantity);
            insert.executeUpdate();
        }
    }

    private static boolean nothingFound(Connection c, String table, long warehouse, String sku) throws SQLException {
        try (PreparedStatement select = c.prepareStatement("SELECT id FROM " + table + " WHERE warehouse_id = ? AND sku = ? FOR UPDATE")) {
            select.setLong(1, warehouse);
            select.setString(2, sku);
            try (ResultSet rs = select.executeQuery()) {
                return !rs.next();
            }
        }
    }

    @Test
    void version1WithoutAUniqueKeyInsertsTheSkuTwice() throws Exception {
        jdbc.sql("CREATE TABLE old_stock_v1 (id BIGINT AUTO_INCREMENT PRIMARY KEY, warehouse_id BIGINT NOT NULL, sku VARCHAR(30) NOT NULL, quantity INT NOT NULL)").update();
        try (Connection a = dataSource.getConnection(); Connection b = dataSource.getConnection()) {
            // The sync job retried on a timeout while the first run was still going: both look before either inserts.
            assertThat(countOf(a, "old_stock_v1", 1, "RICE-5KG")).isZero();
            assertThat(countOf(b, "old_stock_v1", 1, "RICE-5KG")).isZero();
            insert(a, "old_stock_v1", 1, "RICE-5KG", 40);
            insert(b, "old_stock_v1", 1, "RICE-5KG", 40);
        }
        assertThat(jdbc.sql("SELECT count(*) FROM old_stock_v1 WHERE sku = 'RICE-5KG'").query(Long.class).single()).isEqualTo(2);
    }

    private static long countOf(Connection c, String table, long warehouse, String sku) throws SQLException {
        try (PreparedStatement select = c.prepareStatement("SELECT count(*) FROM " + table + " WHERE warehouse_id = ? AND sku = ?")) {
            select.setLong(1, warehouse);
            select.setString(2, sku);
            try (ResultSet rs = select.executeQuery()) {
                rs.next();
                return rs.getLong(1);
            }
        }
    }

    @Test
    void version2WithForUpdateDeadlocksTwoWarehouses() throws Exception {
        jdbc.sql("""
                CREATE TABLE old_stock_v2 (id BIGINT AUTO_INCREMENT PRIMARY KEY, warehouse_id BIGINT NOT NULL, sku VARCHAR(30) NOT NULL,
                    quantity INT NOT NULL, CONSTRAINT old_stock_v2_warehouse_sku UNIQUE (warehouse_id, sku))""").update();
        try (Connection a = dataSource.getConnection(); Connection b = dataSource.getConnection()) {
            a.setAutoCommit(false);
            b.setAutoCommit(false);
            // Two different warehouses, two different new SKUs: they never touch the same row.
            assertThat(nothingFound(a, "old_stock_v2", 1, "RICE-5KG")).isTrue();   // locks the gap where the row would go
            assertThat(nothingFound(b, "old_stock_v2", 2, "ATTA-10KG")).isTrue();  // the same gap: gap locks do not block each other
            List<String> outcomes = together(2, i -> i == 0
                    ? commitAfter(a, () -> insert(a, "old_stock_v2", 1, "RICE-5KG", 40))     // waits for b's gap lock
                    : commitAfter(b, () -> insert(b, "old_stock_v2", 2, "ATTA-10KG", 12)));  // waits for a's: a cycle
            assertThat(outcomes).containsExactlyInAnyOrder("committed", "1213 Deadlock found when trying to get lock; try restarting transaction");
        }
    }

    @Test
    void theUpsertGivesBothWarehousesTheirRowWithoutLookingFirst() throws Exception {
        String upsert = "INSERT INTO stock_levels (warehouse_id, sku, quantity) VALUES (?, ?, ?) AS incoming ON DUPLICATE KEY UPDATE quantity = incoming.quantity";
        try (Connection a = dataSource.getConnection(); Connection b = dataSource.getConnection()) {
            a.setAutoCommit(false);
            b.setAutoCommit(false);
            List<String> outcomes = together(2, i -> i == 0
                    ? commitAfter(a, () -> upsertOne(a, upsert, 1, "RICE-5KG", 40))
                    : commitAfter(b, () -> upsertOne(b, upsert, 2, "ATTA-10KG", 12)));
            assertThat(outcomes).containsOnly("committed");
            // And the retried job from version 1: the second run finds the key taken and updates instead.
            upsertOne(a, upsert, 1, "RICE-5KG", 40);
            a.commit();
        }
        assertThat(rows(1)).isEqualTo(1);
        assertThat(rows(2)).isEqualTo(1);
    }

    private static void upsertOne(Connection c, String sql, long warehouse, String sku, int quantity) throws SQLException {
        try (PreparedStatement upsert = c.prepareStatement(sql)) {
            upsert.setLong(1, warehouse);
            upsert.setString(2, sku);
            upsert.setInt(3, quantity);
            upsert.executeUpdate();
        }
    }

    interface Step {
        void run() throws SQLException;
    }

    private static String commitAfter(Connection c, Step step) throws SQLException {
        try {
            step.run();
            c.commit();
            return "committed";
        } catch (SQLException e) {
            c.rollback();
            return e.getErrorCode() + " " + e.getMessage();
        }
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
docker compose up -d        # MySQL 8.4 on localhost:3306
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 18 tests; starts its own MySQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Ask MySQL how many rows an upsert "affected" (from `docs/captures/row-count.txt`):

``` code
+----------+
| inserted |
+----------+
|        1 |
+----------+
+---------+
| updated |
+---------+
|       2 |
+---------+
+-----------+
| unchanged |
+-----------+
|         0 |
+-----------+
```

1 for an insert, 2 for an update, and 0 when nothing changed. From Java, Connector/J asks MySQL for *found* rows, so the unchanged case comes back as 1 (`mySqlCountsAnUpsertedRowTwice`). Never use the count to mean "how many SKUs".

## Troubleshooting

| You see                                                                          | Cause                                                                                | Fix                                                                                                           |
|----------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| `Deadlock found when trying to get lock; try restarting transaction`             | InnoDB chose this sync as a deadlock victim (error 1213); all of it was rolled back. | Expected now and then; the app runs it again and logs it. Many per night means many writers on the same rows. |
| `Duplicate entry '1-RICE-5KG' for key 'stock_levels.stock_levels_warehouse_sku'` | A plain `INSERT` of a SKU the warehouse already has.                                 | Use the upsert; the unique key is what makes it an update.                                                    |
| `Check constraint 'stock_levels_sku_shape' is violated.`                         | A SKU that was not upper-cased reached the database, for example by a script.        | Upper-case with `Locale.ROOT` before writing.                                                                 |
| `'VALUES function' is deprecated` warning                                        | `… UPDATE quantity = VALUES(quantity)`.                                              | Use a row alias: `VALUES (…) AS incoming … quantity = incoming.quantity`.                                     |

## Project layout

``` tree
stations/060-inventory-sync-with-mysql-upserts/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/basketo/inventory/
│   ├── StockController.java   ├── StockSync.java   └── InventoryApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__warehouses_and_stock.sql, V2__demo_warehouses.sql
├── src/test/java/com/basketo/inventory/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/basketo/inventory/StockController.java`

Does  
Validates the snapshot, upper-cases SKUs, refuses duplicates, and runs the sync again after a deadlock.

Why  
A clear `422` for a SKU sent twice, and no deadlock reaching the warehouse job as a `500`.

Without it  
"Which of 5 and 8 is the count?" answered silently by whichever row came last.

- The retry wraps the whole transaction: after a deadlock InnoDB has rolled it all back, so the only safe retry is from the start.
- `PessimisticLockingFailureException` is what Spring makes of MySQL 1213 (and of a lock wait timeout).

#### `src/main/java/com/basketo/inventory/StockSync.java`

Does  
Locks the warehouse row, then upserts in chunks of 500, all in one transaction.

Why  
One statement per 500 rows, no look-up first, and one sync per warehouse at a time.

Without it  
Select-then-insert's duplicates and deadlocks, or a half-written snapshot.

- `AS incoming … quantity = incoming.quantity` is the MySQL 8.0.19+ form; `VALUES(quantity)` still works but is deprecated.
- The `404` check and the lock are one query.

#### `src/main/resources/db/migration/V1__warehouses_and_stock.sql`

Does  
Warehouses and stock rows, with four named constraints.

Why  
`ON DUPLICATE KEY UPDATE` only fires on a unique key; without `stock_levels_warehouse_sku` it silently inserts.

Without it  
Duplicates from any writer that is not this app.

#### `src/main/resources/db/migration/V2__demo_warehouses.sql`

Bhiwandi (1) and Hoskote (2).

#### `src/main/resources/application.yaml`

Problem details on, whole numbers only.

#### `compose.yaml`

MySQL 8.4 for running the app.

#### `src/main/java/com/basketo/inventory/InventoryApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                             | Test class                     | Result |
|---------------|---------------------------------------------------------|--------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                | `StockContractTest` (9)        | pass   |
| Every station | Reproduce the failure before the fix                    | `SelectThenInsertTrapTest` (3) | pass   |
| Database      | Rollback and constraint tests against a real database   | `StockDatabaseTest` (4)        | pass   |
| Concurrency   | A real concurrency test that proves the invariant holds | `StockConcurrencyTest` (2)     | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, MySQL 8.4 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.basketo.inventory.StockConcurrencyTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.basketo.inventory.SelectThenInsertTrapTest
[INFO] Tests run: 9, Failures: 0, Errors: 0, Skipped: 0 -- in com.basketo.inventory.StockContractTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.basketo.inventory.StockDatabaseTest
[INFO] Tests run: 18, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/basketo/inventory/SelectThenInsertTrapTest.java`

Written first: both old versions on two plain JDBC connections, then the upsert.

#### `src/test/java/com/basketo/inventory/StockConcurrencyTest.java`

Ten syncs at a time, released by one latch: two warehouses on the same new SKUs, and one warehouse with ten different snapshots.

#### `src/test/java/com/basketo/inventory/StockDatabaseTest.java`

Named constraints with plain SQL, a rollback across chunks, an in-place update, and MySQL's affected-row count.

#### `src/test/java/com/basketo/inventory/StockContractTest.java`

The endpoint through HTTP, including a deadlock injected with `@MockitoSpyBean`.

#### `src/test/java/com/basketo/inventory/ApiTest.java`

Shared setup: no stock before each test, the snapshot builder and the latch helper.

#### `src/test/java/com/basketo/inventory/MySqlTestConfig.java`

MySQL 8.4 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/basketo/inventory/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=ReadOneSkuChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 18 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 22 tests pass (18 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Read one SKU

Add `GET /warehouses/{id}/stock/{sku}`: `{warehouseId, sku, quantity}`. `rice-5kg` finds `RICE-5KG`; a SKU the warehouse never synced is `404`.

**Done when:** both tests in `ReadOneSkuChallengeTest` pass.

Hints

- Normalise the path the same way the sync does, with `Locale.ROOT`.
- `JdbcClient … .query(Level.class).optional()` maps a record by column names.

#### `challenge/ReadOneSkuChallengeTest.java`

``` code
package com.basketo.inventory;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /warehouses/{id}/stock/{sku} returns {warehouseId, sku, quantity}. The SKU in the path is matched
 * the way the sync stores it, so "rice-5kg" finds RICE-5KG. A SKU the warehouse has never synced is 404.
 */
class ReadOneSkuChallengeTest extends ApiTest {

    @Test
    void aSyncedSkuCanBeReadInAnyCase() throws Exception {
        sync(1, "[{\"sku\":\"RICE-5KG\",\"quantity\":40}]").andExpect(status().isOk());
        mvc.perform(get("/warehouses/1/stock/rice-5kg")).andExpect(status().isOk())
                .andExpect(jsonPath("$.warehouseId").value(1)).andExpect(jsonPath("$.sku").value("RICE-5KG")).andExpect(jsonPath("$.quantity").value(40));
    }

    @Test
    void aSkuOfAnotherWarehouseOrNoneIs404() throws Exception {
        sync(1, "[{\"sku\":\"RICE-5KG\",\"quantity\":40}]").andExpect(status().isOk());
        mvc.perform(get("/warehouses/2/stock/RICE-5KG")).andExpect(status().isNotFound());
        mvc.perform(get("/warehouses/1/stock/OIL-1L")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## A full stock-take

Add `?mode=full`: the snapshot is everything on the shelves, so every SKU of that warehouse it does not list is set to 0 (kept, not deleted). The response gains `zeroedSkus`.

**Done when:** both tests in `FullSnapshotChallengeTest` pass, and the station tests still do.

Hints

- Zero in the same transaction as the upserts: a sync that fails halfway must not leave SKUs zeroed.
- `… WHERE warehouse_id = ? AND sku NOT IN (?, ?, …)`; the warehouse lock already keeps other syncs out.
- Keep the existing `sync(id, items)` as it is; the contract tests stub it.

#### `challenge/FullSnapshotChallengeTest.java`

``` code
package com.basketo.inventory;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: PUT /warehouses/{id}/stock?mode=full says "this is everything on the shelves": every SKU of that
 * warehouse missing from the snapshot is set to 0 (kept, not deleted), and the response says how many with
 * "zeroedSkus". Without the parameter, the sync works as before. Other warehouses are never touched.
 */
class FullSnapshotChallengeTest extends ApiTest {

    @Test
    void aFullSnapshotZeroesWhatIsMissing() throws Exception {
        sync(1, items(5, 9)).andExpect(status().isOk());
        sync(2, items(5, 9)).andExpect(status().isOk());
        mvc.perform(put("/warehouses/1/stock").param("mode", "full").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"items\":[{\"sku\":\"SKU-00001\",\"quantity\":4},{\"sku\":\"SKU-00002\",\"quantity\":6}]}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.zeroedSkus").value(3)).andExpect(jsonPath("$.skusInWarehouse").value(5));
        assertThat(quantity(1, "SKU-00001")).isEqualTo(4);
        assertThat(quantity(1, "SKU-00005")).isZero();
        assertThat(quantity(2, "SKU-00005")).isEqualTo(9);
    }

    @Test
    void withoutTheModeMissingSkusAreLeftAlone() throws Exception {
        sync(1, items(5, 9)).andExpect(status().isOk());
        sync(1, "[{\"sku\":\"SKU-00001\",\"quantity\":4}]").andExpect(status().isOk()).andExpect(jsonPath("$.zeroedSkus").value(0));
        assertThat(quantity(1, "SKU-00005")).isEqualTo(9);
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## The same sync on PostgreSQL

Basketo's new region runs PostgreSQL. Write the upsert with `INSERT … ON CONFLICT (warehouse_id, sku) DO UPDATE SET quantity = EXCLUDED.quantity`. Then answer: what does each database do when one statement holds the same SKU twice? (PostgreSQL refuses: "ON CONFLICT DO UPDATE command cannot affect row a second time"; MySQL applies both.) Which other unique keys could fire MySQL's update but not PostgreSQL's? Does the warehouse lock still make sense?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: both old versions, step by step on two connections.
2.  Add the unique key, and write the multi-row upsert against it.
3.  Put the snapshot in one transaction, in chunks of 500.
4.  Run real parallel syncs; handle what they show (here: deadlocks, below).

## Why the upsert was not the end

With the upsert alone, ten parallel syncs (five per warehouse, the same 200 new SKUs) deadlocked inside InnoDB about 20 times per test run while building this station, and once a request lost all three attempts. Several syncs of the *same* warehouse were taking row and gap locks on the same new keys in a different order. Locking the warehouse row first (`SELECT … FOR UPDATE` on one existing row: no gap) makes syncs of one warehouse take turns. Afterwards a run showed 0 or 1 deadlocks, between the two warehouses; the retry covers those. The lock is a reduction, not a guarantee: InnoDB may always choose a victim, which is why the retry stays.

## Where MySQL and PostgreSQL differ

|                                 | MySQL 8.4                                                     | PostgreSQL 17                                                           |
|---------------------------------|---------------------------------------------------------------|-------------------------------------------------------------------------|
| Syntax                          | `INSERT … AS incoming ON DUPLICATE KEY UPDATE q = incoming.q` | `INSERT … ON CONFLICT (warehouse_id, sku) DO UPDATE SET q = EXCLUDED.q` |
| Which key                       | Any unique key or the primary key that clashes                | The one you name (or a named constraint)                                |
| Same key twice in one statement | Both applied, in order                                        | Error: cannot affect row a second time                                  |
| Affected rows                   | 1 inserted, 2 updated, 0 unchanged                            | 1 per row inserted or updated                                           |
| Get the row back                | `LAST_INSERT_ID()` tricks                                     | `RETURNING`                                                             |

## Design alternatives and trade-offs

| Approach                                                                        | What it costs                                                                       | Verdict             |
|---------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|---------------------|
| Unique key + multi-row upsert + warehouse lock + retry                          | MySQL-specific SQL; syncs of one warehouse take turns.                              | Chosen              |
| Select, then insert                                                             | Duplicates under concurrency.                                                       | The trap            |
| Select `FOR UPDATE`, then insert                                                | Gap-lock deadlocks, even between warehouses.                                        | The trap, version 2 |
| Insert, catch the duplicate, then update                                        | Two statements per SKU, and an error per known SKU.                                 | Works, slowly       |
| `READ COMMITTED` isolation                                                      | No gap locks for searches; select-then-insert then fails on the unique key instead. | Moves the problem   |
| Load into a staging table, then one `INSERT … SELECT … ON DUPLICATE KEY UPDATE` | An extra table; best for very large snapshots.                                      | Valid at scale      |

## Database design

| Table          | Constraints                                                                                                                 | Why                                                          |
|----------------|-----------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------|
| `warehouses`   | PK                                                                                                                          | What can sync; its row is the per-warehouse lock.            |
| `stock_levels` | `stock_levels_warehouse_sku` (UNIQUE), `stock_levels_warehouse_fk`, `stock_levels_quantity_range`, `stock_levels_sku_shape` | One row per SKU per warehouse; the key the upsert relies on. |

**Transaction boundary:** one snapshot, from the warehouse lock to the last chunk. A retry starts it again from the top.

``` code
CREATE TABLE warehouses (
    id   BIGINT       NOT NULL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE stock_levels (
    id           BIGINT      NOT NULL AUTO_INCREMENT PRIMARY KEY,
    warehouse_id BIGINT      NOT NULL,
    sku          VARCHAR(30) NOT NULL,
    quantity     INT         NOT NULL,
    updated_at   TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    -- The rule the old sync only checked in Java: one row per SKU per warehouse. ON DUPLICATE KEY UPDATE needs it.
    CONSTRAINT stock_levels_warehouse_sku UNIQUE (warehouse_id, sku),
    CONSTRAINT stock_levels_warehouse_fk FOREIGN KEY (warehouse_id) REFERENCES warehouses (id),
    CONSTRAINT stock_levels_quantity_range CHECK (quantity BETWEEN 0 AND 1000000),
    CONSTRAINT stock_levels_sku_shape CHECK (REGEXP_LIKE(sku, '^[A-Z0-9-]{3,30}$', 'c'))
);
```

# 3 · Go deeper: Production

Count the deadlocks  
The app logs each one. A few a night are normal for InnoDB; a rising count means more writers on the same rows.

Lock wait timeout  
A sync waiting for another sync of the same warehouse waits up to `innodb_lock_wait_timeout` (50 s by default). A huge snapshot can make the next one time out.

Snapshot size  
1000 SKUs per call is a demo rule. Larger warehouses send several calls; each is its own transaction.

Counts are not stock  
Orders placed between the count and the sync are lost if the count simply overwrites. Real systems store counts with a time and apply orders after it.

Replication  
`ON DUPLICATE KEY UPDATE` on a table with more than one unique key is flagged unsafe for statement-based replication; row-based (the MySQL 8 default) is fine.

# 3 · Go deeper: Interview

## Interview takeaways

Why does select-then-insert create duplicates?

Two transactions can both look before either inserts. Without a unique key, both inserts succeed. Only a constraint decides between them.

What is a gap lock?

In REPEATABLE READ, InnoDB locks the space between index records that a search covered, so no one can insert there. Locking a row that does not exist locks a gap.

Why did SELECT … FOR UPDATE deadlock two warehouses?

Both locked the same gap (gap locks do not conflict with each other), then both inserted into it, which needs the other's gap lock released. A cycle: InnoDB kills one with error 1213.

How does ON DUPLICATE KEY UPDATE decide to update?

When the insert clashes with any unique key or the primary key. With no unique key it never fires, and simply inserts.

How do you retry a deadlock correctly?

The victim's whole transaction was rolled back, so retry the whole transaction, a bounded number of times, and log it.

## Self-check rubric

| Area         | Meets the bar                            | Above the bar                                                 |
|--------------|------------------------------------------|---------------------------------------------------------------|
| Correctness  | All 18 tests pass.                       | You ran the flawed version and explained each failure.        |
| SQL          | A multi-row upsert with a row alias.     | The PostgreSQL version, and where it behaves differently.     |
| Concurrency  | Why select-then-insert fails, both ways. | Why the warehouse lock reduces deadlocks but the retry stays. |
| Transactions | One snapshot, one transaction.           | What a retry must start from.                                 |

# 3 · Go deeper: Review

## The pull request

A teammate tidies the sync: "the foreign key already checks the warehouse", "SKUs exactly as printed on the label", and the upsert now adds, "like a delivery". Read the two files and list every problem before opening the findings.

#### `review/StockController.java`

``` code
package com.basketo.inventory;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.PessimisticLockingFailureException;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@RestController
class StockController {

    /** Demo limits: up to 1,000 SKUs per call, up to 1,000,000 units each. */
    record Line(@NotNull @Pattern(regexp = "[A-Za-z0-9-]{3,30}") String sku, @NotNull @Min(0) @Max(1_000_000) Integer quantity) {
    }

    record Snapshot(@NotNull @Size(min = 1, max = 1000) List<@NotNull @Valid Line> items) {
    }

    private static final Logger log = LoggerFactory.getLogger(StockController.class);

    private final StockSync sync;

    StockController(StockSync sync) {
        this.sync = sync;
    }

    /** PUT: the body is the warehouse's count for these SKUs. Sending it twice leaves the same rows. */
    @PutMapping("/warehouses/{id}/stock")
    StockSync.Synced put(@PathVariable long id, @Valid @RequestBody Snapshot body) {
        // Warehouses send SKUs exactly as printed on the label; keep them as sent.
        List<StockSync.Item> items = body.items().stream().map(l -> new StockSync.Item(l.sku(), l.quantity())).toList();
        // InnoDB may still pick a sync as a deadlock victim (error 1213); the whole snapshot rolled back, so run it again.
        for (int attempt = 1; ; attempt++) {
            try {
                return sync.sync(id, items);
            } catch (PessimisticLockingFailureException e) {
                log.warn("Stock sync of warehouse {} deadlocked (attempt {}): {}", id, attempt, e.getMostSpecificCause().getMessage());
                if (attempt == 3) {
                    throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "Stock sync kept deadlocking; try again", e);
                }
            }
        }
    }
}
```

#### `review/StockSync.java`

``` code
package com.basketo.inventory;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Writes a warehouse's stock snapshot with one MySQL upsert per chunk: no SELECT first, so there is no gap between
 * "not there" and "insert" for another sync to fall into.
 */
@Service
class StockSync {

    record Item(String sku, int quantity) {
    }

    record Synced(long warehouseId, int syncedItems, long skusInWarehouse) {
    }

    /** Rows per statement. Each row is 3 parameters; 500 rows stays far below MySQL's 65,535 placeholders. */
    static final int CHUNK = 500;

    private final JdbcClient jdbc;

    StockSync(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Transactional
    Synced sync(long warehouseId, List<Item> items) {
        // The foreign key already checks the warehouse; no need for an extra query.
        for (int from = 0; from < items.size(); from += CHUNK) {
            upsert(warehouseId, items.subList(from, Math.min(from + CHUNK, items.size())));
        }
        long skus = jdbc.sql("SELECT count(*) FROM stock_levels WHERE warehouse_id = ?").param(warehouseId).query(Long.class).single();
        return new Synced(warehouseId, items.size(), skus);
    }

    private void upsert(long warehouseId, List<Item> chunk) {
        // A delivery adds to what is on the shelf.
        String sql = "INSERT INTO stock_levels (warehouse_id, sku, quantity) VALUES "
                + String.join(", ", Collections.nCopies(chunk.size(), "(?, ?, ?)"))
                + " AS incoming ON DUPLICATE KEY UPDATE quantity = stock_levels.quantity + incoming.quantity";
        List<Object> params = new ArrayList<>(chunk.size() * 3);
        for (Item item : chunk) {
            params.add(warehouseId);
            params.add(item.sku());
            params.add(item.quantity());
        }
        jdbc.sql(sql).params(params).update();
    }
}
```

## Findings

1The upsert adds the count

"A delivery adds to what is on the shelf" is true for deliveries, not for a stock-take. Every resync doubles the stock.

**Test evidence:** `aSnapshotSetsTheCountsAndTheNextOneOverwritesThem`, `theSameSnapshotTwiceLeavesTheSameRows`, `anUpsertUpdatesTheRowInPlace` and `parallelSnapshotsOfOneWarehouseLeaveOneWholeSnapshot` fail.

2The same SKU twice is accepted

MySQL applies both rows of one statement, so with finding 1 the two counts are summed; without it, the last one wins silently.

**Test evidence:** `theSameSkuTwiceIs422EvenInDifferentCase` fails.

3No warehouse check

"The foreign key already checks it": it does, as a `500` with a constraint message instead of a `404`. The check was also the per-warehouse lock.

**Test evidence:** `anUnknownWarehouseIs404` fails.

4SKUs kept as sent

`dal-1kg` and `DAL-1KG` become two products, and the database's `stock_levels_sku_shape` refuses lower case anyway: a `500`.

**Test evidence:** `skusAreUpperCasedTheSameWayInEveryLocale` fails.

## Same tests, flawed version

From `docs/review-run.txt`: the two flawed files copied over the real ones, then the full suite run.

| Test class                 | Fixed version | Flawed version |
|----------------------------|---------------|----------------|
| `SelectThenInsertTrapTest` | 3 / 3         | 3 / 3          |
| `StockConcurrencyTest`     | 2 / 2         | 1 / 2          |
| `StockContractTest`        | 9 / 9         | 4 / 9          |
| `StockDatabaseTest`        | 4 / 4         | 3 / 4          |

No duplicate row got through: the unique key held. What the flaws broke is what the numbers mean, which no constraint can check for you.
