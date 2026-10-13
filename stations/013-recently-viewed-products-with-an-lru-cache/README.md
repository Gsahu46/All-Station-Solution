# Station 013 · Recently viewed products with an LRU cache

Foundations · 0–1 years · Core · E-commerce · Types: Concurrency

Spring Boot 4.1.1 · Java 25 · Spring MVC · LinkedHashMap (LRU) · virtual threads · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Histories live in each server's memory. The trap test starts two real copies of the app on two ports and plays the load balancer itself. Product ids are just numbers: there is no catalogue.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 13 tests.

# 1 · Understand

## The problem in real life

1.  **Ravi browses phones on Kartwala**

    The "recently viewed" strip shows what he looked at. Behind it, the server keeps every product every user ever opened, and its memory slowly fills up.

2.  **Kartwala adds a second server**

    Now Ravi's views land on either server. Refresh, and the strip shows a different half of his history each time.

3.  **The fix**

    Keep only the last 10 per user and at most 10,000 users per server, evicting the least recently used. Make the deployment route each user to one server, and say plainly that this memory is per server.

Memory inside one server is fast, limited and private to that server. Treat it as a cache with limits, never as the one shared truth.

## What are we building?

`POST /users/{id}/recently-viewed` records a view; `GET` returns the last 10 products, newest first, each once. Memory stays bounded, many requests at once stay correct, and the page is honest about what happens with several servers.

## An everyday analogy

A chai stall owner remembers the last few orders of each regular. If a regular reorders, that order comes to the front of the owner's memory. When there are too many regulars to remember, the one who has not visited for longest is forgotten. And if the owner opens a second stall with a second person, that person remembers nothing of the first stall's customers unless each customer keeps going to the same stall.

## How it works in 4 steps

1.  **A view arrives**. The store takes its one lock.
2.  **The user's history**, a small access-order map, puts the product at the end; viewing it again just moves it.
3.  **If the history has 11**, the least recently used product drops out. The same rule caps the number of users.
4.  **The answer** is a copy of the history, newest first.

Check yourself: why can't reads skip the lock, if they only read?

In access order, reading is not only reading: `get` moves the entry to the end, which changes the map's links. Two threads doing that at once can corrupt the map. Every call, reads included, must hold the lock.

## What this station is not

- **Not a shared cache.** Each server has its own memory; a restart forgets everything. Moving the history to Valkey, shared by all servers, is a later station.
- **No login and no catalogue.** User and product ids are just numbers.
- **Limits are demo rules.** 10 products and 10,000 users per server.

## Key terms

| Term                          | Simple meaning                                                               | Everyday example                                                 | In this project                                           |
|-------------------------------|------------------------------------------------------------------------------|------------------------------------------------------------------|-----------------------------------------------------------|
| **Cache**                     | A fast, limited store of things you are likely to need again.                | The few books on your desk, the rest on the shelf.               | Each user's last 10 products.                             |
| **LRU (least recently used)** | When full, throw out what was used longest ago.                              | Clearing the desk: the book untouched for weeks goes back first. | The 11th product pushes out the oldest.                   |
| **Access order**              | A `LinkedHashMap` mode where every read or write moves the entry to the end. | Putting a book on top of the pile each time you open it.         | `new LinkedHashMap<>(16, 0.75f, true)`                    |
| **Bounded memory**            | A hard limit on how much a structure can hold.                               | A desk only so big.                                              | 10 products per user, 10,000 users per server.            |
| **Thread safety**             | Correct even when many requests touch the same data at the same moment.      | One pen for the register, passed hand to hand.                   | One lock (`synchronized`) around the store.               |
| **Load balancer**             | Spreads requests across several servers.                                     | A receptionist sending visitors to any free counter.             | Two app servers in the trap test.                         |
| **Sticky routing**            | Sending the same user to the same server every time.                         | Always seeing the same bank teller.                              | The fix this station can make without new infrastructure. |

# 2 · Build: Spec

## Business problem

**Kartwala** (the marketplace from stations 003 and 009) shows a "recently viewed" strip. The first version kept every product a user ever opened, in a plain map that only grew; memory alarms started a few weeks after launch. When a second server was added for the sale, customers saw a different strip on every refresh.

## Acceptance criteria

1.  **Given** views of 101, 102, 103, **then** the history is 103, 102, 101.
2.  **Given** 101 viewed again, **then** it moves to the front and is listed once.
3.  **Given** an 11th product, **then** the least recently viewed one is dropped; a re-viewed old product is kept.
4.  **Given** more than 10,000 users on a server, **then** the least recently active user's history is dropped.
5.  **Given** 200 views by one user at the same moment, **then** every request succeeds and the history holds 10 distinct products.
6.  **Given** two servers and round-robin routing, **then** histories split (the trap); **given** routing by user, **then** one server holds the whole history.

## Requirements

- At most 10 products per user and 10,000 users per server (demo rules), least recently used out first.
- Every operation on the store holds one lock; responses are copies.
- User and product ids are positive numbers; anything else is `400`.
- Deployment rule: with several servers, route by user id, and accept that a restart forgets histories.

## Learning objectives

- Build an LRU cache with `LinkedHashMap` in access order and `removeEldestEntry`.
- Bound every in-memory structure that grows with users.
- Explain why access-order reads need a lock, and prove thread safety with a real parallel test.
- Explain what per-server memory means behind a load balancer, and the options.

# 2 · Build: API contract

## Endpoints

| Method | Path                              | Purpose                                                                  |
|--------|-----------------------------------|--------------------------------------------------------------------------|
| `POST` | `/users/{userId}/recently-viewed` | Body `{"productId": 101}`. Records the view; returns the history.        |
| `GET`  | `/users/{userId}/recently-viewed` | The history: `userId`, `productIds` newest first (empty for a new user). |

## Status codes

| Status | When                                                            |
|--------|-----------------------------------------------------------------|
| 200    | Recorded, or read                                               |
| 400    | User id or product id not a positive number; missing product id |

## Captured examples

Captured with curl from the running app on 13 Oct 2026, after viewing 101, 102 and 103. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: product 101 viewed again

**Why:** in access order, putting 101 again moves it to the end, which the API lists first. Still three products.

Request

``` code
POST /users/7/recently-viewed HTTP/1.1
Content-Type: application/json

{
  "productId": 101
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 39

{
  "userId": 7,
  "productIds": [
    101,
    103,
    102
  ]
}
```

### Case 2: after eleven different products

**Why:** the history stops at 10. Product 102 was untouched the longest, so it went; 101 survived because it was viewed again.

Request

``` code
GET /users/7/recently-viewed HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 67

{
  "userId": 7,
  "productIds": [
    111,
    110,
    109,
    108,
    107,
    106,
    105,
    104,
    101,
    103
  ]
}
```

### Case 3: a user with no views

**Why:** an empty history is `200` with an empty list.

Request

``` code
GET /users/8/recently-viewed HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 28

{
  "userId": 8,
  "productIds": []
}
```

### Case 4: user 0

**Why:** ids are positive: `400`.

Request

``` code
POST /users/0/recently-viewed HTTP/1.1
Content-Type: application/json

{
  "productId": 101
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Validation failure",
  "instance": "/users/0/recently-viewed",
  "status": 400,
  "title": "Bad Request"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                              | What happens                                   | Proved by                                                    |
|---------------------------------------------------|------------------------------------------------|--------------------------------------------------------------|
| Three views                                       | Newest first                                   | `viewsAreListedNewestFirst`                                  |
| The same product again                            | Moves to the front, listed once                | `viewingAgainMovesTheProductToTheFrontWithoutADuplicate`     |
| 11th product                                      | The oldest drops out                           | `theEleventhProductPushesOutTheOldest`                       |
| An old product re-viewed before the 11th          | Kept; the next oldest drops                    | `reViewingAnOldProductSavesItFromEviction`                   |
| Reading counts as using                           | `get` saves an entry from eviction             | `theLeastRecentlyUsedEntryIsEvicted`                         |
| 10,005 users                                      | 10,000 kept; the least recently active dropped | `theServerKeepsAtMostMaxUsersAndDropsTheLeastRecentlyActive` |
| A list kept by the caller                         | Does not change later                          | `aReturnedListDoesNotChangeAfterwards`                       |
| Two users; a new user                             | Separate; empty                                | `usersHaveSeparateHistoriesAndANewUserHasNone`               |
| User 0, product -5, no product, user "abc"        | `400`                                          | `badInputIs400`                                              |
| 200 views by one user at once                     | All `200`; 10 distinct                         | `twoHundredViewsByOneUserAtOnceLeaveTenDistinctProducts`     |
| 1,000 mixed reads and writes for 50 users at once | All `200`; limits hold                         | `readsAndWritesForManyUsersAtOnceNeverBreakTheLimits`        |

## The trap

Plausible but wrong

Treating a per-server in-memory cache as shared: each server shows different history.

On one laptop, memory looks like "the" store. The trap test starts two real copies of the app and plays a round-robin load balancer: the first view lands on server A, the second on B, and each server shows half the history. The second test routes user 8 to the same server every time, and the history stays whole. That is the fix this station can make without new infrastructure; its limits (a restart forgets, adding a server moves users) are why a shared store comes in a later station.

``` code
package com.kartwala.recent;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.server.context.WebServerApplicationContext;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestClient;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * Kartwala runs two servers behind a load balancer. Each request may land on either one.
 * This test starts two real copies of the app, on two ports, and plays the load balancer.
 */
class PerServerCacheTrapTest {

    static ConfigurableApplicationContext serverA, serverB;
    static List<RestClient> servers;

    @BeforeAll
    static void startTwoServers() {
        serverA = new SpringApplicationBuilder(RecentlyViewedApplication.class).properties("server.port=0").run();
        serverB = new SpringApplicationBuilder(RecentlyViewedApplication.class).properties("server.port=0").run();
        servers = List.of(client(serverA), client(serverB));
    }

    @AfterAll
    static void stopServers() {
        serverA.close();
        serverB.close();
    }

    static RestClient client(ConfigurableApplicationContext app) {
        int port = ((WebServerApplicationContext) app).getWebServer().getPort();
        return RestClient.create("http://localhost:" + port);
    }

    static void view(RestClient server, long user, long product) {
        server.post().uri("/users/{id}/recently-viewed", user).contentType(MediaType.APPLICATION_JSON)
                .body(Map.of("productId", product)).retrieve().toBodilessEntity();
    }

    @SuppressWarnings("unchecked")
    static List<Integer> history(RestClient server, long user) {
        return (List<Integer>) server.get().uri("/users/{id}/recently-viewed", user).retrieve().body(Map.class).get("productIds");
    }

    @Test
    void roundRobinSendsTheReadToTheServerThatNeverSawTheViews() {
        // The "before" assumption: the in-memory history is "the" history. Round robin: A, B, A, B...
        view(servers.get(0), 7, 501);
        view(servers.get(1), 7, 502);
        assertThat(history(servers.get(0), 7)).containsExactly(501); // the strip shows half the history
        assertThat(history(servers.get(1), 7)).containsExactly(502); // and a different half on the next refresh
    }

    @Test
    void routingEachUserToOneServerKeepsTheirHistoryTogether() {
        // The fix this station can make without new infrastructure: the load balancer sends a user to the same
        // server every time (sticky routing by user id). Its limits are on the page: a restart or a new server
        // loses or moves histories. A shared store (Valkey, a later station) removes them.
        RestClient home = servers.get((int) (8 % servers.size()));
        view(home, 8, 601);
        view(home, 8, 602);
        assertThat(history(home, 8)).containsExactly(602, 601);
    }
}
```

### Measured while building: what the lock is worth

With `synchronized` removed from the store, the 200-parallel-views test failed in 3 runs out of 3, with `ArrayIndexOutOfBoundsException` from inside the corrupted map. With only the read method unlocked ("reads are safe"), the same tests passed 5 runs out of 5, even though that version is broken by design. A race that tests do not catch is still a race; the rule is "every call holds the lock", not "the tests are green".

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
./mvnw test                 # all 13 tests (the trap test starts two more servers on free ports)
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Virtual threads, used by the concurrency test, are in Java 21 and later.

## Try it yourself: two servers

Start two copies on two ports, in two terminals, and view products on each:

``` code
./mvnw spring-boot:run -Dspring-boot.run.arguments=--server.port=8081
./mvnw spring-boot:run -Dspring-boot.run.arguments=--server.port=8082

curl -X POST http://localhost:8081/users/7/recently-viewed -H "Content-Type: application/json" -d "@docs/view.json"
curl http://localhost:8081/users/7/recently-viewed     # [101]
curl http://localhost:8082/users/7/recently-viewed     # []  the other server has never seen it
```

## Troubleshooting

| You see                            | Cause                             | Fix                                                      |
|------------------------------------|-----------------------------------|----------------------------------------------------------|
| `Port 8081 was already in use`     | Something else uses the port.     | Pick other ports.                                        |
| An empty history after a restart   | Memory does not survive restarts. | Expected: see the trap.                                  |
| `release version 25 not supported` | Maven is using an older JDK.      | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`. |

## Project layout

``` tree
stations/013-recently-viewed-products-with-an-lru-cache/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/kartwala/recent/
│   ├── RecentlyViewedController.java   ├── RecentlyViewed.java   ├── LruMap.java
│   └── RecentlyViewedApplication.java
├── src/test/java/com/kartwala/recent/   (see Tests)
├── review/                   the flawed version (see Review)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/kartwala/recent/RecentlyViewedController.java`

Does  
Two endpoints; validates ids.

Why  
HTTP in one place.

Without it  
No API.

#### `src/main/java/com/kartwala/recent/RecentlyViewed.java`

Does  
The store: a bounded LRU of users, each with a bounded LRU of products, behind one lock.

Why  
Both limits make memory bounded whatever the traffic; one lock makes every operation safe.

Without it  
A plain map that grows forever, and races on access-order maps.

- `list` returns a copy, so a caller's list never changes underneath it.
- The class comment states the per-server limit: the next developer must see it.

#### `src/main/java/com/kartwala/recent/LruMap.java`

Does  
A `LinkedHashMap` in access order that removes its eldest entry above a size.

Why  
Ten lines give a correct LRU: the JDK already keeps the order.

Without it  
Hand-written linked lists and eviction code.

- `true` in the constructor is access order; `false` (the default) is insertion order, where re-viewing moves nothing.
- `size() > maxSize`, not `>=`: the check runs after the new entry is added.

#### `src/main/resources/application.yaml`

RFC 9457 problem bodies for every error.

#### `src/main/java/com/kartwala/recent/RecentlyViewedApplication.java`

Standard Spring Boot entry point.

# 2 · Build: Tests

## Required tests for this station

Station type: Concurrency

| Required by   | Requirement                                             | Test class                          | Result |
|---------------|---------------------------------------------------------|-------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                | `RecentlyViewedContractTest` (6)    | pass   |
| Every station | Reproduce the failure before the fix                    | `PerServerCacheTrapTest` (2)        | pass   |
| Concurrency   | A real concurrency test that proves the invariant holds | `RecentlyViewedConcurrencyTest` (2) | pass   |
| This station  | LRU rules and the user bound                            | `LruMapTest` (3)                    | pass   |

"Not found" here is a user with no history: `200` with an empty list.

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.recent.PerServerCacheTrapTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.recent.LruMapTest
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.recent.RecentlyViewedContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.recent.RecentlyViewedConcurrencyTest
[INFO] Tests run: 13, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/kartwala/recent/PerServerCacheTrapTest.java`

Written first: two real servers, round robin against routing by user.

#### `src/test/java/com/kartwala/recent/RecentlyViewedConcurrencyTest.java`

200 and 1,000 requests released together on virtual threads; a 60-second timeout in case a broken map loops.

#### `src/test/java/com/kartwala/recent/RecentlyViewedContractTest.java`

Order, moves, eviction, separate users, bad input.

#### `src/test/java/com/kartwala/recent/LruMapTest.java`

Access order, the 10,000-user bound, copies.

#### `src/test/java/com/kartwala/recent/ApiTest.java`

Shared setup: the whole app through MockMvc, empty history before each test.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/kartwala/recent/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=RemoveProductChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 13 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 17 tests pass (13 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Remove a product from the strip

Add `DELETE /users/{userId}/recently-viewed/{productId}`: `204`, also when the product (or the user) was never there.

**Done when:** both tests in `RemoveProductChallengeTest` pass, and the station's tests still pass.

Hints

- Take the store's lock like every other method.
- Deleting what is not there gives the same result as deleting it: `204` (station 008).

#### `challenge/RemoveProductChallengeTest.java`

``` code
package com.kartwala.recent;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: the "x" on a product in the strip: DELETE /users/{id}/recently-viewed/{productId}, safe to repeat. */
class RemoveProductChallengeTest extends ApiTest {

    @Test
    void removingAProductIs204AndItIsGone() throws Exception {
        view(7, 101);
        view(7, 102);
        mvc.perform(delete("/users/7/recently-viewed/101")).andExpect(status().isNoContent());
        mvc.perform(get("/users/7/recently-viewed")).andExpect(jsonPath("$.productIds", contains(102)));
    }

    @Test
    void removingTwiceOrRemovingSomethingNeverViewedIsStill204() throws Exception {
        view(7, 101);
        mvc.perform(delete("/users/7/recently-viewed/101")).andExpect(status().isNoContent());
        mvc.perform(delete("/users/7/recently-viewed/101")).andExpect(status().isNoContent());
        mvc.perform(delete("/users/99/recently-viewed/5")).andExpect(status().isNoContent());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 40 minutes

## Forget views after 30 days

Views older than 30 days should not be shown. Store when each product was viewed, and filter on read. Viewing again restarts the 30 days.

**Done when:** both tests in `ExpiryChallengeTest` pass. The test brings its own movable clock.

Hints

- Store an `Instant` instead of `Boolean.TRUE` as the map value.
- Inject a `Clock` bean so the test can move time; keep a no-argument constructor for the station's tests.
- Filtering on read is enough: old entries leave through the LRU limit anyway.

#### `challenge/ExpiryChallengeTest.java`

``` code
package com.kartwala.recent;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** Challenge 2: views older than 30 days are not shown. Time is moved by a test clock, not waited for. */
@Import(ExpiryChallengeTest.Clocks.class)
class ExpiryChallengeTest extends ApiTest {

    static class MovableClock extends Clock {
        Instant now = Instant.parse("2026-10-01T10:00:00Z");

        @Override
        public Instant instant() {
            return now;
        }

        @Override
        public ZoneId getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(ZoneId zone) {
            return this;
        }
    }

    @TestConfiguration
    static class Clocks {
        @Bean
        @Primary
        MovableClock movableClock() {
            return new MovableClock();
        }
    }

    @Autowired
    MovableClock clock;

    @Test
    void aViewOlderThanThirtyDaysDisappears() throws Exception {
        view(7, 101);
        clock.now = clock.now.plus(Duration.ofDays(29));
        view(7, 102);
        mvc.perform(get("/users/7/recently-viewed")).andExpect(jsonPath("$.productIds", contains(102, 101)));
        clock.now = clock.now.plus(Duration.ofDays(2));    // 101 is now 31 days old
        mvc.perform(get("/users/7/recently-viewed")).andExpect(jsonPath("$.productIds", contains(102)));
    }

    @Test
    void viewingAgainRestartsTheThirtyDays() throws Exception {
        view(7, 201);
        clock.now = clock.now.plus(Duration.ofDays(25));
        view(7, 201);
        clock.now = clock.now.plus(Duration.ofDays(25));
        mvc.perform(get("/users/7/recently-viewed")).andExpect(jsonPath("$.productIds", contains(201)));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Moving the history out of the servers

Kartwala will run 8 servers and restart them during deploys. Compare three designs: sticky routing (this station), a shared Valkey list per user (`LPUSH`, `LREM`, `LTRIM`), and keeping the history on the phone. For each: what is lost on a restart, what happens when two servers update the same user at once, and what it costs.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: two real servers, round robin, split history.
2.  Write `LruMap`: access order plus `removeEldestEntry`.
3.  Nest two of them: users, then products per user. Put one lock around every method.
4.  Prove the lock with real parallel requests; prove the bounds with unit tests.
5.  Write the deployment rule down where developers will read it: in the class comment and on this page.

## Design alternatives and trade-offs

| Approach                                | What it costs                                                                        | Verdict            |
|-----------------------------------------|--------------------------------------------------------------------------------------|--------------------|
| Access-order `LinkedHashMap` + one lock | One lock is a bottleneck at very high traffic on one server; fine here.              | Chosen             |
| `HashMap` of lists that only grow       | Memory grows forever.                                                                | Wrong              |
| `ConcurrentHashMap` and no lock         | The outer map is safe, the per-user maps are not, and it has no size limit.          | Wrong (see Review) |
| Caffeine cache                          | A tested library with size limits, expiry and good concurrency; one more dependency. | At scale           |
| Shared store (Valkey)                   | Every server sees the same history and it survives restarts; another system to run.  | Later station      |

## Database design

None. If history had to be kept for a long time, it would be a table of (user, product, viewed_at) with a job deleting old rows; a cache is the wrong place for data you cannot lose.

# 3 · Go deeper: Production

Memory  
Worst case is 10,000 users × 10 products per server: about 100,000 small entries. Bounded, so it cannot cause a memory alarm on its own.

Concurrency  
One lock serialises every request to the store. Each operation takes microseconds, so it is fine at this scale; at much higher traffic, use a concurrent cache library.

Reliability  
Restarts and deploys forget histories. That is acceptable for a "recently viewed" strip, not for anything a customer would miss.

Scale  
With several servers, route by user (sticky) or move the history to a shared store. Adding a server changes the routing, so some users see an empty strip once.

# 3 · Go deeper: Interview

## Interview takeaways

How do you build an LRU cache in Java?

LinkedHashMap with accessOrder = true and an override of removeEldestEntry that returns size() \> max. Every get or put moves the entry to the end; the eldest is the least recently used.

Is a LinkedHashMap in access order safe to read from several threads?

No. In access order, get() moves the entry, which changes the map's internal links. Every call needs a lock (or use a concurrent cache library).

Why does ConcurrentHashMap not make this store thread-safe?

It makes the outer map's own operations safe, but the per-user maps inside are ordinary LinkedHashMaps changed from many threads. It also has no size limit.

What happens to in-memory caches behind a load balancer?

Each server has its own copy. Users see different data depending on which server they hit, and a restart empties it. Use sticky routing or a shared cache, and decide what losing it means.

How do you test thread safety?

Release many real requests at the same moment (a latch and virtual threads), then check the invariants. Remember that a passing test does not prove the absence of races; the design must make races impossible.

## Self-check rubric

| Area        | Meets the bar                 | Above the bar                                                         |
|-------------|-------------------------------|-----------------------------------------------------------------------|
| Correctness | All 13 tests pass.            | You can predict which tests the flawed version fails.                 |
| Concurrency | Every method holds the lock.  | You can explain why a green test did not catch unlocked reads.        |
| Design      | Two bounded LRUs.             | You can compare sticky routing with a shared cache.                   |
| Explanation | Access order in one sentence. | You can explain the trap to someone who has only ever run one server. |

# 3 · Go deeper: Review

## The pull request

"Performance: removed the global lock, ConcurrentHashMap is thread-safe. Also simplified LruMap." Read both files and list every problem before opening the findings.

#### `review/RecentlyViewed.java`

``` code
package com.kartwala.recent;

import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/** Recently viewed products. ConcurrentHashMap makes it thread-safe, so no synchronized needed (faster). */
@Component
class RecentlyViewed {

    static final int PER_USER = 10;
    static final int MAX_USERS = 10_000;

    private final Map<Long, LruMap<Long, Boolean>> users = new ConcurrentHashMap<>();

    List<Long> record(long userId, long productId) {
        users.computeIfAbsent(userId, id -> new LruMap<>(PER_USER)).put(productId, Boolean.TRUE);
        return list(userId);
    }

    List<Long> list(long userId) {
        LruMap<Long, Boolean> history = users.get(userId);
        if (history == null) {
            return List.of();
        }
        List<Long> newestFirst = new ArrayList<>(history.keySet());
        Collections.reverse(newestFirst);
        return newestFirst;
    }

    int userCount() {
        return users.size();
    }

    void clear() {
        users.clear();
    }
}
```

#### `review/LruMap.java`

``` code
package com.kartwala.recent;

import java.util.LinkedHashMap;
import java.util.Map;

/** A bounded map: once it holds maxSize entries, the oldest one is removed. */
class LruMap<K, V> extends LinkedHashMap<K, V> {

    private final int maxSize;

    LruMap(int maxSize) {
        super(16, 0.75f);
        this.maxSize = maxSize;
    }

    @Override
    protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
        return size() >= maxSize;
    }
}
```

## Findings

1`LinkedHashMap` in insertion order

`super(16, 0.75f)` leaves access order off. Re-viewing a product does not move it, and the product the user just looked at can be the one evicted.

**Test evidence:** `viewingAgainMovesTheProductToTheFrontWithoutADuplicate`, `reViewingAnOldProductSavesItFromEviction`, `theLeastRecentlyUsedEntryIsEvicted`.

2Off by one in `removeEldestEntry`

`size() >= maxSize` runs after the new entry is added, so the map keeps 9, not 10.

**Test evidence:** `theEleventhProductPushesOutTheOldest` (9 items) and the 200-parallel-views test, which expects 10.

3"ConcurrentHashMap makes it thread-safe"

The outer map is safe, but every user's history is a plain `LinkedHashMap` changed by many threads with no lock, and the outer map has no size limit at all.

**Test evidence:** `theServerKeepsAtMostMaxUsersAndDropsTheLeastRecentlyActive` (10,005 users kept). The concurrency test failed too in our runs (see the table).

## Same tests, flawed version

From `docs/review-run.txt`: the two flawed files copied over the real ones, then the full suite run.

| Test class                      | Fixed version | Flawed version |
|---------------------------------|---------------|----------------|
| `PerServerCacheTrapTest`        | 2 / 2         | 2 / 2          |
| `LruMapTest`                    | 3 / 3         | 1 / 3          |
| `RecentlyViewedConcurrencyTest` | 2 / 2         | 1 / 2          |
| `RecentlyViewedContractTest`    | 6 / 6         | 3 / 6          |

The trap test passes on the flawed version: it is about deployment, not about this code. Each test answers its own question.
