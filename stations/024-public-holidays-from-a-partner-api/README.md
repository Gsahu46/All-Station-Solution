# Station 024 · Public holidays from a partner API

Foundations · 0–1 years · Core · HR SaaS · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · RestClient · @HttpExchange · JDK HttpServer stub · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The holiday provider is simulated by a demo endpoint inside the same app, called over real HTTP; its data is a few fixed-date holidays, not an official list. Tests use a stub HTTP server instead.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 10 tests.

# 1 · Understand

## The problem in real life

1.  **Leave balances ignore holidays**

    Employees in Bengaluru lose a day of leave for Kannada Rajyotsava, because Teamdesk does not know it is a holiday.

2.  **The first fix calls the provider**

    It works in the demo. Then the provider has a slow morning: every leave request waits, threads pile up, and Teamdesk stops answering anyone. When the provider returns 500, Teamdesk returns 500 too.

3.  **The fix**

    Call the provider with a time limit, and translate each kind of failure into an honest answer of our own: too slow, failed, or no list. Never pass their error text on.

Every call to someone else's service needs a time limit and a plan for each way it can fail.

## What are we building?

`GET /holidays?year=2026&state=KA` asks the holiday provider for a state's holidays and returns them sorted, in our own shape. When the provider is slow or broken, it says so with `504` or `502`, quickly.

## An everyday analogy

A shopkeeper phones the wholesaler for a price. If nobody answers in a minute, she tells the customer "the wholesaler is not answering, come back later" instead of standing at the phone all day while the queue grows.

## How it works in 4 steps

1.  **Check the request** first: a bad year or state is `400`, and the provider is never called.
2.  **Call the provider** through an interface client, with a 1 s connect and a 2 s read limit.
3.  **Translate failures**: their 404 is ours; their 5xx, bad key or garbage is `502`; their slowness is `504`.
4.  **Answer in our shape**: only the fields we use, sorted by date.

Check yourself: the provider says 401 because our API key expired. Should our client get 401?

No. 401 tells our client *they* must sign in again, which will not help. The fault is between us and the provider: `502`, and an alert for us.

## What this station is not

- **No real holiday provider.** A simulated one, with a few fixed-date holidays.
- **No retries or circuit breaker.** Discussed in Design; a later station builds them.
- **No leave calculation.** Only the holiday list.

## Key terms

| Term                      | Simple meaning                                                       | Everyday example                                    | In this project                          |
|---------------------------|----------------------------------------------------------------------|-----------------------------------------------------|------------------------------------------|
| **Partner API**           | Someone else's service that our service calls.                       | Calling a supplier to ask what is in stock.         | The holiday provider                     |
| **Timeout**               | How long we wait before giving up.                                   | Hanging up after ringing for a minute.              | `read-timeout: 2s`                       |
| **502 Bad Gateway**       | "The service I depend on failed."                                    | "The supplier gave us a wrong answer."              | Provider 5xx, bad key, unreadable answer |
| **504 Gateway Timeout**   | "The service I depend on was too slow."                              | "The supplier did not pick up."                     | Provider slower than 2 s                 |
| **HTTP interface client** | An interface whose methods Spring turns into HTTP calls.             | A speed-dial button with the number already stored. | `@HttpExchange`                          |
| **Stub server**           | A fake partner, run by the test, that answers however the test says. | A colleague playing the customer in a rehearsal.    | `StubProvider`                           |

# 2 · Build: Spec

## Business problem

**Teamdesk** (a fictional HR app) must count public holidays when it computes leave. Holidays come from a provider's API. The first integration had no timeout and no error handling: one slow morning at the provider took Teamdesk down with it, and every provider error reached users as a 500.

## Acceptance criteria

1.  **Given** 2026 and KA, **then** the provider is asked for `year=2026&region=KA` and the holidays come back sorted by date, without the provider's extra fields.
2.  **Given** the provider takes longer than the read limit, **then** `504`, well before the provider answers.
3.  **Given** the provider answers 500, 401, unreadable data, or hangs up, **then** `502`, and none of its error text in our body.
4.  **Given** the provider has no list for the state, **then** `404`.
5.  **Given** an unknown state, a year outside 2000 to 2100, or no year, **then** `400`, and the provider is not called.

## Requirements

- Connect limit 1 s, read limit 2 s, both in configuration.
- States are normalised with `Locale.ROOT`; the demo list is KA, MH, DL, TN.
- The provider's error bodies are logged, never returned.
- Only the fields we use are mapped; anything else the provider adds is ignored.

## Learning objectives

- Call an HTTP API with `RestClient` and an `@HttpExchange` interface.
- Map a partner's JSON to records.
- Set timeouts, and translate 4xx, 5xx and timeouts into honest answers.
- Test against a stub HTTP server that can be slow or broken on demand.

# 2 · Build: API contract

## Endpoint

| Method | Path                   | Purpose                                                  |
|--------|------------------------|----------------------------------------------------------|
| `GET`  | `/holidays?year&state` | A state's public holidays for a year, from the provider. |

## Status codes

| Status | When                                                                         |
|--------|------------------------------------------------------------------------------|
| 200    | The holidays, sorted by date                                                 |
| 400    | Unknown state, or a year missing or outside 2000 to 2100                     |
| 404    | The provider has no list for that state and year                             |
| 502    | The provider failed, rejected our key, sent something unreadable, or hung up |
| 504    | The provider did not answer within the read limit                            |

## Captured examples

Captured with curl from the running app on 14 Oct 2026. The app calls its simulated provider over HTTP; year 2098 and 2099 are the simulated provider's demo switches for slow and failing. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: what the provider sends

**Why:** their shape: extra fields (`country`, `observed`, `generatedBy`) and their own order.

Request

``` code
GET /demo-provider/v1/holidays?year=2026&region=KA HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json

{
  "country": "IN",
  "year": 2026,
  "generatedBy": "demo",
  "region": "KA",
  "holidays": [
    {
      "type": "NATIONAL",
      "name": "Independence Day",
      "date": "2026-08-15",
      "observed": true
    },
    {
      "type": "NATIONAL",
      "name": "Republic Day",
      "date": "2026-01-26",
      "observed": true
    },
    {
      "type": "NATIONAL",
      "name": "Gandhi Jayanti",
      "date": "2026-10-02",
      "observed": true
    },
    {
      "type": "STATE",
      "name": "Kannada Rajyotsava",
      "date": "2026-11-01",
      "observed": true
    }
  ]
}
```

### Case 2: what we send

**Why:** only the fields we use, sorted by date, under our names.

Request

``` code
GET /holidays?year=2026&state=KA HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 296

{
  "year": 2026,
  "state": "KA",
  "holidays": [
    {
      "date": "2026-01-26",
      "name": "Republic Day",
      "type": "NATIONAL"
    },
    {
      "date": "2026-08-15",
      "name": "Independence Day",
      "type": "NATIONAL"
    },
    {
      "date": "2026-10-02",
      "name": "Gandhi Jayanti",
      "type": "NATIONAL"
    },
    {
      "date": "2026-11-01",
      "name": "Kannada Rajyotsava",
      "type": "STATE"
    }
  ]
}
```

### Case 3: a state the provider has no list for

**Why:** their 404 becomes our 404, with our own wording.

Request

``` code
GET /holidays?year=2026&state=tn HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "The provider has no holiday list for TN in 2026.",
  "instance": "/holidays",
  "status": 404,
  "title": "No holiday list"
}
```

### Case 4: an unknown state

**Why:** refused before any call: `400`.

Request

``` code
GET /holidays?year=2026&state=ZZ HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "state must be one of DL, KA, MH, TN.",
  "instance": "/holidays",
  "status": 400,
  "title": "Unknown state"
}
```

### Case 5: the provider fails

**Why:** its 500 names a database host. We answer `502` and keep that text in our logs.

Request

``` code
GET /holidays?year=2099&state=KA HTTP/1.1
```

Response

``` code
HTTP/1.1 502 
Content-Type: application/problem+json

{
  "detail": "The holiday provider failed to answer. Try again shortly.",
  "instance": "/holidays",
  "status": 502,
  "title": "Holiday provider failed"
}
```

### Case 6: the provider is too slow

**Why:** the provider takes 3 s; we stop waiting at 2 s: `504`.

Request

``` code
GET /holidays?year=2098&state=KA HTTP/1.1
```

Response

``` code
HTTP/1.1 504 
Content-Type: application/problem+json

{
  "detail": "The holiday provider did not answer in time. Try again shortly.",
  "instance": "/holidays",
  "status": 504,
  "title": "Holiday provider too slow"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                     | What happens                             | Proved by                                      |
|------------------------------------------|------------------------------------------|------------------------------------------------|
| 2026, lower-case ka                      | Sorted, our shape; provider asked for KA | `aStatesHolidaysComeBackSortedInOurShape`      |
| Provider 404                             | `404`                                    | `theProvidersNotFoundIsOurNotFound`            |
| ZZ; 1999; abc; no year                   | `400`, no call made                      | `badRequestsAre400AndNeverReachTheProvider`    |
| Provider 500 with a host name            | `502`, host not shown                    | `aProvider500IsOur502WithoutTheirInternals`    |
| Provider 401 (our key)                   | `502`, key not shown                     | `ourExpiredKeyIsOur502NotTheClients401`        |
| HTML instead of JSON                     | `502`                                    | `anAnswerWeCannotReadIs502`                    |
| Connection closed with no answer         | `502` unreachable, not a timeout         | `aDroppedConnectionIs502NotATimeout`           |
| Provider takes 2 s, limit 400 ms (tests) | `504` in under 1.5 s                     | `theRealEndpointGivesUpInTimeAndSaysWhoFailed` |

## The trap

Plausible but wrong

No timeout and no handling of the partner's 5xx, so our API hangs or 500s.

`RestClient.create(url)` works in every demo. The first test shows it waiting the full 2 seconds a slow provider takes, and it would wait far longer. The second shows the provider's 500 escaping as an exception, which our API turns into its own 500. The third shows the real endpoint answering `504` within its limit and `502` for the failure. While building, removing the read timeout turned 1 test red, removing the failure handling turned 4 red, and passing the provider's message through turned 2 red.

``` code
package com.teamdesk.holidays;

import org.junit.jupiter.api.Test;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.RestClient;

import java.time.Duration;
import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: it reproduces the bugs before the fix. */
class SlowProviderTrapTest extends ApiTest {

    /** The "before" call: a RestClient with no timeout and no error handling. Kept only in tests. */
    static String oldCall() {
        return RestClient.create(STUB.baseUrl()).get().uri("/v1/holidays?year=2026&region=KA").retrieve().body(String.class);
    }

    @Test
    void theOldCallWaitsAsLongAsTheProviderLikes() {
        STUB.behaviour = StubProvider.Behaviour.SLOW;
        Instant start = Instant.now();
        oldCall();
        assertThat(Duration.between(start, Instant.now())).isGreaterThanOrEqualTo(Duration.ofMillis(1_900));
        // every request thread stuck like this is one fewer for everyone else
    }

    @Test
    void theOldCallTurnsTheProvidersFailureIntoOurs() {
        STUB.behaviour = StubProvider.Behaviour.FAIL;
        assertThatThrownBy(SlowProviderTrapTest::oldCall)
                .isInstanceOf(HttpServerErrorException.InternalServerError.class);   // uncaught: our API answers 500
    }

    @Test
    void theRealEndpointGivesUpInTimeAndSaysWhoFailed() throws Exception {
        STUB.behaviour = StubProvider.Behaviour.SLOW;
        Instant start = Instant.now();
        holidays("2030", "KA").andExpect(status().isGatewayTimeout())   // years no test fetches successfully: nothing cached
                .andExpect(jsonPath("$.title").value("Holiday provider too slow"));
        assertThat(Duration.between(start, Instant.now())).isLessThan(Duration.ofMillis(1_500));

        STUB.behaviour = StubProvider.Behaviour.FAIL;
        holidays("2031", "KA").andExpect(status().isBadGateway())
                .andExpect(jsonPath("$.title").value("Holiday provider failed"));
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

``` code
curl "http://localhost:8080/holidays?year=2026&state=KA"

# The simulated provider's demo switches: 2099 fails, 2098 is too slow
curl -i "http://localhost:8080/holidays?year=2099&state=KA"
curl -i "http://localhost:8080/holidays?year=2098&state=KA"
```

## Troubleshooting

| You see                             | Cause                                                           | Fix                                                      |
|-------------------------------------|-----------------------------------------------------------------|----------------------------------------------------------|
| `502` unreachable for every request | The provider address is wrong, or the app runs on another port. | Check `teamdesk.holidays.base-url`.                      |
| `504` for normal requests           | The read limit is shorter than the provider's normal answer.    | Raise `read-timeout` a little; never remove it.          |
| `release version 25 not supported`  | Maven is using an older JDK.                                    | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`. |

## Project layout

``` tree
stations/024-public-holidays-from-a-partner-api/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/teamdesk/holidays/
│   ├── HolidayController.java      ├── HolidayProviderClient.java
│   ├── ProviderClientConfig.java   ├── DemoProviderController.java   └── HolidaysApplication.java
├── src/test/java/com/teamdesk/holidays/   (see Tests; StubProvider is the fake partner)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/teamdesk/holidays/HolidayController.java`

Does  
Validates, calls the provider, and translates every failure into our own answer.

Why  
One `try` with a `catch` per kind of failure, ordered from specific to general.

Without it  
Letting the provider's exception become our 500.

#### `src/main/java/com/teamdesk/holidays/HolidayProviderClient.java`

Does  
The provider's API as an interface, with records for its JSON.

Why  
Spring writes the HTTP call; the interface is easy to read and easy to fake.

Without it  
Hand-built URLs and string JSON.

#### `src/main/java/com/teamdesk/holidays/ProviderClientConfig.java`

Does  
Builds the client with a connect and a read time limit.

Why  
Limits from configuration, so operations can tune them without a release.

Without it  
The trap: a client with no time limit.

#### `src/main/java/com/teamdesk/holidays/DemoProviderController.java`

The simulated provider, so the app runs on its own. Switched off in tests, which use a stub server.

#### `src/main/resources/application.yaml`

The provider's address and time limits, and the demo provider switch.

#### `src/main/java/com/teamdesk/holidays/HolidaysApplication.java`

Standard Spring Boot entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                 | Result |
|---------------|-------------------------------------------------------|----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `HolidayContractTest` (3)  | pass   |
| Every station | Reproduce the failure before the fix                  | `SlowProviderTrapTest` (3) | pass   |
| This station  | Every other provider failure; nothing of theirs leaks | `ProviderFailureTest` (4)  | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.teamdesk.holidays.SlowProviderTrapTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.teamdesk.holidays.HolidayContractTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.teamdesk.holidays.ProviderFailureTest
[INFO] Tests run: 10, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/teamdesk/holidays/SlowProviderTrapTest.java`

Written first: the old call's wait and its escaping 500, and the real endpoint's 504 and 502.

#### `src/test/java/com/teamdesk/holidays/HolidayContractTest.java`

A year's holidays, the provider's 404, and requests refused before any call.

#### `src/test/java/com/teamdesk/holidays/ProviderFailureTest.java`

500, 401, HTML and a dropped connection, each with its answer.

#### `src/test/java/com/teamdesk/holidays/StubProvider.java`

The fake partner: the JDK's own HTTP server on a random port, told per test how to behave.

#### `src/test/java/com/teamdesk/holidays/ApiTest.java`

Shared setup: points the app at the stub, with a 400 ms read limit.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/teamdesk/holidays/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=LastGoodAnswerChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 10 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 13 tests pass (10 station tests and 3 challenge tests).

Challenge 1 · Go deeper · about 30 minutes

## Serve the last good answer

A year's holidays rarely change. Keep the last good answer per year and state; when the provider fails or is too slow, serve it. Say where the answer came from: `"source": "provider"` or `"cache"`.

**Done when:** both tests in `LastGoodAnswerChallengeTest` pass, and the station's tests still pass.

Hints

- A `ConcurrentHashMap` keyed by year and state is enough here.
- Catch the failure where you build the answer; rethrow it when there is nothing cached, or when it is a 404.

#### `challenge/LastGoodAnswerChallengeTest.java`

``` code
package com.teamdesk.holidays;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: a year's holidays rarely change. Keep the last good answer per year and state, and serve it when
 * the provider fails or is too slow. The response says where it came from: "provider" or "cache".
 */
class LastGoodAnswerChallengeTest extends ApiTest {

    @Test
    void aFailingProviderIsCoveredByTheLastGoodAnswer() throws Exception {
        holidays("2027", "MH").andExpect(status().isOk()).andExpect(jsonPath("$.source").value("provider"));
        STUB.behaviour = StubProvider.Behaviour.FAIL;
        holidays("2027", "MH").andExpect(status().isOk()).andExpect(jsonPath("$.source").value("cache"))
                .andExpect(jsonPath("$.holidays[0].name").value("Republic Day"));
        STUB.behaviour = StubProvider.Behaviour.SLOW;
        holidays("2027", "MH").andExpect(status().isOk()).andExpect(jsonPath("$.source").value("cache"));
    }

    @Test
    void withNothingCachedTheFailureStillShows() throws Exception {
        STUB.behaviour = StubProvider.Behaviour.FAIL;
        holidays("2028", "MH").andExpect(status().isBadGateway());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Beginner-friendly · about 15 minutes

## Send an API key

The provider wants an `X-Api-Key` header. Read the key from `teamdesk.holidays.api-key` and send it with every call. It must never appear in our responses.

**Done when:** the test in `ApiKeyChallengeTest` passes.

Hints

- `RestClient.builder().defaultHeader(...)` adds it to every request.
- In real deployments the property comes from an environment variable, never from the repository.

#### `challenge/ApiKeyChallengeTest.java`

``` code
package com.teamdesk.holidays;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: the provider wants an API key in an X-Api-Key header. The key comes from configuration
 * (teamdesk.holidays.api-key, set from an environment variable in real life) and never appears in our responses.
 */
@TestPropertySource(properties = "teamdesk.holidays.api-key=tdk_test_1234")
class ApiKeyChallengeTest extends ApiTest {

    @Test
    void everyCallCarriesTheKeyAndNoResponseShowsIt() throws Exception {
        String body = holidays("2026", "DL").andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        assertThat(STUB.lastApiKey).isEqualTo("tdk_test_1234");
        assertThat(body).doesNotContain("tdk_test_1234");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Retry, or stop asking?

Should we retry a failed call to the provider? Which failures are worth one retry, and which never are? If the provider is down for an hour, what stops thousands of our requests from each waiting 2 seconds? Sketch a circuit breaker: when it opens, when it tries again, and what users see meanwhile.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the stub provider and the trap test: the old call waits, and its 500 escapes.
2.  Declare the provider's API as an `@HttpExchange` interface with records.
3.  Build the client with connect and read limits from configuration.
4.  Translate each kind of failure; test each one, including a dropped connection.

## Design alternatives and trade-offs

| Approach                                    | What it costs                                  | Verdict                 |
|---------------------------------------------|------------------------------------------------|-------------------------|
| `@HttpExchange` interface over `RestClient` | An interface and a config class.               | Chosen                  |
| `RestClient` calls written by hand          | More code per call; fine for one or two calls. | Also fine               |
| `RestTemplate`                              | Deprecated in Spring Framework 7.1.            | Avoid in new code       |
| No timeout                                  | One slow partner takes us down.                | The trap                |
| WireMock for the stub                       | A dependency; richer matching and recording.   | For bigger integrations |

## Database design

None in this station. Holidays change once a year: a real system would copy them into a `public_holidays` table (date, state, name) on a schedule, and answer from there, calling the provider only to refresh.

# 3 · Go deeper: Production

Time limits  
The read limit must be shorter than our own clients' patience, and every thread waiting on a partner is one not serving anyone else.

Errors  
Log the partner's error body, with the status; return our own wording. Their messages name hosts, keys and versions.

Secrets  
API keys come from the environment (challenge 2), never from the repository or a log line.

Monitoring  
Count 502s and 504s by cause. A rise in timeouts is often the first sign of a partner's trouble.

# 3 · Go deeper: Interview

## Interview takeaways

What happens without a timeout on an HTTP call?

The thread waits as long as the other side likes. Under load, every request thread ends up waiting and the whole service stops answering.

502 or 504?

504 when the upstream service did not answer in time; 502 when it answered badly (5xx, garbage) or could not be reached.

Should a partner's 401 become our 401?

No. It means our credentials with them are wrong, which our client cannot fix. Answer 502 and alert ourselves.

What is @HttpExchange?

A Spring annotation for declaring an HTTP API as a Java interface. HttpServiceProxyFactory turns it into a client over RestClient.

How do you test a partner integration?

Against a stub HTTP server you control: make it slow, failing, or return garbage, and check each answer. Never against the real partner in unit tests.

## Self-check rubric

| Area        | Meets the bar                      | Above the bar                                                         |
|-------------|------------------------------------|-----------------------------------------------------------------------|
| Correctness | All 10 tests pass.                 | You can map each provider failure to our status code without looking. |
| Resilience  | Timeouts set, failures translated. | You can explain thread exhaustion.                                    |
| Testing     | A stub that can be slow or broken. | Why not test against the real provider.                               |
| Explanation | 502 versus 504.                    | Retries and circuit breakers, and when each helps.                    |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any outgoing HTTP call:

- Is there a connect and a read time limit?
- What does each failure (4xx, 5xx, timeout, garbage) become for our caller?
- Can any of the partner's error text reach our caller?
- Is there a test with a slow and a failing partner?
