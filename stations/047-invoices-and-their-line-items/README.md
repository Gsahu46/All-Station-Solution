# Station 047 · Invoices and their line items

Foundations · 0–1 years · Core · B2B SaaS · Types: Database

Spring Boot 4.1.1 · Java 25 · Spring Data JPA (Hibernate 7) · @OneToMany / @ManyToOne · cascade, orphanRemoval · PostgreSQL 17 · Flyway · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Customers, prices and invoices are demo data, not Billora's. An invoice is a record; nothing is sent, filed with a tax authority or paid.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 10 tests.

# 1 · Understand

## The problem in real life

1.  **A corrected invoice**

    A customer disputed 2 of 6 support hours. The account manager edited the invoice: the screen showed the corrected lines and ₹10,999.

2.  **The old lines came back**

    Opened again, the invoice had four lines and ₹24,998. The finance report, which sums the lines table, had counted the old ones all along.

3.  **The fix**

    Lines taken out of an invoice are deleted (orphanRemoval), lines are added through one helper that sets both sides, and a test reads the table, not just the response.

Removing a child from a Java list is not a DELETE. Say what should happen to it, and check the table.

## What are we building?

Create an invoice with its lines (`POST /invoices`), replace its lines (`PUT /invoices/{id}/lines`), and read it with its total (`GET /invoices/{id}`). After a replacement, the table holds exactly the new lines.

## An everyday analogy

A ring binder of bills, each with item slips clipped to it. Unclipping a slip from the bill in your hand does not take it out of the binder: the slip still says which bill it belongs to, and whoever adds up the binder counts it. Orphan removal is the rule "an unclipped slip goes in the shredder".

## How it works in 4 steps

1.  **The replacement loads** the invoice and its lines in one query.
2.  **It clears** the list and adds the new lines through the helper, which also sets each line's invoice.
3.  **At commit**, Hibernate deletes the lines that left the list and inserts the new ones.
4.  **Every reader**, the API or a SQL report, sees only the new lines.

Check yourself: the old code had `cascade = ALL`. Why did that not delete the old lines?

Cascade repeats operations done to the parent (save it, delete it) on its children. Clearing a list is not an operation on the parent. Only `orphanRemoval` turns "no longer in the list" into a DELETE.

## What this station is not

- **No tax or GST.** Challenge 2 adds a rate per line.
- **No issuing.** Real invoices are locked once issued and corrected with credit notes (challenge 3).
- **No concurrent edits.** Two replacements at the same moment are not handled here.

## Key terms

| Term                     | Simple meaning                                                | Everyday example                                                        | In this project                            |
|--------------------------|---------------------------------------------------------------|-------------------------------------------------------------------------|--------------------------------------------|
| **Parent and child**     | One invoice has many lines; each line belongs to one invoice. | A bill and the items printed on it.                                     | `Invoice`, `InvoiceLine`                   |
| **Owning side**          | The side whose field becomes the foreign key column.          | The item's own note saying which bill it is on.                         | `InvoiceLine.invoice` → `invoice_id`       |
| **Cascade**              | An operation on the parent is repeated on its children.       | Filing the bill files its items with it.                                | `cascade = ALL`                            |
| **Orphan removal**       | A child taken out of its parent's list is deleted.            | An item crossed off the bill is thrown away, not left in the drawer.    | `orphanRemoval = true`                     |
| **Bidirectional helper** | One method that sets both sides of the link.                  | Writing the item on the bill and the bill number on the item, together. | `addLine`                                  |
| **LAZY loading**         | Children are read from the database only when first used.     | Opening the folder only when you need the items.                        | `@EntityGraph` loads them with the invoice |

# 2 · Build: Spec

## Business problem

**Billora** (a fictional B2B invoicing SaaS) lets account managers correct an invoice's lines. Removed lines stayed in the database and kept counting in totals and reports.

## Acceptance criteria

1.  **Given** hosting (₹4,999) and 6 support hours at ₹1,500, **then** `201`, a `Location`, and ₹13,999.
2.  **Given** the lines are replaced with hosting and 4 hours, **then** `200` with ₹10,999, `GET` shows those 2 lines, and the table holds 2 rows for the invoice.
3.  **Given** no lines, a blank name, quantity 0, a missing quantity, or a price with decimals, **then** `400` and nothing changes.
4.  **Given** a replacement the database refuses, **then** the old lines are all still there.
5.  **Given** an unknown invoice, **then** `404`.

## Requirements

- A line belongs to exactly one invoice, also in the database (`NOT NULL` and a named foreign key).
- Lines removed from an invoice are deleted in the same transaction.
- Totals are computed from the lines, in integer paise.
- Reading an invoice with its lines is one query.

## Learning objectives

- Map a bidirectional `@OneToMany` / `@ManyToOne` and know which side owns the column.
- Choose between cascade and orphanRemoval, and know what each does.
- Keep both sides in step with helper methods and a read-only list.
- Load a LAZY collection on purpose, not by accident.

# 2 · Build: API contract

## Endpoints

| Method | Path                   | Purpose                                                                                             |
|--------|------------------------|-----------------------------------------------------------------------------------------------------|
| `POST` | `/invoices`            | Create: `customerName` and 1 to 50 lines (`description`, `quantity` 1 to 10,000, `unitPricePaise`). |
| `PUT`  | `/invoices/{id}/lines` | Replace every line with the ones sent.                                                              |
| `GET`  | `/invoices/{id}`       | The invoice, its lines and the total.                                                               |

## Status codes

| Status | When                                                                                      |
|--------|-------------------------------------------------------------------------------------------|
| 201    | Created; `Location` points at it                                                          |
| 200    | Lines replaced; or the invoice                                                            |
| 400    | A field missing or out of range, no lines, or a price that is not a whole number of paise |
| 404    | No such invoice                                                                           |

## Captured examples

Captured with curl from the running app on 15 Oct 2026, in this order, against one fresh database. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: an invoice with two lines

**Why:** lines saved with the invoice (cascade); total ₹13,999.

Request

``` code
POST /invoices HTTP/1.1
Content-Type: application/json

{
  "customerName": "Kaveri Textiles Pvt Ltd",
  "lines": [
    {
      "description": "Cloud hosting, March 2026",
      "quantity": 1,
      "unitPricePaise": 499900
    },
    {
      "description": "Support hours",
      "quantity": 6,
      "unitPricePaise": 150000
    }
  ]
}
```

Response

``` code
HTTP/1.1 201 
Location: /invoices/1
Content-Type: application/json

{
  "id": 1,
  "customerName": "Kaveri Textiles Pvt Ltd",
  "lines": [
    {
      "description": "Cloud hosting, March 2026",
      "quantity": 1,
      "unitPricePaise": 499900,
      "amountPaise": 499900
    },
    {
      "description": "Support hours",
      "quantity": 6,
      "unitPricePaise": 150000,
      "amountPaise": 900000
    }
  ],
  "totalPaise": 1399900
}
```

### Case 2: 4 support hours instead of 6

**Why:** the new lines and ₹10,999...

Request

``` code
PUT /invoices/1/lines HTTP/1.1
Content-Type: application/json

{
  "lines": [
    {
      "description": "Cloud hosting, March 2026",
      "quantity": 1,
      "unitPricePaise": 499900
    },
    {
      "description": "Support hours",
      "quantity": 4,
      "unitPricePaise": 150000
    }
  ]
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 272

{
  "id": 1,
  "customerName": "Kaveri Textiles Pvt Ltd",
  "lines": [
    {
      "description": "Cloud hosting, March 2026",
      "quantity": 1,
      "unitPricePaise": 499900,
      "amountPaise": 499900
    },
    {
      "description": "Support hours",
      "quantity": 4,
      "unitPricePaise": 150000,
      "amountPaise": 600000
    }
  ],
  "totalPaise": 1099900
}
```

### Case 3: read it back

**Why:** ...and still only those two lines. This is the read the old code got wrong.

Request

``` code
GET /invoices/1 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 272

{
  "id": 1,
  "customerName": "Kaveri Textiles Pvt Ltd",
  "lines": [
    {
      "description": "Cloud hosting, March 2026",
      "quantity": 1,
      "unitPricePaise": 499900,
      "amountPaise": 499900
    },
    {
      "description": "Support hours",
      "quantity": 4,
      "unitPricePaise": 150000,
      "amountPaise": 600000
    }
  ],
  "totalPaise": 1099900
}
```

### Case 4: an empty list of lines

**Why:** an invoice needs at least one line: `400`.

Request

``` code
PUT /invoices/1/lines HTTP/1.1
Content-Type: application/json

{
  "lines": []
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/invoices/1/lines",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 5: `1500.50` as a price in paise

**Why:** refused, not truncated to 1500: `400`.

Request

``` code
PUT /invoices/1/lines HTTP/1.1
Content-Type: application/json

{
  "lines": [
    {
      "description": "Cloud hosting, March 2026",
      "quantity": 1,
      "unitPricePaise": 499900
    },
    {
      "description": "Support hours",
      "quantity": 4,
      "unitPricePaise": 1500.5
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
  "instance": "/invoices/1/lines",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 6: invoice 99

**Why:** `404`.

Request

``` code
GET /invoices/99 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No invoice 99.",
  "instance": "/invoices/99",
  "status": 404,
  "title": "Invoice not found"
}
```

## What the table holds

Read with psql after the requests above (`docs/captures/rows.txt`). Rows 1 and 2, the original lines, were deleted by the replacement.

``` code
 id | invoice_id |        description        | quantity | unit_price_paise 
----+------------+---------------------------+----------+------------------
  3 |          1 | Cloud hosting, March 2026 |        1 |           499900
  4 |          1 | Support hours             |        4 |           150000
(2 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                           | What happens                                       | Proved by                                        |
|----------------------------------------------------------------|----------------------------------------------------|--------------------------------------------------|
| Create, then read                                              | Lines and total                                    | `anInvoiceIsCreatedWithItsLinesAndTotal`         |
| Replace twice, down to one line                                | Only the latest lines remain                       | `replacingLinesKeepsOnlyTheNewOnes`              |
| No lines, blank name, quantity 0 or missing, decimals in paise | `400`, invoice unchanged                           | `badInvoicesAre400`                              |
| Unknown invoice                                                | `404`                                              | `unknownInvoicesAre404`                          |
| Bad rows written directly; deleting an invoice that has lines  | Refused by named constraints                       | `namedConstraintsHoldWithoutJava`                |
| A replacement the database refuses halfway                     | Old lines all kept: deletes roll back with inserts | `aReplacementTheDatabaseRefusesKeepsTheOldLines` |
| Reading an invoice                                             | One query, lines included                          | `readingAnInvoiceWithItsLinesIsOneQuery`         |

## The trap

Plausible but wrong

Removing a line from the collection without orphanRemoval, leaving orphan rows.

The old mapping is kept in the tests as `OldInvoice`, on the same tables: `cascade = ALL`, no `orphanRemoval`, and a list anyone can change. The old replacement clears the list and adds the corrected lines. The new lines are inserted (cascade), the old ones are never deleted, and they still carry `invoice_id = 1`. The table has 4 rows; the API and a SUM both say ₹24,998.

The third test shows the other half of a bidirectional mapping: adding a line to the list without setting the line's invoice. The list is not what fills `invoice_id`; the line's own field is, so PostgreSQL refuses a line with no invoice.

While building, each part was undone once. Without `orphanRemoval`, 2 tests turned red; without the back reference in `addLine`, 9 (no invoice could be saved); without the `@EntityGraph`, 1. Replacing the list object (`lines = new ArrayList<>()`) instead of clearing it turned 2 red with Hibernate's `A collection with orphan deletion was no longer referenced by the owning entity instance`. Separately, the contract test found a real bug while the station was built: Jackson turned `1500.50` into 1500 paise without a word, until `accept-float-as-int` was switched off.

``` code
package com.billora.invoicing;

import jakarta.persistence.EntityManager;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * The first test written for this station: the old line replacement, with the old mapping, on the same tables. The
 * lines leave the Java list but never leave the table, so the next read brings them back.
 */
class OrphanLinesTrapTest extends ApiTest {

    @Autowired
    EntityManager entities;
    @Autowired
    TransactionTemplate transaction;

    /** The old PUT: clear the list, add the corrected lines. Exactly what Invoice.replaceLines does, minus orphanRemoval. */
    void oldReplace(long id) {
        transaction.executeWithoutResult(status -> {
            OldInvoice invoice = entities.find(OldInvoice.class, id);
            invoice.getLines().clear();
            invoice.getLines().add(new OldInvoice.Line(invoice, "Cloud hosting, March 2026", 1, 499900));
            invoice.getLines().add(new OldInvoice.Line(invoice, "Support hours", 4, 150000));
        });
    }

    @Test
    void withoutOrphanRemovalTheOldLinesStayAndCount() throws Exception {
        create(INVOICE);
        oldReplace(1);
        assertThat(lineRows(1)).isEqualTo(4);                 // 2 new rows, and the 2 "removed" ones
        assertThat(sumOfLineRows(1)).isEqualTo(2_499_800);    // ₹13,999 + ₹10,999 instead of ₹10,999
        mvc.perform(get("/invoices/1"))
                .andExpect(jsonPath("$.lines.length()").value(4))
                .andExpect(jsonPath("$.totalPaise").value(2_499_800));
    }

    @Test
    void withOrphanRemovalTheyAreDeleted() throws Exception {
        create(INVOICE);
        replaceLines(1, CORRECTED);
        assertThat(lineRows(1)).isEqualTo(2);
        assertThat(sumOfLineRows(1)).isEqualTo(1_099_900);
    }

    @Test
    void addingToTheListWithoutTheBackReferenceLeavesInvoiceIdEmpty() throws Exception {
        create(INVOICE);
        // invoice_id comes from line.invoice (the owning side), not from the list: the list alone says nothing.
        assertThatThrownBy(() -> transaction.executeWithoutResult(status ->
                entities.find(OldInvoice.class, 1L).getLines().add(new OldInvoice.Line(null, "Domain renewal", 1, 99900))))
                .hasMessageContaining("invoice_id");
        assertThat(lineRows(1)).isEqualTo(2);
    }
}
```

``` code
package com.billora.invoicing;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;

import java.util.ArrayList;
import java.util.List;

/**
 * The mapping as it shipped, kept only in tests, on the same tables: cascade ALL but no orphanRemoval, and a public,
 * modifiable list. Only the annotations differ from Invoice.
 */
@Entity
@Table(name = "invoices")
public class OldInvoice {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    Long id;
    String customerName;
    @OneToMany(mappedBy = "invoice", cascade = CascadeType.ALL)
    List<Line> lines = new ArrayList<>();

    public List<Line> getLines() {
        return lines;
    }

    @Entity(name = "OldInvoiceLine")
    @Table(name = "invoice_lines")
    public static class Line {
        @Id
        @GeneratedValue(strategy = GenerationType.IDENTITY)
        Long id;
        @ManyToOne(fetch = FetchType.LAZY, optional = false)
        @JoinColumn(name = "invoice_id")
        OldInvoice invoice;
        String description;
        int quantity;
        long unitPricePaise;

        Line() {
        }

        Line(OldInvoice invoice, String description, int quantity, long unitPricePaise) {
            this.invoice = invoice;
            this.description = description;
            this.quantity = quantity;
            this.unitPricePaise = unitPricePaise;
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
docker compose up -d        # PostgreSQL 17 on localhost:5432
./mvnw spring-boot:run      # the API on http://localhost:8080
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

Remove `, orphanRemoval = true` from `Invoice`, start the app, and run the captured requests 1 to 3. Then look at the table:

``` code
docker compose exec postgres psql -U billora -d billora -c "SELECT id, invoice_id, quantity FROM invoice_lines"
```

Four rows for one invoice, and the read returns all four. Put the attribute back.

## Troubleshooting

| You see                                                                                    | Cause                                                | Fix                                                         |
|--------------------------------------------------------------------------------------------|------------------------------------------------------|-------------------------------------------------------------|
| Removed children come back on the next read                                                | No `orphanRemoval`: the rows were never deleted.     | `orphanRemoval = true`, or delete them yourself.            |
| `A collection with orphan deletion was no longer referenced by the owning entity instance` | The list field was replaced with a new list.         | `clear()` and `add` on the same list.                       |
| `null value in column "invoice_id"`                                                        | A child added to the list without its parent set.    | Add through a helper that sets both sides.                  |
| `LazyInitializationException ... no session`                                               | Lines read after the transaction.                    | Load them in the service (`@EntityGraph`) and map there.    |
| A price like `1500.50` saved as 1500                                                       | Jackson's default turns decimals into whole numbers. | `spring.jackson.deserialization.accept-float-as-int: false` |

## Project layout

``` tree
stations/047-invoices-and-their-line-items/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/billora/invoicing/
│   ├── InvoiceController.java   ├── InvoiceBook.java   ├── Invoice.java   ├── InvoiceLine.java
│   ├── InvoiceRepository.java   └── InvoicingApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__invoices_and_lines.sql
├── src/test/java/com/billora/invoicing/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the entities and the database.

#### `src/main/java/com/billora/invoicing/InvoiceController.java`

Does  
Validates bodies (limits, at least one line) and calls the book.

Why  
HTTP only.

Without it  
Entity lists exposed to the client.

#### `src/main/java/com/billora/invoicing/InvoiceBook.java`

Does  
Creates invoices, replaces lines, reads them; builds the response inside the transaction.

Why  
Each change is one `@Transactional` method.

Without it  
Lazy lines read after the transaction ended.

#### `src/main/java/com/billora/invoicing/Invoice.java`

Does  
The invoice and its lines.

Why  
`orphanRemoval` deletes what leaves the list; helpers set both sides; the list is read-only outside.

Without it  
Orphan rows, and lines with no invoice.

- `replaceLines` clears the same list object: Hibernate tracks that object, so replacing it fails.
- The total is computed from the lines, never stored apart from them.

#### `src/main/java/com/billora/invoicing/InvoiceLine.java`

Does  
One line; `@ManyToOne(LAZY)` to its invoice, the owning side.

Why  
Its `invoice` field is the `invoice_id` column.

Without it  
A list change that never reaches the column.

#### `src/main/java/com/billora/invoicing/InvoiceRepository.java`

`findWithLinesById`: the invoice and its lines in one query.

#### `src/main/resources/db/migration/V1__invoices_and_lines.sql`

Both tables, the named constraints, an index on `invoice_id`.

#### `src/main/resources/application.yaml`

open-in-view off; schema validation; decimals refused for whole-number fields.

#### `src/main/java/com/billora/invoicing/InvoicingApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                | Result |
|---------------|-------------------------------------------------------|---------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `InvoiceContractTest` (4) | pass   |
| Every station | Reproduce the failure before the fix                  | `OrphanLinesTrapTest` (3) | pass   |
| Database      | Rollback and constraint tests against a real database | `InvoiceDatabaseTest` (3) | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.billora.invoicing.InvoiceContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.billora.invoicing.InvoiceDatabaseTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.billora.invoicing.OrphanLinesTrapTest
[INFO] Tests run: 10, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/billora/invoicing/OrphanLinesTrapTest.java`

Written first: the old mapping leaves rows; the fixed one deletes them; a list change alone fills no column.

#### `src/test/java/com/billora/invoicing/InvoiceContractTest.java`

Create, replace, read, and every refusal.

#### `src/test/java/com/billora/invoicing/InvoiceDatabaseTest.java`

Named constraints, a replacement rolled back whole, one query per read.

#### `src/test/java/com/billora/invoicing/OldInvoice.java`

The old mapping on the same tables, kept only in tests.

#### `src/test/java/com/billora/invoicing/ApiTest.java`

Shared setup: the demo invoice, and SQL counts of the line rows.

#### `src/test/java/com/billora/invoicing/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/billora/invoicing/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=RemoveLineChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 10 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in (Java files and one migration), all 14 tests pass (10 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Remove one line

Add `DELETE /invoices/{id}/lines/{position}`: the line at that position (1 = first) is removed and its row deleted. The last line stays (`409`); a missing position or invoice is `404`.

**Done when:** both tests in `RemoveLineChallengeTest` pass.

Hints

- A `removeLine` helper on `Invoice`; orphanRemoval does the DELETE.
- Check the position against the list before removing.

#### `challenge/RemoveLineChallengeTest.java`

``` code
package com.billora.invoicing;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: DELETE /invoices/{id}/lines/{position} removes one line (1 = the first, in the order returned) and
 * returns the invoice. The row must be gone from the table. The last line cannot be removed (409); a position or
 * invoice that does not exist is 404.
 */
class RemoveLineChallengeTest extends ApiTest {

    @Test
    void removingALineDeletesItsRow() throws Exception {
        create(INVOICE);
        mvc.perform(delete("/invoices/1/lines/2")).andExpect(status().isOk())
                .andExpect(jsonPath("$.lines.length()").value(1)).andExpect(jsonPath("$.totalPaise").value(499900));
        assertThat(lineRows(1)).isEqualTo(1);
        assertThat(sumOfLineRows(1)).isEqualTo(499900);
        mvc.perform(delete("/invoices/1/lines/1")).andExpect(status().isConflict());   // an invoice keeps at least one line
    }

    @Test
    void missingPositionsAndInvoicesAre404() throws Exception {
        create(INVOICE);
        mvc.perform(delete("/invoices/1/lines/3")).andExpect(status().isNotFound());
        mvc.perform(delete("/invoices/1/lines/0")).andExpect(status().isNotFound());
        mvc.perform(delete("/invoices/99/lines/1")).andExpect(status().isNotFound());
        assertThat(lineRows(1)).isEqualTo(2);
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Tax per line

Each line may carry `taxPercent` (0 to 40, absent means 0). Show each line's tax, rounded half up to the paisa, the invoice's tax, and a total that includes it. Store the rate with a named check.

**Done when:** both tests in `LineTaxChallengeTest` pass.

Hints

- A migration adds `tax_percent` with a default, so existing rows stay valid.
- Integer rounding half up: `(amount × rate + 50) / 100`. Never `double` for money.

#### `challenge/LineTaxChallengeTest.java`

``` code
package com.billora.invoicing;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: each line may carry "taxPercent" (a whole number from 0 to 40; absent means 0). A line's taxPaise is
 * amountPaise × taxPercent / 100, rounded half up to the paisa; the invoice shows taxPaise (the sum) and totalPaise
 * (amounts plus tax). The table stores the rate, with a named check. Rates are a demo rule, not tax advice.
 */
class LineTaxChallengeTest extends ApiTest {

    @Test
    void taxIsComputedPerLineAndRounded() throws Exception {
        create("""
                {"customerName":"Kaveri Textiles Pvt Ltd","lines":[
                  {"description":"Cloud hosting, March 2026","quantity":1,"unitPricePaise":499900,"taxPercent":18},
                  {"description":"Printed manual","quantity":1,"unitPricePaise":999,"taxPercent":5},
                  {"description":"Training voucher","quantity":1,"unitPricePaise":50000}]}""")
                .andExpect(status().isCreated())
                .andExpect(content().json("""
                        {"lines":[{"taxPercent":18,"taxPaise":89982},{"taxPercent":5,"taxPaise":50},{"taxPercent":0,"taxPaise":0}],
                         "taxPaise":90032,"totalPaise":640931}"""));
    }

    @Test
    void ratesOutsideTheRangeAreRefused() throws Exception {
        create(INVOICE.replace("\"quantity\":6,", "\"quantity\":6,\"taxPercent\":41,")).andExpect(status().isBadRequest());
        create(INVOICE).andExpect(status().isCreated());
        assertThatThrownBy(() -> jdbc.sql("UPDATE invoice_lines SET tax_percent = -1").update()).hasMessageContaining("invoice_lines_tax_range");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Correcting an issued invoice

Once an invoice is sent, accountants do not edit it: they issue a credit note against it. Design the tables and the endpoint for a credit note that reverses some lines of an issued invoice, and decide what `PUT /invoices/{id}/lines` should answer for an issued one.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test against the table: count the rows, sum them, not just the API answer.
2.  Decide the lifecycle: lines live and die with their invoice, so cascade and orphanRemoval.
3.  Make the list read-only outside the entity and add helpers that set both sides.
4.  Load lines on purpose with an entity graph; count the queries once.

## Design alternatives and trade-offs

| Approach                                       | What it costs                                                          | Verdict                 |
|------------------------------------------------|------------------------------------------------------------------------|-------------------------|
| `cascade = ALL` + `orphanRemoval`, helpers     | Children cannot be shared or moved between parents.                    | Chosen                  |
| `cascade = ALL` only                           | Removed lines stay in the table.                                       | The trap                |
| Delete lines with a query, then insert         | Works, but the loaded list is now stale in memory.                     | Careful                 |
| Unidirectional `@OneToMany` with `@JoinColumn` | Hibernate may insert, then update the foreign key: extra statements.   | Fewer helpers, more SQL |
| Lines as an `@ElementCollection`               | No identity of their own; the whole collection is rewritten on change. | For small value lists   |

## Database design

| Table           | Constraints                                                                                                 | Mapped as                                                                          |
|-----------------|-------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| `invoices`      | `invoices_customer_not_blank`                                                                               | `Invoice`, `@OneToMany(mappedBy = "invoice", cascade = ALL, orphanRemoval = true)` |
| `invoice_lines` | `invoice_lines_invoice_fk` (no cascade delete), `invoice_lines_quantity_range`, `invoice_lines_price_range` | `InvoiceLine`, `@ManyToOne(fetch = LAZY, optional = false)`                        |

``` code
-- Billora invoices: an invoice and its lines. A line always belongs to exactly one invoice.
CREATE TABLE invoices (
    id            BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    customer_name VARCHAR(80) NOT NULL,
    CONSTRAINT invoices_customer_not_blank CHECK (btrim(customer_name) <> '')
);

CREATE TABLE invoice_lines (
    id               BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    invoice_id       BIGINT       NOT NULL,
    description      VARCHAR(120) NOT NULL,
    quantity         INT          NOT NULL,
    unit_price_paise BIGINT       NOT NULL,
    CONSTRAINT invoice_lines_invoice_fk FOREIGN KEY (invoice_id) REFERENCES invoices (id),
    CONSTRAINT invoice_lines_quantity_range CHECK (quantity BETWEEN 1 AND 10000),
    CONSTRAINT invoice_lines_price_range CHECK (unit_price_paise BETWEEN 1 AND 10000000000)
);

CREATE INDEX invoice_lines_invoice ON invoice_lines (invoice_id);
```

# 3 · Go deeper: Production

Find orphans you already have  
Compare what users saw with what the table holds: totals in documents sent versus a SUM over lines. A one-off script then deletes or flags the extra rows, after finance agrees.

Issued documents  
Invoices are legal records once sent. Real systems lock them and correct with credit notes; editing lines is for drafts.

Reports read tables  
Anything that sums a child table directly (BI tools, SQL reports) trusts that the table holds only live rows. That is why orphans cost more than a wrong screen.

Large collections  
Loading every line to replace them is fine for 50; for thousands, page them and delete with a query.

# 3 · Go deeper: Interview

## Interview takeaways

What is the difference between cascade REMOVE and orphanRemoval?

Cascade REMOVE deletes children when the parent is deleted. orphanRemoval also deletes a child when it is removed from the parent's collection, while the parent lives on.

Which side owns a bidirectional one-to-many?

The many side (@ManyToOne): its field is the foreign key column. The @OneToMany(mappedBy) list is a mirror; changing only the list writes nothing to that column.

Why add helper methods?

So both sides change together. Otherwise the list and the foreign key disagree until the next load, and a child can be saved with no parent.

Why must you not replace a collection field with orphanRemoval?

Hibernate tracks the collection object it loaded. A new list object loses that tracking, and Hibernate refuses the flush rather than guess which children to delete.

Is @OneToMany LAZY by default?

Yes. Load it on purpose (an entity graph or a fetch join) when you need it, inside the transaction.

## Self-check rubric

| Area        | Meets the bar                                | Above the bar                                         |
|-------------|----------------------------------------------|-------------------------------------------------------|
| Correctness | All 10 tests pass.                           | You removed `orphanRemoval` and saw the rows in psql. |
| Mapping     | Owning side and `mappedBy` right.            | You can say when not to make it bidirectional.        |
| Lifecycle   | Cascade and orphanRemoval chosen on purpose. | Credit notes instead of edits for issued invoices.    |
| Loading     | Lines loaded in the service.                 | You counted the queries.                              |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any parent–child mapping:

- When a child leaves the parent's list, what happens to its row, and is that written down?
- Can anyone change the list without going through a helper?
- Does a test count rows in the table after a removal, not just read the response?
- Where are the children loaded, and how many queries does that take?
