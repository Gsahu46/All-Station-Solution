# Station 054 · Archiving seller products

Foundations · 0–1 years · Core · E-commerce · Types: Database

Spring Boot 4.1.1 · Java 25 · Spring Data JPA (Hibernate 7) · @PrePersist / @PreUpdate · soft delete · PostgreSQL 17 (ON DELETE RESTRICT, partial unique index) · Flyway · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Sellers, products and the past order are demo data, not Kartwala's. The seller is named in a header because this station has no login.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 11 tests.

# 1 · Understand

## The problem in real life

1.  **Delete means delete**

    A Kartwala seller deleted "Assam tea, 500 g" from their catalogue. The database deleted the product row.

2.  **The order history moved**

    The order lines' foreign key had ON DELETE CASCADE, added so deletes would not fail. Order KW-1001, paid ₹897, now showed one line and ₹199. Refund disputes had nothing to check against.

3.  **The fix**

    "Delete" archives the product: it leaves the shop and stays for every order. The database refuses a real delete while any order line points at the product.

Rows that history points at are not yours to delete. Archive them, and let the database refuse the rest.

## What are we building?

A seller "deletes" a product (`DELETE /seller/products/{id}`), and lists their products (`GET /seller/products`), with or without the archived ones (`?includeArchived=true`). Past orders keep every line.

## An everyday analogy

A shop's price list and its sales receipts. When the shop stops selling a tea, it crosses it off the price list. It does not go back and cut that tea out of last month's receipts.

## How it works in 4 steps

1.  **The seller asks** to delete product 1.
2.  **The service finds it** among this seller's products (anyone else's is "not found").
3.  **It sets** `archived_at`; JPA's `@PreUpdate` moves `updated_at`.
4.  **The shop's list** hides it; the order history still joins to it.

Check yourself: with soft delete, why keep ON DELETE RESTRICT at all?

Because the next person may write a script, an admin tool or a migration that does a real `DELETE`. RESTRICT makes the database refuse it while orders point at the row, whoever wrote the code.

## What this station is not

- **No login.** The seller is named in a header.
- **No restore or purge.** Those are the challenges.
- **No creating products over HTTP.** The demo catalogue is loaded by a migration.

## Key terms

| Term                      | Simple meaning                                         | Everyday example                                     | In this project             |
|---------------------------|--------------------------------------------------------|------------------------------------------------------|-----------------------------|
| **Hard delete**           | Removing the row from the table.                       | Tearing a page out of the register.                  | What the old DELETE did     |
| **Soft delete (archive)** | Marking the row as gone, and keeping it.               | Striking a line through the page.                    | `archived_at`               |
| **Foreign key**           | A column that must point at an existing row elsewhere. | An order slip naming a product from the catalogue.   | `order_lines.product_id`    |
| **ON DELETE RESTRICT**    | Refuse to delete a row that others still point at.     | You cannot tear out a page someone else refers to.   | `order_lines_product_fk`    |
| **ON DELETE CASCADE**     | Delete the rows that point at it too.                  | Tearing out every order slip that names the product. | The old schema              |
| **Entity callback**       | A method JPA calls just before it saves a row.         | A stamp the clerk applies to every form, every time. | `@PrePersist`, `@PreUpdate` |

# 2 · Build: Spec

## Business problem

**Kartwala** (a fictional marketplace) lets sellers remove products. Removing one broke the order history that referenced it.

## Acceptance criteria

1.  **Given** seller 1 deletes Assam tea, **then** `204`; it leaves the default list and shows with `includeArchived=true`, marked archived.
2.  **Given** order KW-1001 had Assam tea, **then** both its lines and their product names are still there.
3.  **Given** a real `DELETE` on the products table, **then** the database refuses it while order lines point at the product.
4.  **Given** the same delete twice, **then** `204` both times, and the first archive date and update time stay.
5.  **Given** another seller's or an unknown product, **then** `404`; no seller header, or a bad parameter, `400`.

## Requirements

- Products are archived, never deleted, while orders reference them; the database enforces it.
- Every row has `created_at` and `updated_at`, set by JPA callbacks, checked by the database.
- A product name is unique per seller among products on sale only.
- Money in integer paise.

## Learning objectives

- Implement soft delete, and know what it costs.
- Choose `ON DELETE` behaviour for each foreign key on purpose.
- Stamp timestamps with `@PrePersist` and `@PreUpdate`.
- Write a partial unique index for "unique among active rows".

# 2 · Build: API contract

## Endpoints

| Method   | Path                                     | Purpose                                                       |
|----------|------------------------------------------|---------------------------------------------------------------|
| `DELETE` | `/seller/products/{id}`                  | Archive one of your products. Header `X-Seller-Id`.           |
| `GET`    | `/seller/products?includeArchived=false` | Your products, on sale only by default. Header `X-Seller-Id`. |

## Status codes

| Status | When                                                                               |
|--------|------------------------------------------------------------------------------------|
| 204    | Archived (or already archived: nothing changes)                                    |
| 200    | The list                                                                           |
| 400    | No `X-Seller-Id`, or one that is not a number; `includeArchived` not true or false |
| 404    | No such product among your products                                                |

## Captured examples

Captured with curl from the running app on 16 Oct 2026, in this order, against one fresh database. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: Chaiwala Traders lists its products

**Why:** two products on sale.

Request

``` code
GET /seller/products HTTP/1.1
X-Seller-Id: 1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 325

[
  {
    "id": 1,
    "name": "Assam tea, 500 g",
    "pricePaise": 34900,
    "archived": false,
    "archivedAt": null,
    "createdAt": "2026-09-01T04:30:00Z",
    "updatedAt": "2026-09-01T04:30:00Z"
  },
  {
    "id": 2,
    "name": "Masala chai mix, 200 g",
    "pricePaise": 19900,
    "archived": false,
    "archivedAt": null,
    "createdAt": "2026-09-01T04:30:00Z",
    "updatedAt": "2026-09-01T04:30:00Z"
  }
]
```

### Case 2: it deletes Assam tea

**Why:** archived: `204`.

Request

``` code
DELETE /seller/products/1 HTTP/1.1
X-Seller-Id: 1
```

Response

``` code
HTTP/1.1 204
```

### Case 3: the list now

**Why:** only the chai mix is on sale.

Request

``` code
GET /seller/products HTTP/1.1
X-Seller-Id: 1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 166

[
  {
    "id": 2,
    "name": "Masala chai mix, 200 g",
    "pricePaise": 19900,
    "archived": false,
    "archivedAt": null,
    "createdAt": "2026-09-01T04:30:00Z",
    "updatedAt": "2026-09-01T04:30:00Z"
  }
]
```

### Case 4: with archived products

**Why:** Assam tea is there, archived, with its new `updatedAt`.

Request

``` code
GET /seller/products?includeArchived=true HTTP/1.1
X-Seller-Id: 1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 356

[
  {
    "id": 1,
    "name": "Assam tea, 500 g",
    "pricePaise": 34900,
    "archived": true,
    "archivedAt": "2026-10-16T06:40:25.187439Z",
    "createdAt": "2026-09-01T04:30:00Z",
    "updatedAt": "2026-10-16T06:40:25.194353Z"
  },
  {
    "id": 2,
    "name": "Masala chai mix, 200 g",
    "pricePaise": 19900,
    "archived": false,
    "archivedAt": null,
    "createdAt": "2026-09-01T04:30:00Z",
    "updatedAt": "2026-09-01T04:30:00Z"
  }
]
```

### Case 5: Chaiwala deletes product 3

**Why:** another seller's product is not found: `404`.

Request

``` code
DELETE /seller/products/3 HTTP/1.1
X-Seller-Id: 1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No product 3 in your catalogue.",
  "instance": "/seller/products/3",
  "status": 404,
  "title": "Product not found"
}
```

### Case 6: no X-Seller-Id

**Why:** `400`.

Request

``` code
DELETE /seller/products/2 HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Required header 'X-Seller-Id' is not present.",
  "instance": "/seller/products/2",
  "status": 400,
  "title": "Bad Request"
}
```

## The order history, and a real DELETE

Through psql, after the requests above (`docs/captures/order-history.txt`): KW-1001 still has both lines, and a real `DELETE` is refused.

``` code
 order_ref |          name          | quantity | unit_price_paise | archived 
-----------+------------------------+----------+------------------+----------
 KW-1001   | Assam tea, 500 g       |        2 |            34900 | t
 KW-1001   | Masala chai mix, 200 g |        1 |            19900 | f
(2 rows)

ERROR:  update or delete on table "products" violates foreign key constraint "order_lines_product_fk" on table "order_lines"
DETAIL:  Key (id)=(1) is still referenced from table "order_lines".
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                  | What happens                                 | Proved by                                         |
|-------------------------------------------------------|----------------------------------------------|---------------------------------------------------|
| Archive, then list both ways                          | Hidden by default; shown archived on request | `anArchivedProductLeavesTheDefaultList`           |
| Archive twice                                         | `204`; dates unchanged                       | `archivingStampsUpdatedAtAndAgainChangesNothing`  |
| Another seller's, or unknown                          | `404`                                        | `anotherSellersProductIsNotFound`                 |
| No header, bad header, bad parameter, bad id          | `400`                                        | `requestsWithoutASellerOrWithBadParametersAre400` |
| Bad rows written directly                             | Refused by named constraints                 | `namedConstraintsHoldWithoutJava`                 |
| Same name: same seller, other seller, after archiving | Refused; allowed; allowed                    | `aNameIsUniqueAmongProductsOnSaleOnly`            |
| Saved, then changed                                   | Equal stamps, then `updated_at` later        | `prePersistAndPreUpdateStampTheRows`              |
| An archive that fails after the UPDATE                | Rolled back                                  | `anArchiveThatFailsLaterIsRolledBack`             |

## The trap

Plausible but wrong

Hard-deleting rows that past orders still reference.

The first test rebuilds the old tables inside a transaction that is rolled back afterwards: an order-lines table whose foreign key says `ON DELETE CASCADE`. It deletes Assam tea, and order KW-1001's total drops from ₹897 to ₹199. The second test tries the same delete on today's schema: PostgreSQL refuses it, naming `order_lines_product_fk`. The third sends the seller's DELETE to the API: the product is archived, and the history still reads.

While building, each part was undone once. CASCADE instead of RESTRICT turned 4 tests red: the "refused" delete went through and took product 1 and its lines with it, so the tests after it found them missing. Without `@PreUpdate`, 2. Archiving that overwrites the first date, 1. The unique index without `WHERE archived_at IS NULL`, 1. A default list that includes archived products, 1.

``` code
package com.kartwala.catalog;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: the old schema and the old DELETE, then the same request today. The old
 * tables are created inside a transaction that is rolled back, so they never outlive the test.
 */
class HardDeleteTrapTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;

    @Test
    void theOldCascadeDeletedTheOrderHistoryWithTheProduct() {
        List<Long> before = new java.util.ArrayList<>(), after = new java.util.ArrayList<>();
        transaction.executeWithoutResult(status -> {
            jdbc.sql("CREATE TABLE old_products (id BIGINT PRIMARY KEY, name TEXT)").update();
            // ON DELETE CASCADE "so deleting a product does not fail": it deletes the lines that sold it.
            jdbc.sql("CREATE TABLE old_order_lines (order_ref TEXT, product_id BIGINT REFERENCES old_products ON DELETE CASCADE, quantity INT, unit_price_paise BIGINT)").update();
            jdbc.sql("INSERT INTO old_products VALUES (1, 'Assam tea, 500 g'), (2, 'Masala chai mix, 200 g')").update();
            jdbc.sql("INSERT INTO old_order_lines VALUES ('KW-1001', 1, 2, 34900), ('KW-1001', 2, 1, 19900)").update();
            before.add(jdbc.sql("SELECT sum(quantity * unit_price_paise) FROM old_order_lines WHERE order_ref = 'KW-1001'").query(Long.class).single());
            jdbc.sql("DELETE FROM old_products WHERE id = 1").update();   // the seller "deletes" Assam tea
            after.add(jdbc.sql("SELECT sum(quantity * unit_price_paise) FROM old_order_lines WHERE order_ref = 'KW-1001'").query(Long.class).single());
            status.setRollbackOnly();
        });
        assertThat(before).containsExactly(89700L);   // ₹897 paid by the customer
        assertThat(after).containsExactly(19900L);    // and now the order says ₹199: a line of a paid order is gone
    }

    @Test
    void todayTheDatabaseRefusesTheHardDelete() {
        assertThatThrownBy(() -> jdbc.sql("DELETE FROM products WHERE id = 1").update()).hasMessageContaining("order_lines_product_fk");
        assertThat(linesOfOrder("KW-1001")).isEqualTo(2);
    }

    @Test
    void andTheApiArchivesInstead() throws Exception {
        archive(1, 1).andExpect(status().isNoContent());
        assertThat(linesOfOrder("KW-1001")).isEqualTo(2);
        assertThat(jdbc.sql("SELECT p.name FROM order_lines l JOIN products p ON p.id = l.product_id WHERE l.order_ref = 'KW-1001' ORDER BY l.id")
                .query(String.class).list()).containsExactly("Assam tea, 500 g", "Masala chai mix, 200 g");   // the history still reads
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

With the app running, try what the old code did:

``` code
docker compose exec postgres psql -U kartwala -d kartwala -c "DELETE FROM products WHERE id = 1"
```

PostgreSQL refuses, naming `order_lines_product_fk`. The seller's way, `curl -X DELETE -H "X-Seller-Id: 1" localhost:8080/seller/products/1`, archives it instead.

## Troubleshooting

| You see                                                    | Cause                                                                           | Fix                                                         |
|------------------------------------------------------------|---------------------------------------------------------------------------------|-------------------------------------------------------------|
| `violates foreign key constraint "order_lines_product_fk"` | A real DELETE of a product that orders use.                                     | Archive it; RESTRICT is doing its job.                      |
| A new product refused with the name of an archived one     | A plain unique index on the name.                                               | A partial index: `WHERE archived_at IS NULL`.               |
| `updated_at` never changes                                 | Changed with a bulk query (`UPDATE ... ` in JPQL or SQL): callbacks do not run. | Change managed entities, or set the column in the query.    |
| Archived products appear in the shop                       | A query without the archive filter.                                             | Every customer-facing query filters; test the default list. |
| `products_updated_after_created` on insert                 | Times set by hand in two calls to `now()` in Java.                              | One value for both in `@PrePersist`.                        |

## Project layout

``` tree
stations/054-archiving-seller-products/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/catalog/
│   ├── SellerProductController.java   ├── SellerCatalog.java   ├── Product.java
│   ├── ProductRepository.java   └── CatalogApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__sellers_products_orders.sql, V2__demo_catalogue.sql
├── src/test/java/com/kartwala/catalog/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the entity and the database.

#### `src/main/java/com/kartwala/catalog/SellerProductController.java`

Does  
Reads the seller from the header; DELETE archives; GET lists.

Why  
HTTP only.

Without it  
Real deletes behind a DELETE verb.

#### `src/main/java/com/kartwala/catalog/SellerCatalog.java`

Does  
Archives one of the seller's products; lists active or all.

Why  
"Delete" is a state change in one transaction.

Without it  
Lost order lines.

- Another seller's product is `404`, so ids reveal nothing.
- The entity is managed: no `save()`; the UPDATE goes at commit.

#### `src/main/java/com/kartwala/catalog/Product.java`

Does  
The product row with archive date and timestamps.

Why  
`@PrePersist` and `@PreUpdate` stamp every write; `archive()` keeps the first date.

Without it  
Rows with no update time, or a time that lies.

- `@PreUpdate` runs only when Hibernate sends an UPDATE, which it does only when a field really changed.
- Times are cut to microseconds, what PostgreSQL keeps.

#### `src/main/java/com/kartwala/catalog/ProductRepository.java`

Find one of a seller's products; list active or all.

#### `src/main/resources/db/migration/V1__sellers_products_orders.sql`

The tables, `ON DELETE RESTRICT`, the named checks and the partial unique index.

#### `src/main/resources/db/migration/V2__demo_catalogue.sql`

Two sellers, three products, one past order.

#### `src/main/resources/application.yaml`

open-in-view off; schema validation.

#### `src/main/java/com/kartwala/catalog/CatalogApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                      | Result |
|---------------|-------------------------------------------------------|---------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `SellerProductContractTest` (4) | pass   |
| Every station | Reproduce the failure before the fix                  | `HardDeleteTrapTest` (3)        | pass   |
| Database      | Rollback and constraint tests against a real database | `ProductDatabaseTest` (4)       | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.catalog.ProductDatabaseTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.catalog.HardDeleteTrapTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.catalog.SellerProductContractTest
[INFO] Tests run: 11, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/kartwala/catalog/HardDeleteTrapTest.java`

Written first: the old CASCADE in a rolled-back transaction, today's RESTRICT, and the API's archive.

#### `src/test/java/com/kartwala/catalog/SellerProductContractTest.java`

Archive, list, idempotent DELETE, and every refusal.

#### `src/test/java/com/kartwala/catalog/ProductDatabaseTest.java`

Named constraints, the partial index, callbacks against the rows, and a rollback.

#### `src/test/java/com/kartwala/catalog/ApiTest.java`

Shared setup: the demo catalogue reset before each test.

#### `src/test/java/com/kartwala/catalog/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/kartwala/catalog/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=RestoreChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 11 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 14 tests pass (11 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Restore a product

Add `POST /seller/products/{id}/restore`: back on sale, `updatedAt` moved. If the seller has since listed another product with the same name, the partial unique index refuses: `409`.

**Done when:** both tests in `RestoreChallengeTest` pass.

Hints

- Clear `archivedAt`; `@PreUpdate` does the rest.
- Flush inside a `try`, so the index's refusal arrives where you can answer it.

#### `challenge/RestoreChallengeTest.java`

``` code
package com.kartwala.catalog;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /seller/products/{id}/restore puts an archived product back on sale (archivedAt cleared,
 * updatedAt moved). If the seller has since listed another product with the same name, the database refuses: 409.
 */
class RestoreChallengeTest extends ApiTest {

    @Test
    void anArchivedProductComesBack() throws Exception {
        archive(1, 1);
        mvc.perform(post("/seller/products/1/restore").header("X-Seller-Id", 1)).andExpect(status().isOk())
                .andExpect(jsonPath("$.archived").value(false)).andExpect(jsonPath("$.archivedAt").doesNotExist());
        list(1, null).andExpect(jsonPath("$.length()").value(2));
        mvc.perform(post("/seller/products/1/restore").header("X-Seller-Id", 2)).andExpect(status().isNotFound());
    }

    @Test
    void notOverAnotherProductWithTheSameName() throws Exception {
        archive(1, 1);
        jdbc.sql("INSERT INTO products (seller_id, name, price_paise, created_at, updated_at) VALUES (1, 'Assam Tea, 500 g', 37900, now(), now())").update();
        mvc.perform(post("/seller/products/1/restore").header("X-Seller-Id", 1)).andExpect(status().isConflict());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 25 minutes

## Purge what no order had

Add `?purge=true` to DELETE: a real delete of an archived product no order ever had. Still on sale, or in an order: `409`. Let RESTRICT decide the second.

**Done when:** the test in `PurgeChallengeTest` passes.

Hints

- Delete and flush; catch `DataIntegrityViolationException`.
- A count of order lines in Java first would race with a new order.

#### `challenge/PurgeChallengeTest.java`

``` code
package com.kartwala.catalog;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: DELETE /seller/products/{id}?purge=true really deletes an archived product that no order ever had:
 * 204, and it is gone even with includeArchived. A product still on sale, or one that orders point at, is 409; let
 * the database's RESTRICT decide the second, not a count in Java.
 */
class PurgeChallengeTest extends ApiTest {

    @Test
    void onlyArchivedProductsNoOrderHadCanBePurged() throws Exception {
        jdbc.sql("INSERT INTO products (id, seller_id, name, price_paise, archived_at, created_at, updated_at) VALUES (40, 1, 'Typo prodcut', 100, now(), now(), now())").update();
        mvc.perform(delete("/seller/products/40").param("purge", "true").header("X-Seller-Id", 1)).andExpect(status().isNoContent());
        assertThat(jdbc.sql("SELECT count(*) FROM products WHERE id = 40").query(Long.class).single()).isZero();

        mvc.perform(delete("/seller/products/2").param("purge", "true").header("X-Seller-Id", 1)).andExpect(status().isConflict());   // still on sale
        archive(1, 1);
        mvc.perform(delete("/seller/products/1").param("purge", "true").header("X-Seller-Id", 1)).andExpect(status().isConflict());   // in KW-1001
        assertThat(linesOfOrder("KW-1001")).isEqualTo(2);
        mvc.perform(delete("/seller/products/999").param("purge", "true").header("X-Seller-Id", 1)).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Archive, history table, or copy into the order?

Three ways to keep orders readable: archive products (this station), move deleted products to a history table, or copy the product's name and price into each order line at purchase. For each, what happens when a seller renames a product, and which one would an auditor prefer?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test with the old CASCADE, in a rolled-back transaction.
2.  Change the foreign key to RESTRICT, and decide what "delete" means for the seller: archive.
3.  Add timestamps with JPA callbacks and database checks.
4.  Make every uniqueness rule "among active rows" where archived rows should not count.

## Design alternatives and trade-offs

| Approach                                     | What it costs                                                                       | Verdict       |
|----------------------------------------------|-------------------------------------------------------------------------------------|---------------|
| Archive column + RESTRICT + explicit filters | Every query must remember the filter.                                               | Chosen        |
| Hard delete with CASCADE                     | History silently loses lines.                                                       | The trap      |
| Hard delete with SET NULL                    | Lines lose their product; names and links are gone.                                 | No            |
| Hibernate `@SoftDelete` or `@SQLRestriction` | Filters automatically, everywhere: also where order history needs the archived row. | Careful       |
| Copy name and price into each order line     | Orders read alone; a little duplication. Often done as well.                        | Good addition |

## Database design

| Table         | Constraints                                                                                                                                                        | Mapped as                               |
|---------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------|
| `products`    | `products_seller_fk`, `products_price_positive`, `products_updated_after_created`, `products_archived_after_created`; partial unique `products_seller_name_active` | `Product`, with callbacks               |
| `order_lines` | `order_lines_product_fk` (ON DELETE RESTRICT), `order_lines_quantity_positive`                                                                                     | Not mapped here: read with SQL in tests |

``` code
-- Kartwala's seller catalogue and the order lines that point at it.
CREATE TABLE sellers (
    id   BIGINT PRIMARY KEY,
    name VARCHAR(80) NOT NULL
);

CREATE TABLE products (
    id          BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    seller_id   BIGINT       NOT NULL,
    name        VARCHAR(120) NOT NULL,
    price_paise BIGINT       NOT NULL,
    archived_at TIMESTAMPTZ,              -- NULL: on sale. A date: archived, kept for order history.
    created_at  TIMESTAMPTZ  NOT NULL,
    updated_at  TIMESTAMPTZ  NOT NULL,
    CONSTRAINT products_seller_fk FOREIGN KEY (seller_id) REFERENCES sellers (id),
    CONSTRAINT products_price_positive CHECK (price_paise > 0),
    CONSTRAINT products_updated_after_created CHECK (updated_at >= created_at),
    CONSTRAINT products_archived_after_created CHECK (archived_at IS NULL OR archived_at >= created_at)
);

-- One product per name per seller among the ones on sale; an archived "Assam tea" does not block a new one.
CREATE UNIQUE INDEX products_seller_name_active ON products (seller_id, lower(name)) WHERE archived_at IS NULL;

CREATE TABLE order_lines (
    id               BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    order_ref        VARCHAR(20) NOT NULL,
    product_id       BIGINT      NOT NULL,
    quantity         INT         NOT NULL,
    unit_price_paise BIGINT      NOT NULL,
    -- RESTRICT: a product that any order line points at cannot be deleted. The order history can never lose a line.
    CONSTRAINT order_lines_product_fk FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE RESTRICT,
    CONSTRAINT order_lines_quantity_positive CHECK (quantity > 0)
);

CREATE INDEX order_lines_product ON order_lines (product_id);
```

# 3 · Go deeper: Production

Changing a live foreign key  
Dropping CASCADE and adding RESTRICT is a migration: drop the old constraint, add the new one (`NOT VALID`, then `VALIDATE CONSTRAINT`, on big tables).

Lines already lost  
Orders whose lines were cascaded away need rebuilding from payments, invoices or backups. Find them by comparing order totals with their lines.

Privacy  
Soft delete keeps data. For personal data a person asks to erase, archive is not enough; anonymise the fields instead.

Index the filter  
Most queries ask for active rows; a partial index `WHERE archived_at IS NULL` keeps them fast.

# 3 · Go deeper: Interview

## Interview takeaways

Soft delete or hard delete?

Soft delete when other records refer to the row or history matters (products in orders, accounts). Hard delete when nothing refers to it, or when the law requires erasure.

What does ON DELETE RESTRICT protect?

Rows that point at the one being deleted. The delete fails instead of leaving them dangling or deleting them with it, whatever code tried it.

How do @PrePersist and @PreUpdate work?

JPA calls them just before it sends the INSERT or UPDATE for an entity. @PreUpdate only runs when dirty checking found a change, and never for bulk JPQL or SQL updates.

Why a partial unique index with soft delete?

Archived rows still exist. A plain unique index would stop a seller from re-listing a product with an old name; the partial index applies uniqueness to active rows only.

What does soft delete cost?

Every query must filter archived rows, tables keep growing, and uniqueness rules need care. In return, nothing that history depends on can vanish.

## Self-check rubric

| Area         | Meets the bar         | Above the bar                                     |
|--------------|-----------------------|---------------------------------------------------|
| Correctness  | All 11 tests pass.    | You tried the real DELETE in psql.                |
| Foreign keys | RESTRICT on history.  | An ON DELETE choice for every key, with a reason. |
| Timestamps   | Callbacks and checks. | You know when callbacks do not run.               |
| Soft delete  | Filtered lists.       | A partial index for active-only uniqueness.       |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any delete:

- What points at this row, and what does each foreign key's ON DELETE say?
- Does anything (orders, invoices, audits) need the row after it is "gone"?
- Does every customer-facing query filter archived rows?
- Do uniqueness rules still make sense with archived rows in the table?
