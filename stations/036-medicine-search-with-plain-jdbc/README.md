# Station 036 · Medicine search with plain JDBC

Foundations · 0–1 years · Core · Healthcare · Types: Database

Spring Boot 4.1.1 · Java 25 · plain JDBC: DataSource, PreparedStatement, ResultSet · HikariCP · PostgreSQL 17 · Flyway · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The catalogue and prices are demo data, not Mediqo's. The prescriptions belong to fictional patients, with phone numbers that are not real; they exist so the trap test can show what the old search leaked.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 15 tests.

# 1 · Understand

## The problem in real life

1.  **A search box**

    Customers type a medicine name. The code glues their text into the SQL: `… WHERE name ILIKE '%` + text + `%'`.

2.  **Someone types SQL**

    One search for `x' UNION SELECT patient_name, patient_phone, doctor FROM prescriptions --` returns every patient's name, phone and doctor. A customer searching for St. John's Wort gets an error, and after a busy hour searches stop working: every search kept a database connection and never gave it back.

3.  **The fix**

    Fixed SQL with a `?`, the text sent as a parameter, wildcards escaped, and everything closed by try-with-resources.

User text is data. It goes into a parameter, never into the SQL itself.

## What are we building?

`GET /medicines?name=para` finds medicines whose name contains the text, in any letter case, with strength, form, price and whether a prescription is needed.

## An everyday analogy

A pharmacist's order form with a box for the medicine name. Whatever is written in the box is looked up as a name. Nobody reads it as an instruction to open the patient files.

## How it works in 4 steps

1.  **Check the text**: 2 to 50 characters.
2.  **Borrow a connection** from the pool.
3.  **Run fixed SQL** with the text as a parameter; read each row into a `Medicine`.
4.  **Close everything**: the connection goes back to the pool, whatever happened.

Check yourself: the box allows only 50 characters. Is that enough to stop injection?

No. `x' OR 1=1 --` is 12 characters and returned every medicine from the old code. Only parameters stop injection; length limits are for usability.

## What this station is not

- **No ORM.** Plain JDBC, every step visible; later stations use helpers.
- **No prescriptions endpoint.** The table exists so the trap can show what leaked.
- **No fuzzy search.** "Contains", not "sounds like".

## Key terms

| Term                          | Simple meaning                                                                     | Everyday example                                                                | In this project              |
|-------------------------------|------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|------------------------------|
| **JDBC**                      | Java's standard way to talk to a relational database.                              | A phone line to the database.                                                   | `java.sql`                   |
| **DataSource and Connection** | A DataSource hands out connections; a connection is one open line to the database. | A switchboard and one call.                                                     | `dataSource.getConnection()` |
| **Connection pool**           | A few connections kept open and lent out, because opening one is slow.             | Library books: borrow, then return.                                             | HikariCP                     |
| **PreparedStatement**         | SQL with `?` where values go; values are sent separately and never read as SQL.    | A form with boxes: whatever you write in a box stays in the box.                | `MedicineSearch`             |
| **SQL injection**             | User text that becomes part of the SQL and changes what the query does.            | Writing "and also give me the safe keys" on a bank slip, and the clerk obeying. | the trap                     |
| **try-with-resources**        | A `try` that closes what it opened, on every path.                                 | A door that shuts itself.                                                       | `try (Connection c = …)`     |

# 2 · Build: Spec

## Business problem

**Mediqo** (a fictional clinic and pharmacy chain) built its medicine search by string concatenation. One query dumped every customer's prescriptions.

## Acceptance criteria

1.  **Given** `name=PARA`, **then** the three paracetamol products, ordered by name, strength and form.
2.  **Given** `name=john's`, **then** St. John's Wort, not an error.
3.  **Given** an injection attempt such as `x' OR 1=1 --`, **then** an empty list: it is just text no medicine is named.
4.  **Given** `%%` or `a_`, **then** they match those characters, not "anything".
5.  **Given** 50 searches in a row, **then** no connection is left in use.
6.  **Given** a missing, blank, 1-character or 51-character name, **then** `400`. No match is `200` with an empty list.

## Requirements

- No user text in SQL text: values only through `PreparedStatement` parameters.
- Every JDBC resource is closed with try-with-resources.
- Catalogue rules are database constraints too: positive price, known form, one row per product.
- Money in integer paise; search text lower-cased with `Locale.ROOT`.

## Learning objectives

- Use `DataSource`, `Connection`, `PreparedStatement` and `ResultSet` directly.
- Explain and prevent SQL injection.
- Close resources on every path, and see what a leak does to a pool.
- Escape `LIKE` wildcards.

# 2 · Build: API contract

## Endpoint

| Method | Path                   | Purpose                                                           |
|--------|------------------------|-------------------------------------------------------------------|
| `GET`  | `/medicines?name=para` | Up to 20 medicines whose name contains the text, any letter case. |

## Status codes

| Status | When                                                           |
|--------|----------------------------------------------------------------|
| 200    | Results, possibly an empty list                                |
| 400    | No name, or blank, shorter than 2 or longer than 50 characters |

## Captured examples

Captured with curl from the running app on 15 Oct 2026. Special characters are URL-encoded in the address (`%27` is an apostrophe, `%25` a percent sign). JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: `para`

**Why:** a contains-search in any case; ordered by name, strength, form.

Request

``` code
GET /medicines?name=para HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 371

{
  "query": "para",
  "results": [
    {
      "id": 3,
      "name": "Paracetamol",
      "strength": "125 mg/5 ml",
      "form": "SYRUP",
      "pricePaise": 4500,
      "prescriptionRequired": false
    },
    {
      "id": 1,
      "name": "Paracetamol",
      "strength": "500 mg",
      "form": "TABLET",
      "pricePaise": 2000,
      "prescriptionRequired": false
    },
    {
      "id": 2,
      "name": "Paracetamol",
      "strength": "650 mg",
      "form": "TABLET",
      "pricePaise": 3050,
      "prescriptionRequired": false
    }
  ]
}
```

### Case 2: `john's`

**Why:** the apostrophe is a character in a parameter, not the end of a SQL string.

Request

``` code
GET /medicines?name=john%27s HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 150

{
  "query": "john's",
  "results": [
    {
      "id": 14,
      "name": "St. John's Wort",
      "strength": "300 mg",
      "form": "CAPSULE",
      "pricePaise": 45000,
      "prescriptionRequired": false
    }
  ]
}
```

### Case 3: `x' OR 1=1 --`

**Why:** no medicine is called that. On the old code, this returned every medicine.

Request

``` code
GET /medicines?name=x%27%20OR%201%3D1%20-- HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 37

{
  "query": "x' OR 1=1 --",
  "results": []
}
```

### Case 4: `%%`

**Why:** escaped, so it means two percent signs, not "everything".

Request

``` code
GET /medicines?name=%25%25 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 27

{
  "query": "%%",
  "results": []
}
```

### Case 5: `aspirin`

**Why:** not in this catalogue: an empty list, not a 404.

Request

``` code
GET /medicines?name=aspirin HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 32

{
  "query": "aspirin",
  "results": []
}
```

### Case 6: `p`

**Why:** one character would match most of the catalogue: `400`.

Request

``` code
GET /medicines?name=p HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Validation failure",
  "instance": "/medicines",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 7: no name

**Why:** `400`.

Request

``` code
GET /medicines HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Required parameter 'name' is not present.",
  "instance": "/medicines",
  "status": 400,
  "title": "Bad Request"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                            | What happens                                                         | Proved by                                                                        |
|-------------------------------------------------|----------------------------------------------------------------------|----------------------------------------------------------------------------------|
| UNION payload; `x' OR 1=1 --`                   | The old code leaks; the real one returns nothing                     | `ConcatenatedSqlTrapTest`                                                        |
| An apostrophe                                   | The old code fails; the real one finds the product                   | `theOldSearchBreaksOnAnApostrophe`, `anApostropheIsJustACharacter`               |
| Connections after many searches                 | The old code empties the pool; the real one returns every connection | `theOldSearchLeaksAConnectionEveryTime`, `theRealSearchGivesEveryConnectionBack` |
| `%%`, `a_`                                      | Literal characters                                                   | `wildcardsAreLiteral`, `escapingKeepsWildcardsLiteral`                           |
| Price 0, form POWDER, a duplicate product       | Refused by named constraints                                         | `namedConstraintsRefuseBadRowsFromAnyWriter`                                     |
| A prescription for a missing medicine           | Refused by the foreign key                                           | `aPrescriptionMustPointAtARealMedicine`                                          |
| Two inserts, the second bad, in one transaction | Neither is kept after rollback                                       | `aFailedStatementInATransactionLeavesNothingAfterRollback`                       |
| The same with auto-commit on                    | The first is kept                                                    | `withAutoCommitTheFirstRowStaysWhenTheSecondFails`                               |
| Missing, blank, 1 or 51 characters              | `400`                                                                | `aMissingTooShortOrTooLongNameIs400`                                             |

## The trap

Plausible but wrong

Building SQL by string concatenation (SQL injection) and leaking connections.

Every test here runs the old code against the real PostgreSQL. The UNION payload returns the three fictional patients' names, phones and doctors. A 12-character payload returns all 15 medicines. An apostrophe ends the SQL string early, and the driver refuses the query with "Unterminated string literal". On a pool of 3 connections, the old search keeps all 3, and the 4th search times out. The real search, given the same text, returns nothing to leak, and after 50 searches no connection is in use. While building, each fix was undone once. Removing the LIKE escaping turned 1 test red, not closing the connection 8, and putting the text into the SQL string 5.

``` code
package com.mediqo.pharmacy;

import com.zaxxer.hikari.HikariDataSource;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.sql.SQLException;
import java.sql.SQLTransientConnectionException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The first test written for this station: the old search, run against the real database. */
class ConcatenatedSqlTrapTest extends ApiTest {

    /** 12 characters: a length limit on the search box is not a defence. */
    static final String ALWAYS_TRUE = "x' OR 1=1 --";
    static final String DUMP_PRESCRIPTIONS = "x' UNION SELECT patient_name, patient_phone, doctor FROM prescriptions --";

    @Autowired
    MedicineSearch search;

    /** A pool of its own, so the leak cannot starve the other tests: 3 connections, give up after 250 ms. */
    HikariDataSource smallPool() {
        HikariDataSource app = (HikariDataSource) dataSource;
        HikariDataSource pool = new HikariDataSource();
        pool.setJdbcUrl(app.getJdbcUrl());
        pool.setUsername(app.getUsername());
        pool.setPassword(app.getPassword());
        pool.setMaximumPoolSize(3);
        pool.setConnectionTimeout(250);
        return pool;
    }

    @Test
    void theOldSearchHandsOverEveryPrescription() throws SQLException {
        try (HikariDataSource pool = smallPool()) {
            assertThat(OldMedicineSearch.byName(pool, DUMP_PRESCRIPTIONS))
                    .contains("Asha Verma | 90000 00001 | Dr Mehta", "Ravi Iyer | 90000 00002 | Dr Rao", "Fatima Shaikh | 90000 00003 | Dr Mehta");
        }
        assertThat(search.byName(DUMP_PRESCRIPTIONS)).isEmpty();   // just text to the fixed query: no medicine has that name
    }

    @Test
    void aShortPayloadFitsTheLengthLimitAndStillGetsEverything() throws SQLException {
        try (HikariDataSource pool = smallPool()) {
            assertThat(OldMedicineSearch.byName(pool, ALWAYS_TRUE)).hasSize(15);   // every medicine, whatever was typed
        }
        assertThat(search.byName(ALWAYS_TRUE)).isEmpty();
    }

    @Test
    void theOldSearchBreaksOnAnApostrophe() throws SQLException {
        try (HikariDataSource pool = smallPool()) {
            assertThatThrownBy(() -> OldMedicineSearch.byName(pool, "john's")).isInstanceOf(SQLException.class).hasMessageContaining("Unterminated string literal");
        }
        assertThat(search.byName("john's")).extracting(Medicine::name).containsExactly("St. John's Wort");
    }

    @Test
    void theOldSearchLeaksAConnectionEveryTime() throws SQLException {
        try (HikariDataSource pool = smallPool()) {
            for (int i = 0; i < 3; i++) {
                OldMedicineSearch.byName(pool, "para");
            }
            assertThat(pool.getHikariPoolMXBean().getActiveConnections()).isEqualTo(3);   // all taken, none returned
            assertThatThrownBy(() -> OldMedicineSearch.byName(pool, "para"))
                    .isInstanceOf(SQLTransientConnectionException.class).hasMessageContaining("request timed out");
        }
    }

    @Test
    void theRealSearchGivesEveryConnectionBack() throws Exception {
        for (int i = 0; i < 50; i++) {
            search("para");
        }
        assertThat(((HikariDataSource) dataSource).getHikariPoolMXBean().getActiveConnections()).isZero();
    }
}
```

``` code
package com.mediqo.pharmacy;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;

/** The search before the fix, kept only in tests. Two bugs: SQL built from the user's text, and nothing closed. */
final class OldMedicineSearch {

    private OldMedicineSearch() {
    }

    static List<String> byName(DataSource dataSource, String name) throws SQLException {
        Connection connection = dataSource.getConnection();   // never closed: the pool never gets it back
        Statement statement = connection.createStatement();
        ResultSet rows = statement.executeQuery(
                "SELECT name, strength, form FROM medicines WHERE name ILIKE '%" + name + "%' ORDER BY name");
        List<String> found = new ArrayList<>();
        while (rows.next()) {
            found.add(rows.getString(1) + " | " + rows.getString(2) + " | " + rows.getString(3));
        }
        return found;
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
./mvnw spring-boot:run      # the API on http://localhost:8080; Flyway creates and fills the tables
./mvnw test                 # all 15 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Search, then look at the same rows in the database:

``` code
curl "http://localhost:8080/medicines?name=cillin"
docker compose exec postgres psql -U mediqo -d mediqo -c "SELECT name, strength, form FROM medicines WHERE lower(name) LIKE '%cillin%'"
```

Then try to insert a free medicine directly, and read the constraint's name in the error:

``` code
docker compose exec postgres psql -U mediqo -d mediqo -c "INSERT INTO medicines (name, strength, form, price_paise, prescription_required) VALUES ('Free pill', '1 mg', 'TABLET', 0, false)"
```

## Troubleshooting

| You see                                                        | Cause                                             | Fix                                                                                   |
|----------------------------------------------------------------|---------------------------------------------------|---------------------------------------------------------------------------------------|
| `Could not find a valid Docker environment`                    | Docker is not running. Testcontainers needs it.   | Start Docker, then run the tests again.                                               |
| `Connection to localhost:5432 refused`                         | PostgreSQL is not up yet.                         | `docker compose up -d`, wait a few seconds, start the app again.                      |
| `Connection is not available, request timed out after 30000ms` | Connections are not returned to the pool: a leak. | Find the `getConnection()` outside a try-with-resources.                              |
| `port 5432 is already allocated`                               | A local PostgreSQL uses the port.                 | Stop it, or map `"5433:5432"` in compose.yaml and change the URL in application.yaml. |

## Project layout

``` tree
stations/036-medicine-search-with-plain-jdbc/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/mediqo/pharmacy/
│   ├── MedicineController.java   ├── MedicineSearch.java
│   ├── Medicine.java             └── PharmacyApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__medicines_and_prescriptions.sql, V2__demo_catalogue.sql
├── src/test/java/com/mediqo/pharmacy/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/mediqo/pharmacy/MedicineController.java`

Does  
Validates the text and returns the results.

Why  
Validation at the edge keeps nonsense away from the database; it is not what stops injection.

Without it  
Relying on a length limit or a blacklist of quotes to stop injection.

#### `src/main/java/com/mediqo/pharmacy/MedicineSearch.java`

Does  
The search in plain JDBC.

Why  
Fixed SQL, one parameter for the text, one for the limit; try-with-resources closes the connection, statement and result set.

Without it  
The trap: text glued into SQL, and connections never returned.

- `prepareStatement(SQL)` sends the SQL once; `setString` sends the value separately.
- `ESCAPE '\'` plus `escapeLike` make `%` and `_` literal.
- Closing a pooled connection returns it to the pool; it does not close the socket.

#### `src/main/java/com/mediqo/pharmacy/Medicine.java`

One catalogue row.

#### `src/main/resources/db/migration/V1__medicines_and_prescriptions.sql`

Does  
The two tables and their named constraints.

Why  
Rules the database enforces for every writer, not just this app.

Without it  
A script or another service inserts a free medicine, or a duplicate in different letter case.

#### `src/main/resources/db/migration/V2__demo_catalogue.sql`

15 demo medicines and 3 fictional prescriptions. `''` is an apostrophe inside a SQL string.

#### `src/main/resources/application.yaml`

The database the app connects to (compose.yaml starts it).

#### `compose.yaml`

PostgreSQL 17 for running the app, with a healthcheck.

#### `src/main/java/com/mediqo/pharmacy/PharmacyApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                    | Result |
|---------------|-------------------------------------------------------|-------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found (empty)      | `MedicineContractTest` (5)    | pass   |
| Every station | Reproduce the failure before the fix                  | `ConcatenatedSqlTrapTest` (5) | pass   |
| Database      | Rollback and constraint tests against a real database | `MedicineDatabaseTest` (5)    | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.pharmacy.MedicineContractTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.pharmacy.ConcatenatedSqlTrapTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.pharmacy.MedicineDatabaseTest
[INFO] Tests run: 15, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/mediqo/pharmacy/ConcatenatedSqlTrapTest.java`

Written first: the old search's leak of prescriptions, its error on an apostrophe, and its connection leak, on a pool of its own.

#### `src/test/java/com/mediqo/pharmacy/MedicineContractTest.java`

Searches through HTTP, wildcards, the injection attempt, and every refusal.

#### `src/test/java/com/mediqo/pharmacy/MedicineDatabaseTest.java`

Plain JDBC against the schema: named constraints, the foreign key, rollback and auto-commit.

#### `src/test/java/com/mediqo/pharmacy/OldMedicineSearch.java`

The old code, kept only in tests.

#### `src/test/java/com/mediqo/pharmacy/ApiTest.java`

Shared setup: the app with a real PostgreSQL.

#### `src/test/java/com/mediqo/pharmacy/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/mediqo/pharmacy/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=FormFilterChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 15 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 19 tests pass (15 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Filter by form

Add an optional `?form=` (any case). The SQL gains `AND form = ?` only when a form is given; an unknown form is a `400` before the database is asked.

**Done when:** both tests in `FormFilterChallengeTest` pass.

Hints

- Building SQL from fixed fragments you wrote is safe; the values still go in as parameters.
- Count the parameters as you add them: the limit moves from position 2 to 3.

#### `challenge/FormFilterChallengeTest.java`

``` code
package com.mediqo.pharmacy;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.everyItem;
import static org.hamcrest.Matchers.is;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: an optional ?form= filter (any case). The SQL may grow an "AND form = ?" only when a form is given:
 * fixed fragments of SQL, values always as parameters. An unknown form is a 400, before the database is asked.
 */
class FormFilterChallengeTest extends ApiTest {

    @Test
    void theFormNarrowsTheSearch() throws Exception {
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/medicines").param("name", "para").param("form", "syrup"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.results[*].strength", contains("125 mg/5 ml")));
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/medicines").param("name", "para").param("form", "TABLET"))
                .andExpect(jsonPath("$.results[*].form", everyItem(is("TABLET"))))
                .andExpect(jsonPath("$.results.length()").value(2));
    }

    @Test
    void anUnknownFormIs400() throws Exception {
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/medicines").param("name", "para").param("form", "TABLET' OR 1=1 --"))
                .andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## How many matches?

Add `?size=` (1 to 20) and a `total` of every match, from the same single query.

**Done when:** both tests in `TotalAndSizeChallengeTest` pass.

Hints

- `count(*) OVER ()` counts the rows before `LIMIT` and repeats the number on every row.
- With no rows, there is no row to read the total from: it is 0.

#### `challenge/TotalAndSizeChallengeTest.java`

``` code
package com.mediqo.pharmacy;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: the app shows "5 matches" above the first 2. Add ?size= (1 to 20, default 20) and a "total" field with
 * every match, in the same single query (count(*) OVER ()), not a second round trip.
 */
class TotalAndSizeChallengeTest extends ApiTest {

    @Test
    void sizeLimitsTheRowsAndTotalCountsThemAll() throws Exception {
        mvc.perform(get("/medicines").param("name", "ol").param("size", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.total").value(5))
                .andExpect(jsonPath("$.results[*].name", contains("Clotrimazole", "Pantoprazole")));
    }

    @Test
    void noMatchHasATotalOfZeroAndABadSizeIs400() throws Exception {
        search("aspirin").andExpect(jsonPath("$.total").value(0));
        mvc.perform(get("/medicines").param("name", "ol").param("size", "0")).andExpect(status().isBadRequest());
        mvc.perform(get("/medicines").param("name", "ol").param("size", "21")).andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## A search for 2 lakh products

`LIKE '%text%'` cannot use a normal index, so it reads every row. With 2,00,000 products and typos ("paracitamol"), compare a trigram index (`pg_trgm`), PostgreSQL full-text search, and a search engine. Which handles typos, which handles brand and generic names, and what each costs to keep in sync?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap tests against a real PostgreSQL: leak, apostrophe, pool exhaustion.
2.  Write the schema with named constraints, and test them with plain inserts.
3.  Write the search: fixed SQL, parameters, escaped wildcards, try-with-resources.
4.  Check that after many searches the pool has no connection in use.

## Design alternatives and trade-offs

| Approach                                       | What it costs                                                        | Verdict                |
|------------------------------------------------|----------------------------------------------------------------------|------------------------|
| `PreparedStatement` with parameters            | A few more lines than concatenation.                                 | Chosen                 |
| Concatenation with quote escaping by hand      | One missed case (encodings, backslashes) and it is injectable again. | Never                  |
| Blocking characters such as `'` and `--`       | Breaks St. John's Wort; attackers find other ways.                   | Not a defence          |
| `JdbcClient` or `JdbcTemplate`                 | Same safety, less code: they prepare and close for you.              | From the next stations |
| A database user that can only read `medicines` | One more role to manage; limits the damage of any mistake.           | Defence in depth       |

## Database design

| Table           | Key and constraints                                                                                                                          | Why                                                                                                            |
|-----------------|----------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| `medicines`     | Identity PK. `medicines_price_positive`, `medicines_form_known`, unique index `medicines_unique_product` on `(lower(name), strength, form)`. | The catalogue's rules hold for every writer; "Paracetamol" and "PARACETAMOL" 500 mg tablets cannot both exist. |
| `prescriptions` | Identity PK, `prescriptions_medicine_fk` to `medicines`.                                                                                     | Personal health data: exactly what injection reached. No search reads it.                                      |

**Transactions:** the search is one read with auto-commit on. `MedicineDatabaseTest` shows the difference a transaction makes: with `setAutoCommit(false)` and a rollback, a failed second insert takes the first with it; with auto-commit, the first stays. The next station builds on this.

**Index:** `lower(name) LIKE '%…%'` cannot use a B-tree index, so it scans the table. At 15 rows that is nothing; challenge 3 is about when it is not.

``` code
-- The catalogue the search reads, and the table the old search leaked: prescriptions hold patients' names and phones.
CREATE TABLE medicines (
    id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                  VARCHAR(100) NOT NULL,
    strength              VARCHAR(30)  NOT NULL,
    form                  VARCHAR(20)  NOT NULL,
    price_paise           BIGINT       NOT NULL,
    prescription_required BOOLEAN      NOT NULL,
    CONSTRAINT medicines_price_positive CHECK (price_paise > 0),
    CONSTRAINT medicines_form_known     CHECK (form IN ('TABLET', 'CAPSULE', 'SYRUP', 'CREAM', 'INJECTION', 'DROPS'))
);

-- One row per product: "Paracetamol" and "PARACETAMOL" 500 mg tablets are the same product.
CREATE UNIQUE INDEX medicines_unique_product ON medicines (lower(name), strength, form);

CREATE TABLE prescriptions (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    patient_name  VARCHAR(100) NOT NULL,
    patient_phone VARCHAR(15)  NOT NULL,
    medicine_id   BIGINT       NOT NULL,
    doctor        VARCHAR(100) NOT NULL,
    issued_on     DATE         NOT NULL,
    CONSTRAINT prescriptions_medicine_fk FOREIGN KEY (medicine_id) REFERENCES medicines (id)
);
```

# 3 · Go deeper: Production

Least privilege  
The app's database user should read and write only what it needs. A search that cannot read `prescriptions` cannot leak it, even with a bug.

Leak detection  
HikariCP's `leakDetectionThreshold` logs where a connection was borrowed when it is held too long; watch active connections next to request rate.

Health data  
Prescriptions are sensitive personal data under India's Digital Personal Data Protection Act, 2023; a leak is a reportable incident, not only a bug.

Logging  
Log that a search happened, not the patient behind it; search text can contain names.

# 3 · Go deeper: Interview

## Interview takeaways

What is SQL injection, and how do you prevent it?

User input that becomes part of the SQL text and changes the query. Prevent it with parameters (PreparedStatement or a library that uses them); never build SQL from input. Validation and least privilege reduce the damage but do not prevent it.

What does closing a pooled connection do?

It returns the connection to the pool for the next request. Not closing it keeps it borrowed until the pool runs out and requests time out.

Why try-with-resources?

It closes every resource declared in it, in reverse order, on every path, including exceptions, which hand-written finally blocks often get wrong.

Can a PreparedStatement parameter be a table or column name?

No. Parameters are values only. Identifiers must come from a fixed list in your code (an allowlist).

Why escape % and \_ in a LIKE parameter?

They are wildcards inside the pattern. Without escaping, a user's '%' matches everything; it is not injection, but it is wrong results and extra load.

## Self-check rubric

| Area        | Meets the bar                  | Above the bar                                                |
|-------------|--------------------------------|--------------------------------------------------------------|
| Correctness | All 15 tests pass.             | You ran the trap and read the leaked rows.                   |
| Security    | Parameters for every value.    | An allowlist for anything that must be part of the SQL text. |
| Resources   | try-with-resources everywhere. | You can watch a pool's active connections.                   |
| Database    | Named constraints with tests.  | Auto-commit vs a transaction, from the test.                 |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any JDBC code:

- Is any `+` joining input into SQL text?
- Is every `getConnection()`, statement and result set in a try-with-resources?
- Are `LIKE` wildcards in user text escaped?
- Can this database user read tables this feature never needs?
