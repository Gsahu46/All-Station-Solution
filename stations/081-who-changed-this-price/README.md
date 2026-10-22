# Station 081 · Who changed this price?

Working Systems · 0–2 years · Core · E-commerce · Types: Database, Security

Spring Boot 4.1.1 · Java 25 · Spring Data JPA · Hibernate 7.4 Envers · Spring Security 7 (HTTP Basic) · PostgreSQL 17 triggers · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Sellers, products and prices are demo data, not Kartwala's. A price change is a row in a table: no listing goes live anywhere.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 19 tests.

# 1 · Understand

## The problem in real life

1.  **A tenfold drop**

    Neha's 55-inch TV on Kartwala went from ₹54,999 to ₹5,499 one evening. Hundreds of orders came in.

2.  **A log that could not answer**

    The change log was lines of text in three different wordings, without dates, and the name in them was whatever the app sent. Nobody could say who had done it, or when.

3.  **The fix**

    Every price change writes a revision: the time, the signed-in user, and the product as it now is, in the same transaction. Nobody can change or delete it afterwards.

History is data: queryable, attributed by the system, and impossible to edit.

## What are we building?

`PUT /products/{id}/price` that records who changed what and when, and `GET /products/{id}/history` that answers it.

## An everyday analogy

A shop's price board where every change is written in a bound register, signed by the person on shift (checked against their staff card, not their word), with the time, and no page can be torn out.

## How it works in 4 steps

1.  **Sign in**: the seller's name comes from the sign-in.
2.  **Change**: Hibernate updates the product.
3.  **Record**: in the same transaction Envers writes a revision (when, who) and the product as it now is.
4.  **Ask**: the history is read back newest first, each price with the one before it.

Check yourself: the request body says "changedBy": "priya.ops". Who does the history name?

The signed-in user. The name comes from Spring Security, never from the request: `whoIsTheSignedInUserNotWhatTheRequestSays`.

## What this station is not

- **No approvals.** Big drops are recorded, not stopped (Practice, challenge 3).
- **No general audit log.** Only products are audited; logins and reads are not.
- **No retention.** History grows forever here (see Production).

## Key terms

| Term                 | Simple meaning                                                                                  | Everyday example                                | In this project          |
|----------------------|-------------------------------------------------------------------------------------------------|-------------------------------------------------|--------------------------|
| **Change history**   | Every version of a record, with when and by whom, kept as data.                                 | A bank passbook: every entry, never rubbed out. | `products_aud`           |
| **Envers**           | Hibernate's history writer: each change to an @Audited entity also writes the row as it now is. | A carbon copy made with every letter.           | `@Audited`               |
| **Revision**         | One change set: one moment, one person, the rows it touched.                                    | One stamped page in the passbook.               | `revisions`              |
| **Security context** | Who is signed in for this request, as Spring Security knows it.                                 | The badge, not the name someone says aloud.     | `ChangedByListener`      |
| **Append-only**      | Rows can be added, never changed or deleted.                                                    | A ledger written in ink.                        | `history_is_append_only` |
| **Paise**            | Money as whole paise: ₹54,999 is 5499900.                                                       | Counting coins, not weighing them.              | `pricePaise`             |

# 2 · Build: Spec

## Business problem

**Kartwala** (a fictional marketplace): a price dropped from ₹54,999 to ₹5,499 and nobody can tell who changed it or when.

## Acceptance criteria

Demo users: sellers neha.store (products 1 and 2) and arun.mart (3), admin priya.ops, support sam.help.

1.  **Given** a seller and their product, **then** the price changes and the history gains one entry with their name and the time.
2.  **Given** a history, **then** newest first, each with the price before it, back to the import.
3.  **Given** a name in the body or a header, **then** the history still names the signed-in user.
4.  **Given** another seller's product, **then** `404`; support may read any history but gets `403` on a change.
5.  **Given** an UPDATE or DELETE on the history tables by any writer, **then** refused.
6.  **Given** a price with paise after the point, **then** `400`.

## Requirements

- Every change and its history are one transaction.
- No change without a signed-in user, even from code that skips the endpoints.
- Money is whole paise from the request to the database.

## Learning objectives

- Audit an entity with Hibernate Envers and a custom revision entity.
- Take "who" from the security context.
- Make history append-only in the database.
- Query history instead of grepping it.

# 2 · Build: API contract

## Endpoints

| Method | Path                     | Purpose                                                                                            |
|--------|--------------------------|----------------------------------------------------------------------------------------------------|
| `PUT`  | `/products/{id}/price`   | `{pricePaise}`, a whole number from 100 (₹1) to 100,000,000 (₹10,00,000).                          |
| `GET`  | `/products/{id}/history` | Newest first: revision, changedAt, changedBy, change (ADD or MOD), pricePaise, previousPricePaise. |

## Status codes

| Status | When                                                                   |
|--------|------------------------------------------------------------------------|
| 200    | Price set / history read                                               |
| 400    | A price missing, out of range, a string, or with paise after the point |
| 401    | No or wrong credentials                                                |
| 403    | Support changing a price; a path with no rule                          |
| 404    | No such product, or another seller's                                   |

## Captured examples

Captured with curl from the running app on 22 Oct 2026, in this order. JSON bodies are indented for reading; `Date`, connection and standard security headers are left out.

### Case 1: Neha sets the TV to ₹5,499

**Why:** her product; recorded.

Request

``` code
PUT /products/1/price HTTP/1.1
Authorization: Basic bmVoYS5zdG9yZTpuZWhhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "pricePaise": 549900
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 58

{
  "id": 1,
  "name": "Aurora 55-inch 4K TV",
  "pricePaise": 549900
}
```

### Case 2: and back to ₹54,999

**Why:** another revision.

Request

``` code
PUT /products/1/price HTTP/1.1
Authorization: Basic bmVoYS5zdG9yZTpuZWhhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "pricePaise": 5499900
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 59

{
  "id": 1,
  "name": "Aurora 55-inch 4K TV",
  "pricePaise": 5499900
}
```

### Case 3: support reads the TV's history

**Why:** who, when, from what to what, back to the import.

Request

``` code
GET /products/1/history HTTP/1.1
Authorization: Basic c2FtLmhlbHA6c2FtLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 430

[
  {
    "revision": 3,
    "changedAt": "2026-10-22T11:01:24.463Z",
    "changedBy": "neha.store",
    "change": "MOD",
    "pricePaise": 5499900,
    "previousPricePaise": 549900
  },
  {
    "revision": 2,
    "changedAt": "2026-10-22T11:01:24.305Z",
    "changedBy": "neha.store",
    "change": "MOD",
    "pricePaise": 549900,
    "previousPricePaise": 5499900
  },
  {
    "revision": 1,
    "changedAt": "2026-10-01T00:00:00Z",
    "changedBy": "catalogue.import",
    "change": "ADD",
    "pricePaise": 5499900,
    "previousPricePaise": null
  }
]
```

### Case 4: a body that says priya.ops changed it

**Why:** the name in the body is ignored (see the rows below).

Request

``` code
PUT /products/2/price HTTP/1.1
Authorization: Basic bmVoYS5zdG9yZTpuZWhhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "pricePaise": 1199900,
  "changedBy": "priya.ops"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 54

{
  "id": 2,
  "name": "Aurora soundbar",
  "pricePaise": 1199900
}
```

### Case 5: Arun asks for Neha's TV

**Why:** `404`.

Request

``` code
GET /products/1/history HTTP/1.1
Authorization: Basic YXJ1bi5tYXJ0OmFydW4tZGVtby1wYXNz
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No such product",
  "instance": "/products/1/history",
  "status": 404,
  "title": "Not Found"
}
```

### Case 6: support tries to change a price

**Why:** `403`: support reads, never sets.

Request

``` code
PUT /products/1/price HTTP/1.1
Authorization: Basic c2FtLmhlbHA6c2FtLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "pricePaise": 100
}
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json
Content-Length: 107

{
  "title": "Not allowed",
  "status": 403,
  "detail": "This sign-in cannot do this.",
  "instance": "/products/1/price"
}
```

### Case 7: 5499.99 paise

**Why:** `400`: by default Jackson would have stored 5499.

Request

``` code
PUT /products/1/price HTTP/1.1
Authorization: Basic bmVoYS5zdG9yZTpuZWhhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "pricePaise": 5499.99
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Failed to read request",
  "instance": "/products/1/price",
  "status": 400,
  "title": "Bad Request"
}
```

## The history rows afterwards

From `psql` in `docs/capture.sh`: revision 4 is case 4, signed by neha.store whatever the body said.

``` code
 product | rev | revtype | price_paise |    changed_by    |     changed_at_utc      
---------+-----+---------+-------------+------------------+-------------------------
       1 |   1 |       0 |     5499900 | catalogue.import | 2026-10-01 00:00:00
       2 |   1 |       0 |     1299900 | catalogue.import | 2026-10-01 00:00:00
       3 |   1 |       0 |      249900 | catalogue.import | 2026-10-01 00:00:00
       1 |   2 |       1 |      549900 | neha.store       | 2026-10-22 11:01:24.305
       1 |   3 |       1 |     5499900 | neha.store       | 2026-10-22 11:01:24.463
       2 |   4 |       1 |     1199900 | neha.store       | 2026-10-22 11:01:25.3
(6 rows)
```

And an attempt to tidy it up, straight in the database:

``` code
ERROR:  history_is_append_only: UPDATE on products_aud
CONTEXT:  PL/pgSQL function history_is_append_only() line 3 at RAISE
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                         | What happens                                                           | Proved by                                      |
|----------------------------------------------|------------------------------------------------------------------------|------------------------------------------------|
| A seller changes their price                 | `200`                                                                  | `aSellerChangesTheirPrice`                     |
| Two changes                                  | History newest first, each with the previous price, back to the import | `theHistoryIsNewestFirstWithEachPreviousPrice` |
| The same price again                         | No new history entry                                                   | `theSamePriceAgainAddsNothingToTheHistory`     |
| Unknown product                              | `404`                                                                  | `unknownProductsAre404`                        |
| 0, 99, too large, missing, a string, 5499.99 | `400`                                                                  | `badPricesAre400`                              |
| No or wrong credentials                      | `401`                                                                  | `noOrWrongCredentialsAre401`                   |
| Another seller's product                     | `404`, unchanged                                                       | `anotherSellersProductIs404AndUnchanged`       |
| Support                                      | Reads any history; `403` to change                                     | `supportReadsAnyHistoryButCannotChangeAPrice`  |
| A header naming someone else                 | Ignored                                                                | `aHeaderNamingSomeoneElseIsIgnored`            |
| An admin's change                            | Carries the admin's name                                               | `anAdminsChangeCarriesTheAdminsName`           |
| A change from code with nobody signed in     | Refused, price unchanged                                               | `aChangeWithNobodySignedInIsRefused`           |
| Odd ids, other paths                         | `400`, `404` or `403`                                                  | `oddInputAndOtherPathsNeverReachTheData`       |
| Rules written by plain SQL                   | Refused by named constraints                                           | `rulesHoldWithoutJava`                         |
| Two changes                                  | Two revisions, two history rows                                        | `eachChangeAddsOneRevisionAndOneHistoryRow`    |
| History that cannot be written               | The price does not change                                              | `aPriceWhoseHistoryFailsDoesNotChange`         |

## The trap

Plausible but wrong

Logging changes as free text, so history cannot be queried or trusted.

- **The old log.** Three lines in three wordings; one names no product; none has a date; the name is whatever the app sent; and a line can be quietly rewritten.
- **Who and when.** The history answers with the signed-in user and the time, and the price before.
- **Not what the request says.** A `changedBy` in the body changes nothing.
- **Not editable.** `UPDATE` and `DELETE` on the history tables are refused by the database.

While building, each part was undone once: allowing changes with nobody signed in turned 1 test red; no `@Audited` 10; no append-only trigger 1; no ownership check 1; floats accepted 1; `denyAll` replaced by `authenticated` 1.

``` code
package com.kartwala.prices;

import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old code wrote a line of text to a log table when a price changed, in whatever words the
 * developer chose that week, with the user name the app sent. The TV went from ₹54,999 to ₹5,499 and nobody could
 * say who did it. Each test asks the old log a question, then asks the real history.
 */
class FreeTextLogTrapTest extends ApiTest {

    /** The old log, as it was: lines of text, editable like any row. */
    static final List<String> OLD_LOG = new ArrayList<>(List.of(
            "price updated for product 1 to 5499 by neha",
            "Product #1: new price Rs 54,999.00",
            "changed price -> 5499 (user: ops)"));

    @Test
    void theOldLogCouldNotSayWhoOrWhenOrEvenWhichPrice() {
        // "Who set product 1 to ₹5,499?" Two lines might be it, in two formats, with two different people, and no time.
        Matcher who = Pattern.compile("product 1 to (\\d+) by (\\w+)").matcher(String.join("\n", OLD_LOG));
        assertThat(who.find()).isTrue();
        assertThat(OLD_LOG.get(2)).doesNotContain("product");   // which product was this one?
        OLD_LOG.set(0, "price updated for product 1 to 54999 by neha");   // and anyone with write access could tidy it up
        assertThat(OLD_LOG).noneMatch(l -> l.matches(".*\\d{4}-\\d{2}-\\d{2}.*"));   // not one line has a date
    }

    @Test
    void theHistoryNamesWhoAndWhenForEveryPrice() throws Exception {
        setPrice("neha.store", 1, 549900).andExpect(status().isOk());
        history("priya.ops", 1).andExpect(status().isOk())
                .andExpect(jsonPath("$[0].changedBy").value("neha.store")).andExpect(jsonPath("$[0].pricePaise").value(549900))
                .andExpect(jsonPath("$[0].previousPricePaise").value(5499900)).andExpect(jsonPath("$[0].changedAt").isNotEmpty())
                .andExpect(jsonPath("$[1].changedBy").value("catalogue.import"));
    }

    @Test
    void whoIsTheSignedInUserNotWhatTheRequestSays() throws Exception {
        setPrice("neha.store", 1, "{\"pricePaise\":549900,\"changedBy\":\"priya.ops\"}").andExpect(status().isOk());
        history("neha.store", 1).andExpect(jsonPath("$[0].changedBy").value("neha.store"));
    }

    @Test
    void theHistoryCannotBeTidiedUp() {
        assertThatThrownBy(() -> jdbc.sql("UPDATE products_aud SET price_paise = 5499900").update())
                .isInstanceOf(DataIntegrityViolationException.class).hasMessageContaining("history_is_append_only");
        assertThatThrownBy(() -> jdbc.sql("DELETE FROM revisions").update())
                .isInstanceOf(DataIntegrityViolationException.class).hasMessageContaining("history_is_append_only");
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
./mvnw test                 # all 19 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Change a price, then try to rewrite the history:

``` code
curl -s -u arun.mart:arun-demo-pass -X PUT http://localhost:8080/products/3/price -H 'Content-Type: application/json' -d '{"pricePaise": 199900}'; echo
curl -s -u arun.mart:arun-demo-pass http://localhost:8080/products/3/history; echo
docker compose exec postgres psql -U kartwala -d kartwala -c "DELETE FROM products_aud WHERE id = 3"
```

The history shows arun.mart and the time; the `DELETE` fails with `history_is_append_only`.

## Troubleshooting

| You see                                     | Cause                                                                        | Fix                                                                                             |
|---------------------------------------------|------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| `history_is_append_only`                    | Something tried to change or delete history.                                 | Do not; add a correcting change instead.                                                        |
| `A price change needs a signed-in user`     | Code changed a product with no user in the security context (a job, a test). | Run it as a named technical user.                                                               |
| A price of 5499.99 stored as 5499           | Jackson's default `ACCEPT_FLOAT_AS_INT`.                                     | `spring.jackson.deserialization.accept-float-as-int: false`. Found while building this station. |
| `Could not find a valid Docker environment` | Docker is not running.                                                       | Start Docker Desktop or the Docker service.                                                     |

## Project layout

``` tree
stations/081-who-changed-this-price/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/prices/
│   ├── Product.java   ├── Revision.java   ├── ChangedByListener.java   ├── Products.java
│   ├── Prices.java   ├── PriceController.java   ├── SecurityConfig.java
│   ├── ProblemResponses.java   └── PricesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__products_and_history.sql, V2__demo_catalogue.sql
├── src/test/java/com/kartwala/prices/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

The entity and its history first, then the service and the endpoints.

#### `src/main/java/com/kartwala/prices/Product.java`

Does  
The listing, @Audited.

Why  
Every change Hibernate writes also writes the row to `products_aud`.

Without it  
Changes that leave no trace.

#### `src/main/java/com/kartwala/prices/Revision.java`

Does  
Envers' revision entity, made our own.

Why  
When (milliseconds, UTC) and who, in `revisions`.

Without it  
A history without names.

#### `src/main/java/com/kartwala/prices/ChangedByListener.java`

Does  
Who, for every revision.

Why  
The name comes from Spring Security's context; no signed-in user, no change.

Without it  
Names taken from the request, or anonymous changes from a batch job.

#### `src/main/java/com/kartwala/prices/Prices.java`

Does  
Change and history.

Why  
Sellers reach their own products, admins all, support reads any; the history is an Envers query, newest first.

Without it  
Another seller's prices, or a history that has to be grepped.

Setting the same price again writes no revision: Hibernate does not flush an unchanged row, so Envers sees nothing to record.

#### `src/main/java/com/kartwala/prices/PriceController.java`

The two endpoints. The body carries only the price.

#### `src/main/java/com/kartwala/prices/SecurityConfig.java`

HTTP Basic with demo users; who may change, who may read; everything else refused.

#### `src/main/java/com/kartwala/prices/ProblemResponses.java`

401 with a Basic challenge and 403 in the same problem JSON as every other error.

#### `src/main/resources/application.yaml`

Does  
Database, JPA and Jackson settings.

Why  
`ddl-auto: validate` (Flyway owns the schema, audit tables included); floats refused for whole-number fields.

Without it  
5499.99 paise silently stored as 5499.

Jackson accepts a float for a `long` and drops the fraction, by default. `accept-float-as-int: false` makes it a `400`. Found while building.

#### `src/main/resources/db/migration/V1__products_and_history.sql`

Does  
Products, revisions, products_aud, and the append-only triggers.

Why  
History rows can only be added, by any writer.

Without it  
Someone tidying up an embarrassing change.

#### `src/main/resources/db/migration/V2__demo_catalogue.sql`

Three products and the import as revision 1, so every history starts with the original price.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/kartwala/prices/PricesApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                       | Test class                | Result |
|---------------|-------------------------------------------------------------------|---------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                          | `PriceContractTest` (5)   | pass   |
| Every station | Reproduce the failure before the fix                              | `FreeTextLogTrapTest` (4) | pass   |
| Database      | Rollback and constraint tests against a real database             | `PriceDatabaseTest` (3)   | pass   |
| Security      | 401, 403, one user accessing another user's data, malicious input | `PriceSecurityTest` (7)   | pass   |

Revision times come from the system clock (Envers takes them itself), so tests check order and presence, not exact times.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Hibernate 7.4 with Envers, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 7, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.prices.PriceSecurityTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.prices.PriceDatabaseTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.prices.PriceContractTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.prices.FreeTextLogTrapTest
[INFO] Tests run: 19, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/kartwala/prices/FreeTextLogTrapTest.java`

Written first: what the old text log could not answer, and the history that can.

#### `src/test/java/com/kartwala/prices/PriceSecurityTest.java`

401, other sellers, support, names from headers, admins, changes with nobody signed in, odd input.

#### `src/test/java/com/kartwala/prices/PriceDatabaseTest.java`

Named constraints with plain SQL, how fast history grows, a change whose history fails.

#### `src/test/java/com/kartwala/prices/PriceContractTest.java`

Prices and history through HTTP.

#### `src/test/java/com/kartwala/prices/ApiTest.java`

Shared setup: the demo catalogue from V2 before each test, request helpers.

#### `src/test/java/com/kartwala/prices/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/kartwala/prices/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=HistoryBetweenDatesChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 19 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 23 tests pass (19 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## History between two moments

`GET /products/{id}/history?from=&to=`: only the changes from `from` (inclusive) to `to` (exclusive); the wrong way round is `400`.

**Done when:** both tests in `HistoryBetweenDatesChallengeTest` pass.

Hints

- Spring converts ISO-8601 text to `Instant` request parameters.
- The reference solution filters the entries it already reads; for long histories, filter in the Envers query with `AuditEntity.revisionProperty("changedAtMs")`.

#### `challenge/HistoryBetweenDatesChallengeTest.java`

``` code
package com.kartwala.prices;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /products/{id}/history?from=2026-10-02T00:00:00Z&to=... returns only the changes in that window
 * (from inclusive, to exclusive), still newest first. A window the wrong way round is 400.
 */
class HistoryBetweenDatesChallengeTest extends ApiTest {

    @Test
    void onlyTheChangesInTheWindow() throws Exception {
        setPrice("neha.store", 1, 549900);
        mvc.perform(get("/products/1/history").param("from", "2026-10-02T00:00:00Z").param("to", "2100-01-01T00:00:00Z")
                        .with(httpBasic("neha.store", "neha-demo-pass")))
                .andExpect(status().isOk()).andExpect(jsonPath("$", hasSize(1))).andExpect(jsonPath("$[0].pricePaise").value(549900));
        mvc.perform(get("/products/1/history").param("from", "2026-10-01T00:00:00Z").param("to", "2026-10-02T00:00:00Z")
                        .with(httpBasic("neha.store", "neha-demo-pass")))
                .andExpect(jsonPath("$", hasSize(1))).andExpect(jsonPath("$[0].changedBy").value("catalogue.import"));
    }

    @Test
    void aWindowTheWrongWayRoundIs400() throws Exception {
        mvc.perform(get("/products/1/history").param("from", "2026-10-05T00:00:00Z").param("to", "2026-10-01T00:00:00Z")
                .with(httpBasic("neha.store", "neha-demo-pass"))).andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## The price at a moment

A customer says "it was ₹54,999 when I ordered". `GET /products/{id}/price-at?time=` answers with the price live at that moment and who set it; before the product existed is `404`.

**Done when:** both tests in `PriceAtChallengeTest` pass.

Hints

- The last revision at or before the moment: `revisionProperty("changedAtMs").le(...)`, newest first, one result.

#### `challenge/PriceAtChallengeTest.java`

``` code
package com.kartwala.prices;

import org.junit.jupiter.api.Test;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: a customer says "it was ₹54,999 when I ordered on 1 October". GET /products/{id}/price-at?time=...
 * answers with the price that was live at that moment, and who set it. Before the product existed is 404.
 */
class PriceAtChallengeTest extends ApiTest {

    @Test
    void thePriceThatWasLiveThen() throws Exception {
        setPrice("neha.store", 1, 549900);
        mvc.perform(get("/products/1/price-at").param("time", "2026-10-01T12:00:00Z").with(httpBasic("sam.help", "sam-demo-pass")))
                .andExpect(status().isOk()).andExpect(jsonPath("$.pricePaise").value(5499900)).andExpect(jsonPath("$.setBy").value("catalogue.import"));
        mvc.perform(get("/products/1/price-at").param("time", "2100-01-01T00:00:00Z").with(httpBasic("sam.help", "sam-demo-pass")))
                .andExpect(jsonPath("$.pricePaise").value(549900)).andExpect(jsonPath("$.setBy").value("neha.store"));
    }

    @Test
    void beforeTheProductExistedIs404() throws Exception {
        mvc.perform(get("/products/1/price-at").param("time", "2026-09-01T00:00:00Z").with(httpBasic("sam.help", "sam-demo-pass"))).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## A history that grows forever, and drops nobody checked

Ten million products, a few price changes each per day: how big is `products_aud` in a year? Design retention (what may be thrown away, after how long, and how without breaking "append-only"), monthly partitions, and an archive. Then: should a seller's 90% drop go live at once, or wait for a second person?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: questions the text log cannot answer.
2.  Audit the entity with Envers; own the revision entity and its listener.
3.  Take who from the security context; refuse changes without one.
4.  Make the history tables append-only in the database.

## Design alternatives and trade-offs

| Approach                                       | What it costs                                                                      | Verdict                          |
|------------------------------------------------|------------------------------------------------------------------------------------|----------------------------------|
| Hibernate Envers with a custom revision entity | Two rows per change; Hibernate-only writes are audited.                            | Chosen                           |
| Free-text log lines                            | Cannot be queried or trusted.                                                      | The trap                         |
| Database triggers writing history              | Every writer audited, even SQL; "who" must reach the database (a session setting). | Stronger coverage, more plumbing |
| Change data capture (Debezium) to a log store  | History outside the app's database; another system.                                | At scale, many services          |
| Spring Data's @CreatedBy and @LastModifiedBy   | Only the last change, not the history.                                             | Not a history                    |

## Database design

| Object                       | What                              | Why                                                         |
|------------------------------|-----------------------------------|-------------------------------------------------------------|
| `revisions`, `products_aud`  | Envers' tables, created by Flyway | History as rows: one revision, one row per product changed. |
| `history_is_append_only`     | Triggers on both                  | No writer can change or delete history.                     |
| `revisions_changed_by_shape` | CHECK                             | A user name, not free text.                                 |
| `products_price_positive`    | CHECK                             | A price can never be zero or negative, from any writer.     |

**Transaction boundary:** a price change, its revision and its history row are one transaction.

``` code
CREATE TABLE products (
    id          bigint CONSTRAINT products_pk PRIMARY KEY,
    seller      text NOT NULL,
    name        text NOT NULL,
    price_paise bigint NOT NULL,
    CONSTRAINT products_price_positive CHECK (price_paise > 0),
    CONSTRAINT products_name_length CHECK (char_length(name) BETWEEN 1 AND 120)
);

-- One row per change set (Hibernate Envers' revision entity): when, and who, taken from the signed-in user.
CREATE TABLE revisions (
    id            bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT revisions_pk PRIMARY KEY,
    changed_at_ms bigint NOT NULL,
    changed_by    text NOT NULL,
    CONSTRAINT revisions_changed_by_shape CHECK (changed_by ~ '^[a-z0-9.]{1,40}$')
);

-- Envers writes the whole product as it was after each change: revtype 0 added, 1 changed, 2 removed.
CREATE TABLE products_aud (
    id          bigint NOT NULL,
    rev         bigint NOT NULL CONSTRAINT products_aud_revision_fk REFERENCES revisions,
    revtype     smallint NOT NULL,
    seller      text,
    name        text,
    price_paise bigint,
    CONSTRAINT products_aud_pk PRIMARY KEY (id, rev),
    CONSTRAINT products_aud_revtype CHECK (revtype IN (0, 1, 2))
);
CREATE INDEX products_aud_by_rev ON products_aud (rev);

-- History you can trust is history nobody can edit: rows are added, never changed or deleted, by any writer.
-- (TRUNCATE is a table owner's operation and is not covered; the application's database user should not own the tables.)
CREATE FUNCTION history_is_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'history_is_append_only: % on %', TG_OP, TG_TABLE_NAME USING ERRCODE = 'check_violation';
END $$ LANGUAGE plpgsql;
CREATE TRIGGER revisions_append_only BEFORE UPDATE OR DELETE ON revisions FOR EACH ROW EXECUTE FUNCTION history_is_append_only();
CREATE TRIGGER products_aud_append_only BEFORE UPDATE OR DELETE ON products_aud FOR EACH ROW EXECUTE FUNCTION history_is_append_only();
```

# 3 · Go deeper: Production

Growth  
Each change adds a whole row to `products_aud` and one to `revisions`. Plan partitions by month and an archive before the tables are large.

Who owns the tables  
The append-only triggers stop UPDATE and DELETE, not TRUNCATE or DROP: the application's database user should not own the tables.

Writes outside Hibernate  
Envers sees only changes made through Hibernate. Bulk SQL updates leave no history; route them through the entity, or add database-side capture.

Logs  
The history is the record; application logs are not.

# 3 · Go deeper: Interview

## Interview takeaways

What does Hibernate Envers do?

For each @Audited entity it keeps a \_aud table and writes the row as it is after each change, tied to a revision with a number and a time.

Where should "who" come from?

From the authenticated principal in the security context, set by the server. Never from the request body or a header.

How do you make history trustworthy?

Write it in the same transaction as the change, attribute it by the server, and forbid updates and deletes in the database.

What does Envers not see?

Changes made outside Hibernate: bulk SQL, other services, migrations.

Why does the same price twice add no history?

Hibernate flushes only changed rows; Envers records what Hibernate writes.

## Self-check rubric

| Area        | Meets the bar              | Above the bar                                          |
|-------------|----------------------------|--------------------------------------------------------|
| Correctness | All 19 tests pass.         | You ran the flawed version and explained each failure. |
| History     | Every change recorded.     | Queried by time; growth planned.                       |
| Who         | From the security context. | No change at all without a user.                       |
| Trust       | Same transaction.          | Append-only, enforced by the database.                 |

# 3 · Go deeper: Review

## The pull request

A teammate lets support fix prices for sellers who call in, and records the seller, not the agent, by taking the name from an `X-Changed-By` header when present. Read the three files and list every problem before opening the findings.

#### `review/ChangedByListener.java`

``` code
package com.kartwala.prices;

import org.hibernate.envers.RevisionListener;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

/** "Who" for the history: the signed-in user, or the person support is acting for (X-Changed-By). */
public class ChangedByListener implements RevisionListener {

    @Override
    public void newRevision(Object revision) {
        Authentication who = SecurityContextHolder.getContext().getAuthentication();
        if (who == null || !who.isAuthenticated()) {
            throw new IllegalStateException("A price change needs a signed-in user");
        }
        // Support fixes prices while the seller is on the phone: record the seller, not the support agent.
        String actingFor = RequestContextHolder.getRequestAttributes() instanceof ServletRequestAttributes r ? r.getRequest().getHeader("X-Changed-By") : null;
        ((Revision) revision).changedBy(actingFor != null ? actingFor : who.getName());
    }
}
```

#### `review/SecurityConfig.java`

``` code
package com.kartwala.prices;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
class SecurityConfig {

    @Bean
    SecurityFilterChain api(HttpSecurity http, ProblemResponses problems) throws Exception {
        http.authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.PUT, "/products/*/price").hasAnyRole("SELLER", "ADMIN", "SUPPORT")
                        .requestMatchers(HttpMethod.GET, "/products/*/history").hasAnyRole("SELLER", "ADMIN", "SUPPORT")
                        .requestMatchers("/error").permitAll()
                        .anyRequest().denyAll())
                .httpBasic(b -> b.authenticationEntryPoint(problems::unauthenticated))
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .csrf(csrf -> csrf.disable());   // credentials in a header with every request, no cookie a browser sends by itself
        return http.build();
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();
    }

    /** Demo users, password "name-demo-pass" (name before the dot). Support fixes prices for sellers who call in. */
    @Bean
    InMemoryUserDetailsManager users(PasswordEncoder encoder) {
        return new InMemoryUserDetailsManager(
                User.withUsername("neha.store").password(encoder.encode("neha-demo-pass")).roles("SELLER").build(),
                User.withUsername("arun.mart").password(encoder.encode("arun-demo-pass")).roles("SELLER").build(),
                User.withUsername("priya.ops").password(encoder.encode("priya-demo-pass")).roles("ADMIN").build(),
                User.withUsername("sam.help").password(encoder.encode("sam-demo-pass")).roles("SUPPORT").build());
    }
}
```

#### `review/Prices.java`

``` code
package com.kartwala.prices;

import jakarta.persistence.EntityManager;
import org.hibernate.envers.AuditReaderFactory;
import org.hibernate.envers.RevisionType;
import org.hibernate.envers.query.AuditEntity;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

@Service
class Prices {

    record Entry(long revision, Instant changedAt, String changedBy, String change, long pricePaise, Long previousPricePaise) {
    }

    private final Products products;
    private final EntityManager em;

    Prices(Products products, EntityManager em) {
        this.products = products;
        this.em = em;
    }

    /** A seller reaches their own listings; admins and support all of them. Anyone else's listing is a 404. */
    private Product reachable(Authentication who, long id, boolean toChange) {
        Product p = products.findById(id).orElseThrow(Prices::notFound);
        boolean all = has(who, "ROLE_ADMIN") || has(who, "ROLE_SUPPORT");
        if (!all && !p.seller().equals(who.getName())) {
            throw notFound();
        }
        return p;
    }

    private static boolean has(Authentication who, String role) {
        return who.getAuthorities().stream().anyMatch(a -> a.getAuthority().equals(role));
    }

    /** Hibernate writes the new price; Envers, in the same transaction, the revision (who, when) and the row as it now is. */
    @Transactional
    Product changePrice(Authentication who, long id, long pricePaise) {
        Product p = reachable(who, id, true);
        p.changePrice(pricePaise);
        return p;
    }

    /** Newest first, each with the price before it: a question the history can answer, not a log to grep. */
    @Transactional(readOnly = true)
    List<Entry> history(Authentication who, long id) {
        reachable(who, id, false);
        @SuppressWarnings("unchecked")
        List<Object[]> rows = AuditReaderFactory.get(em).createQuery().forRevisionsOfEntity(Product.class, false, true)
                .add(AuditEntity.id().eq(id)).addOrder(AuditEntity.revisionNumber().asc()).getResultList();
        List<Entry> entries = new ArrayList<>();
        Long previous = null;
        for (Object[] row : rows) {
            Product p = (Product) row[0];
            Revision r = (Revision) row[1];
            entries.add(new Entry(r.id(), Instant.ofEpochMilli(r.changedAtMs()), r.changedBy(), ((RevisionType) row[2]).name(), p.pricePaise(), previous));
            previous = p.pricePaise();
        }
        return entries.reversed();
    }

    static ResponseStatusException notFound() {
        return new ResponseStatusException(HttpStatus.NOT_FOUND, "No such product");
    }
}
```

## Findings

1The name comes from a header

"Support acts for the seller on the phone": now any client can put any name in `X-Changed-By`, and the history says what the client wanted. That is the free-text log again, with a timestamp.

**Test evidence:** `aHeaderNamingSomeoneElseIsIgnored` fails.

2Support may change any price

The fix for "sellers call support" gives every support agent every seller's prices, and their changes are recorded under the seller's name.

**Test evidence:** `supportReadsAnyHistoryButCannotChangeAPrice` fails.

## Same tests, flawed version

From `docs/review-run.txt`: the three flawed files copied over the real ones, then the full suite run.

| Test class            | Fixed version | Flawed version |
|-----------------------|---------------|----------------|
| `FreeTextLogTrapTest` | 4 / 4         | 4 / 4          |
| `PriceContractTest`   | 5 / 5         | 5 / 5          |
| `PriceDatabaseTest`   | 3 / 3         | 3 / 3          |
| `PriceSecurityTest`   | 7 / 7         | 5 / 7          |

If support must act for sellers, record both: the agent as who, the seller as on whose behalf. Both from the server's knowledge, neither from a header.
