# Station 096 · Partner API keys and quotas

Working Systems · 0–2 years · Core · SaaS · Types: Security

Spring Boot 4.1.1 · Java 25 · servlet filter (OncePerRequestFilter) · token bucket · 429 Too Many Requests and Retry-After · @ConfigurationProperties · a test clock. Needs JDK 25 (or 21, see Set up & code). No database, no Docker. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows). Demo keys: Zoomkart `mw_demo_zoomkart_7Qp2Lx9V`, Chalo (trial) `mw_demo_chalo_K3vN8sT1`, Old Maps (suspended) `mw_demo_oldmaps_P0dW5yZr`.

**Simulation:** The geocoder is simulated: a fixed list of five places stands in for Mapwise's maps data. The partners and their keys are demo ones.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 13 tests.

# 1 · Understand

## The problem in real life

1.  **A loop that never stops**

    A partner's app has a bug: it calls Mapwise's geocoder again and again, 3 million times in an hour.

2.  **Everyone slows down**

    Mapwise had one limit for the whole API. The buggy partner used it all, and every other partner's requests were slow or refused.

3.  **The fix**

    Each partner gets its own bucket and its own daily quota, keyed by its API key. The buggy partner gets 429s; everyone else carries on as usual.

A limit protects others only if it belongs to the one who is over it. Count per partner, not per API.

## What are we building?

A geocoding API for partners: every request carries a key, and every partner has its own limits.

## An everyday analogy

A water tank with one tap per flat. A flat that leaves its tap open drains its own share, not the whole building's.

## How it works in 4 steps

1.  **Who**: read the key from the `X-Api-Key` header and find the partner. No key or a wrong key: `401`.
2.  **Allowed?** A suspended partner: `403`.
3.  **How much?** Take a token from that partner's bucket and count the request for the day. None left: `429` and how long to wait.
4.  **Answer**: look up the address.

Check yourself: a partner sends nothing for an hour, then 100 requests at once. How many get through with a bucket of 10 refilled at 5 a second?

10 at once (the bucket is full, but never more than its size), then about 5 a second as tokens come back. A quiet hour does not save up 18,000 requests.

## What this station is not

- **No real maps.** Five places in a list.
- **One server.** The counters live in this server's memory; with several servers each would count on its own (Production).
- **No sign-up.** Keys and plans are in configuration.

## Key terms

| Term                    | Simple meaning                                                             | Everyday example                             | In this project        |
|-------------------------|----------------------------------------------------------------------------|----------------------------------------------|------------------------|
| **API key**             | A long secret string that says which partner is calling.                   | A member card at a club's door.              | `X-Api-Key`            |
| **Rate limit**          | How many requests a partner may send in a short time.                      | A tap that only runs so fast.                | 5 a second             |
| **Token bucket**        | A bucket of tokens refilled at a steady speed; each request takes one.     | A jar of coupons refilled every few minutes. | `RateLimiter.Bucket`   |
| **Burst**               | How many requests can come at once after a quiet spell: the bucket's size. | How many coupons the jar holds.              | 10                     |
| **Quota**               | How many requests a partner may send in a whole day.                       | A monthly phone data pack.                   | 20 a day for the trial |
| **429 and Retry-After** | The answer "too many requests", with how many seconds to wait.             | "Come back in 5 minutes" on a shop door.     | `Retry-After: 1`       |

# 2 · Build: Spec

## Business problem

**Mapwise** (a fictional maps company): one partner's bug sent 3 million requests in an hour and slowed the API for everyone.

## Acceptance criteria

Demo plans: Zoomkart 5 a second, bursts of 10, 100,000 a day; Chalo (trial) 1 a second, bursts of 3, 20 a day; Old Maps suspended. Days are UTC days.

1.  **Given** a valid key and a known address, **then** `200` with the place; any case and spacing.
2.  **Given** no key, a wrong key, or a key in the URL, **then** `401`; a suspended key `403`.
3.  **Given** a full bucket, **then** a burst of its size gets through, the next is `429` with `Retry-After`, and a token comes back every 1/rate seconds.
4.  **Given** the day's quota used, **then** `429` with the seconds until 00:00 UTC; refused requests do not count.
5.  **Given** one partner over its limit, **then** other partners are not affected.
6.  **Given** another partner's id on `/usage`, **then** `403`.

## Requirements

- The key is checked and the limit applied before any controller runs.
- Two requests at once can never both take the last token.
- Keys are not stored, only their SHA-256.

## Learning objectives

- Authenticate API keys in a servlet filter and pass the caller on.
- Write a token bucket, and explain why it beats a fixed window.
- Answer `429` with a correct `Retry-After` in the RFC 9457 problem shape.
- Test time-based limits with a clock you move, and concurrency with real threads.

# 2 · Build: API contract

## Endpoints

| Method | Path                                    | Purpose                                                     |
|--------|-----------------------------------------|-------------------------------------------------------------|
| `GET`  | `/geocode?address=...` with `X-Api-Key` | Coordinates for an address.                                 |
| `GET`  | `/partners/{id}/usage` with `X-Api-Key` | The partner's plan and what is left (this call counts too). |

## Status codes

| Status | When                                                                                                   |
|--------|--------------------------------------------------------------------------------------------------------|
| 200    | Found; or the partner's usage                                                                          |
| 400    | No address, under 3 or over 200 characters, control characters; an id that is not a number             |
| 401    | No key, an unknown key, or the key in the URL                                                          |
| 403    | A suspended key; another partner's usage                                                               |
| 404    | No place for this address                                                                              |
| 429    | The partner's bucket is empty, or its day's quota is used: `Retry-After` says how many seconds to wait |

## Captured examples

Captured with curl from the running app on 23 Oct 2026, in this order. `Date`, connection and standard security headers are left out.

### Case 1: Zoomkart looks up MG Road

**Why:** `200`.

Request

``` code
GET /geocode?address=MG%20Road,%20Bengaluru HTTP/1.1
X-Api-Key: mw_demo_zoomkart_7Qp2Lx9V
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 70

{
  "address": "MG Road, Bengaluru, Karnataka",
  "lat": 12.9756,
  "lng": 77.605
}
```

### Case 2: odd case and spaces

**Why:** the same place: addresses are normalised with `Locale.ROOT`.

Request

``` code
GET /geocode?address=%20%20marine%20%20DRIVE,%20mumbai HTTP/1.1
X-Api-Key: mw_demo_zoomkart_7Qp2Lx9V
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 73

{
  "address": "Marine Drive, Mumbai, Maharashtra",
  "lat": 18.944,
  "lng": 72.823
}
```

### Case 3: an unknown address

**Why:** `404`.

Request

``` code
GET /geocode?address=Nowhere%20Lane,%20Atlantis HTTP/1.1
X-Api-Key: mw_demo_zoomkart_7Qp2Lx9V
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No place found for this address.",
  "instance": "/geocode",
  "status": 404,
  "title": "Not Found"
}
```

### Case 4: two letters

**Why:** `400`.

Request

``` code
GET /geocode?address=MG HTTP/1.1
X-Api-Key: mw_demo_zoomkart_7Qp2Lx9V
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Validation failure",
  "instance": "/geocode",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 5: no key

**Why:** `401`.

Request

``` code
GET /geocode?address=MG%20Road,%20Bengaluru HTTP/1.1
```

Response

``` code
HTTP/1.1 401 
Content-Type: application/problem+json
Content-Length: 113

{
  "title": "Unauthorized",
  "status": 401,
  "detail": "Send your API key in the X-Api-Key header.",
  "instance": "/geocode"
}
```

### Case 6: a real key in the URL

**Why:** `401`: keys in URLs end up in logs; it is refused, not read.

Request

``` code
GET /geocode?address=MG%20Road,%20Bengaluru&api_key=mw_demo_zoomkart_7Qp2Lx9V HTTP/1.1
```

Response

``` code
HTTP/1.1 401 
Content-Type: application/problem+json
Content-Length: 124

{
  "title": "Unauthorized",
  "status": 401,
  "detail": "Send the key in the X-Api-Key header, not in the URL.",
  "instance": "/geocode"
}
```

### Case 7: a suspended key

**Why:** `403`.

Request

``` code
GET /geocode?address=MG%20Road,%20Bengaluru HTTP/1.1
X-Api-Key: mw_demo_oldmaps_P0dW5yZr
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json
Content-Length: 111

{
  "title": "Forbidden",
  "status": 403,
  "detail": "This API key is suspended. Contact Mapwise.",
  "instance": "/geocode"
}
```

### Case 8: Chalo reads Zoomkart's usage

**Why:** `403`.

Request

``` code
GET /partners/1/usage HTTP/1.1
X-Api-Key: mw_demo_chalo_K3vN8sT1
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json

{
  "detail": "A key can only read its own partner's usage.",
  "instance": "/partners/1/usage",
  "status": 403,
  "title": "Forbidden"
}
```

### Case 9: Zoomkart's request after its 50

**Why:** its bucket is empty: `429`, wait a second.

Request

``` code
GET /geocode?address=MG%20Road,%20Bengaluru HTTP/1.1
X-Api-Key: mw_demo_zoomkart_7Qp2Lx9V
```

Response

``` code
HTTP/1.1 429 
Retry-After: 1
Content-Type: application/problem+json
Content-Length: 128

{
  "title": "Too Many Requests",
  "status": 429,
  "detail": "Rate limit: 5 requests a second, bursts of up to 10.",
  "instance": "/geocode"
}
```

### Case 10: Chalo, right after

**Why:** `200`: Zoomkart's bug did not touch Chalo's bucket.

Request

``` code
GET /geocode?address=Park%20Street,%20Kolkata HTTP/1.1
X-Api-Key: mw_demo_chalo_K3vN8sT1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 73

{
  "address": "Park Street, Kolkata, West Bengal",
  "lat": 22.553,
  "lng": 88.352
}
```

### Case 11: Chalo's fourth request in a second

**Why:** its own bucket holds 3: `429`.

Request

``` code
GET /geocode?address=Park%20Street,%20Kolkata HTTP/1.1
X-Api-Key: mw_demo_chalo_K3vN8sT1
```

Response

``` code
HTTP/1.1 429 
Retry-After: 1
Content-Type: application/problem+json
Content-Length: 126

{
  "title": "Too Many Requests",
  "status": 429,
  "detail": "Rate limit: 1 request a second, bursts of up to 3.",
  "instance": "/geocode"
}
```

### Case 12: Chalo's usage, a second later

**Why:** the token that came back paid for this call.

Request

``` code
GET /partners/2/usage HTTP/1.1
X-Api-Key: mw_demo_chalo_K3vN8sT1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 155

{
  "partnerId": 2,
  "partner": "Chalo Rides (trial)",
  "perSecond": 1,
  "burst": 3,
  "tokensLeft": 0,
  "dailyQuota": 20,
  "usedToday": 5,
  "quotaResetsAt": "2026-10-24T00:00:00Z"
}
```

## Zoomkart's 50 requests

Before case 9, `docs/capture.sh` sent 50 requests with Zoomkart's key one after another, as fast as curl could. Status codes counted:

``` code
200 x 13
429 x 37
```

More than 10 got through because tokens came back while the 50 ran (5 a second): the bucket at work, not a leak.

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                         | What happens                                           | Proved by                                             |
|--------------------------------------------------------------|--------------------------------------------------------|-------------------------------------------------------|
| One global limit, one buggy partner                          | Everyone refused                                       | `oneGlobalLimitLetsOnePartnersBugSlowEveryone`        |
| Per-partner buckets                                          | The buggy partner gets its 10; another is not affected | `eachPartnerHasItsOwnBucket`                          |
| A known address, any case and spacing                        | `200`, the same place                                  | `aKnownAddressIsFoundWhateverItsCaseAndSpacing`       |
| Unknown, too short, too long, missing; a trailing slash      | `404`, `400`, `404`                                    | `unknownAddressesAre404AndBadOnes400`                 |
| Usage                                                        | Plan, tokens left, used today, reset time              | `aPartnerReadsItsOwnLimitsAndWhatIsLeft`              |
| 10 at once, then 0.2 s, then a quiet minute                  | 10, then 1, then 10 again (not 300)                    | `aBurstOfTenThenOneEveryFifthOfASecond`               |
| The trial's 21st request of the day; midnight UTC            | `429` until midnight; then `200`                       | `theDailyQuotaStopsAtTwentyAndComesBackAtMidnightUtc` |
| 100 requests at the same moment                              | Exactly 10 answered                                    | `aHundredRequestsAtOnceGetExactlyTheBurst`            |
| 8 threads, 20,000 takes, a bucket of 5,000                   | Exactly 5,000                                          | `parallelTakesNeverHandOutMoreThanTheBucketHolds`     |
| No key, wrong, upper-cased, 10,000 characters, in the URL    | `401`; none counted                                    | `withoutAValidKeyInTheHeaderIt401s`                   |
| A suspended key                                              | `403`                                                  | `aSuspendedKeyIs403`                                  |
| Another partner's usage                                      | `403`                                                  | `aPartnerCannotReadAnotherPartnersUsage`              |
| CRLF, NUL, tab, 5,000 characters; SQL, paths, lookup strings | `400`; `404`                                           | `maliciousAddressesAreRefusedOrHarmless`              |

## The trap

Plausible but wrong

One global limit, so one partner's bug slows everyone.

- **The old way.** The test makes one bucket for the whole API (5 a second, bursts of 10). Zoomkart's loop sends 50 requests; Chalo's single request is then refused.
- **The API.** The same 50 from Zoomkart: 10 answered, 40 refused with `429`. Chalo's request: `200`.

While building, each part was undone once: one bucket for all partners turned 4 tests red; refused requests counted against the day 1; no daily quota 1; no cap on the refill 4; no `Retry-After` 2; the key read from the URL 1; suspended keys let in 1; any partner's usage 1; control characters allowed 1; addresses not normalised 1. Removing `synchronized` at first turned nothing red (see Tests).

``` code
package com.mapwise.geocode;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** Zoomkart's bug sends 50 requests at once. Written first. */
class GlobalLimitTrapTest extends ApiTest {

    @Test
    void oneGlobalLimitLetsOnePartnersBugSlowEveryone() {
        // The old way: one bucket for the whole API, whoever is asking.
        RateLimiter old = new RateLimiter(CLOCK);
        Partners.Partner everyone = new Partners.Partner(0, "the whole API", "-", 5, 10, 100_000, false);
        for (int i = 0; i < 50; i++) {
            old.take(everyone);   // Zoomkart's runaway loop
        }
        assertThat(old.take(everyone).allowed()).isFalse();   // Chalo's one request: refused for Zoomkart's bug
    }

    @Test
    void eachPartnerHasItsOwnBucket() throws Exception {
        List<Integer> zoomkart = new ArrayList<>();
        for (int i = 0; i < 50; i++) {
            zoomkart.add(answer(ZOOMKART));
        }
        assertThat(zoomkart).containsOnly(200, 429);
        assertThat(zoomkart.stream().filter(s -> s == 200)).hasSize(10);   // its burst, then 429 for its own bug
        assertThat(answer(CHALO)).isEqualTo(200);   // Chalo is not affected
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
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 13 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Send Chalo's trial key four times in a row:

``` code
for i in 1 2 3 4; do curl -s -o /dev/null -w '%{http_code}\n' -H 'X-Api-Key: mw_demo_chalo_K3vN8sT1' 'http://localhost:8080/geocode?address=Charminar,%20Hyderabad'; done
```

Three `200`s and a `429`. Then read `/partners/2/usage` with the same key, and send Zoomkart's key in between: it is never refused because of Chalo.

## Troubleshooting

| You see                             | Cause                                                             | Fix                                                   |
|-------------------------------------|-------------------------------------------------------------------|-------------------------------------------------------|
| Every request is 401                | The key is in the URL or misspelt; keys are exact, case included. | Send it in the `X-Api-Key` header.                    |
| 429 although you sent few requests  | The trial bucket holds 3; or the daily 20 are used.               | Read `/partners/2/usage`; wait `Retry-After` seconds. |
| A limit twice as high in production | Two servers, each with its own counters.                          | Shared counters (Production).                         |

## Project layout

``` tree
stations/096-partner-api-keys-and-quotas/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/mapwise/geocode/
│   ├── ApiKeyFilter.java   ├── RateLimiter.java   ├── Partners.java
│   ├── GeocodeController.java   ├── Geocoder.java   └── GeocodeApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/mapwise/geocode/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/mapwise/geocode/ApiKeyFilter.java`

Does  
Key, suspension and limit, before any controller.

Why  
Reads `X-Api-Key`, finds the partner by hash, refuses suspended ones, takes a token, and answers `401`, `403` or `429` in the problem shape.

Without it  
Requests without a key reaching the geocoder; one partner using everyone's capacity.

- A key in the URL is refused with a message, not read: URLs are written to access logs.
- Unknown keys never get a bucket, so random keys cost no memory.

#### `src/main/java/com/mapwise/geocode/RateLimiter.java`

Does  
A token bucket and a daily count per partner.

Why  
Refills by elapsed time, capped at the burst; takes a token; counts only answered requests; works out `Retry-After`.

Without it  
Bursts at window edges; a partner locked out for the day by its own refused retries.

- The check and the take are one synchronized step per partner: partners never wait for each other.
- Shortcut: in memory, per server. With N servers each partner gets N times the limit.

#### `src/main/java/com/mapwise/geocode/Partners.java`

Does  
Partners and plans from configuration.

Why  
Finds a partner by the SHA-256 of its key.

Without it  
Keys readable by anyone who reads the configuration.

#### `src/main/java/com/mapwise/geocode/GeocodeController.java`

Does  
The two endpoints.

Why  
Validates the address; checks the usage id against the caller.

Without it  
One partner reading another's usage.

#### `src/main/java/com/mapwise/geocode/Geocoder.java`

Simulated: five places in a map, addresses normalised with `Locale.ROOT`.

#### `src/main/resources/application.yaml`

The partners, their key hashes and plans.

#### `src/main/java/com/mapwise/geocode/GeocodeApplication.java`

Entry point, and the `Clock` the buckets refill by.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                       | Test class                                     | Result |
|---------------|-------------------------------------------------------------------|------------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                          | `GeocodeContractTest` (3), `RateLimitTest` (4) | pass   |
| Every station | Reproduce the failure before the fix                              | `GlobalLimitTrapTest` (2)                      | pass   |
| Security      | 401, 403, one user accessing another user's data, malicious input | `ApiKeySecurityTest` (4)                       | pass   |

Time stands still in the tests unless a test moves it (`TestClock`), so "0.2 s later" means exactly that, however slow the machine. Each test starts on a new day, so buckets are full and daily counts are zero without any reset hook in the app.

Found while building: with `synchronized` removed, the 100-requests-at-once test still passed in most runs: through MockMvc the requests rarely meet inside the few lines that check and take a token. A second test hits the bucket itself from 8 threads, 20,000 times, with room for 5,000: without `synchronized` it handed out more in each of three runs.

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.mapwise.geocode.RateLimitTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.mapwise.geocode.GeocodeContractTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.mapwise.geocode.ApiKeySecurityTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.mapwise.geocode.GlobalLimitTrapTest
[INFO] Tests run: 13, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/mapwise/geocode/GlobalLimitTrapTest.java`

Written first: one bucket for everyone against one per partner.

#### `src/test/java/com/mapwise/geocode/RateLimitTest.java`

Burst, refill, cap, daily quota, midnight, and two concurrency tests.

#### `src/test/java/com/mapwise/geocode/GeocodeContractTest.java`

Found, not found, bad input, usage.

#### `src/test/java/com/mapwise/geocode/ApiKeySecurityTest.java`

401, 403, another partner's usage, malicious addresses.

#### `src/test/java/com/mapwise/geocode/ApiTest.java`

Shared setup: the demo keys, a new day at 10:00 UTC before each test.

#### `src/test/java/com/mapwise/geocode/TestClock.java`

A clock moved by hand.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/mapwise/geocode/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=RemainingHeadersChallengeTest`.
3.  Change the code until it passes, then run `./mvnw test` to check the other 13 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 17 tests pass (13 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Say what is left

Every answer after the key check carries `X-RateLimit-Remaining` (whole requests left in the bucket) and `X-Quota-Remaining` (requests left today), on `200`, `404` and `429` alike. Partners can slow down before they hit the wall.

**Done when:** both tests in `RemainingHeadersChallengeTest` pass.

Hints

- Let the decision carry what is left, and set the headers in the filter.
- An IETF draft standardises `RateLimit` headers; it is still a draft, so this challenge uses the common `X-` names.

#### `challenge/RemainingHeadersChallengeTest.java`

``` code
package com.mapwise.geocode;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: tell partners what is left before they hit the wall. Every request that passes the key check gets
 * X-RateLimit-Remaining (whole requests left in the bucket) and X-Quota-Remaining (requests left today).
 */
class RemainingHeadersChallengeTest extends ApiTest {

    @Test
    void everyAnswerSaysWhatIsLeft() throws Exception {
        geocode(CHALO, "MG Road, Bengaluru").andExpect(status().isOk())
                .andExpect(header().string("X-RateLimit-Remaining", "2")).andExpect(header().string("X-Quota-Remaining", "19"));
        geocode(CHALO, "Nowhere Lane, Atlantis").andExpect(status().isNotFound())
                .andExpect(header().string("X-RateLimit-Remaining", "1")).andExpect(header().string("X-Quota-Remaining", "18"));
        geocode(CHALO, "MG Road, Bengaluru").andExpect(header().string("X-RateLimit-Remaining", "0"));
        geocode(CHALO, "MG Road, Bengaluru").andExpect(status().isTooManyRequests())
                .andExpect(header().string("X-RateLimit-Remaining", "0")).andExpect(header().string("X-Quota-Remaining", "17"));
    }

    @Test
    void noHeadersForAnUnknownKey() throws Exception {
        geocode("mw_demo_nobody", "MG Road, Bengaluru").andExpect(status().isUnauthorized())
                .andExpect(header().doesNotExist("X-RateLimit-Remaining")).andExpect(header().doesNotExist("X-Quota-Remaining"));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## A batch costs what it asks for

`POST /geocode/batch` with `{"addresses": [...]}` (1 to 10) answers each address. It costs one request per address, from the bucket and from the day: all or nothing. An invalid body costs nothing.

**Done when:** both tests in `BatchGeocodeChallengeTest` pass.

Hints

- The filter cannot know the cost before the body is read: let it skip the take for this path and the controller take *n*.
- `ErrorResponseException.getHeaders()` carries `Retry-After` on a `429` thrown from a controller.

#### `challenge/BatchGeocodeChallengeTest.java`

``` code
package com.mapwise.geocode;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /geocode/batch looks up 1 to 10 addresses at once. It costs one request per address, from the
 * bucket and from the day's quota: all or nothing.
 */
class BatchGeocodeChallengeTest extends ApiTest {

    ResultActions batch(String key, String json) throws Exception {
        return mvc.perform(post("/geocode/batch").header("X-Api-Key", key).contentType(MediaType.APPLICATION_JSON).content(json));
    }

    @Test
    void eachAddressCostsOneRequest() throws Exception {
        batch(ZOOMKART, "{\"addresses\":[\"MG Road, Bengaluru\",\"Nowhere Lane\",\"marine drive, mumbai\"]}").andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(3))
                .andExpect(jsonPath("$[0].found").value(true)).andExpect(jsonPath("$[0].place.address").value("MG Road, Bengaluru, Karnataka"))
                .andExpect(jsonPath("$[1].found").value(false)).andExpect(jsonPath("$[1].place").doesNotExist())
                .andExpect(jsonPath("$[2].place.address").value("Marine Drive, Mumbai, Maharashtra"));
        mvc.perform(get("/partners/1/usage").header("X-Api-Key", ZOOMKART)).andExpect(jsonPath("$.usedToday").value(4))   // 3 + this one
                .andExpect(jsonPath("$.tokensLeft").value(6));
    }

    @Test
    void aBatchBiggerThanWhatIsLeftIsRefusedWhole() throws Exception {
        answer(CHALO);   // 2 of its 3 left
        batch(CHALO, "{\"addresses\":[\"a b c\",\"d e f\",\"g h i\"]}").andExpect(status().isTooManyRequests())   // needs 3
                .andExpect(header().string("Retry-After", "1"));
        batch(CHALO, "{\"addresses\":[]}").andExpect(status().isBadRequest());
        batch(CHALO, "{\"addresses\":[" + "\"MG Road, Bengaluru\",".repeat(10) + "\"MG Road, Bengaluru\"]}").andExpect(status().isBadRequest());   // 11
        mvc.perform(get("/partners/2/usage").header("X-Api-Key", CHALO)).andExpect(jsonPath("$.usedToday").value(2)).andExpect(jsonPath("$.tokensLeft").value(1));   // nothing taken by the refused ones
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Six servers, one limit

Mapwise runs six copies of this API behind a load balancer. Each counts on its own, so Zoomkart really gets 30 a second. Design shared limits: what you store in Valkey (Redis) per partner, how one request takes a token atomically (a Lua script, or `INCR` with an expiry per second), what happens when Valkey is slow or down (refuse, or allow and log?), and how many milliseconds that adds to every request.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: one bucket for all against one per partner.
2.  Write the filter: key, suspension, then the limit, all before the controller.
3.  Write the bucket with a clock you can move, and test burst, refill, cap and quota.
4.  Prove the bucket under threads.

## Design alternatives and trade-offs

| Approach                    | What it costs                                                            | Verdict         |
|-----------------------------|--------------------------------------------------------------------------|-----------------|
| A token bucket per partner  | A few numbers per partner; a lock per partner.                           | Chosen          |
| One limit for the whole API | One partner's bug refuses everyone.                                      | The trap        |
| A fixed one-second window   | Twice the burst across a window edge; a second of nothing after a burst. | Review finding  |
| A sliding log of timestamps | Exact, but memory grows with the rate.                                   | Rarely worth it |
| Limits at the API gateway   | Another system to configure; no code here.                               | At larger scale |

## Database design

No database: partners and plans are configuration, counters are memory. Nothing survives a restart, which is acceptable for counters that refill in seconds; the daily quota restarts too (a demo rule). With several servers or a quota that must survive restarts, keep the counters in Valkey.

# 3 · Go deeper: Production

Several servers  
Memory counters multiply the limit by the number of servers. Use a shared store (Valkey; Redis 8 is AGPL) or limits at the gateway.

Keys  
Generate them long and random (at least 128 bits), show them once, store only a hash, let partners rotate them, and give them a prefix (`mw_live_`) so secret scanners can spot leaked ones.

Before the key check  
Unknown keys are refused before any bucket exists, but a flood of them still costs a hash each. Limit by address at the edge too.

Clients  
Tell partners to honour `Retry-After` and back off with jitter; a client that retries at once makes a 429 storm.

Monitoring  
Count 429s per partner: a sudden rise is usually a partner's bug, worth an email.

# 3 · Go deeper: Interview

## Interview takeaways

Why per-key limits rather than one global limit?

So one client's bug or abuse only affects that client. A global limit is a shared resource any one client can use up.

Token bucket or fixed window?

A token bucket: smooth refill, bursts capped at its size. A fixed window lets twice the limit through across a window edge.

What goes in a 429?

Retry-After with the seconds to wait, and a body that says which limit was hit.

Where do API keys go?

In a header. Query strings end up in access logs, proxies and browser history.

How do you store API keys?

Only a hash. Long random keys do not need a slow hash like passwords do; SHA-256 is enough.

How do you test a rate limiter?

With a clock you control, so refill is exact; and with real threads for the check-and-take.

## Self-check rubric

| Area        | Meets the bar                    | Above the bar                                                                                       |
|-------------|----------------------------------|-----------------------------------------------------------------------------------------------------|
| Correctness | All 13 tests pass.               | You ran the flawed version and explained each failure.                                              |
| Limits      | Per-key 429s.                    | A token bucket with a cap, a daily quota that only counts answered requests, a correct Retry-After. |
| Security    | Keys checked before controllers. | Keys hashed, refused in URLs, suspended keys 403.                                                   |
| Testing     | A burst test.                    | A moved clock, and a thread test that fails without the lock.                                       |

# 3 · Go deeper: Review

## The pull request

A teammate replaces the bucket with "a simpler counter per second" and moves the daily count to the top "so every request is counted". Read the file and list every problem before opening the findings.

#### `review/RateLimiter.java`

``` code
package com.mapwise.geocode;

import org.springframework.stereotype.Component;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * One window counter and one daily counter per partner, so one partner's bug only slows that partner.
 * shortcut: in this server's memory, so with N servers each partner gets N times the limit; keep the counters in a
 * shared store (Valkey) when the API runs on more than one server.
 */
@Component
class RateLimiter {

    /** allowed, or refused with the whole seconds to wait (Retry-After) and why. */
    record Decision(boolean allowed, long retryAfterSeconds, String reason) {
        static final Decision OK = new Decision(true, 0, null);
    }

    /** What a partner has left, for the usage endpoint. */
    record Usage(long tokensLeft, int usedToday, Instant quotaResetsAt) {
    }

    private final Clock clock;
    private final Map<Long, Bucket> buckets = new ConcurrentHashMap<>();   // only known partners get one: bounded

    RateLimiter(Clock clock) {
        this.clock = clock;
    }

    Decision take(Partners.Partner partner) {
        return buckets.computeIfAbsent(partner.id(), id -> new Bucket(partner, clock.instant())).take(clock.instant());
    }

    Usage usage(Partners.Partner partner) {
        return buckets.computeIfAbsent(partner.id(), id -> new Bucket(partner, clock.instant())).usage(clock.instant());
    }

    private static final class Bucket {
        private final Partners.Partner plan;
        private long windowSecond;
        private int inWindow;
        private LocalDate day;
        private int usedToday;

        Bucket(Partners.Partner plan, Instant now) {
            this.plan = plan;
            this.day = LocalDate.ofInstant(now, ZoneOffset.UTC);
        }

        /** Simpler than a bucket: count the requests in each second, at most `burst` of them. */
        synchronized Decision take(Instant now) {
            newDay(now);
            usedToday++;
            if (usedToday > plan.dailyQuota()) {
                Instant midnight = day.plusDays(1).atStartOfDay(ZoneOffset.UTC).toInstant();
                return new Decision(false, seconds(Duration.between(now, midnight)),
                        "Daily quota of " + plan.dailyQuota() + " requests used. It resets at 00:00 UTC.");
            }
            if (now.getEpochSecond() != windowSecond) {
                windowSecond = now.getEpochSecond();
                inWindow = 0;
            }
            if (inWindow >= plan.burst()) {
                return new Decision(false, 1,
                        "Rate limit: " + plan.perSecond() + (plan.perSecond() == 1 ? " request" : " requests") + " a second, bursts of up to " + plan.burst() + ".");
            }
            inWindow++;
            return Decision.OK;
        }

        synchronized Usage usage(Instant now) {
            newDay(now);
            return new Usage(now.getEpochSecond() == windowSecond ? plan.burst() - inWindow : plan.burst(), usedToday,
                    day.plusDays(1).atStartOfDay(ZoneOffset.UTC).toInstant());
        }

        private void newDay(Instant now) {
            LocalDate today = LocalDate.ofInstant(now, ZoneOffset.UTC);
            if (!today.equals(day)) {
                day = today;
                usedToday = 0;
            }
        }

        private static long seconds(Duration d) {
            return Math.max(1, (d.toMillis() + 999) / 1000);
        }
    }
}
```

## Findings

1A fixed one-second window is not a bucket

"Simpler than a bucket: count the requests in each second": and a partner can send 10 at 10:00:00.999 and 10 more at 10:00:01.000, twice the burst in a millisecond. After a burst it allows nothing until the second turns, then everything at once. The plan says 5 a second; this allows 10.

**Test evidence:** `aBurstOfTenThenOneEveryFifthOfASecond` fails: 0.2 s after the burst, the token that should be back is not.

2Refused requests are counted against the day

`usedToday++` runs before the checks, so every 429 also uses up the quota. A partner whose client retries a burst without waiting burns its whole day in seconds, and is then locked out until midnight by its own refused requests.

**Test evidence:** `theDailyQuotaStopsAtTwentyAndComesBackAtMidnightUtc` and `parallelTakesNeverHandOutMoreThanTheBucketHolds` fail: the day counts 20,000 instead of 5,000.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class            | Fixed version | Flawed version |
|-----------------------|---------------|----------------|
| `ApiKeySecurityTest`  | 4 / 4         | 4 / 4          |
| `GeocodeContractTest` | 3 / 3         | 3 / 3          |
| `GlobalLimitTrapTest` | 2 / 2         | 2 / 2          |
| `RateLimitTest`       | 4 / 4         | 1 / 4          |

The trap test passes on the flawed version: limits are still per partner. Its problems are in how the limit counts, which only tests that look at time and at refused requests can see.
