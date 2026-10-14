# Station 023 · Accepting a partner's snake_case JSON

Foundations · 0–1 years · Core · Logistics · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · Jackson 3 (tools.jackson) · java.time · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The courier partner is simulated: its updates are the JSON bodies in the examples. Events are records in memory; no parcel moves.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 10 tests.

# 1 · Understand

## The problem in real life

1.  **The partner adds a field**

    One Monday, every delivery update gains `rider_phone`. Dakroute's webhook answers 400 to all of them; tracking pages stop moving.

2.  **A quick fix makes it worse**

    Someone switches the parser to lenient and renames nothing. Now updates are accepted, and every field reads as empty, because `awb_number` never matched `awbNumber`.

3.  **The fix**

    Map the partner's snake_case names on their class only, ignore fields we do not use (on that class only), and say in code which time zone their times are in.

Be strict with what you control; be tolerant, explicitly and locally, with what a partner sends.

## What are we building?

`POST /partner/delivery-updates` accepts the courier partner's JSON exactly as they send it and records a tracking event in our own shape: camelCase names, our status names, and times as exact UTC instants.

## An everyday analogy

A post office accepts parcels from another country. It reads the address in their format and ignores the customs stickers it does not need, but it still refuses a parcel with no address.

## How it works in 4 steps

1.  **Read their names**: `awb_number` fills `awbNumber`, for this class only.
2.  **Ignore their extras**: new fields are skipped, for this class only; ours stay strict.
3.  **Pin the time**: their "09:15" is India time by contract, so it becomes 03:45 UTC.
4.  **Translate and record**: their status code becomes ours; an unknown one is kept as UNKNOWN.

Check yourself: why not make the whole API ignore unknown fields?

Then a typo by our own app (`"amout"`) is silently ignored too, and a bug becomes missing data. Tolerance belongs where we cannot control the sender.

## What this station is not

- **No real partner.** The updates are sample JSON.
- **No webhook security.** Signature checks come in a later station.
- **No tracking page.** Events are only recorded.

## Key terms

| Term                       | Simple meaning                                                  | Everyday example                                                  | In this project                               |
|----------------------------|-----------------------------------------------------------------|-------------------------------------------------------------------|-----------------------------------------------|
| **snake_case / camelCase** | Two ways to join words in a name: `awb_number` and `awbNumber`. | Two offices that write dates differently.                         | `@JsonNaming`                                 |
| **Tolerant reader**        | Read the fields you need; ignore the rest.                      | Reading a letter for the address and ignoring the decorations.    | `@JsonIgnoreProperties(ignoreUnknown = true)` |
| **Strict reader**          | Refuse anything unexpected.                                     | A form that is rejected if anything is written outside the boxes. | `fail-on-unknown-properties: true`            |
| **AWB**                    | Air waybill number: the tracking number of a parcel.            | DKR100000001IN on the label.                                      | `awb_number`                                  |
| **Local time**             | A clock time with no time zone.                                 | "09:15" on a message from a friend abroad.                        | `event_time`                                  |
| **Instant**                | One exact point in time, shown in UTC.                          | The moment a rocket launches, whatever the clocks say.            | `at` in our response                          |

# 2 · Build: Spec

## Business problem

**Dakroute** (a fictional logistics platform) receives delivery updates from a courier partner. The partner's JSON is snake_case, its times have no zone, and it adds fields without notice. Dakroute's platform is strict about unknown fields for its own clients, so each new partner field took the webhook down until someone noticed.

## Acceptance criteria

1.  **Given** an update with fields we have never seen, **then** `202`, and the fields we know are read.
2.  **Given** `"event_time": "2026-10-14 09:15:00"`, **then** the event is at `2026-10-14T03:45:00Z`; 02:00 on 15 October is 20:30 UTC on the 14th.
3.  **Given** `"promised_by": "2026-10-14T18:00:00+05:30"`, **then** `2026-10-14T12:30:00Z`.
4.  **Given** a status code we do not know, **then** accepted as UNKNOWN with the raw code kept.
5.  **Given** an AWB we never booked, **then** `404`.
6.  **Given** a missing AWB, a time in another format, a bad PIN code, or our own camelCase names, **then** `400`.

## Requirements

- Snake_case naming and ignoring unknown fields apply to the partner's classes only.
- Event times are India time by the partner contract; every time we return is a UTC instant.
- AWBs are normalised to upper case with `Locale.ROOT`.
- Our responses use our names (camelCase), never the partner's.

## Learning objectives

- Use Jackson naming strategies and `@JsonProperty`-style mapping per class.
- Decide where to ignore unknown fields, and keep the rest strict.
- Handle a time with no zone, and an ISO time with an offset.
- Know where Jackson 3 lives (`tools.jackson`) and its defaults.

# 2 · Build: API contract

## Endpoint

| Method | Path                        | Purpose                                                                |
|--------|-----------------------------|------------------------------------------------------------------------|
| `POST` | `/partner/delivery-updates` | Record a partner's delivery update. `202` with the event in our shape. |

## Request body (the partner's shape)

| Field         | Rule                                                                 |
|---------------|----------------------------------------------------------------------|
| `awb_number`  | Required; 10 to 20 letters and digits; must be a shipment we booked. |
| `status_code` | Required. PKD, ITR, OFD, DLV, RTO are mapped; others become UNKNOWN. |
| `event_time`  | Required; `yyyy-MM-dd HH:mm:ss`, India time by contract.             |
| `location`    | Optional: `city_name`, `pin_code` (6 digits).                        |
| `promised_by` | Optional; ISO 8601 with an offset.                                   |
| Anything else | Ignored.                                                             |

## Status codes

| Status | When                                                                   |
|--------|------------------------------------------------------------------------|
| 202    | Recorded                                                               |
| 400    | A required field missing or malformed, including the wrong time format |
| 404    | An AWB we never booked                                                 |

## Captured examples

Captured with curl from the running app on 14 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: an update with three fields we do not know

**Why:** `hub_id`, `rider_phone` and `temperature_c` are ignored. 09:15 India time is 03:45 UTC; 18:00+05:30 is 12:30 UTC.

Request

``` code
POST /partner/delivery-updates HTTP/1.1
Content-Type: application/json

{
  "awb_number": "DKR100000001IN",
  "status_code": "OFD",
  "event_time": "2026-10-14 09:15:00",
  "location": {
    "city_name": "Pune",
    "pin_code": "411001",
    "hub_id": "PNQ-07"
  },
  "promised_by": "2026-10-14T18:00:00+05:30",
  "rider_phone": "98XXXXXX21",
  "temperature_c": 31.5
}
```

Response

``` code
HTTP/1.1 202 
Content-Type: application/json
Content-Length: 207

{
  "accepted": true,
  "event": {
    "awbNumber": "DKR100000001IN",
    "status": "OUT_FOR_DELIVERY",
    "partnerStatusCode": "OFD",
    "at": "2026-10-14T03:45:00Z",
    "city": "Pune",
    "pinCode": "411001",
    "promisedBy": "2026-10-14T12:30:00Z"
  }
}
```

### Case 2: delivered at 02:00 India time

**Why:** 02:00 on 15 October in India is 20:30 on 14 October in UTC: the date changes too. The lower-case AWB is normalised.

Request

``` code
POST /partner/delivery-updates HTTP/1.1
Content-Type: application/json

{
  "awb_number": "dkr100000002in",
  "status_code": "DLV",
  "event_time": "2026-10-15 02:00:00"
}
```

Response

``` code
HTTP/1.1 202 
Content-Type: application/json
Content-Length: 176

{
  "accepted": true,
  "event": {
    "awbNumber": "DKR100000002IN",
    "status": "DELIVERED",
    "partnerStatusCode": "DLV",
    "at": "2026-10-14T20:30:00Z",
    "city": null,
    "pinCode": null,
    "promisedBy": null
  }
}
```

### Case 3: a status code we do not know

**Why:** HLD is kept as UNKNOWN with the raw code, and a warning is logged so someone maps it.

Request

``` code
POST /partner/delivery-updates HTTP/1.1
Content-Type: application/json

{
  "awb_number": "DKR100000001IN",
  "status_code": "HLD",
  "event_time": "2026-10-14 10:00:00"
}
```

Response

``` code
HTTP/1.1 202 
Content-Type: application/json
Content-Length: 174

{
  "accepted": true,
  "event": {
    "awbNumber": "DKR100000001IN",
    "status": "UNKNOWN",
    "partnerStatusCode": "HLD",
    "at": "2026-10-14T04:30:00Z",
    "city": null,
    "pinCode": null,
    "promisedBy": null
  }
}
```

### Case 4: an AWB we never booked

**Why:** `404`: there is no shipment to attach it to.

Request

``` code
POST /partner/delivery-updates HTTP/1.1
Content-Type: application/json

{
  "awb_number": "DKR999999999IN",
  "status_code": "OFD",
  "event_time": "2026-10-14 09:15:00"
}
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No shipment with this AWB was booked with us.",
  "instance": "/partner/delivery-updates",
  "status": 404,
  "title": "Unknown AWB"
}
```

### Case 5: a date in another format

**Why:** `14/10/2026 09:15` is not the agreed format: `400`, rather than a guess.

Request

``` code
POST /partner/delivery-updates HTTP/1.1
Content-Type: application/json

{
  "awb_number": "DKR100000001IN",
  "status_code": "OFD",
  "event_time": "14/10/2026 09:15"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Failed to read request",
  "instance": "/partner/delivery-updates",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 6: our own camelCase names

**Why:** this endpoint speaks the partner's names; `awb_number` is missing: `400`.

Request

``` code
POST /partner/delivery-updates HTTP/1.1
Content-Type: application/json

{
  "awbNumber": "DKR100000001IN",
  "statusCode": "OFD",
  "eventTime": "2026-10-14 09:15:00"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/partner/delivery-updates",
  "status": 400,
  "title": "Bad Request"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                              | What happens                 | Proved by                                  |
|-----------------------------------------------------------------------------------|------------------------------|--------------------------------------------|
| Snake_case in, camelCase out, times in UTC                                        | 202; converted               | `snakeCaseInCamelCaseOutAndEveryTimeInUtc` |
| 02:00 India time                                                                  | 20:30 UTC the day before     | `anIndianLateNightTimeIsTheDayBeforeInUtc` |
| Status HLD                                                                        | UNKNOWN, raw code kept       | `aStatusCodeWeDoNotKnowYetIsKeptAsUnknown` |
| AWB never booked                                                                  | `404`                        | `anAwbWeNeverBookedIs404`                  |
| No AWB; other date formats; short AWB; empty status; 4-digit PIN; camelCase names | `400`                        | `missingOrMalformedFieldsAre400`           |
| An unknown field on our own type                                                  | Rejected by the app's mapper | `ourOwnTypesStillRejectUnknownFields`      |
| Unknown fields on the partner type, nested too                                    | Ignored                      | `onlyThePartnerTypesOptOut`                |

## The trap

Plausible but wrong

Failing on unknown fields, so every new partner field breaks parsing.

Jackson 2 failed on unknown fields by default; Jackson 3's plain `JsonMapper` does not, but platforms often switch it on to catch their own clients' typos (this one does). The first test shows a strict mapper throwing on `rider_phone`. The second shows the other wrong fix: a lenient mapper with camelCase names reads every field as `null`, silently. The third shows the endpoint accepting the payload. While building, removing `ignoreUnknown` turned 3 tests red, removing snake_case naming turned many red, and reading the partner's times as UTC turned 2 red.

``` code
package com.dakroute.partner;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.databind.PropertyNamingStrategies;
import tools.jackson.databind.annotation.JsonNaming;
import tools.jackson.databind.exc.UnrecognizedPropertyException;
import tools.jackson.databind.json.JsonMapper;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: it reproduces the two ways the old code broke on partner JSON. */
class NewPartnerFieldTrapTest extends ApiTest {

    /** The "before" DTO: snake_case mapped, but strict like the rest of the platform. Kept only in tests. */
    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    record OldStrictUpdate(String awbNumber, String statusCode, String eventTime, Object location, String promisedBy) {
    }

    /** The other "before" DTO: camelCase names, lenient. Kept only in tests. */
    record OldCamelUpdate(String awbNumber, String statusCode, String eventTime) {
    }

    static final JsonMapper STRICT = JsonMapper.builder().enable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES).build();
    static final JsonMapper LENIENT = JsonMapper.builder().build();   // Jackson 3's own default: unknown fields ignored

    @Test
    void aStrictMapperRejectsThePayloadTheDayThePartnerAddsAField() {
        assertThatThrownBy(() -> STRICT.readValue(PARTNER_PAYLOAD, OldStrictUpdate.class))
                .isInstanceOf(UnrecognizedPropertyException.class)
                .hasMessageContaining("rider_phone");
    }

    @Test
    void camelCaseNamesReadNothingAndSayNothing() {
        OldCamelUpdate u = LENIENT.readValue(PARTNER_PAYLOAD, OldCamelUpdate.class);
        assertThat(u.awbNumber()).isNull();     // "awb_number" never matched "awbNumber"
        assertThat(u.statusCode()).isNull();
        assertThat(u.eventTime()).isNull();
    }

    @Test
    void theRealEndpointAcceptsThePayloadWithItsNewFields() throws Exception {
        update(PARTNER_PAYLOAD)
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.event.awbNumber").value("DKR100000001IN"))
                .andExpect(jsonPath("$.event.status").value("OUT_FOR_DELIVERY"));
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                         | Check with      |
|----------|-------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below  | `java -version` |
| Maven    | Not needed: the project ships the Maven wrapper |                 |
| Docker   | Not needed for this station                     |                 |

**macOS / Linux**

``` code
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 10 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

The partner's update is in `docs/partner-update.json`. Add any field you like and send it again.

``` code
curl -i -X POST http://localhost:8080/partner/delivery-updates -H "Content-Type: application/json" -d "@docs/partner-update.json"
```

## Troubleshooting

| You see                        | Cause                                               | Fix                                                          |
|--------------------------------|-----------------------------------------------------|--------------------------------------------------------------|
| `400` with our field names     | This endpoint reads the partner's snake_case names. | Send `awb_number`, not `awbNumber`.                          |
| `404`                          | Only DKR100000001IN and DKR100000002IN are booked.  | Use one of them.                                             |
| Times an hour or 5.5 hours off | A time read without its zone.                       | Check which zone the source means, and convert in one place. |

## Project layout

``` tree
stations/023-accepting-a-partners-snake-case-json/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/dakroute/partner/
│   ├── DeliveryUpdateController.java   ├── PartnerUpdate.java
│   ├── TrackingEvent.java              └── PartnerApplication.java
├── src/test/java/com/dakroute/partner/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     sample update, capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/dakroute/partner/DeliveryUpdateController.java`

Does  
Finds the shipment, maps the status, pins the time zone and records the event.

Why  
The partner's zone is a named constant with a comment: the JSON cannot carry it, so the code must.

Without it  
Treating a zone-less time as the server's zone.

#### `src/main/java/com/dakroute/partner/PartnerUpdate.java`

Does  
The partner's shape: snake_case, tolerant, with its time format.

Why  
Naming and tolerance are annotations on this class only, so the rest of the API stays strict.

Without it  
The trap: strict parsing of a payload we do not control.

- `@JsonNaming` from `tools.jackson.databind.annotation` (Jackson 3); `@JsonIgnoreProperties` and `@JsonFormat` stay in `com.fasterxml.jackson.annotation`.
- The nested `Location` needs its own annotations.

#### `src/main/java/com/dakroute/partner/TrackingEvent.java`

Does  
Our shape, and our statuses with the partner's code for each: an enum with data.

Why  
An unknown code becomes UNKNOWN, kept with the raw code, not a rejected update.

Without it  
Rejecting the partner's whole update over a status we can map later.

#### `src/main/resources/application.yaml`

The platform's strict rule: unknown fields are an error, except where a class opts out.

#### `src/main/java/com/dakroute/partner/PartnerApplication.java`

Standard Spring Boot entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                 | Test class                       | Result |
|---------------|-------------------------------------------------------------|----------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                    | `DeliveryUpdateContractTest` (5) | pass   |
| Every station | Reproduce the failure before the fix                        | `NewPartnerFieldTrapTest` (3)    | pass   |
| This station  | The app's own mapper: strict, except where a class opts out | `JsonRulesTest` (2)              | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.dakroute.partner.DeliveryUpdateContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.dakroute.partner.JsonRulesTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.dakroute.partner.NewPartnerFieldTrapTest
[INFO] Tests run: 10, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/dakroute/partner/NewPartnerFieldTrapTest.java`

Written first: a strict mapper throws, a camelCase DTO reads nulls, the endpoint accepts.

#### `src/test/java/com/dakroute/partner/DeliveryUpdateContractTest.java`

Names, times and statuses translated, and every refusal.

#### `src/test/java/com/dakroute/partner/JsonRulesTest.java`

Spring's configured `JsonMapper`: our types strict, partner types tolerant.

#### `src/test/java/com/dakroute/partner/ApiTest.java`

Shared setup and the partner's real payload.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/dakroute/partner/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=DuplicateUpdateChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 10 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 13 tests pass (10 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## A retry is not a new event

The partner retries when we answer slowly. The same AWB, status and event time is one event: accept the copy, mark it `duplicate`, and do not store it again. Return `eventsForShipment`.

**Done when:** the test in `DuplicateUpdateChallengeTest` passes.

Hints

- A record's `equals` compares every field, so two identical events are equal.
- `CopyOnWriteArrayList.addIfAbsent` checks and adds in one atomic step.

#### `challenge/DuplicateUpdateChallengeTest.java`

``` code
package com.dakroute.partner;

import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: the partner retries when our answer is slow, so the same update can arrive twice. The same AWB, status
 * and event time is one event: the second copy is accepted, marked duplicate, and not stored again.
 */
class DuplicateUpdateChallengeTest extends ApiTest {

    static final String UPDATE = "{\"awb_number\":\"DKR100000002IN\",\"status_code\":\"PKD\",\"event_time\":\"2026-10-13 18:20:00\"}";

    @Test
    void theSameUpdateTwiceIsOneEvent() throws Exception {
        // other tests may have added events to this shipment already: count from the first answer
        int before = JsonPath.read(update(UPDATE).andExpect(status().isAccepted()).andExpect(jsonPath("$.duplicate").value(false))
                .andReturn().getResponse().getContentAsString(), "$.eventsForShipment");
        update(UPDATE).andExpect(status().isAccepted()).andExpect(jsonPath("$.duplicate").value(true))
                .andExpect(jsonPath("$.eventsForShipment").value(before));
        update(UPDATE.replace("18:20:00", "18:21:00")).andExpect(jsonPath("$.duplicate").value(false))
                .andExpect(jsonPath("$.eventsForShipment").value(before + 1));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Two time formats

The partner's v2 sends `event_time` as ISO 8601 with an offset. Accept both formats with a Jackson 3 `ValueDeserializer`; ISO without an offset is still refused.

**Done when:** both tests in `TimeFormatsChallengeTest` pass, and the station's tests still pass.

Hints

- Extend `tools.jackson.databind.ValueDeserializer<Instant>`; attach it with `@JsonDeserialize(using = ...)`.
- Try the v1 pattern with the India zone first, then `OffsetDateTime.parse`.
- `ctxt.handleWeirdStringValue` turns a bad value into a normal `400`.

#### `challenge/TimeFormatsChallengeTest.java`

``` code
package com.dakroute.partner;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: the partner's v2 sends event_time as ISO 8601 with an offset ("2026-10-14T09:15:00+05:30"). Accept both
 * that and the old "2026-10-14 09:15:00" (India time), with a custom Jackson deserializer. ISO without an offset is
 * still refused: it does not say which zone.
 */
class TimeFormatsChallengeTest extends ApiTest {

    static String at(String eventTime) {
        return "{\"awb_number\":\"DKR100000001IN\",\"status_code\":\"ITR\",\"event_time\":\"" + eventTime + "\"}";
    }

    @Test
    void bothFormatsGiveTheSameInstant() throws Exception {
        update(at("2026-10-14 09:15:00")).andExpect(jsonPath("$.event.at").value("2026-10-14T03:45:00Z"));
        update(at("2026-10-14T09:15:00+05:30")).andExpect(jsonPath("$.event.at").value("2026-10-14T03:45:00Z"));
        update(at("2026-10-14T03:45:00Z")).andExpect(jsonPath("$.event.at").value("2026-10-14T03:45:00Z"));
    }

    @Test
    void aTimeWithoutAZoneInIsoFormIsStillRefused() throws Exception {
        update(at("2026-10-14T09:15:00")).andExpect(status().isBadRequest());
        update(at("yesterday")).andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## A contract with a partner

Write the one-page contract you would agree with the partner: field names, which are required, the time zone, how they add fields, and how they remove or rename one. What do you do when they send something the contract does not allow: reject, accept and alert, or accept silently?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test with the partner's real payload: strict throws, camelCase reads nulls.
2.  Give the partner's payload its own class, with snake_case naming and tolerance on that class only.
3.  Read the zone-less time with its agreed format and convert it with the agreed zone, in one place.
4.  Translate their statuses into ours; keep the unknown ones visible.

## Design alternatives and trade-offs

| Approach                                          | What it costs                                         | Verdict    |
|---------------------------------------------------|-------------------------------------------------------|------------|
| A partner class with its own naming and tolerance | One class per partner payload.                        | Chosen     |
| Global snake_case naming                          | Our own API changes shape for everyone.               | Wrong here |
| Global tolerance                                  | Our own clients' typos are silently ignored.          | Hides bugs |
| Strict parsing of partner payloads                | Every new partner field is an outage.                 | The trap   |
| Reading the payload as a `Map`                    | No types, no validation; mistakes move into the code. | Avoid      |

## Database design

None in this station. With a database: `tracking_events` (awb, status, partner_status_code, at `timestamptz`) with a unique key on (awb, partner_status_code, at), so a partner retry cannot insert twice even under concurrency.

# 3 · Go deeper: Production

Visibility  
Ignored fields and unknown status codes are tolerated, not forgotten: log the unknown codes, and count them, so a partner change shows up on a dashboard before it shows up in complaints.

Time  
Store instants (`timestamptz`); convert to India time only for display. Write the partner's zone into the contract.

Security  
A webhook must check that the update really came from the partner (a shared signature), or anyone can move parcels on the tracking page.

Retries  
Partners retry on timeouts. Answer fast (202), and treat repeats as the same event (challenge 1).

# 3 · Go deeper: Interview

## Interview takeaways

How do you map snake_case JSON to Java?

A naming strategy: @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class) on the class, or @JsonProperty on single fields. Set it per class unless your whole API is snake_case.

Should you fail on unknown JSON fields?

For your own clients, failing catches typos. For partners you do not control, ignore unknown fields on their classes, so their additions do not break you.

What changed in Jackson 3?

Packages moved to tools.jackson (annotations stay in com.fasterxml.jackson.annotation), JsonMapper is the main type, dates are ISO strings by default, and a plain mapper no longer fails on unknown properties.

How do you handle a time with no zone?

Find out which zone it means, write that into the contract and the code, and convert to an instant once, at the edge.

Why keep unknown status codes instead of rejecting?

Rejecting loses the whole update over one field you can map later. Keep it as UNKNOWN with the raw code, and alert so it gets mapped.

## Self-check rubric

| Area        | Meets the bar                                   | Above the bar                                               |
|-------------|-------------------------------------------------|-------------------------------------------------------------|
| Correctness | All 10 tests pass.                              | You can predict case 2's UTC time before running it.        |
| Jackson     | Naming and tolerance per class.                 | You know Jackson 3's defaults and where they differ from 2. |
| Time        | Zone-less times converted with the agreed zone. | You can explain why 02:00 IST is the previous day in UTC.   |
| Explanation | Strict for ours, tolerant for theirs.           | What a partner contract must say.                           |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any partner integration:

- Does a new field from the partner break parsing?
- Is tolerance limited to the partner's classes?
- Which zone are the partner's times in, and where is that written down?
- What happens to a value we do not recognise: rejected, kept, or silently dropped?
