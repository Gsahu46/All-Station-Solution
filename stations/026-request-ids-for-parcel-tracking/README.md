# Station 026 · Request ids for parcel tracking

Foundations · 0–1 years · Core · Logistics · Types: Operations

Spring Boot 4.1.1 · Java 25 · Spring MVC · OncePerRequestFilter · SLF4J MDC · Micrometer · Actuator · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Shipments are demo records in memory; no parcel moves. The store outage is simulated by a switch that is off unless a drill turns it on.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 14 tests.

# 1 · Understand

## The problem in real life

1.  **A customer's tracking page fails**

    She sends support a screenshot. Support opens the logs: 40,000 lines a minute, from hundreds of customers, all mixed together.

2.  **The first fix makes it worse**

    Someone adds a request id to the logs, but never clears it. Server threads serve one request after another, so the next customer's lines carry the first customer's id. Support now finds the wrong person's logs.

3.  **The fix**

    One filter gives every request its own id, puts it on every log line, returns it in a header and in error bodies, and removes it when the request ends, whatever happened.

Whatever you put on a shared thread, take it off in a `finally`.

## What are we building?

`GET /shipments/{awb}` returns a parcel's tracking. Around it: a request id on every response and every log line, a metric of lookups by outcome, and a drill that proves support can find a failure from a screenshot.

## An everyday analogy

A hospital gives each patient a token at the door. Every desk writes the token on its notes, and the token is taken back when the patient leaves, so the next patient does not walk around with it.

## How it works in 4 steps

1.  **At the door**: take the caller's `X-Request-Id` if it is safe, or make one.
2.  **On the badge**: put it in the MDC; every log line of the request carries it.
3.  **On the way out**: return it in the header, and in any error body.
4.  **At the end, always**: remove it from the MDC, even when the request failed.

Check yourself: why must the id be removed if the next request sets its own anyway?

Not every request sets one: the old code only did when the caller sent an id. And work outside a request on that thread (a scheduled task, a log line after an error) would carry a stranger's id too.

## What this station is not

- **Not distributed tracing.** One service; tracing across services is discussed in Design.
- **No log storage.** Logs go to the console; searching them is the log platform's job.
- **No real tracking store.** Demo records, with a simulated outage for drills.

## Key terms

| Term            | Simple meaning                                                                          | Everyday example                                                 | In this project                                    |
|-----------------|-----------------------------------------------------------------------------------------|------------------------------------------------------------------|----------------------------------------------------|
| **Request id**  | A label for one request, the same in every log line it writes.                          | A token number at a hospital: every desk writes it on your file. | `X-Request-Id`                                     |
| **MDC**         | Mapped Diagnostic Context: values the logger adds to every line on this thread.         | A name badge the logger reads before writing anything.           | `MDC.put("requestId", id)`                         |
| **Filter**      | Code that runs around every request, before Spring decides which controller handles it. | Security at the building door, not at one office.                | `RequestIdFilter`                                  |
| **Interceptor** | Code that runs around a controller call, after Spring picked the controller.            | A check at one office door.                                      | Not used: it misses requests no controller handles |
| **Log level**   | How important a line is: DEBUG, INFO, WARN, ERROR.                                      | A note, a message, a warning, an alarm.                          | INFO per lookup, ERROR when the store fails        |
| **Metric**      | A number that changes over time, counted by the app.                                    | The counter at a toll booth.                                     | `tracking.lookups{outcome}`                        |

# 2 · Build: Spec

## Business problem

**Dakroute** (a fictional logistics platform) logs 40,000 lines a minute. When a customer's tracking request fails, support cannot find its lines. A first attempt at request ids filed some customers' lines under other customers' ids, which is worse than no id.

## Acceptance criteria

1.  **Given** a request with `X-Request-Id: app-7f3a9c21`, **then** the response carries the same header, and every log line of the request shows `[rid:app-7f3a9c21]`.
2.  **Given** no id, or an unsafe one (spaces, too short or long, control characters), **then** the server makes a UUID and returns it.
3.  **Given** two requests on one thread, **then** each logs only its own id, and nothing is left in the MDC afterwards, even after a failure.
4.  **Given** an unknown shipment or a bad AWB, **then** `404` or `400` with `requestId` in the body.
5.  **Given** a path no controller handles, **then** the `404` still carries `X-Request-Id`.
6.  **Given** the store is down, **then** `503` with `Retry-After: 60`, one ERROR line with the id, and the error metric goes up.

## Requirements

- Accepted ids: 8 to 64 letters, digits or `-`. Anything else is replaced and never logged.
- The filter runs first, for every request; the MDC entry is removed in `finally`.
- Log levels: DEBUG detail, INFO per lookup, ERROR when the store fails.
- `tracking.lookups` counts lookups by outcome: found, not_found, invalid, error.

## Learning objectives

- Write a `OncePerRequestFilter`, and explain filter versus `HandlerInterceptor`.
- Use the MDC safely on pooled threads.
- Choose log levels, and treat request headers as untrusted input to logs.
- Publish a metric and run a controlled failure drill.

# 2 · Build: API contract

## Endpoints

| Method | Path                                 | Purpose                                                |
|--------|--------------------------------------|--------------------------------------------------------|
| `GET`  | `/shipments/{awb}`                   | A parcel's status and events.                          |
| `GET`  | `/actuator/metrics/tracking.lookups` | The lookup counter, by `outcome` tag (for monitoring). |

## Headers

| Header                    | Rule                                                                 |
|---------------------------|----------------------------------------------------------------------|
| `X-Request-Id` (request)  | Optional. 8 to 64 letters, digits or `-`; anything else is replaced. |
| `X-Request-Id` (response) | Always present: the caller's id, or the one the server made.         |

## Status codes

| Status | When                                          |
|--------|-----------------------------------------------|
| 200    | The shipment                                  |
| 400    | Not an AWB (10 to 20 letters and digits)      |
| 404    | No such shipment, or no such path             |
| 503    | The tracking store is down; `Retry-After: 60` |

## Captured examples

Captured with curl from the running app on 14 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: the app sends its id

**Why:** the same id comes back in `X-Request-Id`; the app shows it on its error screens.

Request

``` code
GET /shipments/DKR100000001IN HTTP/1.1
X-Request-Id: app-7f3a9c21
```

Response

``` code
HTTP/1.1 200 
X-Request-Id: app-7f3a9c21
Content-Type: application/json
Content-Length: 229

{
  "awb": "DKR100000001IN",
  "status": "OUT_FOR_DELIVERY",
  "destinationCity": "Pune",
  "events": [
    {
      "at": "2026-10-13T12:50:00Z",
      "status": "PICKED_UP",
      "place": "Mumbai"
    },
    {
      "at": "2026-10-14T03:45:00Z",
      "status": "OUT_FOR_DELIVERY",
      "place": "Pune"
    }
  ]
}
```

### Case 2: no id

**Why:** the server makes a UUID and returns it.

Request

``` code
GET /shipments/DKR100000002IN HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
X-Request-Id: 3cbe0a7f-7c38-4128-a81f-5906c51b7d26
Content-Type: application/json
Content-Length: 219

{
  "awb": "DKR100000002IN",
  "status": "DELIVERED",
  "destinationCity": "Nagpur",
  "events": [
    {
      "at": "2026-10-12T09:10:00Z",
      "status": "PICKED_UP",
      "place": "Mumbai"
    },
    {
      "at": "2026-10-14T06:30:00Z",
      "status": "DELIVERED",
      "place": "Nagpur"
    }
  ]
}
```

### Case 3: an unknown shipment

**Why:** `404`, and the body names the request id, so a screenshot is enough for support.

Request

``` code
GET /shipments/DKR999999999IN HTTP/1.1
X-Request-Id: support-case-41
```

Response

``` code
HTTP/1.1 404 
X-Request-Id: support-case-41
Content-Type: application/problem+json

{
  "detail": "No shipment has this AWB.",
  "instance": "/shipments/DKR999999999IN",
  "status": 404,
  "title": "Shipment not found",
  "requestId": "support-case-41"
}
```

### Case 4: an id with spaces and fake log text

**Why:** replaced by a UUID; the caller's text never reaches a log line.

Request

``` code
GET /shipments/DKR100000001IN HTTP/1.1
X-Request-Id: x ERROR forged
```

Response

``` code
HTTP/1.1 200 
X-Request-Id: 20997a4f-64db-46fe-825e-7cfde5ea77a1
Content-Type: application/json
Content-Length: 229

{
  "awb": "DKR100000001IN",
  "status": "OUT_FOR_DELIVERY",
  "destinationCity": "Pune",
  "events": [
    {
      "at": "2026-10-13T12:50:00Z",
      "status": "PICKED_UP",
      "place": "Mumbai"
    },
    {
      "at": "2026-10-14T03:45:00Z",
      "status": "OUT_FOR_DELIVERY",
      "place": "Pune"
    }
  ]
}
```

### Case 5: a typo in the path

**Why:** no controller ran, but the filter did: the `404` carries the id.

Request

``` code
GET /shipment/DKR100000001IN HTTP/1.1
X-Request-Id: typo-path-0001
```

Response

``` code
HTTP/1.1 404 
X-Request-Id: typo-path-0001
Content-Type: application/problem+json

{
  "detail": "No static resource shipment/DKR100000001IN.",
  "instance": "/shipment/DKR100000001IN",
  "status": 404,
  "title": "Not Found"
}
```

### Case 6: the metric

**Why:** lookups counted by outcome; the alert in the Production tab reads this counter.

Request

``` code
GET /actuator/metrics/tracking.lookups?tag=outcome:found HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
X-Request-Id: 561a953e-31c0-4d9f-9a61-4f71e886c21e
Content-Disposition: inline;filename=f.txt
Content-Type: application/vnd.spring-boot.actuator.v3+json
Content-Length: 97

{
  "availableTags": [],
  "measurements": [
    {
      "statistic": "COUNT",
      "value": 3.0
    }
  ],
  "name": "tracking.lookups"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                  | What happens                          | Proved by                                           |
|-------------------------------------------------------|---------------------------------------|-----------------------------------------------------|
| Caller's id, lower-case AWB                           | 200, same id back                     | `aShipmentComesBackWithTheCallersRequestId`         |
| No id                                                 | A UUID                                | `withoutAnIdTheServerMakesOne`                      |
| Unknown shipment                                      | `404` with requestId                  | `anUnknownShipmentIs404AndTheBodyNamesTheRequestId` |
| Bad AWB                                               | `400` with requestId                  | `aBadAwbIs400WithItsRequestId`                      |
| A path no controller handles                          | `404` with the header                 | `evenAPathNoControllerHandlesGetsAnId`              |
| Short, spaced, 65 characters, a tab and fake log text | Replaced                              | `anUnsafeIdIsReplacedNotEchoed`                     |
| A lookup                                              | INFO line with `[rid:…]`              | `theLookupsLogLineCarriesTheRequestId`              |
| Forged log text in the header                         | Never in the log                      | `forgedLogTextInTheHeaderNeverReachesTheLog`        |
| Two requests on one thread; a failing handler         | Own ids; MDC empty after              | `LeakedRequestIdTrapTest`                           |
| Store outage; recovery; the metric endpoint           | 503 with trail; 200; counter readable | `OperationsDrillTest`                               |

## The trap

Plausible but wrong

Setting the MDC without clearing it, so the next request on the thread logs the wrong id.

The MDC is per thread, and a server reuses threads. The first test runs the old filter for two requests on one thread: the second, sent without an id, logs under the first one's. The second test runs the real filter the same way: each request has its own id, and nothing is left behind. The third makes the handler throw: the id is still removed. While building, removing the `MDC.remove` turned 2 tests red, accepting any incoming id turned 2 red, and dropping `requestId` from error bodies turned 3 red.

``` code
package com.dakroute.tracking;

import jakarta.servlet.FilterChain;
import jakarta.servlet.http.HttpServletRequest;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The first test written for this station: it reproduces the bug before the fix. Both requests run on one thread,
 * as they do in a server's thread pool, one after another.
 */
class LeakedRequestIdTrapTest {

    /** The "before" code: put the caller's id in the MDC when there is one; never clear it. Kept only in tests. */
    static void oldFilter(HttpServletRequest request, Runnable handler) {
        String id = request.getHeader("X-Request-Id");
        if (id != null) {
            MDC.put("requestId", id);
        }
        handler.run();
    }

    static MockHttpServletRequest request(String requestId) {
        MockHttpServletRequest r = new MockHttpServletRequest("GET", "/shipments/DKR100000001IN");
        if (requestId != null) {
            r.addHeader("X-Request-Id", requestId);
        }
        return r;
    }

    @Test
    void theOldFilterLetsTheNextRequestLogTheLastOnesId() {
        List<String> logged = new ArrayList<>();
        oldFilter(request("customer-a-0001"), () -> logged.add(MDC.get("requestId")));
        oldFilter(request(null), () -> logged.add(MDC.get("requestId")));        // a client that sends no id
        assertThat(logged).containsExactly("customer-a-0001", "customer-a-0001");   // B's lines are filed under A
        MDC.clear();
    }

    @Test
    void theRealFilterGivesEachRequestItsOwnIdAndLeavesNothingBehind() throws Exception {
        RequestIdFilter filter = new RequestIdFilter();
        List<String> logged = new ArrayList<>();
        FilterChain chain = (req, res) -> logged.add(MDC.get("requestId"));
        filter.doFilter(request("customer-a-0001"), new MockHttpServletResponse(), chain);
        MockHttpServletResponse second = new MockHttpServletResponse();
        filter.doFilter(request(null), second, chain);
        assertThat(logged.get(0)).isEqualTo("customer-a-0001");
        assertThat(logged.get(1)).isNotEqualTo("customer-a-0001").isEqualTo(second.getHeader("X-Request-Id"));
        assertThat(MDC.get("requestId")).isNull();
    }

    @Test
    void theIdIsClearedEvenWhenTheRequestFails() {
        RequestIdFilter filter = new RequestIdFilter();
        FilterChain failing = (req, res) -> {
            throw new IllegalStateException("handler failed");
        };
        try {
            filter.doFilter(request("customer-b-0002"), new MockHttpServletResponse(), failing);
        } catch (Exception expected) {
            // the failure itself is not the point here
        }
        assertThat(MDC.get("requestId")).isNull();
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
./mvnw test                 # all 14 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Send a request with your own id, then look for it in the app's console.

``` code
curl -i -H "X-Request-Id: my-first-request" http://localhost:8080/shipments/DKR100000001IN
# in the app's console:  INFO [rid:my-first-request] ... Tracking lookup for DKR100000001IN: OUT_FOR_DELIVERY
```

## What the log lines look like

The running app's own console lines while the examples above were captured (`docs/captures/app-log.txt`; timestamps and process id removed). Case 1 and case 3, each under its request id.

``` console
INFO [rid:app-7f3a9c21] --- [dakroute-tracking] [nio-8080-exec-2] c.dakroute.tracking.ShipmentController   : Tracking lookup for DKR100000001IN: OUT_FOR_DELIVERY
INFO [rid:support-case-41] --- [dakroute-tracking] [nio-8080-exec-4] c.dakroute.tracking.ShipmentController   : Tracking lookup for DKR999999999IN: not found
```

## Troubleshooting

| You see                      | Cause                                            | Fix                                                         |
|------------------------------|--------------------------------------------------|-------------------------------------------------------------|
| `[rid:-]` on a line          | Logged outside a request, or on another thread.  | Expected at startup; for worker threads, see challenge 2.   |
| A different id than you sent | Yours was not 8 to 64 letters, digits or dashes. | Send a UUID or similar.                                     |
| `503` on every lookup        | The drill switch is on.                          | Restart without `--dakroute.tracking.simulate-outage=true`. |

## Project layout

``` tree
stations/026-request-ids-for-parcel-tracking/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/dakroute/tracking/
│   ├── RequestIdFilter.java   ├── ShipmentController.java
│   ├── Shipments.java         └── TrackingApplication.java
├── src/main/resources/application.yaml   log pattern, actuator, drill switch
├── src/test/java/com/dakroute/tracking/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/dakroute/tracking/RequestIdFilter.java`

Does  
Takes or makes the id, puts it in the MDC and the response header, and removes it at the end.

Why  
A filter at the highest precedence: it wraps everything, including requests no controller handles.

Without it  
The trap: `MDC.put` with no `finally`.

- Only `[A-Za-z0-9-]{8,64}` is accepted: a header is attacker input, and the log is not a place for it.
- `MDC.remove` in `finally` runs even when the handler throws.

#### `src/main/java/com/dakroute/tracking/ShipmentController.java`

Does  
The lookup, its log lines at the right levels, the metric, and problems that carry the request id.

Why  
One `count(outcome)` per path through the method, so the metric adds up to all lookups.

Without it  
A 500 with a stack trace when the store fails.

#### `src/main/java/com/dakroute/tracking/Shipments.java`

Demo shipments in memory, and the outage switch used by the failure drill.

#### `src/main/resources/application.yaml`

The log pattern with `[rid:…]`, the actuator endpoints, and the drill switch (off).

#### `src/main/java/com/dakroute/tracking/TrackingApplication.java`

Standard Spring Boot entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                    | Test class                    | Result |
|---------------|------------------------------------------------|-------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found       | `ShipmentContractTest` (6)    | pass   |
| Every station | Reproduce the failure before the fix           | `LeakedRequestIdTrapTest` (3) | pass   |
| Operations    | A controlled failure drill                     | `OperationsDrillTest` (3)     | pass   |
| This station  | Log lines carry the id; forged text never does | `RequestIdLoggingTest` (2)    | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.dakroute.tracking.RequestIdLoggingTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.dakroute.tracking.OperationsDrillTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.dakroute.tracking.LeakedRequestIdTrapTest
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.dakroute.tracking.ShipmentContractTest
[INFO] Tests run: 14, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/dakroute/tracking/LeakedRequestIdTrapTest.java`

Written first: the old filter on one thread, the real filter, and a failing handler.

#### `src/test/java/com/dakroute/tracking/ShipmentContractTest.java`

The id on every response and error body, and unsafe ids replaced.

#### `src/test/java/com/dakroute/tracking/RequestIdLoggingTest.java`

The real console output, captured: the id on the line, forged text absent.

#### `src/test/java/com/dakroute/tracking/OperationsDrillTest.java`

The drill: outage, the trail it leaves (503, ERROR line, metric), and recovery.

#### `src/test/java/com/dakroute/tracking/ApiTest.java`

Shared setup: the whole app through MockMvc, filters included.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/dakroute/tracking/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=AccessLogChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 14 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 16 tests pass (14 station tests and 2 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## An access line per request

Log one INFO line when each request ends: method, path, status and duration, under the request's id. Requests that log nothing else, and paths no controller handles, get one too.

**Done when:** the test in `AccessLogChallengeTest` passes.

Hints

- The filter already wraps every request: time it there.
- Log in the `finally`, before the MDC entry is removed.

#### `challenge/AccessLogChallengeTest.java`

``` code
package com.dakroute.tracking;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/**
 * Challenge 1: one INFO line when each request ends: method, path, status and how long it took, under the request's
 * id. Support can then see every request a customer made, not only the ones that logged something.
 */
@ExtendWith(OutputCaptureExtension.class)
class AccessLogChallengeTest extends ApiTest {

    @Test
    void everyRequestEndsWithOneAccessLine(CapturedOutput output) throws Exception {
        track("DKR100000001IN", "access-log-0001");
        mvc.perform(get("/shipment/typo").header("X-Request-Id", "access-log-0002"));
        assertThat(output.getOut())
                .containsPattern("INFO \\[rid:access-log-0001\\] .* GET /shipments/DKR100000001IN -> 200 in \\d+ ms")
                .containsPattern("INFO \\[rid:access-log-0002\\] .* GET /shipment/typo -> 404 in \\d+ ms");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Keep the id on another thread

Add `GET /shipments/{awb}/eta`, which works out the estimate on a worker thread and logs it. The MDC belongs to one thread, so the worker's line has no id. Make the executor carry it across.

**Done when:** the test in `AsyncRequestIdChallengeTest` passes. Without the fix the line shows `[rid:-]`.

Hints

- A `TaskDecorator` on a `ThreadPoolTaskExecutor` runs around every task.
- Copy with `MDC.getCopyOfContextMap()` on the caller's thread; `setContextMap` and `clear` on the worker.

#### `challenge/AsyncRequestIdChallengeTest.java`

``` code
package com.dakroute.tracking;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /shipments/{awb}/eta works out the delivery estimate on a worker thread. The MDC belongs to one
 * thread, so the worker's log line loses the request id unless the executor copies it across (a TaskDecorator).
 */
@ExtendWith(OutputCaptureExtension.class)
class AsyncRequestIdChallengeTest extends ApiTest {

    @Test
    void theWorkerThreadLogsUnderTheSameRequestId(CapturedOutput output) throws Exception {
        mvc.perform(get("/shipments/DKR100000001IN/eta").header("X-Request-Id", "eta-request-0001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.estimate").value("TODAY"));
        assertThat(output.getOut()).containsPattern("\\[rid:eta-request-0001\\] .*eta-worker.* Estimated DKR100000001IN: TODAY");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## One id across five services

Tracking calls the courier partner, the address service and the notification service. How would one customer's request be followed through all of them? Compare passing `X-Request-Id` along with the W3C Trace Context `traceparent` header and a tracing system. What does each service need to do, and what happens at a service that does not?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: two requests on one thread through the old filter.
2.  Write the filter with `finally`; test it the same way, and with a failing handler.
3.  Add the id to the log pattern and to error bodies; capture real log output in a test.
4.  Add the metric and the outage switch; write the drill as a test.

## Design alternatives and trade-offs

| Approach                                         | What it costs                                                                     | Verdict           |
|--------------------------------------------------|-----------------------------------------------------------------------------------|-------------------|
| `OncePerRequestFilter` at the highest precedence | A filter class.                                                                   | Chosen            |
| `HandlerInterceptor`                             | Runs only when a controller is chosen: unknown paths and early errors have no id. | Misses requests   |
| Set the MDC, never clear it                      | The next request on the thread logs the wrong id.                                 | The trap          |
| Trust any incoming id                            | Callers write into your logs: fake lines, huge values.                            | Unsafe            |
| Micrometer Tracing (trace and span ids)          | A dependency and a tracing backend; ids across services.                          | For many services |

## Database design

None in this station. Logs and metrics are not stored in the application's database: they go to a log platform and a metrics system, which keep them for a set time.

# 3 · Go deeper: Production

## Operations

Metric  
`tracking.lookups`, tagged `outcome` = found, not_found, invalid, error. Error rate = error ÷ all lookups.

Alert  
Page the on-call engineer when the error rate is above 5% for 5 minutes (thresholds are a starting point; tune them on real traffic). A rise in not_found alone is not an outage: it often follows a partner's bad data.

Rollback  
The filter and metric hold no data, so rolling back is redeploying the previous version. If a release breaks request ids (missing headers, wrong ids in logs), roll back first and investigate after.

## Runbook: "a customer's tracking failed"

1.  Ask for the screenshot or the error body: it shows `requestId`.
2.  Search the logs for `[rid:<that id>]`. Every line of that request appears, in order.
3.  An ERROR line names the failure (for example, the store did not answer). Check `tracking.lookups{outcome=error}`: one customer, or everyone?
4.  Everyone: follow the store's own runbook; tell customers to retry (the response already says `Retry-After: 60`). One customer: check the AWB and the shipment's data.

## Failure drill

A controlled failure drill, run before you need the runbook for real:

1.  Start a test instance with `--dakroute.tracking.simulate-outage=true`.
2.  Send a lookup with `X-Request-Id: drill-001`: expect `503`, `Retry-After: 60` and `requestId: drill-001` in the body.
3.  Follow the runbook from that id alone: find the ERROR line, and see `outcome=error` rise in `/actuator/metrics/tracking.lookups`.
4.  Restart without the switch; check lookups answer `200` again.

The same drill runs on every build as `OperationsDrillTest` (3 tests, passing in `docs/test-run.txt`).

## Real-world considerations

Privacy  
Request ids are opaque labels. Never use a phone number or an email as one: it would sit in every log line.

Threads  
Virtual threads, async executors and reactive code do not carry the MDC on their own (challenge 2).

Volume  
DEBUG lines are off in production. INFO per lookup at 40,000 lines a minute costs storage: keep only what support uses.

# 3 · Go deeper: Interview

## Interview takeaways

What is the MDC?

A per-thread map of values that the logging pattern can print on every line, such as a request id. It belongs to the thread, not the request.

Why clear the MDC in finally?

Servers reuse threads. Anything left in the MDC is printed on the next request's lines, and finally runs even when the request fails.

Filter or HandlerInterceptor?

A filter wraps the whole request, before Spring chooses a controller. An interceptor runs around controller calls only, so unknown paths and some errors never reach it.

Should you trust the incoming X-Request-Id?

Only if it matches a strict pattern. It is caller input going into your logs: it can forge lines or be huge.

Which log level for what?

DEBUG: details for debugging. INFO: normal events. WARN: something a person should look at soon. ERROR: a failure that needs action now.

## Self-check rubric

| Area        | Meets the bar                           | Above the bar                                               |
|-------------|-----------------------------------------|-------------------------------------------------------------|
| Correctness | All 14 tests pass.                      | You can explain why the trap only shows on a reused thread. |
| Logging     | Every line of a request carries its id. | You can keep it on worker threads too.                      |
| Operations  | A metric, an alert and a runbook.       | You ran the failure drill end to end.                       |
| Explanation | Filter versus interceptor.              | Request ids versus distributed tracing.                     |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any logging change:

- Is everything put in the MDC removed in a `finally`?
- Does every request get an id, including errors and unknown paths?
- Can a caller write arbitrary text into the logs?
- Does every error body carry something support can search for?
