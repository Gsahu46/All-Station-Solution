# Station 091 · Bulk shipment creation

Working Systems · 0–2 years · Core · Logistics · Types: Database

Spring Boot 4.1.1 · Java 25 · batch endpoints with per-item results · Bean Validation per item · JdbcClient · PostgreSQL 17 · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The sellers, shipments and addresses are demo data, not Dakroute's. Creating a shipment records a row; no courier is booked.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 9 tests.

# 1 · Understand

## The problem in real life

1.  **500 shipments, one call**

    Sellers upload the day's orders as one batch of up to 500 shipments.

2.  **One bad address**

    Item 312 had a five-digit PIN code. The whole batch ran in one transaction: the database refused that row, everything rolled back, and the seller got a 500 with a database message. They re-sent 500 orders, one at a time, to find it.

3.  **The fix**

    Each shipment is checked and saved on its own. The answer is a report: created or failed for each item, by position and by the seller's own reference, with the field that is wrong.

In a batch of independent items, one bad item should fail one item, and the answer should say which.

## What are we building?

A bulk endpoint that creates every valid shipment and reports, item by item, what was created and what was wrong.

## An everyday analogy

A good post office clerk takes the 499 letters that are fine and hands back one, with a note: "this one, the PIN code has five digits".

## How it works in 4 steps

1.  **Check the batch**: there is a list, with 1 to 500 items.
2.  **Check each item** on its own: every field rule, every problem listed.
3.  **Save each item** on its own: a refusal from the database fails that item only.
4.  **Report**: how many were created, how many failed, and one result per item in order.

Check yourself: half the items fail. Should the answer be 200 or an error?

200: the call worked, and the report says how each item went. An error status is for a call that could not be handled at all, such as an empty list or a body that is not JSON.

## What this station is not

- **No courier booking.** A shipment is a row.
- **No background processing.** 500 items are handled in the request; 50,000 would need a job (challenge 3).
- **No sign-in.** One seller, to keep the batch logic in view.

## Key terms

| Term                 | Simple meaning                                                     | Everyday example                                    | In this project        |
|----------------------|--------------------------------------------------------------------|-----------------------------------------------------|------------------------|
| **Batch endpoint**   | One call that does many things, here creating many shipments.      | Handing the post office a sack of letters.          | `POST /shipments/bulk` |
| **Per-item result**  | An answer for each item: done, or what is wrong with it.           | A receipt line per letter.                          | `results[]`            |
| **All-or-nothing**   | Either every item is done or none is.                              | The clerk returns the whole sack for one bad stamp. | the old code           |
| **Transaction**      | A group of database changes that succeed or fail together.         | One sealed envelope.                                | `@Transactional`       |
| **207 Multi-Status** | An HTTP status from WebDAV for many results in one answer, in XML. | A form meant for another office.                    | not used here          |
| **Batch limit**      | The most items one call may carry.                                 | "At most 500 letters per sack."                     | 500 (demo rule)        |

# 2 · Build: Spec

## Business problem

**Dakroute** (a fictional courier): sellers create 500 shipments in one call; one bad address makes the whole batch fail with no hint which.

## Acceptance criteria

Demo rules: 1 to 500 items per call; weight 1 to 50,000 g; PIN codes of six digits not starting with 0; a 10-digit Indian mobile number; refs of 3 to 40 letters, digits or dashes, unique.

1.  **Given** a batch with good and bad items, **then** `200`, the good ones created, each bad one failed by index, ref and field.
2.  **Given** an item with several problems, **then** all of them listed, by field.
3.  **Given** a ref used before or twice in the batch, **then** that item fails, the others do not.
4.  **Given** an item the database refuses for another reason, **then** that item fails, without SQL details.
5.  **Given** an empty list, more than 500 items, or a body that is not JSON of the right shape, **then** `400` and nothing saved.

## Requirements

- One result per item, in the order sent.
- No item's failure can undo another item.
- Every rule is also a named database constraint.

## Learning objectives

- Design a batch endpoint with per-item results.
- Validate items one by one instead of cascading validation over the list.
- Know what a transaction around a batch does, in PostgreSQL in particular.
- Choose a status for partial success, and a batch limit.

# 2 · Build: API contract

## Endpoint

| Method | Path              | Purpose                                                                   |
|--------|-------------------|---------------------------------------------------------------------------|
| `POST` | `/shipments/bulk` | `{shipments: [...]}`, 1 to 500: create each valid one; a report per item. |

## Status codes

| Status | When                                                                                       |
|--------|--------------------------------------------------------------------------------------------|
| 200    | The batch was handled: the report says, per item, created or failed                        |
| 400    | No list, an empty list, more than 500 items, or a body that is not JSON of the right shape |

## Captured examples

Captured with curl from the running app on 23 Oct 2026, in this order. JSON bodies are indented for reading; `Date`, connection and standard security headers are left out.

### Case 1: three shipments, the second with a five-digit PIN code

**Why:** two created; item 1 failed, naming `to.pincode`.

Request

``` code
POST /shipments/bulk HTTP/1.1
Content-Type: application/json

{
  "shipments": [
    {
      "ref": "ORD-1001",
      "fromPincode": "560001",
      "weightGrams": 1200,
      "to": {
        "name": "Meera Iyer",
        "line1": "14 Lodhi Road",
        "city": "New Delhi",
        "pincode": "110003",
        "phone": "9810000001"
      }
    },
    {
      "ref": "ORD-1002",
      "fromPincode": "560001",
      "weightGrams": 800,
      "to": {
        "name": "Arjun Rao",
        "line1": "2 MG Road",
        "city": "Pune",
        "pincode": "41100",
        "phone": "9820000002"
      }
    },
    {
      "ref": "ORD-1003",
      "fromPincode": "560001",
      "weightGrams": 2500,
      "to": {
        "name": "Meera Iyer",
        "line1": "14 Lodhi Road",
        "city": "New Delhi",
        "pincode": "110003",
        "phone": "9810000001"
      }
    }
  ]
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 293

{
  "created": 2,
  "failed": 1,
  "results": [
    {
      "index": 0,
      "ref": "ORD-1001",
      "status": "created",
      "shipmentId": 1
    },
    {
      "index": 1,
      "ref": "ORD-1002",
      "status": "failed",
      "errors": [
        {
          "field": "to.pincode",
          "message": "must be 6 digits, not starting with 0"
        }
      ]
    },
    {
      "index": 2,
      "ref": "ORD-1003",
      "status": "created",
      "shipmentId": 2
    }
  ]
}
```

### Case 2: one item with three problems

**Why:** all three listed, by field.

Request

``` code
POST /shipments/bulk HTTP/1.1
Content-Type: application/json

{
  "shipments": [
    {
      "ref": "ORD-1004",
      "fromPincode": "560001",
      "weightGrams": 0,
      "to": {
        "name": " ",
        "line1": "14 Lodhi Road",
        "city": "New Delhi",
        "pincode": "110003",
        "phone": "12345"
      }
    }
  ]
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 288

{
  "created": 0,
  "failed": 1,
  "results": [
    {
      "index": 0,
      "ref": "ORD-1004",
      "status": "failed",
      "errors": [
        {
          "field": "to.name",
          "message": "must not be blank"
        },
        {
          "field": "to.phone",
          "message": "must be a 10-digit Indian mobile number"
        },
        {
          "field": "weightGrams",
          "message": "must be greater than or equal to 1"
        }
      ]
    }
  ]
}
```

### Case 3: ORD-1001 again

**Why:** the ref is unique: that item fails.

Request

``` code
POST /shipments/bulk HTTP/1.1
Content-Type: application/json

{
  "shipments": [
    {
      "ref": "ORD-1001",
      "fromPincode": "560001",
      "weightGrams": 900,
      "to": {
        "name": "Meera Iyer",
        "line1": "14 Lodhi Road",
        "city": "New Delhi",
        "pincode": "110003",
        "phone": "9810000001"
      }
    }
  ]
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 158

{
  "created": 0,
  "failed": 1,
  "results": [
    {
      "index": 0,
      "ref": "ORD-1001",
      "status": "failed",
      "errors": [
        {
          "field": "ref",
          "message": "is already used by another shipment"
        }
      ]
    }
  ]
}
```

### Case 4: an empty list

**Why:** `400`: nothing to do.

Request

``` code
POST /shipments/bulk HTTP/1.1
Content-Type: application/json

{
  "shipments": []
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/shipments/bulk",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 5: weightGrams "heavy"

**Why:** the body is not JSON of the right shape, so there is no item to report on: `400` for the call.

Request

``` code
POST /shipments/bulk HTTP/1.1
Content-Type: application/json

{
  "shipments": [
    {
      "ref": "ORD-1005",
      "fromPincode": "560001",
      "weightGrams": "heavy",
      "to": {
        "name": "Meera Iyer",
        "line1": "14 Lodhi Road",
        "city": "New Delhi",
        "pincode": "110003",
        "phone": "9810000001"
      }
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
  "instance": "/shipments/bulk",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 6: 501 items

**Why:** over the limit: `400`, nothing saved. The request line is shortened here; all 501 items were sent.

Request

``` code
POST /shipments/bulk HTTP/1.1
Content-Type: application/json

{"shipments":[ 501 items: {"ref":"BIG-1", ...} to {"ref":"BIG-501", ...} ]}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/shipments/bulk",
  "status": 400,
  "title": "Bad Request"
}
```

## The shipments afterwards

``` code
 id |   ref    | from_pincode |  to_city  | to_pincode | weight_grams 
----+----------+--------------+-----------+------------+--------------
  1 | ORD-1001 | 560001       | New Delhi | 110003     |         1200
  2 | ORD-1003 | 560001       | New Delhi | 110003     |         2500
(2 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                           | What happens                     | Proved by                                            |
|------------------------------------------------|----------------------------------|------------------------------------------------------|
| A good batch                                   | One result per item, in order    | `aGoodBatchIsCreatedWithOneResultPerItemInOrder`     |
| Several problems in one item                   | All listed by field              | `everyProblemInAnItemIsListedByField`                |
| A ref used before, or twice in the batch       | That item fails                  | `aRefUsedBeforeOrTwiceInTheBatchFailsThatItemOnly`   |
| Empty list, no list, a wrong type, a null item | `400`; a null item fails alone   | `theBatchAsAWholeMustBeUsable`                       |
| 500 and 501 items                              | Created; `400`                   | `fiveHundredIsTheLimit`                              |
| The database refuses one item                  | That item fails, the others stay | `anItemTheDatabaseRefusesFailsAloneAndTheOthersStay` |
| Rules written by plain SQL                     | Refused by named constraints     | `shipmentRulesHoldWithoutJava`                       |

## The trap

Plausible but wrong

All-or-nothing batches with no per-item results.

- **The old way.** The test inserts three shipments in one transaction; the second has a five-digit PIN code. The database refuses it, the transaction rolls back, nothing is saved, and the only message names a database constraint.
- **The API.** The same three items: two created, and item 1 failed with `to.pincode`: "must be 6 digits, not starting with 0".

While building, each part was undone once: one transaction around the loop turned 2 tests red; validation cascading over the list 2; no per-item validation 2; no specific message for a used ref 1; no batch limit 1; refs not upper-cased 2; indexes off by one 3. Trimming names changed no test, so the trimming was removed.

``` code
package com.dakroute.shipments;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old endpoint saved the whole batch in one transaction. Item 312 of 500 had a five-digit PIN
 * code: the database refused it, the transaction rolled back, nothing was created, and the seller got a 500 with no
 * hint which item. Here the same thing with three items.
 */
class AllOrNothingTrapTest extends ApiTest {

    @Autowired
    TransactionTemplate tx;

    void insert(String ref, String toPincode) {
        jdbc.sql("""
                INSERT INTO shipments (ref, from_pincode, to_name, to_line1, to_city, to_pincode, to_phone, weight_grams)
                VALUES (?, '560001', 'Meera Iyer', '14 Lodhi Road', 'New Delhi', ?, '9810000001', 1200)""").params(ref, toPincode).update();
    }

    @Test
    void theOldWayOneBadItemCreatedNothingAndSaidNothingUseful() {
        assertThatThrownBy(() -> tx.executeWithoutResult(s -> {
            insert("ORD-1", "110003");
            insert("ORD-2", "11003");    // five digits
            insert("ORD-3", "110003");
        })).hasMessageContaining("shipments_pincodes");   // a database message, not a field a seller can fix
        assertThat(count()).isZero();
    }

    @Test
    void theApiCreatesTheGoodItemsAndNamesTheBadOne() throws Exception {
        bulk(List.of(item("ORD-1"), item("ORD-2").replace("110003", "11003"), item("ORD-3"))).andExpect(status().isOk())
                .andExpect(jsonPath("$.created").value(2)).andExpect(jsonPath("$.failed").value(1))
                .andExpect(jsonPath("$.results[1].index").value(1)).andExpect(jsonPath("$.results[1].ref").value("ORD-2"))
                .andExpect(jsonPath("$.results[1].status").value("failed"))
                .andExpect(jsonPath("$.results[1].errors[0].field").value("to.pincode"))
                .andExpect(jsonPath("$.results[1].errors[0].message").value("must be 6 digits, not starting with 0"));
        assertThat(count()).isEqualTo(2);
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
./mvnw test                 # all 9 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Run `docs/capture.sh` against your running app (from the station folder, with `docker compose` up): it sends the six requests above and writes the answers to `docs/captures/`. Then edit one item in case 1 and send it again with the `curl` line from that file.

## Troubleshooting

| You see                                                 | Cause                                                                    | Fix                                                 |
|---------------------------------------------------------|--------------------------------------------------------------------------|-----------------------------------------------------|
| Every item after a failed one says "could not be saved" | A transaction around the batch: PostgreSQL aborts it at the first error. | Save each item on its own, as `BulkShipments` does. |
| One bad item makes the whole call a 400                 | `@Valid` cascades over the list's items.                                 | Validate each item yourself and report it.          |
| `Could not find a valid Docker environment`             | Docker is not running.                                                   | Start Docker Desktop or the Docker service.         |

## Project layout

``` tree
stations/091-bulk-shipment-creation/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/dakroute/shipments/
│   ├── BulkShipmentController.java   ├── BulkShipments.java   └── ShipmentsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__shipments.sql
├── src/test/java/com/dakroute/shipments/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/dakroute/shipments/BulkShipmentController.java`

Does  
The endpoint.

Why  
Checks the list (present, 1 to 500) and hands it over; answers 200 with the report.

Without it  
One bad item turning the whole call into a 400.

- No `@Valid` on the list's items: with it, one bad item makes the whole call a 400, the all-or-nothing answer again.
- Not 207 Multi-Status: that status comes from WebDAV (RFC 4918), whose clients expect an XML body.

#### `src/main/java/com/dakroute/shipments/BulkShipments.java`

Does  
Checking and saving each item on its own.

Why  
A Validator per item, errors sorted by field; one INSERT per item, committed on its own; a used ref and other refusals reported as that item's failure.

Without it  
One item's failure undoing or hiding the others.

No transaction around the loop: in PostgreSQL, the first refused statement aborts the whole transaction, so every later item fails and the earlier ones are rolled back at commit. See the Review tab.

#### `src/main/resources/db/migration/V1__shipments.sql`

Does  
Shipments and their rules.

Why  
Ref unique and shaped, PIN codes, phone, weight, address present.

Without it  
A bad shipment from any writer.

#### `src/main/resources/application.yaml`

Database connection; fractions refused for whole-number fields.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/dakroute/shipments/ShipmentsApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                 | Result |
|---------------|-------------------------------------------------------|----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `BulkContractTest` (5)     | pass   |
| Every station | Reproduce the failure before the fix                  | `AllOrNothingTrapTest` (2) | pass   |
| Database      | Rollback and constraint tests against a real database | `ShipmentDatabaseTest` (2) | pass   |

There is no "not found" here: a batch creates, it does not look anything up. The 400 cases stand in for invalid calls.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.dakroute.shipments.BulkContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.dakroute.shipments.ShipmentDatabaseTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.dakroute.shipments.AllOrNothingTrapTest
[INFO] Tests run: 9, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/dakroute/shipments/AllOrNothingTrapTest.java`

Written first: one transaction for the batch, and the API's report.

#### `src/test/java/com/dakroute/shipments/BulkContractTest.java`

The report, field errors, used refs, bad calls, the limit.

#### `src/test/java/com/dakroute/shipments/ShipmentDatabaseTest.java`

Named constraints with plain SQL; one item refused by the database.

#### `src/test/java/com/dakroute/shipments/ApiTest.java`

Shared setup: no shipments before each test, an item builder, request helpers.

#### `src/test/java/com/dakroute/shipments/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/dakroute/shipments/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=ValidateOnlyChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 9 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 12 tests pass (9 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## A dry run

`POST /shipments/bulk?validateOnly=true` checks a batch without saving it: good items `valid`, bad ones `failed` with the same errors as a real call, including a ref already used.

**Done when:** the test in `ValidateOnlyChallengeTest` passes.

Hints

- A `@RequestParam(defaultValue = "false")` passed down to where an item would be saved.
- Checking a used ref without saving means looking it up first.

#### `challenge/ValidateOnlyChallengeTest.java`

``` code
package com.dakroute.shipments;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /shipments/bulk?validateOnly=true checks a batch without saving it, so a seller can fix a file
 * before sending it for real. Good items are "valid"; bad ones "failed" with the same errors as a real call,
 * including a ref already used.
 */
class ValidateOnlyChallengeTest extends ApiTest {

    @Test
    void aDryRunReportsAndSavesNothing() throws Exception {
        bulk(java.util.List.of(item("ORD-1")));
        String body = "{\"shipments\":[" + item("ORD-1").replace("1200", "1500") + "," + item("ORD-2") + "," + item("ORD-3").replace("110003", "11003") + "]}";
        mvc.perform(post("/shipments/bulk").param("validateOnly", "true").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk()).andExpect(jsonPath("$.created").value(0)).andExpect(jsonPath("$.failed").value(2))
                .andExpect(jsonPath("$.results[0].errors[0].message").value("is already used by another shipment"))
                .andExpect(jsonPath("$.results[1].status").value("valid"))
                .andExpect(jsonPath("$.results[2].errors[0].field").value("to.pincode"));
        assertThat(count()).isOne();
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## The same file twice

A seller whose upload timed out sends the same file again. An item identical to the shipment already created under its ref is `existing`, with that shipment's id; the same ref with other details still fails. The report counts `existing`.

**Done when:** both tests in `ResubmitChallengeTest` pass (the second already passes: it guards the old behaviour).

Hints

- Compare every stored field, not just the ref.
- Leave `existing` out of the report when it is 0, so other clients see no change (`@JsonInclude(NON_DEFAULT)`).

#### `challenge/ResubmitChallengeTest.java`

``` code
package com.dakroute.shipments;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 2: a seller whose upload timed out sends the same file again. An item identical to a shipment already
 * created under its ref is "existing" with that shipment's id, not a failure; the same ref with different details
 * still fails, as before. The report counts them under "existing".
 */
class ResubmitChallengeTest extends ApiTest {

    @Test
    void theSameFileTwiceCreatesEachShipmentOnce() throws Exception {
        bulk(List.of(item("ORD-1"), item("ORD-2")));
        bulk(List.of(item("ORD-1"), item("ORD-2"), item("ORD-3"))).andExpect(jsonPath("$.created").value(1))
                .andExpect(jsonPath("$.existing").value(2)).andExpect(jsonPath("$.failed").value(0))
                .andExpect(jsonPath("$.results[0].status").value("existing")).andExpect(jsonPath("$.results[0].shipmentId").value(1))
                .andExpect(jsonPath("$.results[2].status").value("created"));
        assertThat(count()).isEqualTo(3);
    }

    @Test
    void theSameRefWithOtherDetailsStillFails() throws Exception {
        bulk(List.of(item("ORD-1")));
        bulk(List.of(item("ORD-1").replace("1200", "1500"))).andExpect(jsonPath("$.failed").value(1))
                .andExpect(jsonPath("$.results[0].errors[0].message").value("is already used by another shipment"));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## 50,000 items

A marketplace wants to send 50,000 shipments at once. Design it as a job: upload, `202` with a job id, progress, and a downloadable report (station 098 does long-running work). How do you keep the per-item results, let the seller fix and resend only the failed ones, and stop one seller's job from slowing everyone else?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: one transaction for the batch.
2.  Check the list; check each item with a Validator; collect errors by field.
3.  Insert each item in its own statement; turn a refusal into that item's failure.
4.  Return the report: counts and one result per item.

## Design alternatives and trade-offs

| Approach                                         | What it costs                                                           | Verdict                 |
|--------------------------------------------------|-------------------------------------------------------------------------|-------------------------|
| Independent items, 200 with a report             | Clients must read the report, not just the status.                      | Chosen                  |
| One transaction, all-or-nothing                  | One bad item fails all; without a report, the seller cannot tell which. | The trap                |
| All-or-nothing, with a report of what would fail | Right when items depend on each other (a payment and its order lines).  | For dependent items     |
| 207 Multi-Status                                 | WebDAV's status; clients expect XML.                                    | Uncommon for JSON APIs  |
| A JDBC batch insert                              | Faster; a failure in the batch is harder to tie to one item.            | When speed matters more |

Google's API Improvement Proposals AIP-231 to AIP-235 are Google's own design guide for batch methods, not a standard; compare their choices with this one.

## Database design

| Object                                             | What   | Why                                         |
|----------------------------------------------------|--------|---------------------------------------------|
| `shipments_ref_unique`                             | UNIQUE | A ref is one shipment, even across batches. |
| `shipments_pincodes`, `shipments_phone`            | CHECKs | Addresses a courier can deliver to.         |
| `shipments_weight`                                 | CHECK  | 1 to 50,000 g.                              |
| `shipments_address_present`, `shipments_ref_shape` | CHECKs | No blank names or odd refs from any writer. |

**Transaction boundary:** one INSERT per item, committed on its own. Nothing groups items: they do not depend on each other.

``` code
-- One row per shipment. The seller's own reference identifies it, so a batch sent twice cannot create it twice.
CREATE TABLE shipments (
    id            bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT shipments_pk PRIMARY KEY,
    ref           text NOT NULL,
    from_pincode  text NOT NULL,
    to_name       text NOT NULL,
    to_line1      text NOT NULL,
    to_city       text NOT NULL,
    to_pincode    text NOT NULL,
    to_phone      text NOT NULL,
    weight_grams  integer NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT shipments_ref_unique UNIQUE (ref),
    CONSTRAINT shipments_ref_shape CHECK (ref ~ '^[A-Z0-9-]{3,40}$'),
    CONSTRAINT shipments_pincodes CHECK (from_pincode ~ '^[1-9][0-9]{5}$' AND to_pincode ~ '^[1-9][0-9]{5}$'),
    CONSTRAINT shipments_phone CHECK (to_phone ~ '^[6-9][0-9]{9}$'),
    CONSTRAINT shipments_weight CHECK (weight_grams BETWEEN 1 AND 50000),
    CONSTRAINT shipments_address_present CHECK (length(trim(to_name)) > 0 AND length(trim(to_line1)) > 0 AND length(trim(to_city)) > 0)
);
```

# 3 · Go deeper: Production

Limits  
Limit items per call and the body size (the server's request size limit), and say so in the docs; a batch that is too big is refused before any work.

Time  
500 inserts take a moment; much more and the request time grows past what clients and load balancers wait. Move big batches to a job.

Retries  
A client that times out re-sends the batch: unique refs stop duplicates (challenge 2 makes it friendly).

Metrics  
Count failed items by field: a spike in one field usually means a client bug, not bad data.

# 3 · Go deeper: Interview

## Interview takeaways

200, 207 or 400 for partial success?

200 with a per-item report is the common choice for JSON APIs. 207 is WebDAV's and implies an XML body. 400 is for a call that cannot be handled at all.

Why not one transaction for the batch?

Items are independent, so one item's problem should not undo the others. In PostgreSQL the first failed statement also aborts the transaction, so later items fail too.

How do you validate items one by one in Spring?

Do not cascade @Valid over the list; inject a Validator and validate each item, collecting the violations.

How do you make a batch safe to resend?

Give each item a client reference with a unique constraint, and answer an identical resend with the existing item.

When is all-or-nothing right?

When the items depend on each other, like an order and its lines, or a transfer's two sides.

## Self-check rubric

| Area        | Meets the bar                    | Above the bar                                                          |
|-------------|----------------------------------|------------------------------------------------------------------------|
| Correctness | All 9 tests pass.                | You ran the flawed version and explained each failure.                 |
| Results     | A result per item.               | Every problem by field, in order, with the client's reference.         |
| Isolation   | Bad items do not stop good ones. | You can explain what a transaction around the loop does in PostgreSQL. |
| Limits      | A batch limit.                   | Limits on items, size and time, documented.                            |

# 3 · Go deeper: Review

## The pull request

A teammate wraps the batch in one `@Transactional`, "so a batch is consistent and 500 commits become one", and raises the limit to 5,000 for big sellers. The per-item report is kept. Read the file and list every problem before opening the findings.

#### `review/BulkShipments.java`

``` code
package com.dakroute.shipments;

import com.fasterxml.jackson.annotation.JsonInclude;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Valid;
import jakarta.validation.Validator;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.dao.DataAccessException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

@Service
class BulkShipments {

    /** Big sellers asked for bigger batches. */
    static final int MAX_BATCH = 5000;

    record Address(@NotBlank String name, @NotBlank String line1, @NotBlank String city,
                   @NotNull @Pattern(regexp = "[1-9][0-9]{5}", message = "must be 6 digits, not starting with 0") String pincode,
                   @NotNull @Pattern(regexp = "[6-9][0-9]{9}", message = "must be a 10-digit Indian mobile number") String phone) {
    }

    record ShipmentRequest(@NotNull @Pattern(regexp = "[A-Za-z0-9-]{3,40}", message = "must be 3 to 40 letters, digits or dashes") String ref,
                           @NotNull @Pattern(regexp = "[1-9][0-9]{5}", message = "must be 6 digits, not starting with 0") String fromPincode,
                           @NotNull @Valid Address to,
                           @Min(1) @Max(50_000) int weightGrams) {
    }

    record FieldError(String field, String message) {
    }

    @JsonInclude(JsonInclude.Include.NON_NULL)
    record ItemResult(int index, String ref, String status, Long shipmentId, List<FieldError> errors) {
    }

    record Report(int created, int failed, List<ItemResult> results) {
    }

    private final JdbcClient jdbc;
    private final Validator validator;

    BulkShipments(JdbcClient jdbc, Validator validator) {
        this.jdbc = jdbc;
        this.validator = validator;
    }

    /**
     * Each shipment stands alone: it is checked on its own and saved in its own statement, so one bad address fails
     * one item, and the report says which, by its position and the seller's reference.
     */
    @Transactional   // one transaction for the whole batch: consistent, and faster than 500 commits
    Report create(List<ShipmentRequest> items) {
        List<ItemResult> results = new ArrayList<>();
        for (int i = 0; i < items.size(); i++) {
            results.add(createOne(i, items.get(i)));
        }
        int created = (int) results.stream().filter(r -> r.status().equals("created")).count();
        return new Report(created, results.size() - created, results);
    }

    private ItemResult createOne(int index, ShipmentRequest s) {
        if (s == null) {
            return failed(index, null, List.of(new FieldError("", "must not be null")));
        }
        List<FieldError> errors = validator.validate(s).stream()
                .sorted(Comparator.comparing((ConstraintViolation<ShipmentRequest> v) -> v.getPropertyPath().toString()))
                .map(v -> new FieldError(v.getPropertyPath().toString(), v.getMessage())).toList();
        if (!errors.isEmpty()) {
            return failed(index, s.ref(), errors);
        }
        String ref = s.ref().toUpperCase(Locale.ROOT);
        try {
            long id = jdbc.sql("""
                            INSERT INTO shipments (ref, from_pincode, to_name, to_line1, to_city, to_pincode, to_phone, weight_grams)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""")
                    .params(ref, s.fromPincode(), s.to().name(), s.to().line1(), s.to().city(), s.to().pincode(), s.to().phone(), s.weightGrams())
                    .query(Long.class).single();
            return new ItemResult(index, ref, "created", id, null);
        } catch (DuplicateKeyException e) {
            return failed(index, ref, List.of(new FieldError("ref", "is already used by another shipment")));
        } catch (DataAccessException e) {
            // The database refused it for a reason Java did not check: say so, without passing on SQL details.
            return failed(index, ref, List.of(new FieldError("", "could not be saved")));
        }
    }

    private static ItemResult failed(int index, String ref, List<FieldError> errors) {
        return new ItemResult(index, ref, "failed", null, errors);
    }
}
```

## Findings

1One transaction for the whole batch

"Consistent, and faster than 500 commits": but in PostgreSQL the first refused statement aborts the transaction. Every later item then fails with "could not be saved", and at commit the items reported as created are rolled back. Seen while building: a report saying "created": 1 for an item that was never stored.

**Test evidence:** `aRefUsedBeforeOrTwiceInTheBatchFailsThatItemOnly` and `anItemTheDatabaseRefusesFailsAloneAndTheOthersStay` fail.

2A batch limit of 5,000

"Big sellers asked for bigger batches": ten times the work in one request, past the time clients and load balancers wait, with nothing saying where the work stopped.

**Test evidence:** `fiveHundredIsTheLimit` fails.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class             | Fixed version | Flawed version |
|------------------------|---------------|----------------|
| `AllOrNothingTrapTest` | 2 / 2         | 2 / 2          |
| `BulkContractTest`     | 5 / 5         | 3 / 5          |
| `ShipmentDatabaseTest` | 2 / 2         | 1 / 2          |

With only good items, the flawed version passes: one transaction commits them all. It takes one refused item to see the report lie.
