# Station 090 · Partner shipping-rate API docs

Working Systems · 0–2 years · Core · Logistics · Types: none

Spring Boot 4.1.1 · Java 25 · OpenAPI 3.1 · springdoc-openapi 3.1.1 · documented errors and examples, tested against the API. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The tariff, zones and the list of PIN codes not served are demo rules, not Dakroute's. A quote is a price: nothing is booked or shipped. The partner server and support addresses are examples.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 11 tests.

# 1 · Understand

## The problem in real life

1.  **A PDF from two releases ago**

    Dakroute's partners integrate from a PDF someone wrote by hand. It says weight_kg and origin; the API takes weightGrams and fromPincode.

2.  **200 tickets a month**

    Every partner who copies the PDF's example gets 400, writes to support, and waits. Nobody updated the PDF when the API changed, because nothing made them.

3.  **The fix**

    The docs are generated from the code, with the errors and examples in it, and a test sends every example to the API and compares the answers. A change to the docs shows as a diff to review.

Docs that nothing checks will drift. Generate them from the code and test them against the API.

## What are we building?

A rate-quote endpoint whose OpenAPI description is generated from the code, documents every error with an example, and is tested so that every example really works.

## An everyday analogy

A recipe printed straight from the kitchen's own cards, and tasted: every recipe in the book is cooked once before the book is printed.

## How it works in 4 steps

1.  **Describe in code**: field limits come from the validation annotations, descriptions and examples from annotations next to them.
2.  **Generate**: springdoc serves the description at `/v3/api-docs`.
3.  **Test it**: every example is sent; every documented answer is compared with the real one.
4.  **Review it**: the description is compared with an approved copy; a change shows as a diff in the pull request.

Check yourself: the docs are generated from the code. Can they still be wrong?

Yes. springdoc first said `weightGrams` was optional, because it only knows `@NotNull`, while the API refused a request without it. The test that removes each field found it: see Tests.

## What this station is not

- **No docs website.** The description is JSON; Swagger UI or Redoc can show it (one more dependency).
- **No real tariff.** Zones and prices are demo rules.
- **No booking.** A quote is a price.

## Key terms

| Term                  | Simple meaning                                                                   | Everyday example                                    | In this project    |
|-----------------------|----------------------------------------------------------------------------------|-----------------------------------------------------|--------------------|
| **API docs**          | The description partners read to call your API: paths, fields, errors, examples. | The manual for a machine.                           | `GET /v3/api-docs` |
| **OpenAPI**           | A standard format for describing HTTP APIs, readable by people and tools.        | A standard wiring diagram any electrician can read. | OpenAPI 3.1        |
| **springdoc-openapi** | A library that builds the OpenAPI description from Spring code.                  | A manual printed from the machine's own blueprint.  | version 3.1.1      |
| **Example**           | A real request or answer shown in the docs.                                      | A filled-in sample form.                            | `@ExampleObject`   |
| **Drift**             | Docs and API slowly saying different things.                                     | A map of a town that kept building.                 | the old PDF        |
| **Contract review**   | Looking at every change to the API description before it ships.                  | Checking the new map before it is printed.          | `approved.json`    |

# 2 · Build: Spec

## Business problem

**Dakroute** (a fictional courier): partners integrate from a stale PDF and open 200 tickets a month.

## Acceptance criteria

Demo tariff: same first three PIN digits LOCAL (₹40 per started 500 g), same first two REGIONAL (₹55), else NATIONAL (₹75); EXPRESS half as much again; chargeable weight is the larger of actual and volumetric (L×W×H cm / 5, in grams); GST 18%; at most 50 kg; PIN codes 744101 and 194101 not served.

1.  **Given** a valid parcel, **then** `200` with the zone, chargeable weight, price, GST and total in paise.
2.  **Given** invalid input, **then** `400`; a parcel the network cannot carry, `422`.
3.  **Given** `/v3/api-docs`, **then** an OpenAPI description with every field's limits, every error, and examples.
4.  **Given** any example in the docs, **then** sending it gets the documented status and answer.
5.  **Given** a change to the API, **then** the description differs from the approved copy until someone reviews and approves it.

## Requirements

- No hand-written docs that can disagree with the code.
- Errors documented with examples, not only the happy path.
- The docs' required fields are exactly the ones the API refuses without.

## Learning objectives

- Generate OpenAPI with springdoc and enrich it with annotations.
- Document errors and examples that are true.
- Test docs against the API instead of trusting them.
- Review API changes as diffs of the description.

# 2 · Build: API contract

## Endpoints

| Method | Path           | Purpose                                           |
|--------|----------------|---------------------------------------------------|
| `POST` | `/rate-quotes` | Price one parcel between two PIN codes.           |
| `GET`  | `/v3/api-docs` | The OpenAPI description, generated from the code. |

## Status codes

| Status | When                                                                         |
|--------|------------------------------------------------------------------------------|
| 200    | The quote; the description                                                   |
| 400    | A field missing, of the wrong type, or out of range                          |
| 422    | Valid, but the network cannot carry it: over 50 kg, or a PIN code not served |

## Captured examples

Captured with curl from the running app on 22 Oct 2026, in this order. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: 1.2 kg, Bengaluru to Delhi

**Why:** NATIONAL, 3 started slabs of 500 g: ₹225 + ₹40.50 GST.

Request

``` code
POST /rate-quotes HTTP/1.1
Content-Type: application/json

{
  "fromPincode": "560001",
  "toPincode": "110001",
  "weightGrams": 1200,
  "lengthCm": 30,
  "widthCm": 20,
  "heightCm": 10,
  "service": "STANDARD"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 136

{
  "quoteId": "Q-1",
  "zone": "NATIONAL",
  "chargeableWeightGrams": 1200,
  "pricePaise": 22500,
  "gstPaise": 4050,
  "totalPaise": 26550,
  "estimatedDays": 5
}
```

### Case 2: 800 g but 60×40×40 cm, EXPRESS, within Bengaluru

**Why:** the volumetric weight, 19.2 kg, is charged.

Request

``` code
POST /rate-quotes HTTP/1.1
Content-Type: application/json

{
  "fromPincode": "560001",
  "toPincode": "560034",
  "weightGrams": 800,
  "lengthCm": 60,
  "widthCm": 40,
  "heightCm": 40,
  "service": "EXPRESS"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 137

{
  "quoteId": "Q-2",
  "zone": "LOCAL",
  "chargeableWeightGrams": 19200,
  "pricePaise": 234000,
  "gstPaise": 42120,
  "totalPaise": 276120,
  "estimatedDays": 1
}
```

### Case 3: 62 kg

**Why:** valid input the network cannot carry: `422`.

Request

``` code
POST /rate-quotes HTTP/1.1
Content-Type: application/json

{
  "fromPincode": "560001",
  "toPincode": "110001",
  "weightGrams": 62000,
  "lengthCm": 80,
  "widthCm": 60,
  "heightCm": 60,
  "service": "STANDARD"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "Parcels above 50000 g cannot be carried",
  "instance": "/rate-quotes",
  "status": 422,
  "title": "Unprocessable Content"
}
```

### Case 4: to 744101

**Why:** not served yet: `422`.

Request

``` code
POST /rate-quotes HTTP/1.1
Content-Type: application/json

{
  "fromPincode": "560001",
  "toPincode": "744101",
  "weightGrams": 500,
  "lengthCm": 10,
  "widthCm": 10,
  "heightCm": 10,
  "service": "STANDARD"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "This PIN code is not served yet",
  "instance": "/rate-quotes",
  "status": 422,
  "title": "Unprocessable Content"
}
```

### Case 5: a five-digit PIN code

**Why:** `400`.

Request

``` code
POST /rate-quotes HTTP/1.1
Content-Type: application/json

{
  "fromPincode": "56001",
  "toPincode": "110001",
  "weightGrams": 1200,
  "lengthCm": 30,
  "widthCm": 20,
  "heightCm": 10,
  "service": "STANDARD"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/rate-quotes",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 6: the old PDF's example

**Why:** its field names no longer exist: `400`, the ticket partners kept opening.

Request

``` code
POST /rate-quotes HTTP/1.1
Content-Type: application/json

{
  "origin": "560001",
  "destination": "110001",
  "weight_kg": 1.2,
  "dimensions": "30x20x10",
  "type": "surface"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Failed to read request",
  "instance": "/rate-quotes",
  "status": 400,
  "title": "Bad Request"
}
```

## The generated description

From `docs/captures/api-docs.json`, fetched from the running app (200 application/json). The request schema, as partners see it:

``` code
{
  "type": "object",
  "description": "A parcel to price.",
  "properties": {
    "fromPincode": {
      "type": "string",
      "description": "Pickup PIN code: six digits, not starting with 0.",
      "example": "560001",
      "pattern": "[1-9][0-9]{5}"
    },
    "toPincode": {
      "type": "string",
      "description": "Delivery PIN code.",
      "example": "110001",
      "pattern": "[1-9][0-9]{5}"
    },
    "weightGrams": {
      "type": "integer",
      "format": "int32",
      "description": "Actual weight in grams. Above 50,000 g the parcel service cannot carry it (422).",
      "example": 1200,
      "minimum": 1
    },
    "lengthCm": {
      "type": "integer",
      "format": "int32",
      "description": "Length in cm.",
      "example": 30,
      "maximum": 150,
      "minimum": 1
    },
    "widthCm": {
      "type": "integer",
      "format": "int32",
      "description": "Width in cm.",
      "example": 20,
      "maximum": 150,
      "minimum": 1
    },
    "heightCm": {
      "type": "integer",
      "format": "int32",
      "description": "Height in cm.",
      "example": 10,
      "maximum": 150,
      "minimum": 1
    },
    "service": {
      "type": "string",
      "description": "STANDARD or EXPRESS.",
      "enum": [
        "STANDARD",
        "EXPRESS"
      ],
      "example": "STANDARD"
    }
  },
  "required": [
    "fromPincode",
    "heightCm",
    "lengthCm",
    "service",
    "toPincode",
    "weightGrams",
    "widthCm"
  ]
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                            | What happens                             | Proved by                                                           |
|-----------------------------------------------------------------|------------------------------------------|---------------------------------------------------------------------|
| A national parcel                                               | Slabs, GST, total                        | `aNationalParcelIsPricedBySlabWithGst`                              |
| Local, regional, volumetric, express, a started slab            | Priced by the demo tariff                | `zonesVolumetricWeightAndExpress`                                   |
| GST with a fraction of a paisa                                  | Rounded to the nearest paisa             | `gstIsRoundedToTheNearestPaisa`                                     |
| 50 kg; 50.001 kg; a PIN code not served                         | `200`; `422`; `422`                      | `whatTheNetworkCannotCarryIs422`                                    |
| Bad PIN codes, zero weight, 151 cm, unknown service, a fraction | `400`                                    | `badRequestsAre400`                                                 |
| The old PDF's example                                           | `400`                                    | `thePdfsExampleIsRefusedByTheRealApi`                               |
| Every example in the docs                                       | Gets its documented status               | `everyRequestExampleGetsTheStatusTheDocsGiveIt`                     |
| Every documented answer                                         | Matches the real one                     | `everyDocumentedAnswerMatchesTheRealOne`                            |
| Each field removed in turn                                      | `400` exactly when the docs say required | `theFieldsTheDocsCallRequiredAreExactlyTheOnesTheApiRefusesWithout` |
| Any change to the description                                   | Fails until the approved copy is updated | `theDescriptionMatchesTheApprovedCopy`                              |

## The trap

Plausible but wrong

Hand-written docs that drift from the real API.

- **The PDF.** The test sends the PDF's own example to the API: `400`. Nothing ever checked the PDF, so nothing noticed.
- **Generated docs.** The description's request schema has exactly the fields the API takes, with the PIN code pattern and the size limits from the validation annotations.
- **Generated is not enough.** The generated docs were wrong twice while building (see Tests). Only the tests that send the examples and compare the answers caught it.

While building, each part was undone once: an int field not marked required in the docs turned 2 tests red; a wrong total in a documented example 2; a field renamed 7; the weight limit changed 3; another volumetric divisor 1; GST cut instead of rounded 1; no LOCAL zone 1; no rounding up to a started slab 3.

``` code
package com.dakroute.rates;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Written first. Partners integrated from a PDF written by hand two releases ago. Its example request, copied below,
 * uses field names and units the API stopped accepting: every partner who copied it got a 400 and opened a ticket.
 */
class HandWrittenDocsTrapTest extends ApiTest {

    /** Page 4 of "Dakroute Rate API v2.pdf". */
    static final String FROM_THE_PDF = """
            {"origin": "560001", "destination": "110001", "weight_kg": 1.2, "dimensions": "30x20x10", "type": "surface"}""";

    @Test
    void thePdfsExampleIsRefusedByTheRealApi() throws Exception {
        assertThat(quoteResponse(FROM_THE_PDF).getStatus()).isEqualTo(400);
    }

    @Test
    void theGeneratedDocsDescribeTheFieldsTheApiReallyTakes() throws Exception {
        var properties = spec().at("/components/schemas/QuoteRequest/properties");
        assertThat(properties.propertyNames()).containsExactly("fromPincode", "toPincode", "weightGrams", "lengthCm", "widthCm", "heightCm", "service");
        assertThat(properties.has("weight_kg")).isFalse();
        assertThat(properties.at("/fromPincode/pattern").asString()).isEqualTo("[1-9][0-9]{5}");
        assertThat(properties.at("/lengthCm/maximum").asInt()).isEqualTo(150);
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                         | Check with      |
|----------|-------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below  | `java -version` |
| Maven    | Not needed: the project ships the Maven wrapper |                 |

**macOS / Linux**

``` code
./mvnw spring-boot:run      # the API on http://localhost:8080, the docs at /v3/api-docs
./mvnw test                 # all 11 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Ask the docs which fields are required:

``` code
curl -s http://localhost:8080/v3/api-docs | python3 -c "import json,sys; print(json.load(sys.stdin)['components']['schemas']['QuoteRequest']['required'])"
```

It prints `['fromPincode', 'heightCm', 'lengthCm', 'service', 'toPincode', 'weightGrams', 'widthCm']` (read from the captured description). Then remove `requiredMode = Schema.RequiredMode.REQUIRED` from `weightGrams`, restart, ask again, and run `./mvnw test`: two tests fail and `target/openapi-generated.json` shows the change.

## Troubleshooting

| You see                                         | Cause                                             | Fix                                                                                                                       |
|-------------------------------------------------|---------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| `theDescriptionMatchesTheApprovedCopy` fails    | The API's description changed, on purpose or not. | Diff `target/openapi-generated.json` with `approved.json`; if the change is right, copy it over in the same pull request. |
| A primitive field shown as optional             | springdoc only marks `@NotNull` fields required.  | Add `requiredMode = REQUIRED` to its `@Schema`.                                                                           |
| A documented answer does not match the real one | The example was written by hand and is wrong.     | Copy the real answer into the example; the test will hold it.                                                             |

## Project layout

``` tree
stations/090-partner-shipping-rate-api-docs/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/dakroute/rates/
│   ├── RateQuoteController.java   ├── RateCard.java   └── RatesApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/dakroute/rates/   (see Tests)
├── src/test/resources/openapi/approved.json
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

The endpoint and its docs first, then the tariff and the approved description.

#### `src/main/java/com/dakroute/rates/RateQuoteController.java`

Does  
The endpoint, and most of its docs.

Why  
Validation annotations become the docs' patterns and limits; `@Schema` adds descriptions and examples; `@Operation`, `@ApiResponse` and named `@ExampleObject`s document 200, 400 and 422.

Without it  
Partners guessing field names, units and errors.

- The int fields carry `requiredMode = REQUIRED` by hand: springdoc marks only `@NotNull` fields required, but Jackson 3 refuses a missing `int`. Found by a test while building.
- Request and answer examples share a name, so a test can pair them and send one to check the other.
- The error examples have no `type` field: Spring does not send `about:blank`. The first version had it; a test caught it.

#### `src/main/java/com/dakroute/rates/RateCard.java`

Does  
The demo tariff.

Why  
Zones, volumetric weight, slabs, express, GST, days.

Without it  
Prices computed differently in different places.

#### `src/main/java/com/dakroute/rates/RatesApplication.java`

Does  
Entry point, and the parts of the docs not in the code.

Why  
Title, version, contact and the partner server address.

Without it  
Docs that point partners at `localhost`.

#### `src/test/resources/openapi/approved.json`

The approved description. A change to the API changes the generated one; the test fails and writes the new one to `target/openapi-generated.json`, to diff and approve in the pull request.

#### `src/main/resources/application.yaml`

Problem details for errors; fractions refused for whole-number fields.

#### `pom.xml`

`springdoc-openapi-starter-webmvc-api` 3.1.1, the line for Spring Boot 4 (built against 4.1.0). The `-ui` starter would add Swagger UI.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                              | Test class                    | Result |
|---------------|------------------------------------------|-------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found | `RateQuoteContractTest` (5)   | pass   |
| Every station | Reproduce the failure before the fix     | `HandWrittenDocsTrapTest` (2) | pass   |
| This station  | The docs tested against the API          | `OpenApiDocsTest` (4)         | pass   |

Two of these tests failed on the first generated docs, for real reasons: the required-fields test found `weightGrams` and the sizes marked optional, and the documented-answer test found a `type` field Spring does not send. Both were fixed in the code; the approved copy was then taken from the generated description. Found while building.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, springdoc-openapi 3.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.dakroute.rates.OpenApiDocsTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.dakroute.rates.HandWrittenDocsTrapTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.dakroute.rates.RateQuoteContractTest
[INFO] Tests run: 11, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/dakroute/rates/HandWrittenDocsTrapTest.java`

Written first: the PDF's example against the real API, and the generated schema's fields.

#### `src/test/java/com/dakroute/rates/OpenApiDocsTest.java`

Examples sent, answers compared, required fields checked, the approved copy compared.

#### `src/test/java/com/dakroute/rates/RateQuoteContractTest.java`

The tariff and the errors through HTTP.

#### `src/test/java/com/dakroute/rates/ApiTest.java`

Shared setup: request helpers and the generated description.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/dakroute/rates/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=NotServedExampleChallengeTest`.
3.  Change the code until it passes. Both challenges change the description, so `theDescriptionMatchesTheApprovedCopy` fails next: review `target/openapi-generated.json` and copy it over `approved.json`. Then run `./mvnw test` to check the other 11 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, including their approved description (`challenge/solution/test-resources/`), all 14 tests pass (11 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Document the second 422

Add a request example named `not-served` (a parcel to 744101) and a `422` answer example with the same name. `OpenApiDocsTest` then sends it and checks the answer.

**Done when:** the test in `NotServedExampleChallengeTest` passes, and so does `OpenApiDocsTest` after you approve the new description.

Hints

- `examples` takes a list: `examples = {@ExampleObject(...), @ExampleObject(...)}`.
- Copy the real answer from a `curl`, not from memory.

#### `challenge/NotServedExampleChallengeTest.java`

``` code
package com.dakroute.rates;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 1: document the second 422. Add a request example named "not-served" (a parcel to PIN 744101) and a 422
 * example with the same name. OpenApiDocsTest then sends it and compares the answer; approve the new description.
 */
class NotServedExampleChallengeTest extends ApiTest {

    @Test
    void theNotServedAnswerIsDocumentedWithAnExample() throws Exception {
        JsonNode op = spec().at("/paths/~1rate-quotes/post");
        assertThat(op.at("/requestBody/content/application~1json/examples/not-served/value/toPincode").asString()).isEqualTo("744101");
        assertThat(op.at("/responses/422/content/application~1problem+json/examples/not-served/value/detail").asString()).isEqualTo("This PIN code is not served yet");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Name the wrong field

Partners still sending the old PDF's body get told which field is wrong: an unknown field by name (`Unknown field 'cod'`), a missing or mistyped one too, with where the docs are. Document it with a request example `from-the-old-pdf` and its `400`.

**Done when:** both tests in `UnknownFieldChallengeTest` pass.

Hints

- Refuse unknown fields: `spring.jackson.deserialization.fail-on-unknown-properties=true`, then name the field from the exception's path in an `@ExceptionHandler`.
- For a record, Jackson 3 reports a missing number before an unknown field: the PDF's body is answered about `weightGrams`. Found while writing the solution.

#### `challenge/UnknownFieldChallengeTest.java`

``` code
package com.dakroute.rates;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: partners still sending the old PDF's fields get told which field is wrong: unknown fields are refused
 * (400) by name, and a missing or mistyped field is named too, with where the docs are. The docs show the old PDF's
 * body as a request example "from-the-old-pdf". Jackson 3 reports a record's missing number before an unknown field.
 */
class UnknownFieldChallengeTest extends ApiTest {

    @Test
    void theWrongFieldIsNamed() throws Exception {
        quote(HandWrittenDocsTrapTest.FROM_THE_PDF).andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail").value("Field 'weightGrams' is missing or has the wrong type. The fields are described at /v3/api-docs"));
        quote("{\"fromPincode\":\"560001\",\"toPincode\":\"110001\",\"weightGrams\":500,\"lengthCm\":10,\"widthCm\":10,\"heightCm\":10,\"service\":\"STANDARD\",\"cod\":true}")
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.detail").value("Unknown field 'cod'. The fields are described at /v3/api-docs"));
    }

    @Test
    void theDocsShowIt() throws Exception {
        JsonNode op = spec().at("/paths/~1rate-quotes/post");
        assertThat(op.at("/requestBody/content/application~1json/examples/from-the-old-pdf/value/origin").asString()).isEqualTo("560001");
        assertThat(op.at("/responses/400/content/application~1problem+json/examples/from-the-old-pdf/value/detail").asString()).startsWith("Field 'weightGrams' is missing");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Publishing to partners

Partners need the docs where they work: a docs site, a downloadable file, maybe generated client libraries. Design how the approved description is published on each release, how partners learn what changed (a changelog made from the diff), and how a breaking change is announced long enough before it ships (station 088).

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the PDF's example against the API.
2.  Write the endpoint with validation annotations; add springdoc; add descriptions, errors and named examples.
3.  Write the tests that send the examples, compare answers and check required fields.
4.  Approve the description and test against the approved copy.

## Design alternatives and trade-offs

| Approach                                                    | What it costs                                                                  | Verdict             |
|-------------------------------------------------------------|--------------------------------------------------------------------------------|---------------------|
| Code first: generated from annotations, tested              | Annotations next to the code; the tests to keep them true.                     | Chosen              |
| Hand-written docs (PDF, wiki)                               | Drift, and nothing notices.                                                    | The trap            |
| Design first: write the OpenAPI file, generate code from it | The contract is agreed before code; generators and their output to maintain.   | Good for many teams |
| Generated, untested                                         | Better than a PDF; still wrong where the library guesses (required ints here). | Not enough          |

## Database design

This station has no database: a quote is computed, not stored. The same approach documents any table-backed API.

# 3 · Go deeper: Production

Exposure  
Decide whether `/v3/api-docs` is public. Internal endpoints should not appear in partner docs; springdoc can group or hide them.

Review  
The approved copy turns every API change into a diff in the pull request: the moment to ask "is this breaking?".

Tooling  
OpenAPI feeds linters, mock servers, client generators and API gateways; a true description pays off many times.

Support  
Name the wrong field in errors (challenge 2): it turns tickets into self-service.

# 3 · Go deeper: Interview

## Interview takeaways

Code first or design first?

Code first generates the description from the code, so it follows the code; design first agrees the contract before coding. Either way, test the description against the running API.

Where do field limits in the docs come from?

springdoc reads the Bean Validation annotations (pattern, min, max, not null) and @Schema; anything it cannot know, such as Jackson refusing a missing int, must be added.

How do you stop docs from drifting?

Generate them, send every example in a test, compare documented answers with real ones, and review the description's diff on every change.

Why document errors?

Partners spend most of their integration time on errors. Each error needs its status, when it happens and an example.

What is contract review?

Looking at the change to the API description in the pull request, before it ships, to catch breaking or accidental changes.

## Self-check rubric

| Area        | Meets the bar           | Above the bar                                          |
|-------------|-------------------------|--------------------------------------------------------|
| Correctness | All 11 tests pass.      | You ran the flawed version and explained each failure. |
| Docs        | Generated docs.         | Errors and examples documented, and true.              |
| Tests       | The endpoint is tested. | The docs are tested against it, both ways.             |
| Review      | Changes are reviewed.   | As a diff of the description, in the pull request.     |

# 3 · Go deeper: Review

## The pull request

A teammate tidies the controller: the documentation annotations go, since springdoc generates the docs from the code anyway, and an over-weight parcel becomes a `400` like other invalid input. Read the file and list every problem before opening the findings.

#### `review/RateQuoteController.java`

``` code
package com.dakroute.rates;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.concurrent.atomic.AtomicLong;

/**
 * The partner docs are generated from this code: the paths, the fields with their limits (from the validation
 * annotations), the errors and the examples. Every example here is sent to the API by a test, so it cannot drift.
 */
@RestController
class RateQuoteController {

        @Schema(description = "A parcel to price.")
    record QuoteRequest(
            @Schema(description = "Pickup PIN code: six digits, not starting with 0.", example = "560001")
            @NotNull @Pattern(regexp = "[1-9][0-9]{5}") String fromPincode,
            @Schema(description = "Delivery PIN code.", example = "110001")
            @NotNull @Pattern(regexp = "[1-9][0-9]{5}") String toPincode,
            @Schema(description = "Actual weight in grams. Above 50,000 g the parcel service cannot carry it (422).", example = "1200")
            @Min(1) int weightGrams,
            @Schema(description = "Length in cm.", example = "30") @Min(1) @Max(150) int lengthCm,
            @Schema(description = "Width in cm.", example = "20") @Min(1) @Max(150) int widthCm,
            @Schema(description = "Height in cm.", example = "10") @Min(1) @Max(150) int heightCm,
            @Schema(description = "STANDARD or EXPRESS.", example = "STANDARD") @NotNull RateCard.Service service) {
    }

    @Schema(description = "A price for one parcel. Amounts are integer paise (₹1 = 100 paise).")
    record Quote(@Schema(example = "Q-1") String quoteId, RateCard.Zone zone,
                 @Schema(description = "The larger of actual and volumetric weight.") long chargeableWeightGrams,
                 long pricePaise, @Schema(description = "GST at 18%.") long gstPaise, long totalPaise,
                 @Schema(description = "Working days, a demo estimate.") int estimatedDays) {
    }

    static final String PARCEL = """
            {"fromPincode": "560001", "toPincode": "110001", "weightGrams": 1200, "lengthCm": 30, "widthCm": 20, "heightCm": 10, "service": "STANDARD"}""";
    static final String PARCEL_QUOTE = """
            {"quoteId": "Q-1", "zone": "NATIONAL", "chargeableWeightGrams": 1200, "pricePaise": 22500, "gstPaise": 4050, "totalPaise": 26550, "estimatedDays": 5}""";
    static final String LIGHT_BUT_BULKY = """
            {"fromPincode": "560001", "toPincode": "560034", "weightGrams": 800, "lengthCm": 60, "widthCm": 40, "heightCm": 40, "service": "EXPRESS"}""";
    static final String TOO_HEAVY = """
            {"fromPincode": "560001", "toPincode": "110001", "weightGrams": 62000, "lengthCm": 80, "widthCm": 60, "heightCm": 60, "service": "STANDARD"}""";
    static final String BAD_PINCODE = """
            {"fromPincode": "56001", "toPincode": "110001", "weightGrams": 1200, "lengthCm": 30, "widthCm": 20, "heightCm": 10, "service": "STANDARD"}""";

    private final AtomicLong quotes = new AtomicLong();

    // springdoc generates the docs from the method anyway: no need for all those annotations.
    @PostMapping("/rate-quotes")
    Quote quote(@Valid @RequestBody QuoteRequest r) {
        if (r.weightGrams() > RateCard.MAX_WEIGHT_GRAMS) {
            // A weight we cannot carry is a bad request like any other invalid input.
            throw new ErrorResponseException(HttpStatus.BAD_REQUEST, ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, "Parcels above " + RateCard.MAX_WEIGHT_GRAMS + " g cannot be carried"), null);
        }
        if (RateCard.NOT_SERVED.contains(r.fromPincode()) || RateCard.NOT_SERVED.contains(r.toPincode())) {
            throw unprocessable("This PIN code is not served yet");
        }
        RateCard.Zone zone = RateCard.zone(r.fromPincode(), r.toPincode());
        long chargeable = Math.max(r.weightGrams(), RateCard.volumetricGrams(r.lengthCm(), r.widthCm(), r.heightCm()));
        long price = RateCard.pricePaise(zone, r.service(), chargeable);
        long gst = RateCard.gstPaise(price);
        return new Quote("Q-" + quotes.incrementAndGet(), zone, chargeable, price, gst, price + gst, RateCard.days(zone, r.service()));
    }

    private static ErrorResponseException unprocessable(String detail) {
        return new ErrorResponseException(HttpStatus.UNPROCESSABLE_CONTENT, ProblemDetail.forStatusAndDetail(HttpStatus.UNPROCESSABLE_CONTENT, detail), null);
    }
}
```

## Findings

1The documentation annotations removed

"springdoc generates the docs anyway": it generates the paths and the schema, but not the errors, the examples, or that the int fields are required. Partners are back to guessing, and the tests that send the examples have nothing to send.

**Test evidence:** `everyRequestExampleGetsTheStatusTheDocsGiveIt`, `theFieldsTheDocsCallRequiredAreExactlyTheOnesTheApiRefusesWithout` and `theDescriptionMatchesTheApprovedCopy` fail.

2Too heavy answered 400

"A weight we cannot carry is a bad request": but the request is valid; the network cannot carry it. Partners handle 400 by fixing their code and 422 by telling their customer; the change sends them the wrong way.

**Test evidence:** `whatTheNetworkCannotCarryIs422` fails.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class                | Fixed version | Flawed version |
|---------------------------|---------------|----------------|
| `HandWrittenDocsTrapTest` | 2 / 2         | 2 / 2          |
| `OpenApiDocsTest`         | 4 / 4         | 1 / 4          |
| `RateQuoteContractTest`   | 5 / 5         | 4 / 5          |

The API still answers every quote correctly. What breaks is what partners can learn from the docs, which only tests on the docs themselves can see.
