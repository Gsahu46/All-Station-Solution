# Station 025 · OTP request limiter

Foundations · 0–1 years · Core · Fintech · Types: Concurrency, Idempotency

Spring Boot 4.1.1 · Java 25 · Spring MVC · ConcurrentHashMap.compute · CompletableFuture · virtual threads · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** No SMS is sent: a simulated sender waits as long as a provider call and counts what it would have sent. OTP codes are generated but never returned or logged. Limits are kept in this server's memory.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 14 tests.

# 1 · Understand

## The problem in real life

1.  **A bot targets one number**

    It sends 20 OTP requests at the same instant. Each one checks "fewer than 3 sent in 10 minutes?", sees yes, and calls the SMS provider. 20 SMS go out, and Tijori pays for each.

2.  **The app retries a slow request**

    The customer taps once, the network is slow, the app retries. The old code counts it as a second request and sends a second code.

3.  **The fix**

    Check and book the slot in one atomic step, before calling the SMS provider. Remember each Idempotency-Key, so a retry, even one arriving at the same instant, gets the first answer.

"Check, then act" is two steps. Under load, something always fits between them.

## What are we building?

`POST /otp-requests` sends (simulated) an OTP to a number, at most 3 times in any 10 minutes per number. Beyond that it answers `429` with how long to wait. A retried request gets the same answer and no second SMS.

## An everyday analogy

A temple gives 3 tokens per family per hour. A careless counter looks at the register, hands over the token, then writes the entry: four relatives at four windows all get one. A careful counter writes the entry and hands the token in one movement, at one register.

## How it works in 4 steps

1.  **Normalise the number**: +91 98765 43210 and 098765-43210 are 9876543210.
2.  **Look up the key**: seen before? Return that answer, even if it is still being made.
3.  **Check and book in one step**: fewer than 3 in the window? Take a slot. Otherwise `429` with the wait.
4.  **Send the SMS** only after the slot is booked.

Check yourself: the count is a ConcurrentHashMap. Why is that not enough?

Each call on it is safe, but "read the count, decide, then add" is three calls. Another request can run between them. The decision and the update must be one atomic call: `compute`.

## What this station is not

- **Not across servers.** The count lives in one server's memory: with N servers, a number can get 3 × N. Station 125 shares the count.
- **No real SMS.** A simulated sender counts messages.
- **No OTP verification.** Only requesting one.

## Key terms

| Term                    | Simple meaning                                                                        | Everyday example                                          | In this project               |
|-------------------------|---------------------------------------------------------------------------------------|-----------------------------------------------------------|-------------------------------|
| **OTP**                 | A one-time password sent by SMS to prove you hold the phone.                          | The 6-digit code your bank texts you.                     | `POST /otp-requests`          |
| **Race condition**      | Two things happening at once give a result neither would alone.                       | Two people book the last seat because both saw it free.   | Check, then send, then record |
| **Atomic**              | Done as one step that nothing can come between.                                       | Taking the last token from the counter in one grab.       | `ConcurrentHashMap.compute`   |
| **Idempotency key**     | An id the app sends with a request, and again on a retry, so the server does it once. | A cheque number: paying the same cheque twice is refused. | `Idempotency-Key` header      |
| **429 and Retry-After** | "Too many requests", and how many seconds to wait.                                    | "Counter closed, back in 10 minutes."                     | `Retry-After: 360`            |
| **Injectable clock**    | Code asks a Clock object for the time, so tests can set it.                           | A stage clock the director moves forward between scenes.  | `TestClock`                   |

# 2 · Build: Spec

## Business problem

**Tijori** (a fictional fintech app) pays for every OTP SMS. Bots request thousands for one number, to run up costs or to flood someone's phone. The existing limit fails exactly when it matters: requests that arrive together all slip past it. App retries are counted as new requests.

## Acceptance criteria

1.  **Given** 20 requests for one number at the same instant, **then** exactly 3 are accepted, 17 get `429`, and 3 SMS are sent.
2.  **Given** requests at 09:00, 09:02 and 09:04, **then** a 4th at 09:05 gets `429` with `Retry-After: 300`, and one at 09:10 is accepted.
3.  **Given** the same Idempotency-Key twice, **then** the same requestId, no second SMS, no slot used; 10 copies at once are still one request.
4.  **Given** a key reused for another number, **then** `422`.
5.  **Given** +91 98765 43210, 098765-43210 and 9876543210, **then** one number, one limit.
6.  **Given** a number that is not a 10-digit Indian mobile, or a missing or malformed key, **then** `400`.

## Requirements

- 3 requests per number in any 10 minutes (a demo rule); different numbers never wait for each other.
- The slot is booked before the SMS is sent; Retry-After counts from the oldest request in the window, rounded up.
- The code is never in a response or a log; responses show the number masked.
- Time comes from an injected `Clock`.

## Learning objectives

- Recognise check-then-act races, and fix them with an atomic operation.
- Choose between `synchronized` and `ConcurrentHashMap.compute`.
- Make a request idempotent, including two copies arriving at once.
- Answer `429` with an honest `Retry-After`, and test time with an injectable clock.
- Prove an invariant with a real parallel test.

# 2 · Build: API contract

## Endpoint

| Method | Path            | Purpose                                                               |
|--------|-----------------|-----------------------------------------------------------------------|
| `POST` | `/otp-requests` | Send an OTP to a number. `202`: accepted, SMS on its way (simulated). |

## Request

| Part                     | Rule                                                                                                  |
|--------------------------|-------------------------------------------------------------------------------------------------------|
| `Idempotency-Key` header | 8 to 64 letters, digits or `-`. A new key per tap of "Send OTP"; the same key when retrying that tap. |
| `mobile`                 | An Indian mobile number; +91, a leading 0, spaces and dashes are allowed.                             |

## Status codes

| Status | When                                                                           |
|--------|--------------------------------------------------------------------------------|
| 202    | Accepted (or a retry of an accepted request: the same body)                    |
| 400    | Not a mobile number, or the key is missing or malformed                        |
| 422    | The key was already used for another number                                    |
| 429    | 3 requests in the last 10 minutes; `Retry-After` says how many seconds to wait |

`Idempotency-Key` is described in an IETF draft (draft-ietf-httpapi-idempotency-key-header); check its current status before calling it a standard. `429` is defined in RFC 6585 and `Retry-After` in RFC 9110.

## Captured examples

Captured with curl from the running app on 14 Oct 2026, in this order, within a few seconds. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: the first tap

**Why:** accepted; the code is not in the response, the number is masked, two attempts left.

Request

``` code
POST /otp-requests HTTP/1.1
Content-Type: application/json
Idempotency-Key: tap-7f3a-0001

{
  "mobile": "9876543210"
}
```

Response

``` code
HTTP/1.1 202 
Content-Type: application/json
Content-Length: 126

{
  "requestId": "otp_a6b2ca80b25948a9820b4e8758785bd2",
  "mobile": "XXXXXX3210",
  "expiresAt": "2026-10-14T13:25:03Z",
  "attemptsLeft": 2
}
```

### Case 2: the app retries that tap

**Why:** the same key (and the same number, written with +91): the same requestId, no second SMS, no slot used.

Request

``` code
POST /otp-requests HTTP/1.1
Content-Type: application/json
Idempotency-Key: tap-7f3a-0001

{
  "mobile": "+91 98765 43210"
}
```

Response

``` code
HTTP/1.1 202 
Content-Type: application/json
Content-Length: 126

{
  "requestId": "otp_a6b2ca80b25948a9820b4e8758785bd2",
  "mobile": "XXXXXX3210",
  "expiresAt": "2026-10-14T13:25:03Z",
  "attemptsLeft": 2
}
```

### Case 3: a second tap

**Why:** a new key: a new request. 098765-43210 is the same number.

Request

``` code
POST /otp-requests HTTP/1.1
Content-Type: application/json
Idempotency-Key: tap-7f3a-0002

{
  "mobile": "098765-43210"
}
```

Response

``` code
HTTP/1.1 202 
Content-Type: application/json
Content-Length: 126

{
  "requestId": "otp_cda68d76f026430787505616f16a6de9",
  "mobile": "XXXXXX3210",
  "expiresAt": "2026-10-14T13:25:03Z",
  "attemptsLeft": 1
}
```

### Case 4: a third tap

**Why:** the last slot in this window.

Request

``` code
POST /otp-requests HTTP/1.1
Content-Type: application/json
Idempotency-Key: tap-7f3a-0003

{
  "mobile": "9876543210"
}
```

Response

``` code
HTTP/1.1 202 
Content-Type: application/json
Content-Length: 126

{
  "requestId": "otp_e9b0337e52244585899fe8c0e48d6589",
  "mobile": "XXXXXX3210",
  "expiresAt": "2026-10-14T13:25:03Z",
  "attemptsLeft": 0
}
```

### Case 5: a fourth tap

**Why:** `429`. `Retry-After` counts to when the first request leaves the 10-minute window.

Request

``` code
POST /otp-requests HTTP/1.1
Content-Type: application/json
Idempotency-Key: tap-7f3a-0004

{
  "mobile": "9876543210"
}
```

Response

``` code
HTTP/1.1 429 
Retry-After: 600
Content-Type: application/problem+json

{
  "detail": "This number has had 3 OTPs in the last 10 minutes. Try again in 600 seconds.",
  "instance": "/otp-requests",
  "status": 429,
  "title": "Too many OTP requests"
}
```

### Case 6: a key reused for another number

**Why:** a bug in the app, not a retry: `422`, and no SMS.

Request

``` code
POST /otp-requests HTTP/1.1
Content-Type: application/json
Idempotency-Key: tap-7f3a-0001

{
  "mobile": "9123456780"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "This Idempotency-Key was used for a different number. Use a new key for a new request.",
  "instance": "/otp-requests",
  "status": 422,
  "title": "Idempotency key reused"
}
```

### Case 7: not a mobile number

**Why:** `400`, before any limit or SMS.

Request

``` code
POST /otp-requests HTTP/1.1
Content-Type: application/json
Idempotency-Key: tap-7f3a-0005

{
  "mobile": "12345"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "mobile must be an Indian mobile number of 10 digits.",
  "instance": "/otp-requests",
  "status": 400,
  "title": "Invalid mobile number"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                             | What happens                           | Proved by                                                 |
|--------------------------------------------------|----------------------------------------|-----------------------------------------------------------|
| First request                                    | 202, masked, no code, 2 left           | `anOtpRequestIsAcceptedWithoutShowingTheCodeOrTheNumber`  |
| Three formats of one number, then a 4th          | One limit; `429`, Retry-After 360      | `theFourthIn10MinutesIs429WithRetryAfterFromTheOldest`    |
| 09:00, 09:02, 09:04, then 09:05, 09:09:59, 09:10 | Retry-After 300, then 1, then accepted | `retryAfterCountsFromTheOldestRequestInTheWindow`         |
| 20 requests at once, one number                  | 3 accepted, 17 × 429, 3 SMS            | `twentyBotRequestsAtOnceGetThreeSms`                      |
| 3 numbers × 5 requests at once                   | 3 each                                 | `differentNumbersEachGetTheirOwnThree`                    |
| Same key twice                                   | Same answer, 1 SMS, no slot            | `aRetryWithTheSameKeyGetsTheSameAnswerAndNoSecondSms`     |
| Same key 10 times at once                        | One requestId, 1 SMS                   | `tenCopiesOfOneRequestAtTheSameInstantAreOneRequest`      |
| Key reused for another number                    | `422`, no SMS                          | `aKeyReusedForAnotherNumberIs422`                         |
| A refused request's key, retried later           | Accepted                               | `aRefusedRequestCanBeRetriedWithItsKeyOnceTheWindowMoves` |
| Bad numbers, keys, bodies                        | `400`                                  | `badRequestsAre400`                                       |
| Two servers                                      | 6: the limit is per server             | `theLimitIsPerServerSoTwoServersAllowSix`                 |

## The trap

Plausible but wrong

An in-memory limiter that only works on one server, and check-then-act races.

The old limiter uses thread-safe pieces: a `ConcurrentHashMap` and a synchronized list. The first test sends 20 requests at once and more than 3 get through: each checked before any had recorded. The second runs the real limiter the same way: exactly 3. The third states the limit that remains: two servers, each with its own count, allow 6. That is not fixed here; it needs a shared store (station 125).

``` code
package com.tijori.otp;

import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;

/** The first test written for this station: it reproduces the bug before the fix, and states the fix's limit. */
class CheckThenActTrapTest {

    /**
     * The "before" limiter: check the count, send the SMS, then record the request. Each step is thread-safe on its
     * own (a ConcurrentHashMap, a synchronized list); the sequence is not. Kept only in tests.
     */
    static final class OldLimiter {
        final Map<String, List<Instant>> sent = new ConcurrentHashMap<>();

        boolean request(String mobile) throws InterruptedException {
            List<Instant> times = sent.computeIfAbsent(mobile, m -> java.util.Collections.synchronizedList(new ArrayList<>()));
            if (times.size() >= 3) {
                return false;
            }
            Thread.sleep(50);              // the SMS provider call
            times.add(Instant.now());
            return true;
        }
    }

    static int acceptedOutOf20(java.util.function.Predicate<String> request) throws Exception {
        AtomicInteger accepted = new AtomicInteger();
        CountDownLatch start = new CountDownLatch(1);
        try (var threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 20; i++) {
                threads.submit(() -> {
                    start.await();
                    if (request.test("9876543210")) {
                        accepted.incrementAndGet();
                    }
                    return null;
                });
            }
            start.countDown();   // all 20 at the same instant, like a bot
        }
        return accepted.get();
    }

    @Test
    void theOldLimiterLetsTwentyThroughWhenTheyArriveTogether() throws Exception {
        OldLimiter old = new OldLimiter();
        int accepted = acceptedOutOf20(m -> {
            try {
                return old.request(m);
            } catch (InterruptedException e) {
                throw new IllegalStateException(e);
            }
        });
        assertThat(accepted).isGreaterThan(3);   // every one checked "fewer than 3 sent" before any was recorded
    }

    @Test
    void theAtomicLimiterLetsExactlyThreeThrough() throws Exception {
        OtpLimiter limiter = new OtpLimiter(Clock.systemUTC());
        assertThat(acceptedOutOf20(m -> limiter.tryAcquire(m).accepted())).isEqualTo(3);
    }

    @Test
    void theLimitIsPerServerSoTwoServersAllowSix() throws Exception {
        // The known limit of an in-memory count: each server keeps its own. Station 125 shares the count.
        OtpLimiter serverA = new OtpLimiter(Clock.systemUTC());
        OtpLimiter serverB = new OtpLimiter(Clock.systemUTC());
        AtomicInteger turn = new AtomicInteger();
        int accepted = acceptedOutOf20(m -> (turn.getAndIncrement() % 2 == 0 ? serverA : serverB).tryAcquire(m).accepted());
        assertThat(accepted).isEqualTo(6);
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

On JDK 21, add `-Djava.version=21`. Virtual threads are final in Java 21.

## Try it yourself

``` code
# Run this four times, changing the key each time; the 4th answers 429 with Retry-After
curl -i -X POST http://localhost:8080/otp-requests -H "Content-Type: application/json" \
     -H "Idempotency-Key: my-tap-0001" -d '{"mobile":"9876543210"}'
```

## Troubleshooting

| You see                             | Cause                                                                             | Fix                                       |
|-------------------------------------|-----------------------------------------------------------------------------------|-------------------------------------------|
| The same requestId every time       | You are resending the same key.                                                   | Change the key for a new tap.             |
| `400` with a valid number           | The key has characters other than letters, digits and dashes, or is under 8 long. | Use a UUID or similar.                    |
| `429` straight away after a restart | Not possible: counts live in memory and start empty.                              | If you see it, another instance answered. |

## Project layout

``` tree
stations/025-otp-request-limiter/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tijori/otp/
│   ├── OtpController.java   ├── OtpService.java   ├── OtpLimiter.java
│   ├── SmsSender.java       ├── SimulatedSmsSender.java   └── OtpApplication.java
├── src/test/java/com/tijori/otp/   (see Tests)
├── review/                   The flawed version for the Review tab
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/tijori/otp/OtpController.java`

Does  
Reads the key and the body, and hands them to the service. `202` on success.

Why  
The controller has no rules; the service is where retries, limits and the SMS meet.

Without it  
Rules spread across controllers.

#### `src/main/java/com/tijori/otp/OtpService.java`

Does  
Normalises the number, handles replays, asks the limiter, sends the SMS.

Why  
`putIfAbsent` of a `CompletableFuture`: the first request with a key does the work; any copy waits for the same result.

Without it  
Storing the answer only after it is ready, so two copies both do the work.

- A refused request removes its key: nothing happened, so a later retry may try again.
- `Retry-After` is rounded up, never inviting an early retry.
- The code goes to the SMS text only.

#### `src/main/java/com/tijori/otp/OtpLimiter.java`

Does  
3 per number per 10 minutes, checked and booked in one `compute`.

Why  
Atomic per key: requests for one number take turns; other numbers do not wait.

Without it  
The trap: check, send, then record.

#### `src/main/java/com/tijori/otp/SimulatedSmsSender.java`

Waits like a provider, counts per number, logs the masked number and never the text.

#### `src/main/java/com/tijori/otp/SmsSender.java`

The one-method interface the real provider would implement.

#### `src/main/resources/application.yaml`

Problem bodies for errors, and the simulated SMS latency.

#### `src/main/java/com/tijori/otp/OtpApplication.java`

Entry point, and the `Clock` bean tests replace.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                | Test class                 | Result |
|---------------|--------------------------------------------|----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found   | `OtpContractTest` (5)      | pass   |
| Every station | Reproduce the failure before the fix       | `CheckThenActTrapTest` (3) | pass   |
| Concurrency   | A real parallel test proving the invariant | `OtpConcurrencyTest` (2)   | pass   |
| Idempotency   | The same request twice gives one effect    | `OtpReplayTest` (4)        | pass   |

The parallel tests use virtual threads released together by a `CountDownLatch`. While building, the concurrency, replay and trap classes were run five more times in a row: no failures.

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.otp.OtpConcurrencyTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.otp.OtpContractTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.otp.OtpReplayTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.otp.CheckThenActTrapTest
[INFO] Tests run: 14, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tijori/otp/CheckThenActTrapTest.java`

Written first: the old limiter's race, the atomic limiter's exact 3, and the per-server limit.

#### `src/test/java/com/tijori/otp/OtpConcurrencyTest.java`

Twenty bot requests at once, and three numbers at once, through the whole app.

#### `src/test/java/com/tijori/otp/OtpReplayTest.java`

Retries, ten copies at once, a reused key, and a retry after a refusal.

#### `src/test/java/com/tijori/otp/OtpContractTest.java`

The first request, the limit with Retry-After, the window moving, and bad requests.

#### `src/test/java/com/tijori/otp/ApiTest.java`

Shared setup: a clock the tests move by hand, and empty limits before each test.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tijori/otp/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=KeyExpiryChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 14 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 16 tests pass (14 station tests and 2 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Forget keys after a day

Keys are kept forever (the `shortcut:` comment in `OtpService`). Remember each key for 24 hours, then treat it as new and free its memory.

**Done when:** the test in `KeyExpiryChallengeTest` passes.

Hints

- Store the time with each key, from the injected `Clock`.
- `map.values().removeIf(...)` drops the old ones.

#### `challenge/KeyExpiryChallengeTest.java`

``` code
package com.tijori.otp;

import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 1: an Idempotency-Key is remembered for 24 hours, then forgotten. A key seen again after that is a new
 * request (and the memory it used is freed).
 */
class KeyExpiryChallengeTest extends ApiTest {

    String requestId(String key) throws Exception {
        return JsonPath.read(otp(key, "9876543210").andReturn().getResponse().getContentAsString(), "$.requestId");
    }

    @Test
    void aKeyIsRememberedForADayThenForgotten() throws Exception {
        String first = requestId("old-key-123456");
        clock.advance(Duration.ofHours(23));
        assertThat(requestId("old-key-123456")).isEqualTo(first);
        clock.advance(Duration.ofHours(2));
        assertThat(requestId("old-key-123456")).isNotEqualTo(first);
        assertThat(sms.sentTo("9876543210")).isEqualTo(2);
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## A limit per address too

Bots rotate numbers. Also allow at most 20 requests per client address in 10 minutes, whatever the numbers, with its own `429`.

**Done when:** the test in `PerIpLimitChallengeTest` passes, and the station's tests still pass.

Hints

- Give the limiter a key and a maximum: `tryAcquire("ip:" + address, 20)`.
- Decide whether a request refused by the number limit still uses an address slot, and write the reason down.
- Behind a load balancer, the remote address is the balancer's: trust forwarded headers only from it.

#### `challenge/PerIpLimitChallengeTest.java`

``` code
package com.tijori.otp;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: bots rotate numbers. Also limit each client address to 20 OTP requests in 10 minutes, whatever the
 * numbers. Other addresses are not affected.
 */
class PerIpLimitChallengeTest extends ApiTest {

    ResultActions from(String ip, int n) throws Exception {
        return mvc.perform(post("/otp-requests").header("Idempotency-Key", "ip-test-key-" + ip.replace(".", "-") + "-" + n)
                .with(r -> { r.setRemoteAddr(ip); return r; })
                .contentType(MediaType.APPLICATION_JSON).content("{\"mobile\":\"9" + String.format("%09d", n) + "\"}"));
    }

    @Test
    void oneAddressGetsTwentyAcrossAllNumbers() throws Exception {
        for (int n = 1; n <= 20; n++) {
            from("203.0.113.9", n).andExpect(status().isAccepted());
        }
        from("203.0.113.9", 21).andExpect(status().isTooManyRequests())
                .andExpect(header().exists("Retry-After"))
                .andExpect(jsonPath("$.title").value("Too many OTP requests from this address"));
        from("198.51.100.4", 21).andExpect(status().isAccepted());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Three servers, one limit

Tijori runs three instances. Where should the count live so all three share it: a database row with a lock, an atomic counter in Valkey with an expiry, or something else? What happens to OTP requests when that store is down: refuse all, or allow and alert? Station 125 builds one answer.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: 20 requests at once through the old limiter.
2.  Make check-and-book one `compute` call; test 20 at once again: exactly 3.
3.  Add the idempotency map with a future per key; test 10 copies at once.
4.  Inject the clock; test Retry-After and the window moving.

## Design alternatives and trade-offs

| Approach                            | What it costs                                                      | Verdict                  |
|-------------------------------------|--------------------------------------------------------------------|--------------------------|
| `compute` per number                | Requests for one number take turns; others never wait.             | Chosen                   |
| `synchronized` on the whole limiter | Correct, but every number waits for every other.                   | Works, slower            |
| Check, send, then record            | Races exactly when a bot attacks.                                  | The trap                 |
| Book after the SMS succeeds         | Sounds kind to customers; reopens the race for the whole SMS call. | Wrong                    |
| A shared store (Valkey, a database) | Infrastructure, and a plan for when it is down.                    | For more than one server |

## Database design

None in this station. Across servers: an `otp_requests` table (mobile, requested_at) and a count in the same transaction with a row lock per number, or a Valkey key per number with an expiry and an atomic increment.

# 3 · Go deeper: Production

Servers  
The guarantee is "3 per number per 10 minutes per server instance". With more than one instance, the count must be shared.

Restarts  
Counts and keys live in memory: a restart forgets them, and a bot gets a fresh 3. Acceptable for a demo; not for a bank.

Secrets  
The OTP itself appears only in the SMS text. It is not in responses or logs, and the number is masked in both.

Cost  
Count 429s per number and per address; a spike is an attack, and the SMS bill is the first place it shows.

# 3 · Go deeper: Interview

## Interview takeaways

What is a check-then-act race?

Code reads a value, decides, then writes. Between the read and the write another thread does the same, so both decide on stale information.

synchronized or ConcurrentHashMap.compute?

Both make the step atomic. A synchronized method locks everything; compute locks only the entry for that key, so different numbers do not wait for each other.

How do you make a request idempotent?

The client sends a key; the server stores the result under it. A repeat returns the stored result. To cover two copies arriving at once, store a placeholder (a future) atomically before doing the work.

Why inject a Clock?

So tests can set and move time: a 10-minute window is tested in milliseconds, and Retry-After can be checked exactly.

Why is an in-memory limiter not enough?

Each server counts on its own, and restarts forget. Behind a load balancer the real limit is N times the intended one.

## Self-check rubric

| Area        | Meets the bar                       | Above the bar                                                   |
|-------------|-------------------------------------|-----------------------------------------------------------------|
| Correctness | All 14 tests pass.                  | You found all four flaws in the Review tab before opening them. |
| Concurrency | Check and book in one atomic step.  | You can say why compute beats synchronized here.                |
| Idempotency | A retry returns the first answer.   | Two copies at the same instant, too.                            |
| Explanation | Why the old limiter let 20 through. | What changes with three servers.                                |

# 3 · Go deeper: Review

## The pull request

A teammate made the limiter "kinder": customers keep their attempt when the SMS provider fails, retries are remembered once the answer is ready, Retry-After is "simpler", and numbers are accepted in any common format. The sequential tests still pass. Read both files and list every problem before opening the findings.

#### `review/OtpService.java`

``` code
package com.tijori.otp;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Service;
import org.springframework.web.ErrorResponseException;

import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;

/**
 * One OTP request: replay check, limit, SMS. Each Idempotency-Key maps to one future result, created atomically,
 * so the same request sent twice, even at the same instant, books one slot and sends one SMS.
 */
@Service
class OtpService {

    static final Duration CODE_VALID_FOR = Duration.ofMinutes(5);

    record OtpRequest(String requestId, String mobile, Instant expiresAt, int attemptsLeft) {
    }

    /** The first request with a key stores its future here; any repeat waits for that same future. */
    private record Stored(String mobile, CompletableFuture<OtpRequest> result) {
    }

    private final OtpLimiter limiter;
    private final SmsSender sms;
    private final Clock clock;
    private final SecureRandom random = new SecureRandom();
    // shortcut: keys are kept until restart; a real store expires them after a day (a table or a cache with a TTL)
    private final Map<String, Stored> byKey = new ConcurrentHashMap<>();

    OtpService(OtpLimiter limiter, SmsSender sms, Clock clock) {
        this.limiter = limiter;
        this.sms = sms;
        this.clock = clock;
    }

    OtpRequest request(String idempotencyKey, String rawMobile) {
        String mobile = normalise(rawMobile);
        Stored seen = byKey.get(idempotencyKey);
        if (seen != null) {
            if (!seen.mobile().equals(mobile)) {
                throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Idempotency key reused",
                        "This Idempotency-Key was used for a different number. Use a new key for a new request.");
            }
            return seen.result().join();
        }
        OtpRequest result = issue(mobile);
        byKey.put(idempotencyKey, new Stored(mobile, CompletableFuture.completedFuture(result)));   // remember it for retries
        return result;
    }

    private OtpRequest issue(String mobile) {
        OtpLimiter.Decision d = limiter.check(mobile);
        if (!d.accepted()) {
            long seconds = Math.max(1, (d.retryAfter().toMillis() + 999) / 1000);   // round up: never invite an early retry
            ErrorResponseException tooMany = problem(HttpStatus.TOO_MANY_REQUESTS, "Too many OTP requests",
                    "This number has had " + OtpLimiter.MAX + " OTPs in the last 10 minutes. Try again in " + seconds + " seconds.");
            tooMany.getHeaders().set(HttpHeaders.RETRY_AFTER, String.valueOf(seconds));
            throw tooMany;
        }
        String code = String.format("%06d", random.nextInt(1_000_000));
        sms.send(mobile, "Your Tijori code is " + code + ". It expires in 5 minutes. Never share it.");
        limiter.book(mobile);   // only now: if the SMS provider had failed, the customer would keep the attempt
        return new OtpRequest("otp_" + UUID.randomUUID().toString().replace("-", ""), masked(mobile),
                clock.instant().plus(CODE_VALID_FOR).truncatedTo(java.time.temporal.ChronoUnit.SECONDS), d.attemptsLeft());
    }

    /** Keeps the digits; numbers with a country code or a leading 0 are accepted too. */
    static String normalise(String raw) {
        String digits = raw.replaceAll("\\D", "");
        if (!digits.matches("\\d{10,12}")) {
            throw problem(HttpStatus.BAD_REQUEST, "Invalid mobile number", "mobile must be an Indian mobile number of 10 digits.");
        }
        return digits;
    }

    static String masked(String mobile) {
        return "XXXXXX" + mobile.substring(6);
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }

    void clear() {
        byKey.clear();
    }
}
```

#### `review/OtpLimiter.java`

``` code
package com.tijori.otp;

import org.springframework.stereotype.Component;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * At most MAX requests per number in any WINDOW (demo rule: 3 in 10 minutes). The check and the booking happen in
 * one ConcurrentHashMap.compute call, which is atomic per key: two requests for one number cannot both see "2 used"
 * and both book the third slot. Requests for different numbers do not wait for each other.
 *
 * Limit: this map lives in one server's memory. With N servers behind a load balancer, a number can get N x MAX.
 * Safe while one instance runs; across servers the count needs a shared store (station 125).
 */
@Component
class OtpLimiter {

    static final int MAX = 3;
    static final Duration WINDOW = Duration.ofMinutes(10);

    /** accepted: whether a slot was booked; attemptsLeft after this one; retryAfter until a slot frees, if refused. */
    record Decision(boolean accepted, int attemptsLeft, Duration retryAfter) {
    }

    private final Clock clock;
    private final Map<String, Deque<Instant>> windows = new ConcurrentHashMap<>();

    OtpLimiter(Clock clock) {
        this.clock = clock;
    }

    Decision tryAcquire(String mobile) {
        Instant now = clock.instant();
        Decision[] decision = new Decision[1];
        windows.compute(mobile, (m, times) -> {
            Deque<Instant> window = times == null ? new ArrayDeque<>() : times;
            while (!window.isEmpty() && !window.peekFirst().isAfter(now.minus(WINDOW))) {
                window.pollFirst();   // older than the window: no longer counts
            }
            if (window.size() >= MAX) {
                decision[0] = new Decision(false, 0, Duration.between(now, window.peekLast().plus(WINDOW)));
            } else {
                window.addLast(now);
                decision[0] = new Decision(true, MAX - window.size(), Duration.ZERO);
            }
            return window;
        });
        return decision[0];
    }

    /** Whether a request would be accepted now, without booking a slot. */
    Decision check(String mobile) {
        Instant now = clock.instant();
        Deque<Instant> window = windows.getOrDefault(mobile, new ArrayDeque<>());
        long recent = window.stream().filter(t -> t.isAfter(now.minus(WINDOW))).count();
        return recent >= MAX
                ? new Decision(false, 0, Duration.between(now, window.peekLast().plus(WINDOW)))
                : new Decision(true, (int) (MAX - recent - 1), Duration.ZERO);
    }

    /** Books a slot. Called once the SMS has actually gone out, so a failed SMS costs the customer no attempt. */
    void book(String mobile) {
        windows.compute(mobile, (m, times) -> {
            Deque<Instant> window = times == null ? new ArrayDeque<>() : times;
            window.addLast(clock.instant());
            return window;
        });
    }

    void clear() {
        windows.clear();
    }
}
```

## Findings

1The slot is booked after the SMS is sent

"A failed SMS should not cost the customer an attempt" is a kind thought, and it brings back check-then-act with a 50 ms gap: every request checks before any books.

**Test evidence:** `twentyBotRequestsAtOnceGetThreeSms` and `differentNumbersEachGetTheirOwnThree` both fail: more than 3 accepted per number.

2The replay is stored after the request completes

Sequential retries still work, so it looks fine; two copies arriving together both miss the map and both send an SMS.

**Test evidence:** `tenCopiesOfOneRequestAtTheSameInstantAreOneRequest`: more than one requestId.

3Retry-After counts from the newest request

The wait looks plausible, but it is too long: the slot frees when the oldest request leaves the window.

**Test evidence:** `retryAfterCountsFromTheOldestRequestInTheWindow`: 540 instead of 300.

4Numbers keep their +91 or leading 0

"Accept any 10 to 12 digits" makes 9876543210, 919876543210 and 09876543210 three numbers: a bot gets 9 OTPs, and a retry written with +91 looks like a different number.

**Test evidence:** `theFourthIn10MinutesIs429WithRetryAfterFromTheOldest` (2 attempts left instead of 0), `badRequestsAre400` and `aRetryWithTheSameKeyGetsTheSameAnswerAndNoSecondSms` (422).

## Same tests, flawed version

From `docs/review-run.txt`: the two flawed files copied over the real ones, then the full suite run.

| Test class             | Fixed version | Flawed version |
|------------------------|---------------|----------------|
| `CheckThenActTrapTest` | 3 / 3         | 3 / 3          |
| `OtpConcurrencyTest`   | 2 / 2         | 0 / 2          |
| `OtpContractTest`      | 5 / 5         | 2 / 5          |
| `OtpReplayTest`        | 4 / 4         | 2 / 4          |

Two of the four flaws pass every test that sends one request at a time. Only the parallel tests catch them, which is why this station has them.
