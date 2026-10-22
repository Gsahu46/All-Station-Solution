# Station 089 · App config with HTTP caching

Working Systems · 0–2 years · Core · Streaming · Types: none

Spring Boot 4.1.1 · Java 25 · ETag and If-None-Match · 304 Not Modified · Cache-Control · minimum supported app version. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The config is demo data in memory, not Streamo's, and much smaller than a real 40 KB config; the byte counts on this page are for the demo config. The endpoints in it are example addresses.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 8 tests.

# 1 · Understand

## The problem in real life

1.  **The same bytes, millions of times**

    Every launch of the Streamo app downloaded the full config: 40 KB, 20 million times a day, almost always identical to the copy already on the phone.

2.  **And no way to retire old apps**

    Old app versions with a playback bug kept being used. There was no way to tell them they must update.

3.  **The fix**

    Each answer carries a fingerprint (ETag) and a time it may be reused (max-age). The app sends its fingerprint back; if nothing changed, the answer is an empty 304. The config also says which versions must update.

Most of what a busy endpoint sends is something the client already has. Let it ask "changed?" and answer "no" for free.

## What are we building?

One endpoint: the config for a platform and an app version, with an ETag and Cache-Control, answering `304` when the app's copy is current, and telling old apps to update.

## An everyday analogy

A newspaper stand that, when you show yesterday's paper, says "there is no new edition yet" instead of selling you the same paper again.

## How it works in 4 steps

1.  **Build** the answer for this platform and version, including whether it must update.
2.  **Fingerprint** it: a hash of its JSON is the ETag.
3.  **Compare** with the app's `If-None-Match`: the same, `304` with no body; different, `200` with the new config.
4.  **Say how long** the app may keep it without asking: `max-age=300`.

Check yourself: the minimum version is 5.9.0 and the app is 5.10.0. Must it update?

No: 10 is more than 9. Compared as text, "5.10.0" sorts before "5.9.0" and the app would be wrongly forced to update: `versionsAreComparedAsNumbersNotText`.

## What this station is not

- **No CDN.** The same headers let a CDN answer for you; challenge 3 is about that.
- **No publishing API.** Config changes come from the code's demo data and the tests.
- **No real 40 KB.** The demo config is about 500 bytes; the saving is the same in proportion.

## Key terms

| Term                          | Simple meaning                                                                                               | Everyday example                            | In this project         |
|-------------------------------|--------------------------------------------------------------------------------------------------------------|---------------------------------------------|-------------------------|
| **App config**                | Settings the app downloads at launch: which features are on, where the servers are, which version is needed. | The day's menu at a restaurant.             | `GET /app-config`       |
| **ETag**                      | A short fingerprint of an answer. Same answer, same fingerprint.                                             | A version number printed on the menu.       | `ETag: "LFOu..."`       |
| **If-None-Match**             | The app sends the fingerprint it has: "only send the answer if it changed".                                  | "I have menu 12; anything new?"             | request header          |
| **304 Not Modified**          | "Nothing changed, keep yours": no body.                                                                      | "Still menu 12."                            | the answer to a match   |
| **Cache-Control: max-age**    | How long the app may reuse its copy without asking at all.                                                   | "This menu is good until lunch."            | 300 seconds (demo rule) |
| **Minimum supported version** | Apps older than this must update before they can be used.                                                    | "This card no longer works; get a new one." | `updateRequired`        |

# 2 · Build: Spec

## Business problem

**Streamo** (a fictional streaming app): 20 million app launches a day download the same 40 KB config, and old app versions need a forced update.

## Acceptance criteria

Demo config: Android latest 6.2.0, minimum 5.9.0; iOS latest 6.1.3, minimum 5.8.0. Demo rule: reuse for 5 minutes.

1.  **Given** a launch, **then** `200` with the config, an `ETag` and `Cache-Control: max-age=300, public`.
2.  **Given** `If-None-Match` with the current ETag, **then** `304`, no body, the same ETag and Cache-Control.
3.  **Given** a published change, **then** the next revalidation gets `200` and a new ETag.
4.  **Given** an app below the minimum, **then** `updateRequired: true`; versions compared as numbers.
5.  **Given** an unknown platform or a malformed version, **then** `400`.

## Requirements

- The ETag changes when the answer changes, and only then.
- Nothing in the answer changes on every request.
- A 304 repeats the caching headers.

## Learning objectives

- Use ETag and If-None-Match for conditional GETs, and get 304s from Spring.
- Choose a max-age with its cost: how late a change can arrive.
- Compare versions as numbers.
- Measure the saving instead of assuming it.

# 2 · Build: API contract

## Endpoint

| Method | Path                                             | Purpose                                                                            |
|--------|--------------------------------------------------|------------------------------------------------------------------------------------|
| `GET`  | `/app-config?platform=android|ios&version=x.y.z` | The config for this app, with caching headers. Send `If-None-Match` to revalidate. |

## Status codes

| Status | When                                                                        |
|--------|-----------------------------------------------------------------------------|
| 200    | The config: first launch, or it changed                                     |
| 304    | If-None-Match matches: keep your copy; no body                              |
| 400    | Platform not android or ios; version not three numbers; a parameter missing |

## Captured examples

Captured with curl from the running app on 22 Oct 2026, in this order. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: an app launch

**Why:** the config, its ETag, and how long it may be reused.

Request

``` code
GET /app-config?platform=android&version=6.1.0 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Cache-Control: max-age=300, public
ETag: "LFOuLmFl9BsqClJ2z7-mhN"
Content-Type: application/json

{
  "platform": "android",
  "appVersion": "6.1.0",
  "updateRequired": false,
  "updateAvailable": true,
  "latestVersion": "6.2.0",
  "minSupportedVersion": "5.9.0",
  "features": {
    "downloads": true,
    "liveSports": true,
    "watchParty": false
  },
  "homeRails": [
    "continue-watching",
    "trending-in-india",
    "new-releases",
    "cricket-live",
    "kids",
    "regional-tamil",
    "regional-telugu",
    "documentaries"
  ],
  "endpoints": {
    "api": "https://api.streamo.example",
    "images": "https://img.streamo.example",
    "player": "https://play.streamo.example"
  }
}
```

### Case 2: the next launch sends the ETag back

**Why:** unchanged: `304` with no body, and the same caching headers.

Request

``` code
GET /app-config?platform=android&version=6.1.0 HTTP/1.1
If-None-Match: "LFOuLmFl9BsqClJ2z7-mhN"
```

Response

``` code
HTTP/1.1 304 
Cache-Control: max-age=300, public
ETag: "LFOuLmFl9BsqClJ2z7-mhN"
```

### Case 3: app 5.8.9

**Why:** below 5.9.0: `updateRequired: true`. Its own ETag, since the answer differs.

Request

``` code
GET /app-config?platform=android&version=5.8.9 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Cache-Control: max-age=300, public
ETag: "UcCk2z774v-Hbfdwc_yjvt"
Content-Type: application/json

{
  "platform": "android",
  "appVersion": "5.8.9",
  "updateRequired": true,
  "updateAvailable": true,
  "latestVersion": "6.2.0",
  "minSupportedVersion": "5.9.0",
  "features": {
    "downloads": true,
    "liveSports": true,
    "watchParty": false
  },
  "homeRails": [
    "continue-watching",
    "trending-in-india",
    "new-releases",
    "cricket-live",
    "kids",
    "regional-tamil",
    "regional-telugu",
    "documentaries"
  ],
  "endpoints": {
    "api": "https://api.streamo.example",
    "images": "https://img.streamo.example",
    "player": "https://play.streamo.example"
  }
}
```

### Case 4: app 5.10.0

**Why:** compared as numbers, it is above 5.9.0.

Request

``` code
GET /app-config?platform=android&version=5.10.0 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Cache-Control: max-age=300, public
ETag: "5V22jt_OOy7O0npyKMmOHx"
Content-Type: application/json

{
  "platform": "android",
  "appVersion": "5.10.0",
  "updateRequired": false,
  "updateAvailable": true,
  "latestVersion": "6.2.0",
  "minSupportedVersion": "5.9.0",
  "features": {
    "downloads": true,
    "liveSports": true,
    "watchParty": false
  },
  "homeRails": [
    "continue-watching",
    "trending-in-india",
    "new-releases",
    "cricket-live",
    "kids",
    "regional-tamil",
    "regional-telugu",
    "documentaries"
  ],
  "endpoints": {
    "api": "https://api.streamo.example",
    "images": "https://img.streamo.example",
    "player": "https://play.streamo.example"
  }
}
```

### Case 5: If-None-Match: \*

**Why:** Spring answers `200` here; RFC 9110 (section 13.1.2) calls for `304`. Apps never send `*`, so it is left and recorded.

Request

``` code
GET /app-config?platform=android&version=6.1.0 HTTP/1.1
If-None-Match: *
```

Response

``` code
HTTP/1.1 200 
Cache-Control: max-age=300, public
ETag: "LFOuLmFl9BsqClJ2z7-mhN"
Content-Type: application/json

{
  "platform": "android",
  "appVersion": "6.1.0",
  "updateRequired": false,
  "updateAvailable": true,
  "latestVersion": "6.2.0",
  "minSupportedVersion": "5.9.0",
  "features": {
    "downloads": true,
    "liveSports": true,
    "watchParty": false
  },
  "homeRails": [
    "continue-watching",
    "trending-in-india",
    "new-releases",
    "cricket-live",
    "kids",
    "regional-tamil",
    "regional-telugu",
    "documentaries"
  ],
  "endpoints": {
    "api": "https://api.streamo.example",
    "images": "https://img.streamo.example",
    "player": "https://play.streamo.example"
  }
}
```

### Case 6: platform windows

**Why:** `400`.

Request

``` code
GET /app-config?platform=windows&version=6.1.0 HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Validation failure",
  "instance": "/app-config",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 7: version 6.1

**Why:** `400`: three numbers are expected.

Request

``` code
GET /app-config?platform=android&version=6.1 HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Validation failure",
  "instance": "/app-config",
  "status": 400,
  "title": "Bad Request"
}
```

## What 20 launches download

Measured by `docs/capture.sh` with `curl -w '%{size_download}'` on the demo config:

``` code
Body bytes: 481 for a 200, 0 for a 304. For 20 launches: 9620 without the ETag, 481 with it.
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                     | What happens                                  | Proved by                                            |
|----------------------------------------------------------|-----------------------------------------------|------------------------------------------------------|
| Below, at and above the minimum; IOS in capitals         | `updateRequired` only below                   | `theConfigTellsTheAppWhetherItMustUpdate`            |
| 5.10.0 against 5.9.0                                     | Newer: no update needed                       | `versionsAreComparedAsNumbersNotText`                |
| The same request twice; another version or platform      | The same ETag; a different one                | `theETagChangesWhenAndOnlyWhenTheAnswerChanges`      |
| A published change                                       | `200` and a new ETag on the next revalidation | `aPublishedChangeReachesAppsOnTheirNextRevalidation` |
| A weak ETag, a list, `*`, another ETag                   | `304`, `304`, `200` (Spring), `200`           | `conditionalRequestsFollowHttpRules`                 |
| Bad platform, version, missing parameter, trailing slash | `400`; `404`                                  | `badQueriesAre400`                                   |

## The trap

Plausible but wrong

No ETag or Cache-Control, so every launch downloads the same config.

- **The old way.** The test launches the app 20 times without an ETag to send: 20 full downloads of the same bytes.
- **With the ETag.** The first launch downloads the config and keeps the ETag; the next 19 send it back and get `304` with an empty body. One download in 20.

While building, each part was undone once: no ETag turned 4 tests red; no Cache-Control 2; a fixed ETag that never changes 3; versions compared as text 1; the platform not lower-cased 1; `<=` instead of `<` for the minimum 1.

``` code
package com.streamo.config;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletResponse;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Written first. The old endpoint sent no ETag and no Cache-Control: every app launch downloaded the whole config
 * again, the same bytes each time. These tests count the bytes 20 launches download.
 */
class EveryLaunchDownloadsTrapTest extends ApiTest {

    @Test
    void anAppThatCannotRevalidateDownloadsEverythingEveryTime() throws Exception {
        long bytes = 0;
        for (int launch = 0; launch < 20; launch++) {
            bytes += ask("android", "6.1.0", null).getContentAsByteArray().length;   // the old app: no If-None-Match to send
        }
        int one = ask("android", "6.1.0", null).getContentAsByteArray().length;
        assertThat(one).isGreaterThan(400);
        assertThat(bytes).isEqualTo(20L * one);
    }

    @Test
    void anAppThatKeepsTheETagDownloadsOnceAndThenGets304s() throws Exception {
        MockHttpServletResponse first = ask("android", "6.1.0", null);
        String etag = first.getHeader("ETag");
        assertThat(etag).matches("\"[A-Za-z0-9_-]{22}\"");
        assertThat(first.getHeader("Cache-Control")).isEqualTo("max-age=300, public");
        long bytes = first.getContentAsByteArray().length;
        for (int launch = 1; launch < 20; launch++) {
            MockHttpServletResponse again = ask("android", "6.1.0", etag);
            assertThat(again.getStatus()).isEqualTo(304);
            bytes += again.getContentAsByteArray().length;
        }
        assertThat(bytes).isEqualTo(first.getContentAsByteArray().length);   // 19 launches downloaded nothing
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
./mvnw test                 # all 8 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Download once, then revalidate with the ETag you got, and compare the sizes:

``` code
U='http://localhost:8080/app-config?platform=android&version=6.1.0'
ETAG=$(curl -s -i "$U" | tr -d '\r' | sed -n 's/^ETag: //p')
curl -s -o /dev/null -w '%{http_code} %{size_download} bytes\n' "$U"
curl -s -o /dev/null -w '%{http_code} %{size_download} bytes\n' "$U" -H "If-None-Match: $ETAG"
```

The first prints `200` and the size of the config, the second `304 0 bytes`: the numbers in `docs/captures/bytes.txt` come from the same two requests.

## Troubleshooting

| You see                                   | Cause                                                                                              | Fix                                                                |
|-------------------------------------------|----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| Never a `304`                             | Something in the answer changes on every request (a timestamp, a random id), so the ETag does too. | Keep per-request values out of cached answers; see the Review tab. |
| A `304` without Cache-Control             | The headers were set only on the `200` path.                                                       | Set them on the `ResponseEntity` and let Spring answer the `304`.  |
| Apps forced to update that are new enough | Versions compared as text.                                                                         | Compare number by number, as `AppVersion` does.                    |

## Project layout

``` tree
stations/089-app-config-with-http-caching/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/streamo/config/
│   ├── AppConfigController.java   ├── AppVersion.java   ├── AppConfigs.java   └── AppConfigApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/streamo/config/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/streamo/config/AppConfigController.java`

Does  
The endpoint.

Why  
Builds the answer, hashes its JSON into an ETag, sets Cache-Control, and lets Spring answer `304` when If-None-Match matches.

Without it  
Every launch downloading the same bytes.

- Spring compares If-None-Match with the ETag of a `ResponseEntity` by itself, weakly, and keeps Cache-Control on the `304`. Found while building: no `checkNotModified` code was needed.
- Maps are sorted (`TreeMap`) so the same config always gives the same JSON, and the same ETag.

#### `src/main/java/com/streamo/config/AppVersion.java`

Does  
An app version, compared number by number.

Why  
Three integers, compared in order.

Without it  
5.10.0 treated as older than 5.9.0.

#### `src/main/java/com/streamo/config/AppConfigs.java`

The published config per platform, demo data in memory; `publish` stands for an operator publishing a change.

#### `src/main/resources/application.yaml`

Problem details for errors.

#### `src/main/java/com/streamo/config/AppConfigApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                              | Test class                         | Result |
|---------------|------------------------------------------|------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found | `AppConfigContractTest` (6)        | pass   |
| Every station | Reproduce the failure before the fix     | `EveryLaunchDownloadsTrapTest` (2) | pass   |

`conditionalRequestsFollowHttpRules` records one place where Spring differs from RFC 9110: `If-None-Match: *` gets `200`. It was first written expecting `304` and failed; the running app answers the same (case 5). Found while building.

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.streamo.config.AppConfigContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.streamo.config.EveryLaunchDownloadsTrapTest
[INFO] Tests run: 8, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/streamo/config/EveryLaunchDownloadsTrapTest.java`

Written first: bytes for 20 launches, without and with the ETag.

#### `src/test/java/com/streamo/config/AppConfigContractTest.java`

The answer, versions, ETags, publishing, conditional rules, bad queries.

#### `src/test/java/com/streamo/config/ApiTest.java`

Shared setup: the demo config before each test, request helpers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/streamo/config/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=RolloutBucketChallengeTest`. The Last-Modified test needs a `Clock` bean before it starts.
3.  Change the code until it passes, then run `./mvnw test` to check the other 8 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 11 tests pass (8 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Last-Modified

Each answer carries `Last-Modified`: when its platform's config was published, to the second. `If-Modified-Since` with that date (and no If-None-Match) gets `304` until the next publish.

**Done when:** the test in `LastModifiedChallengeTest` passes.

Hints

- Record the publish time with a `Clock`, cut to seconds: HTTP dates have no fractions.
- `ResponseEntity.ok().lastModified(...)`; Spring checks If-Modified-Since too.

#### `challenge/LastModifiedChallengeTest.java`

``` code
package com.streamo.config;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.test.context.bean.override.convention.TestBean;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 1: Last-Modified. Each answer says when its platform's config was published; an app that sends
 * If-Modified-Since with that date (and no If-None-Match) gets 304 until the next publish.
 */
class LastModifiedChallengeTest extends ApiTest {

    static volatile Instant now = Instant.parse("2026-10-22T10:00:00Z");

    @TestBean
    Clock clock;

    static Clock clock() {
        return new Clock() {
            public ZoneId getZone() {
                return ZoneOffset.UTC;
            }

            public Clock withZone(ZoneId zone) {
                return this;
            }

            public Instant instant() {
                return now;
            }
        };
    }

    MockHttpServletResponse since(String date) throws Exception {
        return mvc.perform(config("android", "6.1.0").header("If-Modified-Since", date)).andReturn().getResponse();
    }

    @Test
    void anUnchangedConfigIs304ByDateAndAPublishMakesIt200() throws Exception {
        now = Instant.parse("2026-10-22T10:00:00Z");
        configs.reset();   // published at 10:00 UTC
        MockHttpServletResponse first = mvc.perform(config("android", "6.1.0")).andReturn().getResponse();
        assertThat(first.getHeader("Last-Modified")).isEqualTo("Thu, 22 Oct 2026 10:00:00 GMT");
        assertThat(since("Thu, 22 Oct 2026 10:00:00 GMT").getStatus()).isEqualTo(304);
        now = Instant.parse("2026-10-22T11:30:00Z");
        configs.publish("android", configs.get("android"));   // republished at 11:30
        MockHttpServletResponse after = since("Thu, 22 Oct 2026 10:00:00 GMT");
        assertThat(after.getStatus()).isEqualTo(200);
        assertThat(after.getHeader("Last-Modified")).isEqualTo("Thu, 22 Oct 2026 11:30:00 GMT");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## A 10% rollout that stays cacheable

The app sends `bucket=0..99`, stable per install. Demo rule: `watchParty` is on for buckets 0 to 9. Installs on the same side of the rollout share one ETag.

**Done when:** both tests in `RolloutBucketChallengeTest` pass.

Hints

- Let only "in or out" reach the answer, never the bucket number itself.
- `@Min(0) @Max(99)` on an optional `Integer` parameter.

#### `challenge/RolloutBucketChallengeTest.java`

``` code
package com.streamo.config;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: a gradual rollout. The app sends bucket=0..99 (from a hash of its install id, stable per install).
 * Demo rule: watchParty is on for buckets 0 to 9 (10%). Answers depend on whether the bucket is in, not on the bucket
 * itself, so all installs on the same side share one ETag and caches stay useful.
 */
class RolloutBucketChallengeTest extends ApiTest {

    @Test
    void tenPercentGetTheFeature() throws Exception {
        mvc.perform(config("android", "6.1.0").param("bucket", "5")).andExpect(status().isOk()).andExpect(jsonPath("$.features.watchParty").value(true));
        mvc.perform(config("android", "6.1.0").param("bucket", "10")).andExpect(jsonPath("$.features.watchParty").value(false));
        mvc.perform(config("android", "6.1.0")).andExpect(jsonPath("$.features.watchParty").value(false));
        mvc.perform(config("android", "6.1.0").param("bucket", "100")).andExpect(status().isBadRequest());
    }

    @Test
    void bucketsOnTheSameSideShareOneETag() throws Exception {
        String in3 = mvc.perform(config("android", "6.1.0").param("bucket", "3")).andReturn().getResponse().getHeader("ETag");
        String in7 = mvc.perform(config("android", "6.1.0").param("bucket", "7")).andReturn().getResponse().getHeader("ETag");
        String out50 = mvc.perform(config("android", "6.1.0").param("bucket", "50")).andReturn().getResponse().getHeader("ETag");
        String none = mvc.perform(config("android", "6.1.0")).andReturn().getResponse().getHeader("ETag");
        assertThat(in3).isEqualTo(in7);
        assertThat(out50).isEqualTo(none).isNotEqualTo(in3);
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## A CDN in front, and an urgent update

Put a CDN in front of `/app-config`. With `max-age=300, public`, what does it store, and how many requests still reach the app? Now a security bug means 6.1.x must update today: how quickly can a new minimum reach every phone, and what do you add (a shorter max-age, a purge, `stale-while-revalidate`) to make it faster?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: bytes for 20 launches.
2.  Build a deterministic answer (sorted maps, no per-request values).
3.  Hash it into an ETag; set Cache-Control; let Spring answer If-None-Match.
4.  Compare versions as numbers for `updateRequired`.

## Design alternatives and trade-offs

| Approach                                 | What it costs                                                                         | Verdict                     |
|------------------------------------------|---------------------------------------------------------------------------------------|-----------------------------|
| ETag from a hash of the answer + max-age | The answer is built and hashed for each request, even for a 304.                      | Chosen                      |
| No caching headers                       | Every launch downloads everything.                                                    | The trap                    |
| ETag from a config version number        | No hashing; the answer must then depend only on that version.                         | Faster, easier to get wrong |
| `ShallowEtagHeaderFilter`                | One line; hashes every response in the app, including ones that should not be cached. | Broad                       |
| A long max-age, no revalidation          | Fewest requests; a change or forced update arrives late.                              | Review finding              |

## Database design

This station has no database: the config is demo data in memory. With a table behind it, an `updated_at` or version column could give Last-Modified (challenge 1) or the ETag without building the answer.

# 3 · Go deeper: Production

max-age is a delay  
Every minute of max-age is a minute a change may take to arrive. Pick it with the forced-update case in mind.

CDNs and gzip  
A CDN can answer revalidations for you. Compression changes the bytes; CDNs often turn a strong ETag weak, which If-None-Match still matches.

Measure  
Count `304`s against `200`s; a sudden drop in `304`s means something in the answer started changing per request.

Clients  
Mobile HTTP clients revalidate only if they keep a cache: make sure the app's HTTP client has one, or stores and sends the ETag itself.

# 3 · Go deeper: Interview

## Interview takeaways

What does an ETag do?

It identifies one version of an answer. The client sends it back in If-None-Match; if it still matches, the server answers 304 with no body.

max-age or ETag?

Both: max-age says how long the client may skip asking; the ETag makes asking cheap afterwards.

What breaks ETags?

Anything in the answer that changes per request: timestamps, request ids, unordered maps.

Strong or weak ETags?

Strong means byte-for-byte equal; weak means equivalent. If-None-Match compares weakly, so both give 304s.

How do you force old apps to update?

Send the minimum supported version (or a flag) in the config, compare versions as numbers, and keep max-age short enough for the update to arrive in time.

## Self-check rubric

| Area        | Meets the bar         | Above the bar                                                    |
|-------------|-----------------------|------------------------------------------------------------------|
| Correctness | All 8 tests pass.     | You ran the flawed version and explained each failure.           |
| Caching     | ETag and 304.         | Cache-Control on the 304 too; nothing per-request in the answer. |
| Versions    | updateRequired works. | Compared as numbers, with the 5.10 case tested.                  |
| Evidence    | It caches.            | You measured the bytes before and after.                         |

# 3 · Go deeper: Review

## The pull request

A teammate adds `serverTime` to the config, so apps can warn users whose phone clock is wrong, and raises max-age to a day, since the config rarely changes. Read the file and list every problem before opening the findings.

#### `review/AppConfigController.java`

``` code
package com.streamo.config;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.databind.json.JsonMapper;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;

@RestController
class AppConfigController {

    record AppConfig(String platform, String appVersion, boolean updateRequired, boolean updateAvailable, String latestVersion,
                     String minSupportedVersion, Map<String, Boolean> features, List<String> homeRails, Map<String, String> endpoints,
                     Instant serverTime) {
    }

    /** The config rarely changes, so apps may keep it for a day: far fewer requests. */
    static final CacheControl CACHE = CacheControl.maxAge(Duration.ofDays(1)).cachePublic();

    private final AppConfigs configs;
    private final JsonMapper json;

    AppConfigController(AppConfigs configs, JsonMapper json) {
        this.configs = configs;
        this.json = json;
    }

    /**
     * The ETag is a hash of the answer's JSON, so it changes when, and only when, the answer changes. Spring compares
     * it with the app's If-None-Match and, if they match, answers 304 with no body: the app keeps the copy it has.
     */
    @GetMapping("/app-config")
    ResponseEntity<AppConfig> config(@RequestParam @NotNull @Pattern(regexp = "(?i)android|ios") String platform,
                                     @RequestParam @NotNull @Pattern(regexp = "\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}") String version) {
        String p = platform.toLowerCase(Locale.ROOT);
        AppConfigs.Published c = configs.get(p);
        AppVersion app = AppVersion.parse(version);
        AppConfig body = new AppConfig(p, app.toString(), app.compareTo(AppVersion.parse(c.minSupportedVersion())) < 0,
                app.compareTo(AppVersion.parse(c.latestVersion())) < 0, c.latestVersion(), c.minSupportedVersion(),
                new TreeMap<>(c.features()), c.homeRails(), new TreeMap<>(c.endpoints()),
                Instant.now());   // apps compare it with the phone's clock to warn about a wrong time
        return ResponseEntity.ok().eTag(etag(json.writeValueAsBytes(body))).cacheControl(CACHE).body(body);
    }

    static String etag(byte[] bytes) {
        try {
            byte[] hash = MessageDigest.getInstance("SHA-256").digest(bytes);
            return "\"" + Base64.getUrlEncoder().withoutPadding().encodeToString(hash).substring(0, 22) + "\"";
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }
}
```

## Findings

1A timestamp in a cached answer

"Apps compare serverTime with the phone's clock" is useful, but it makes every answer different. The ETag changes on every request, no app ever gets a `304`, and every launch downloads everything again: the original problem, back.

**Test evidence:** `anAppThatKeepsTheETagDownloadsOnceAndThenGets304s`, `theETagChangesWhenAndOnlyWhenTheAnswerChanges` and `conditionalRequestsFollowHttpRules` fail.

2A one-day max-age

"Far fewer requests": also a day before a raised minimum version, a turned-off feature or a moved server reaches the apps that already have a copy.

**Test evidence:** The Cache-Control checks in the same tests fail; the cost shows only on the day an update is urgent.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class                     | Fixed version | Flawed version |
|--------------------------------|---------------|----------------|
| `AppConfigContractTest`        | 6 / 6         | 4 / 6          |
| `EveryLaunchDownloadsTrapTest` | 2 / 2         | 1 / 2          |

Every request still gets a correct config, so nothing looks broken in the app. The cost shows on the bandwidth bill, and on the day an update cannot wait.
