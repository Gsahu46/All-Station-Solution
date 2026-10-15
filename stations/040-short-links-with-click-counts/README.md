# Station 040 · Short links with click counts

Foundations · 0–1 years · Core · SaaS · Types: Database, Concurrency

Spring Boot 4.1.1 · Java 25 · base62 codes · PostgreSQL 17 ON CONFLICT · 302 redirects · LongAdder + @Scheduled flush · virtual threads · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Links and campaigns are demo data, not Chhotu's. No SMS is sent; the short links point at example addresses.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 16 tests.

# 1 · Understand

## The problem in real life

1.  **Long links in SMS**

    Marketing pastes 300-character tracking links into SMS. Chhotu shortens them to a few characters.

2.  **Two campaigns, one code**

    Codes were 4 random characters, saved with "update if it exists, else insert". A new campaign drew a code already in use, and the Diwali sale's link quietly started opening the phone launch. Lakhs of SMS were already out.

3.  **The fix**

    Seven-character codes, a primary key on the code, and a retry when it is taken. A taken code is refused, never overwritten. Clicks are counted in memory so redirects stay fast.

Random is not unique. The database's key makes it unique.

## What are we building?

`POST /links` shortens a URL. `GET /{code}` sends the visitor on and counts the click, and `GET /links/{code}/stats` shows the count.

## An everyday analogy

A coat check. You get a token; the attendant never gives out a token that is already on a hook. If the number they pick is taken, they pick another. They do not take the coat that is there off the hook.

## How it works in 4 steps

1.  **Pick a random code** of 7 base62 characters.
2.  **Insert it**; if the code is taken, the database inserts nothing, and we try another.
3.  **On a click**, look up the target, add one to a counter in memory, and answer 302.
4.  **Every 5 seconds**, write the counted clicks to the database.

Check yourself: why not answer 301, which browsers remember, so repeat clicks are faster?

Because they are remembered: later clicks never reach us, so they are never counted, and the link's destination can never be changed. A short link for a campaign needs both.

## What this station is not

- **No SMS.** Links only.
- **No accounts.** Anyone can create a link; a real service needs owners and abuse checks.
- **One app instance for counting.** Stats include this instance's unflushed clicks; challenge 3 covers many servers.

## Key terms

| Term                  | Simple meaning                                                        | Everyday example                                                  | In this project                 |
|-----------------------|-----------------------------------------------------------------------|-------------------------------------------------------------------|---------------------------------|
| **Short link**        | A short address that redirects to a long one.                         | A token number that stands for a long address.                    | `http://localhost:8080/k9Qz7Ab` |
| **Base62**            | Digits 0–9, A–Z and a–z: 62 symbols, so short codes hold many values. | Number plates using letters and digits.                           | `CodeGenerator`                 |
| **Collision**         | Two links getting the same random code.                               | Two people drawing the same raffle ticket.                        | the trap                        |
| **302 and 301**       | Redirects: 302 says "for now", 301 says "forever, remember it".       | A temporary diversion sign vs a new road on the map.              | `follow`                        |
| **Buffered counting** | Count in memory, write the totals every few seconds.                  | A tally on paper, entered in the register at the end of the hour. | `ClickCounter`                  |
| **Birthday problem**  | Repeats among random picks come much sooner than intuition says.      | 23 people: 50% chance two share a birthday.                       | `chanceOfARepeat`               |

# 2 · Build: Spec

## Business problem

**Chhotu** (a fictional link shortener) serves marketing teams who paste 300-character tracking links into SMS. Two campaigns got the same short code, and one overwrote the other.

## Acceptance criteria

1.  **Given** a long URL, **then** `201` with a 7-character base62 code and a short URL; the same URL again gets a new code.
2.  **Given** a code that is already taken, **then** another code is tried; the existing link is never changed. If 5 attempts all collide, `503`.
3.  **Given** a click, **then** `302` to the target, and the click is counted.
4.  **Given** 1,000 clicks at the same moment, **then** the count is 1,000, including clicks that arrive during a flush.
5.  **Given** `javascript:`, `data:`, `ftp:` or an address without a host, **then** `400`.
6.  **Given** an unknown code, `404`.

## Requirements

- The code is the primary key; a collision is never resolved by overwriting.
- Only http and https targets, checked in Java and by a constraint.
- A redirect never waits for a database write.
- Codes are case-sensitive: in base62, `a` and `A` are different digits, so codes are never normalised.

## Learning objectives

- Generate base62 codes and reason about collisions.
- Use a unique key with `ON CONFLICT DO NOTHING` and retry.
- Choose between 301 and 302.
- Count high-volume events without slowing the request.

# 2 · Build: API contract

## Endpoints

| Method | Path                  | Purpose                                     |
|--------|-----------------------|---------------------------------------------|
| `POST` | `/links`              | `{"targetUrl"}`: a new short link.          |
| `GET`  | `/{code}`             | `302` to the target, and one click counted. |
| `GET`  | `/links/{code}/stats` | The target and the click count.             |

## Status codes

| Status | When                                                                                   |
|--------|----------------------------------------------------------------------------------------|
| 201    | A link was created                                                                     |
| 302    | Following a link                                                                       |
| 400    | Not an http or https address, blank, longer than 2,048 characters, or an unknown field |
| 404    | No such code                                                                           |
| 503    | Every attempt drew a taken code; try again                                             |

## Captured examples

Captured with curl from the running app on 15 Oct 2026, in this order, against one fresh database. curl does not follow redirects here, so the `302` and its `Location` are visible. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: a 109-character campaign link

**Why:** a random 7-character code; `Location` is the short URL.

Request

``` code
POST /links HTTP/1.1
Content-Type: application/json

{
  "targetUrl": "https://shop.example/diwali-sale?utm_source=sms&utm_medium=bulk&utm_campaign=diwali2026&utm_content=variant-b"
}
```

Response

``` code
HTTP/1.1 201 
Location: http://localhost:8080/bMOWE17
Content-Type: application/json

{
  "code": "bMOWE17",
  "shortUrl": "http://localhost:8080/bMOWE17",
  "targetUrl": "https://shop.example/diwali-sale?utm_source=sms&utm_medium=bulk&utm_campaign=diwali2026&utm_content=variant-b"
}
```

### Case 2: a tap

**Why:** `302` to the long URL; the click is counted in memory.

Request

``` code
GET /bMOWE17 HTTP/1.1
```

Response

``` code
HTTP/1.1 302 
Location: https://shop.example/diwali-sale?utm_source=sms&utm_medium=bulk&utm_campaign=diwali2026&utm_content=variant-b
Content-Length: 0
```

### Case 3: another tap

**Why:** 302 again: browsers do not cache it, so every click reaches us.

Request

``` code
GET /bMOWE17 HTTP/1.1
```

Response

``` code
HTTP/1.1 302 
Location: https://shop.example/diwali-sale?utm_source=sms&utm_medium=bulk&utm_campaign=diwali2026&utm_content=variant-b
Content-Length: 0
```

### Case 4: the stats

**Why:** 2 clicks: stored clicks plus those not yet written.

Request

``` code
GET /links/bMOWE17/stats HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 195

{
  "code": "bMOWE17",
  "targetUrl": "https://shop.example/diwali-sale?utm_source=sms&utm_medium=bulk&utm_campaign=diwali2026&utm_content=variant-b",
  "clicks": 2,
  "createdAt": "2026-10-15T09:29:24.232891Z"
}
```

### Case 5: zzzzzzz

**Why:** `404`.

Request

``` code
GET /zzzzzzz HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No short link zzzzzzz.",
  "instance": "/zzzzzzz",
  "status": 404,
  "title": "Link not found"
}
```

### Case 6: a javascript: URL

**Why:** a short link would hide it: `400`.

Request

``` code
POST /links HTTP/1.1
Content-Type: application/json

{
  "targetUrl": "javascript:alert(document.cookie)"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "targetUrl must be an http or https address with a host.",
  "instance": "/links",
  "status": 400,
  "title": "Not a web address"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                            | What happens                                       | Proved by                                                       |
|---------------------------------------------------------------------------------|----------------------------------------------------|-----------------------------------------------------------------|
| A forced collision                                                              | Another code is tried; the first link is untouched | `nowACollisionIsRetriedAndTheFirstLinkIsUntouched`              |
| Every attempt collides                                                          | `503`; nothing overwritten                         | `whenEveryAttemptCollidesNothingIsOverwrittenAndTheAnswerIs503` |
| Codes differing only in case                                                    | Two different links                                | `codesDifferingOnlyInCaseAreDifferentLinks`                     |
| 1,000 clicks at once                                                            | 1,000 counted                                      | `aThousandClicksAtOnceAreAThousandClicks`                       |
| 2,000 clicks while flushes run                                                  | 2,000 stored                                       | `clicksArrivingDuringAFlushAreKeptForTheNextOne`                |
| 200 first clicks on each of 50 new links                                        | 200 each                                           | `theFirstClicksOnANewLinkAreNotLost`                            |
| 200 links created at once                                                       | 200 different codes                                | `twoHundredLinksAtOnceGetTwoHundredCodes`                       |
| Duplicate code, bad code, javascript: target, negative clicks, written directly | Refused by named constraints                       | `namedConstraintsHoldWithoutJava`                               |
| javascript:, data:, ftp:, no host, not a URL; too long; extra field             | `400`                                              | `LinkContractTest`                                              |

## The trap

Plausible but wrong

Random codes without a unique constraint, so collisions overwrite links.

The old store saves the Diwali link, then a launch link that drew the same code: the Diwali link now opens the launch. The birthday problem shows why it happened so soon. Among 5,000 four-character codes, the chance of at least one repeat is about 57%. With seven characters and 1 lakh links, it is under 0.2%, which is rare but still not never. That is why the key, not the length, is the fix. With the code forced to repeat, the real store tries another code and leaves the first link alone. While building, each fix was undone once. A non-atomic flush (`sum()` then `reset()`) turned 1 test red. A race when creating a new link's counter turned 1 red, but only after a test called the counter directly from 200 threads; through HTTP the requests were too spread out to hit it. No retry turned 1 red, and an upsert that overwrites 2.

``` code
package com.chhotu.links;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;
import static org.mockito.Mockito.when;

/** The first test written for this station: two campaigns, one code. The generator is forced to repeat itself. */
class OverwritingCodesTrapTest extends ApiTest {

    @MockitoBean
    CodeGenerator codes;

    @Test
    void theOldSaveLetTheSecondCampaignTakeOverTheFirstOnesLink() {
        OldLinkStore.createTable(jdbc);
        OldLinkStore.save(jdbc, "k9Qz", "https://shop.example/diwali-sale?utm_campaign=diwali");
        OldLinkStore.save(jdbc, "k9Qz", "https://shop.example/new-phones?utm_campaign=launch");   // same random code
        // Every SMS already sent for the Diwali sale now opens the phone launch.
        assertThat(OldLinkStore.target(jdbc, "k9Qz")).endsWith("utm_campaign=launch");
    }

    @Test
    void fourCharactersMadeARepeatLikelyWithinAFewThousandLinks() {
        assertThat(OldLinkStore.chanceOfARepeat(5_000, Math.pow(62, 4))).isCloseTo(0.57, within(0.01));
        assertThat(OldLinkStore.chanceOfARepeat(100_000, Math.pow(62, 7))).isLessThan(0.002);   // rare, still not never
    }

    @Test
    void nowACollisionIsRetriedAndTheFirstLinkIsUntouched() {
        when(codes.next()).thenReturn("Diwali1", "Diwali1", "Launch2");
        String first = links.create("https://shop.example/diwali-sale").orElseThrow();
        String second = links.create("https://shop.example/new-phones").orElseThrow();
        assertThat(first).isEqualTo("Diwali1");
        assertThat(second).isEqualTo("Launch2");
        assertThat(targetOf("Diwali1")).isEqualTo("https://shop.example/diwali-sale");
    }
}
```

``` code
package com.chhotu.links;

import org.springframework.jdbc.core.simple.JdbcClient;

/**
 * The link store before the fix, kept only in tests: 4-character codes, a table with no key on the code, and a
 * "save" that updates the row if the code exists, else inserts. A collision silently replaces the earlier link.
 */
final class OldLinkStore {

    private OldLinkStore() {
    }

    static void createTable(JdbcClient jdbc) {
        jdbc.sql("DROP TABLE IF EXISTS old_links").update();
        jdbc.sql("CREATE TABLE old_links (code VARCHAR(4), target_url TEXT)").update();   // no primary key, no unique
    }

    static void save(JdbcClient jdbc, String code, String targetUrl) {
        int updated = jdbc.sql("UPDATE old_links SET target_url = ? WHERE code = ?").params(targetUrl, code).update();
        if (updated == 0) {
            jdbc.sql("INSERT INTO old_links (code, target_url) VALUES (?, ?)").params(code, targetUrl).update();
        }
    }

    static String target(JdbcClient jdbc, String code) {
        return jdbc.sql("SELECT target_url FROM old_links WHERE code = ?").param(code).query(String.class).single();
    }

    /** The birthday problem: chance that n random codes out of `space` contain at least one repeat. */
    static double chanceOfARepeat(long n, double space) {
        return 1 - Math.exp(-(double) n * (n - 1) / (2 * space));
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
./mvnw test                 # all 16 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Create a link, open the short URL in a browser a few times, then compare the stats with the database before and after 5 seconds:

``` code
curl -X POST http://localhost:8080/links -H "Content-Type: application/json" -d '{"targetUrl":"https://example.com"}'
curl http://localhost:8080/links/<code>/stats
docker compose exec postgres psql -U chhotu -d chhotu -c "SELECT code, clicks FROM links"
```

The stats count every click at once; the table catches up at the next flush.

## Troubleshooting

| You see                                                 | Cause                                                      | Fix                                                          |
|---------------------------------------------------------|------------------------------------------------------------|--------------------------------------------------------------|
| The browser stops hitting the app after the first click | A 301 was cached (from another service or an old version). | Clear the browser cache; this app answers 302.               |
| Clicks in the table lag behind the stats                | Buffered clicks are written every 5 seconds.               | Expected. Lower `chhotu.clicks.flush-ms` to see them sooner. |
| `Could not find a valid Docker environment`             | Docker is not running.                                     | Start Docker, then run the tests again.                      |

## Project layout

``` tree
stations/040-short-links-with-click-counts/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/chhotu/links/
│   ├── LinkController.java   ├── LinkStore.java   ├── ClickCounter.java
│   ├── CodeGenerator.java    └── LinksApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__links.sql
├── src/test/java/com/chhotu/links/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the pieces it uses.

#### `src/main/java/com/chhotu/links/LinkController.java`

Does  
Creates links, redirects with 302, and shows stats.

Why  
Only web addresses are accepted, and a redirect does nothing slow.

Without it  
301 (clicks stop reaching us), or any URI (a short link hiding `javascript:`).

#### `src/main/java/com/chhotu/links/LinkStore.java`

Does  
Inserts with a random code, retrying when it is taken.

Why  
`ON CONFLICT (code) DO NOTHING`: a taken code inserts 0 rows and touches nothing.

Without it  
The trap: "update if it exists", which turns a collision into an overwrite.

#### `src/main/java/com/chhotu/links/ClickCounter.java`

Does  
Counts clicks in memory and writes them every few seconds.

Why  
A `LongAdder` per link: many threads add without waiting; `sumThenReset` keeps clicks that arrive during a flush.

Without it  
An `UPDATE … clicks + 1` per click: every click on a hot link waits for the same row lock.

- The limit: clicks not yet flushed are lost if the process crashes; a clean shutdown flushes first (`@PreDestroy`).

#### `src/main/java/com/chhotu/links/CodeGenerator.java`

Does  
Seven random base62 characters from `SecureRandom`.

Why  
Unpredictable, so one link's code says nothing about the next.

Without it  
Sequential codes: anyone can walk through every link.

#### `src/main/resources/db/migration/V1__links.sql`

Does  
The links table and its named constraints.

Why  
The code is the primary key: no writer can create a second link with it.

Without it  
Two rows with one code, and a redirect that picks either.

#### `src/main/resources/application.yaml`

The database, the base of short URLs, and the flush interval.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/chhotu/links/LinksApplication.java`

Entry point, with scheduling switched on for the flush.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                             | Test class                     | Result |
|---------------|---------------------------------------------------------|--------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                | `LinkContractTest` (5)         | pass   |
| Every station | Reproduce the failure before the fix                    | `OverwritingCodesTrapTest` (3) | pass   |
| Database      | Rollback and constraint tests against a real database   | `LinkDatabaseTest` (4)         | pass   |
| Concurrency   | A real concurrency test that proves the invariant holds | `LinkConcurrencyTest` (4)      | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.chhotu.links.LinkContractTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.chhotu.links.LinkConcurrencyTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.chhotu.links.LinkDatabaseTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.chhotu.links.OverwritingCodesTrapTest
[INFO] Tests run: 16, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/chhotu/links/OverwritingCodesTrapTest.java`

Written first: the old overwrite, the birthday odds, and the retry.

#### `src/test/java/com/chhotu/links/LinkConcurrencyTest.java`

Clicks and creates on virtual threads released by one latch, including clicks during flushes.

#### `src/test/java/com/chhotu/links/LinkDatabaseTest.java`

Named constraints, case-sensitive codes, every attempt colliding, and a rollback.

#### `src/test/java/com/chhotu/links/LinkContractTest.java`

Create, follow, stats, and every refusal through HTTP.

#### `src/test/java/com/chhotu/links/OldLinkStore.java`

The old store, kept only in tests.

#### `src/test/java/com/chhotu/links/ApiTest.java`

Shared setup: no links and no buffered clicks before each test; flushes are done by hand.

#### `src/test/java/com/chhotu/links/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/chhotu/links/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=CustomCodeChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 16 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in (two Java files and one migration), all 20 tests pass (16 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Custom codes

Marketing may ask for a code of its own, such as `Diwali7`. If it is free, use it; if it is taken, `409`. A chosen code is never swapped for a random one, and never takes over an existing link.

**Done when:** both tests in `CustomCodeChallengeTest` pass.

Hints

- The same `ON CONFLICT DO NOTHING` insert: 0 rows means taken.
- A retry makes sense for a random code, not for one a person chose.

#### `challenge/CustomCodeChallengeTest.java`

``` code
package com.chhotu.links;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: marketing may ask for a code of its own ("Diwali7"), seven base62 characters. If it is taken, that is
 * a 409: a chosen code is never swapped for a random one, and never takes over the existing link.
 */
class CustomCodeChallengeTest extends ApiTest {

    ResultActions createWithCode(String url, String code) throws Exception {
        return mvc.perform(post("/links").contentType(MediaType.APPLICATION_JSON)
                .content("{\"targetUrl\":\"%s\",\"code\":\"%s\"}".formatted(url, code)));
    }

    @Test
    void aFreeCustomCodeIsUsedAsGiven() throws Exception {
        createWithCode("https://shop.example/diwali", "Diwali7").andExpect(status().isCreated()).andExpect(jsonPath("$.code").value("Diwali7"));
        follow("Diwali7").andExpect(status().isFound());
    }

    @Test
    void aTakenCustomCodeIs409AndTheOldLinkStays() throws Exception {
        createWithCode("https://shop.example/diwali", "Diwali7").andExpect(status().isCreated());
        createWithCode("https://other.example/", "Diwali7").andExpect(status().isConflict());
        assertThat(targetOf("Diwali7")).isEqualTo("https://shop.example/diwali");
        createWithCode("https://shop.example/x", "diwali-7").andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Links that expire

An optional `expiresAt`, in the future when the link is made. After it, following the link is `410 Gone`; its stats stay readable. The column comes in a new migration.

**Done when:** both tests in `ExpiryChallengeTest` pass.

Hints

- `@Future` on the request field refuses a past time with `400`.
- Let the database compare with its own clock: `expires_at <= now()`.

#### `challenge/ExpiryChallengeTest.java`

``` code
package com.chhotu.links;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import java.time.OffsetDateTime;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: campaign links may end. An optional "expiresAt" (must be in the future when the link is made); after
 * it, following the link is 410 Gone (it existed, and will not come back), while its stats stay readable.
 */
class ExpiryChallengeTest extends ApiTest {

    String createExpiring(OffsetDateTime at, int expectedStatus) throws Exception {
        return mvc.perform(post("/links").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"targetUrl\":\"https://shop.example/sale\",\"expiresAt\":\"" + at + "\"}"))
                .andExpect(status().is(expectedStatus))
                .andReturn().getResponse().getContentAsString().replaceAll(".*\"code\":\"([^\"]+)\".*", "$1");
    }

    @Test
    void anExpiredLinkIsGoneButItsStatsRemain() throws Exception {
        String code = createExpiring(OffsetDateTime.now().plusDays(7), 201);
        follow(code).andExpect(status().isFound());
        jdbc.sql("UPDATE links SET expires_at = now() - interval '1 minute' WHERE code = ?").param(code).update();
        follow(code).andExpect(status().isGone());
        mvc.perform(get("/links/{c}/stats", code)).andExpect(status().isOk());
    }

    @Test
    void anExpiryInThePastIsRefused() throws Exception {
        createExpiring(OffsetDateTime.now().minusDays(1), 400);
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## 10,000 clicks a second on six servers

A cricket-final campaign link gets 10,000 clicks a second, spread over six app servers. Stats from one server miss the other five's unflushed clicks. Compare a shared counter in a cache (Valkey `INCR`), a click-event stream processed elsewhere, and this station's buffer with a shorter flush. What does each lose in a crash, and how fresh is the count?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: two campaigns forced onto one code.
2.  Make the code the primary key; insert with `ON CONFLICT DO NOTHING` and retry.
3.  Redirect with 302; count in memory; flush on a schedule and on shutdown.
4.  Prove it with parallel clicks, clicks during flushes, and parallel creates.

## Design alternatives and trade-offs

| Choice    | Options                                       | Chosen, and why                                                                                                                 |
|-----------|-----------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| Code      | Sequential base62; random; hash of the URL    | Random: not guessable, and the same URL can have several campaign links. Costs a collision check, which the key gives for free. |
| Collision | Overwrite; retry; longer codes only           | Retry with the key deciding. Longer codes make collisions rare, never impossible.                                               |
| Redirect  | 301; 302; 307                                 | 302: every click reaches us and targets can change. 307 also keeps the method; links are only clicked (GET), so 302 is enough.  |
| Counting  | UPDATE per click; event table; memory + flush | Memory + flush: no lock per click. Costs up to one flush interval of clicks in a crash, a stated limit.                         |

## Database design

| Constraint                  | Rule                            | Why                                                                                   |
|-----------------------------|---------------------------------|---------------------------------------------------------------------------------------|
| `links_pkey`                | The code is unique              | A collision is refused, whoever writes.                                               |
| `links_code_base62`         | 7 characters from 0–9, A–Z, a–z | Codes stay readable in a URL.                                                         |
| `links_target_web`          | Starts with http:// or https:// | A short link can never hide a `javascript:` or `data:` URL, even if Java is bypassed. |
| `links_clicks_non_negative` | clicks ≥ 0                      | A broken flush cannot make counts negative.                                           |

``` code
-- The code is the primary key: two links can never share one, whoever writes. A collision is refused, never merged.
CREATE TABLE links (
    code       VARCHAR(7)    NOT NULL,
    target_url VARCHAR(2048) NOT NULL,
    clicks     BIGINT        NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT links_pkey                PRIMARY KEY (code),
    CONSTRAINT links_code_base62         CHECK (code ~ '^[0-9A-Za-z]{7}$'),
    CONSTRAINT links_target_web          CHECK (target_url ~* '^https?://'),
    CONSTRAINT links_clicks_non_negative CHECK (clicks >= 0)
);
```

# 3 · Go deeper: Production

Abuse  
Shorteners are used to hide phishing links. Real services check targets against blocklists, rate-limit creation, and can disable a link.

Counting limits  
Up to one flush interval of clicks can be lost in a crash; stats on one server miss other servers' unflushed clicks. State both to whoever reads the numbers.

Bots  
Link previews in chat apps and security scanners "click" links too. Raw counts include them unless filtered by user agent or behaviour.

Caching  
The target lookup is one primary-key read. A small in-memory cache helps at very high rates, as long as changed or expired links are invalidated.

# 3 · Go deeper: Interview

## Interview takeaways

How do you generate unique short codes?

Random base62 codes long enough that collisions are rare, a unique key on the code, and an insert that reports a conflict (ON CONFLICT DO NOTHING) followed by a retry. Never resolve a conflict by updating.

301 or 302 for a short link?

302 if you need every click to reach you (counting) or the destination may change. 301 is cached by browsers and proxies, sometimes indefinitely.

How do you count clicks without slowing redirects?

Do not write per click. Increment in memory (LongAdder) and flush totals periodically, or publish events to a queue. Accept and state the small loss window.

Why does a 4-character random code collide so soon?

The birthday problem: with N possible codes, a repeat becomes likely after about √N picks. 62^4 is about 1.5 crore, whose square root is about 3,800.

Why are short codes not lower-cased like other identifiers?

In base62, upper and lower case are different digits. Normalising would merge distinct codes.

## Self-check rubric

| Area        | Meets the bar                    | Above the bar                                          |
|-------------|----------------------------------|--------------------------------------------------------|
| Correctness | All 16 tests pass.               | You ran the flawed version and explained each failure. |
| Uniqueness  | A key and a retry.               | The birthday maths for your code length.               |
| HTTP        | 302 for counted links.           | When 301 or 307 is the right answer.                   |
| Concurrency | Parallel clicks counted exactly. | Why sumThenReset loses nothing during a flush.         |

# 3 · Go deeper: Review

## The pull request

A teammate simplifies the service. An upsert replaces the retry loop, because it "never fails". 301 replaces 302, because it is "faster for users, less load for us". Any URI that parses is accepted, for app deep links. Read both files and list every problem before opening the findings.

#### `review/LinkStore.java`

``` code
package com.chhotu.links;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import java.time.OffsetDateTime;
import java.util.Optional;

@Repository
class LinkStore {

    /** Tries this many codes before giving up; with 7 characters even one retry is extremely rare. */
    static final int ATTEMPTS = 5;

    record Link(String code, String targetUrl, long clicks, OffsetDateTime createdAt) {
    }

    private final JdbcClient jdbc;
    private final CodeGenerator codes;

    LinkStore(JdbcClient jdbc, CodeGenerator codes) {
        this.jdbc = jdbc;
        this.codes = codes;
    }

    /** PR: "An upsert never fails, so no retry loop is needed: one statement, one code, always a link." */
    Optional<String> create(String targetUrl) {
        String code = codes.next();
        jdbc.sql("INSERT INTO links (code, target_url) VALUES (:code, :url) ON CONFLICT (code) DO UPDATE SET target_url = EXCLUDED.target_url")
                .param("code", code).param("url", targetUrl).update();
        return Optional.of(code);
    }

    Optional<String> target(String code) {
        return jdbc.sql("SELECT target_url FROM links WHERE code = :code").param("code", code).query(String.class).optional();
    }

    Optional<Link> link(String code) {
        return jdbc.sql("SELECT code, target_url, clicks, created_at FROM links WHERE code = :code").param("code", code).query(Link.class).optional();
    }

    void addClicks(String code, long clicks) {
        jdbc.sql("UPDATE links SET clicks = clicks + :n WHERE code = :code").param("n", clicks).param("code", code).update();
    }
}
```

#### `review/LinkController.java`

``` code
package com.chhotu.links;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.time.OffsetDateTime;

/** Codes are case-sensitive on purpose: base62 uses upper and lower case as different digits, so they are never normalised. */
@RestController
class LinkController {

    record NewLink(@NotBlank @Size(max = 2048) String targetUrl) {
    }

    record Created(String code, String shortUrl, String targetUrl) {
    }

    record Stats(String code, String targetUrl, long clicks, OffsetDateTime createdAt) {
    }

    private final LinkStore links;
    private final ClickCounter clicks;
    private final String baseUrl;

    LinkController(LinkStore links, ClickCounter clicks, @Value("${chhotu.base-url}") String baseUrl) {
        this.links = links;
        this.clicks = clicks;
        this.baseUrl = baseUrl;
    }

    @PostMapping("/links")
    ResponseEntity<Created> create(@Valid @RequestBody NewLink request) {
        String target = request.targetUrl().strip();
        if (!isWebAddress(target)) {
            throw problem(HttpStatus.BAD_REQUEST, "Not a web address", "targetUrl must be an http or https address with a host.");
        }
        String code = links.create(target).orElseThrow(() ->
                problem(HttpStatus.SERVICE_UNAVAILABLE, "Try again", "Could not find a free short code; please try again."));
        String shortUrl = baseUrl + "/" + code;
        return ResponseEntity.created(URI.create(shortUrl)).body(new Created(code, shortUrl, target));
    }

    /** PR: "301 is permanent, so browsers remember it and skip a round trip: faster for users, less load for us." */
    @GetMapping("/{code:[0-9A-Za-z]{7}}")
    ResponseEntity<Void> follow(@PathVariable String code) {
        String target = links.target(code).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Link not found", "No short link " + code + "."));
        clicks.record(code);
        return ResponseEntity.status(HttpStatus.MOVED_PERMANENTLY).location(URI.create(target)).build();
    }

    /** Stored clicks plus those not yet flushed by this instance. */
    @GetMapping("/links/{code}/stats")
    Stats stats(@PathVariable String code) {
        LinkStore.Link link = links.link(code).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Link not found", "No short link " + code + "."));
        return new Stats(link.code(), link.targetUrl(), link.clicks() + clicks.pending(code), link.createdAt());
    }

    /** PR: "Marketing also shortens app deep links, so accept any URI that parses." */
    static boolean isWebAddress(String url) {
        try {
            return new URI(url).getScheme() != null;
        } catch (java.net.URISyntaxException e) {
            return false;
        }
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
```

## Findings

1An upsert turns a collision into an overwrite

"An upsert never fails" is true, and that is the problem: when the random code is taken, the existing link is silently re-pointed. The original bug again, in one SQL statement.

**Test evidence:** `nowACollisionIsRetriedAndTheFirstLinkIsUntouched` and `whenEveryAttemptCollidesNothingIsOverwrittenAndTheAnswerIs503` fail.

2301 instead of 302

Browsers remember a 301, so repeat clicks never reach Chhotu: counts stop growing, and a campaign's destination can never be changed.

**Test evidence:** `followingALinkIsATemporaryRedirectAndCounts` and `aThousandClicksAtOnceAreAThousandClicks` fail on the status.

3Any parseable URI is accepted

`javascript:` and `data:` parse fine. A short link would hide them. The database's `links_target_web` still refused the row, so nothing harmful was stored, but the user got a `500` instead of a clear `400`.

**Test evidence:** `onlyWebAddressesCanBeShortened` errors with the constraint violation.

## Same tests, flawed version

From `docs/review-run.txt`: the two flawed files copied over the real ones, then the full suite run.

| Test class                 | Fixed version | Flawed version |
|----------------------------|---------------|----------------|
| `LinkConcurrencyTest`      | 4 / 4         | 3 / 4          |
| `LinkContractTest`         | 5 / 5         | 3 / 5          |
| `LinkDatabaseTest`         | 4 / 4         | 3 / 4          |
| `OverwritingCodesTrapTest` | 3 / 3         | 2 / 3          |

The third flaw shows a constraint doing its job: Java let the bad URL through, and the database still refused it. Defence in depth turned a security bug into an ugly error, not a stored phishing link.
